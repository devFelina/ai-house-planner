using HousePlanner.API.DTOs;
using HousePlanner.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/constructor/workflow/projects/{projectId}/logs")]
[Authorize(Roles = "Constructor")]
public class ConstructorLogbookController : ControllerBase
{
    private readonly IDailyConstructionLogService _logService;
    private readonly ICurrentUserContextService _currentUserContext;

    public ConstructorLogbookController(IDailyConstructionLogService logService, ICurrentUserContextService currentUserContext)
    {
        _logService = logService;
        _currentUserContext = currentUserContext;
    }

    [HttpGet]
    public async Task<IActionResult> GetLogs(Guid projectId, CancellationToken cancellationToken)
    {
        var user = await _currentUserContext.GetAsync(HttpContext);
        if (user?.Id == null) return Unauthorized();

        try
        {
            var logs = await _logService.GetLogsAsync(projectId, user.Id.Value, cancellationToken);
            return Ok(logs);
        }
        catch (UnauthorizedAccessException)
        {
            return NotFound();
        }
    }

    [HttpGet("{logId}")]
    public async Task<IActionResult> GetLog(Guid projectId, Guid logId, CancellationToken cancellationToken)
    {
        var user = await _currentUserContext.GetAsync(HttpContext);
        if (user?.Id == null) return Unauthorized();

        try
        {
            var log = await _logService.GetLogAsync(projectId, logId, user.Id.Value, cancellationToken);
            if (log == null) return NotFound();
            return Ok(log);
        }
        catch (UnauthorizedAccessException)
        {
            return NotFound();
        }
    }

    [HttpPost]
    public async Task<IActionResult> CreateLog(Guid projectId, [FromBody] CreateDailyConstructionLogRequest request, CancellationToken cancellationToken)
    {
        var user = await _currentUserContext.GetAsync(HttpContext);
        if (user?.Id == null) return Unauthorized();

        try
        {
            var log = await _logService.CreateLogAsync(projectId, user.Id.Value, request, cancellationToken);
            return Ok(log);
        }
        catch (UnauthorizedAccessException)
        {
            return NotFound();
        }
        catch (InvalidOperationException ex) when (ex.Message == "project_completed_logbook_read_only")
        {
            return StatusCode(409, ex.Message);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpPut("{logId}")]
    public async Task<IActionResult> UpdateLog(Guid projectId, Guid logId, [FromBody] UpdateDailyConstructionLogRequest request, CancellationToken cancellationToken)
    {
        var user = await _currentUserContext.GetAsync(HttpContext);
        if (user?.Id == null) return Unauthorized();

        try
        {
            var log = await _logService.UpdateLogAsync(projectId, logId, user.Id.Value, request, cancellationToken);
            return Ok(log);
        }
        catch (UnauthorizedAccessException)
        {
            return NotFound();
        }
        catch (InvalidOperationException ex) when (ex.Message == "project_completed_logbook_read_only")
        {
            return StatusCode(409, ex.Message);
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
        catch (ArgumentException ex)
        {
            return BadRequest(ex.Message);
        }
    }

    [HttpDelete("{logId}")]
    public async Task<IActionResult> DeleteLog(Guid projectId, Guid logId, CancellationToken cancellationToken)
    {
        var user = await _currentUserContext.GetAsync(HttpContext);
        if (user?.Id == null) return Unauthorized();

        try
        {
            await _logService.DeleteLogAsync(projectId, logId, user.Id.Value, cancellationToken);
            return NoContent();
        }
        catch (UnauthorizedAccessException)
        {
            return NotFound();
        }
        catch (InvalidOperationException ex) when (ex.Message == "project_completed_logbook_read_only")
        {
            return StatusCode(409, ex.Message);
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
    }
}
