using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace HousePlanner.API.Entities
{
    [Table("WorkflowStates")]
    public class WorkflowState
    {
        [Key]
        public Guid Id { get; set; }

        [Required]
        public Guid LandSubmissionId { get; set; }

        [ForeignKey("LandSubmissionId")]
        public virtual LandSubmission LandSubmission { get; set; } = null!;

        [Required]
        [StringLength(30)]
        public string Status { get; set; } = "pending"; 

        [StringLength(30)]
        public string? TerrainType { get; set; }
        
        [StringLength(30)]
        public string? SlopeEstimate { get; set; }
        
        public string? NotableFeatures { get; set; }

        [Required]
        [StringLength(30)]
        public string ApprovalStatus { get; set; } = "not_requested";

        public Guid? ApprovedByUserId { get; set; }
        
        [ForeignKey("ApprovedByUserId")]
        public virtual User? ApprovedByUser { get; set; }

        public DateTimeOffset? ApprovedAt { get; set; }

        public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
        public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
    }
}
