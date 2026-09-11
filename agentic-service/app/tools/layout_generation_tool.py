"""
Template-based layout generation tool.

This has been rewritten to use Agentic AI (Google Gemini) instead of deterministic templates.
The tool prompts the LLM to generate an appropriate room layout and runs geometry validation.
It will retry up to 3 times if the validation fails.
"""
import json
from app.schemas.design_result import DesignResult, RoomLayout
from app.tools.geometry_validator import validate_geometry
from app.tools.land_utils import max_buildable_area
from app.config import GOOGLE_API_KEY


# Foundation selection based on terrain
TERRAIN_FOUNDATION_MAP = {
    "flat": "slab",
    "hillside": "stepped",
    "coastal": "raised",
}


def select_template(bedrooms: int, floors: int, terrain_type: str, land_size_perches: float):
    """
    Return a lightweight bounded template registry used as the starting design concept.
    This is intentionally small and practical for university demo work: a tiny set of
    templates keyed by bedrooms, floor count, and terrain, with bounded room ranges.
    """
    normalized_terrain = (terrain_type or "flat").lower()
    if normalized_terrain not in ("flat", "hillside", "coastal"):
        normalized_terrain = "flat"

    registry = {
        # ----------------------------------------------------------------
        # 3 Bedroom, 2 Floor, Flat terrain
        # Bottom row: public zone. Top row: private zone.
        # Every room shares at least one wall with a neighbour.
        # ----------------------------------------------------------------
        "3BR_2F_FLAT": {
            "template_id": "3BR_2F_FLAT",
            "max_width": 35,
            "max_length": 26,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 15, "length": 14},
                "kitchen":     {"x": 15, "y": 0, "width": 10, "length": 14},
                "bedroom_1":   {"x": 25, "y": 0, "width": 10, "length": 14},
                "bathroom":    {"x": 0, "y": 14, "width": 8, "length": 8},
                "bedroom_2":   {"x": 8, "y": 14, "width": 10, "length": 12},
                "bedroom_3":   {"x": 18, "y": 14, "width": 10, "length": 12},
            },
            "dimension_ranges": {
                "living_room": {"width": [12, 18], "length": [12, 16]},
                "kitchen": {"width": [8, 12], "length": [10, 14]},
                "bathroom": {"width": [6, 10], "length": [6, 10]},
                "bedroom": {"width": [9, 12], "length": [10, 14]},
            },
        },
        # ----------------------------------------------------------------
        # 3 Bedroom, 2 Floor, Hillside terrain — compact for stepped foundation
        # ----------------------------------------------------------------
        "3BR_2F_HILLSIDE": {
            "template_id": "3BR_2F_HILLSIDE",
            "max_width": 34,
            "max_length": 26,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 14, "length": 14},
                "kitchen":     {"x": 14, "y": 0, "width": 10, "length": 14},
                "bedroom_1":   {"x": 24, "y": 0, "width": 10, "length": 14},
                "bathroom":    {"x": 0, "y": 14, "width": 8, "length": 8},
                "bedroom_2":   {"x": 8, "y": 14, "width": 10, "length": 12},
                "bedroom_3":   {"x": 18, "y": 14, "width": 10, "length": 12},
            },
            "dimension_ranges": {
                "living_room": {"width": [12, 16], "length": [12, 16]},
                "kitchen": {"width": [8, 12], "length": [10, 14]},
                "bathroom": {"width": [6, 10], "length": [6, 10]},
                "bedroom": {"width": [9, 12], "length": [10, 14]},
            },
        },
        # ----------------------------------------------------------------
        # 4 Bedroom, 2 Floor, Coastal terrain — compact for raised foundation
        # ----------------------------------------------------------------
        "4BR_2F_COASTAL": {
            "template_id": "4BR_2F_COASTAL",
            "max_width": 38,
            "max_length": 26,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 16, "length": 14},
                "kitchen":     {"x": 16, "y": 0, "width": 10, "length": 14},
                "bedroom_1":   {"x": 26, "y": 0, "width": 10, "length": 14},
                "bathroom":    {"x": 0, "y": 14, "width": 8, "length": 8},
                "bedroom_2":   {"x": 8, "y": 14, "width": 10, "length": 12},
                "bedroom_3":   {"x": 18, "y": 14, "width": 10, "length": 12},
                "bedroom_4":   {"x": 28, "y": 14, "width": 10, "length": 12},
            },
            "dimension_ranges": {
                "living_room": {"width": [14, 18], "length": [12, 16]},
                "kitchen": {"width": [8, 12], "length": [10, 14]},
                "bathroom": {"width": [6, 10], "length": [6, 10]},
                "bedroom": {"width": [9, 12], "length": [10, 14]},
            },
        },
        # ----------------------------------------------------------------
        # 3 Bedroom, 1 Floor, Flat terrain — single story
        # ----------------------------------------------------------------
        "3BR_1F_FLAT": {
            "template_id": "3BR_1F_FLAT",
            "max_width": 35,
            "max_length": 26,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 14, "length": 14},
                "kitchen":     {"x": 14, "y": 0, "width": 10, "length": 14},
                "bedroom_1":   {"x": 24, "y": 0, "width": 10, "length": 14},
                "bathroom":    {"x": 0, "y": 14, "width": 8, "length": 8},
                "bedroom_2":   {"x": 8, "y": 14, "width": 10, "length": 12},
                "bedroom_3":   {"x": 18, "y": 14, "width": 10, "length": 12},
            },
            "dimension_ranges": {
                "living_room": {"width": [12, 16], "length": [12, 16]},
                "kitchen": {"width": [8, 12], "length": [10, 14]},
                "bathroom": {"width": [6, 10], "length": [6, 10]},
                "bedroom": {"width": [8, 12], "length": [10, 14]},
            },
        },
    }

    template_key = f"{bedrooms}BR_{floors}F_{normalized_terrain.upper()}"
    if template_key in registry:
        return registry[template_key]

    generic_key = f"{max(1, bedrooms)}BR_{max(1, floors)}F_{normalized_terrain.upper()}"
    if generic_key in registry:
        return registry[generic_key]

    # Fallback — same tight two-row layout pattern
    return {
        "template_id": f"{bedrooms}BR_{floors}F_{normalized_terrain.upper()}",
        "max_width": 35,
        "max_length": 26,
        "layout": {
            "living_room": {"x": 0, "y": 0, "width": 15, "length": 14},
            "kitchen":     {"x": 15, "y": 0, "width": 10, "length": 14},
            "bathroom":    {"x": 0, "y": 14, "width": 8, "length": 8},
        },
        "dimension_ranges": {
            "living_room": {"width": [12, 18], "length": [12, 16]},
            "kitchen": {"width": [8, 12], "length": [10, 14]},
            "bathroom": {"width": [6, 10], "length": [6, 10]},
            "bedroom": {"width": [9, 12], "length": [10, 14]},
        },
    }


