using HousePlanner.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class CurrencyController : ControllerBase
{
    private readonly ICurrencyService _currencyService;

    public CurrencyController(ICurrencyService currencyService)
    {
        _currencyService = currencyService;
    }

    [HttpGet("rate")]
    public async Task<IActionResult> GetRate([FromQuery] string from = "LKR", [FromQuery] string to = "USD")
    {
        var rate = await _currencyService.GetExchangeRateAsync(from, to);
        if (rate == null)
        {
            return StatusCode(503, new { message = "Currency conversion temporarily unavailable." });
        }

        return Ok(new
        {
            baseCurrency = from,
            targetCurrency = to,
            rate = rate.Value,
            source = "frankfurter",
            fetchedAt = DateTimeOffset.UtcNow
        });
    }
}
