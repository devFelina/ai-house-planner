using FirebaseAdmin.Auth;
using HousePlanner.API.DTOs;

namespace HousePlanner.API.Services
{
    public class FirebaseAuthService : IFirebaseAuthService
    {
        private readonly ILogger<FirebaseAuthService> _logger;

        public FirebaseAuthService(ILogger<FirebaseAuthService> logger)
        {
            _logger = logger;
        }

        public async Task<UserInfoResponseDto> VerifyTokenAsync(string token)
        {
            try
            {
                // 1. Verify the Firebase ID Token using FirebaseAdmin SDK
                FirebaseToken decodedToken = await FirebaseAuth.DefaultInstance.VerifyIdTokenAsync(token);
                
                string uid = decodedToken.Uid;
                
                // Try to get email from decoded claims
                string email = string.Empty;
                if (decodedToken.Claims.TryGetValue("email", out var emailObj) && emailObj != null)
                {
                    email = emailObj.ToString() ?? string.Empty;
                }

                // 2. Mock Role Mapping (since database tables are not built yet)
                // Assigns "Architect" if the email contains "architect", otherwise "Contractor".
                string role = "Contractor";
                if (!string.IsNullOrEmpty(email) && email.Contains("architect", StringComparison.OrdinalIgnoreCase))
                {
                    role = "Architect";
                }

                _logger.LogInformation("Successfully verified Firebase token for User UID: {Uid}, Email: {Email}, Mapped Role: {Role}", uid, email, role);

                return new UserInfoResponseDto
                {
                    Uid = uid,
                    Email = email,
                    Role = role
                };
            }
            catch (FirebaseAuthException ex)
            {
                _logger.LogError(ex, "Firebase ID Token verification failed.");
                throw new UnauthorizedAccessException("Invalid Firebase ID Token.", ex);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Unexpected error occurred during token verification.");
                throw;
            }
        }
    }
}