SYSTEM_PROMPT = """You are the Design Agent of an AI-Assisted Home Design & Cost Planner.

Your responsibility is to generate a VALID conceptual 2D house floor plan based on:

* land size
* terrain type
* requested number of bedrooms
* requested number of floors
* homeowner preferences
* a bounded template selected by the application

This is a university-level planning and estimation system. The generated design is NOT construction-ready architectural documentation. It is a conceptual floor plan used for visualization, cost estimation, validation, and design revision.

IMPORTANT:
The application uses deterministic geometry validation after your response. Therefore, correctness and constraint satisfaction are more important than creativity.

## 1. OUTPUT FORMAT

Return ONLY valid JSON.

Do NOT return:

* Markdown
* explanations
* comments
* ```json code blocks
* additional fields outside the required structure

Return exactly this structure:

{
  "floor_count": 2,
  "total_built_up_area_sqft": 1500,
  "rooms": [
    {
      "room_type": "living_room",
      "name": "Living Room",
      "floor": 1,
      "x": 0,
      "y": 0,
      "width": 15,
      "length": 16
    }
  ]
}

Each room MUST contain:

* room_type
* name
* floor
* x
* y
* width
* length

Use integer values for x, y, width and length.

## 2. DESIGN INPUTS

The application will provide:

* bedrooms: required number of bedrooms
* floors: required number of floors
* land_size_perches: available land size
* terrain_type: flat, hillside, or coastal
* max_buildable_area_sqft: maximum permitted built-up area
* selected_template: bounded template selected by the application
* template_bounds: maximum width and length
* template_layout: starting room arrangement
* dimension_ranges: permitted room dimension ranges

You MUST respect these constraints.

## 3. TEMPLATE-BASED DESIGN

The selected template is the primary design structure.

DO NOT invent a completely different building layout.

Use the selected template as the starting point and make only reasonable adaptations needed to satisfy the user's requirements.

The template provides:

* room types
* approximate room positions
* building proportions
* maximum width
* maximum length
* acceptable room dimension ranges

Keep the generated design within the template's overall bounds.

Do NOT move rooms outside the template boundary.

Do NOT create unnecessary rooms unless they are required to make the requested design valid.

## 4. REQUIRED ROOMS

Every design MUST contain:

* exactly the requested number of bedrooms
* at least one living_room
* at least one kitchen
* at least one bathroom

Bedroom room types MUST be named:

bedroom_1
bedroom_2
bedroom_3
...

For example, if bedrooms = 3:

bedroom_1
bedroom_2
bedroom_3

Do NOT generate bedroom_4 when only 3 bedrooms were requested.

## 5. FLOOR DISTRIBUTION

The requested number of floors MUST be respected.

If floors = 1:

* All rooms must be on floor 1.

If floors = 2:

* Rooms may be distributed between floor 1 and floor 2.
* The total number of bedrooms across the entire house must equal the requested bedroom count.
* Do NOT duplicate the same bedroom on both floors.

Prefer a practical distribution.

For example, for a 3-bedroom, 2-floor house:

* Floor 1: living room, kitchen, bathroom, 1 bedroom
* Floor 2: 2 bedrooms, bathroom if appropriate

However, follow the selected template when it provides a better distribution.

## 6. ROOM GEOMETRY

Every room MUST be an axis-aligned rectangle.

Coordinates represent the bottom-left corner.

Rules:

* x >= 0
* y >= 0
* width > 0
* length > 0
* width and length must normally be at least 4 ft
* width and length must be integers

Rooms on the SAME FLOOR:

* MUST NOT overlap
* MAY share walls
* MAY touch at their boundaries

CRITICAL ADJACENCY RULE:

Every room MUST share at least one full wall edge with at least one other room on the same floor.

A wall is shared when one room's edge exactly meets another room's edge along the same axis.

For example, this is valid wall sharing:

Room A: x=0, y=0, width=15, length=14
Room B: x=15, y=0, width=10, length=14

Room A's right edge (x=15) meets Room B's left edge (x=15). They share a wall.

Room C: x=0, y=14, width=8, length=8

Room C's bottom edge (y=14) meets Room A's top edge (y=0+14=14). They share a wall.

This is INVALID (scattered rooms with gaps):

Room A: x=0, y=0, width=15, length=16
Room B: x=25, y=5, width=10, length=12

There is a 10 ft gap between them. This is NOT a real house.

The rooms must tile together to form a single connected building footprint with no empty gaps between rooms. Use a two-row grid pattern:

* Bottom row: public rooms (living room, kitchen) placed side by side sharing walls at their x boundaries, all starting at y=0 with the same length.
* Top row: private rooms (bedrooms, bathroom) placed side by side sharing walls at their x boundaries, starting at y = bottom row length.
* The bottom row and top row share a horizontal wall where they meet.

This produces a compact rectangular or L-shaped building.

## 7. BUILDING BOUNDARY

All rooms must fit within the selected template's maximum dimensions.

The application provides:

max_width
max_length

Therefore:

x + width <= max_width

y + length <= max_length

Do NOT place rooms outside these boundaries.

Prefer a compact rectangular or L-shaped building footprint.

Avoid scattered rooms. NO GAPS between rooms.

## 8. ROOM DIMENSIONS

Follow the provided dimension ranges whenever possible.

For example:

bedroom:
width = 9-14 ft
length = 10-14 ft

kitchen:
width = 8-12 ft
length = 8-14 ft

bathroom:
width = 6-10 ft
length = 6-10 ft

living room:
width = 12-18 ft
length = 12-18 ft

Do not make rooms unnecessarily large.

The purpose is to create a realistic conceptual house while keeping construction area and estimated cost reasonable.

## 9. BUILT-UP AREA

Calculate:

room_area = width * length

The total built-up area is the sum of the areas of all generated rooms.

The total MUST NOT exceed:

max_buildable_area_sqft

Set:

total_built_up_area_sqft

to the calculated sum of room areas.

Do NOT invent a total area.

Do NOT simply copy the example value of 1200.

## 10. LAND SIZE

The available land size is given in perches.

1 perch = 272.25 sq ft.

The design must remain within the permitted buildable area calculated by the application.

Do NOT create a house larger than the available buildable area.

A smaller practical design is acceptable.

## 11. ARCHITECTURAL FLOW

Within the limitations of the selected template:

* Living room should be close to the main entrance.
* Kitchen should be adjacent to or reasonably close to the living room.
* Bedrooms should have reasonable privacy from the main living area.
* Bathrooms should be accessible.
* Avoid placing rooms in isolated or disconnected positions.
* Keep the overall layout compact and practical.

Do not sacrifice geometry validity to achieve architectural flow.

## 12. TERRAIN

Terrain type is supplied by the application.

The application separately determines the foundation type using deterministic rules:

flat -> slab
hillside -> stepped
coastal -> raised

Do NOT generate or modify foundation information.

Your responsibility is the room layout only.

For hillside terrain:

* Prefer a compact layout suitable for stepped construction.
* Avoid unnecessarily wide or irregular footprints.

For coastal terrain:

* Prefer a compact layout suitable for raised construction.
* Do not introduce unsupported structural assumptions.

For flat terrain:

* Prefer a conventional compact footprint.

## 13. DESIGN REVISION

Sometimes a previous design and a revision reason will be provided.

If a previous design is supplied:

* Treat it as the design being revised.
* Preserve valid aspects where possible.
* Fix the specific validation or user-reported problem.
* Do NOT repeat the same geometry error.
* Stay within the selected template bounds.
* Continue satisfying the original bedroom, floor, land and area requirements.

The revision must produce a new valid layout rather than simply repeating the previous layout.

## 14. VALIDATION PRIORITY

Before returning your answer, internally check:

1. JSON is valid.
2. floor_count equals the requested floors.
3. Exactly the requested number of bedrooms exists.
4. Living room exists.
5. Kitchen exists.
6. Bathroom exists.
7. Every room has positive dimensions.
8. No same-floor rooms overlap.
9. Every room is inside the template bounds.
10. Total room area does not exceed max_buildable_area_sqft.
11. Coordinates and dimensions are integers.
12. Room dimensions stay within the supplied ranges where possible.

If any condition fails, fix the design before returning it.

## 15. IMPORTANT BEHAVIOR

Do NOT:

* invent random coordinates
* create overlapping rooms
* duplicate bedrooms across floors
* exceed the land/buildable-area constraint
* exceed template boundaries
* create construction-level structural details
* return doors/windows unless explicitly requested by the output schema
* return explanations
* return invalid JSON

The deterministic validator is the final authority for geometry.

Your goal is to produce a simple, valid, realistic and renderable conceptual floor plan that can be stored in PostgreSQL and displayed by the React SVG viewer and Flutter CustomPainter.

Return ONLY the JSON object.
"""

