"""
Deterministic geometry validation for house designs.

Why deterministic validation instead of relying on the LLM:
- LLMs cannot guarantee non-overlapping room coordinates
- Validation catches impossible dimensions before they reach the database
- Provides structured feedback for the revision flow

All checks are rule-based — no AI involved.
"""
from typing import List, Tuple
from app.schemas.design_result import RoomLayout
from app.tools.land_utils import max_buildable_area


class GeometryValidationResult:
    """Result of geometry validation with pass/fail and structured reasons."""

    def __init__(self):
        self.passed = True
        self.failures: List[str] = []
        self.failed_rules: List[str] = []

    def fail(self, rule: str, message: str):
        self.passed = False
        self.failures.append(message)
        self.failed_rules.append(rule)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failures": self.failures,
            "failed_rules": self.failed_rules,
        }


def validate_geometry(
    rooms: List[RoomLayout],
    expected_bedrooms: int,
    expected_floors: int,
    land_size_perches: float,
) -> GeometryValidationResult:
    """
    Run all geometry checks on a generated design.

    Checks:
    1. Room dimensions are positive
    2. Room area matches width × length
    3. Rooms on the same floor don't overlap
    4. Bedroom count matches requirement
    5. Floor count matches requirement
    6. Total built-up area respects coverage limit
    7. Required rooms exist (at least 1 living, 1 kitchen, 1 bathroom)
    8. No impossible dimensions (rooms wider than 50ft or longer than 50ft)
    """
    result = GeometryValidationResult()

    if not rooms:
        result.fail("no_rooms", "Design has no rooms.")
        return result

    # 1. Positive dimensions
    for room in rooms:
        if room.width <= 0 or room.length <= 0:
            result.fail(
                "invalid_dimensions",
                f"Room '{room.room_type}' has invalid dimensions: {room.width}x{room.length}"
            )

    # 2. Area consistency
    for room in rooms:
        expected_area = round(room.width * room.length, 2)
        actual_area = room.area_sqft if room.area_sqft is not None else expected_area
        if abs(actual_area - expected_area) > 1.0:  # Allow 1 sqft rounding tolerance
            result.fail(
                "area_mismatch",
                f"Room '{room.room_type}' area {actual_area} doesn't match {room.width}×{room.length}={expected_area}"
            )

    # 3. Overlap detection (per floor)
    floors = set(r.floor for r in rooms)
    for floor_num in floors:
        floor_rooms = [r for r in rooms if r.floor == floor_num]
        for i, a in enumerate(floor_rooms):
            for b in floor_rooms[i + 1:]:
                if _rooms_overlap(a, b):
                    result.fail(
                        "room_overlap",
                        f"Floor {floor_num}: '{a.room_type}' overlaps with '{b.room_type}'"
                    )

    # 4. Bedroom count
    bedroom_rooms = [r for r in rooms if "bedroom" in r.room_type.lower()]
    if len(bedroom_rooms) != expected_bedrooms:
        result.fail(
            "bedroom_count",
            f"Expected {expected_bedrooms} bedrooms, found {len(bedroom_rooms)}"
        )

    # 5. Floor count
    actual_floors = len(floors)
    if actual_floors != expected_floors:
        result.fail(
            "floor_count",
            f"Expected {expected_floors} floors, found {actual_floors}"
        )

    # 6. Coverage limit
    total_area = sum(r.width * r.length for r in rooms)
    max_area = max_buildable_area(land_size_perches)
    if total_area > max_area:
        result.fail(
            "coverage_ratio",
            f"Total built-up area {total_area:.1f} sqft exceeds maximum {max_area:.1f} sqft "
            f"(65% of {land_size_perches} perches)"
        )

    # 7. Required rooms
    room_types = {r.room_type.lower() for r in rooms}
    if not any("living" in rt for rt in room_types):
        result.fail("missing_room", "Design is missing a living room.")
    if not any("kitchen" in rt for rt in room_types):
        result.fail("missing_room", "Design is missing a kitchen.")
    if not any("bathroom" in rt or "bath" in rt for rt in room_types):
        result.fail("missing_room", "Design is missing a bathroom.")

    # 8. Sanity limits — no room larger than 50×50 ft
    for room in rooms:
        if room.width > 50 or room.length > 50:
            result.fail(
                "impossible_dimensions",
                f"Room '{room.room_type}' has unrealistic dimensions: {room.width}x{room.length}"
            )

    return result


def _rooms_overlap(a: RoomLayout, b: RoomLayout) -> bool:
    """
    Check if two axis-aligned rectangles overlap.
    Uses the separating axis theorem: two rectangles DON'T overlap if
    one is completely to the left, right, above, or below the other.
    A small epsilon prevents false positives from shared walls.
    """
    epsilon = 0.01  # Allow rooms to share walls without being flagged as overlapping

    a_right = a.x + a.width
    b_right = b.x + b.width
    a_top = a.y + a.length
    b_top = b.y + b.length

    # No overlap if separated along X or Y
    if a_right <= b.x + epsilon or b_right <= a.x + epsilon:
        return False
    if a_top <= b.y + epsilon or b_top <= a.y + epsilon:
        return False

    return True
