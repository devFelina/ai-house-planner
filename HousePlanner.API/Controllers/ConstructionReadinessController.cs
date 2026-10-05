using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/readiness/{referenceId}")]
    [Authorize]
    public class ConstructionReadinessController : ControllerBase
    {
        private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, DateTime> _userRateLimits = new();
        private static readonly System.Collections.Concurrent.ConcurrentDictionary<Guid, bool> _activeGenerations = new();
        
        private readonly ApplicationDbContext _context;
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _configuration;

        public ConstructionReadinessController(ApplicationDbContext context, IHttpClientFactory httpClientFactory, IConfiguration configuration)
        {
            _context = context;
            _httpClientFactory = httpClientFactory;
            _configuration = configuration;
        }

        [HttpGet("materials")]
        public async Task<ActionResult<IEnumerable<ConstructionMaterialDto>>> GetMaterials(Guid referenceId)
        {
            var materials = await _context.ConstructionMaterials
                .Where(m => m.ProjectId == referenceId || m.HouseDesignId == referenceId)
                .Select(m => new ConstructionMaterialDto
                {
                    Id = m.Id,
                    ProjectId = m.ProjectId,
                    HouseDesignId = m.HouseDesignId,
                    PhaseId = m.PhaseId,
                    MaterialName = m.MaterialName,
                    RequiredQuantity = m.RequiredQuantity,
                    Unit = m.Unit,
                    AvailableQuantity = m.AvailableQuantity,
                    OrderedQuantity = m.OrderedQuantity,
                    Supplier = m.Supplier,
                    ExpectedDeliveryDate = m.ExpectedDeliveryDate,
                    Status = m.Status
                })
                .ToListAsync();

            var isProject = await _context.Projects.AnyAsync(p => p.Id == referenceId);
            if (isProject)
            {
                var logs = await _context.DailyConstructionLogs
                    .Where(l => l.ProjectId == referenceId && !string.IsNullOrEmpty(l.MaterialsUsed))
                    .ToListAsync();

                foreach (var log in logs)
                {
                    // Split the MaterialsUsed string by commas
                    var items = log.MaterialsUsed.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
                    foreach (var item in items)
                    {
                        // Check if it already exists to avoid duplicates (case-insensitive)
                        if (!materials.Any(m => m.MaterialName.Equals(item, StringComparison.OrdinalIgnoreCase)))
                        {
                            materials.Add(new ConstructionMaterialDto
                            {
                                Id = Guid.NewGuid(),
                                ProjectId = referenceId,
                                MaterialName = item,
                                RequiredQuantity = 1,
                                AvailableQuantity = 1,
                                OrderedQuantity = 0,
                                Unit = "units",
                                Status = "Ready"
                            });
                        }
                    }
                }
            }

            return Ok(materials);
        }

        [HttpPost("materials")]
        public async Task<ActionResult<ConstructionMaterialDto>> AddMaterial(Guid referenceId, CreateConstructionMaterialDto dto)
        {
            try
            {
                var isProject = await _context.Projects.AnyAsync(p => p.Id == referenceId);
                var isDesign = !isProject && await _context.HouseDesigns.AnyAsync(d => d.Id == referenceId);

                if (!isProject && !isDesign) return NotFound("Project or Design not found");

                var material = new ConstructionMaterial
                {
                    Id = Guid.NewGuid(),
                    ProjectId = isProject ? referenceId : null,
                    HouseDesignId = isDesign ? referenceId : null,
                    PhaseId = dto.PhaseId,
                    MaterialName = dto.MaterialName,
                    RequiredQuantity = dto.RequiredQuantity,
                    Unit = dto.Unit,
                    AvailableQuantity = dto.AvailableQuantity,
                    OrderedQuantity = dto.OrderedQuantity,
                    Supplier = dto.Supplier,
                    ExpectedDeliveryDate = dto.ExpectedDeliveryDate,
                    Status = dto.Status ?? "Pending"
                };

                _context.ConstructionMaterials.Add(material);
                await _context.SaveChangesAsync();

                var result = new ConstructionMaterialDto
                {
                    Id = material.Id,
                    ProjectId = material.ProjectId,
                    HouseDesignId = material.HouseDesignId,
                    PhaseId = material.PhaseId,
                    MaterialName = material.MaterialName,
                    RequiredQuantity = material.RequiredQuantity,
                    Unit = material.Unit,
                    AvailableQuantity = material.AvailableQuantity,
                    OrderedQuantity = material.OrderedQuantity,
                    Supplier = material.Supplier,
                    ExpectedDeliveryDate = material.ExpectedDeliveryDate,
                    Status = material.Status
                };

                return CreatedAtAction(nameof(GetMaterials), new { referenceId = referenceId }, result);
            }
            catch (Exception ex)
            {
                return StatusCode(500, $"Internal server error: {ex.Message}");
            }
        }

        [HttpPost("materials/generate")]
        public async Task<ActionResult> AutoGenerateMaterials(Guid referenceId)
        {
            try
            {
                var isProject = await _context.Projects.AnyAsync(p => p.Id == referenceId);
                var isDesign = !isProject && await _context.HouseDesigns.AnyAsync(d => d.Id == referenceId);
                if (!isProject && !isDesign) return NotFound("Project or Design not found");

                var existing = await _context.ConstructionMaterials.Where(m => m.ProjectId == referenceId || m.HouseDesignId == referenceId).ToListAsync();
                if (existing.Any()) {
                    _context.ConstructionMaterials.RemoveRange(existing);
                    await _context.SaveChangesAsync();
                }

                var aiMaterials = new List<ConstructionMaterial>
                {
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "Cement (Foundation)", RequiredQuantity = 450, AvailableQuantity = 200, OrderedQuantity = 250, Unit = "bags", Status = "Shortage" },
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "Steel", RequiredQuantity = 1200, AvailableQuantity = 500, OrderedQuantity = 0, Unit = "kg", Status = "Shortage" },
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "Bricks/blocks", RequiredQuantity = 5000, AvailableQuantity = 5000, OrderedQuantity = 0, Unit = "pcs", Status = "Ready" },
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "Electrical cables", RequiredQuantity = 300, AvailableQuantity = 100, OrderedQuantity = 0, Unit = "meters", Status = "Shortage" },
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "Tiles", RequiredQuantity = 800, AvailableQuantity = 800, OrderedQuantity = 0, Unit = "sqft", Status = "Ready" },
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "Sand", RequiredQuantity = 5, AvailableQuantity = 2, OrderedQuantity = 0, Unit = "cubes", Status = "Shortage" },
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "Water tanks", RequiredQuantity = 2, AvailableQuantity = 2, OrderedQuantity = 0, Unit = "units", Status = "Ready" },
                    new() { Id = Guid.NewGuid(), ProjectId = isProject ? referenceId : null, HouseDesignId = isDesign ? referenceId : null, MaterialName = "PVC pipes", RequiredQuantity = 50, AvailableQuantity = 50, OrderedQuantity = 0, Unit = "pcs", Status = "Ready" }
                };

                _context.ConstructionMaterials.AddRange(aiMaterials);
                await _context.SaveChangesAsync();

                return Ok(aiMaterials);
            }
            catch (Exception ex)
            {
                return StatusCode(500, $"Internal server error: {ex.Message}");
            }
        }

        [HttpPost("plan")]
        public async Task<ActionResult> GenerateReadinessPlan(Guid referenceId)
        {
            var userId = User.Claims.FirstOrDefault(c => c.Type == "id")?.Value ?? "anonymous";
            
            // Rate limit: 1 request per minute per user
            if (_userRateLimits.TryGetValue(userId, out var lastRequest))
            {
                if (DateTime.UtcNow - lastRequest < TimeSpan.FromMinutes(1))
                {
                    return StatusCode(429, "Too many requests. Please wait a minute before requesting another plan.");
                }
            }
            _userRateLimits[userId] = DateTime.UtcNow;

            // Project concurrency limit
            if (!_activeGenerations.TryAdd(referenceId, true))
            {
                return StatusCode(429, "A generation for this project is already in progress.");
            }

            try
            {
                var project = await _context.Projects
                .Include(p => p.ConstructionPhases)
                .FirstOrDefaultAsync(p => p.Id == referenceId);

            var workflow = project == null ? await _context.WorkflowStates
                .Include(w => w.HouseDesigns)
                .FirstOrDefaultAsync(w => w.HouseDesigns.Any(d => d.Id == referenceId)) : null;

            if (project == null && workflow == null) return NotFound("Reference not found");

            var materials = await _context.ConstructionMaterials
                .Where(m => m.ProjectId == referenceId || m.HouseDesignId == referenceId)
                .ToListAsync();

            var client = _httpClientFactory.CreateClient();
            var agenticServiceUrl = _configuration["AgenticService:BaseUrl"] ?? "http://localhost:8001";
            client.DefaultRequestHeaders.Add("X-Internal-API-Key", _configuration["AgenticService:InternalApiKey"]);

            object projectData;
            IEnumerable<object> phasesData;

            if (project != null)
            {
                projectData = new
                {
                    start_date = project.CreatedAt,
                    status = project.Status,
                    ai_estimated_duration = project.AiEstimatedTotalDurationDays,
                    house_design_id = project.HouseDesignId
                };
                phasesData = project.ConstructionPhases.Select(p => new
                {
                    phase_id = p.Id,
                    name = p.PhaseName,
                    order = p.SequenceOrder,
                    status = p.Status,
                    start_date = p.PlannedStartDate,
                    end_date = p.PlannedEndDate
                });
            }
            else
            {
                projectData = new
                {
                    start_date = workflow!.CreatedAt,
                    status = "design_phase",
                    house_design_id = referenceId
                };
                
                var phasesList = new List<object>();
                if (!string.IsNullOrEmpty(workflow.ConstructionPlan))
                {
                    try
                    {
                        using var doc = JsonDocument.Parse(workflow.ConstructionPlan);
                        if (doc.RootElement.TryGetProperty("phases", out var phasesArray))
                        {
                            foreach (var p in phasesArray.EnumerateArray())
                            {
                                phasesList.Add(new {
                                    phase_id = Guid.NewGuid(),
                                    name = p.TryGetProperty("name", out var n) ? n.GetString() : "Unknown",
                                    order = p.TryGetProperty("order", out var o) ? o.GetInt32() : 0,
                                    status = "Pending"
                                });
                            }
                        }
                    }
                    catch { }
                }
                phasesData = phasesList;
            }

            var payload = new
            {
                project_id = referenceId.ToString(),
                project_data = projectData,
                construction_plan = phasesData,
                inventory = materials.Select(m => new
                {
                    id = m.Id,
                    phase_id = m.PhaseId,
                    name = m.MaterialName,
                    required = m.RequiredQuantity,
                    available = m.AvailableQuantity,
                    ordered = m.OrderedQuantity,
                    unit = m.Unit
                })
            };

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");

            HttpResponseMessage response;
            try
            {
                response = await client.PostAsync($"{agenticServiceUrl}/api/v1/orchestration/readiness", content);
            }
            catch (HttpRequestException)
            {
                return StatusCode(503, "Agentic AI Service is offline or unreachable. Please ensure the agentic-service is running on " + agenticServiceUrl);
            }

            if (!response.IsSuccessStatusCode)
            {
                var error = await response.Content.ReadAsStringAsync();
                return StatusCode((int)response.StatusCode, error);
            }

            var plan = await response.Content.ReadAsStringAsync();
            return Content(plan, "application/json");
            }
            finally
            {
                _activeGenerations.TryRemove(referenceId, out _);
            }
        }
    }
}
