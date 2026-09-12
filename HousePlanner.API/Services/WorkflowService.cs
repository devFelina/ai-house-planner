using System.Collections.Concurrent;
using Microsoft.EntityFrameworkCore;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;

namespace HousePlanner.API.Services
{
    public class WorkflowService : IWorkflowService
    {
        private readonly IServiceScopeFactory _scopeFactory;
        private readonly ILogger<WorkflowService> _logger;
        private readonly ConcurrentDictionary<Guid, WorkflowSessionInfo> _activeWorkflows = new();

        public WorkflowService(IServiceScopeFactory scopeFactory, ILogger<WorkflowService> logger)
        {
            _scopeFactory = scopeFactory;
            _logger = logger;
        }

        public void SetWorkflowSession(WorkflowSessionInfo session)
        {
            _activeWorkflows[session.WorkflowId] = session;
        }

        public async Task<WorkflowSessionInfo?> GetWorkflowStatusAsync(Guid workflowId)
        {
            if (_activeWorkflows.TryGetValue(workflowId, out var session))
            {
                return session;
            }

            // Fallback: check if an approved project already exists in the database for this workflow
            using var scope = _scopeFactory.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

            var existingProject = await dbContext.Projects
                .AsNoTracking()
                .FirstOrDefaultAsync(p => p.WorkflowStateId == workflowId);

            if (existingProject != null)
            {
                var reconstructed = new WorkflowSessionInfo
                {
                    WorkflowId = workflowId,
                    Status = "approved",
                    ApprovalStatus = "approved",
                    ValidationPassed = true,
                    ProjectId = existingProject.Id,
                    CreatedAt = existingProject.CreatedAt,
                    UpdatedAt = existingProject.UpdatedAt
                };
                _activeWorkflows[workflowId] = reconstructed;
                return reconstructed;
            }

            return null;
        }

        public async Task<ApprovalServiceResult> ProcessApprovalAsync(
            Guid workflowId,
            ApprovalRequestDto request,
            string? userEmail = null,
            string? userRole = null)
        {
            // 1. Confirm the workflow exists
            var session = await GetWorkflowStatusAsync(workflowId);
            if (session == null)
            {
                _logger.LogWarning("Approval attempt failed: Workflow '{WorkflowId}' not found.", workflowId);
                return ApprovalServiceResult.NotFound($"Workflow with ID '{workflowId}' was not found.");
            }

            // 2. Prevent invalid duplicate approvals
            using var scope = _scopeFactory.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();

            var existingProject = await dbContext.Projects
                .AsNoTracking()
                .FirstOrDefaultAsync(p => p.WorkflowStateId == workflowId);

            if (existingProject != null || session.ApprovalStatus == "approved")
            {
                _logger.LogWarning("Duplicate approval attempt for Workflow '{WorkflowId}'. Project already exists: '{ProjectId}'",
                    workflowId, existingProject?.Id ?? session.ProjectId);
                return ApprovalServiceResult.Conflict($"Workflow '{workflowId}' has already been approved and a project has been created.");
            }

            // 3. Confirm the workflow is in the human approval stage
            if (session.Status != "awaiting_approval" && session.ApprovalStatus != "pending")
            {
                _logger.LogWarning("Approval rejected for Workflow '{WorkflowId}': Invalid status '{Status}'.",
                    workflowId, session.Status);
                return ApprovalServiceResult.InvalidState(
                    $"Workflow '{workflowId}' is not ready for human approval. Current status: '{session.Status}', approval status: '{session.ApprovalStatus}'.");
            }

            // 4. Confirm deterministic validation passed before allowing approval
            if (!session.ValidationPassed)
            {
                _logger.LogWarning("Approval rejected for Workflow '{WorkflowId}': Validation has not passed.", workflowId);
                return ApprovalServiceResult.ValidationFailed(
                    $"Cannot approve workflow '{workflowId}': Safety validation has not passed or is in a failed state.");
            }

            // 5. Normalize and apply requested decision
            var decision = request.Decision.Trim().ToLowerInvariant();

            switch (decision)
            {
                case "approve":
                case "approved":
                    // Create Project record atomically in database
                    var newProject = new Project
                    {
                        Id = Guid.NewGuid(),
                        WorkflowStateId = workflowId,
                        Status = "not_started",
                        CreatedAt = DateTimeOffset.UtcNow,
                        UpdatedAt = DateTimeOffset.UtcNow
                    };

                    dbContext.Projects.Add(newProject);
                    await dbContext.SaveChangesAsync();

                    session.Status = "approved";
                    session.ApprovalStatus = "approved";
                    session.ProjectId = newProject.Id;
                    session.UpdatedAt = DateTimeOffset.UtcNow;

                    _logger.LogInformation("Workflow '{WorkflowId}' successfully APPROVED. Created Project '{ProjectId}'.",
                        workflowId, newProject.Id);

                    return ApprovalServiceResult.Success(new ApprovalResponseDto
                    {
                        WorkflowId = workflowId,
                        Decision = "approved",
                        Status = "approved",
                        ProjectId = newProject.Id,
                        Message = "Workflow approved and construction project created successfully.",
                        Timestamp = DateTimeOffset.UtcNow
                    });

                case "reject":
                case "rejected":
                    session.Status = "rejected";
                    session.ApprovalStatus = "rejected";
                    session.RevisionNotes = request.RevisionNotes;
                    session.UpdatedAt = DateTimeOffset.UtcNow;

                    _logger.LogInformation("Workflow '{WorkflowId}' REJECTED.", workflowId);

                    return ApprovalServiceResult.Success(new ApprovalResponseDto
                    {
                        WorkflowId = workflowId,
                        Decision = "rejected",
                        Status = "rejected",
                        ProjectId = null,
                        Message = "Workflow has been rejected.",
                        Timestamp = DateTimeOffset.UtcNow
                    });

                case "request_revision":
                case "revision_requested":
                case "revision":
                    session.Status = "running";
                    session.ApprovalStatus = "revision_requested";
                    session.RevisionNotes = request.RevisionNotes;
                    session.RetryCount++;
                    session.UpdatedAt = DateTimeOffset.UtcNow;

                    _logger.LogInformation("Workflow '{WorkflowId}' REVISION REQUESTED (Retry count: {RetryCount}).",
                        workflowId, session.RetryCount);

                    return ApprovalServiceResult.Success(new ApprovalResponseDto
                    {
                        WorkflowId = workflowId,
                        Decision = "request_revision",
                        Status = "revision_requested",
                        ProjectId = null,
                        Message = "Revision requested. Workflow returned for design adjustments.",
                        Timestamp = DateTimeOffset.UtcNow
                    });

                default:
                    return ApprovalServiceResult.BadRequest(
                        $"Invalid approval decision '{request.Decision}'. Allowed values are: 'approve', 'reject', 'request_revision'.");
            }
        }
    }
}
