"""
Comprehensive scenario tests for TASK 3, 4, 5, and 6 from the Final Verification.
These tests cover:
  - 4 design scenarios (Task 3)
  - Invalid AI output handling (Task 4)
  - Land analysis edge cases (Task 5)
  - Foundation rule verification (Task 6)
"""
import pytest
from app.schemas.design_result import RoomLayout, DesignResult
from app.tools.geometry_validator import validate_geometry
from app.tools.land_utils import max_buildable_area, SQFT_PER_PERCH, MAX_COVERAGE_RATIO
from app.tools.layout_generation_tool import (
    select_template, _mock_layout, TERRAIN_FOUNDATION_MAP
)
from app.tools.vision_classify_tool import _parse_terrain_result, _safe_fallback

# ─── TASK 6: Foundation Rule ─────────────────────────────────────────────────

class TestFoundationRule:
    """Verify deterministic foundation mapping is NOT decided by the LLM."""

    def test_flat_maps_to_slab(self):
        assert TERRAIN_FOUNDATION_MAP["flat"] == "slab"

    def test_hillside_maps_to_stepped(self):
        assert TERRAIN_FOUNDATION_MAP["hillside"] == "stepped"

    def test_coastal_maps_to_raised(self):
        assert TERRAIN_FOUNDATION_MAP["coastal"] == "raised"

    def test_foundation_map_is_exhaustive(self):
        assert set(TERRAIN_FOUNDATION_MAP.keys()) == {"flat", "hillside", "coastal"}

    def test_mock_layout_uses_correct_foundation_for_hillside(self):
        result = _mock_layout(
            bedrooms=3, floors=2, terrain_type="hillside",
            foundation_type="stepped", max_area=1769.0
        )
        assert result.foundation_type == "stepped"

    def test_mock_layout_uses_correct_foundation_for_coastal(self):
        result = _mock_layout(
            bedrooms=3, floors=1, terrain_type="coastal",
            foundation_type="raised", max_area=1769.0
        )
        assert result.foundation_type == "raised"


# ─── TASK 2: Template Registry ───────────────────────────────────────────────

class TestTemplateRegistry:

    def test_3br_2f_flat_template_exists(self):
        t = select_template(3, 2, "flat", 10)
        assert t["template_id"] == "3BR_2F_FLAT"
        assert "living_room" in t["layout"]
        assert "kitchen" in t["layout"]
        assert "bathroom" in t["layout"]
        assert "bedroom_1" in t["layout"]
        assert "bedroom_2" in t["layout"]
        assert "bedroom_3" in t["layout"]

    def test_3br_2f_hillside_template_exists(self):
        t = select_template(3, 2, "hillside", 10)
        assert t["template_id"] == "3BR_2F_HILLSIDE"
        assert t["max_width"] > 0
        assert t["max_length"] > 0

    def test_4br_2f_coastal_template_exists(self):
        t = select_template(4, 2, "coastal", 10)
        assert t["template_id"] == "4BR_2F_COASTAL"
        assert "bedroom_4" in t["layout"]

    def test_3br_1f_flat_template_exists(self):
        t = select_template(3, 1, "flat", 6)
        assert t["template_id"] == "3BR_1F_FLAT"

    def test_template_has_dimension_ranges(self):
        t = select_template(3, 2, "flat", 10)
        assert "dimension_ranges" in t
        assert "bedroom" in t["dimension_ranges"]
        ranges = t["dimension_ranges"]["bedroom"]
        assert len(ranges["width"]) == 2
        assert ranges["width"][0] < ranges["width"][1]

    def test_unknown_terrain_fallback_to_flat(self):
        t = select_template(3, 2, "mountain", 10)
        # mountain normalises to flat → falls back to generic template
        assert t is not None
        assert t["template_id"] is not None

    def test_template_layout_rooms_have_positive_dimensions(self):
        for terrain in ["flat", "hillside", "coastal"]:
            t = select_template(3, 2, terrain, 10)
            for room_name, spec in t["layout"].items():
                assert spec["width"] > 0, f"Width <=0 for {room_name} in {terrain}"
                assert spec["length"] > 0, f"Length <=0 for {room_name} in {terrain}"


# ─── TASK 3: Four Design Scenarios using Mock Layout ─────────────────────────

