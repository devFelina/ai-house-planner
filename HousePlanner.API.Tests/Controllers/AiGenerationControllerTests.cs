using HousePlanner.API.Controllers;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;
using HousePlanner.API.Services;
using HousePlanner.API.Models;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Moq;
using Moq.Protected;
using System.Net;
using System.Text.Json;
using Xunit;

namespace HousePlanner.API.Tests.Controllers
{
    public class AiGenerationControllerTests
    {
        private readonly ApplicationDbContext _dbContext;
        private readonly AiGenerationController _controller;
        private readonly Mock<HttpMessageHandler> _mockHttpMessageHandler;
        private readonly Mock<IDesignOptionsService> _mockDesignOptionsService;
        private readonly Guid _clientId = Guid.NewGuid();

        public AiGenerationControllerTests()
        {
            var options = new DbContextOptionsBuilder<ApplicationDbContext>()
                .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
                .Options;

            _dbContext = new ApplicationDbContext(options);

            // Add a mock client to avoid foreign key/user null checks
            _dbContext.Users.Add(new User { Id = _clientId, Email = "test@example.com", FullName = "Test User", PasswordHash = "dummy" });
            _dbContext.SaveChanges();

            _mockHttpMessageHandler = new Mock<HttpMessageHandler>();
            var httpClient = new HttpClient(_mockHttpMessageHandler.Object)
            {
                BaseAddress = new Uri("http://localhost:8001")
            };

            var httpClientFactory = new Mock<IHttpClientFactory>();
            httpClientFactory.Setup(f => f.CreateClient("AgenticService")).Returns(httpClient);

            _mockDesignOptionsService = new Mock<IDesignOptionsService>();

            var currentUser = new Mock<ICurrentUserContextService>();
            currentUser.Setup(x => x.GetAsync(It.IsAny<HttpContext>()))
                .ReturnsAsync(new CurrentUserContext(_clientId, "test@example.com", "Customer"));
            _controller = new AiGenerationController(_dbContext, httpClientFactory.Object, _mockDesignOptionsService.Object, currentUser.Object)
            {
                ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() }
            };
        }

        [Fact]
        public async Task Generate_IgnoresSpoofedClientIdAndUsesAuthenticatedCustomer()
        {
            var otherCustomer = new User { Id = Guid.NewGuid(), Email = "other@example.com", FullName = "Other" };
            _dbContext.Users.Add(otherCustomer);
            await _dbContext.SaveChangesAsync();
            var request = new StartDesignRequest
            {
                LandSizeCategory = "medium",
                LandSizePerches = 15,
                Bedrooms = 3,
                Bathrooms = 2,
                HouseType = "modern"
            };
            _mockDesignOptionsService.Setup(s => s.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(new DesignOptionsValidationResult { IsValid = true });
            _mockHttpMessageHandler.Protected()
                .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK));

