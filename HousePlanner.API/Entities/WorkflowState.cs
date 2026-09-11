using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace HousePlanner.API.Entities;

[Table("WorkflowStates")]
public class WorkflowState
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    public Guid LandSubmissionId { get; set; }

    [Required]
    [MaxLength(30)]
    public string Status { get; set; } = "pending";

    [MaxLength(30)]
    public string? TerrainType { get; set; }

    [MaxLength(30)]
    public string? SlopeEstimate { get; set; }

    [Column(TypeName = "jsonb")]
    public string? NotableFeatures { get; set; }

    [Required]
    [MaxLength(30)]
    public string ApprovalStatus { get; set; } = "not_requested";

    public Guid? ApprovedByUserId { get; set; }

    public DateTimeOffset? ApprovedAt { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;

    // Navigation properties
    public virtual ICollection<HouseDesign> HouseDesigns { get; set; } = new List<HouseDesign>();
}
