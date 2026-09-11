using System.Text.Json;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/workflows")]
public class WorkflowController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<WorkflowController> _logger;

    public WorkflowController(ApplicationDbContext context, ILogger<WorkflowController> logger)
    {
        _context = context;
        _logger = logger;
    }

    /// <summary>
    /// Returns the current workflow state and latest design summary (including rooms with doors/windows).
    /// </summary>
    /// <param name="id">The WorkflowState unique ID</param>
    [HttpGet("{id:guid}/status")]
    [ProducesResponseType(typeof(WorkflowStatusResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<ActionResult<WorkflowStatusResponseDto>> GetWorkflowStatus(Guid id)
    {
        try
        {
            var workflow = await _context.WorkflowStates
                .AsNoTracking()
                .Where(w => w.Id == id)
                .Select(w => new
                {
                    w.Id,
                    w.Status,
                    w.TerrainType,
                    w.SlopeEstimate,
                    w.ApprovalStatus,
                    // Pick the current (or latest) design version
                    LatestDesign = w.HouseDesigns
                        .OrderByDescending(d => d.IsCurrent)
                        .ThenByDescending(d => d.Version)
                        .Select(d => new
                        {
                            d.Id,
                            d.Version,
                            d.FloorCount,
                            d.TotalBuiltUpAreaSqft,
                            d.FoundationType,
                            d.TemplateId,
                            d.TerrainType,
                            d.IsCurrent,
                            d.LayoutJson,
                            Rooms = d.Rooms
                                .OrderBy(r => r.FloorNumber)
                                .ThenBy(r => r.RoomType)
                                .Select(r => new
                                {
                                    r.Id,
                                    r.RoomType,
                                    r.Name,
                                    r.FloorNumber,
                                    r.X,
                                    r.Y,
                                    r.Width,
                                    r.Length,
                                    r.AreaSqft,
                                    r.WallHeight
                                })
                                .ToList()
                        })
                        .FirstOrDefault()
                })
                .FirstOrDefaultAsync();

            if (workflow is null)
            {
                _logger.LogWarning("Workflow with ID {WorkflowId} not found.", id);
                return NotFound(new { message = $"Workflow {id} not found." });
            }

            HouseDesignSummaryDto? designDto = null;
            if (workflow.LatestDesign is not null)
            {
                // Extract doors/windows from LayoutJson for each room
                var doorsWindowsMap = ExtractDoorsWindows(workflow.LatestDesign.LayoutJson);

                var roomDtos = workflow.LatestDesign.Rooms.Select(r =>
                {
                    var roomKey = r.RoomType;
                    doorsWindowsMap.TryGetValue(roomKey, out var openings);

                    return new RoomSummaryDto(
                        RoomId: r.Id,
                        RoomType: r.RoomType,
                        Name: r.Name,
                        FloorNumber: r.FloorNumber,
                        X: r.X,
                        Y: r.Y,
                        Width: r.Width,
                        Length: r.Length,
                        AreaSqft: r.AreaSqft,
                        WallHeight: r.WallHeight,
                        Doors: openings?.Doors,
                        Windows: openings?.Windows
                    );
                }).ToList();

                designDto = new HouseDesignSummaryDto(
                    DesignId: workflow.LatestDesign.Id,
                    Version: workflow.LatestDesign.Version,
                    FloorCount: workflow.LatestDesign.FloorCount,
                    TotalBuiltUpAreaSqft: workflow.LatestDesign.TotalBuiltUpAreaSqft,
                    FoundationType: workflow.LatestDesign.FoundationType,
                    TemplateId: workflow.LatestDesign.TemplateId,
                    TerrainType: workflow.LatestDesign.TerrainType,
                    IsCurrent: workflow.LatestDesign.IsCurrent,
                    Rooms: roomDtos
                );
            }

            var response = new WorkflowStatusResponseDto(
                WorkflowId: workflow.Id,
                Status: workflow.Status,
                TerrainType: workflow.TerrainType,
                SlopeEstimate: workflow.SlopeEstimate,
                Design: designDto,
                Cost: null, // CostSummary is populated when Component C adds CostEstimates
                ApprovalStatus: workflow.ApprovalStatus
            );

            return Ok(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving workflow status for ID {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred retrieving workflow status." });
        }
    }

    /// <summary>
    /// Extract doors and windows from the LayoutJson for each room (keyed by room_type).
    /// </summary>
    private static Dictionary<string, RoomOpenings> ExtractDoorsWindows(string layoutJson)
    {
        var result = new Dictionary<string, RoomOpenings>();

        try
        {
            using var doc = JsonDocument.Parse(layoutJson);
            if (doc.RootElement.TryGetProperty("rooms", out var roomsElement) && roomsElement.ValueKind == JsonValueKind.Array)
            {
                foreach (var roomEl in roomsElement.EnumerateArray())
                {
                    var roomType = roomEl.TryGetProperty("room_type", out var rt) ? rt.GetString() ?? "" : "";

                    var doors = new List<OpeningDto>();
                    var windows = new List<OpeningDto>();

                    if (roomEl.TryGetProperty("doors", out var doorsEl) && doorsEl.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var d in doorsEl.EnumerateArray())
                        {
                            doors.Add(new OpeningDto(
                                Wall: d.TryGetProperty("wall", out var w) ? w.GetString() ?? "" : "",
                                Offset: d.TryGetProperty("offset", out var o) ? o.GetDecimal() : 0m,
                                Width: d.TryGetProperty("width", out var wd) ? wd.GetDecimal() : 0m
                            ));
                        }
                    }

                    if (roomEl.TryGetProperty("windows", out var winsEl) && winsEl.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var win in winsEl.EnumerateArray())
                        {
                            windows.Add(new OpeningDto(
                                Wall: win.TryGetProperty("wall", out var w) ? w.GetString() ?? "" : "",
                                Offset: win.TryGetProperty("offset", out var o) ? o.GetDecimal() : 0m,
                                Width: win.TryGetProperty("width", out var wd) ? wd.GetDecimal() : 0m
                            ));
                        }
                    }

                    result[roomType] = new RoomOpenings { Doors = doors, Windows = windows };
                }
            }
        }
        catch (JsonException ex)
        {
            // If LayoutJson is malformed, return empty — don't crash the status endpoint
            Console.WriteLine($"Warning: Could not parse LayoutJson for doors/windows: {ex.Message}");
        }

        return result;
    }

    private class RoomOpenings
    {
        public List<OpeningDto> Doors { get; set; } = new();
        public List<OpeningDto> Windows { get; set; } = new();
    }
}
