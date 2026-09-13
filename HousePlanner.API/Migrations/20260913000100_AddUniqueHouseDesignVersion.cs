using HousePlanner.API.Data;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HousePlanner.API.Migrations
{
    [DbContext(typeof(ApplicationDbContext))]
    [Migration("20260913000100_AddUniqueHouseDesignVersion")]
    public partial class AddUniqueHouseDesignVersion : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateIndex(
                name: "UX_HouseDesigns_WorkflowState_Version",
                table: "HouseDesigns",
                columns: new[] { "WorkflowStateId", "Version" },
                unique: true);
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "UX_HouseDesigns_WorkflowState_Version",
                table: "HouseDesigns");
        }
    }
}
