using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace HousePlanner.API.Entities
{
    [Table("Projects")]
    public class Project
    {
        [Key]
        public Guid Id { get; set; }

        [Required]
        public Guid WorkflowStateId { get; set; }

        // TODO: Add WorkflowState navigation property once the entity is created by Member 1
        // [ForeignKey("WorkflowStateId")]
        // public virtual WorkflowState WorkflowState { get; set; } = null!;

        public Guid? ContractorId { get; set; }

        [Required]
        [StringLength(50)]
        public string Status { get; set; } = "not_started";

        public DateTimeOffset CreatedAt { get; set; }

        public DateTimeOffset UpdatedAt { get; set; }

        public virtual ICollection<ConstructionPhase> ConstructionPhases { get; set; } = new List<ConstructionPhase>();
    }
}
