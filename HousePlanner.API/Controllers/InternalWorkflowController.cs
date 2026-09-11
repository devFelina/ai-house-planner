using Microsoft.AspNetCore.Mvc;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;
using System.Text.Json;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/internal/workflows")]
    public class InternalWorkflowController : ControllerBase
    {
        private readonly ApplicationDbContext _context;

        public InternalWorkflowController(ApplicationDbContext context)
        {
            _context = context;
        }

        [HttpPatch("{id}/state")]
        public async Task<IActionResult> UpdateState(Guid id, [FromBody] JsonElement payload)
        {
            var workflow = await _context.WorkflowStates.FindAsync(id);
            if (workflow == null) return NotFound();

            // Store the result back into the database
            // Realistically we'd parse this into the correct columns, but for now we'll just log or update status
            // If the python agent sends DesignResult, we can store it.
            if (payload.TryGetProperty("DesignResult", out var designResultProp))
            {
                workflow.DesignResult = designResultProp;
                workflow.Status = "awaiting_approval";
            }
            
            workflow.UpdatedAt = DateTimeOffset.UtcNow;
            await _context.SaveChangesAsync();

            return Ok();
        }
    }
}
