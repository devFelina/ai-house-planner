using System.Text.Json;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/internal/workflows")]
public class InternalWorkflowController : ControllerBase
{
    private static readonly HashSet<string> ToolAuditActions = new(StringComparer.Ordinal)
    {
        "tool_call_succeeded",
        "tool_call_failed",
        "tool_authorization_denied"
    };
    private const int MaxToolAuditEntries = 100;
    private const int MaxToolAuditPayloadCharacters = 256_000;
    public sealed record VisualizationUpdateRequest(string? ImageUrl, string Status = "completed");
    private readonly ApplicationDbContext _context;
    private readonly ILogger<InternalWorkflowController> _logger;

    public InternalWorkflowController(ApplicationDbContext context, ILogger<InternalWorkflowController> logger)
    {
        _context = context;
        _logger = logger;
    }

    private async Task<WorkflowState?> FindWorkflowState(Guid id)
    {
        return await _context.WorkflowStates
            .Include(w => w.HouseDesigns)
                .ThenInclude(d => d.CostEstimates)
            .FirstOrDefaultAsync(w => w.Id == id);
    }

    [HttpGet("{id:guid}/visualization")]
    public async Task<IActionResult> GetCurrentVisualization(Guid id)
    {
        var design = await _context.HouseDesigns.AsNoTracking()
            .Where(d => d.WorkflowStateId == id && d.IsCurrent && !d.IsArchived)
            .OrderByDescending(d => d.Version)
            .Select(d => new { designId = d.Id, imageUrl = d.AIVisualizationImage, status = d.AIVisualizationStatus })
            .FirstOrDefaultAsync();

        return design is null ? NotFound() : Ok(design);
    }

    [HttpPatch("{id:guid}/visualization")]
    public async Task<IActionResult> SaveCurrentVisualization(Guid id, [FromBody] VisualizationUpdateRequest request)
    {
        var status = request.Status.Trim().ToLowerInvariant();
        if (status is not ("generating" or "completed" or "failed"))
            return BadRequest(new { message = "Visualization status must be generating, completed, or failed." });
        if (status == "completed" && string.IsNullOrWhiteSpace(request.ImageUrl))
            return BadRequest(new { message = "A completed visualization requires an image URL." });

        var design = await _context.HouseDesigns
            .Where(d => d.WorkflowStateId == id && d.IsCurrent && !d.IsArchived)
            .OrderByDescending(d => d.Version)
            .FirstOrDefaultAsync();

        if (design is null) return NotFound();
        if (status == "completed" && string.IsNullOrWhiteSpace(design.AIVisualizationImage))
        {
            design.AIVisualizationImage = request.ImageUrl;
        }
        design.AIVisualizationStatus = string.IsNullOrWhiteSpace(design.AIVisualizationImage)
            ? status
            : "completed";
        await _context.SaveChangesAsync();

        return Ok(new { designId = design.Id, imageUrl = design.AIVisualizationImage, status = design.AIVisualizationStatus });
    }

