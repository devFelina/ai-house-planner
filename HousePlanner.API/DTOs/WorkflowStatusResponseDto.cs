namespace HousePlanner.API.DTOs
{
    public class WorkflowStatusResponseDto
    {
        public Guid WorkflowId { get; set; }
        public string Status { get; set; } = string.Empty;
        public string ApprovalStatus { get; set; } = string.Empty;
        public bool ValidationPassed { get; set; }
        public int RetryCount { get; set; }
        public string? RevisionNotes { get; set; }
        public object? ValidationResult { get; set; }
        public Guid? ProjectId { get; set; }
        public DateTimeOffset CreatedAt { get; set; }
        public DateTimeOffset UpdatedAt { get; set; }
    }
}
