using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using HousePlanner.API.Controllers;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using HousePlanner.API.Services;
using Xunit;

namespace HousePlanner.API.Tests
{
    public class ProjectTrackingTests
    {
        private (ProjectController projectController, WorkflowService workflowService, ApplicationDbContext dbContext) CreateTestEnvironment(string dbName)
        {
            var services = new ServiceCollection();
            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseInMemoryDatabase(databaseName: dbName));

            var provider = services.BuildServiceProvider();
            var scopeFactory = provider.GetRequiredService<IServiceScopeFactory>();
            var dbContext = provider.GetRequiredService<ApplicationDbContext>();

            var workflowService = new WorkflowService(scopeFactory, NullLogger<WorkflowService>.Instance);
            var projectController = new ProjectController(dbContext, NullLogger<ProjectController>.Instance);

            return (projectController, workflowService, dbContext);
        }

        [Fact]
        public async Task GetProjectById_ExistingProject_ReturnsProjectTrackingDetails()
        {
            // Arrange
            var (controller, _, dbContext) = CreateTestEnvironment(nameof(GetProjectById_ExistingProject_ReturnsProjectTrackingDetails));
            var projectId = Guid.NewGuid();
            var workflowId = Guid.NewGuid();

            var project = new Project
            {
                Id = projectId,
                WorkflowStateId = workflowId,
                Status = "not_started",
                CreatedAt = DateTimeOffset.UtcNow,
                UpdatedAt = DateTimeOffset.UtcNow
            };

            dbContext.Projects.Add(project);
            await dbContext.SaveChangesAsync();

            // Act
            var result = await controller.GetProjectById(projectId);

            // Assert
            var okResult = Assert.IsType<OkObjectResult>(result);
            var response = Assert.IsType<ProjectTrackingResponseDto>(okResult.Value);
            Assert.Equal(projectId, response.ProjectId);
            Assert.Equal("not_started", response.Status);
            Assert.Null(response.ContractorName);
            Assert.Empty(response.Phases);
        }

        [Fact]
        public async Task GetProjectTracking_ExistingProject_ReturnsTrackingAlias()
        {
            // Arrange
            var (controller, _, dbContext) = CreateTestEnvironment(nameof(GetProjectTracking_ExistingProject_ReturnsTrackingAlias));
            var projectId = Guid.NewGuid();

            var project = new Project
            {
                Id = projectId,
                WorkflowStateId = Guid.NewGuid(),
                Status = "not_started",
                CreatedAt = DateTimeOffset.UtcNow,
                UpdatedAt = DateTimeOffset.UtcNow
            };

            dbContext.Projects.Add(project);
            await dbContext.SaveChangesAsync();

            // Act
            var result = await controller.GetProjectTracking(projectId);

            // Assert
            var okResult = Assert.IsType<OkObjectResult>(result);
            var response = Assert.IsType<ProjectTrackingResponseDto>(okResult.Value);
            Assert.Equal(projectId, response.ProjectId);
        }

        [Fact]
        public async Task GetProjectByWorkflowId_ExistingProject_ReturnsProjectTracking()
        {
            // Arrange
            var (controller, _, dbContext) = CreateTestEnvironment(nameof(GetProjectByWorkflowId_ExistingProject_ReturnsProjectTracking));
            var projectId = Guid.NewGuid();
            var workflowId = Guid.NewGuid();

            var project = new Project
            {
                Id = projectId,
                WorkflowStateId = workflowId,
                Status = "not_started",
                CreatedAt = DateTimeOffset.UtcNow,
                UpdatedAt = DateTimeOffset.UtcNow
            };

            dbContext.Projects.Add(project);
            await dbContext.SaveChangesAsync();

            // Act
            var result = await controller.GetProjectByWorkflowId(workflowId);

            // Assert
            var okResult = Assert.IsType<OkObjectResult>(result);
            var response = Assert.IsType<ProjectTrackingResponseDto>(okResult.Value);
            Assert.Equal(projectId, response.ProjectId);
            Assert.Equal("not_started", response.Status);
        }

        [Fact]
        public async Task GetProjectById_NonExistentProject_ReturnsNotFound()
        {
            // Arrange
            var (controller, _, _) = CreateTestEnvironment(nameof(GetProjectById_NonExistentProject_ReturnsNotFound));
            var nonExistentId = Guid.NewGuid();

            // Act
            var result = await controller.GetProjectById(nonExistentId);

            // Assert
            Assert.IsType<NotFoundObjectResult>(result);
        }

        [Fact]
        public async Task GetProjectByWorkflowId_NonExistentWorkflow_ReturnsNotFound()
        {
            // Arrange
            var (controller, _, _) = CreateTestEnvironment(nameof(GetProjectByWorkflowId_NonExistentWorkflow_ReturnsNotFound));
            var nonExistentWorkflowId = Guid.NewGuid();

            // Act
            var result = await controller.GetProjectByWorkflowId(nonExistentWorkflowId);

            // Assert
            Assert.IsType<NotFoundObjectResult>(result);
        }

        [Fact]
        public async Task FullEndToEndFlow_ValidationPass_Approve_CreatesProject_ProjectStatusRetrievable()
        {
            // Arrange
            var (controller, workflowService, _) = CreateTestEnvironment(nameof(FullEndToEndFlow_ValidationPass_Approve_CreatesProject_ProjectStatusRetrievable));
            var workflowId = Guid.NewGuid();

            // 1. Setup workflow in awaiting_approval state with validation passed
            workflowService.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = true,
                ValidationResult = new
                {
                    GroundCoverage = "PASS",
                    TerrainFoundation = "PASS",
                    BudgetTolerance = "PASS",
                    RoomPreferences = "PASS"
                }
            });

            // 2. Submit approval decision
            var approvalResult = await workflowService.ProcessApprovalAsync(workflowId, new ApprovalRequestDto { Decision = "approve" });
            Assert.Equal(ApprovalOutcome.Success, approvalResult.Outcome);
            Assert.NotNull(approvalResult.Response?.ProjectId);

            var createdProjectId = approvalResult.Response.ProjectId.Value;

            // 3. Query project status via ProjectController using ProjectId
            var statusResult = await controller.GetProjectById(createdProjectId);
            var okResult = Assert.IsType<OkObjectResult>(statusResult);
            var projectDto = Assert.IsType<ProjectTrackingResponseDto>(okResult.Value);

            Assert.Equal(createdProjectId, projectDto.ProjectId);
            Assert.Equal("not_started", projectDto.Status);

            // 4. Query project status via ProjectController using WorkflowId
            var workflowLookupResult = await controller.GetProjectByWorkflowId(workflowId);
            var okLookupResult = Assert.IsType<OkObjectResult>(workflowLookupResult);
            var lookupDto = Assert.IsType<ProjectTrackingResponseDto>(okLookupResult.Value);

            Assert.Equal(createdProjectId, lookupDto.ProjectId);
            Assert.Equal("not_started", lookupDto.Status);
        }
    }
}
