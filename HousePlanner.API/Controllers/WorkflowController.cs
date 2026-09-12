using Microsoft.AspNetCore.Mvc;
using HousePlanner.API.DTOs;
using HousePlanner.API.Services;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/[controller]s")] // Routes to /api/v1/workflows
    public class WorkflowController : ControllerBase
    {
        private readonly IWorkflowService _workflowService;
        private readonly ILogger<WorkflowController> _logger;

        public WorkflowController(IWorkflowService workflowService, ILogger<WorkflowController> logger)
        {
            _workflowService = workflowService;
            _logger = logger;
        }

        /// <summary>
        /// Retrieves the current execution status and validation outcome of a workflow session.
        /// </summary>
        /// <param name="id">Unique Workflow GUID</param>
        /// <returns>WorkflowStatusResponseDto</returns>
        [HttpGet("{id}/status")]
        [ProducesResponseType(typeof(WorkflowStatusResponseDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> GetStatus(Guid id)
        {
            var session = await _workflowService.GetWorkflowStatusAsync(id);
            if (session == null)
            {
                return NotFound(new { Message = $"Workflow with ID '{id}' was not found." });
            }

            var response = new WorkflowStatusResponseDto
            {
                WorkflowId = session.WorkflowId,
                Status = session.Status,
                ApprovalStatus = session.ApprovalStatus,
                ValidationPassed = session.ValidationPassed,
                RetryCount = session.RetryCount,
                RevisionNotes = session.RevisionNotes,
                ValidationResult = session.ValidationResult,
                ProjectId = session.ProjectId,
                CreatedAt = session.CreatedAt,
                UpdatedAt = session.UpdatedAt
            };

            return Ok(response);
        }

        /// <summary>
        /// Submits an authorized human approval decision (approve, reject, or request_revision)
        /// on a workflow proposal that has successfully passed deterministic validation.
        /// </summary>
        /// <param name="id">Unique Workflow GUID</param>
        /// <param name="request">Approval decision and optional revision notes</param>
        /// <returns>ApprovalResponseDto</returns>
        [HttpPost("{id}/approve")]
        [ProducesResponseType(typeof(ApprovalResponseDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        [ProducesResponseType(StatusCodes.Status409Conflict)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> Approve(Guid id, [FromBody] ApprovalRequestDto request)
        {
            if (!ModelState.IsValid)
            {
                return BadRequest(ModelState);
            }

            var result = await _workflowService.ProcessApprovalAsync(id, request);

            return result.Outcome switch
            {
                ApprovalOutcome.Success => Ok(result.Response),
                ApprovalOutcome.NotFound => NotFound(new { Message = result.ErrorMessage }),
                ApprovalOutcome.InvalidState => BadRequest(new { Message = result.ErrorMessage }),
                ApprovalOutcome.ValidationFailed => BadRequest(new { Message = result.ErrorMessage }),
                ApprovalOutcome.Conflict => Conflict(new { Message = result.ErrorMessage }),
                ApprovalOutcome.BadRequest => BadRequest(new { Message = result.ErrorMessage }),
                ApprovalOutcome.Unauthorized => Unauthorized(new { Message = result.ErrorMessage }),
                _ => StatusCode(StatusCodes.Status500InternalServerError, new { Message = "An unexpected error occurred." })
            };
        }
    }
}