    /// <summary>
    /// Internal endpoint for the Design Agent to save generated/revised layouts.
    /// </summary>
    [HttpPost("{id:guid}/design")]
    public async Task<IActionResult> SaveDesign(Guid id, [FromBody] JsonElement layoutData)
    {
        try
        {
            var workflow = await FindWorkflowState(id);
            if (workflow is null)
            {
                _logger.LogWarning("Workflow {WorkflowId} not found when saving design.", id);
                return NotFound(new { message = $"Workflow {id} not found." });
            }

            int floorCount = layoutData.GetProperty("floor_count").GetInt32();
            decimal totalArea = layoutData.TryGetProperty("total_built_up_area_sqft", out var areaProp)
                ? areaProp.GetDecimal()
                : 0m;

            string foundationType = layoutData.TryGetProperty("foundation_type", out var foundProp)
                ? foundProp.GetString() ?? "unknown"
                : "unknown";

            string templateId = layoutData.TryGetProperty("template_id", out var tmplProp) && tmplProp.ValueKind != JsonValueKind.Null
                ? tmplProp.GetString() ?? "CUSTOM"
                : "CUSTOM";

            string terrainType = layoutData.TryGetProperty("terrain_type", out var terrProp) && terrProp.ValueKind != JsonValueKind.Null
                ? terrProp.GetString() ?? "flat"
                : "flat";

            // Mark all existing designs for this workflow as not current
            foreach (var existing in workflow.HouseDesigns.Where(d => d.IsCurrent))
            {
                existing.IsCurrent = false;
            }

            var basePlanId = await _context.LandSubmissions.Where(s => s.Id == workflow.LandSubmissionId)
                .Select(s => s.BasePreDesignedPlanId).FirstOrDefaultAsync();
            var newDesign = new HouseDesign
            {
                WorkflowStateId = id,
                Version = (workflow.HouseDesigns.Count == 0 ? 0 : workflow.HouseDesigns.Max(d => d.Version)) + 1,
                FloorCount = floorCount,
                TotalBuiltUpAreaSqft = totalArea,
                FoundationType = foundationType,
                TemplateId = templateId,
                TerrainType = terrainType,
                IsCurrent = true, // New design is always current
                LayoutJson = layoutData.GetRawText(),
                TechnicalPlanImage = layoutData.TryGetProperty("technical_plan_image", out var techProp) ? techProp.GetString() : null,
                AIVisualizationImage = layoutData.TryGetProperty("ai_visualization", out var aiProp) && aiProp.ValueKind != JsonValueKind.Null ? aiProp.GetProperty("image_url").GetString() : null,
                AIVisualizationStatus = "generating",
                DesignSource = basePlanId is null ? "AI_GENERATED" : "adapted_pre_designed",
                BasePreDesignedPlanId = basePlanId,
                CreatedAt = DateTimeOffset.UtcNow,
                Rooms = new List<Room>()
            };

            // Parse rooms into the relational DB format for querying/validation
            if (layoutData.TryGetProperty("rooms", out var roomsElement) && roomsElement.ValueKind == JsonValueKind.Array)
            {
                foreach (var roomEl in roomsElement.EnumerateArray())
                {
                    var roomType = roomEl.GetProperty("room_type").GetString() ?? "unknown";
                    var width = roomEl.GetProperty("width").GetDecimal();
                    var length = roomEl.GetProperty("length").GetDecimal();

                    var room = new Room
                    {
                        RoomType = roomType,
                        Name = roomEl.TryGetProperty("name", out var nameProp) ? nameProp.GetString() : null,
                        FloorNumber = roomEl.GetProperty("floor").GetInt32(),
                        X = roomEl.GetProperty("x").GetDecimal(),
                        Y = roomEl.GetProperty("y").GetDecimal(),
                        Width = width,
                        Length = length,
                        AreaSqft = Math.Round(width * length, 2),
                        WallHeight = roomEl.TryGetProperty("wall_height", out var wh) ? wh.GetDecimal() : 9.0m
                    };
                    newDesign.Rooms.Add(room);
                }
            }

            _context.HouseDesigns.Add(newDesign);

            // Update workflow status and terrain
            workflow.Status = "design_generated";
            workflow.FailureReason = null;
            if (terrainType != null)
                workflow.TerrainType ??= terrainType;
            workflow.UpdatedAt = DateTimeOffset.UtcNow;

            await _context.SaveChangesAsync();

            _logger.LogInformation("Successfully saved design revision v{Version} for workflow {WorkflowId}", newDesign.Version, id);
            return Ok(new { message = "Design saved successfully.", designId = newDesign.Id, version = newDesign.Version });
        }
        catch (KeyNotFoundException ex)
        {
            return BadRequest(new { message = "Missing required fields in layout JSON.", error = ex.Message });
        }
        catch (Exception ex)
        {
            Console.WriteLine(ex.ToString());
            _logger.LogError(ex, "Error saving design for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred saving the design." });
        }
    }

    /// <summary>
    /// Internal endpoint for the Validation Agent to update validation status.
    /// </summary>
    [HttpPatch("{id:guid}/validation")]
    public async Task<IActionResult> UpdateValidationStatus(Guid id, [FromBody] JsonElement validationData)
    {
        try
        {
            var workflow = await FindWorkflowState(id);
            if (workflow is null) return NotFound(new { message = $"Unknown workflow {id}." });

            bool passed = validationData.TryGetProperty("passed", out var pProp) && pProp.GetBoolean();
            if (passed)
            {
                workflow.Status = "awaiting_approval";
                workflow.ApprovalStatus = "pending";
                workflow.FailureReason = null;
            }
            else
            {
                string? reason = validationData.TryGetProperty("summary", out var sProp) ? sProp.GetString() :
                                 validationData.TryGetProperty("revision_reason", out var rProp) ? rProp.GetString() : "Validation failed";
                workflow.FailureReason = reason?[..Math.Min(reason.Length, 1000)];
            }

            workflow.UpdatedAt = DateTimeOffset.UtcNow;
            await _context.SaveChangesAsync();

            _logger.LogInformation("Validation status updated for workflow {WorkflowId}: passed={Passed}, status={Status}", id, passed, workflow.Status);
            return Ok(new { message = "Validation status updated.", status = workflow.Status, approvalStatus = workflow.ApprovalStatus });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating validation status for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred updating validation status." });
        }
    }

    [HttpPatch("{id:guid}/status")]
    public async Task<IActionResult> UpdateGenerationStatus(Guid id, [FromBody] JsonElement data)
    {
        if (!data.TryGetProperty("status", out var status) || status.GetString() != "failed")
            return BadRequest(new { message = "This endpoint accepts only generation failure." });
        var workflow = await FindWorkflowState(id);
        if (workflow is null) return NotFound(new { message = $"Unknown workflow {id}." });
        workflow.Status = "failed";
        workflow.ApprovalStatus = "not_requested";
        var reasonText = data.TryGetProperty("reason", out var reason)
            ? reason.GetString() ?? "Design generation failed."
            : "Design generation failed without a detailed reason.";
        workflow.FailureReason = reasonText[..Math.Min(reasonText.Length, 1000)];
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();
        return Ok(new { status = workflow.Status });
    }

    /// <summary>
    /// Internal endpoint for the Python agent pipeline to persist the agent execution timeline.
    /// Accepts a JSON array of { agent, status, message } entries and stores them as jsonb.
    /// </summary>
    [HttpPatch("{id:guid}/execution-log")]
    public async Task<IActionResult> UpdateExecutionLog(Guid id, [FromBody] JsonElement logData)
    {
        if (logData.ValueKind != JsonValueKind.Array)
            return BadRequest(new { message = "Body must be a JSON array of log entries." });

        var workflow = await FindWorkflowState(id);
        if (workflow is null)
            return NotFound(new { message = $"Unknown workflow {id}." });

        workflow.AgentExecutionLogJson = logData.GetRawText();
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();

        _logger.LogInformation("Execution log saved for workflow {WorkflowId} ({Count} entries)",
            id, logData.GetArrayLength());
        return Ok(new { message = "Execution log saved.", count = logData.GetArrayLength() });
    }

    /// <summary>Persist the complete sanitized governed-tool audit trail.</summary>
    [HttpPatch("{id:guid}/tool-audit-log")]
    public async Task<IActionResult> UpdateToolAuditLog(Guid id, [FromBody] ToolAuditLogRequest? request)
    {
        if (request?.Entries is null || request.Entries.Count == 0 || request.Entries.Count > MaxToolAuditEntries)
            return BadRequest(new { message = $"Entries must contain between 1 and {MaxToolAuditEntries} items." });

        foreach (var entry in request.Entries)
        {
            if (string.IsNullOrWhiteSpace(entry.AgentName)
                || string.IsNullOrWhiteSpace(entry.Action)
                || string.IsNullOrWhiteSpace(entry.ToolCalled)
                || string.IsNullOrWhiteSpace(entry.Result)
                || string.IsNullOrWhiteSpace(entry.CreatedAtUtc)
                || !ToolAuditActions.Contains(entry.Action)
                || entry.DurationMs < 0
                || !DateTimeOffset.TryParse(entry.CreatedAtUtc, out _))
            {
                return BadRequest(new { message = "One or more tool audit entries are invalid." });
            }
        }

        var json = JsonSerializer.Serialize(request, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });
        if (json.Length > MaxToolAuditPayloadCharacters)
            return BadRequest(new { message = "Tool audit payload is too large." });

        var workflow = await FindWorkflowState(id);
        if (workflow is null)
            return NotFound(new { message = $"Unknown workflow {id}." });

        workflow.ToolAuditLogJson = json;
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();

        _logger.LogInformation(
            "Tool audit log saved for workflow {WorkflowId} ({Count} entries)",
            id,
            request.Entries.Count);
        return Ok(new { message = "Tool audit log saved.", count = request.Entries.Count });
    }

    /// <summary>
    /// Internal endpoint to persist workflow orchestrator plan state.
    /// </summary>
    [HttpPatch("{id:guid}/plan")]
    public async Task<IActionResult> UpdatePlan(Guid id, [FromBody] WorkflowPlanStateRequest request)
    {
        try
        {
            var workflow = await FindWorkflowState(id);
            if (workflow is null) return NotFound(new { message = $"Unknown workflow {id}." });

            workflow.PlanJson = JsonSerializer.Serialize(request);
            workflow.UpdatedAt = DateTimeOffset.UtcNow;

            await _context.SaveChangesAsync();

            _logger.LogInformation("Workflow plan saved for workflow {WorkflowId}", id);
            return Ok(new { message = "Workflow plan saved." });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error saving plan for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred saving the plan." });
        }
    }


    /// <summary>
    /// Internal endpoint for the Land Analysis Agent to update terrain results.
    /// </summary>
    [HttpPatch("{id:guid}/terrain")]
    public async Task<IActionResult> UpdateTerrain(Guid id, [FromBody] JsonElement terrainData)
    {
        try
        {
            var workflow = await FindWorkflowState(id);
            if (workflow is null) return NotFound(new { message = $"Unknown workflow {id}." });

            if (terrainData.TryGetProperty("terrain_type", out var terrainProp))
                workflow.TerrainType = terrainProp.GetString();

            if (terrainData.TryGetProperty("slope_estimate", out var slopeProp))
                workflow.SlopeEstimate = slopeProp.GetString();

            if (terrainData.TryGetProperty("notable_features", out var featuresProp))
                workflow.NotableFeatures = featuresProp.GetRawText();

            workflow.UpdatedAt = DateTimeOffset.UtcNow;

            await _context.SaveChangesAsync();

            _logger.LogInformation("Terrain updated for workflow {WorkflowId}: {TerrainType}", id, workflow.TerrainType);
            return Ok(new { message = "Terrain updated.", terrainType = workflow.TerrainType });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating terrain for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred updating terrain." });
        }
    }

    /// <summary>
    /// Internal endpoint for the Construction Planning Agent to update construction plan results.
    /// </summary>
    [HttpPatch("{id:guid}/construction-plan")]
    public async Task<IActionResult> UpdateConstructionPlan(Guid id, [FromBody] JsonElement planData)
    {
        try
        {
            var workflow = await FindWorkflowState(id);
            if (workflow is null) return NotFound(new { message = $"Unknown workflow {id}." });

            workflow.ConstructionPlan = planData.GetRawText();
            workflow.UpdatedAt = DateTimeOffset.UtcNow;

            await _context.SaveChangesAsync();

            _logger.LogInformation("Construction plan updated for workflow {WorkflowId}", id);
            return Ok(new { message = "Construction plan updated." });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating construction plan for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred updating the construction plan." });
        }
    }

    /// <summary>
    /// Persists the Cost Estimation Agent result for the current design.
    /// The first successful estimate is locked to the design so later pricing
    /// changes cannot silently rewrite an estimate already under review.
    /// </summary>
    [HttpPost("{id:guid}/cost-estimate")]
    public async Task<IActionResult> SaveCostEstimate(Guid id, [FromBody] SaveCostEstimateRequestDto request)
    {
        try
        {
            if (request is null)
                return BadRequest(new { message = "Request body cannot be null." });

            if (request.MaterialCostLkr < 0 || request.LabourCostLkr < 0 ||
                request.TotalCostLkr < 0 || request.BudgetDeltaPercent is < 0)
                return BadRequest(new { message = "Cost values and budget delta cannot be negative." });

            if (request.PricingSnapshot.ValueKind != JsonValueKind.Array ||
                request.PricingSnapshot.GetArrayLength() == 0)
                return BadRequest(new { message = "A non-empty pricing snapshot is required." });

            if (request.Breakdown.ValueKind != JsonValueKind.Array || request.Breakdown.GetArrayLength() == 0)
                return BadRequest(new { message = "A non-empty calculated cost breakdown is required." });
            if (request.AppliedAreaSqft <= 0)
                return BadRequest(new { message = "Applied area must be greater than zero." });
            if (string.IsNullOrWhiteSpace(request.FormulaVersion) || request.FormulaVersion.Length > 50)
                return BadRequest(new { message = "A valid formula version is required." });
            var terrain = request.TerrainType.Trim().ToLowerInvariant();
            if (terrain is not ("flat" or "hillside" or "coastal"))
                return BadRequest(new { message = "Terrain type must be flat, hillside, or coastal." });

            var pricingSnapshotJson = request.PricingSnapshot.GetRawText();
            var breakdownJson = request.Breakdown.GetRawText();

            const decimal tolerance = 0.05m;
            if (Math.Abs(request.TotalCostLkr - (request.MaterialCostLkr + request.LabourCostLkr)) > tolerance)
                return BadRequest(new { message = "Total cost must equal material cost plus labour cost." });

            var workflow = await FindWorkflowState(id);
            if (workflow is null)
                return NotFound(new { message = $"Unknown workflow {id}; cost estimate was not persisted." });

            var currentDesign = workflow.HouseDesigns.FirstOrDefault(d => d.IsCurrent && !d.IsArchived);
            if (currentDesign is null)
                return Conflict(new { message = "No current house design exists for this workflow." });

            var existingEstimate = currentDesign.CostEstimates
                .OrderByDescending(c => c.CreatedAt)
                .FirstOrDefault();

            CostEstimate estimate;
            if (existingEstimate is not null)
            {
                return Ok(ToResponse(existingEstimate, currentDesign.Id, true));
            }
            else
            {
                estimate = new CostEstimate
                {
                    HouseDesignId = currentDesign.Id,
                    MaterialCostLkr = request.MaterialCostLkr,
                    LabourCostLkr = request.LabourCostLkr,
                    TotalCostLkr = request.TotalCostLkr,
                    BudgetDeltaPercent = request.BudgetDeltaPercent,
                    PricingSnapshotJson = pricingSnapshotJson,
                    BreakdownJson = breakdownJson,
                    FormulaVersion = request.FormulaVersion.Trim(),
                    AppliedAreaSqft = request.AppliedAreaSqft,
                    TerrainType = terrain,
                    CreatedAt = DateTimeOffset.UtcNow
                };
                _context.CostEstimates.Add(estimate);
            }

            workflow.UpdatedAt = DateTimeOffset.UtcNow;
            try
            {
                await _context.SaveChangesAsync();
            }
            catch (DbUpdateException) when (existingEstimate is null)
            {
                _context.Entry(estimate).State = EntityState.Detached;
                var concurrentEstimate = await _context.CostEstimates
                    .SingleOrDefaultAsync(c => c.HouseDesignId == currentDesign.Id);
                if (concurrentEstimate is null)
                    throw;

                return Ok(ToResponse(concurrentEstimate, currentDesign.Id, true));
            }

            return Ok(ToResponse(estimate, currentDesign.Id, true));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error saving cost estimate for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred saving the cost estimate." });
        }
    }

    [HttpPost("{id:guid}/cost-estimation-runs")]
    public async Task<IActionResult> SaveCostEstimationRun(Guid id, [FromBody] SaveCostEstimationRunDto request)
    {
        var workflow = await FindWorkflowState(id);
        if (workflow is null) return NotFound(new { message = $"Unknown workflow {id}." });
        var status = request.Status.Trim().ToLowerInvariant();
        if (status is not ("success" or "failed"))
            return BadRequest(new { message = "Run status must be success or failed." });
        if (request.CompletedAt < request.StartedAt)
            return BadRequest(new { message = "Completed time cannot precede started time." });

        var design = workflow.HouseDesigns.FirstOrDefault(d => d.IsCurrent && !d.IsArchived);
        var run = new CostEstimationRun
        {
            WorkflowStateId = id,
            HouseDesignId = design?.Id,
            Status = status,
            FormulaVersion = request.FormulaVersion.Trim(),
            PricingRecordCount = Math.Max(0, request.PricingRecordCount),
            AppliedAreaSqft = request.AppliedAreaSqft,
            TerrainType = request.TerrainType?.Trim().ToLowerInvariant(),
            FailureReason = request.FailureReason is { Length: > 1000 }
                ? request.FailureReason[..1000]
                : request.FailureReason,
            StartedAt = request.StartedAt,
            CompletedAt = request.CompletedAt
        };
        _context.CostEstimationRuns.Add(run);
        await _context.SaveChangesAsync();
        return Ok(new { runId = run.Id, run.Status });
    }

    private static CostEstimateResponseDto ToResponse(CostEstimate estimate, Guid designId, bool locked) => new()
    {
        CostEstimateId = estimate.Id,
        HouseDesignId = designId,
        MaterialCostLkr = estimate.MaterialCostLkr,
        LabourCostLkr = estimate.LabourCostLkr,
        TotalCostLkr = estimate.TotalCostLkr,
        BudgetDeltaPercent = estimate.BudgetDeltaPercent,
        PricingSnapshot = JsonSerializer.Deserialize<JsonElement>(estimate.PricingSnapshotJson),
        Breakdown = JsonSerializer.Deserialize<JsonElement>(estimate.BreakdownJson),
        FormulaVersion = estimate.FormulaVersion,
        AppliedAreaSqft = estimate.AppliedAreaSqft,
        TerrainType = estimate.TerrainType,
        Locked = locked
    };
}
