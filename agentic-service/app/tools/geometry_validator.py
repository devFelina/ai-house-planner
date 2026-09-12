"""
Deterministic geometry validation for house designs.

Why deterministic validation instead of relying on the LLM:
- LLMs cannot guarantee non-overlapping room coordinates
- Validation catches impossible dimensions before they reach the database
- Provides structured feedback for the revision flow

All checks are rule-based — no AI involved.
"""
from typing import List
from math import isfinite
from app.design.plot_constraints import PlotConstraints
from app.design.adjacency import shared_wall, exterior_segments, graph_for, reachable, road_access_clear
from app.design.room_rules import rule_for, room_kind, CIRCULATION_TYPES, MIN_COMPACTNESS
from app.schemas.design_result import DesignResult
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
    *,
    plot: PlotConstraints | None = None,
    design: DesignResult | None = None,
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

    if any(not all(isfinite(v) for v in (r.x, r.y, r.width, r.length, r.area_sqft or 0)) for r in rooms):
        result.fail('invalid_dimensions', 'Geometry must contain only finite numbers.')
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

    _validate_spatial_rules(result, rooms, expected_floors, plot, design)
    return result


def _validate_spatial_rules(result: GeometryValidationResult, rooms: List[RoomLayout],
                            expected_floors: int, plot: PlotConstraints | None,
                            design: DesignResult | None) -> None:
    if len({r.room_id for r in rooms}) != len(rooms):
        result.fail('duplicate_room_id', 'Room IDs must be unique across all floors.')
    if {r.floor for r in rooms} != set(range(1, expected_floors+1)):
        result.fail('floor_count', 'Floors must be contiguous starting at 1.')
    for room in rooms:
        rule = rule_for(room.room_type)
        dims, minimum = sorted((room.width, room.length)), sorted((rule.min_width, rule.min_length))
        if dims[0] < minimum[0]-0.001 or dims[1] < minimum[1]-0.001:
            result.fail('minimum_dimensions', f'{room.name} is below conceptual minimum dimensions.')
        if dims[0] > 0 and dims[1]/dims[0] > rule.aspect_limit:
            result.fail('aspect_ratio', f'{room.name} is excessively narrow.')
        if room.x < -0.001 or room.y < -0.001 or (plot and
                (room.x+room.width > plot.buildable_width+0.001 or room.y+room.length > plot.buildable_length+0.001)):
            result.fail('building_bounds', f'{room.name} lies outside the buildable boundary.')
        for opening in room.doors + room.windows:
            span = room.width if opening.wall in ('north', 'south') else room.length
            if not all(isfinite(v) for v in (opening.offset, opening.width)) or opening.offset < 0 or opening.width <= 0 or opening.offset+opening.width > span+0.001:
                result.fail('opening_bounds', f'{room.name} has an opening outside its wall.')
    # Geometric components are checked even for legacy callers without metadata.
    for floor in range(1, expected_floors+1):
        rs = [r for r in rooms if r.floor == floor]
        if not rs:
            continue
        graph = {r.room_id: {b.room_id for b in rs if r != b and shared_wall(r, b)} for r in rs}
        if len(reachable(graph, rs[0].room_id)) != len(rs):
            result.fail('disconnected_layout', f'Floor {floor} has disconnected room components.')
        if not any(room_kind(r.room_type) not in CIRCULATION_TYPES | {'balcony', 'veranda', 'utility', 'bathroom'} for r in rs):
            result.fail('floor_utilisation', f'Floor {floor} contains no meaningful habitable spaces.')
        bbox = (max(r.x+r.width for r in rs)-min(r.x for r in rs))*(max(r.y+r.length for r in rs)-min(r.y for r in rs))
        if bbox > 0 and sum(r.width*r.length for r in rs)/bbox < MIN_COMPACTNESS:
            result.fail('footprint_compactness', f'Floor {floor} is unreasonably scattered.')
        if expected_floors > 1 and not any(room_kind(r.room_type) == 'staircase' for r in rs):
            result.fail('stair_requirement', f'Floor {floor} needs a staircase.')
    if not design:
        # Legacy room-only inspection cannot certify door accessibility. Production
        # callers must pass the complete design to receive full certification.
        return
    total = sum(r.width*r.length for r in rooms)
    ground = sum(r.width*r.length for r in rooms if r.floor == 1)
    if abs(design.total_built_up_area_sqft-total) > 0.1 or (design.ground_footprint_sqft is not None and abs(design.ground_footprint_sqft-ground) > 0.1):
        result.fail('area_mismatch', 'Reported design totals do not match room geometry.')
    if design.floor_count != expected_floors:
        result.fail('floor_count', 'Design floor_count differs from the request.')
    if plot and ground > plot.maximum_ground_footprint+0.01:
        result.fail('ground_footprint', 'Ground footprint exceeds the plot limit.')
    by_id = {r.room_id: r for r in rooms}
    verified = []
    for connection in design.connections:
        a, b = by_id.get(connection.from_room), by_id.get(connection.to_room)
        if not a or not b or a.room_id == b.room_id:
            result.fail('invalid_connection', 'Connection references missing/identical rooms.')
            continue
        if connection.kind == 'stair':
            if (room_kind(a.room_type) != 'staircase' or room_kind(b.room_type) != 'staircase'
                    or abs(a.floor-b.floor) != 1 or
                    any(abs(getattr(a, key)-getattr(b, key)) > 0.001 for key in ('x', 'y', 'width', 'length'))):
                result.fail('stair_requirement', 'Stair connections must align across consecutive floors.')
                continue
        else:
            wall = shared_wall(a, b)
            if not wall:
                result.fail('invalid_connection', 'Door connection lacks a shared wall of sufficient width.')
                continue
            side, lo, hi = wall
            from app.design.adjacency import OPPOSITE
            def intervals(room: RoomLayout, side: str) -> list[tuple[float, float]]:
                origin = room.x if side in ('north', 'south') else room.y
                return [(origin+d.offset, origin+d.offset+d.width) for d in room.doors if d.wall == side]
            if not any(min(a1, b1, hi)-max(a0, b0, lo) >= 3-0.001
                       for a0, a1 in intervals(a, side) for b0, b1 in intervals(b, OPPOSITE[side])):
                result.fail('invalid_connection', 'Connection needs matching door openings on both rooms.')
                continue
        verified.append(connection)
    graph = graph_for(rooms, verified)
    valid_entrances = []
    for entrance in design.entrances:
        r = by_id.get(entrance.room_id)
        if not all(isfinite(v) for v in (entrance.offset, entrance.width)) or entrance.width < 3 or entrance.offset < 0:
            result.fail('entrance', 'Entrance needs a finite opening at least 3 ft wide.')
            continue
        if not r or r.floor != 1 or not any(wall == entrance.wall and lo <= entrance.offset+0.001 and hi >= entrance.offset+entrance.width-0.001
                                           for wall, lo, hi in exterior_segments(r, rooms)):
            result.fail('entrance', 'Entrance must open onto a ground-floor exterior wall.')
            continue
        if not any(d.wall == entrance.wall and abs(d.offset-entrance.offset) < 0.001 and d.width >= entrance.width for d in r.doors):
            result.fail('entrance', 'Entrance metadata must match a rendered door.')
            continue
        if plot and (entrance.wall != plot.road_side or not road_access_clear(r, rooms, entrance.wall, entrance.offset, entrance.width)):
            result.fail('entrance_access', 'Entrance must have a clear access strip toward the road.')
            continue
        valid_entrances.append(r.room_id)
    if not valid_entrances:
        result.fail('entrance', 'A ground-floor exterior entrance is required.')
        return
    accessible = set().union(*(reachable(graph, key) for key in valid_entrances))
    if len(accessible) != len(rooms):
        result.fail('accessibility', 'Every room must be reachable from the entrance through actual connections.')
    private_ids = {r.room_id for r in rooms if room_kind(r.room_type) in ('bedroom', 'bathroom', 'home_office')}
    for r in rooms:
        blocked = private_ids - {r.room_id}
        if r.room_type == 'bathroom_attached':
            blocked -= {b.room_id for b in rooms if b.room_type == 'bedroom_1'}
        if not any(r.room_id in reachable(graph, key, blocked) for key in valid_entrances):
            result.fail('privacy_access', f'{r.name} requires passage through an unrelated private room.')
    for a, b, strength in (design.program or {}).get('adjacency_preferences', []):
        if strength != 'required':
            continue
        ra = next((r for r in rooms if r.room_type == a), None)
        rb = next((r for r in rooms if r.room_type == b), None)
        if not ra or not rb or rb.room_id not in graph[ra.room_id]:
            result.fail('required_adjacency', f'{a} must connect directly to {b}.')
    for spec in (design.program or {}).get('rooms', []):
        matching = [r for r in rooms if r.room_type == spec['room_type'] and r.floor == spec['floor']]
        if not matching:
            result.fail('spatial_program', f"Missing requested space {spec['id']} on floor {spec['floor']}.")
    # Exterior exposure is a preference, reflected in scoring rather than a code claim.


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
