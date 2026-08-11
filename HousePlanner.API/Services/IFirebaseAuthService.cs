using HousePlanner.API.DTOs;

namespace HousePlanner.API.Services
{
    public interface IFirebaseAuthService
    {
        Task<UserInfoResponseDto> VerifyTokenAsync(string token);
    }
}
