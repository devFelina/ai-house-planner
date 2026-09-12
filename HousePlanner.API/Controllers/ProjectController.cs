using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/projects")]
    public class ProjectController : ControllerBase
    {
        private readonly ApplicationDbContext _dbContext;
        private readonly ILogger<ProjectController> _logger;

        public ProjectController(ApplicationDbContext dbContext, ILogger<ProjectController> logger)
        {
            _dbContext = dbContext;
            _logger = logger;
        }

        /// <summary>
        /// Retrieves the project tracking and status details by project ID.
        /// </summary>
        [HttpGet("{id:guid}")]
        [ProducesResponseType(typeof(ProjectTrackingResponseDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> GetProjectById(Guid id)
        {
            var project = await _dbContext.Projects
                .Include(p => p.ConstructionPhases)
                .AsNoTracking()
                .FirstOrDefaultAsync(p => p.Id == id);

            if (project == null)
            {
                _logger.LogWarning("Project with ID '{ProjectId}' not found.", id);
                return NotFound(new { message = $"Project with ID '{id}' was not found." });
            }

            var response = new ProjectTrackingResponseDto
            {
                ProjectId = project.Id,
                Status = project.Status,
                ContractorName = null, // Component D boundary: contractor assignment not in scope
                Phases = project.ConstructionPhases
                    .OrderBy(cp => cp.SequenceOrder)
                    .Select(cp => new PhaseTrackingDto
                    {
                        PhaseName = cp.PhaseName,
                        Status = cp.Status,
                        StartedAtUtc = cp.StartedAt,
                        CompletedAtUtc = cp.CompletedAt,
                        SequenceOrder = cp.SequenceOrder
                    })
                    .ToList()
            };

            return Ok(response);
        }

        /// <summary>
        /// Retrieves project tracking details by project ID (alias for tracking).
        /// </summary>
        [HttpGet("{id:guid}/tracking")]
        [ProducesResponseType(typeof(ProjectTrackingResponseDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public Task<IActionResult> GetProjectTracking(Guid id)
        {
            return GetProjectById(id);
        }

        /// <summary>
        /// Retrieves project tracking details by the originating workflow ID.
        /// </summary>
        [HttpGet("by-workflow/{workflowId:guid}")]
        [ProducesResponseType(typeof(ProjectTrackingResponseDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> GetProjectByWorkflowId(Guid workflowId)
        {
            var project = await _dbContext.Projects
                .Include(p => p.ConstructionPhases)
                .AsNoTracking()
                .FirstOrDefaultAsync(p => p.WorkflowStateId == workflowId);

            if (project == null)
            {
                _logger.LogWarning("Project for Workflow '{WorkflowId}' not found.", workflowId);
                return NotFound(new { message = $"No project found for workflow ID '{workflowId}'." });
            }

            var response = new ProjectTrackingResponseDto
            {
                ProjectId = project.Id,
                Status = project.Status,
                ContractorName = null,
                Phases = project.ConstructionPhases
                    .OrderBy(cp => cp.SequenceOrder)
                    .Select(cp => new PhaseTrackingDto
                    {
                        PhaseName = cp.PhaseName,
                        Status = cp.Status,
                        StartedAtUtc = cp.StartedAt,
                        CompletedAtUtc = cp.CompletedAt,
                        SequenceOrder = cp.SequenceOrder
                    })
                    .ToList()
            };

            return Ok(response);
        }
    }
}
