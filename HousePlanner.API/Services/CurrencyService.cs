using Microsoft.Extensions.Caching.Memory;
using System.Text.Json;

namespace HousePlanner.API.Services;

public interface ICurrencyService
{
    Task<decimal?> GetExchangeRateAsync(string fromCurrency, string toCurrency);
}

public class CurrencyService : ICurrencyService
{
    private readonly HttpClient _httpClient;
    private readonly IMemoryCache _cache;
    private readonly ILogger<CurrencyService> _logger;

    public CurrencyService(HttpClient httpClient, IMemoryCache cache, IConfiguration config, ILogger<CurrencyService> logger)
    {
        _httpClient = httpClient;
        _cache = cache;
        _logger = logger;
        
        var baseUrl = config["CURRENCY_API_BASE_URL"] ?? Environment.GetEnvironmentVariable("CURRENCY_API_BASE_URL");
        if (!string.IsNullOrWhiteSpace(baseUrl))
        {
            _httpClient.BaseAddress = new Uri(baseUrl);
        }
        else
        {
            _httpClient.BaseAddress = new Uri("https://api.frankfurter.dev");
        }
    }

    public async Task<decimal?> GetExchangeRateAsync(string fromCurrency, string toCurrency)
    {
        string cacheKey = $"ExchangeRate_{fromCurrency}_{toCurrency}";
        if (_cache.TryGetValue(cacheKey, out decimal cachedRate))
        {
            return cachedRate;
        }

        try
        {
            var response = await _httpClient.GetAsync($"/v2/rate/{fromCurrency.ToLower()}/{toCurrency.ToLower()}");
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Failed to fetch exchange rate. Status Code: {StatusCode}", response.StatusCode);
                return null;
            }

            var jsonString = await response.Content.ReadAsStringAsync();
            using var document = JsonDocument.Parse(jsonString);
            var root = document.RootElement;
            
            if (root.TryGetProperty("rate", out var rateElement) && rateElement.TryGetDecimal(out var rate))
            {
                var cacheEntryOptions = new MemoryCacheEntryOptions()
                    .SetAbsoluteExpiration(TimeSpan.FromHours(1));

                _cache.Set(cacheKey, rate, cacheEntryOptions);
                return rate;
            }
            return null;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error occurred while fetching exchange rate.");
            return null;
        }
    }
}
