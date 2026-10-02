using System.Text;
using System.Text.Json;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;
using HousePlanner.API.Models;
using HousePlanner.API.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/ai-generation")]
public class AiGenerationController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly HttpClient _agenticServiceClient;
    private readonly IDesignOptionsService _designOptionsService;
    private readonly ICurrentUserContextService _currentUser;

    public AiGenerationController(ApplicationDbContext context, IHttpClientFactory httpClientFactory,
        IDesignOptionsService designOptionsService, ICurrentUserContextService currentUser)
    {
        _context = context;
        _agenticServiceClient = httpClientFactory.CreateClient("AgenticService");
        _designOptionsService = designOptionsService;
        _currentUser = currentUser;
    }

    [HttpPost("generate")]
    public async Task<IActionResult> Generate([FromBody] StartDesignRequest request, CancellationToken cancellationToken)
    {
        Console.WriteLine($"[TRACE] received bathroom count: {request.Bathrooms}");
        var requirement = request.ToRequirement();
        var validation = await _designOptionsService.ValidateFinalSelectionAsync(requirement, cancellationToken);
        if (!validation.IsValid)
            return BadRequest(new { code = validation.ErrorCode, message = validation.Message,
                conflicts = validation.Conflicts, suggestions = validation.Suggestions });

        WorkflowState workflow;
        try
        {
            var identity = await _currentUser.GetAsync(HttpContext);
            if (identity is null) return Unauthorized(new { Message = "Authentication required. Application profile not found." });
            var client = await _context.Users.FindAsync(identity.Id);
            if (client is null) return Unauthorized(new { Message = "Authentication required. Application profile not found." });

            var activeStatuses = new[] { "running", "processing" };
            var activeWorkflow = await _context.WorkflowStates
                .AsNoTracking()
                .Where(w => w.LandSubmission.ClientId == client.Id
                    && activeStatuses.Contains(w.Status.ToLower())
                    && w.LandSubmission.LandSizeCategory == requirement.LandSizeCategory
                    && w.LandSubmission.LandSizePerches == requirement.LandSizePerches
                    && w.LandSubmission.PreferredBedrooms == requirement.Bedrooms
                    && w.LandSubmission.PreferredBathrooms == requirement.Bathrooms
                    && w.LandSubmission.PreferredFloors == requirement.Floors
                    && w.LandSubmission.StylePreference == requirement.HouseType)
                .OrderByDescending(w => w.CreatedAt)
                .FirstOrDefaultAsync(cancellationToken);
            if (activeWorkflow is not null)
            {
                Console.WriteLine($"[Workflow Guard] Duplicate generation ignored for workflow {activeWorkflow.Id}");
                return Ok(new
                {
                    Message = "Workflow already running",
                    WorkflowId = activeWorkflow.Id,
                    Reused = true
                });
            }

            var submission = new LandSubmission
            {
                Id = Guid.NewGuid(), ClientId = client.Id, BudgetLkr = 0,
                LandSizePerches = requirement.LandSizePerches, ManualTerrainType = "flat",
                PreferredBedrooms = requirement.Bedrooms, PreferredBathrooms = requirement.Bathrooms,
                PreferredFloors = requirement.Floors, LandSizeCategory = requirement.LandSizeCategory,
                StylePreference = requirement.HouseType, CreatedAt = DateTimeOffset.UtcNow,
                UpdatedAt = DateTimeOffset.UtcNow
            };
            Console.WriteLine($"[TRACE] saved bathroom count: {submission.PreferredBathrooms}");
            workflow = new WorkflowState
            {
                Id = Guid.NewGuid(), LandSubmissionId = submission.Id, Status = "running",
                ApprovalStatus = "not_requested", CreatedAt = DateTimeOffset.UtcNow,
                UpdatedAt = DateTimeOffset.UtcNow
            };
            _context.LandSubmissions.Add(submission);
            _context.WorkflowStates.Add(workflow);
            await _context.SaveChangesAsync(cancellationToken);
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { Message = "Database error while saving the submission.", Details = ex.InnerException?.Message ?? ex.Message });
        }

        var payload = new
        {
            workflow_id = workflow.Id,
            submission_id = workflow.LandSubmissionId,
            land_size_category = requirement.LandSizeCategory,
            land_size_perches = requirement.LandSizePerches,
            bedrooms = requirement.Bedrooms,
            bathrooms = requirement.Bathrooms,
            house_type = requirement.HouseType,
            target_duration_days = requirement.TargetDurationDays
        };
        var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        try
        {
            var response = await _agenticServiceClient.PostAsync("/workflows/start", content, cancellationToken);
            if (!response.IsSuccessStatusCode)
                return BadRequest(new { Message = $"Agentic service returned an error: {response.StatusCode}" });
        }
        catch (HttpRequestException ex)
        {
            return BadRequest(new { Message = "Cannot connect to the AI Agentic Service. Please make sure it is running on port 8001.", Details = ex.Message });
        }

        return Ok(new { Message = "Workflow started successfully", WorkflowId = workflow.Id });
    }
}