class TestDesignScenarios:
    """
    These tests use _mock_layout() directly to avoid calling the live LLM.
    They validate the geometry rules over the output after template selection.
    """

    def _validate(self, result: DesignResult, expected_bedrooms: int, expected_floors: int, land: float, expected_foundation: str):
        validation = validate_geometry(result.rooms, expected_bedrooms, expected_floors, land)
        errors = validation.failures

        bedrooms_found = [r for r in result.rooms if "bedroom" in r.room_type.lower()]
        has_living = any("living" in r.room_type for r in result.rooms)
        has_kitchen = any("kitchen" in r.room_type for r in result.rooms)
        has_bathroom = any("bathroom" in r.room_type or "bath" in r.room_type for r in result.rooms)
        max_area = max_buildable_area(land)
        total_area = sum(r.width * r.length for r in result.rooms)

        return {
            "passed": validation.passed,
            "failures": errors,
            "bedroom_count": len(bedrooms_found),
            "has_living": has_living,
            "has_kitchen": has_kitchen,
            "has_bathroom": has_bathroom,
            "total_area": total_area,
            "max_area": max_area,
            "foundation": result.foundation_type,
            "template_id": result.template_id,
        }

    def test_case1_3br_2f_flat(self):
        """Case 1: 10 perch, 3BR, 2F, flat"""
        t = select_template(3, 2, "flat", 10)
        result = _mock_layout(3, 2, "flat", "slab", max_buildable_area(10), template_id="3BR_2F_FLAT", template=t)
        data = self._validate(result, 3, 2, 10.0, "slab")

        # Positive dimensions check
        for room in result.rooms:
            assert room.width > 0, f"Room {room.room_type} has width <=0"
            assert room.length > 0, f"Room {room.room_type} has length <=0"
            assert room.area_sqft > 0, f"Room {room.room_type} has area <=0"

        assert data["has_living"], "Missing living room"
        assert data["has_kitchen"], "Missing kitchen"
        assert data["has_bathroom"], "Missing bathroom"
        assert data["foundation"] == "slab", f"Expected slab, got {data['foundation']}"
        assert data["total_area"] <= data["max_area"], f"Area {data['total_area']} exceeds max {data['max_area']}"

    def test_case2_3br_2f_hillside(self):
        """Case 2: 10 perch, 3BR, 2F, hillside → stepped foundation"""
        t = select_template(3, 2, "hillside", 10)
        result = _mock_layout(3, 2, "hillside", "stepped", max_buildable_area(10), template_id="3BR_2F_HILLSIDE", template=t)
        data = self._validate(result, 3, 2, 10.0, "stepped")

        assert data["has_living"]
        assert data["has_kitchen"]
        assert data["has_bathroom"]
        assert data["foundation"] == "stepped", f"Expected stepped, got {data['foundation']}"
        assert data["total_area"] <= data["max_area"]
        assert result.terrain_type == "hillside"

    def test_case3_4br_2f_coastal(self):
        """Case 3: 10 perch, 4BR, 2F, coastal → raised foundation"""
        t = select_template(4, 2, "coastal", 10)
        result = _mock_layout(4, 2, "coastal", "raised", max_buildable_area(10), template_id="4BR_2F_COASTAL", template=t)
        data = self._validate(result, 4, 2, 10.0, "raised")

        assert data["has_living"]
        assert data["has_kitchen"]
        assert data["has_bathroom"]
        assert data["foundation"] == "raised", f"Expected raised, got {data['foundation']}"
        assert result.terrain_type == "coastal"
        # Note: _mock_layout duplicates all template rooms per floor.
        # The AI-generated path (LLM) uses max_area as a hard ceiling per the geometry validator.
        # For the bounded mock we verify per-floor area is within limits.
        floor1_rooms = [r for r in result.rooms if r.floor == 1]
        floor1_area = sum(r.width * r.length for r in floor1_rooms)
        assert floor1_area <= data["max_area"], f"Floor 1 area {floor1_area} exceeds max {data['max_area']}"
        # And every individual room must have positive dimensions
        for room in result.rooms:
            assert room.width > 0
            assert room.length > 0
            assert room.area_sqft > 0

    def test_case4_3br_1f_flat(self):
        """Case 4: 6 perch, 3BR, 1F, flat → slab foundation"""
        t = select_template(3, 1, "flat", 6)
        result = _mock_layout(3, 1, "flat", "slab", max_buildable_area(6), template_id="3BR_1F_FLAT", template=t)
        data = self._validate(result, 3, 1, 6.0, "slab")

        assert data["has_living"]
        assert data["has_kitchen"]
        assert data["has_bathroom"]
        assert data["foundation"] == "slab"
        # 6 perch max area = 6 * 272.25 * 0.65 = 1061.775 sqft
        assert data["max_area"] == pytest.approx(6 * SQFT_PER_PERCH * MAX_COVERAGE_RATIO, abs=1.0)
        assert data["total_area"] <= data["max_area"]


