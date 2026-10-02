using System.Text.Json;
using HousePlanner.API.Controllers;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;

namespace HousePlanner.API.Tests.Controllers;

public sealed class InternalWorkflowToolAuditTests
{
    private static ToolAuditEntryDto ValidEntry() => new()
    {
        AgentName = "design",
        Action = "tool_call_succeeded",
        ToolCalled = "geometry_generator",
        DurationMs = 12,
        Result = "success",
        EventStatus = "succeeded",
        InputSummary = new Dictionary<string, JsonElement>
        {
            ["bedrooms"] = JsonSerializer.Deserialize<JsonElement>("3")
        },
        OutputSummary = new Dictionary<string, JsonElement>
        {
            ["room_count"] = JsonSerializer.Deserialize<JsonElement>("8")
        },
        CreatedAtUtc = "2026-10-02T00:00:00+00:00"
    };

    private static (ApplicationDbContext Db, InternalWorkflowController Controller) CreateController()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;
        var db = new ApplicationDbContext(options);
        return (db, new InternalWorkflowController(db, NullLogger<InternalWorkflowController>.Instance));
    }

    [Fact]
    public async Task UpdateToolAuditLog_ValidEntries_PersistsCompleteJson()
    {
        var (db, controller) = CreateController();
        var id = Guid.NewGuid();
        db.WorkflowStates.Add(new WorkflowState { Id = id, LandSubmissionId = Guid.NewGuid() });
        await db.SaveChangesAsync();

        var result = await controller.UpdateToolAuditLog(
            id,
            new ToolAuditLogRequest { Entries = [ValidEntry()] });

        Assert.IsType<OkObjectResult>(result);
        var stored = (await db.WorkflowStates.FindAsync(id))!.ToolAuditLogJson;
        Assert.NotNull(stored);
        using var document = JsonDocument.Parse(stored);
        var entry = document.RootElement.GetProperty("entries")[0];
        Assert.Equal("geometry_generator", entry.GetProperty("toolCalled").GetString());
        Assert.Equal(12, entry.GetProperty("durationMs").GetInt32());
        Assert.Equal("succeeded", entry.GetProperty("eventStatus").GetString());
        Assert.Equal(3, entry.GetProperty("inputSummary").GetProperty("bedrooms").GetInt32());
        Assert.Equal(8, entry.GetProperty("outputSummary").GetProperty("room_count").GetInt32());
        Assert.Equal(JsonValueKind.Null, entry.GetProperty("errorType").ValueKind);
        Assert.Equal(JsonValueKind.Null, entry.GetProperty("errorSummary").ValueKind);
    }

    [Fact]
    public async Task UpdateToolAuditLog_MissingWorkflow_ReturnsNotFound()
    {
        var (_, controller) = CreateController();
        var result = await controller.UpdateToolAuditLog(
            Guid.NewGuid(),
            new ToolAuditLogRequest { Entries = [ValidEntry()] });
        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UpdateToolAuditLog_InvalidPayload_ReturnsBadRequest()
    {
        var (_, controller) = CreateController();
        var invalid = ValidEntry();
        invalid.ToolCalled = "";

        var result = await controller.UpdateToolAuditLog(
            Guid.NewGuid(),
            new ToolAuditLogRequest { Entries = [invalid] });
        Assert.IsType<BadRequestObjectResult>(result);
    }
}

public sealed class InternalToolAuditRouteContractTests
{
    [Fact]
    public void ToolAuditEndpoint_RemainsUnderAuthenticatedInternalRoute()
    {
        var controllerRoute = Assert.Single(
            typeof(InternalWorkflowController)
                .GetCustomAttributes(typeof(RouteAttribute), inherit: true)
                .Cast<RouteAttribute>());
        var method = typeof(InternalWorkflowController)
            .GetMethod(nameof(InternalWorkflowController.UpdateToolAuditLog));
        var patchRoute = Assert.Single(
            method!.GetCustomAttributes(typeof(HttpPatchAttribute), inherit: true)
                .Cast<HttpPatchAttribute>());

        Assert.StartsWith("api/v1/internal/", controllerRoute.Template);
        Assert.Equal("{id:guid}/tool-audit-log", patchRoute.Template);
    }
}
