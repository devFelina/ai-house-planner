using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace HousePlanner.API.Entities
{
    [Table("ConstructionPhases")]
    public class ConstructionPhase
    {
        [Key]
        public Guid Id { get; set; }

        [Required]
        public Guid ProjectId { get; set; }

        [ForeignKey("ProjectId")]
        public virtual Project Project { get; set; } = null!;

        [Required]
        [StringLength(150)]
        public string PhaseName { get; set; } = null!;

        [Required]
        [StringLength(50)]
        public string Status { get; set; } = "pending";

        public DateTimeOffset? StartedAt { get; set; }

        public DateTimeOffset? CompletedAt { get; set; }

        [Required]
        public int SequenceOrder { get; set; }
    }
}
