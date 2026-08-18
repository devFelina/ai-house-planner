using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using HousePlanner.API.DTOs;
using HousePlanner.API.Services;
using HousePlanner.API.Data;
using HousePlanner.API.Entities;

namespace HousePlanner.API.Controllers
{
    [ApiController]
    [Route("api/v1/[controller]")]
    public class AuthController : ControllerBase
    {
        private readonly IFirebaseAuthService _firebaseAuthService;
        private readonly ApplicationDbContext _dbContext;

        public AuthController(IFirebaseAuthService firebaseAuthService, ApplicationDbContext dbContext)
        {
            _firebaseAuthService = firebaseAuthService;
            _dbContext = dbContext;
        }

        ///<summary>
        /// Register a new user in local database after Firebase authenticates
        /// </summary>
        [HttpPost("register")]
        [ProducesResponseType(StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        public async Task<IActionResult> Register([FromBody]VerifyTokenRequestDto requestDto)
        {
            if(!ModelState.IsValid)
                return BadRequest(ModelState);

            var userInfo = await _firebaseAuthService.VerifyTokenAsync(requestDto.Token);
            if(userInfo == null)
                return Unauthorized("Invalid Firebase Token");
            
            // Map by email since FirebaseUid doesn't exist on User.cs
            var existingUser = await _dbContext.Users.FirstOrDefaultAsync(u => u.Email == userInfo.Email);
            if(existingUser == null)
            {
                _dbContext.Users.Add(new User 
                {
                    Email = userInfo.Email,
                    FullName = "Firebase User", // Fallback name
                    PasswordHash = "FIREBASE_AUTH", // Placeholder since Firebase manages the actual password
                    RoleId = 1, // Assuming 1 is a default role like "User"
                    CreatedAt = DateTimeOffset.UtcNow,
                    UpdatedAt = DateTimeOffset.UtcNow
                });
                await _dbContext.SaveChangesAsync();
            }
            return Ok(new {Message="User successfully registered in local database", User=userInfo});
        }

        /// <summary>
        /// Verifies a Firebase ID token and returns authenticated user details and role.
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
