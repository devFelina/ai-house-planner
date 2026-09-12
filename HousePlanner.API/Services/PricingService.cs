using Microsoft.EntityFrameworkCore;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;

namespace HousePlanner.API.Services
{
    public class PricingService : IPricingService
    {
        private readonly ApplicationDbContext _context;

        public PricingService(ApplicationDbContext context)
        {
            _context = context;
        }

        public async Task<IEnumerable<PricingDto>> GetAllPricingAsync()
        {
            var items = await _context.PricingItems.ToListAsync();
            return items.Select(MapToDto);
        }

        public async Task<PricingDto?> GetPricingByIdAsync(int id)
        {
            var item = await _context.PricingItems.FindAsync(id);
            if (item == null) return null;
            return MapToDto(item);
        }

        public async Task<PricingDto?> UpdatePricingAsync(int id, UpdatePricingDto updateDto)
        {
            var item = await _context.PricingItems.FindAsync(id);
            if (item == null) return null;

            item.UnitCostLkr = updateDto.UnitCostLkr;
            
            // Only update terrain multipliers if provided
            if (updateDto.TerrainMultiplier != null)
            {
                item.TerrainMultiplier.Flat = updateDto.TerrainMultiplier.Flat;
                item.TerrainMultiplier.Hillside = updateDto.TerrainMultiplier.Hillside;
                item.TerrainMultiplier.Coastal = updateDto.TerrainMultiplier.Coastal;
            }

            item.UpdatedAt = DateTimeOffset.UtcNow;

            await _context.SaveChangesAsync();

            return MapToDto(item);
        }

        private PricingDto MapToDto(PricingData entity)
        {
            return new PricingDto
            {
                Id = entity.Id,
                ItemName = entity.ItemName,
                Category = entity.Category,
                UnitCostLkr = entity.UnitCostLkr,
                Unit = entity.Unit,
                TerrainMultiplier = new TerrainMultiplierData 
                {
                    Flat = entity.TerrainMultiplier.Flat,
                    Hillside = entity.TerrainMultiplier.Hillside,
                    Coastal = entity.TerrainMultiplier.Coastal
                }
            };
        }
    }
}
