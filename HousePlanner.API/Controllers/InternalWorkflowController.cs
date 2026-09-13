using System.Text.Json;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/internal/workflows")]
// Requires InternalServiceAuthMiddleware — shared secret header, not JWT
public class InternalWorkflowController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<InternalWorkflowController> _logger;

    public InternalWorkflowController(ApplicationDbContext context, ILogger<InternalWorkflowController> logger)
    {
        _context = context;
        _logger = logger;
    }

    private async Task<WorkflowState?> FindWorkflowState(Guid workflowId)
    {
        var workflow = await _context.WorkflowStates
            .Include(w => w.HouseDesigns)
            .FirstOrDefaultAsync(w => w.Id == workflowId);

        return workflow;
    }

    /// <summary>
    /// Internal endpoint for the Design Agent to submit a new generated layout.
    /// Used both for initial generation and revisions after validation failure.
    /// Manages design versioning — marks old versions as not current.
    /// </summary>
    [HttpPost("{id:guid}/design")]
    public async Task<IActionResult> SubmitDesignRevision(Guid id, [FromBody] JsonElement layoutData)
    {
        try
        {
            var workflow = await FindWorkflowState(id);
            if (workflow is null)
                return NotFound(new { message = $"Unknown workflow {id}; callback was not persisted." });

            // Extract required fields from the JSON contract
            int floorCount = layoutData.GetProperty("floor_count").GetInt32();
            decimal totalArea = layoutData.TryGetProperty("total_built_up_area_sqft", out var areaProp)
                ? areaProp.GetDecimal()
                : 0m;

            string foundationType = layoutData.TryGetProperty("foundation_type", out var foundProp)
                ? foundProp.GetString() ?? "unknown"
                : "unknown";

            string? templateId = layoutData.TryGetProperty("template_id", out var tmplProp)
                ? tmplProp.GetString()
                : null;

            string? terrainType = layoutData.TryGetProperty("terrain_type", out var terrProp)
                ? terrProp.GetString()
                : null;

            // Mark all existing designs for this workflow as not current
            foreach (var existing in workflow.HouseDesigns.Where(d => d.IsCurrent))
            {
                existing.IsCurrent = false;
            }

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
            _logger.LogError(ex, "Error saving design for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred saving the design." });
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
}
