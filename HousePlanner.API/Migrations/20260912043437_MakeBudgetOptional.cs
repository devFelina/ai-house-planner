using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace HousePlanner.API.Migrations
{
    /// <inheritdoc />
    public partial class MakeBudgetOptional : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("ALTER TABLE \"LandSubmissions\" ALTER COLUMN \"BudgetLkr\" DROP NOT NULL;");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("ALTER TABLE \"LandSubmissions\" ALTER COLUMN \"BudgetLkr\" SET NOT NULL;");
        }
    }
}
