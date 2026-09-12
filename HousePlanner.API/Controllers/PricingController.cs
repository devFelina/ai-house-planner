using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using HousePlanner.API.DTOs;
using HousePlanner.API.Services;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/[controller]")]
    public class PricingController : ControllerBase
    {
        private readonly IPricingService _pricingService;

        public PricingController(IPricingService pricingService)
        {
            _pricingService = pricingService;
        }

        /// <summary>
        /// Retrieves all current pricing items.
        /// </summary>
        [HttpGet]
        [ProducesResponseType(typeof(IEnumerable<PricingDto>), StatusCodes.Status200OK)]
        public async Task<IActionResult> GetAllPricing()
        {
            var pricingItems = await _pricingService.GetAllPricingAsync();
            return Ok(pricingItems);
        }

        /// <summary>
        /// Updates a specific pricing item.
        /// </summary>
        /// <param name="id">The ID of the pricing item to update.</param>
        /// <param name="updateDto">The updated pricing data.</param>
        [HttpPut("{id}")]
        // TODO: Integration Dependency - This requires Member 1's shared authentication middleware 
        // to be completed so that [Authorize(Roles = "Contractor")] functions correctly with the tokens.
        [Authorize(Roles = "Contractor")]
        [ProducesResponseType(typeof(PricingDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        [ProducesResponseType(StatusCodes.Status403Forbidden)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> UpdatePricing(int id, [FromBody] UpdatePricingDto updateDto)
        {
            if (!ModelState.IsValid)
            {
                return BadRequest(ModelState);
            }

            // Additional validation per requirements
            if (updateDto.UnitCostLkr <= 0)
            {
                return BadRequest("UnitCostLkr must be greater than zero.");
            }

            if (updateDto.TerrainMultiplier == null || 
                updateDto.TerrainMultiplier.Flat <= 0 || 
                updateDto.TerrainMultiplier.Hillside <= 0 || 
                updateDto.TerrainMultiplier.Coastal <= 0)
            {
                return BadRequest("TerrainMultiplier values must be provided and greater than zero.");
            }

            var updatedItem = await _pricingService.UpdatePricingAsync(id, updateDto);
            
            if (updatedItem == null)
            {
                return NotFound($"Pricing item with ID {id} not found.");
            }

            return Ok(updatedItem);
        }
    }
}
