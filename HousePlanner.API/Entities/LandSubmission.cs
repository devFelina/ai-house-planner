using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace HousePlanner.Domain.Entities
{
    [Table("LandSubmissions")]
    public class LandSubmission
    {
        [Key]
        public Guid Id{get;set;}

        [Required]
        public Guid ClientId{get;set;}

        [ForeignKey("ClientId")]
        public virtual User Client{get;set;}=null!;

        [Required]
        [Column(TypeName="decimal(14,2)")]
        public decimal BudgetLkr {get;set}

        [Required]
        [Column(TypeName="decimal(10,2)")]
        public decimal LandSizePerches {get;set;}

        [StringLength(500)]
        public string? LandPhotoUrl {get;set;}

        [StringLength(30)]
        public string? ManualTerrainType {get;set;} //fallback if there is no photo

        [Required]
        pubic int PreferredBedrooms {get;set;}

        [Required]
        public int PreferredFloors {get;set;}

        [StringLength(50)]
        public string? StylePreference {get;set;}

        public DateTimeOffset CreatedAt {get;set;}

        public DateTimeOffset UpdatedAt {get;set;}
    }
}