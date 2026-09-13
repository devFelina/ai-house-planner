using System.Text.Json;
using HousePlanner.API.Controllers;
using HousePlanner.API.Data;
using HousePlanner.API.DTOs;
using HousePlanner.API.Entities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;

namespace HousePlanner.API.Tests.Controllers;

public class ProceduralContractTests
{
    private static ApplicationDbContext Database() => new(new DbContextOptionsBuilder<ApplicationDbContext>()
        .UseInMemoryDatabase(Guid.NewGuid().ToString()).Options);

    private static WorkflowController Controller(ApplicationDbContext db)
    {
        var clients = new Mock<IHttpClientFactory>();
        clients.Setup(f => f.CreateClient(It.IsAny<string>())).Returns(new HttpClient());
        return new WorkflowController(db, NullLogger<WorkflowController>.Instance, clients.Object);
    }

    [Fact]
    public async Task RepeatedRoomTypesKeepTheirOwnOpeningsAndMetadata()
    {
        using var db = Database();
        var workflowId = Guid.NewGuid();
        var roomIds = new[] { Guid.NewGuid(), Guid.NewGuid() };
        var layout = new {
            template_family = "DUPLEX_STACKED", design_seed = 123,
            design_score = 87.5, ground_footprint_sqft = 500,
            connections = new[] { new { from_room = roomIds[0], to_room = roomIds[1], kind = "stair" } },
            entrances = new[] { new { room_id = roomIds[0], wall = "south", offset = 1, width = 3 } },
            plot_constraints = new { dimensions_estimated = true },
            rooms = new[] {
                new { room_id = roomIds[0], room_type = "staircase", floor = 1, x = 0, y = 0,
                      doors = new[] { new { wall = "south", offset = 1, width = 3 } } },
                new { room_id = roomIds[1], room_type = "staircase", floor = 2, x = 0, y = 0,
                      doors = new[] { new { wall = "east", offset = 2, width = 3 } } }
            }
        };
        db.WorkflowStates.Add(new WorkflowState {
            Id = workflowId, LandSubmissionId = Guid.NewGuid(), Status = "design_generated",
            HouseDesigns = new List<HouseDesign> { new() {
                WorkflowStateId = workflowId, FloorCount = 2, Version = 1, IsCurrent = true,
                FoundationType = "slab", LayoutJson = JsonSerializer.Serialize(layout),
                Rooms = new List<Room> {
                    new() { RoomType = "staircase", FloorNumber = 1, Width = 6, Length = 10 },
                    new() { RoomType = "staircase", FloorNumber = 2, Width = 6, Length = 10 }
                }
            } }
        });
        await db.SaveChangesAsync();
        var controller = Controller(db);
        var response = await controller.GetWorkflowStatus(workflowId);
        var dto = Assert.IsType<WorkflowStatusResponseDto>(Assert.IsType<OkObjectResult>(response.Result).Value);
        Assert.Equal("DUPLEX_STACKED", dto.Design!.TemplateFamily);
        Assert.Equal(123, dto.Design.DesignSeed);
        Assert.Equal(87.5m, dto.Design.DesignScore);
        Assert.Equal(500m, dto.Design.GroundFootprintSqft);
        Assert.Equal(roomIds[0], dto.Design.Rooms[0].RoomId);
        Assert.Equal(roomIds[1], dto.Design.Rooms[1].RoomId);
        Assert.Equal("south", dto.Design.Rooms[0].Doors![0].Wall);
        Assert.Equal("east", dto.Design.Rooms[1].Doors![0].Wall);
        Assert.Equal(roomIds[0], dto.Design.Entrances!.Value[0].GetProperty("room_id").GetGuid());
    }

    [Fact]
    public async Task FailedGenerationIsVisibleWithoutSavingADesign()
    {
        using var db = Database();
        var id = Guid.NewGuid();
        db.WorkflowStates.Add(new WorkflowState { Id = id, LandSubmissionId = Guid.NewGuid() });
        await db.SaveChangesAsync();
        var controller = new InternalWorkflowController(db, NullLogger<InternalWorkflowController>.Instance);
        using var json = JsonDocument.Parse("{\"status\":\"failed\"}");
        Assert.IsType<OkObjectResult>(await controller.UpdateGenerationStatus(id, json.RootElement));
        Assert.Equal("failed", (await db.WorkflowStates.FindAsync(id))!.Status);
        Assert.Empty(db.HouseDesigns);
    }

    [Fact]
    public void ExpandedIntakeSerializesPythonCompatibleFieldNames()
    {
        var preferences = new PreferencesDto {
            Bedrooms = 3, Bathrooms = 2, Floors = 1, OpenPlan = true,
            MasterEnsuite = true, SeparateDining = false, UtilityRoom = true,
            ParkingRequired = true, SpacePriority = "balanced",
            CirculationPreference = "space_efficient"
        };
        var plot = new PlotConstraintsDto {
            road_side = "south", north_direction = "east", entrance_side = "west",
            setbacks = new SetbacksDto { front = 10, rear = 6, left = 5, right = 5 }
        };
        var options = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

        using var preferencesJson = JsonDocument.Parse(JsonSerializer.Serialize(preferences, options));
        using var plotJson = JsonDocument.Parse(JsonSerializer.Serialize(plot, options));
        Assert.True(preferencesJson.RootElement.GetProperty("open_plan").GetBoolean());
        Assert.True(preferencesJson.RootElement.GetProperty("master_ensuite").GetBoolean());
        Assert.True(preferencesJson.RootElement.GetProperty("utility_room").GetBoolean());
        Assert.Equal("space_efficient", preferencesJson.RootElement.GetProperty("circulation_preference").GetString());
        Assert.Equal("east", plotJson.RootElement.GetProperty("north_direction").GetString());
        Assert.Equal(6, plotJson.RootElement.GetProperty("setbacks").GetProperty("rear").GetDecimal());
    }
}
