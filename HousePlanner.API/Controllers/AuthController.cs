using System.Security.Claims;
using HousePlanner.API.DTOs;
using HousePlanner.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HousePlanner.API.Controllers;

[ApiController]
[Route("api/v1/auth")]
public class AuthController(ISupabaseUserSyncService users) : ControllerBase
{
    /// <summary>
    /// Creates or synchronizes an application-user profile for a verified Supabase identity.
    /// Used by Google sign-in and existing session restoration. A new identity is provisioned as
    /// Customer; an existing identity keeps its PostgreSQL role.
    /// The UID and email are derived from the validated Authorization bearer token only.
    /// </summary>
    [Authorize]
    [HttpPost("session")]
    [ProducesResponseType(typeof(UserInfoResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<UserInfoResponseDto>> CreateSession(CancellationToken cancellationToken)
    {
        var supabaseUser = ExtractSupabaseIdentity();
        var applicationUser = await users.SynchronizeAsync(supabaseUser, cancellationToken);
        return Ok(ToDto(applicationUser));
    }

    /// <summary>
    /// Public registration always provisions Customer. Supabase UID, email, and role are trusted
    /// server-side values; extra client fields such as role, RoleId, or SupabaseUid are ignored.
    /// </summary>
    [Authorize]
    [HttpPost("register")]
    [ProducesResponseType(typeof(UserInfoResponseDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<UserInfoResponseDto>> Register(
        [FromBody] RegisterRequestDto request,
        CancellationToken cancellationToken)
    {
        var supabaseUser = ExtractSupabaseIdentity();
        var applicationUser = await users.RegisterCustomerAsync(
            supabaseUser, request.FullName, cancellationToken);
        return Ok(ToDto(applicationUser));
    }

    /// <summary>Loads the current application user and server-owned role after Supabase token validation.</summary>
    [Authorize]
    [HttpGet("me")]
    public async Task<ActionResult<UserInfoResponseDto>> Me(CancellationToken cancellationToken)
        => await CreateSession(cancellationToken);

    [Authorize]
    [HttpGet("debug")]
    public IActionResult Debug()
    {
        return Ok(new
        {
            authenticated = User.Identity?.IsAuthenticated ?? false,
            userId = User.FindFirst("sub")?.Value,
            claims = User.Claims.Select(c => new { c.Type, c.Value })
        });
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private UserInfoResponseDto ExtractSupabaseIdentity() => new()
    {
        Uid = User.FindFirst("sub")?.Value ?? string.Empty,
        Email = User.FindFirst("email")?.Value ?? string.Empty,
    };

    private static UserInfoResponseDto ToDto(Entities.User user) => new()
    {
        Uid = user.SupabaseUid ?? string.Empty,
        Email = user.Email,
        FullName = user.FullName,
        Role = user.Role.Name,
    };
}
