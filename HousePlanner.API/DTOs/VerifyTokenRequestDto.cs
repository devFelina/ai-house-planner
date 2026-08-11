using System.ComponentModel.DataAnnotations;

namespace HousePlanner.API.DTOs
{
    public class VerifyTokenRequestDto
    {
        [Required(ErrorMessage = "Firebase ID Token is required.")]
        public string Token { get; set; } = string.Empty;
    }
}