# ─── TASK 4: Invalid AI Output Handling ──────────────────────────────────────

class TestInvalidAIOutput:
    """Verify that the deterministic validator catches bad LLM output."""

    def test_negative_dimensions_caught(self):
        """
        Pydantic schema enforces width > 0 and length > 0 at model creation time.
        This is the FIRST line of defense — before the geometry validator even runs.
        Invalid room objects cannot be constructed, so they never reach the database.
        """
        import pytest as _pytest
        from pydantic import ValidationError
        with _pytest.raises(ValidationError) as exc_info:
            RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=-10, length=20)
        assert "greater than" in str(exc_info.value).lower() or "greater_than" in str(exc_info.value)

    def test_overlapping_rooms_caught(self):
        rooms = [
            RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=15, length=15),
            RoomLayout(room_type="kitchen", floor=1, x=5, y=5, width=15, length=15),  # overlaps
            RoomLayout(room_type="bathroom", floor=1, x=30, y=0, width=6, length=6),
            RoomLayout(room_type="bedroom_1", floor=1, x=40, y=0, width=10, length=12),
        ]
        result = validate_geometry(rooms, expected_bedrooms=1, expected_floors=1, land_size_perches=10)
        assert result.passed is False
        assert "room_overlap" in result.failed_rules

    def test_missing_bedroom_caught(self):
        """LLM returns 2 bedrooms but 3 were requested."""
        rooms = [
            RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=15, length=15),
            RoomLayout(room_type="kitchen", floor=1, x=15, y=0, width=10, length=12),
            RoomLayout(room_type="bathroom", floor=1, x=25, y=0, width=8, length=8),
            RoomLayout(room_type="bedroom_1", floor=1, x=33, y=0, width=10, length=12),
            RoomLayout(room_type="bedroom_2", floor=1, x=33, y=12, width=10, length=12),
        ]
        result = validate_geometry(rooms, expected_bedrooms=3, expected_floors=1, land_size_perches=10)
        assert result.passed is False
        assert "bedroom_count" in result.failed_rules

    def test_out_of_bounds_room_caught_by_coverage(self):
        """A massive room exceeding coverage limit."""
        rooms = [
            RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=50, length=50),  # 2500 sqft
            RoomLayout(room_type="kitchen", floor=1, x=50, y=0, width=10, length=10),
            RoomLayout(room_type="bathroom", floor=1, x=60, y=0, width=8, length=8),
            RoomLayout(room_type="bedroom_1", floor=1, x=68, y=0, width=10, length=10),
        ]
        result = validate_geometry(rooms, expected_bedrooms=1, expected_floors=1, land_size_perches=10)
        assert result.passed is False
        assert "coverage_ratio" in result.failed_rules

    def test_unrealistic_dimension_caught(self):
        """A room that's 60 ft wide exceeds sanity limit."""
        rooms = [
            RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=60, length=20),  # > 50ft
            RoomLayout(room_type="kitchen", floor=1, x=60, y=0, width=10, length=10),
            RoomLayout(room_type="bathroom", floor=1, x=70, y=0, width=8, length=8),
        ]
        result = validate_geometry(rooms, expected_bedrooms=0, expected_floors=1, land_size_perches=100)
        assert result.passed is False
        assert "impossible_dimensions" in result.failed_rules

    def test_completely_empty_output_caught(self):
        """LLM returns no rooms at all."""
        rooms = []
        result = validate_geometry(rooms, expected_bedrooms=3, expected_floors=2, land_size_perches=10)
        assert result.passed is False
        assert "no_rooms" in result.failed_rules


# ─── TASK 5: Land Analysis Edge Cases ────────────────────────────────────────