            Assert.IsType<OkObjectResult>(await _controller.Generate(request, CancellationToken.None));
            var submission = await _dbContext.LandSubmissions.SingleAsync();
            Assert.Equal(_clientId, submission.ClientId);
            Assert.NotEqual(otherCustomer.Id, submission.ClientId);
            Assert.Equal(submission.Id, (await _dbContext.WorkflowStates.SingleAsync()).LandSubmissionId);
        }

        [Fact]
        public async Task Generate_HappyPath_CreatesWorkflowAndReturns200()
        {
            // Arrange
            var req = new StartDesignRequest
            {
                LandSizeCategory = "medium",
                LandSizePerches = 15,
                Bedrooms = 3,
                Bathrooms = 2,
                HouseType = "Modern Minimalist"
            };

            _mockDesignOptionsService.Setup(s => s.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(new DesignOptionsValidationResult { IsValid = true });

            _mockHttpMessageHandler.Protected()
                .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage { StatusCode = HttpStatusCode.OK });

            // Act
            var result = await _controller.Generate(req, CancellationToken.None);

            // Assert
            var okResult = Assert.IsType<OkObjectResult>(result);
            var response = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(okResult.Value));
            Assert.True(response.TryGetProperty("WorkflowId", out var workflowIdProp));

            var workflowId = workflowIdProp.GetGuid();
            var workflow = await _dbContext.WorkflowStates.FindAsync(workflowId);
            Assert.NotNull(workflow);
            Assert.Equal("running", workflow.Status);
        }

        [Fact]
        public async Task Generate_DuplicateActiveRequest_ReusesWorkflowWithoutSecondAgentCall()
        {
            var request = new StartDesignRequest
            {
                LandSizeCategory = "medium", LandSizePerches = 15,
                Bedrooms = 3, Bathrooms = 2, HouseType = "modern"
            };
            _mockDesignOptionsService
                .Setup(s => s.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(new DesignOptionsValidationResult { IsValid = true });
            _mockHttpMessageHandler.Protected()
                .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK));

            var first = Assert.IsType<OkObjectResult>(await _controller.Generate(request, CancellationToken.None));
            var duplicate = Assert.IsType<OkObjectResult>(await _controller.Generate(request, CancellationToken.None));
            var firstJson = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(first.Value));
            var duplicateJson = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(duplicate.Value));

            Assert.Equal(firstJson.GetProperty("WorkflowId").GetGuid(), duplicateJson.GetProperty("WorkflowId").GetGuid());
            Assert.True(duplicateJson.GetProperty("Reused").GetBoolean());
            Assert.Single(_dbContext.WorkflowStates);
            Assert.Single(_dbContext.LandSubmissions);
            _mockHttpMessageHandler.Protected().Verify(
                "SendAsync",
                Times.Once(),
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>());
        }

        [Fact]
        public async Task Generate_CompletedWorkflow_AllowsNewGeneration()
        {
            var request = new StartDesignRequest
            {
                LandSizeCategory = "medium", LandSizePerches = 15,
                Bedrooms = 3, Bathrooms = 2, HouseType = "modern"
            };
            _mockDesignOptionsService
                .Setup(s => s.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(new DesignOptionsValidationResult { IsValid = true });
            _mockHttpMessageHandler.Protected()
                .Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK));

            Assert.IsType<OkObjectResult>(await _controller.Generate(request, CancellationToken.None));
            var firstWorkflow = await _dbContext.WorkflowStates.SingleAsync();
            firstWorkflow.Status = "approved";
            await _dbContext.SaveChangesAsync();

            Assert.IsType<OkObjectResult>(await _controller.Generate(request, CancellationToken.None));

            Assert.Equal(2, await _dbContext.WorkflowStates.CountAsync());
            Assert.Equal(2, await _dbContext.LandSubmissions.CountAsync());
            _mockHttpMessageHandler.Protected().Verify(
                "SendAsync",
                Times.Exactly(2),
                ItExpr.IsAny<HttpRequestMessage>(),
                ItExpr.IsAny<CancellationToken>());
        }

        [Fact]
        public async Task Generate_UnsupportedConfiguration_Returns400WithSuggestions()
        {
            // Arrange
            var req = new StartDesignRequest
            {
                LandSizeCategory = "medium",
                LandSizePerches = 15,
                Bedrooms = 3,
                Bathrooms = 2,
                HouseType = "modern"
            };

            var validationResult = new DesignOptionsValidationResult
            {
                IsValid = false,
                ErrorCode = "UNSUPPORTED_DESIGN_CONFIGURATION",
                Conflicts = new List<string> { "parking" },
                Suggestions = new List<SuggestionDto> {
                    new SuggestionDto("parkingRequired", false, "Remove parking")
                }
            };

            _mockDesignOptionsService.Setup(s => s.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(validationResult);

            // Act
            var result = await _controller.Generate(req, CancellationToken.None);

            // Assert
            var badRequest = Assert.IsType<BadRequestObjectResult>(result);
            var response = JsonSerializer.Deserialize<JsonElement>(JsonSerializer.Serialize(badRequest.Value));

            Assert.Equal("UNSUPPORTED_DESIGN_CONFIGURATION", response.GetProperty("code").GetString());
            var conflicts = response.GetProperty("conflicts").EnumerateArray().Select(e => e.GetString()).ToList();
            Assert.Contains("parking", conflicts);

            var suggestions = response.GetProperty("suggestions").EnumerateArray();
            Assert.Equal("parkingRequired", suggestions.First().GetProperty("field").GetString());

            // Ensure no workflow was created in DB
            Assert.Empty(_dbContext.WorkflowStates);
        }



        [Fact]
        public async Task Generate_AssignsLandSubmissionToAuthenticatedUser()
        {
            var request = new StartDesignRequest { LandSizeCategory = "medium", LandSizePerches = 15, Bedrooms = 3, Bathrooms = 2, HouseType = "modern" };
            _mockDesignOptionsService.Setup(x => x.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(new DesignOptionsValidationResult { IsValid = true });
            _mockHttpMessageHandler.Protected().Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK));

            var result = await _controller.Generate(request, CancellationToken.None);

            Assert.IsType<OkObjectResult>(result);
            var submission = await _dbContext.LandSubmissions.SingleAsync();
            Assert.Equal(_clientId, submission.ClientId);
        }

        [Fact]
        public async Task Generate_DoesNotUseFirstDatabaseUser()
        {
            var oldUser = new User { Id = Guid.NewGuid(), Email = "oldest@example.com", FullName = "Old User", CreatedAt = DateTimeOffset.MinValue };
            _dbContext.Users.Add(oldUser);
            await _dbContext.SaveChangesAsync();

            var request = new StartDesignRequest { LandSizeCategory = "medium", LandSizePerches = 15, Bedrooms = 3, Bathrooms = 2, HouseType = "modern" };
            _mockDesignOptionsService.Setup(x => x.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(new DesignOptionsValidationResult { IsValid = true });
            _mockHttpMessageHandler.Protected().Setup<Task<HttpResponseMessage>>("SendAsync", ItExpr.IsAny<HttpRequestMessage>(), ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage(HttpStatusCode.OK));

            var result = await _controller.Generate(request, CancellationToken.None);

            Assert.IsType<OkObjectResult>(result);
            var submission = await _dbContext.LandSubmissions.SingleAsync();
            Assert.Equal(_clientId, submission.ClientId);
            Assert.NotEqual(oldUser.Id, submission.ClientId);
        }

        [Fact]
        public async Task Generate_MissingApplicationUser_DoesNotFallbackToAnotherUser()
        {
            var oldUser = new User { Id = Guid.NewGuid(), Email = "oldest@example.com", FullName = "Old User", CreatedAt = DateTimeOffset.MinValue };
            _dbContext.Users.Add(oldUser);
            await _dbContext.SaveChangesAsync();

            // Simulate missing authenticated user
            var currentUser = new Mock<ICurrentUserContextService>();
            currentUser.Setup(x => x.GetAsync(It.IsAny<HttpContext>())).ReturnsAsync((CurrentUserContext?)null);

            var localController = new AiGenerationController(_dbContext, new Mock<IHttpClientFactory>().Object, _mockDesignOptionsService.Object, currentUser.Object)
            {
                ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() }
            };

            var request = new StartDesignRequest { LandSizeCategory = "medium", LandSizePerches = 15, Bedrooms = 3, Bathrooms = 2, HouseType = "modern" };
            _mockDesignOptionsService.Setup(x => x.ValidateFinalSelectionAsync(It.IsAny<HouseRequirement>(), It.IsAny<CancellationToken>()))
                .ReturnsAsync(new DesignOptionsValidationResult { IsValid = true });

            var result = await localController.Generate(request, CancellationToken.None);

            var unauthorizedResult = Assert.IsType<UnauthorizedObjectResult>(result);
            Assert.Empty(_dbContext.LandSubmissions);
        }
    }
}
