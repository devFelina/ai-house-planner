using HousePlanner.API.DTOs;

namespace HousePlanner.API.Services
{
    public interface IPricingService
    {
        Task<IEnumerable<PricingDto>> GetAllPricingAsync();
        Task<PricingDto?> GetPricingByIdAsync(int id);
        Task<PricingDto?> UpdatePricingAsync(int id, UpdatePricingDto updateDto);
    }
}
