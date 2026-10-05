using System;
using System.Collections.Generic;
using Microsoft.Extensions.Configuration;
using Xunit;

namespace HousePlanner.API.Tests
{
    public class AgenticServiceConfigurationTests
    {
        [Fact]
        public void InternalApiKey_ConfigurationTakesPrecedence()
        {
            // Arrange
            var inMemorySettings = new Dictionary<string, string> {
                {"AgenticService:InternalApiKey", "config-key"}
            };
            IConfiguration configuration = new ConfigurationBuilder()
                .AddInMemoryCollection(inMemorySettings)
                .Build();

            // Act
            var key = configuration["AgenticService:InternalApiKey"];
            if (string.IsNullOrWhiteSpace(key))
            {
                key = Environment.GetEnvironmentVariable("AGENTIC_INTERNAL_API_KEY");
            }

            // Assert
            Assert.Equal("config-key", key);
        }

        [Fact]
        public void InternalApiKey_EmptyConfigurationFallsBackToEnvironment()
        {
            // Arrange
            var inMemorySettings = new Dictionary<string, string> {
                {"AgenticService:InternalApiKey", ""}
            };
            IConfiguration configuration = new ConfigurationBuilder()
                .AddInMemoryCollection(inMemorySettings)
                .Build();

            Environment.SetEnvironmentVariable("AGENTIC_INTERNAL_API_KEY", "env-key");

            try
            {
                // Act
                var key = configuration["AgenticService:InternalApiKey"];
                if (string.IsNullOrWhiteSpace(key))
                {
                    key = Environment.GetEnvironmentVariable("AGENTIC_INTERNAL_API_KEY");
                }

                // Assert
                Assert.Equal("env-key", key);
            }
            finally
            {
                Environment.SetEnvironmentVariable("AGENTIC_INTERNAL_API_KEY", null);
            }
        }

        [Fact]
        public void BaseUrl_CanBeSuppliedThroughEnvironmentMapping()
        {
            // Arrange
            Environment.SetEnvironmentVariable("AgenticService__BaseUrl", "https://production.onrender.com");

            IConfiguration configuration = new ConfigurationBuilder()
                .AddEnvironmentVariables()
                .Build();

            try
            {
                // Act
                var baseUrl = configuration["AgenticService:BaseUrl"];

                // Assert
                Assert.Equal("https://production.onrender.com", baseUrl);
            }
            finally
            {
                Environment.SetEnvironmentVariable("AgenticService__BaseUrl", null);
            }
        }
    }
}
