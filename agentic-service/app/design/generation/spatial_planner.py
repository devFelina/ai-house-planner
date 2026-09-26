import json
import logging
import time
from typing import Any

from app.design.program.models import Requirements
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.spatial_program import SpatialProgram
from app.design.exceptions import GenerationFailure
from app.providers import get_available_design_provider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the HousePlanner Spatial Planning Agent.
ROLE:
Generate a semantic architectural spatial program based on the provided requirements and site constraints.
Do NOT generate room coordinates (x, y, width, length).
Reason about room types, zones, adjacencies, multi-floor allocation, privacy, and circulation.

CONSTRAINTS:
1. You MUST include exactly the requested number of bedrooms and bathrooms.
2. Ensure the total programmed area fits within the area_budget_sqft.
3. Use semantic positions (e.g., FRONT, REAR, CENTER) for room placement.
4. Rooms must be assigned to valid floors (1 to floor_count).
5. Output ONLY raw JSON matching the required schema.

ARCHITECTURAL PRIORITIES:
- Respect the requested space priority (e.g., compact, spacious living).
- Place public zones near the entrance.
- Ensure private zones have high privacy and are away from the road if possible.
- Group service zones (kitchen, utility) and wet zones (bathrooms) for plumbing efficiency.
"""

def _build_prompt(req: Requirements, plot: PlotConstraints, area_budget_sqft: float) -> str:
    # Build a compact structured input payload
    site = {
        "buildable_width": round(plot.buildable_width, 1),
        "buildable_depth": round(plot.buildable_length, 1),
        "road_side": plot.road_side.upper(),
        "north_direction": plot.north_direction.upper() if plot.north_direction else "UNKNOWN",
        "plot_class": plot.plot_class.upper(),
        "terrain": plot.terrain_type.upper(),
        "entrance_preference": plot.effective_entrance_side.upper()
    }
    
    house = {
        "floors": req.floors,
        "bedrooms": req.bedrooms,
        "bathrooms": req.bathrooms,
        "style": req.style,
        "open_plan": req.open_plan
    }
    
    features = {
        "separate_dining": req.dining_required,
        "master_bedroom": req.master_bedroom,
        "home_office": req.home_office,
        "parking": req.parking,
        "accessibility": req.accessibility,
        "utility_room": req.utility_room
    }
    
    priority = {
        "space": req.space_priority,
        "circulation": req.circulation_preference,
        "compact": req.compact_priority,
        "privacy": req.privacy_priority
    }

    payload = {
        "SITE": site,
        "HOUSE": house,
        "FEATURES": features,
        "PRIORITY": priority,
        "CONSTRAINTS": {
            "area_budget_sqft": round(area_budget_sqft, 1)
        }
    }
    return json.dumps(payload, separators=(',', ':'))


def _validate_spatial_program(program: SpatialProgram, req: Requirements, area_budget_sqft: float) -> None:
    # 1. Floor count match
    if program.floor_count != req.floors:
        raise ValueError(f"Expected {req.floors} floors, got {program.floor_count}.")
    
    # 2. Room counts
    bedrooms = [r for r in program.rooms if "bedroom" in r.type.lower()]
    bathrooms = [r for r in program.rooms if "bathroom" in r.type.lower() or "bath" in r.type.lower()]
    if len(bedrooms) != req.bedrooms:
        raise ValueError(f"Expected {req.bedrooms} bedrooms, got {len(bedrooms)}.")
    if len(bathrooms) != req.bathrooms:
        raise ValueError(f"Expected {req.bathrooms} bathrooms, got {len(bathrooms)}.")
    
    # 3. Features
    if req.dining_required and not any("dining" in r.type.lower() for r in program.rooms):
        raise ValueError("Requested separate dining but no dining room provided.")
    if req.home_office and not any("office" in r.type.lower() for r in program.rooms):
        raise ValueError("Requested home office but none provided.")
    
    # 4. Valid floors
    for room in program.rooms:
        if room.floor < 1 or room.floor > program.floor_count:
            raise ValueError(f"Room {room.id} assigned to invalid floor {room.floor}.")
            
    # 5. Adjacency references and unique IDs
    room_ids = set()
    for r in program.rooms:
        if r.id in room_ids:
            raise ValueError(f"Duplicate room ID '{r.id}'.")
        room_ids.add(r.id)
        
    for adj in program.adjacencies:
        if adj.room_a not in room_ids:
            raise ValueError(f"Adjacency references unknown room '{adj.room_a}'.")
        if adj.room_b not in room_ids:
            raise ValueError(f"Adjacency references unknown room '{adj.room_b}'.")
            
    # 6. Area budget
    total_target_area = sum(r.target_area_sqft for r in program.rooms)
    if total_target_area > area_budget_sqft * 1.1: # 10% leniency
        raise ValueError(f"Programmed area {total_target_area} exceeds budget {area_budget_sqft}.")
    if total_target_area <= 0:
        raise ValueError("Programmed area must be positive.")


def plan_spatial_program(req: Requirements, plot: PlotConstraints) -> tuple[SpatialProgram, dict[str, Any]]:
    # 1. Area budget calculation
    # Using 65% coverage limit (max_buildable_area from land_math)
    # Total available area depends on floors
    from app.land.land_math import max_buildable_area
    max_ground = min(max_buildable_area(plot.land_size_perches), plot.buildable_width * plot.buildable_length)
    area_budget_sqft = max_ground * req.floors * 0.9  # 90% of max theoretical box

    user_prompt = _build_prompt(req, plot, area_budget_sqft)
    
    # Track prompt size
    prompt_chars = len(user_prompt)
    logger.info("[SpatialPlanner] request_chars=%d", prompt_chars)

    provider = get_available_design_provider()
    if not provider:
        raise GenerationFailure("No LLM provider available for spatial planning.")

    start_time = time.time()
    try:
        # Ask for up to 1500 tokens. A spatial program might take ~800 tokens depending on room count.
        raw_json = provider.generate_json(SYSTEM_PROMPT, user_prompt, SpatialProgram, max_tokens=1500)
    except Exception as exc:
        raise GenerationFailure(f"Spatial planning failed: {exc}") from exc
        
    latency_ms = int((time.time() - start_time) * 1000)

    try:
        program = SpatialProgram.model_validate(raw_json)
        _validate_spatial_program(program, req, area_budget_sqft)
    except ValueError as exc:
        raise GenerationFailure(f"Validation failed on generated spatial program: {exc}") from exc

    metadata = {
        "provider": provider.provider_name,
        "model": provider.model_name,
        "latency_ms": latency_ms,
        "prompt_chars": prompt_chars,
        "area_budget_sqft": round(area_budget_sqft, 1),
        "total_target_area": sum(r.target_area_sqft for r in program.rooms)
    }
    
    return program, metadata
