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

        /// <summary>
        /// Native PostgreSQL Registration (No Firebase)
        /// </summary>
        [HttpPost("local/register")]
        public async Task<IActionResult> LocalRegister([FromBody] LocalRegisterRequestDto request)
        {
            if (!ModelState.IsValid) return BadRequest(ModelState);

            var existing = await _dbContext.Users.FirstOrDefaultAsync(u => u.Email == request.Email);
            if (existing != null) return BadRequest("User with this email already exists.");

            var newUser = new User
            {
                Email = request.Email,
                FullName = request.FullName,
                PasswordHash = request.Password, // TODO: Use a proper password hasher like BCrypt in production
                RoleId = request.RoleId == 0 ? 1 : request.RoleId, // Default to 1
                CreatedAt = DateTimeOffset.UtcNow,
                UpdatedAt = DateTimeOffset.UtcNow
            };

            _dbContext.Users.Add(newUser);
            await _dbContext.SaveChangesAsync();

            return Ok(new { Message = "Registration successful", UserId = newUser.Id });
        }

        /// <summary>
        /// Native PostgreSQL Login (No Firebase)
        /// </summary>
        [HttpPost("local/login")]
        public async Task<IActionResult> LocalLogin([FromBody] LocalLoginRequestDto request)
        {
            if (!ModelState.IsValid) return BadRequest(ModelState);

            var user = await _dbContext.Users
                .Include(u => u.Role)
                .FirstOrDefaultAsync(u => u.Email == request.Email);

            if (user == null || user.PasswordHash != request.Password) 
            {
                return Unauthorized("Invalid email or password.");
            }

            // Return user info (In a real app, generate a JWT token here)
            return Ok(new 
            { 
                Message = "Login successful", 
                User = new { user.Id, user.Email, user.FullName, Role = user.Role?.Name }
            });
        }
    }
}
