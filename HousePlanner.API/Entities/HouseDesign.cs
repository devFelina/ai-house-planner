using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace HousePlanner.API.Entities;

[Table("HouseDesigns")]
public class HouseDesign
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    public Guid WorkflowStateId { get; set; }

    [ForeignKey(nameof(WorkflowStateId))]
    public virtual WorkflowState WorkflowState { get; set; } = null!;

    [Required]
    public int Version { get; set; } = 1;

    [Required]
    public int FloorCount { get; set; }

    [Required]
    [Column(TypeName = "decimal(10,2)")]
    public decimal TotalBuiltUpAreaSqft { get; set; }

    [Required]
    [MaxLength(30)]
    public string FoundationType { get; set; } = string.Empty;

    /// <summary>
    /// Identifier of the deterministic layout template used (e.g. "3BR_2F_HILLSIDE").
    /// </summary>
    [MaxLength(50)]
    public string? TemplateId { get; set; }

    /// <summary>
    /// Terrain type used for this design (flat, hillside, coastal).
    /// </summary>
    [MaxLength(30)]
    public string? TerrainType { get; set; }

    /// <summary>
    /// Only one design version per workflow should be marked as current.
    /// Previous versions are kept for traceability but marked IsCurrent = false.
    /// </summary>
    [Required]
    public bool IsCurrent { get; set; } = true;

    /// <summary>
    /// Stores the shared JSON layout contract (rooms, coordinates, openings) as native PostgreSQL JSONB.
    /// </summary>
    [Required]
    [Column(TypeName = "jsonb")]
    public string LayoutJson { get; set; } = "{}";

    [Column(TypeName = "timestamp with time zone")]
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    // Relational navigation to room rows
    public virtual ICollection<Room> Rooms { get; set; } = new List<Room>();
}
