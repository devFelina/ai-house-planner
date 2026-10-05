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
    System.Text.Json.JsonElement? ConstructionPlan,
    string ApprovalStatus,
    string? FailureReason = null,
    Guid? PreferredHouseDesignId = null,
    string? ArchitectReviewStatus = null,
    string? ArchitectFeedback = null,
    IReadOnlyList<AgentExecutionEventDto>? AgentExecutionLog = null,
    string? LandSizeCategory = null,
    decimal? LandSizePerches = null,
    int? Bedrooms = null,
    int? Bathrooms = null,
    string? HouseType = null,
    WorkflowRequirementsDto? Requirements = null,
    CostEstimationRunSummaryDto? CostEstimationRun = null,
    string? ValidationResultJson = null,
    DateTimeOffset? ArchitectDecisionDate = null
);

public record AgentExecutionEventDto(
    string Agent,
    string Status,
    string Message,
    string? ToolCalled,
    int? DurationMs,
    DateTimeOffset? CreatedAt
);

public record CostEstimationRunSummaryDto(
    string Status,
    string FormulaVersion,
    int PricingRecordCount,
    decimal? AppliedAreaSqft,
    string? TerrainType,
    string? FailureReason,
    DateTimeOffset StartedAt,
    DateTimeOffset CompletedAt
);

public class WorkflowRequirementsDto
{
    public string? LandSizeCategory { get; set; }
    public decimal? LandSizePerches { get; set; }
    public int? Bedrooms { get; set; }
    public int? Bathrooms { get; set; }
    public string? HouseType { get; set; }
    public int? Floors { get; set; }
}

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
    decimal? BudgetDeltaPercent,
    IReadOnlyList<CostBreakdownItemDto>? Breakdown = null,
    string? FormulaVersion = null,
    decimal? AppliedAreaSqft = null,
    string? TerrainType = null,
    DateTimeOffset? EstimatedAt = null
);

public record CostBreakdownItemDto(
    string ItemName,
    string CostHead,
    string Category,
    decimal UnitCostLkr,
    string Unit,
    decimal AppliedQuantity,
    string QuantityUnit,
    decimal TerrainMultiplier,
    decimal AmountLkr,
    decimal SharePercent,
    string? Provider = null,
    string? SourceReference = null,
    DateTimeOffset? PricingUpdatedAt = null
);

public record DesignHistoryDto(
    Guid DesignId,
    int Version,
    bool IsCurrent,
    bool IsPreferred,
    bool IsArchived,
    bool IsArchitectApproved,
    string? Topology,
    int Bedrooms,
    int Bathrooms,
    int FloorCount,
    decimal TotalBuiltUpAreaSqft,
    string FoundationType,
    string? GenerationMode,
    string? SelectedBasePlan,
    string? GeometryFingerprint,
    decimal? SuitabilityScore,
    decimal? ArchitecturalQualityScore,
    List<DesignPreviewRoomDto> PreviewRooms,
    DateTimeOffset CreatedAt
);

public record DesignPreviewRoomDto(
    string RoomType, int Floor, decimal X, decimal Y, decimal Width, decimal Length
);

public record WorkflowDesignHistoryDto(
    Guid WorkflowId,
    string Status,
    Guid? PreferredHouseDesignId,
    DateTimeOffset CreatedAt,
    List<DesignHistoryDto> Designs,
    Guid? ProjectId = null,
    string? ArchitectReviewStatus = null,
    string? ArchitectFeedback = null
);

// ──────────────────────────────────────────────────
// Constructor Workflow DTOs
// ──────────────────────────────────────────────────

public record ConstructionPhaseDto(
    Guid Id,
    string PhaseName,
    int SequenceOrder,
    string Status,
    DateTimeOffset? StartedAt,
    DateTimeOffset? CompletedAt,
    int AiEstimatedDurationDays,
    int PlannedDurationDays,
    DateOnly? PlannedStartDate,
    DateOnly? PlannedEndDate
);

public record ConstructorDesignDto(
    Guid DesignId,
    int Version,
    int FloorCount,
    decimal TotalBuiltUpAreaSqft,
    string FoundationType,
    string LayoutJson
);

public record ConstructorProjectDto(
    Guid Id,
    Guid WorkflowStateId,
    Guid? HouseDesignId,
    Guid? ContractorId,
    string Status,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    int AiEstimatedTotalDurationDays,
    int PlannedTotalDurationDays,
    List<ConstructionPhaseDto> ConstructionPhases,
    ConstructorDesignDto? Design = null,
    CostSummaryDto? Cost = null
);

public record UpdatePhaseScheduleRequest(
    int PlannedDurationDays
);

public record AdminWorkflowSummaryDto(
    Guid WorkflowId,
    string ClientName,
    string ClientEmail,
    string Status,
    string ApprovalStatus,
    DateTimeOffset CreatedAt
);

public sealed class WorkflowPlanStateRequest
{
    public System.Text.Json.JsonElement Plan { get; set; }
    public string? CurrentStepId { get; set; }
    public List<string> CompletedStepIds { get; set; } = new();
}

public sealed class ToolAuditLogRequest
{
    public List<ToolAuditEntryDto>? Entries { get; set; } = new();
}

public sealed class ToolAuditEntryDto
{
    public string AgentName { get; set; } = string.Empty;
    public string Action { get; set; } = string.Empty;
    public string? ToolCalled { get; set; }
    public int? DurationMs { get; set; }
    public string Result { get; set; } = string.Empty;
    public string? EventStatus { get; set; }
    public Dictionary<string, System.Text.Json.JsonElement>? InputSummary { get; set; }
    public Dictionary<string, System.Text.Json.JsonElement>? OutputSummary { get; set; }
    public string? ErrorType { get; set; }
    public string? ErrorSummary { get; set; }
    public string CreatedAtUtc { get; set; } = string.Empty;
}
