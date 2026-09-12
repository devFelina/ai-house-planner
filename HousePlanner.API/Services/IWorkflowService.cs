using HousePlanner.API.DTOs;

namespace HousePlanner.API.Services
{
    public class WorkflowSessionInfo
    {
        public Guid WorkflowId { get; set; }
        public string Status { get; set; } = "running"; // running, awaiting_approval, approved, rejected, failed
        public string ApprovalStatus { get; set; } = "not_requested"; // not_requested, pending, approved, rejected, revision_requested
        public bool ValidationPassed { get; set; }
        public int RetryCount { get; set; }
        public string? RevisionNotes { get; set; }
        public object? ValidationResult { get; set; }
        public Guid? ProjectId { get; set; }
        public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
        public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    }

    public enum ApprovalOutcome
    {
        Success,
        NotFound,
        InvalidState,
        ValidationFailed,
        Conflict,
        BadRequest,
        Unauthorized
    }

    public class ApprovalServiceResult
    {
        public ApprovalOutcome Outcome { get; set; }
        public string ErrorMessage { get; set; } = string.Empty;
        public ApprovalResponseDto? Response { get; set; }

        public static ApprovalServiceResult Success(ApprovalResponseDto response) =>
            new() { Outcome = ApprovalOutcome.Success, Response = response };

        public static ApprovalServiceResult NotFound(string message) =>
            new() { Outcome = ApprovalOutcome.NotFound, ErrorMessage = message };

        public static ApprovalServiceResult InvalidState(string message) =>
            new() { Outcome = ApprovalOutcome.InvalidState, ErrorMessage = message };

        public static ApprovalServiceResult ValidationFailed(string message) =>
            new() { Outcome = ApprovalOutcome.ValidationFailed, ErrorMessage = message };

        public static ApprovalServiceResult Conflict(string message) =>
            new() { Outcome = ApprovalOutcome.Conflict, ErrorMessage = message };

        public static ApprovalServiceResult BadRequest(string message) =>
            new() { Outcome = ApprovalOutcome.BadRequest, ErrorMessage = message };

        public static ApprovalServiceResult Unauthorized(string message) =>
            new() { Outcome = ApprovalOutcome.Unauthorized, ErrorMessage = message };
    }

    public interface IWorkflowService
    {
        Task<WorkflowSessionInfo?> GetWorkflowStatusAsync(Guid workflowId);
        Task<ApprovalServiceResult> ProcessApprovalAsync(Guid workflowId, ApprovalRequestDto request, string? userEmail = null, string? userRole = null);
        void SetWorkflowSession(WorkflowSessionInfo session);
    }
}
