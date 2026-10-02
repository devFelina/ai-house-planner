using HousePlanner.API.Data;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace HousePlanner.API.Migrations
{
    [DbContext(typeof(ApplicationDbContext))]
    [Migration("20261002130000_AddWorkflowToolAuditLog")]
    public partial class AddWorkflowToolAuditLog : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "ToolAuditLogJson",
                table: "WorkflowStates",
                type: "jsonb",
                nullable: true);
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "ToolAuditLogJson",
                table: "WorkflowStates");
        }
    }
}
