using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using HousePlanner.API.Controllers;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace HousePlanner.API.Tests.Controllers;

public class WorkflowControllerTests
{
    private readonly ApplicationDbContext _dbContext;
    private readonly Mock<ILogger<WorkflowController>> _loggerMock;
    private readonly WorkflowController _controller;

    public WorkflowControllerTests()
    {
        var options = new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
            .Options;
        _dbContext = new ApplicationDbContext(options);
        _loggerMock = new Mock<ILogger<WorkflowController>>();
        var clients = new Mock<IHttpClientFactory>();
        clients.Setup(f => f.CreateClient(It.IsAny<string>())).Returns(new HttpClient());
        _controller = new WorkflowController(_dbContext, _loggerMock.Object, clients.Object);
    }

    [Fact]
    public async Task GetWorkflowStatus_ReturnsNotFound_WhenWorkflowDoesNotExist()
    {
        // Act
        var result = await _controller.GetWorkflowStatus(Guid.NewGuid());

        // Assert
        Assert.IsType<NotFoundObjectResult>(result.Result);
    }

    [Fact]
    public async Task GetWorkflowStatus_ReturnsWorkflow_WhenNoDesignExists()
    {
        // Arrange
        var workflowId = Guid.NewGuid();
        _dbContext.WorkflowStates.Add(new WorkflowState
        {
            Id = workflowId,
            LandSubmissionId = Guid.NewGuid(),
            Status = "pending",
            TerrainType = "flat"
        });
        await _dbContext.SaveChangesAsync();

        // Act
        var result = await _controller.GetWorkflowStatus(workflowId);

        // Assert
        var okResult = Assert.IsType<OkObjectResult>(result.Result);
        var response = Assert.IsType<WorkflowStatusResponseDto>(okResult.Value);
        
        Assert.Equal(workflowId, response.WorkflowId);
        Assert.Equal("pending", response.Status);
        Assert.Equal("flat", response.TerrainType);
        Assert.Null(response.Design);
    }

    [Fact]
    public async Task GetWorkflowStatus_ReturnsWorkflow_WithLatestDesign()
    {
        // Arrange
        var workflowId = Guid.NewGuid();
        
        var olderDesign = new HouseDesign
        {
            Id = Guid.NewGuid(),
            WorkflowStateId = workflowId,
            Version = 1,
            IsCurrent = false,
            FloorCount = 1,
            TotalBuiltUpAreaSqft = 1000m,
            FoundationType = "slab",
            LayoutJson = "{ \"rooms\": [] }"
        };

        var currentDesign = new HouseDesign
        {
            Id = Guid.NewGuid(),
            WorkflowStateId = workflowId,
            Version = 2,
            IsCurrent = true,
            FloorCount = 2,
            TotalBuiltUpAreaSqft = 1500m,
            FoundationType = "stepped",
            LayoutJson = "{ \"rooms\": [ { \"room_type\": \"living_room\", \"floor\": 1, \"x\": 0, \"y\": 0, \"width\": 10, \"length\": 10 } ] }",
            Rooms = new List<Room>
            {
                new Room { Id = Guid.NewGuid(), RoomType = "living_room", FloorNumber = 1, X = 0, Y = 0, Width = 10, Length = 10, AreaSqft = 100 }
            }
        };

        var workflow = new WorkflowState
        {
            Id = workflowId,
            LandSubmissionId = Guid.NewGuid(),
            Status = "design_generated",
            HouseDesigns = new List<HouseDesign> { olderDesign, currentDesign }
        };

        _dbContext.WorkflowStates.Add(workflow);
        await _dbContext.SaveChangesAsync();

        // Act
        var result = await _controller.GetWorkflowStatus(workflowId);

        // Assert
        var okResult = Assert.IsType<OkObjectResult>(result.Result);
        var response = Assert.IsType<WorkflowStatusResponseDto>(okResult.Value);
        
        Assert.Equal(workflowId, response.WorkflowId);
        Assert.NotNull(response.Design);
        Assert.Equal(2, response.Design.Version);
        Assert.Equal(2, response.Design.FloorCount);
        Assert.Equal(1500m, response.Design.TotalBuiltUpAreaSqft);
        Assert.Single(response.Design.Rooms);
        Assert.Equal("living_room", response.Design.Rooms[0].RoomType);
    }
}
