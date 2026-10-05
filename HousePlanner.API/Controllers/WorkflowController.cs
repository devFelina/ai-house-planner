using System.Text;
using System.Text.Json;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using HousePlanner.API.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Authorization;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/workflows")]
public class WorkflowController : ControllerBase
{
    private readonly ApplicationDbContext _context;
    private readonly ILogger<WorkflowController> _logger;
    private readonly HttpClient _agenticServiceClient;
    private readonly IWorkflowService _workflowService;
    private readonly ICurrentUserContextService _currentUserService;
    private readonly IAIVisualizationUrlService _visualizationUrls;

    public WorkflowController(
        ApplicationDbContext context,
        ILogger<WorkflowController> logger,
        IHttpClientFactory httpClientFactory,
        IWorkflowService workflowService,
        ICurrentUserContextService currentUserService,
        IAIVisualizationUrlService visualizationUrls)
    {
        _context = context;
        _logger = logger;
        _agenticServiceClient = httpClientFactory.CreateClient("AgenticService");
        _workflowService = workflowService;
        _currentUserService = currentUserService;
        _visualizationUrls = visualizationUrls;
    }

    /// <summary>
    /// Returns the current workflow state and latest design summary (including rooms with doors/windows).
    /// </summary>
    /// <param name="id">The WorkflowState unique ID</param>
    [HttpGet("{id:guid}/status")]
    [Authorize(Roles = "Customer,Admin,Constructor")]
    [ProducesResponseType(typeof(WorkflowStatusResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status500InternalServerError)]
    public async Task<ActionResult<WorkflowStatusResponseDto>> GetWorkflowStatus(Guid id, [FromQuery] Guid? designId = null)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();
        bool isCustomer = string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase);
        bool isAdmin = string.Equals(user.Role, "Admin", StringComparison.OrdinalIgnoreCase);
        bool isConstructor = string.Equals(user.Role, "Constructor", StringComparison.OrdinalIgnoreCase);

