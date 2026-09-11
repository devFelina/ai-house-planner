"""
Deterministic layout templates for house designs.

Why templates instead of free-form LLM generation:
- LLMs cannot reliably generate non-overlapping room coordinates
- Templates ensure rooms fit within boundaries and don't overlap
- The AI selects and adapts a template rather than inventing coordinates
- Each template is a proven room arrangement for a given bedroom/floor/terrain combo

Templates define room positions relative to a grid.
All dimensions are in feet. The AI can scale dimensions within bounded ranges.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from app.schemas.design_result import RoomLayout, Opening


@dataclass
class RoomSpec:
    """Specification for a single room in a template."""
    room_type: str
    name: str
    floor: int
    x: float
    y: float
    width: float
    length: float
    doors: List[Dict] = field(default_factory=list)
    windows: List[Dict] = field(default_factory=list)


@dataclass
class LayoutTemplate:
    """A complete deterministic room arrangement."""
    template_id: str
    bedroom_count: int
    floor_count: int
    terrain_compatibility: List[str]  # ["flat", "hillside", "coastal"]
    foundation_type: str
    rooms: List[RoomSpec] = field(default_factory=list)
    description: str = ""


def _make_opening(wall: str, offset: float, width: float) -> Dict:
    return {"wall": wall, "offset": offset, "width": width}


# ============================================================
# 3 BEDROOM / 1 FLOOR TEMPLATES
# ============================================================

TEMPLATE_3BR_1F_FLAT = LayoutTemplate(
    template_id="3BR_1F_FLAT",
    bedroom_count=3,
    floor_count=1,
    terrain_compatibility=["flat"],
    foundation_type="slab",
    description="3 bedroom single-floor home for flat terrain",
    rooms=[
        # Row 1 (y=0): Living + Kitchen + Dining
        RoomSpec("living_room", "Living Room", 1, 0, 0, 16, 14,
                 doors=[_make_opening("south", 5, 4)],
                 windows=[_make_opening("west", 4, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 16, 0, 12, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("south", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 28, 0, 12, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("east", 3, 4)]),
        # Row 2 (y=14): Bedrooms + Bathrooms
        RoomSpec("bedroom_1", "Master Bedroom", 1, 0, 14, 16, 13,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 4, 5)]),
        RoomSpec("bathroom_1", "Master Bathroom", 1, 16, 14, 8, 8,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_2", "Bedroom 2", 1, 24, 14, 13, 13,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_2", "Bathroom", 1, 16, 22, 8, 5,
                 doors=[_make_opening("east", 1, 3)],
                 windows=[]),
        RoomSpec("bedroom_3", "Bedroom 3", 1, 37, 14, 13, 13,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("east", 3, 4)]),
    ]
)

TEMPLATE_3BR_1F_HILLSIDE = LayoutTemplate(
    template_id="3BR_1F_HILLSIDE",
    bedroom_count=3,
    floor_count=1,
    terrain_compatibility=["hillside"],
    foundation_type="stepped",
    description="3 bedroom single-floor home for hillside terrain with stepped foundation",
    rooms=[
        # Compact layout for hillside — narrower, deeper footprint
        RoomSpec("living_room", "Living Room", 1, 0, 0, 16, 14,
                 doors=[_make_opening("south", 5, 4)],
                 windows=[_make_opening("west", 3, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 16, 0, 10, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("east", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 26, 0, 10, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("east", 3, 4)]),
        RoomSpec("bedroom_1", "Master Bedroom", 1, 0, 14, 14, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_1", "Bathroom", 1, 14, 14, 8, 7,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_2", "Bedroom 2", 1, 22, 14, 14, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bedroom_3", "Bedroom 3", 1, 0, 26, 14, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("west", 3, 4)]),
        RoomSpec("bathroom_2", "Bathroom 2", 1, 14, 21, 8, 5,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[]),
    ]
)

TEMPLATE_3BR_1F_COASTAL = LayoutTemplate(
    template_id="3BR_1F_COASTAL",
    bedroom_count=3,
    floor_count=1,
    terrain_compatibility=["coastal"],
    foundation_type="raised",
    description="3 bedroom single-floor home for coastal terrain with raised foundation",
    rooms=[
        # Same layout as flat but with raised foundation
        RoomSpec("living_room", "Living Room", 1, 0, 0, 16, 14,
                 doors=[_make_opening("south", 5, 4)],
                 windows=[_make_opening("west", 4, 5), _make_opening("north", 3, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 16, 0, 12, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("south", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 28, 0, 10, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("east", 3, 4)]),
        RoomSpec("bedroom_1", "Master Bedroom", 1, 0, 14, 14, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_1", "Bathroom", 1, 14, 14, 8, 7,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_2", "Bedroom 2", 1, 22, 14, 12, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bedroom_3", "Bedroom 3", 1, 0, 26, 14, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_2", "Bathroom 2", 1, 14, 21, 8, 5,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[]),
    ]
)


# ============================================================
# 3 BEDROOM / 2 FLOOR TEMPLATES
# ============================================================

TEMPLATE_3BR_2F_FLAT = LayoutTemplate(
    template_id="3BR_2F_FLAT",
    bedroom_count=3,
    floor_count=2,
    terrain_compatibility=["flat"],
    foundation_type="slab",
    description="3 bedroom two-floor home for flat terrain",
    rooms=[
        # Ground Floor
        RoomSpec("living_room", "Living Room", 1, 0, 0, 16, 14,
                 doors=[_make_opening("south", 5, 4)],
                 windows=[_make_opening("west", 4, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 16, 0, 12, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("south", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 0, 14, 12, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_1", "Guest Bathroom", 1, 12, 14, 8, 7,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("staircase", "Staircase", 1, 20, 14, 8, 12,
                 doors=[_make_opening("west", 2, 3), _make_opening("south", 2, 3)],
                 windows=[]),
        # Upper Floor
        RoomSpec("bedroom_1", "Master Bedroom", 2, 0, 0, 16, 14,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 4, 5), _make_opening("west", 3, 4)]),
        RoomSpec("bathroom_2", "Master Bathroom", 2, 16, 0, 8, 8,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_2", "Bedroom 2", 2, 0, 14, 14, 12,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("west", 3, 4)]),
        RoomSpec("bedroom_3", "Bedroom 3", 2, 14, 14, 14, 12,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("east", 3, 4)]),
        RoomSpec("staircase_upper", "Staircase", 2, 16, 8, 8, 6,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[]),
    ]
)

TEMPLATE_3BR_2F_HILLSIDE = LayoutTemplate(
    template_id="3BR_2F_HILLSIDE",
    bedroom_count=3,
    floor_count=2,
    terrain_compatibility=["hillside"],
    foundation_type="stepped",
    description="3 bedroom two-floor split-level home for hillside terrain",
    rooms=[
        # Ground Floor (lower level on hillside)
        RoomSpec("living_room", "Living Room", 1, 0, 0, 16, 13,
                 doors=[_make_opening("south", 5, 4)],
                 windows=[_make_opening("west", 3, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 16, 0, 10, 13,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("east", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 0, 13, 12, 10,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_1", "Guest Bathroom", 1, 12, 13, 7, 6,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("staircase", "Staircase", 1, 19, 13, 7, 10,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[]),
        # Upper Floor (upper level on hillside)
        RoomSpec("bedroom_1", "Master Bedroom", 2, 0, 0, 14, 13,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 5), _make_opening("west", 3, 4)]),
        RoomSpec("bathroom_2", "Master Bathroom", 2, 14, 0, 7, 7,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_2", "Bedroom 2", 2, 0, 13, 13, 10,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("west", 3, 4)]),
        RoomSpec("bedroom_3", "Bedroom 3", 2, 13, 13, 13, 10,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("east", 3, 4)]),
        RoomSpec("staircase_upper", "Staircase", 2, 14, 7, 7, 6,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[]),
    ]
)

TEMPLATE_3BR_2F_COASTAL = LayoutTemplate(
    template_id="3BR_2F_COASTAL",
    bedroom_count=3,
    floor_count=2,
    terrain_compatibility=["coastal"],
    foundation_type="raised",
    description="3 bedroom two-floor home for coastal terrain with raised pile foundation",
    rooms=[
        # Ground Floor
        RoomSpec("living_room", "Living Room", 1, 0, 0, 15, 13,
                 doors=[_make_opening("south", 4, 4)],
                 windows=[_make_opening("west", 3, 5), _make_opening("north", 3, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 15, 0, 10, 13,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("south", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 0, 13, 12, 10,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_1", "Guest Bathroom", 1, 12, 13, 7, 6,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[]),
        RoomSpec("staircase", "Staircase", 1, 19, 13, 6, 10,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[]),
        # Upper Floor
        RoomSpec("bedroom_1", "Master Bedroom", 2, 0, 0, 14, 13,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 5), _make_opening("west", 3, 4)]),
        RoomSpec("bathroom_2", "Master Bathroom", 2, 14, 0, 7, 7,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_2", "Bedroom 2", 2, 0, 13, 13, 10,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bedroom_3", "Bedroom 3", 2, 13, 13, 12, 10,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("east", 3, 4)]),
        RoomSpec("staircase_upper", "Staircase", 2, 14, 7, 7, 6,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[]),
    ]
)


# ============================================================
# 4 BEDROOM / 2 FLOOR TEMPLATES
# ============================================================

TEMPLATE_4BR_2F_FLAT = LayoutTemplate(
    template_id="4BR_2F_FLAT",
    bedroom_count=4,
    floor_count=2,
    terrain_compatibility=["flat"],
    foundation_type="slab",
    description="4 bedroom two-floor home for flat terrain",
    rooms=[
        # Ground Floor
        RoomSpec("living_room", "Living Room", 1, 0, 0, 18, 14,
                 doors=[_make_opening("south", 6, 4)],
                 windows=[_make_opening("west", 4, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 18, 0, 12, 14,
                 doors=[_make_opening("west", 5, 3)],
                 windows=[_make_opening("south", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 0, 14, 14, 12,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bedroom_1", "Bedroom 1 (Guest)", 1, 14, 14, 14, 12,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("east", 3, 4)]),
        RoomSpec("bathroom_1", "Guest Bathroom", 1, 28, 14, 7, 7,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("staircase", "Staircase", 1, 28, 0, 7, 14,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[]),
        # Upper Floor
        RoomSpec("bedroom_2", "Master Bedroom", 2, 0, 0, 16, 14,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 4, 5), _make_opening("west", 3, 4)]),
        RoomSpec("bathroom_2", "Master Bathroom", 2, 16, 0, 8, 8,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_3", "Bedroom 3", 2, 0, 14, 14, 12,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("west", 3, 4)]),
        RoomSpec("bedroom_4", "Bedroom 4", 2, 14, 14, 14, 12,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("east", 3, 4)]),
        RoomSpec("bathroom_3", "Bathroom", 2, 16, 8, 8, 6,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("staircase_upper", "Staircase", 2, 24, 0, 7, 8,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[]),
    ]
)

TEMPLATE_4BR_2F_HILLSIDE = LayoutTemplate(
    template_id="4BR_2F_HILLSIDE",
    bedroom_count=4,
    floor_count=2,
    terrain_compatibility=["hillside"],
    foundation_type="stepped",
    description="4 bedroom two-floor split-level home for hillside terrain",
    rooms=[
        # Ground Floor
        RoomSpec("living_room", "Living Room", 1, 0, 0, 16, 13,
                 doors=[_make_opening("south", 5, 4)],
                 windows=[_make_opening("west", 3, 5)]),
        RoomSpec("dining_room", "Dining Room", 1, 16, 0, 10, 13,
                 doors=[_make_opening("west", 4, 3)],
                 windows=[_make_opening("east", 3, 4)]),
        RoomSpec("kitchen", "Kitchen", 1, 0, 13, 12, 10,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bedroom_1", "Bedroom 1 (Guest)", 1, 12, 13, 12, 10,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bathroom_1", "Guest Bathroom", 1, 24, 13, 7, 6,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[]),
        RoomSpec("staircase", "Staircase", 1, 24, 0, 7, 13,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[]),
        # Upper Floor
        RoomSpec("bedroom_2", "Master Bedroom", 2, 0, 0, 14, 13,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 5), _make_opening("west", 3, 4)]),
        RoomSpec("bathroom_2", "Master Bathroom", 2, 14, 0, 7, 7,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("bedroom_3", "Bedroom 3", 2, 0, 13, 12, 10,
                 doors=[_make_opening("east", 2, 3)],
                 windows=[_make_opening("north", 3, 4)]),
        RoomSpec("bedroom_4", "Bedroom 4", 2, 12, 13, 12, 10,
                 doors=[_make_opening("west", 2, 3)],
                 windows=[_make_opening("north", 3, 4), _make_opening("east", 3, 4)]),
        RoomSpec("bathroom_3", "Bathroom", 2, 14, 7, 7, 6,
                 doors=[_make_opening("west", 1, 3)],
                 windows=[_make_opening("east", 2, 3)]),
        RoomSpec("staircase_upper", "Staircase", 2, 21, 0, 7, 7,
                 doors=[_make_opening("south", 2, 3)],
                 windows=[]),
    ]
)


# ============================================================
# TEMPLATE REGISTRY
# ============================================================

ALL_TEMPLATES: List[LayoutTemplate] = [
    TEMPLATE_3BR_1F_FLAT,
    TEMPLATE_3BR_1F_HILLSIDE,
    TEMPLATE_3BR_1F_COASTAL,
    TEMPLATE_3BR_2F_FLAT,
    TEMPLATE_3BR_2F_HILLSIDE,
    TEMPLATE_3BR_2F_COASTAL,
    TEMPLATE_4BR_2F_FLAT,
    TEMPLATE_4BR_2F_HILLSIDE,
]


def select_template(
    bedrooms: int,
    floors: int,
    terrain_type: str,
) -> Optional[LayoutTemplate]:
    """
    Select the best matching template for the given requirements.
    Exact match on bedroom_count and floor_count, then prefer terrain match.
    Falls back to any terrain-compatible template if no exact match.
    """
    # Exact match
    for t in ALL_TEMPLATES:
        if (t.bedroom_count == bedrooms
                and t.floor_count == floors
                and terrain_type in t.terrain_compatibility):
            return t

    # Fallback: match bedrooms and floors, ignore terrain
    for t in ALL_TEMPLATES:
        if t.bedroom_count == bedrooms and t.floor_count == floors:
            return t

    # Fallback: match floors, closest bedroom count
    candidates = [t for t in ALL_TEMPLATES if t.floor_count == floors]
    if candidates:
        # Pick the one with closest bedroom count
        candidates.sort(key=lambda t: abs(t.bedroom_count - bedrooms))
        return candidates[0]

    # Last resort: return the first template
    return ALL_TEMPLATES[0] if ALL_TEMPLATES else None


def template_to_rooms(template: LayoutTemplate) -> List[RoomLayout]:
    """Convert a LayoutTemplate's room specs into RoomLayout Pydantic models."""
    rooms = []
    for spec in template.rooms:
        room = RoomLayout(
            room_type=spec.room_type,
            name=spec.name,
            floor=spec.floor,
            x=spec.x,
            y=spec.y,
            width=spec.width,
            length=spec.length,
            doors=[Opening(**d) for d in spec.doors],
            windows=[Opening(**w) for w in spec.windows],
        )
        rooms.append(room)
    return rooms
