using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using HousePlanner.API.Controllers;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace HousePlanner.API.Tests.Controllers;

public class InternalWorkflowControllerTests
{
    private readonly ApplicationDbContext _dbContext;
    private readonly Mock<ILogger<InternalWorkflowController>> _loggerMock;
    private readonly InternalWorkflowController _controller;

    public InternalWorkflowControllerTests()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        _dbContext = new ApplicationDbContext(options);
        _loggerMock = new Mock<ILogger<InternalWorkflowController>>();
        _controller = new InternalWorkflowController(_dbContext, _loggerMock.Object);
    }

    [Fact]
    public async Task UpdateTerrain_UpdatesWorkflow_Successfully()
    {
        // Arrange
        var workflowId = Guid.NewGuid();
        var workflow = new WorkflowState
        {
            Id = workflowId,
            LandSubmissionId = Guid.NewGuid(),
            Status = "pending"
        };
        _dbContext.WorkflowStates.Add(workflow);
        await _dbContext.SaveChangesAsync();

        var json = @"{
            ""terrain_type"": ""hillside"",
            ""slope_estimate"": ""moderate"",
            ""notable_features"": [""trees""]
        }";
        var element = JsonDocument.Parse(json).RootElement;

        // Act
        var result = await _controller.UpdateTerrain(workflowId, element);

        // Assert
        Assert.IsType<OkObjectResult>(result);
        
        var dbWorkflow = await _dbContext.WorkflowStates.FindAsync(workflowId);
        Assert.Equal("hillside", dbWorkflow!.TerrainType);
        Assert.Equal("moderate", dbWorkflow.SlopeEstimate);
        Assert.Contains("trees", dbWorkflow.NotableFeatures);
    }

    [Fact]
    public async Task SubmitDesignRevision_CreatesNewVersion_AndMarksOldAsNotCurrent()
    {
        // Arrange
        var workflowId = Guid.NewGuid();
        var oldDesign = new HouseDesign
        {
            Id = Guid.NewGuid(),
            WorkflowStateId = workflowId,
            Version = 1,
            IsCurrent = true,
            FloorCount = 1,
            TotalBuiltUpAreaSqft = 1000m,
            FoundationType = "slab",
            LayoutJson = "{}"
        };

        var workflow = new WorkflowState
        {
            Id = workflowId,
            LandSubmissionId = Guid.NewGuid(),
            Status = "pending",
            HouseDesigns = new List<HouseDesign> { oldDesign }
        };
        _dbContext.WorkflowStates.Add(workflow);
        await _dbContext.SaveChangesAsync();

        var json = @"{
            ""floor_count"": 2,
            ""total_built_up_area_sqft"": 1500.5,
            ""foundation_type"": ""stepped"",
            ""template_id"": ""TEST_TEMPLATE"",
            ""terrain_type"": ""hillside"",
            ""rooms"": [
                {
                    ""room_type"": ""kitchen"",
                    ""floor"": 1,
                    ""x"": 0,
                    ""y"": 0,
                    ""width"": 12,
                    ""length"": 10,
                    ""wall_height"": 9
                }
            ]
        }";
        var element = JsonDocument.Parse(json).RootElement;

        // Act
        var result = await _controller.SubmitDesignRevision(workflowId, element);

        // Assert
        Assert.IsType<OkObjectResult>(result);

        var dbWorkflow = await _dbContext.WorkflowStates
            .Include(w => w.HouseDesigns)
            .ThenInclude(d => d.Rooms)
            .FirstOrDefaultAsync(w => w.Id == workflowId);

        Assert.Equal("design_generated", dbWorkflow!.Status);
        Assert.Equal("hillside", dbWorkflow.TerrainType);

        var oldDbDesign = dbWorkflow.HouseDesigns.FirstOrDefault(d => d.Id == oldDesign.Id);
        Assert.False(oldDbDesign!.IsCurrent);

        var newDbDesign = dbWorkflow.HouseDesigns.FirstOrDefault(d => d.Id != oldDesign.Id);
        Assert.NotNull(newDbDesign);
        Assert.True(newDbDesign.IsCurrent);
        Assert.Equal(2, newDbDesign.Version);
        Assert.Equal(2, newDbDesign.FloorCount);
        Assert.Equal(1500.5m, newDbDesign.TotalBuiltUpAreaSqft);
        Assert.Equal("stepped", newDbDesign.FoundationType);
        
        Assert.Single(newDbDesign.Rooms);
        var room = newDbDesign.Rooms.First();
        Assert.Equal("kitchen", room.RoomType);
        Assert.Equal(1, room.FloorNumber);
        Assert.Equal(12m, room.Width);
        Assert.Equal(10m, room.Length);
        Assert.Equal(120m, room.AreaSqft);
    }
}
