using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using HousePlanner.API.Services;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using Moq.Protected;
using Xunit;

namespace HousePlanner.API.Tests.Services
{
    public class CurrencyServiceTests
    {
        private readonly Mock<ILogger<CurrencyService>> _mockLogger;
        private readonly IMemoryCache _memoryCache;
        private readonly Mock<IConfiguration> _mockConfig;
        
        public CurrencyServiceTests()
        {
            _mockLogger = new Mock<ILogger<CurrencyService>>();
            _memoryCache = new MemoryCache(new MemoryCacheOptions());
            _mockConfig = new Mock<IConfiguration>();
        }

        private CurrencyService CreateService(HttpMessageHandler handler)
        {
            var httpClient = new HttpClient(handler)
            {
                BaseAddress = new Uri("https://api.frankfurter.dev")
            };
            return new CurrencyService(httpClient, _memoryCache, _mockConfig.Object, _mockLogger.Object);
        }

        [Fact]
        public async Task GetExchangeRateAsync_ValidResponse_ReturnsRateAndCaches()
        {
            // Arrange
            var mockHandler = new Mock<HttpMessageHandler>();
            mockHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>()
                )
                .ReturnsAsync(new HttpResponseMessage
                {
                    StatusCode = HttpStatusCode.OK,
                    Content = new StringContent("{\"date\":\"2026-10-04\",\"base\":\"LKR\",\"quote\":\"USD\",\"rate\":0.0033}")
                });

            var service = CreateService(mockHandler.Object);

            // Act
            var rate1 = await service.GetExchangeRateAsync("LKR", "USD");
            var rate2 = await service.GetExchangeRateAsync("LKR", "USD");

            // Assert
            Assert.Equal(0.0033m, rate1);
            Assert.Equal(0.0033m, rate2);

            // Verify handler was called only once (caching works)
            mockHandler.Protected().Verify(
                "SendAsync",
                Times.Once(),
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>()
            );
        }

        [Fact]
        public async Task GetExchangeRateAsync_InvalidResponse_ReturnsNull()
        {
            // Arrange
            var mockHandler = new Mock<HttpMessageHandler>();
            mockHandler.Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>()
                )
                .ReturnsAsync(new HttpResponseMessage
                {
                    StatusCode = HttpStatusCode.BadRequest,
                    Content = new StringContent("{\"message\":\"not found\"}")
                });

            var service = CreateService(mockHandler.Object);

            // Act
            var rate = await service.GetExchangeRateAsync("LKR", "USD");

            // Assert
            Assert.Null(rate);
        }
    }
}
