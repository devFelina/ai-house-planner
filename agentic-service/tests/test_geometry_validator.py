import pytest
from app.tools.geometry_validator import validate_geometry, GeometryValidationResult
from app.schemas.design_result import RoomLayout, Opening

def test_validate_geometry_success():
    rooms = [
        RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=10, length=10),
        RoomLayout(room_type="kitchen", floor=1, x=10, y=0, width=10, length=10),
        RoomLayout(room_type="bathroom_1", floor=1, x=20, y=0, width=5, length=5),
        RoomLayout(room_type="bedroom_1", floor=2, x=0, y=0, width=10, length=10),
        RoomLayout(room_type="staircase", floor=1, x=0, y=10, width=6, length=10),
        RoomLayout(room_type="staircase", floor=2, x=0, y=10, width=6, length=10),
    ]
    result = validate_geometry(rooms, expected_bedrooms=1, expected_floors=2, land_size_perches=10.0)
    assert result.passed is True
    assert len(result.failures) == 0

def test_validate_geometry_missing_required_rooms():
    rooms = [
        RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=10, length=10),
        RoomLayout(room_type="bedroom_1", floor=1, x=10, y=0, width=10, length=10),
    ]
    result = validate_geometry(rooms, expected_bedrooms=1, expected_floors=1, land_size_perches=10.0)
    assert result.passed is False
    assert "missing_room" in result.failed_rules
    # missing kitchen and bathroom
    assert sum(1 for r in result.failed_rules if r == "missing_room") == 2

def test_validate_geometry_overlap():
    rooms = [
        RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=10, length=10),
        RoomLayout(room_type="kitchen", floor=1, x=5, y=5, width=10, length=10), # overlaps
        RoomLayout(room_type="bathroom_1", floor=1, x=20, y=0, width=5, length=5),
    ]
    result = validate_geometry(rooms, expected_bedrooms=0, expected_floors=1, land_size_perches=10.0)
    assert result.passed is False
    assert "room_overlap" in result.failed_rules

def test_validate_geometry_no_overlap_different_floors():
    rooms = [
        RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=10, length=10),
        RoomLayout(room_type="kitchen", floor=2, x=0, y=0, width=10, length=10), # same coords, diff floor
        RoomLayout(room_type="bathroom_1", floor=1, x=20, y=0, width=5, length=5),
    ]
    result = validate_geometry(rooms, expected_bedrooms=0, expected_floors=2, land_size_perches=10.0)
    assert "room_overlap" not in result.failed_rules
    assert not result.passed  # Separate floors do not excuse disconnected rooms or missing stairs.

def test_validate_geometry_exceeds_coverage():
    rooms = [
        RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=50, length=50), # 2500 sqft
        RoomLayout(room_type="kitchen", floor=1, x=50, y=0, width=10, length=10),
        RoomLayout(room_type="bathroom_1", floor=1, x=60, y=0, width=10, length=10),
    ]
    # 10 perches = 2722.5 sqft, 65% is ~1769 sqft. 2500 sqft > 1769 sqft
    result = validate_geometry(rooms, expected_bedrooms=0, expected_floors=1, land_size_perches=10.0)
    assert result.passed is False
    assert "coverage_ratio" in result.failed_rules
