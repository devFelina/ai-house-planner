using Microsoft.EntityFrameworkCore;
using HousePlanner.API.Entities;

namespace HousePlanner.API.Data
{
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options) { }

        public DbSet<User> Users { get; set; }
        public DbSet<Role> Roles { get; set; }
        public DbSet<LandSubmission> LandSubmissions { get; set; }
        public DbSet<HouseDesign> HouseDesigns { get; set; }
        public DbSet<Room> Rooms { get; set; }
        public DbSet<WorkflowState> WorkflowStates { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            modelBuilder.Entity<HouseDesign>(entity =>
            {
                entity.HasIndex(e => e.WorkflowStateId).HasDatabaseName("IX_HouseDesigns_WorkflowStateId");
                entity.HasIndex(e => new { e.WorkflowStateId, e.IsCurrent }).HasDatabaseName("IX_HouseDesigns_WorkflowState_IsCurrent");
                if (Database.IsRelational())
                {
                    entity.Property(e => e.CreatedAt).HasDefaultValueSql("now()");
                }
            });

            modelBuilder.Entity<Room>(entity =>
            {
                entity.HasIndex(e => e.HouseDesignId).HasDatabaseName("IX_Rooms_HouseDesignId");
            });
        }
    }
}