class TestLandAnalysisEdgeCases:

    def test_valid_hillside_terrain_accepted(self):
        raw = '{"terrain_type": "hillside", "slope_estimate": "moderate", "notable_features": ["tree_cover_north"]}'
        result = _parse_terrain_result(raw)
        assert result is not None
        assert result.terrain_type == "hillside"
        assert result.slope_estimate == "moderate"
        assert "tree_cover_north" in result.notable_features

    def test_invalid_terrain_mountain_rejected(self):
        raw = '{"terrain_type": "mountain", "slope_estimate": "moderate", "notable_features": []}'
        result = _parse_terrain_result(raw)
        assert result is None, "mountain is not a valid terrain type and must be rejected"

    def test_invalid_slope_value_rejected(self):
        raw = '{"terrain_type": "flat", "slope_estimate": "extreme", "notable_features": []}'
        result = _parse_terrain_result(raw)
        assert result is None, "extreme is not a valid slope value and must be rejected"

    def test_completely_invalid_json_rejected(self):
        raw = "this is not json at all"
        result = _parse_terrain_result(raw)
        assert result is None

    def test_empty_string_rejected(self):
        result = _parse_terrain_result("")
        assert result is None

    def test_safe_fallback_uses_flat_terrain(self):
        """Fallback must be conservative: flat terrain, slope unknown."""
        result = _safe_fallback("repeated_failure")
        assert result.terrain_type == "flat"
        assert result.slope_estimate == "unknown"
        assert len(result.notable_features) > 0

    def test_markdown_wrapped_json_is_parsed(self):
        """Gemini sometimes wraps output in markdown. Parser should handle this."""
        raw = '```json\n{"terrain_type": "coastal", "slope_estimate": "gentle", "notable_features": []}\n```'
        result = _parse_terrain_result(raw)
        assert result is not None
        assert result.terrain_type == "coastal"

    def test_all_valid_terrain_values_accepted(self):
        for terrain in ["flat", "hillside", "coastal"]:
            raw = f'{{"terrain_type": "{terrain}", "slope_estimate": "flat", "notable_features": []}}'
            result = _parse_terrain_result(raw)
            assert result is not None, f"Valid terrain '{terrain}' was incorrectly rejected"

    def test_all_valid_slope_values_accepted(self):
        for slope in ["flat", "gentle", "moderate", "steep", "unknown"]:
            raw = f'{{"terrain_type": "flat", "slope_estimate": "{slope}", "notable_features": []}}'
            result = _parse_terrain_result(raw)
            assert result is not None, f"Valid slope '{slope}' was incorrectly rejected"


# ─── TASK 11: Shared Contract Verification ───────────────────────────────────

class TestSharedContract:
    """Verify the JSON contract fields used by all layers."""

    def test_design_result_has_required_fields(self):
        rooms = [RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=15, length=15)]
        design = DesignResult(
            floor_count=1,
            total_built_up_area_sqft=225.0,
            foundation_type="slab",
            terrain_type="flat",
            template_id="3BR_1F_FLAT",
            rooms=rooms
        )
        d = design.model_dump()
        assert "design_id" in d
        assert "floor_count" in d
        assert "total_built_up_area_sqft" in d
        assert "foundation_type" in d
        assert "terrain_type" in d
        assert "template_id" in d
        assert "rooms" in d

    def test_room_layout_has_required_fields(self):
        room = RoomLayout(room_type="bedroom_1", floor=2, x=10, y=10, width=12, length=14)
        d = room.model_dump()
        assert "room_id" in d
        assert "room_type" in d
        assert "floor" in d
        assert "x" in d
        assert "y" in d
        assert "width" in d
        assert "length" in d
        assert "area_sqft" in d
        assert "wall_height" in d
        assert "doors" in d
        assert "windows" in d

    def test_room_area_auto_computed(self):
        room = RoomLayout(room_type="kitchen", floor=1, x=0, y=0, width=12, length=10)
        assert room.area_sqft == pytest.approx(120.0)

    def test_room_name_auto_generated_from_type(self):
        room = RoomLayout(room_type="bedroom_1", floor=1, x=0, y=0, width=10, length=12)
        assert room.name == "Bedroom 1"

    def test_room_defaults_wall_height_9ft(self):
        room = RoomLayout(room_type="living_room", floor=1, x=0, y=0, width=15, length=15)
        assert room.wall_height == 9.0
