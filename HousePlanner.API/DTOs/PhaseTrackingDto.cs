namespace HousePlanner.API.DTOs
{
    public class PhaseTrackingDto
    {
        public string PhaseName { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
        public DateTimeOffset? StartedAtUtc { get; set; }
        public DateTimeOffset? CompletedAtUtc { get; set; }
        public int SequenceOrder { get; set; }
    }
}
