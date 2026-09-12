namespace HousePlanner.API.DTOs
{
    public class ApprovalResponseDto
    {
        public Guid WorkflowId { get; set; }
        public string Decision { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
        public Guid? ProjectId { get; set; }
        public string Message { get; set; } = string.Empty;
        public DateTimeOffset Timestamp { get; set; }
    }
}
