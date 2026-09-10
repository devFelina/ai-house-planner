namespace HousePlanner.API.DTOs
{
    public class ProjectTrackingResponseDto
    {
        public Guid ProjectId { get; set; }
        public string Status { get; set; } = string.Empty;
        public string? ContractorName { get; set; }
        public List<PhaseTrackingDto> Phases { get; set; } = new List<PhaseTrackingDto>();
    }
}
