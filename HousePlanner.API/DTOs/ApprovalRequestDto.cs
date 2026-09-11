namespace HousePlanner.API.DTOs
{
    public record ApprovalRequestDto(
        string Decision,
        string? RevisionNotes
    );
}
