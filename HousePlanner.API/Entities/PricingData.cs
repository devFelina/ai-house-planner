using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using System.Text.Json.Serialization;

namespace HousePlanner.API.Entities
{
    [Table("PricingData")]
    public class PricingData
    {
        [Key]
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        public int Id { get; set; }

        [Required]
        [StringLength(255)]
        public string ItemName { get; set; } = null!;

        [Required]
        [StringLength(100)]
        public string Category { get; set; } = null!; // e.g. material, labour

        [Required]
        [Column(TypeName = "decimal(18,2)")]
        public decimal UnitCostLkr { get; set; }

        [Required]
        [StringLength(50)]
        public string Unit { get; set; } = null!;

        [Required]
        public TerrainMultiplierData TerrainMultiplier { get; set; } = new TerrainMultiplierData();

        public DateTimeOffset UpdatedAt { get; set; }
    }

    public class TerrainMultiplierData
    {
        [JsonPropertyName("flat")]
        public decimal Flat { get; set; } = 1.0m;

        [JsonPropertyName("hillside")]
        public decimal Hillside { get; set; } = 1.25m;

        [JsonPropertyName("coastal")]
        public decimal Coastal { get; set; } = 1.35m;
    }
}
