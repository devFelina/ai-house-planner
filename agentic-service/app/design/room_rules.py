"""Conceptual project limits; these are not statutory building-code rules."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RoomRule:
    min_width: float
    min_length: float
    target_area: float
    aspect_limit: float = 3.0


ROOM_RULES = {
    'living_room': RoomRule(10, 10, 180),
    'bedroom': RoomRule(9, 10, 130),
    'kitchen': RoomRule(8, 8, 100),
    'bathroom': RoomRule(5, 5, 45),
    'dining': RoomRule(8, 8, 110),
    'home_office': RoomRule(8, 8, 90),
    'family_lounge': RoomRule(8, 8, 100),
    'hallway': RoomRule(3.5, 4, 32, 8),
    'entrance': RoomRule(4, 4, 24, 16),
    'foyer': RoomRule(4, 4, 32, 16),
    'staircase': RoomRule(6, 10, 60),
    'balcony': RoomRule(4, 6, 48),
    'veranda': RoomRule(4, 6, 48),
    'utility': RoomRule(5, 5, 40),
}
MAX_ROOM_DIMENSION = 50
MIN_DOOR_WIDTH = 3.0
MIN_COMPACTNESS = 0.35
CIRCULATION_TYPES = {'hallway', 'entrance', 'foyer', 'staircase'}


def room_kind(room_type: str) -> str:
    for kind in sorted(ROOM_RULES, key=len, reverse=True):
        if room_type == kind or room_type.startswith(kind + '_'):
            return kind
    return room_type


def rule_for(room_type: str) -> RoomRule:
    return ROOM_RULES.get(room_kind(room_type), RoomRule(4, 4, 64))
