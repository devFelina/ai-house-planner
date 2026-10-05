using HousePlanner.API.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Threading.Tasks;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/health")]
    public class HealthController : ControllerBase
    {
        private readonly ApplicationDbContext _context;

        public HealthController(ApplicationDbContext context)
        {
            _context = context;
        }

        [HttpGet("database")]
        public async Task<IActionResult> CheckDatabaseConnectivity()
        {
            try
            {
                var canConnect = await _context.Database.CanConnectAsync();

                if (canConnect)
                {
                    return Ok(new { status = "Healthy", message = "Successfully connected to the database." });
                }

                return StatusCode(500, new { status = "Unhealthy", message = "Failed to connect to the database." });
            }
            catch (System.Exception)
            {
                return StatusCode(500, new { status = "Unhealthy", message = "Database connection error." });
            }
        }
    }
}
