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
    public class WorkflowApprovalTests
    {
        private (WorkflowService service, ApplicationDbContext dbContext, ServiceProvider provider) CreateTestEnvironment(string dbName)
        {
            var services = new ServiceCollection();

            services.AddDbContext<ApplicationDbContext>(options =>
                options.UseInMemoryDatabase(databaseName: dbName));

            var provider = services.BuildServiceProvider();
            var scopeFactory = provider.GetRequiredService<IServiceScopeFactory>();
            var dbContext = provider.GetRequiredService<ApplicationDbContext>();

            var service = new WorkflowService(scopeFactory, NullLogger<WorkflowService>.Instance);

            return (service, dbContext, provider);
        }

        [Fact]
        public async Task ApproveWorkflow_ValidProposalPassedValidation_CreatesProjectAndReturnsSuccess()
        {
            // Arrange
            var (service, dbContext, _) = CreateTestEnvironment(nameof(ApproveWorkflow_ValidProposalPassedValidation_CreatesProjectAndReturnsSuccess));
            var workflowId = Guid.NewGuid();

            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = true,
                ValidationResult = new { Passed = true }
            });

            var request = new ApprovalRequestDto
            {
                Decision = "approve"
            };

            // Act
            var result = await service.ProcessApprovalAsync(workflowId, request);

            // Assert
            Assert.Equal(ApprovalOutcome.Success, result.Outcome);
            Assert.NotNull(result.Response);
            Assert.Equal(workflowId, result.Response.WorkflowId);
            Assert.Equal("approved", result.Response.Decision);
            Assert.Equal("approved", result.Response.Status);
            Assert.NotNull(result.Response.ProjectId);

            // Verify Project record exists in ApplicationDbContext
            var createdProject = await dbContext.Projects.FirstOrDefaultAsync(p => p.WorkflowStateId == workflowId);
            Assert.NotNull(createdProject);
            Assert.Equal(result.Response.ProjectId, createdProject.Id);
            Assert.Equal("not_started", createdProject.Status);
        }

        [Fact]
        public async Task ApproveWorkflow_ValidationFailed_RejectsApprovalAndDoesNotCreateProject()
        {
            // Arrange
            var (service, dbContext, _) = CreateTestEnvironment(nameof(ApproveWorkflow_ValidationFailed_RejectsApprovalAndDoesNotCreateProject));
            var workflowId = Guid.NewGuid();

            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = false, // Validation has NOT passed
                ValidationResult = new { Passed = false, Error = "Ground coverage exceeds 65%" }
            });

            var request = new ApprovalRequestDto
            {
                Decision = "approve"
            };

            // Act
            var result = await service.ProcessApprovalAsync(workflowId, request);

            // Assert
            Assert.Equal(ApprovalOutcome.ValidationFailed, result.Outcome);
            Assert.Contains("Safety validation has not passed", result.ErrorMessage);

            // Verify NO Project was created
            var project = await dbContext.Projects.FirstOrDefaultAsync(p => p.WorkflowStateId == workflowId);
            Assert.Null(project);
        }

        [Fact]
        public async Task ApproveWorkflow_WorkflowNotFound_ReturnsNotFound()
        {
            // Arrange
            var (service, _, _) = CreateTestEnvironment(nameof(ApproveWorkflow_WorkflowNotFound_ReturnsNotFound));
            var nonExistentId = Guid.NewGuid();

            var request = new ApprovalRequestDto { Decision = "approve" };

            // Act
            var result = await service.ProcessApprovalAsync(nonExistentId, request);

            // Assert
            Assert.Equal(ApprovalOutcome.NotFound, result.Outcome);
            Assert.Contains("was not found", result.ErrorMessage);
        }

        [Fact]
        public async Task ApproveWorkflow_InvalidStatusNotAwaitingApproval_ReturnsInvalidState()
        {
            // Arrange
            var (service, _, _) = CreateTestEnvironment(nameof(ApproveWorkflow_InvalidStatusNotAwaitingApproval_ReturnsInvalidState));
            var workflowId = Guid.NewGuid();

            // Status is still running
            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "running",
                ApprovalStatus = "not_requested",
                ValidationPassed = false
            });

            var request = new ApprovalRequestDto { Decision = "approve" };

            // Act
            var result = await service.ProcessApprovalAsync(workflowId, request);

            // Assert
            Assert.Equal(ApprovalOutcome.InvalidState, result.Outcome);
            Assert.Contains("not ready for human approval", result.ErrorMessage);
        }

        [Fact]
        public async Task ApproveWorkflow_RevisionRequested_UpdatesStateAndDoesNotCreateProject()
        {
            // Arrange
            var (service, dbContext, _) = CreateTestEnvironment(nameof(ApproveWorkflow_RevisionRequested_UpdatesStateAndDoesNotCreateProject));
            var workflowId = Guid.NewGuid();

            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = true,
                RetryCount = 0
            });

            var request = new ApprovalRequestDto
            {
                Decision = "request_revision",
                RevisionNotes = "Please reduce cost by LKR 500,000."
            };

            // Act
            var result = await service.ProcessApprovalAsync(workflowId, request);

            // Assert
            Assert.Equal(ApprovalOutcome.Success, result.Outcome);
            Assert.NotNull(result.Response);
            Assert.Equal("request_revision", result.Response.Decision);
            Assert.Equal("revision_requested", result.Response.Status);
            Assert.Null(result.Response.ProjectId);

            // Verify session mutated
            var session = await service.GetWorkflowStatusAsync(workflowId);
            Assert.NotNull(session);
            Assert.Equal("running", session.Status);
            Assert.Equal("revision_requested", session.ApprovalStatus);
            Assert.Equal(1, session.RetryCount);
            Assert.Equal("Please reduce cost by LKR 500,000.", session.RevisionNotes);

            // Verify NO Project created
            var project = await dbContext.Projects.FirstOrDefaultAsync(p => p.WorkflowStateId == workflowId);
            Assert.Null(project);
        }

        [Fact]
        public async Task ApproveWorkflow_Rejected_UpdatesStateAndDoesNotCreateProject()
        {
            // Arrange
            var (service, dbContext, _) = CreateTestEnvironment(nameof(ApproveWorkflow_Rejected_UpdatesStateAndDoesNotCreateProject));
            var workflowId = Guid.NewGuid();

            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = true
            });

            var request = new ApprovalRequestDto
            {
                Decision = "reject",
                RevisionNotes = "Client decided not to proceed."
            };

            // Act
            var result = await service.ProcessApprovalAsync(workflowId, request);

            // Assert
            Assert.Equal(ApprovalOutcome.Success, result.Outcome);
            Assert.NotNull(result.Response);
            Assert.Equal("rejected", result.Response.Decision);
            Assert.Equal("rejected", result.Response.Status);
            Assert.Null(result.Response.ProjectId);

            // Verify session mutated
            var session = await service.GetWorkflowStatusAsync(workflowId);
            Assert.NotNull(session);
            Assert.Equal("rejected", session.Status);
            Assert.Equal("rejected", session.ApprovalStatus);

            // Verify NO Project created
            var project = await dbContext.Projects.FirstOrDefaultAsync(p => p.WorkflowStateId == workflowId);
            Assert.Null(project);
        }

        [Fact]
        public async Task ApproveWorkflow_DuplicateApprovalAttempt_ReturnsConflict()
        {
            // Arrange
            var (service, _, _) = CreateTestEnvironment(nameof(ApproveWorkflow_DuplicateApprovalAttempt_ReturnsConflict));
            var workflowId = Guid.NewGuid();

            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = true
            });

            var request = new ApprovalRequestDto { Decision = "approve" };

            // First approval succeeds
            var firstResult = await service.ProcessApprovalAsync(workflowId, request);
            Assert.Equal(ApprovalOutcome.Success, firstResult.Outcome);

            // Second approval attempt on the same workflow
            var secondResult = await service.ProcessApprovalAsync(workflowId, request);

            // Assert conflict
            Assert.Equal(ApprovalOutcome.Conflict, secondResult.Outcome);
            Assert.Contains("has already been approved", secondResult.ErrorMessage);
        }

        [Fact]
        public async Task ApproveWorkflow_InvalidDecision_ReturnsBadRequest()
        {
            // Arrange
            var (service, _, _) = CreateTestEnvironment(nameof(ApproveWorkflow_InvalidDecision_ReturnsBadRequest));
            var workflowId = Guid.NewGuid();

            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = true
            });

            var request = new ApprovalRequestDto { Decision = "invalid_decision" };

            // Act
            var result = await service.ProcessApprovalAsync(workflowId, request);

            // Assert
            Assert.Equal(ApprovalOutcome.BadRequest, result.Outcome);
            Assert.Contains("Invalid approval decision", result.ErrorMessage);
        }

        [Fact]
        public async Task WorkflowController_ApproveAndGetStatus_ReturnsCorrectActionResults()
        {
            // Arrange
            var (service, _, _) = CreateTestEnvironment(nameof(WorkflowController_ApproveAndGetStatus_ReturnsCorrectActionResults));
            var controller = new WorkflowController(service, NullLogger<WorkflowController>.Instance);
            var workflowId = Guid.NewGuid();

            service.SetWorkflowSession(new WorkflowSessionInfo
            {
                WorkflowId = workflowId,
                Status = "awaiting_approval",
                ApprovalStatus = "pending",
                ValidationPassed = true,
                ValidationResult = new { Passed = true, RuleCount = 4 }
            });

            // 1. Test GET /api/v1/workflows/{id}/status
            var statusResult = await controller.GetStatus(workflowId);
            var okStatus = Assert.IsType<OkObjectResult>(statusResult);
            var statusDto = Assert.IsType<WorkflowStatusResponseDto>(okStatus.Value);
            Assert.Equal("awaiting_approval", statusDto.Status);
            Assert.True(statusDto.ValidationPassed);

            // 2. Test POST /api/v1/workflows/{id}/approve
            var approveResult = await controller.Approve(workflowId, new ApprovalRequestDto { Decision = "approve" });
            var okApprove = Assert.IsType<OkObjectResult>(approveResult);
            var approveDto = Assert.IsType<ApprovalResponseDto>(okApprove.Value);
            Assert.Equal("approved", approveDto.Status);
            Assert.NotNull(approveDto.ProjectId);

            // 3. Test GET for non-existent workflow returns 404
            var notFoundResult = await controller.GetStatus(Guid.NewGuid());
            Assert.IsType<NotFoundObjectResult>(notFoundResult);
        }
    }
}
