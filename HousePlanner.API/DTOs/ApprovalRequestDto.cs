using System.ComponentModel.DataAnnotations;

namespace HousePlanner.API.DTOs
{
    public class ApprovalRequestDto
    {
        [Required(ErrorMessage = "Decision is required.")]
        public string Decision { get; set; } = string.Empty;

        public string? RevisionNotes { get; set; }
    }
}
