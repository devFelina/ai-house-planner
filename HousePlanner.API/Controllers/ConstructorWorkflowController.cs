using HousePlanner.API.Entities;
using HousePlanner.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using HousePlanner.API.Data;
using Microsoft.EntityFrameworkCore;
using HousePlanner.API.DTOs;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/constructor/workflow")]
    [Authorize] // Require auth, specify roles on actions
    public class ConstructorWorkflowController : ControllerBase
    {
        private readonly IConstructorWorkflowService _workflowService;
        private readonly ICurrentUserContextService _currentUserContext;
        private readonly ApplicationDbContext _db;
        private readonly IDailyConstructionLogService _logService;
        private readonly IAIVisualizationUrlService _visualizationUrls;

        public ConstructorWorkflowController(
            IConstructorWorkflowService workflowService,
            ICurrentUserContextService currentUserContext,
            ApplicationDbContext db,
            IDailyConstructionLogService logService,
            IAIVisualizationUrlService visualizationUrls)
        {
            _workflowService = workflowService;
            _currentUserContext = currentUserContext;
            _db = db;
            _logService = logService;
            _visualizationUrls = visualizationUrls;
        }

        [HttpGet("projects")]
        [Authorize(Roles = "Constructor,Admin")]
        public async Task<IActionResult> GetProjects()
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            var projects = await _workflowService.GetConstructorProjectsAsync(user.Id.Value, user.Role);
            return Ok(projects);
        }

        [HttpGet("projects/{projectId}")]
        [Authorize(Roles = "Constructor,Admin")]
        public async Task<IActionResult> GetProjectDetails(Guid projectId)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            var project = await _workflowService.GetProjectDetailsAsync(projectId, user.Id.Value, user.Role);
            if (project == null) return NotFound("Project not found or unauthorized.");

            var design = project.HouseDesign;
            var cost = design?.CostEstimates.OrderByDescending(c => c.CreatedAt).FirstOrDefault();
            var dto = new ConstructorProjectDto(
                project.Id,
                project.WorkflowStateId,
                project.HouseDesignId,
                project.ContractorId,
                project.Status,
                project.CreatedAt,
                project.UpdatedAt,
                project.AiEstimatedTotalDurationDays,
                project.PlannedTotalDurationDays,
                project.ConstructionPhases.Select(phase => new ConstructionPhaseDto(
                    phase.Id,
                    phase.PhaseName,
                    phase.SequenceOrder,
                    phase.Status,
                    phase.StartedAt,
                    phase.CompletedAt,
                    phase.AiEstimatedDurationDays,
                    phase.PlannedDurationDays,
                    phase.PlannedStartDate,
                    phase.PlannedEndDate
                )).ToList(),
                design is null ? null : new ConstructorDesignDto(
                    design.Id,
                    design.Version,
                    design.FloorCount,
                    design.TotalBuiltUpAreaSqft,
                    design.FoundationType,
                    design.LayoutJson
                ),
                cost is null ? null : CostBreakdownBuilder.ToSummary(cost, design?.TerrainType)
            );

            return Ok(dto);
        }


        [HttpGet("projects/{projectId}/progress")]
        [Authorize(Roles = "Constructor,Admin")]
        public async Task<IActionResult> GetProjectProgress(Guid projectId)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            try
            {
                var progress = await _workflowService.GetProjectProgressAsync(projectId, user.Id.Value, user.Role);
                return Ok(progress);
            }
            catch (UnauthorizedAccessException)
            {
                return Forbid();
            }
        }

        [HttpPost("logs")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> CreateLog([FromBody] ConstructorWorkflowLog log)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            try
            {
                var createdLog = await _workflowService.CreateWorkflowLogAsync(user.Id.Value, log);
                return Ok(createdLog);
            }
            catch (UnauthorizedAccessException ex)
            {
                return StatusCode(403, ex.Message);
            }
        }

        [HttpPut("logs/{id}")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> UpdateLog(Guid id, [FromBody] ConstructorWorkflowLog updatedLog)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            try
            {
                var log = await _workflowService.UpdateWorkflowLogAsync(user.Id.Value, id, updatedLog);
                return Ok(log);
            }
            catch (KeyNotFoundException)
            {
                return NotFound("Log not found.");
            }
        }

        [HttpPut("projects/{projectId:guid}/phases/{phaseId:guid}/schedule")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> UpdatePhaseSchedule(Guid projectId, Guid phaseId, [FromBody] HousePlanner.API.DTOs.UpdatePhaseScheduleRequest request)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            if (request.PlannedDurationDays < 0) return BadRequest("Duration cannot be negative.");

            var updatedPhase = await _workflowService.UpdatePhaseScheduleAsync(projectId, phaseId, user.Id.Value, request.PlannedDurationDays);

            if (updatedPhase == null) return NotFound("Project or phase not found, or unauthorized.");

            return Ok(updatedPhase);
        }

        // --- NEW ASSIGNMENT ENDPOINTS ---

        [HttpGet("search/{projectId}")]
        [Authorize(Roles = "Constructor,Admin")]
        public async Task<IActionResult> SearchProject(Guid projectId)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();
            var allowed = user.Role == "Admin" || await _db.Projects.AnyAsync(p => p.Id == projectId &&
                (p.ContractorId == user.Id.Value || _db.ConstructorProjectRequests.Any(r => r.ProjectId == p.Id && r.ConstructorId == user.Id.Value)));
            if (!allowed) return NotFound("Project not found.");
            var project = await _workflowService.SearchProjectByIdAsync(projectId);
            if (project == null) return NotFound("Project not found.");

            return Ok(new
            {
                project.Id,
                project.Status,
                project.CreatedAt,
                HouseDesignId = project.WorkflowState?.PreferredHouseDesignId,
                DesignName = "Custom Design"
            });
        }

        [HttpPost("request/{projectId}")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> RequestProject(Guid projectId)
        {
            await Task.CompletedTask;
            return StatusCode(StatusCodes.Status410Gone, new { message = "Customers now initiate construction requests from an architect-approved design." });
        }

        [HttpPost("approve/{requestId}")]
        [Authorize(Roles = "Admin")]
        public async Task<IActionResult> ApproveRequest(Guid requestId)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            try
            {
                var request = await _workflowService.ApproveConstructorRequestAsync(requestId, user.Id.Value);
                return Ok(request);
            }
            catch (KeyNotFoundException)
            {
                return NotFound("Request not found.");
            }
        }

        [HttpGet("requests/project/{projectId}")]
        [Authorize(Roles = "Admin")]
        public async Task<IActionResult> GetProjectRequests(Guid projectId)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            var requests = await _workflowService.GetPendingRequestsForProjectAsync(projectId, user.Id.Value);
            return Ok(requests);
        }

        [HttpGet("requests/constructor")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> GetConstructorRequests()
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            // Materialize basic data from DB first to avoid EF translation errors
            var raw = await _db.ConstructorProjectRequests.AsNoTracking()
                .Where(r => r.ConstructorId == user.Id.Value && r.Status == "Pending")
                .Select(r => new
                {
                    r.Id,
                    r.ProjectId,
                    r.HouseDesignId,
                    r.Status,
                    RequestedAt = r.CreatedAt,
                    CustomerName = r.Customer != null ? r.Customer.FullName : "Unknown",
                    DesignVersion = r.HouseDesign != null ? (int?)r.HouseDesign.Version : null,
                    Area = r.HouseDesign != null ? r.HouseDesign.TotalBuiltUpAreaSqft : 0m,
                    FloorCount = r.HouseDesign != null ? r.HouseDesign.FloorCount : 0,
                    LayoutJson = r.HouseDesign != null ? r.HouseDesign.LayoutJson : null,
                    Cost = r.HouseDesign != null ? r.HouseDesign.CostEstimates.OrderByDescending(c => c.CreatedAt).FirstOrDefault() : null,
                    r.DeclineReason,
                    TerrainType = r.HouseDesign != null ? r.HouseDesign.TerrainType : null,
                    BasePreDesignedPlanCode = r.HouseDesign != null && r.HouseDesign.BasePreDesignedPlan != null ? r.HouseDesign.BasePreDesignedPlan.DesignCode : null,
                    TemplateId = r.HouseDesign != null ? r.HouseDesign.TemplateId : null,
                    BasePreDesignedPlanId = r.HouseDesign != null ? r.HouseDesign.BasePreDesignedPlanId : null
                })
                .OrderByDescending(r => r.RequestedAt)
                .ToListAsync();

            return Ok(raw.Select(r => new
            {
                id = r.Id,
                projectId = r.ProjectId,
                houseDesignId = r.HouseDesignId,
                status = r.Status,
                requestedAt = r.RequestedAt,
                customerName = r.CustomerName,
                designVersion = r.DesignVersion,
                area = r.Area,
                floorCount = r.FloorCount,
                cost = r.Cost == null ? null : CostBreakdownBuilder.ToSummary(new CostEstimate
                {
                    MaterialCostLkr = r.Cost.MaterialCostLkr,
                    LabourCostLkr = r.Cost.LabourCostLkr,
                    TotalCostLkr = r.Cost.TotalCostLkr,
                    BudgetDeltaPercent = r.Cost.BudgetDeltaPercent,
                    PricingSnapshotJson = r.Cost.PricingSnapshotJson,
                    BreakdownJson = r.Cost.BreakdownJson,
                    FormulaVersion = r.Cost.FormulaVersion,
                    AppliedAreaSqft = r.Cost.AppliedAreaSqft,
                    TerrainType = r.Cost.TerrainType,
                    CreatedAt = r.Cost.CreatedAt
                }),
                declineReason = r.DeclineReason,
                title = DesignTitle(r.LayoutJson, r.DesignVersion ?? 0),
                bedrooms = CountRooms(r.LayoutJson, "bedroom"),
                bathrooms = CountRooms(r.LayoutJson, "bathroom"),
                layoutJson = r.LayoutJson,
                terrainType = r.TerrainType,
                planReference = r.BasePreDesignedPlanCode ?? r.TemplateId,
                layoutType = !string.IsNullOrEmpty(r.LayoutJson) && r.LayoutJson.Contains("topology") ? "See JSON" : "Standard",
                basePreDesignedPlanId = r.BasePreDesignedPlanId
            }));
        }

        [HttpGet("requests/{requestId:guid}")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> GetConstructorRequest(
            Guid requestId, CancellationToken cancellationToken = default)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            var rawReq = await _db.ConstructorProjectRequests.AsNoTracking()
                .Where(req => req.Id == requestId && req.ConstructorId == user.Id.Value)
                .Include(req => req.Customer)
                .Include(req => req.HouseDesign).ThenInclude(design => design!.CostEstimates)
                .Include(req => req.HouseDesign).ThenInclude(design => design!.BasePreDesignedPlan)
                .FirstOrDefaultAsync();

            if (rawReq == null) return NotFound();

            var design = rawReq.HouseDesign;
            var cost = design?.CostEstimates.OrderByDescending(c => c.CreatedAt).FirstOrDefault();
            var aiVisualizationUrl = design?.AIVisualizationStatus == "completed"
                ? await _visualizationUrls.GetReadUrlAsync(
                    design.AIVisualizationImage, cancellationToken)
                : null;

            return Ok(new
            {
                id = rawReq.Id,
                projectId = rawReq.ProjectId,
                houseDesignId = rawReq.HouseDesignId,
                status = rawReq.Status,
                requestedAt = rawReq.CreatedAt,
                customerName = rawReq.Customer?.FullName ?? "Unknown",
                designVersion = design?.Version,
                area = design?.TotalBuiltUpAreaSqft ?? 0m,
                floorCount = design?.FloorCount ?? 0,
                cost = cost == null ? null : CostBreakdownBuilder.ToSummary(new CostEstimate
                {
                    MaterialCostLkr = cost.MaterialCostLkr,
                    LabourCostLkr = cost.LabourCostLkr,
                    TotalCostLkr = cost.TotalCostLkr,
                    BudgetDeltaPercent = cost.BudgetDeltaPercent,
                    PricingSnapshotJson = cost.PricingSnapshotJson,
                    BreakdownJson = cost.BreakdownJson,
                    FormulaVersion = cost.FormulaVersion,
                    AppliedAreaSqft = cost.AppliedAreaSqft,
                    TerrainType = cost.TerrainType,
                    CreatedAt = cost.CreatedAt
                }),
                declineReason = rawReq.DeclineReason,
                title = DesignTitle(design?.LayoutJson, design?.Version ?? 0),
                bedrooms = CountRooms(design?.LayoutJson, "bedroom"),
                bathrooms = CountRooms(design?.LayoutJson, "bathroom"),
                aiVisualizationUrl,
                aiVisualizationStatus = design?.AIVisualizationStatus,
                terrainType = design?.TerrainType,
                planReference = design?.BasePreDesignedPlan?.DesignCode ?? design?.TemplateId,
                layoutType = !string.IsNullOrEmpty(design?.LayoutJson) && design.LayoutJson.Contains("topology") ? "See JSON" : "Standard",
                layoutJson = design?.LayoutJson,
                basePreDesignedPlanId = design?.BasePreDesignedPlanId
            });
        }

        private static int CountRooms(string? json, string type)
        {
            if (string.IsNullOrEmpty(json)) return 0;
            try { using var doc = System.Text.Json.JsonDocument.Parse(json); return doc.RootElement.GetProperty("rooms").EnumerateArray().Count(r => r.TryGetProperty("room_type", out var t) && t.GetString()?.Contains(type, StringComparison.OrdinalIgnoreCase) == true); }
            catch { return 0; }
        }
        private static string DesignTitle(string? json, int version)
        {
            if (!string.IsNullOrEmpty(json))
            {
                try { using var doc = System.Text.Json.JsonDocument.Parse(json); if (doc.RootElement.TryGetProperty("topology", out var t)) return $"{t.GetString()?.Replace('_', ' ')} Home"; }
                catch { }
            }
            return $"Approved Design v{version}";
        }

        [HttpPost("requests/{requestId:guid}/accept")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> AcceptRequest(Guid requestId)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();
            var request = await _db.ConstructorProjectRequests.Include(r => r.Project).ThenInclude(p => p!.WorkflowState)
                .FirstOrDefaultAsync(r => r.Id == requestId && r.ConstructorId == user.Id.Value);
            if (request == null) return NotFound();
            if (request.Status != "Pending") return Conflict(new { message = "Only pending requests can be accepted." });
            var approved = await _db.ValidationRequests.Include(v => v.WorkflowState).AnyAsync(v => (v.HouseDesignId == request.HouseDesignId || v.WorkflowState.PreferredHouseDesignId == request.HouseDesignId) && v.ClientId == request.CustomerId && v.Status == "Approved");
            if (!approved) return Conflict(new { message = "The design is no longer approved for construction." });
            if (request.Project == null) return Conflict(new { message = "Construction project is unavailable." });
            if (request.Project.ContractorId != null) return Conflict(new { message = "This project already has an assigned constructor." });
            request.Status = "Accepted"; request.RespondedAt = DateTimeOffset.UtcNow; request.UpdatedAt = request.RespondedAt.Value;
            request.Project.ContractorId = user.Id.Value; request.Project.HouseDesignId = request.HouseDesignId;
            request.Project.Status = "active"; request.Project.UpdatedAt = DateTimeOffset.UtcNow;

            // Initialize ConstructionPhases from AI plan
            if (request.Project.WorkflowState != null && !string.IsNullOrEmpty(request.Project.WorkflowState.ConstructionPlan))
            {
                try
                {
                    using var doc = System.Text.Json.JsonDocument.Parse(request.Project.WorkflowState.ConstructionPlan);
                    var root = doc.RootElement;

                    if (root.TryGetProperty("project_summary", out var summary) && summary.TryGetProperty("estimated_duration_days", out var estTotal))
                    {
                        request.Project.AiEstimatedTotalDurationDays = estTotal.GetInt32();
                        request.Project.PlannedTotalDurationDays = estTotal.GetInt32();
                    }

                    if (root.TryGetProperty("phases", out var phasesList))
                    {
                        var existingPhases = await _db.ConstructionPhases.Where(cp => cp.ProjectId == request.Project.Id).ToListAsync();
                        if (existingPhases.Any())
                        {
                            _db.ConstructionPhases.RemoveRange(existingPhases);
                        }

                        var currentDate = DateOnly.FromDateTime(DateTime.UtcNow);
                        int order = 1;

                        foreach (var phaseEl in phasesList.EnumerateArray())
                        {
                            string phaseName = phaseEl.TryGetProperty("name", out var nameEl) ? nameEl.GetString() ?? "Unknown Phase" : "Unknown Phase";
                            int duration = phaseEl.TryGetProperty("duration_days", out var durEl) ? durEl.GetInt32() : 7;
                            int seq = phaseEl.TryGetProperty("id", out var idEl) ? idEl.GetInt32() : order;

                            var cp = new HousePlanner.API.Entities.ConstructionPhase
                            {
                                Id = Guid.NewGuid(),
                                ProjectId = request.Project.Id,
                                PhaseName = phaseName,
                                SequenceOrder = seq,
                                Status = "pending",
                                AiEstimatedDurationDays = duration,
                                PlannedDurationDays = duration,
                                PlannedStartDate = currentDate,
                                PlannedEndDate = currentDate.AddDays(Math.Max(0, duration - 1))
                            };

                            request.Project.ConstructionPhases.Add(cp);
                            _db.ConstructionPhases.Add(cp);
                            currentDate = currentDate.AddDays(Math.Max(1, duration));
                            order++;
                        }
                    }
                }
                catch (Exception)
                {
                    // Ignore parsing errors, fallback
                }
            }

            var competing = await _db.ConstructorProjectRequests.Where(r => r.ProjectId == request.ProjectId && r.Id != request.Id && r.Status == "Pending").ToListAsync();
            foreach (var other in competing) { other.Status = "Cancelled"; other.UpdatedAt = DateTimeOffset.UtcNow; }
            try
            {
                await _db.SaveChangesAsync();
            }
            catch (Microsoft.EntityFrameworkCore.DbUpdateConcurrencyException ex)
            {
                var entry = ex.Entries.FirstOrDefault();
                throw new Exception($"Failed on {entry?.Entity.GetType().Name}. State: {entry?.State}", ex);
            }
            return Ok(new { request.Id, request.Status, request.ProjectId });
        }

        [HttpPost("requests/{requestId:guid}/decline")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> DeclineRequest(Guid requestId, [FromBody] DeclineConstructionRequest? dto)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();
            var request = await _db.ConstructorProjectRequests.FirstOrDefaultAsync(r => r.Id == requestId && r.ConstructorId == user.Id.Value);
            if (request == null) return NotFound();
            if (request.Status != "Pending") return Conflict(new { message = "Only pending requests can be declined." });
            request.Status = "Declined"; request.DeclineReason = string.IsNullOrWhiteSpace(dto?.Reason) ? null : dto.Reason.Trim();
            request.RespondedAt = DateTimeOffset.UtcNow; request.UpdatedAt = request.RespondedAt.Value;
            await _db.SaveChangesAsync();
            return Ok(new { request.Id, request.Status, request.DeclineReason });
        }

        [HttpPatch("projects/{projectId}/phases/{phaseId}/status")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> UpdatePhaseStatus(Guid projectId, Guid phaseId, [FromBody] PhaseStatusUpdateDto dto)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            if (string.IsNullOrWhiteSpace(dto.Status)) return BadRequest(new { message = "Status is required." });

            try
            {
                var result = await _workflowService.UpdatePhaseStatusAsync(projectId, phaseId, user.Id.Value, dto.Status);
                if (result == null) return NotFound(new { message = "Project or phase not found." });
                return Ok(result);
            }
            catch (HousePlanner.API.Exceptions.ProjectCancelledException ex)
            {
                return Conflict(new { message = ex.Message });
            }
            catch (InvalidOperationException ex)
            {
                return Conflict(new { message = ex.Message });
            }
            catch (ArgumentException ex)
            {
                return BadRequest(new { message = ex.Message });
            }
        }

        [HttpPost("projects/{projectId}/duration")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> SetEstimatedDuration(Guid projectId, [FromBody] int estimatedDays)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            var success = await _workflowService.SetProjectEstimatedDurationAsync(projectId, user.Id.Value, estimatedDays);
            if (!success) return BadRequest("Failed to set estimated duration.");

            return Ok(new { success = true });
        }
        [HttpGet("projects/{projectId:guid}/calendar")]
        [Authorize(Roles = "Constructor")]
        public async Task<IActionResult> GetProjectCalendar(Guid projectId, CancellationToken cancellationToken)
        {
            var user = await _currentUserContext.GetAsync(HttpContext);
            if (user?.Id == null) return Unauthorized();

            try
            {
                var events = await _logService.GetProjectCalendarAsync(projectId, user.Id.Value, cancellationToken);
                return Ok(events);
            }
            catch (UnauthorizedAccessException)
            {
                // Follow the convention where a project not owned returns 404
                // as not to leak the existence of a project ID to an unauthorized constructor.
                return NotFound();
            }
        }
    }

    public record DeclineConstructionRequest(string? Reason);
    public record PhaseStatusUpdateDto(string Status);
}