        if (!isCustomer && !isAdmin && !isConstructor) return Forbid();
        try
        {
            var now = DateTimeOffset.UtcNow;
            var staleCandidate = await _context.WorkflowStates
                .Where(w => w.Id == id && (!isCustomer || w.LandSubmission.ClientId == user.Id.Value))
                .FirstOrDefaultAsync();
            if (staleCandidate is not null && WorkflowExecutionPolicy.IsStale(staleCandidate, now))
            {
                WorkflowExecutionPolicy.MarkStaleFailed(staleCandidate, now);
                await _context.SaveChangesAsync();
            }

            var workflow = await _context.WorkflowStates
                .AsNoTracking()
                .Where(w => w.Id == id && (!isCustomer || w.LandSubmission.ClientId == user.Id.Value))
                .Select(w => new
                {
                    w.Id,
                    w.Status,
                    w.TerrainType,
                    w.SlopeEstimate,
                    w.ApprovalStatus,
                    w.PreferredHouseDesignId,
                    w.FailureReason,
                    w.ConstructionPlan,
                    w.AgentExecutionLogJson,
                    w.ValidationResultJson,
                    w.LandSubmission.LandSizeCategory,
                    w.LandSubmission.LandSizePerches,
                    w.LandSubmission.PreferredBedrooms,
                    w.LandSubmission.PreferredBathrooms,
                    w.LandSubmission.PreferredFloors,
                    w.LandSubmission.StylePreference,
                    // Pick the current (or latest) design version
                    LatestDesign = w.HouseDesigns
                        .Where(d => !d.IsArchived && (designId == null || d.Id == designId))
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
                                .ToList(),
                            LatestCost = d.CostEstimates
                                .OrderByDescending(c => c.CreatedAt)
                                .Select(c => new
                                {
                                    c.MaterialCostLkr,
                                    c.LabourCostLkr,
                                    c.TotalCostLkr,
                                    c.BudgetDeltaPercent,
                                    c.PricingSnapshotJson,
                                    c.BreakdownJson,
                                    c.FormulaVersion,
                                    c.AppliedAreaSqft,
                                    c.TerrainType,
                                    c.CreatedAt
                                })
                                .FirstOrDefault()
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
            CostSummaryDto? costDto = null;
            if (workflow.LatestDesign is not null)
            {
                // Extract doors/windows from LayoutJson for each room
                var doorsWindowsMap = ExtractDoorsWindows(workflow.LatestDesign.LayoutJson);

                var roomDtos = workflow.LatestDesign.Rooms.Select(r =>
                {
                    var roomKey = (r.RoomType, r.FloorNumber, r.X, r.Y);
                    doorsWindowsMap.TryGetValue(roomKey, out var openings);

                    return new RoomSummaryDto(
                        RoomId: openings?.SourceId ?? r.Id,
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

                using var metadata = ParseLayout(workflow.LatestDesign.LayoutJson);
                var root = metadata.RootElement;
                designDto = new HouseDesignSummaryDto(
                    DesignId: workflow.LatestDesign.Id,
                    Version: workflow.LatestDesign.Version,
                    FloorCount: workflow.LatestDesign.FloorCount,
                    TotalBuiltUpAreaSqft: workflow.LatestDesign.TotalBuiltUpAreaSqft,
                    FoundationType: workflow.LatestDesign.FoundationType,
                    TemplateId: workflow.LatestDesign.TemplateId,
                    TerrainType: workflow.LatestDesign.TerrainType,
                    IsCurrent: workflow.LatestDesign.IsCurrent,
                    Rooms: roomDtos,
                    TemplateFamily: root.TryGetProperty("template_family", out var tf) ? tf.GetString() : null,
                    DesignSeed: root.TryGetProperty("design_seed", out var ds) && ds.ValueKind != JsonValueKind.Null ? ds.GetInt64() : null,
                    DesignScore: root.TryGetProperty("design_score", out var sc) && sc.ValueKind != JsonValueKind.Null ? sc.GetDecimal() : null,
                    GeometryFingerprint: root.TryGetProperty("geometry_fingerprint", out var fp) && fp.ValueKind != JsonValueKind.Null ? fp.GetString() : null,
                    GroundFootprintSqft: root.TryGetProperty("ground_footprint_sqft", out var gf) && gf.ValueKind != JsonValueKind.Null ? gf.GetDecimal() : null,
                    Connections: GetMetadata(root, "room_connections"),
                    Entrances: GetMetadata(root, "entrances"),
                    PlotConstraints: GetMetadata(root, "plot_constraints"),
                    CandidateSummary: GetMetadata(root, "candidate_summary")
                );

                if (workflow.LatestDesign.LatestCost is not null)
                {
                    var latest = workflow.LatestDesign.LatestCost;
                    costDto = CostBreakdownBuilder.ToSummary(new CostEstimate
                    {
                        MaterialCostLkr = latest.MaterialCostLkr,
                        LabourCostLkr = latest.LabourCostLkr,
                        TotalCostLkr = latest.TotalCostLkr,
                        BudgetDeltaPercent = latest.BudgetDeltaPercent,
                        PricingSnapshotJson = latest.PricingSnapshotJson,
                        BreakdownJson = latest.BreakdownJson,
                        FormulaVersion = latest.FormulaVersion,
                        AppliedAreaSqft = latest.AppliedAreaSqft,
                        TerrainType = latest.TerrainType,
                        CreatedAt = latest.CreatedAt
                    }, workflow.LatestDesign.TerrainType);
                }
            }

            JsonElement? parsedConstructionPlan = null;
            if (!string.IsNullOrEmpty(workflow.ConstructionPlan))
            {
                try
                {
                    using var doc = JsonDocument.Parse(workflow.ConstructionPlan);
                    parsedConstructionPlan = doc.RootElement.Clone();
                }
                catch (JsonException)
                {
                    // Ignore JSON parsing failure
                }
            }

            IReadOnlyList<AgentExecutionEventDto>? parsedExecutionLog = null;
            if (!string.IsNullOrEmpty(workflow.AgentExecutionLogJson))
            {
                try
                {
                    using var logDoc = JsonDocument.Parse(workflow.AgentExecutionLogJson);
                    if (logDoc.RootElement.ValueKind == JsonValueKind.Array)
                        parsedExecutionLog = logDoc.RootElement.EnumerateArray()
                            .Where(entry => entry.ValueKind == JsonValueKind.Object)
                            .Select(MapExecutionEvent)
                            .ToList();
                }
                catch (JsonException) { /* best-effort */ }
            }

            var latestCostRun = await _context.CostEstimationRuns.AsNoTracking()
                .Where(run => run.WorkflowStateId == id &&
                    (designDto == null || run.HouseDesignId == designDto.DesignId))
                .OrderByDescending(run => run.StartedAt)
                .Select(run => new CostEstimationRunSummaryDto(
                    run.Status, run.FormulaVersion, run.PricingRecordCount,
                    run.AppliedAreaSqft, run.TerrainType, run.FailureReason,
                    run.StartedAt, run.CompletedAt))
                .FirstOrDefaultAsync();

            var validationRequest = designDto is null ? null : await _context.ValidationRequests.AsNoTracking()
                .Where(r => r.WorkflowStateId == workflow.Id && r.HouseDesignId == designDto.DesignId)
                .OrderByDescending(r => r.CreatedAt)
                .Select(r => new { r.Status, r.ArchitectReview, r.DecisionAt })
                .FirstOrDefaultAsync();

            var responseDto = new WorkflowStatusResponseDto(
                WorkflowId: workflow.Id,
                Status: workflow.Status,
                TerrainType: workflow.TerrainType,
                SlopeEstimate: workflow.SlopeEstimate,
                Design: designDto,
                Cost: costDto,
                ConstructionPlan: parsedConstructionPlan,
                ApprovalStatus: workflow.ApprovalStatus,
                FailureReason: workflow.FailureReason,
                PreferredHouseDesignId: workflow.PreferredHouseDesignId,
                ArchitectReviewStatus: validationRequest?.Status,
                ArchitectFeedback: validationRequest?.ArchitectReview,
                AgentExecutionLog: parsedExecutionLog,
                LandSizeCategory: workflow.LandSizeCategory,
                LandSizePerches: workflow.LandSizePerches,
                Bedrooms: workflow.PreferredBedrooms,
                Bathrooms: workflow.PreferredBathrooms,
                HouseType: workflow.StylePreference,
                CostEstimationRun: latestCostRun,
                Requirements: new WorkflowRequirementsDto
                {
                    LandSizeCategory = workflow.LandSizeCategory,
                    LandSizePerches = workflow.LandSizePerches,
                    Bedrooms = workflow.PreferredBedrooms,
                    Bathrooms = workflow.PreferredBathrooms,
                    HouseType = workflow.StylePreference,
                    Floors = workflow.PreferredFloors
                },
                ValidationResultJson: workflow.ValidationResultJson,
                ArchitectDecisionDate: validationRequest?.DecisionAt
            );

            Console.WriteLine("REQUIREMENTS DUMP:");
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(responseDto.Requirements));
            Console.WriteLine($"[TRACE] response bathroom count: {responseDto.Requirements?.Bathrooms}");

            return Ok(responseDto);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error retrieving status for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred retrieving workflow status." });
        }
    }

    private static AgentExecutionEventDto MapExecutionEvent(JsonElement entry)
    {
        static string? ReadString(JsonElement value, string name) =>
            value.TryGetProperty(name, out var property) && property.ValueKind == JsonValueKind.String
                ? property.GetString() : null;
        var agent = ReadString(entry, "agent") ?? ReadString(entry, "agent_name") ?? "unknown";
        var action = ReadString(entry, "action") ?? "step";
        var tool = ReadString(entry, "toolCalled") ?? ReadString(entry, "tool_called");
        var result = ReadString(entry, "result");
        var failed = ReadString(entry, "status") == "failed" ||
            ReadString(entry, "event_status") == "failed" ||
            result == "failed" || action.Contains("failed", StringComparison.OrdinalIgnoreCase);
        var message = ReadString(entry, "message") ?? ReadString(entry, "error_summary") ??
            (tool is null ? action.Replace('_', ' ') : $"{tool.Replace('_', ' ')}: {result ?? action}");
        int? duration = (entry.TryGetProperty("durationMs", out var durationValue) ||
            entry.TryGetProperty("duration_ms", out durationValue)) &&
            durationValue.TryGetInt32(out var milliseconds) ? milliseconds : null;
        DateTimeOffset? createdAt = DateTimeOffset.TryParse(
            ReadString(entry, "createdAt") ?? ReadString(entry, "created_at_utc"), out var parsed)
            ? parsed : null;
        return new AgentExecutionEventDto(agent, failed ? "failed" : "completed", message, tool, duration, createdAt);
    }

    /// <summary>
    /// Extract doors and windows from the LayoutJson for each room (keyed by room_type).
    /// </summary>
    private static Dictionary<(string, int, decimal, decimal), RoomOpenings> ExtractDoorsWindows(string layoutJson)
    {
        var result = new Dictionary<(string, int, decimal, decimal), RoomOpenings>();

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

                    var floor = roomEl.TryGetProperty("floor", out var f) ? f.GetInt32() : 1;
                    var x = roomEl.TryGetProperty("x", out var xp) ? xp.GetDecimal() : 0;
                    var y = roomEl.TryGetProperty("y", out var yp) ? yp.GetDecimal() : 0;
                    Guid? sourceId = roomEl.TryGetProperty("room_id", out var id) && id.TryGetGuid(out var guid) ? guid : null;
                    result[(roomType, floor, x, y)] = new RoomOpenings { SourceId = sourceId, Doors = doors, Windows = windows };
                }
            }
        }
        catch (JsonException ex)
        {
            Console.WriteLine($"Warning: Could not parse LayoutJson for doors/windows: {ex.Message}");
        }

        return result;
    }

