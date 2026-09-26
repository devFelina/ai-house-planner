"""Room counts shared by catalogue ingestion, export, and revisions."""
from app.design.program.room_rules import room_kind


def count_bathrooms(rooms) -> int:
    return sum(room_kind(room.get('room_type', '') if isinstance(room, dict) else room.room_type)
               == 'bathroom' for room in rooms)
