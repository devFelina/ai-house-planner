using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace HousePlanner.API.Entities;

[Table("Rooms")]
public class Room
{
    [Key]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Required]
    public Guid HouseDesignId { get; set; }

    [ForeignKey(nameof(HouseDesignId))]
    public virtual HouseDesign HouseDesign { get; set; } = null!;

    [Required]
    [MaxLength(50)]
    public string RoomType { get; set; } = string.Empty;

    /// <summary>
    /// Human-readable display name (e.g. "Living Room", "Master Bedroom").
    /// </summary>
    [MaxLength(100)]
    public string? Name { get; set; }

    [Required]
    [Column(TypeName = "decimal(8,2)")]
    public decimal X { get; set; }

    [Required]
    [Column(TypeName = "decimal(8,2)")]
    public decimal Y { get; set; }

    [Required]
    [Column(TypeName = "decimal(8,2)")]
    public decimal Width { get; set; }

    [Required]
    [Column(TypeName = "decimal(8,2)")]
    public decimal Length { get; set; }

    /// <summary>
    /// Computed area = Width * Length. Stored for quick querying.
    /// </summary>
    [Column(TypeName = "decimal(10,2)")]
    public decimal AreaSqft { get; set; }

    [Required]
    [Column(TypeName = "decimal(6,2)")]
    public decimal WallHeight { get; set; } = 9.0m;

    [Required]
    public int FloorNumber { get; set; } = 1;
}
