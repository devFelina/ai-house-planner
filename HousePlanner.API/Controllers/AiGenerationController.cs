using Microsoft.AspNetCore.Mvc;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;
using System.Text;
using System.Text.Json;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class AiGenerationController : ControllerBase
    {
        private readonly ApplicationDbContext _context;
        private readonly HttpClient _agenticServiceClient;

        public AiGenerationController(ApplicationDbContext context, IHttpClientFactory httpClientFactory)
        {
            _context = context;
            _agenticServiceClient = httpClientFactory.CreateClient("AgenticService");
        }

        [HttpPost("generate")]
        public async Task<IActionResult> Generate([FromBody] AiGenerationRequest request)
        {
            WorkflowState workflowState;
            object payload;
            try 
            {
                var client = _context.Users.FirstOrDefault() ?? new User { Id = Guid.NewGuid(), Email = "test@example.com", FullName = "Test User", RoleId = 1, PasswordHash = "dummyhash" };
                if (_context.Users.FirstOrDefault() == null) {
                    _context.Users.Add(client);
                    await _context.SaveChangesAsync();
                }

                var submission = new LandSubmission
                {
                    Id = Guid.NewGuid(),
                    ClientId = client.Id,
                    BudgetLkr = request.BudgetLkr,
                    LandSizePerches = request.LandSizePerches,
                    ManualTerrainType = request.ManualTerrainType,
                    PreferredBedrooms = request.Preferences?.Bedrooms ?? 3,
                    PreferredFloors = request.Preferences?.Floors ?? 1,
                    StylePreference = request.Preferences?.ArchitecturalStyle ?? "Modern Minimalist",
                    CreatedAt = DateTimeOffset.UtcNow,
                    UpdatedAt = DateTimeOffset.UtcNow
                };

                _context.LandSubmissions.Add(submission);
                
                workflowState = new WorkflowState
                {
                    Id = Guid.NewGuid(),
                    LandSubmissionId = submission.Id,
                    Status = "running",
                    ApprovalStatus = "not_requested",
                    CreatedAt = DateTimeOffset.UtcNow,
                    UpdatedAt = DateTimeOffset.UtcNow
                };
                
                _context.WorkflowStates.Add(workflowState);
                await _context.SaveChangesAsync();

                payload = new {
                    workflow_id = workflowState.Id,
                    submission_id = submission.Id,
                    budget_lkr = request.BudgetLkr,
                    land_size_perches = request.LandSizePerches,
                    manual_terrain_type = request.ManualTerrainType,
                    preferences = request.Preferences,
                    plot_constraints = request.PlotConstraints,
                    design_seed = request.DesignSeed
                };
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { Message = "Database error while saving the submission.", Details = ex.InnerException?.Message ?? ex.Message });
            }

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            _agenticServiceClient.DefaultRequestHeaders.Clear();
            _agenticServiceClient.DefaultRequestHeaders.Add("X-Internal-API-Key", "shared-internal-secret");

            try
            {
                var response = await _agenticServiceClient.PostAsync("http://localhost:8001/workflows/start", content);
                if (!response.IsSuccessStatusCode)
                {
                    // If the Python API returns a 4xx or 5xx, we handle it gracefully instead of a raw 500
                    return BadRequest(new { Message = $"Agentic service returned an error: {response.StatusCode}" });
                }
            }
            catch (HttpRequestException ex)
            {
                // This means the Python backend is NOT running or is unreachable
                return BadRequest(new { Message = "Cannot connect to the AI Agentic Service. Please make sure it is running on port 8001.", Details = ex.Message });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { Message = "An unexpected error occurred while calling the AI service.", Details = ex.Message });
            }

            return Ok(new { Message = "Workflow started successfully", WorkflowId = workflowState.Id });
        }
    }

    public class AiGenerationRequest
    {
        public decimal BudgetLkr { get; set; }
        public decimal LandSizePerches { get; set; }
        public string? ManualTerrainType { get; set; }
        public PreferencesDto? Preferences { get; set; }
        public PlotConstraintsDto? PlotConstraints { get; set; }
        public long? DesignSeed { get; set; }
    }

    public class PreferencesDto
    {
        public int Bedrooms { get; set; }
        public int Floors { get; set; }
        public string? ArchitecturalStyle { get; set; }
        public string? LandUnit { get; set; }
    }

    public class PlotConstraintsDto
    {
        public string? road_side { get; set; }
        public decimal? plot_width_ft { get; set; }
        public decimal? plot_length_ft { get; set; }
    }
}