def generate_layout(
    land_size_perches: float,
    terrain_type: str,
    preferences: dict,
    previous_design: dict | None = None,
    revision_reason: str | None = None,
) -> DesignResult:
    """
    Generate a house layout using a small template registry to bound the creative AI output.
    The AI is still allowed to adapt within those limits before the final geometry validation runs.
    """
    bedrooms = preferences.get("bedrooms", 3)
    floors = preferences.get("floors", 2)
    max_area = max_buildable_area(land_size_perches)

    # Normalize terrain
    terrain_type = terrain_type.lower()
    if terrain_type not in ("flat", "hillside", "coastal"):
        terrain_type = "flat"

    # Select foundation
    foundation_type = TERRAIN_FOUNDATION_MAP.get(terrain_type, "slab")
    template = select_template(bedrooms, floors, terrain_type, land_size_perches)
    template_id = template["template_id"]

    user_prompt = f"""Generate the conceptual house floor plan using the selected bounded template.

PROJECT REQUIREMENTS:

* Bedrooms: {bedrooms}
* Floors: {floors}
* Terrain: {terrain_type}
* Land size: {land_size_perches} perches
* Maximum buildable area: {max_area} sqft

SELECTED TEMPLATE:

* Template ID: {template_id}
* Maximum building width: {template['max_width']} ft
* Maximum building length: {template['max_length']} ft

STARTING TEMPLATE LAYOUT (use these exact positions as a starting point):
{json.dumps(template['layout'], indent=2)}

ALLOWED ROOM DIMENSION RANGES:
{json.dumps(template['dimension_ranges'], indent=2)}

CRITICAL LAYOUT RULES:

1. Use the template layout above as-is or with MINIMAL adjustments.
2. Every room MUST share at least one full wall with another room. NO isolated rooms. NO gaps between rooms.
3. Place rooms in a two-row grid:
   - Bottom row (y=0): public rooms (living room, kitchen, optionally one bedroom) side by side, all with the SAME length (height).
   - Top row (y=bottom row length): private rooms (bedrooms, bathroom) side by side, all with the SAME length (height).
4. Adjacent rooms in the same row must share a vertical wall: Room A ends at x=N, Room B starts at x=N.
5. The top row and bottom row share a horizontal wall where they meet at y = bottom row length.
6. Generate exactly {bedrooms} bedrooms named bedroom_1 through bedroom_{bedrooms}.
7. Generate exactly {floors} floor(s).
8. Include at least one living_room, one kitchen, and one bathroom.
9. Rooms on the same floor MUST NOT overlap.
10. Keep the total room area at or below {max_area} sqft.
11. Keep every room within bounds: x + width <= {template['max_width']} and y + length <= {template['max_length']}.
12. Return ONLY the required JSON structure. No markdown, no explanation.

Before returning the JSON, verify:
- All rooms share walls (no gaps).
- No rooms overlap.
- All rooms are inside the template bounds.
- Exactly {bedrooms} bedrooms exist.
- Total area <= {max_area}.
"""
    if previous_design and revision_reason:
        user_prompt += f"""
DESIGN REVISION REQUIRED:

The previous design failed validation.

Reason: {revision_reason}

Previous layout:
{json.dumps(previous_design.get('rooms', []) if isinstance(previous_design, dict) else [])}

Fix the specific problem stated above. Do NOT repeat the same geometry error.
Stay within the template bounds and satisfy all original requirements.
Return a corrected JSON layout.
"""

    # Loop up to 3 times to satisfy the geometry validator
    max_retries = 3
    last_validation = None
    last_design_result = None

    if not GOOGLE_API_KEY:
        print("[Layout Generator] No GOOGLE_API_KEY set. Falling back to bounded template mock.")
        return _mock_layout(bedrooms, floors, terrain_type, foundation_type, max_area, template_id=template_id, template=template)

    try:
        from google import genai
        client = genai.Client(api_key=GOOGLE_API_KEY)
    except ImportError:
        print("[Layout Generator] google-genai package not available. Returning mock.")
        return _mock_layout(bedrooms, floors, terrain_type, foundation_type, max_area)

    for attempt in range(max_retries):
        try:
            print(f"[Layout Generator] Attempt {attempt+1}/{max_retries} calling LLM...")
            result_text = _call_gemini_design(client, user_prompt)
            print("RAW TEXT:")
            print(result_text)
            parsed_data = _parse_design_result(result_text)
            
            if not parsed_data:
                user_prompt += "\n\nError: You did not return valid JSON. Please return ONLY JSON."
                continue

            rooms = [RoomLayout(**r) for r in parsed_data.get("rooms", [])]
            
            # Validate geometry locally
            validation = validate_geometry(rooms, bedrooms, floors, land_size_perches)
            
            total_area = sum(r.width * r.length for r in rooms)
            design_result = DesignResult(
                floor_count=parsed_data.get("floor_count", floors),
                total_built_up_area_sqft=round(total_area, 2),
                foundation_type=foundation_type,
                terrain_type=terrain_type,
                template_id=template_id,
                rooms=rooms,
            )

            if validation.passed:
                print(f"[Layout Generator] Attempt {attempt+1} passed validation.")
                return design_result
            
            print(f"[Layout Generator] Attempt {attempt+1} failed validation: {validation.failures}")
            last_validation = validation
            last_design_result = design_result
            
            # Add failure feedback to the prompt for the next iteration
            failures_str = "\\n".join(validation.failures)
            user_prompt += f"\n\nYOUR LAST DESIGN FAILED VALIDATION:\n{failures_str}\nPlease adjust coordinates and dimensions to fix this."

        except Exception as e:
            print(f"[Layout Generator] API error: {e}")
            import time
            time.sleep(2)
            continue

    # If we exhausted retries, return the last generated one (or a mock if it completely failed)
    if last_design_result:
        print(f"[Layout Generator] Exhausted retries. Returning invalid design with warnings.")
        return last_design_result

    print("[Layout Generator] Complete failure to generate. Returning safe bounded mock.")
    return _mock_layout(bedrooms, floors, terrain_type, foundation_type, max_area, template_id=template_id, template=template)