    private static JsonDocument ParseLayout(string json)
    {
        try { return JsonDocument.Parse(json); }
        catch (JsonException) { return JsonDocument.Parse("{}"); }
    }

    private static JsonElement? GetMetadata(JsonElement root, string key) =>
        root.ValueKind == JsonValueKind.Object && root.TryGetProperty(key, out var value)
        && value.ValueKind != JsonValueKind.Null ? value.Clone() : null;

    private class RoomOpenings
    {
        public Guid? SourceId { get; set; }
        public List<OpeningDto> Doors { get; set; } = new();
        public List<OpeningDto> Windows { get; set; } = new();
    }

    [HttpGet("{id:guid}/designs")]
    [Authorize(Roles = "Customer")]
    public async Task<IActionResult> GetDesigns(Guid id, [FromQuery] bool includeArchived = true)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();
        if (!string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase)) return Forbid();
        var workflow = await _context.WorkflowStates.AsNoTracking()
            .Include(w => w.HouseDesigns).ThenInclude(d => d.Rooms)
            .FirstOrDefaultAsync(w => w.Id == id && w.LandSubmission.ClientId == user.Id.Value);
        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });
        var review = await _context.ValidationRequests.AsNoTracking().Where(r => r.WorkflowStateId == id)
            .OrderByDescending(r => r.CreatedAt).Select(r => new { r.Status, r.ArchitectReview }).FirstOrDefaultAsync();
        var approvedDesignId = await _context.ValidationRequests.AsNoTracking().Where(r => r.WorkflowStateId == id && r.Status == "Approved").Select(r => r.HouseDesignId).FirstOrDefaultAsync();
        return Ok(ToHistory(workflow, includeArchived, null, review?.Status, review?.ArchitectReview, approvedDesignId));
    }

    [HttpGet("designs")]
    [Authorize(Roles = "Customer")]
    public async Task<IActionResult> GetMyDesigns()
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized(new { message = "User not identified." });
        if (!string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase)) return Forbid();

        var workflowsData = await _context.WorkflowStates.AsNoTracking()
            .Where(w => w.LandSubmission.ClientId == user.Id.Value)
            .OrderByDescending(w => w.UpdatedAt)
            .Select(w => new
            {
                w.Id,
                w.Status,
                w.PreferredHouseDesignId,
                w.CreatedAt,
                Designs = w.HouseDesigns.Where(d => !d.IsArchived).OrderByDescending(d => d.Version).Select(d => new
                {
                    d.Id,
                    d.Version,
                    d.IsCurrent,
                    d.IsArchived,
                    d.TemplateId,
                    d.FloorCount,
                    d.TotalBuiltUpAreaSqft,
                    d.FoundationType,
                    d.CreatedAt,
                    Bedrooms = d.Rooms.Count(r => r.RoomType.ToLower().Contains("bedroom")),
                    Bathrooms = d.Rooms.Count(r => r.RoomType.ToLower().Contains("bathroom"))
                }).ToList()
            })
            .ToListAsync();

        var workflowIds = workflowsData.Select(w => w.Id).ToList();

        var reviews = await _context.ValidationRequests.AsNoTracking()
            .Where(r => workflowIds.Contains(r.WorkflowStateId))
            .Select(r => new { r.WorkflowStateId, r.Status, r.ArchitectReview, r.HouseDesignId, r.CreatedAt })
            .ToListAsync();

        var latestReviewsByWorkflow = reviews
            .GroupBy(r => r.WorkflowStateId)
            .ToDictionary(g => g.Key, g => g.OrderByDescending(r => r.CreatedAt).First());

        var result = workflowsData.Select(w =>
        {
            var hasReview = latestReviewsByWorkflow.TryGetValue(w.Id, out var review);
            var approvedDesignId = hasReview && review.Status == "Approved" ? review.HouseDesignId : (Guid?)null;
            var pid = (Guid?)null;

            var designs = w.Designs.Select(d => new DesignHistoryDto(
                d.Id, d.Version, d.IsCurrent, w.PreferredHouseDesignId == d.Id, d.IsArchived, approvedDesignId == d.Id,
                d.TemplateId, d.Bedrooms, d.Bathrooms, d.FloorCount, d.TotalBuiltUpAreaSqft, d.FoundationType,
                null, null, null, null, null, new List<DesignPreviewRoomDto>(), d.CreatedAt
            )).ToList();

            return new WorkflowDesignHistoryDto(
                w.Id, w.Status, w.PreferredHouseDesignId, w.CreatedAt, designs, pid, hasReview ? review.Status : null, hasReview ? review.ArchitectReview : null
            );
        }).Where(w => w.Designs.Count > 0).ToList();

        return Ok(result);
    }

    [HttpPost("{id:guid}/designs/{designId:guid}/select")]
    [Authorize(Roles = "Customer")]
    public async Task<IActionResult> SelectDesign(Guid id, Guid designId)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();
        if (!string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase)) return Forbid();
        var workflow = await _context.WorkflowStates.Include(w => w.HouseDesigns)
            .FirstOrDefaultAsync(w => w.Id == id && w.LandSubmission.ClientId == user.Id.Value);
        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });
        if (!workflow.HouseDesigns.Any(d => d.Id == designId && !d.IsArchived))
            return BadRequest(new { message = "The selected design does not belong to this workflow." });
        workflow.PreferredHouseDesignId = designId;
        workflow.Status = "selected_by_client";
        workflow.ApprovalStatus = "selected_by_client";
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();
        return Ok(new { workflowId = id, preferredHouseDesignId = designId, status = workflow.Status });
    }

    [HttpDelete("{id:guid}/design-selection")]
    [Authorize(Roles = "Customer")]
    public async Task<IActionResult> ClearDesignSelection(Guid id)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();
        if (!string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase)) return Forbid();
        var workflow = await _context.WorkflowStates.FirstOrDefaultAsync(w => w.Id == id && w.LandSubmission.ClientId == user.Id.Value);
        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });
        workflow.PreferredHouseDesignId = null;
        if (workflow.Status == "selected_by_client") workflow.Status = "design_generated";
        if (workflow.ApprovalStatus == "selected_by_client") workflow.ApprovalStatus = "client_review";
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();
        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });
        workflow.PreferredHouseDesignId = null;
        if (workflow.Status == "selected_by_client") workflow.Status = "design_generated";
        if (workflow.ApprovalStatus == "selected_by_client") workflow.ApprovalStatus = "client_review";
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();
        return Ok(new { workflowId = id, preferredHouseDesignId = (Guid?)null, status = workflow.Status });
    }

    [HttpDelete("{id:guid}/designs/{designId:guid}")]
    [Authorize(Roles = "Customer")]
    public async Task<IActionResult> RemoveDesign(Guid id, Guid designId)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();
        if (!string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase)) return Forbid();
        var workflow = await _context.WorkflowStates.Include(w => w.HouseDesigns)
            .FirstOrDefaultAsync(w => w.Id == id && w.LandSubmission.ClientId == user.Id.Value);
        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });
        var design = workflow.HouseDesigns.FirstOrDefault(d => d.Id == designId && !d.IsArchived);
        if (design is null) return NotFound(new { message = "Design version not found." });
        // 1. Find actual blocking active Project
        // A Project is active if it's not completed. We'll block if there is any Project associated with this design.
        // Wait, the convention is: if an actual active construction Project exists.
        // Even if the project is "completed", the prompt says: "Prefer preserving completed construction history and do not hard-delete anything." So we'll block if ANY Project is linked to it.
        // BUT wait, is a Project automatically created? Let's check if the project has a ContractorId.
        // The prompt says: "Accepted request with ACTIVE construction Project: BLOCK archive with 409."
        var hasActiveProject = await _context.Projects
            .AnyAsync(p => p.HouseDesignId == designId && p.ContractorId != null && p.Status != "Cancelled" && p.Status != "completed");

        if (hasActiveProject)
        {
            return Conflict(new
            {
                code = "design_in_active_construction",
                message = "This design is already being used by an active construction project and cannot be removed."
            });
        }

        // 2. Find pending ConstructorProjectRequests for this design.
        var pendingRequests = await _context.ConstructorProjectRequests
            .Where(r => r.HouseDesignId == designId && r.Status == "Pending")
            .ToListAsync();
        var submitted = workflow.Status == "awaiting_architect_review" ||
            workflow.ApprovalStatus == "awaiting_architect_review" ||
            await _context.ValidationRequests.AnyAsync(r => r.WorkflowStateId == id &&
                (r.Status == "Pending" || r.Status == "Under Review"));




        if (workflow.PreferredHouseDesignId == designId)
        {
            workflow.PreferredHouseDesignId = null;
            workflow.UpdatedAt = DateTimeOffset.UtcNow;
        }

        foreach (var req in pendingRequests)
        {
            req.Status = "Cancelled";
            req.UpdatedAt = DateTimeOffset.UtcNow;
        }

        design.IsArchived = true;
        design.IsCurrent = false;

        var newestRemaining = workflow.HouseDesigns.Where(d => !d.IsArchived && d.Id != designId)
            .OrderByDescending(d => d.Version).FirstOrDefault();
        if (newestRemaining is not null && !workflow.HouseDesigns.Any(d => !d.IsArchived && d.Id != designId && d.IsCurrent))
            newestRemaining.IsCurrent = true;

        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();

        return Ok(new { workflowId = id, designId, action = submitted ? "archived" : "deleted", selectionCleared = workflow.PreferredHouseDesignId is null });
    }

    [HttpPost("{id:guid}/submit-architect-review/{designId:guid}")]
    [Authorize(Roles = "Customer")]
    public async Task<IActionResult> SubmitArchitectReview(Guid id, Guid designId)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();
        if (!string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase)) return Forbid();
        var workflow = await _context.WorkflowStates.Include(w => w.LandSubmission)
            .Include(w => w.HouseDesigns).FirstOrDefaultAsync(w => w.Id == id && w.LandSubmission.ClientId == user.Id.Value);
        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });
        var selected = workflow.HouseDesigns.FirstOrDefault(d => d.Id == designId && !d.IsArchived);
        if (selected is null)
            return BadRequest(new { message = "Selected design version not found." });
        if (string.Equals(workflow.Status, "approved", StringComparison.OrdinalIgnoreCase))
            return Conflict(new { message = "Architect-approved designs cannot be resubmitted." });
        var active = await _context.ValidationRequests.AnyAsync(r => r.WorkflowStateId == id &&
            (r.Status == "Pending" || r.Status == "Under Review"));
        if (active) return Conflict(new { message = "This workflow already has an active architect review." });
        var alreadyReviewed = await _context.ValidationRequests.AnyAsync(r => r.WorkflowStateId == id &&
            r.HouseDesignId == selected.Id && (r.Status == "Approved" || r.Status == "Rejected"));
        if (alreadyReviewed) return Conflict(new { message = "Select a new design version before submitting another review." });
        _context.ValidationRequests.Add(new HousePlanner.API.Entities.ValidationRequest
        {
            WorkflowStateId = id,
            HouseDesignId = selected.Id,
            ClientId = workflow.LandSubmission.ClientId,
            Status = "Pending"
        });
        workflow.Status = "awaiting_architect_review";
        workflow.ApprovalStatus = "awaiting_architect_review";
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();
        return Ok(new { workflowId = id, status = workflow.Status });
    }

    private static WorkflowDesignHistoryDto ToHistory(HousePlanner.API.Entities.WorkflowState workflow, bool includeArchived = true, Guid? projectId = null, string? reviewStatus = null, string? architectFeedback = null, Guid? approvedDesignId = null) =>
        new(workflow.Id, workflow.Status, workflow.PreferredHouseDesignId, workflow.CreatedAt,
            workflow.HouseDesigns.Where(d => includeArchived || !d.IsArchived).OrderByDescending(d => d.Version).Select(d =>
            {
                using var document = ParseLayout(d.LayoutJson);
                var root = document.RootElement;
                var summary = root.TryGetProperty("candidate_summary", out var value) && value.ValueKind == JsonValueKind.Object
                    ? value : default;
                string? SummaryString(string key) => summary.ValueKind == JsonValueKind.Object &&
                    summary.TryGetProperty(key, out var item) && item.ValueKind == JsonValueKind.String ? item.GetString() : null;
                decimal? Number(JsonElement container, string key) => container.ValueKind == JsonValueKind.Object &&
                    container.TryGetProperty(key, out var item) && item.ValueKind == JsonValueKind.Number ? item.GetDecimal() : null;
                var bedrooms = d.Rooms.Count(r => r.RoomType.Contains("bedroom", StringComparison.OrdinalIgnoreCase));
                var bathrooms = d.Rooms.Count(r => r.RoomType.Contains("bathroom", StringComparison.OrdinalIgnoreCase));
                return new DesignHistoryDto(
                    d.Id, d.Version, d.IsCurrent, workflow.PreferredHouseDesignId == d.Id, d.IsArchived, approvedDesignId == d.Id,
                    root.TryGetProperty("template_family", out var topology) ? topology.GetString() : d.TemplateId,
                    bedrooms, bathrooms, d.FloorCount, d.TotalBuiltUpAreaSqft, d.FoundationType,
                    SummaryString("generation_mode"), SummaryString("selected_plan_code") ?? SummaryString("base_plan_code"),
                    root.TryGetProperty("geometry_fingerprint", out var fingerprint) ? fingerprint.GetString() : null,
                    Number(summary, "compatibility_score") ?? Number(summary, "suitability_score"),
                    Number(root, "design_score"),
                    d.Rooms.Select(r => new DesignPreviewRoomDto(r.RoomType, r.FloorNumber, r.X, r.Y, r.Width, r.Length)).ToList(),
                    d.CreatedAt);
            }).ToList(), projectId, reviewStatus, architectFeedback);

    [HttpPost("{id}/approve")]
    [Authorize(Roles = "Customer,Architect,Admin")]
    public async Task<IActionResult> ApproveWorkflow(Guid id, [FromBody] ApprovalRequestDto request)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();
        if (string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase))
        {
            var ownsWorkflow = await _context.WorkflowStates.AnyAsync(w =>
                w.Id == id && w.LandSubmission.ClientId == user.Id.Value);
            if (!ownsWorkflow) return NotFound(new { message = $"Workflow {id} not found." });
        }
        else if (string.Equals(user.Role, "Architect", StringComparison.OrdinalIgnoreCase))
        {
            var submittedForReview = await _context.ValidationRequests.AnyAsync(r => r.WorkflowStateId == id);
            if (!submittedForReview) return NotFound(new { message = $"Workflow {id} not found." });
        }
        else if (!string.Equals(user.Role, "Admin", StringComparison.OrdinalIgnoreCase))
        {
            return Forbid();
        }
        var result = await _workflowService.ProcessApprovalAsync(id, request, user?.Email, user?.Role);

        switch (result.Outcome)
        {
            case ApprovalOutcome.NotFound:
                return NotFound(new { message = result.ErrorMessage });
            case ApprovalOutcome.Conflict:
                return Conflict(new { message = result.ErrorMessage });
            case ApprovalOutcome.InvalidState:
            case ApprovalOutcome.ValidationFailed:
            case ApprovalOutcome.BadRequest:
                return BadRequest(new { message = result.ErrorMessage });
            case ApprovalOutcome.Unauthorized:
                return StatusCode(StatusCodes.Status403Forbidden, new { message = result.ErrorMessage });
            case ApprovalOutcome.Success:
                if (request.Decision.Trim().ToLowerInvariant() is "request_revision" or "revision_requested" or "revision")
                {
                    // Resume LangGraph workflow in Python
                    var workflow = await _context.WorkflowStates
                        .Include(w => w.LandSubmission)
                        .Include(w => w.HouseDesigns)
                        .FirstOrDefaultAsync(w => w.Id == id);
                    if (workflow != null && workflow.LandSubmission != null)
                    {
                        var current = workflow.HouseDesigns.OrderByDescending(d => d.Version).FirstOrDefault();
                        if (current != null)
                        {
                            using var currentLayout = ParseLayout(current.LayoutJson);
                            var root = currentLayout.RootElement;
                            var currentSeed = GetMetadata(root, "design_seed")?.GetInt64() ?? 0;
                            var nextSeed = currentSeed + 1;

                            var payload = new
                            {
                                workflow_id = id,
                                resume_from = "design",
                                user_revision_prompt = request.RevisionNotes,
                                budget_lkr = workflow.LandSubmission.BudgetLkr,
                                land_size_perches = workflow.LandSubmission.LandSizePerches,
                                manual_terrain_type = workflow.LandSubmission.ManualTerrainType,
                                preferences = BuildRevisionPreferences(root, workflow.LandSubmission),
                                terrain_result = new
                                {
                                    terrain_type = workflow.TerrainType,
                                    slope_estimate = workflow.SlopeEstimate
                                },
                                previous_design = root.Clone(),
                                plot_constraints = GetMetadata(root, "plot_constraints"),
                                design_seed = nextSeed,
                                persisted_plan_json = workflow.PlanJson,
                            };

                            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                            await _agenticServiceClient.PostAsync("/workflows/resume", content);
                        }
                    }
                }
                return Ok(result.Response);
            default:
                return BadRequest(new { message = "Unknown approval outcome." });
        }
    }

    private static Dictionary<string, object?> BuildRevisionPreferences(
        JsonElement layout, HousePlanner.API.Entities.LandSubmission submission)
    {
        var preferences = new Dictionary<string, object?>
        {
            ["bedrooms"] = submission.PreferredBedrooms,
            ["floors"] = submission.PreferredFloors,
            ["style"] = submission.StylePreference
        };

        if (layout.TryGetProperty("candidate_summary", out var summary)
            && summary.TryGetProperty("normalized_input", out var normalized)
            && normalized.ValueKind == JsonValueKind.Object)
        {
            var mappings = new Dictionary<string, string>
            {
                ["bedrooms"] = "bedrooms",
                ["bathrooms"] = "bathrooms",
                ["floors"] = "floors",
                ["architectural_style"] = "style",
                ["space_priority"] = "space_priority",
                ["open_plan"] = "open_plan",
                ["master_ensuite"] = "attached_bathroom",
                ["separate_dining"] = "dining_required",
                ["home_office"] = "home_office",
                ["balcony"] = "balcony",
                ["veranda"] = "veranda",
                ["utility_room"] = "utility_room",
                ["parking_required"] = "parking",
                ["accessibility"] = "accessibility"
            };
            foreach (var mapping in mappings)
                if (normalized.TryGetProperty(mapping.Key, out var value) && value.ValueKind != JsonValueKind.Null)
                    preferences[mapping.Value] = value.Clone();
        }

        if (!preferences.ContainsKey("bathrooms"))
        {
            var bathroomCount = layout.TryGetProperty("rooms", out var rooms)
                ? rooms.EnumerateArray().Count(room => room.TryGetProperty("room_type", out var type)
                    && (type.GetString() ?? string.Empty).Contains("bathroom", StringComparison.OrdinalIgnoreCase))
                : 0;
            if (bathroomCount > 0)
                preferences["bathrooms"] = bathroomCount;
        }
        return preferences;
    }

    [HttpPost("{id:guid}/regenerate/{designId:guid}")]
    [Authorize(Roles = "Customer")]
    public async Task<IActionResult> RegenerateDesign(Guid id, Guid designId)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();

        var workflow = await _context.WorkflowStates
            .Include(w => w.LandSubmission)
            .Include(w => w.HouseDesigns)
            .FirstOrDefaultAsync(w => w.Id == id && w.LandSubmission.ClientId == user.Id.Value);

        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });

        var currentDesign = workflow.HouseDesigns.FirstOrDefault(d => d.Id == designId && !d.IsArchived);
        if (currentDesign is null) return NotFound(new { message = "Current design version not found." });

        using var currentLayout = ParseLayout(currentDesign.LayoutJson);
        var root = currentLayout.RootElement;
        var currentSeed = GetMetadata(root, "design_seed")?.GetInt64() ?? 0;
        var nextSeed = currentSeed + 1;
        var previousPlanCode = root.TryGetProperty("candidate_summary", out var summary) && summary.TryGetProperty("selected_plan_code", out var planCode) ? planCode.GetString() : null;
        var previousFingerprint = root.TryGetProperty("geometry_fingerprint", out var fp) ? fp.GetString() : null;

        var payload = new
        {
            workflow_id = id,
            resume_from = "design",
            user_revision_prompt = "Generate Another",
            budget_lkr = workflow.LandSubmission.BudgetLkr,
            land_size_perches = workflow.LandSubmission.LandSizePerches,
            manual_terrain_type = workflow.LandSubmission.ManualTerrainType,
            preferences = BuildRevisionPreferences(root, workflow.LandSubmission),
            terrain_result = new
            {
                terrain_type = workflow.TerrainType,
                slope_estimate = workflow.SlopeEstimate
            },
            previous_design = root.Clone(),
            plot_constraints = GetMetadata(root, "plot_constraints"),
            design_seed = nextSeed,
            persisted_plan_json = workflow.PlanJson,
            regeneration = true,
            previous_base_plan_code = previousPlanCode,
            previous_design_fingerprint = previousFingerprint
        };

        var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        await _agenticServiceClient.PostAsync("/workflows/resume", content);

        workflow.Status = "running";
        workflow.UpdatedAt = DateTimeOffset.UtcNow;
        await _context.SaveChangesAsync();

        return Ok(new { message = "Regeneration started." });
    }

    [HttpPut("{id:guid}/construction-plan")]
    [Authorize(Roles = "Admin,Constructor")]
    public async Task<IActionResult> UpdateConstructionPlan(Guid id, [FromBody] JsonElement planData)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id is null) return Unauthorized();

        var workflow = await _context.WorkflowStates.FirstOrDefaultAsync(w => w.Id == id);
        if (workflow is null) return NotFound(new { message = $"Workflow {id} not found." });

        try
        {
            workflow.ConstructionPlan = planData.GetRawText();
            workflow.UpdatedAt = DateTimeOffset.UtcNow;
            await _context.SaveChangesAsync();

            return Ok(new { message = "Construction plan updated successfully.", constructionPlan = planData });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating construction plan for workflow {WorkflowId}", id);
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred updating the construction plan." });
        }
    }

    [HttpGet("admin/all")]
    [Authorize(Roles = "Admin")]
    public async Task<ActionResult<IEnumerable<AdminWorkflowSummaryDto>>> GetAllWorkflows()
    {
        try
        {
            var workflows = await _context.WorkflowStates
                .AsNoTracking()
                .Include(w => w.LandSubmission)
                    .ThenInclude(ls => ls.Client)
                .OrderByDescending(w => w.CreatedAt)
                .ToListAsync();

            var result = workflows.Select(w => new AdminWorkflowSummaryDto(
                w.Id,
                w.LandSubmission?.Client?.FullName ?? "Unknown",
                w.LandSubmission?.Client?.Email ?? "Unknown",
                w.Status ?? "unknown",
                w.ApprovalStatus ?? "unknown",
                w.CreatedAt
            )).ToList();

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching all workflows for admin");
            return StatusCode(StatusCodes.Status500InternalServerError, new { message = "An error occurred fetching workflows." });
        }
    }

    [HttpDelete("admin/{id:guid}")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> DeleteWorkflow(Guid id)
    {
        var workflow = await _context.WorkflowStates.FindAsync(id);
        if (workflow == null) return NotFound(new { message = $"Workflow {id} not found." });

        _context.WorkflowStates.Remove(workflow);
        await _context.SaveChangesAsync();

        return Ok(new { message = "Workflow deleted successfully." });
    }

    [HttpGet("/api/v1/design/{id:guid}/visualization")]
    [Authorize]
    public async Task<IActionResult> GetDesignVisualization(Guid id)
    {
        var user = await _currentUserService.GetAsync(HttpContext);
        if (user?.Id == null) return Unauthorized();

        var design = await _context.HouseDesigns.AsNoTracking()
            .FirstOrDefaultAsync(d => d.Id == id);

        if (design == null) return NotFound();

        // Check if user has access
        var workflow = await _context.WorkflowStates.AsNoTracking()
            .Include(w => w.LandSubmission)
            .FirstOrDefaultAsync(w => w.Id == design.WorkflowStateId);
            
        if (workflow == null) return NotFound();
        
        bool isCustomer = string.Equals(user.Role, "Customer", StringComparison.OrdinalIgnoreCase);
        if (isCustomer && workflow.LandSubmission.ClientId != user.Id.Value)
        {
            return Forbid();
        }

        JsonElement? layoutRoot = null;
        if (!string.IsNullOrWhiteSpace(design.LayoutJson) && design.LayoutJson != "{}")
        {
            try {
                using var document = JsonDocument.Parse(design.LayoutJson);
                layoutRoot = document.RootElement.Clone();
            } catch { }
        }
        
        var imageUrl = await _visualizationUrls.GetReadUrlAsync(
            design.AIVisualizationImage, HttpContext.RequestAborted);

        return Ok(new
        {
            designId = design.Id.ToString(),
            layout = layoutRoot,
            technicalImage = design.TechnicalPlanImage,
            imageUrl,
            status = design.AIVisualizationStatus
        });
    }
}
