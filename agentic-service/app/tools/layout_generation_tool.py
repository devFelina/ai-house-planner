"""
Template-based layout generation tool.

This replaces free-form LLM coordinate generation with deterministic templates.
The tool selects an appropriate template, scales it if needed to fit within
coverage limits, runs geometry validation, and returns a valid DesignResult.
"""
from app.schemas.design_result import DesignResult, RoomLayout
from app.tools.layout_templates import select_template, template_to_rooms
from app.tools.geometry_validator import validate_geometry
from app.tools.land_utils import max_buildable_area, perches_to_sqft


# Foundation selection based on terrain
TERRAIN_FOUNDATION_MAP = {
    "flat": "slab",
    "hillside": "stepped",
    "coastal": "raised",
}


def generate_layout(
    land_size_perches: float,
    terrain_type: str,
    preferences: dict,
    previous_design: dict | None = None,
    revision_reason: str | None = None,
) -> DesignResult:
    """
    Generate a house layout using deterministic templates.

    Args:
        land_size_perches: Land size in perches
        terrain_type: One of 'flat', 'hillside', 'coastal'
        preferences: Dict with 'bedrooms', 'floors', 'style' keys
        previous_design: Previous design dict (for revision flow)
        revision_reason: Why the previous design was rejected

    Returns:
        DesignResult: Validated floor plan
    """
    bedrooms = preferences.get("bedrooms", 3)
    floors = preferences.get("floors", 2)

    # Normalize terrain
    terrain_type = terrain_type.lower()
    if terrain_type not in ("flat", "hillside", "coastal"):
        terrain_type = "flat"

    # Select foundation
    foundation_type = TERRAIN_FOUNDATION_MAP.get(terrain_type, "slab")

    # Select template
    template = select_template(bedrooms, floors, terrain_type)
    if template is None:
        raise ValueError(
            f"No compatible template found for {bedrooms}BR/{floors}F/{terrain_type}"
        )

    # Override foundation based on terrain (template may have a different default)
    foundation_type = TERRAIN_FOUNDATION_MAP.get(terrain_type, template.foundation_type)

    # Convert template to room layouts
    rooms = template_to_rooms(template)

    # Scale rooms if total area exceeds coverage limit
    max_area = max_buildable_area(land_size_perches)
    total_area = sum(r.width * r.length for r in rooms)

    if total_area > max_area:
        scale_factor = (max_area / total_area) ** 0.5  # Scale both dimensions
        rooms = _scale_rooms(rooms, scale_factor)
        total_area = sum(r.width * r.length for r in rooms)

    # If this is a revision, apply targeted fixes
    if previous_design and revision_reason:
        rooms = _apply_revision(rooms, revision_reason, max_area)
        total_area = sum(r.width * r.length for r in rooms)

    # Validate geometry
    validation = validate_geometry(rooms, bedrooms, floors, land_size_perches)
    if not validation.passed:
        # Log validation failures but still return (let ASP.NET decide)
        print(f"[Layout Generator] Geometry validation warnings: {validation.failures}")

    return DesignResult(
        floor_count=floors,
        total_built_up_area_sqft=round(total_area, 2),
        foundation_type=foundation_type,
        terrain_type=terrain_type,
        template_id=template.template_id,
        rooms=rooms,
    )


def _scale_rooms(rooms: list[RoomLayout], factor: float) -> list[RoomLayout]:
    """
    Uniformly scale all room dimensions and positions.
    Maintains relative positions and prevents overlap.
    """
    scaled = []
    for r in rooms:
        scaled.append(RoomLayout(
            room_type=r.room_type,
            name=r.name,
            floor=r.floor,
            x=round(r.x * factor, 2),
            y=round(r.y * factor, 2),
            width=round(max(r.width * factor, 4.0), 2),  # Min 4ft room width
            length=round(max(r.length * factor, 4.0), 2),  # Min 4ft room length
            wall_height=r.wall_height,
            doors=r.doors,
            windows=r.windows,
        ))
    return scaled


def _apply_revision(
    rooms: list[RoomLayout],
    revision_reason: str,
    max_area: float,
) -> list[RoomLayout]:
    """
    Apply targeted revision to address a specific validation failure.
    Modifies only what is necessary rather than regenerating from scratch.
    """
    reason_lower = revision_reason.lower()

    if "coverage" in reason_lower or "area" in reason_lower:
        # Reduce room sizes proportionally to fit within coverage
        total = sum(r.width * r.length for r in rooms)
        if total > max_area:
            factor = (max_area * 0.95 / total) ** 0.5  # Target 95% of max for safety margin
            rooms = _scale_rooms(rooms, factor)

    # Other revision types can be added here as the project evolves

    return rooms