def _call_gemini_design(client, user_prompt: str) -> str:
    """Call Gemini API and return the raw text."""
    from google.genai import types

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part.from_text(text=SYSTEM_PROMPT),
                    types.Part.from_text(text=user_prompt),
                ]
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,  # Low temperature for deterministic layout
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )
    return response.text.strip()

def _parse_design_result(text: str) -> dict | None:
    """Parse raw LLM text into a dictionary. Handles markdown wrappers."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"[Layout Generator] Parse error: {e}")
        return None

def _mock_layout(
    bedrooms: int,
    floors: int,
    terrain_type: str,
    foundation_type: str,
    max_area: float,
    template_id: str | None = None,
    template: dict | None = None,
) -> DesignResult:
    """Safe fallback mock using the selected bounded template instead of random room placement."""
    room_specs = [
        ("living_room", "Living Room", 0, 0, 15, 16),
        ("kitchen", "Kitchen", 15, 0, 10, 12),
        ("bathroom", "Bathroom", 0, 16, 8, 8),
    ]

    if template and template.get("layout"):
        room_specs = []
        for key, values in template["layout"].items():
            room_type = key
            if room_type.startswith("bedroom_"):
                room_name = room_type.replace("_", " ").title()
            elif room_type == "bathroom":
                room_name = "Bathroom"
            elif room_type == "kitchen":
                room_name = "Kitchen"
            elif room_type == "living_room":
                room_name = "Living Room"
            else:
                room_name = room_type.replace("_", " ").title()
            room_specs.append((room_type, room_name, values["x"], values["y"], values["width"], values["length"]))

    rooms = []
    for floor in range(1, floors + 1):
        for index, spec in enumerate(room_specs):
            room_type, name, x, y, width, length = spec
            if room_type.startswith("bedroom_"):
                room_key = room_type
                if floor > 1:
                    room_key = f"{room_type}_upper"
            else:
                room_key = room_type
            rooms.append(RoomLayout(
                room_type=room_key,
                name=name,
                floor=floor,
                x=x,
                y=y if floor == 1 else y + 4,
                width=width,
                length=length,
            ))

    if len(rooms) < bedrooms:
        for i in range(1, bedrooms + 1):
            if not any(r.room_type == f"bedroom_{i}" for r in rooms):
                rooms.append(RoomLayout(
                    room_type=f"bedroom_{i}",
                    name=f"Bedroom {i}",
                    floor=1,
                    x=25 + ((i - 1) * 10),
                    y=0,
                    width=10,
                    length=12,
                ))

    return DesignResult(
        floor_count=floors,
        total_built_up_area_sqft=sum(r.width * r.length for r in rooms),
        foundation_type=foundation_type,
        terrain_type=terrain_type,
        template_id=template_id or "MOCK_FALLBACK",
        rooms=rooms,
    )
