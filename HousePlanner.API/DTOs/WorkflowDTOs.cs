namespace HousePlanner.API.DTOs;

// ──────────────────────────────────────────────────
// Workflow Status Response (public endpoint)
// ──────────────────────────────────────────────────

public record WorkflowStatusResponseDto(
    Guid WorkflowId,
    string Status,
    string? TerrainType,
    string? SlopeEstimate,
    HouseDesignSummaryDto? Design,
    CostSummaryDto? Cost,
    string ApprovalStatus,
    string? FailureReason = null
);

public record HouseDesignSummaryDto(
    Guid DesignId,
    int Version,
    int FloorCount,
    decimal TotalBuiltUpAreaSqft,
    string FoundationType,
    string? TemplateId,
    string? TerrainType,
    bool IsCurrent,
    List<RoomSummaryDto> Rooms,
    string? TemplateFamily = null,
    long? DesignSeed = null,
    decimal? DesignScore = null,
    string? GeometryFingerprint = null,
    decimal? GroundFootprintSqft = null,
    System.Text.Json.JsonElement? Connections = null,
    System.Text.Json.JsonElement? Entrances = null,
    System.Text.Json.JsonElement? PlotConstraints = null,
    System.Text.Json.JsonElement? CandidateSummary = null
);

public record RoomSummaryDto(
    Guid RoomId,
    string RoomType,
    string? Name,
    int FloorNumber,
    decimal X,
    decimal Y,
    decimal Width,
    decimal Length,
    decimal AreaSqft,
    decimal WallHeight,
    List<OpeningDto>? Doors,
    List<OpeningDto>? Windows
);

public record OpeningDto(
    string Wall,
    decimal Offset,
    decimal Width
);

public record CostSummaryDto(
    decimal MaterialCostLkr,
    decimal LabourCostLkr,
    decimal TotalCostLkr,
    decimal BudgetDeltaPercent
);
