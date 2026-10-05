using System.Text.Json;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;
using HousePlanner.API.DTOs;
using HousePlanner.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/customer/construction")]
[Authorize(Roles = "Customer")]
public class CustomerConstructionController : ControllerBase
{
    private readonly ApplicationDbContext _db;
    private readonly ICurrentUserContextService _currentUser;
    private readonly IConstructorWorkflowService _workflow;
    private readonly IStaffAccountService _staff;

    public CustomerConstructionController(ApplicationDbContext db, ICurrentUserContextService currentUser, IConstructorWorkflowService workflow, IStaffAccountService staff)
    {
        _db = db; _currentUser = currentUser; _workflow = workflow; _staff = staff;
    }

    private async Task<Guid?> CustomerId()
    {
        var user = await _currentUser.GetAsync(HttpContext);
        if (user is null || !string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase))
            return null;
        return user.Id;
    }

    [HttpGet("approved-designs")]
    public async Task<IActionResult> ApprovedDesigns()
    {
        var customerId = await CustomerId(); if (customerId is null) return Unauthorized();

        var customerWorkflowIds = await _db.WorkflowStates.AsNoTracking()
            .Where(w => w.LandSubmission.ClientId == customerId)
            .Select(w => w.Id)
            .ToListAsync();

        var items = await _db.ValidationRequests.AsNoTracking()
            .Where(v => customerWorkflowIds.Contains(v.WorkflowStateId) && v.Status == "Approved")
            .Include(v => v.HouseDesign).ThenInclude(d => d!.CostEstimates)
            .Include(v => v.WorkflowState).ThenInclude(w => w.HouseDesigns).ThenInclude(d => d.CostEstimates)
            .OrderByDescending(v => v.DecisionAt)
            .ToListAsync();

        var distinctDesigns = items.Select(v =>
        {
            var design = v.HouseDesign ?? v.WorkflowState?.HouseDesigns?.FirstOrDefault(d => d.Id == v.WorkflowState.PreferredHouseDesignId && !d.IsArchived);
            if (design == null || design.IsArchived) return null;
            var cost = design.CostEstimates.OrderByDescending(c => c.CreatedAt).FirstOrDefault();
            return new
            {
                designId = design.Id,
                basePreDesignedPlanId = design.BasePreDesignedPlanId,
                workflowId = v.WorkflowStateId,
                version = design.Version,
                floorCount = design.FloorCount,
                area = design.TotalBuiltUpAreaSqft,
                layoutJson = design.LayoutJson,
                approvedAt = v.DecisionAt,
                cost = ToCostSummary(cost),
                title = DesignTitle(design.LayoutJson, design.Version),
                bedrooms = CountRooms(design.LayoutJson, "bedroom"),
                bathrooms = CountRooms(design.LayoutJson, "bathroom")
            };
        }).Where(x => x is not null).Select(x => x!).DistinctBy(x => x.designId).ToList();

        return Ok(distinctDesigns);
    }

    [HttpGet("constructors")]
    public async Task<IActionResult> Constructors(CancellationToken cancellationToken)
    {
        if (await CustomerId() is null) return Unauthorized();
        var constructors = await _db.Users.AsNoTracking()
            .Where(u => u.Role!.Name == "Constructor")
            .OrderBy(u => u.FullName)
            .Select(u => new { id = u.Id, name = u.FullName })
            .ToListAsync(cancellationToken);
        return Ok(constructors);
    }

    [HttpPost("requests")]
    public async Task<IActionResult> CreateRequest([FromBody] CreateConstructionRequest dto, CancellationToken cancellationToken)
    {
        var customerId = await CustomerId(); if (customerId is null) return Unauthorized();
        var approved = await _db.ValidationRequests
            .Include(v => v.WorkflowState).ThenInclude(w => w.LandSubmission)
            .Include(v => v.WorkflowState).ThenInclude(w => w.HouseDesigns)
            .FirstOrDefaultAsync(v => (v.HouseDesignId == dto.HouseDesignId || v.WorkflowState.PreferredHouseDesignId == dto.HouseDesignId) && v.Status == "Approved", cancellationToken);
        if (approved == null) return BadRequest(new { message = "Construction can only be requested for an architect-approved design." });
        if (approved.ClientId != customerId || approved.WorkflowState.LandSubmission.ClientId != customerId) return NotFound();

        var isConstructor = await _db.Users.AnyAsync(u => u.Id == dto.ConstructorId && u.Role!.Name == "Constructor", cancellationToken);
        if (!isConstructor) return BadRequest(new { message = "The selected account is not an available constructor." });

        var project = await _db.Projects.FirstOrDefaultAsync(p => p.WorkflowStateId == approved.WorkflowStateId, cancellationToken);
        if (project == null)
        {
            project = NewProject(approved.WorkflowStateId, dto.HouseDesignId);
            _db.Projects.Add(project);
        }
        if (project.HouseDesignId != null && project.HouseDesignId != dto.HouseDesignId)
            return Conflict(new { message = "The construction project is linked to a different approved design." });
        if (project.ContractorId != null) return Conflict(new { message = "This design already has an active construction project." });
        project.HouseDesignId = dto.HouseDesignId;

        if (await _db.ConstructorProjectRequests.AnyAsync(r => r.HouseDesignId == dto.HouseDesignId && r.ConstructorId == dto.ConstructorId && r.Status == "Pending", cancellationToken))
            return Conflict(new { message = "A pending request already exists for this constructor." });

        var request = new ConstructorProjectRequest
        {
            Id = Guid.NewGuid(),
            Project = project,
            ProjectId = project.Id,
            CustomerId = customerId.Value,
            ConstructorId = dto.ConstructorId,
            HouseDesignId = dto.HouseDesignId,
            Status = "Pending"
        };
        _db.ConstructorProjectRequests.Add(request);
        try { await _db.SaveChangesAsync(cancellationToken); }
        catch (DbUpdateException)
        {
            _db.Entry(request).State = EntityState.Detached;
            if (await _db.ConstructorProjectRequests.AsNoTracking().AnyAsync(r => r.HouseDesignId == dto.HouseDesignId && r.ConstructorId == dto.ConstructorId && r.Status == "Pending", cancellationToken))
                return Conflict(new { message = "A pending request already exists for this constructor." });
            throw;
        }
        return CreatedAtAction(nameof(GetConstruction), new { }, new { request.Id, request.Status });
    }

    [HttpPost("requests/from-plan")]
    public async Task<IActionResult> CreateRequestFromPlan([FromBody] CreateConstructionRequestFromPlan dto, CancellationToken cancellationToken)
    {
        var customerId = await CustomerId(); if (customerId is null) return Unauthorized();
        var isConstructor = await _db.Users.AnyAsync(u => u.Id == dto.ConstructorId && u.Role!.Name == "Constructor", cancellationToken);
        if (!isConstructor) return BadRequest(new { message = "The selected account is not an available constructor." });

        var plan = await _db.PreDesignedHousePlans.FirstOrDefaultAsync(p => p.Id == dto.BasePreDesignedPlanId && p.IsActive, cancellationToken);
        if (plan == null) return NotFound("Plan not found or not architect-validated.");

        var executionStrategy = _db.Database.CreateExecutionStrategy();

        var request = new ConstructorProjectRequest();

        await executionStrategy.ExecuteAsync(async () =>
        {
            using var transaction = await _db.Database.BeginTransactionAsync(cancellationToken);

            var landSubmission = new LandSubmission { Id = Guid.NewGuid(), ClientId = customerId.Value, BasePreDesignedPlanId = plan.Id, LandSizePerches = plan.MinimumLandSizePerches, PreferredBedrooms = plan.Bedrooms, PreferredFloors = plan.FloorCount, CreatedAt = DateTimeOffset.UtcNow, UpdatedAt = DateTimeOffset.UtcNow };
            var workflow = new WorkflowState { Id = Guid.NewGuid(), LandSubmissionId = landSubmission.Id, Status = "approved", ApprovalStatus = "approved", CreatedAt = DateTimeOffset.UtcNow, UpdatedAt = DateTimeOffset.UtcNow };
            var houseDesign = new HouseDesign { Id = Guid.NewGuid(), WorkflowStateId = workflow.Id, BasePreDesignedPlanId = plan.Id, DesignSource = "PreDesignedPlan", LayoutJson = plan.LayoutJson, FloorCount = plan.FloorCount, TotalBuiltUpAreaSqft = plan.TotalBuiltUpAreaSqft, Version = 1, IsCurrent = true };

            _db.LandSubmissions.Add(landSubmission);
            _db.WorkflowStates.Add(workflow);
            _db.HouseDesigns.Add(houseDesign);
            await _db.SaveChangesAsync(cancellationToken);

            workflow.PreferredHouseDesignId = houseDesign.Id;
            await _db.SaveChangesAsync(cancellationToken);

            var validationRequest = new ValidationRequest { Id = Guid.NewGuid(), WorkflowStateId = workflow.Id, HouseDesignId = houseDesign.Id, ClientId = customerId.Value, Status = "Approved", DecisionAt = DateTimeOffset.UtcNow };
            var project = NewProject(workflow.Id, houseDesign.Id);

            _db.ValidationRequests.Add(validationRequest);
            _db.Projects.Add(project);
            await _db.SaveChangesAsync(cancellationToken);

            request = new ConstructorProjectRequest { Id = Guid.NewGuid(), Project = project, ProjectId = project.Id, CustomerId = customerId.Value, ConstructorId = dto.ConstructorId, HouseDesignId = houseDesign.Id, Status = "Pending" };
            _db.ConstructorProjectRequests.Add(request);
            await _db.SaveChangesAsync(cancellationToken);

            await transaction.CommitAsync(cancellationToken);
        });

        return CreatedAtAction(nameof(GetConstruction), new { }, new { request.Id, request.Status });
    }

    [HttpGet]
    public async Task<IActionResult> GetConstruction()
    {
        var customerId = await CustomerId(); if (customerId is null) return Unauthorized();

        var customerWorkflowIds = await _db.WorkflowStates.AsNoTracking()
            .Where(w => w.LandSubmission.ClientId == customerId)
            .Select(w => w.Id)
            .ToListAsync();

        var requests = await _db.ConstructorProjectRequests.AsNoTracking()
            .Where(r => r.CustomerId == customerId).Include(r => r.Constructor).Include(r => r.HouseDesign)
            .OrderByDescending(r => r.CreatedAt).Select(r => new
            {
                r.Id,
                r.ProjectId,
                r.HouseDesignId,
                constructorName = r.Constructor != null ? r.Constructor.FullName : "Unknown",
                r.Status,
                r.DeclineReason,
                requestedAt = r.CreatedAt,
                r.RespondedAt,
                designVersion = r.HouseDesign != null ? (int?)r.HouseDesign.Version : null
            }).ToListAsync();

        var projects = await _db.Projects.AsNoTracking()
            .Where(p => customerWorkflowIds.Contains(p.WorkflowStateId) && p.ContractorId != null && p.Status != "Cancelled")
            .Include(p => p.Contractor).Include(p => p.HouseDesign).ThenInclude(d => d!.CostEstimates).Include(p => p.ConstructionPhases)
            .OrderByDescending(p => p.UpdatedAt).ToListAsync();

        return Ok(new
        {
            pendingRequests = requests.Where(r => r.Status == "Pending"),
            declinedRequests = requests.Where(r => r.Status == "Declined"),
            activeProjects = projects.Where(p => !p.Status.Equals("completed", StringComparison.OrdinalIgnoreCase) && !p.Status.Equals("cancelled", StringComparison.OrdinalIgnoreCase)).Select(ProjectSummary),
            completedProjects = projects.Where(p => p.Status.Equals("completed", StringComparison.OrdinalIgnoreCase)).Select(ProjectSummary)
        });
    }

    [HttpGet("projects/{projectId:guid}")]
    public async Task<IActionResult> Project(Guid projectId)
    {
        var customerId = await CustomerId(); if (customerId is null) return Unauthorized();
        var project = await _db.Projects.AsNoTracking()
            .Include(p => p.Contractor).Include(p => p.HouseDesign).ThenInclude(d => d!.CostEstimates).Include(p => p.ConstructionPhases)
            .FirstOrDefaultAsync(p => p.Id == projectId && p.WorkflowState!.LandSubmission.ClientId == customerId);
        if (project == null || project.ContractorId == null) return NotFound();
        var logs = await _db.ConstructorWorkflowLogs.AsNoTracking().Include(l => l.ConstructionPhase)
            .Where(l => l.ProjectId == projectId).OrderByDescending(l => l.Date).ThenByDescending(l => l.CreatedAt).ToListAsync();
        var progress = await _workflow.GetProjectProgressAsync(projectId, Guid.Empty, "Admin");
        return Ok(new
        {
            project = ProjectSummary(project),
            progress,
            phases = project.ConstructionPhases.OrderBy(p => p.SequenceOrder).Select(p => new { p.Id, p.PhaseName, p.Status, p.SequenceOrder, p.AiEstimatedDurationDays, p.PlannedDurationDays, p.PlannedStartDate, p.PlannedEndDate }),
            logs = logs.Select(l => new { l.Id, l.Date, l.CompletedWork, l.ProgressPercentage, l.Status, l.Challenges, l.Issues, l.Resolution, l.TomorrowPlan, l.AdditionalNotes, phase = l.ConstructionPhase == null ? null : l.ConstructionPhase.PhaseName }),
            activity = logs.GroupBy(l => DateOnly.FromDateTime(l.Date.UtcDateTime)).Select(g => new { date = g.Key, count = g.Count(), intensity = Math.Min(3, g.Count()) })
        });
    }

    [HttpPatch("projects/{projectId:guid}/cancel")]
    public async Task<IActionResult> CancelProject(Guid projectId, CancellationToken cancellationToken)
    {
        var customerId = await CustomerId(); if (customerId is null) return Unauthorized();

        var project = await _db.Projects
            .Include(p => p.WorkflowState).ThenInclude(w => w!.LandSubmission)
            .FirstOrDefaultAsync(p => p.Id == projectId, cancellationToken);

        if (project == null) return NotFound(new { message = "Project not found." });
        if (project.WorkflowState?.LandSubmission.ClientId != customerId) return Forbid();

        if (project.Status.Equals("completed", StringComparison.OrdinalIgnoreCase) ||
            project.Status.Equals("cancelled", StringComparison.OrdinalIgnoreCase))
        {
            return BadRequest(new { message = $"Cannot cancel a project that is already {project.Status.ToLower()}." });
        }

        project.Status = "Cancelled";
        project.UpdatedAt = DateTimeOffset.UtcNow;

        if (project.HouseDesignId != null)
        {
            var pendingRequests = await _db.ConstructorProjectRequests
                .Where(r => r.HouseDesignId == project.HouseDesignId && r.Status == "Pending")
                .ToListAsync(cancellationToken);

            foreach (var req in pendingRequests)
            {
                req.Status = "Cancelled";
                req.UpdatedAt = DateTimeOffset.UtcNow;
            }
        }

        await _db.SaveChangesAsync(cancellationToken);

        return Ok(new { projectId = project.Id, status = "Cancelled" });
    }

    private static object ProjectSummary(Project p) => new
    {
        p.Id,
        p.Status,
        p.CreatedAt,
        p.UpdatedAt,
        p.HouseDesignId,
        constructorName = p.Contractor?.FullName,
        designVersion = p.HouseDesign?.Version,
        cost = ToCostSummary(p.HouseDesign?.CostEstimates.OrderByDescending(c => c.CreatedAt).FirstOrDefault()),
        currentPhase = p.ConstructionPhases.OrderBy(x => x.SequenceOrder).FirstOrDefault(x => x.Status == "in_progress")?.PhaseName
            ?? p.ConstructionPhases.OrderBy(x => x.SequenceOrder).FirstOrDefault(x => x.Status != "completed")?.PhaseName
    };

    private static CostSummaryDto? ToCostSummary(CostEstimate? cost) =>
        cost is null ? null : CostBreakdownBuilder.ToSummary(cost, cost.HouseDesign?.TerrainType);

    private static Project NewProject(Guid workflowId, Guid designId) => new()
    {
        Id = Guid.NewGuid(),
        WorkflowStateId = workflowId,
        HouseDesignId = designId,
        Status = "awaiting_constructor",
        ConstructionPhases = new List<ConstructionPhase> {
            new() { Id=Guid.NewGuid(), PhaseName="Site Preparation", Status="pending", SequenceOrder=1 },
            new() { Id=Guid.NewGuid(), PhaseName="Foundation", Status="pending", SequenceOrder=2 },
            new() { Id=Guid.NewGuid(), PhaseName="Framing", Status="pending", SequenceOrder=3 },
            new() { Id=Guid.NewGuid(), PhaseName="Roofing", Status="pending", SequenceOrder=4 },
            new() { Id=Guid.NewGuid(), PhaseName="Interior & Finish", Status="pending", SequenceOrder=5 }
        }
    };

    private static int CountRooms(string json, string type)
    {
        try { using var doc = JsonDocument.Parse(json); return doc.RootElement.GetProperty("rooms").EnumerateArray().Count(r => r.TryGetProperty("room_type", out var t) && t.GetString()?.Contains(type, StringComparison.OrdinalIgnoreCase) == true); }
        catch { return 0; }
    }
    private static string DesignTitle(string json, int version)
    {
        try { using var doc = JsonDocument.Parse(json); if (doc.RootElement.TryGetProperty("topology", out var t)) return $"{t.GetString()?.Replace('_', ' ')} Home"; }
        catch { }
        return $"Approved Design v{version}";
    }
}

public record CreateConstructionRequest(Guid HouseDesignId, Guid ConstructorId);
public record CreateConstructionRequestFromPlan(Guid BasePreDesignedPlanId, Guid ConstructorId);
