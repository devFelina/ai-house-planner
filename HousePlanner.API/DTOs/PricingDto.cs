using System.Text.Json.Serialization;
using HousePlanner.API.Entities;

namespace HousePlanner.API.DTOs
{
    public class PricingDto
    {
        public int Id { get; set; }
        public string ItemName { get; set; } = null!;
        public string Category { get; set; } = null!;
        public decimal UnitCostLkr { get; set; }
        public string Unit { get; set; } = null!;
        public TerrainMultiplierData TerrainMultiplier { get; set; } = null!;
    }

    public class UpdatePricingDto
    {
        public decimal UnitCostLkr { get; set; }
        public TerrainMultiplierData TerrainMultiplier { get; set; } = null!;
    }
}
