using Microsoft.AspNetCore.Mvc;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using System.Text;
using System.Text.Json;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/workflows")]
    public class WorkflowController : ControllerBase
    {
        private readonly ApplicationDbContext _context;
        private readonly HttpClient _agenticServiceClient;

        public WorkflowController(ApplicationDbContext context, IHttpClientFactory httpClientFactory)
        {
            _context = context;
            _agenticServiceClient = httpClientFactory.CreateClient("AgenticService");
        }

        [HttpPost("{id}/approve")]
        public async Task<IActionResult> ApproveWorkflow(Guid id, [FromBody] ApprovalRequestDto request)
        {
            var workflow = await _context.WorkflowStates.FindAsync(id);
            if (workflow == null) return NotFound();

            if (request.Decision == "request_revision")
            {
                workflow.Status = "running";
                workflow.UpdatedAt = DateTimeOffset.UtcNow;
                await _context.SaveChangesAsync();
                
                // Tell the Python AI service to run the Design agent again with the chat prompt
                var payload = new {
                    workflow_id = id,
                    resume_from = "design",
                    user_revision_prompt = request.RevisionNotes // Pass the chat text to the AI
                };
                
                var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                
                // POST to Python internal API to resume the graph
                // Need to clear headers to safely re-add them if re-used, though new content shouldn't clash
                _agenticServiceClient.DefaultRequestHeaders.Clear();
                _agenticServiceClient.DefaultRequestHeaders.Add("X-Internal-API-Key", "shared-internal-secret");
                
                await _agenticServiceClient.PostAsync("http://localhost:8001/workflows/resume", content);
                
                return Ok(new { Message = "Revision started" });
            }
            else if (request.Decision == "approve")
            {
                workflow.ApprovalStatus = "approved";
                workflow.Status = "approved";
                workflow.ApprovedAt = DateTimeOffset.UtcNow;
                
                workflow.UpdatedAt = DateTimeOffset.UtcNow;
                await _context.SaveChangesAsync();
                
                return Ok(new { Message = "Workflow approved successfully" });
            }
            else if (request.Decision == "reject")
            {
                workflow.ApprovalStatus = "rejected";
                workflow.Status = "rejected";
                
                workflow.UpdatedAt = DateTimeOffset.UtcNow;
                await _context.SaveChangesAsync();
                
                return Ok(new { Message = "Workflow rejected" });
            }
            
            return BadRequest(new { Message = "Invalid Decision. Use 'approve', 'reject', or 'request_revision'." });
        }
    }
}
