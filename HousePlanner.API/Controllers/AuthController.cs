using Microsoft.AspNetCore.Mvc;
using HousePlanner.API.DTOs;
using HousePlanner.API.Services;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/[controller]")]
    public class AuthController : ControllerBase
    {
        private readonly IFirebaseAuthService _firebaseAuthService;

        public AuthController(IFirebaseAuthService firebaseAuthService)
        {
            _firebaseAuthService = firebaseAuthService;
        }

        /// <summary>
        /// Verifies a Firebase ID token and returns authenticated user details & role.
        /// </summary>
        /// <param name="requestDto">Contains the Firebase ID Token</param>
        /// <returns>UserInfoResponseDto</returns>
        [HttpPost("verify")]
        [ProducesResponseType(typeof(UserInfoResponseDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status401Unauthorized)]
        public async Task<IActionResult> Verify([FromBody] VerifyTokenRequestDto requestDto)
        {
            if (!ModelState.IsValid)
            {
                return BadRequest(ModelState);
            }

            var userInfo = await _firebaseAuthService.VerifyTokenAsync(requestDto.Token);
            return Ok(userInfo);
        }
    }
}
