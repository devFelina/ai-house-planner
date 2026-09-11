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
        "3BR_2F_FLAT": {
            "template_id": "3BR_2F_FLAT",
            "max_width": 36,
            "max_length": 30,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 16, "length": 16},
                "kitchen": {"x": 16, "y": 0, "width": 10, "length": 12},
                "bathroom": {"x": 0, "y": 16, "width": 8, "length": 8},
                "bedroom_1": {"x": 26, "y": 0, "width": 10, "length": 12},
                "bedroom_2": {"x": 26, "y": 12, "width": 10, "length": 12},
                "bedroom_3": {"x": 8, "y": 16, "width": 12, "length": 10},
            },
            "dimension_ranges": {
                "living_room": {"width": [12, 18], "length": [12, 18]},
                "kitchen": {"width": [8, 12], "length": [8, 14]},
                "bathroom": {"width": [6, 10], "length": [6, 10]},
                "bedroom": {"width": [9, 12], "length": [10, 14]},
            },
        },
        "3BR_2F_HILLSIDE": {
            "template_id": "3BR_2F_HILLSIDE",
            "max_width": 38,
            "max_length": 32,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 16, "length": 16},
                "kitchen": {"x": 16, "y": 0, "width": 10, "length": 12},
                "bathroom": {"x": 0, "y": 16, "width": 8, "length": 8},
                "bedroom_1": {"x": 24, "y": 0, "width": 12, "length": 12},
                "bedroom_2": {"x": 24, "y": 12, "width": 12, "length": 12},
                "bedroom_3": {"x": 8, "y": 18, "width": 12, "length": 10},
            },
            "dimension_ranges": {
                "living_room": {"width": [12, 18], "length": [12, 18]},
                "kitchen": {"width": [8, 12], "length": [8, 14]},
                "bathroom": {"width": [6, 10], "length": [6, 10]},
                "bedroom": {"width": [9, 14], "length": [10, 14]},
            },
        },
        "4BR_2F_COASTAL": {
            "template_id": "4BR_2F_COASTAL",
            "max_width": 40,
            "max_length": 34,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 17, "length": 16},
                "kitchen": {"x": 17, "y": 0, "width": 11, "length": 12},
                "bathroom": {"x": 0, "y": 16, "width": 8, "length": 8},
                "bedroom_1": {"x": 25, "y": 0, "width": 12, "length": 12},
                "bedroom_2": {"x": 25, "y": 12, "width": 12, "length": 12},
                "bedroom_3": {"x": 8, "y": 18, "width": 10, "length": 10},
                "bedroom_4": {"x": 18, "y": 18, "width": 10, "length": 10},
            },
            "dimension_ranges": {
                "living_room": {"width": [14, 18], "length": [12, 18]},
                "kitchen": {"width": [9, 12], "length": [9, 13]},
                "bathroom": {"width": [6, 10], "length": [6, 10]},
                "bedroom": {"width": [9, 14], "length": [10, 14]},
            },
        },
        "3BR_1F_FLAT": {
            "template_id": "3BR_1F_FLAT",
            "max_width": 34,
            "max_length": 28,
            "layout": {
                "living_room": {"x": 0, "y": 0, "width": 15, "length": 16},
                "kitchen": {"x": 15, "y": 0, "width": 10, "length": 12},
                "bathroom": {"x": 0, "y": 16, "width": 8, "length": 8},
                "bedroom_1": {"x": 25, "y": 0, "width": 9, "length": 12},
                "bedroom_2": {"x": 25, "y": 12, "width": 9, "length": 12},
                "bedroom_3": {"x": 8, "y": 18, "width": 10, "length": 10},
            },
            "dimension_ranges": {
                "living_room": {"width": [12, 16], "length": [12, 18]},
                "kitchen": {"width": [8, 12], "length": [8, 14]},
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

    return {
        "template_id": f"{bedrooms}BR_{floors}F_{normalized_terrain.upper()}",
        "max_width": 36,
        "max_length": 32,
        "layout": {
            "living_room": {"x": 0, "y": 0, "width": 15, "length": 16},
            "kitchen": {"x": 15, "y": 0, "width": 10, "length": 12},
            "bathroom": {"x": 0, "y": 16, "width": 8, "length": 8},
        },
        "dimension_ranges": {
            "living_room": {"width": [12, 18], "length": [12, 18]},
            "kitchen": {"width": [8, 12], "length": [8, 14]},
            "bathroom": {"width": [6, 10], "length": [6, 10]},
            "bedroom": {"width": [9, 14], "length": [10, 14]},
        },
    }


SYSTEM_PROMPT = """You are an expert architectural AI agent responsible for generating house floor plans.

Your task is to generate a list of rooms with precise (x, y) coordinates and (width, length) dimensions.
You MUST output ONLY valid JSON. No markdown, no explanations, no code blocks.

You will be given the constraints:
- bedrooms: required number of bedrooms
- floors: required number of floors
- land_size_perches: the size of the land
- max_buildable_area_sqft: the maximum allowed total area of all rooms combined.

Rules for Room Layouts:
1. Every room must be an axis-aligned rectangle.
2. Coordinates (x, y) represent the bottom-left corner of the room.
3. Dimensions (width, length) must be positive integers (minimum 4 ft).
4. Rooms on the SAME FLOOR MUST NOT overlap. They can share walls (e.g. room1.x + room1.width == room2.x).
5. All rooms must fit within a logical house boundary. Try to align outer walls where possible to create a realistic rectangular or L-shaped building footprint.
6. The total area (sum of width * length of all rooms) MUST NOT exceed max_buildable_area_sqft.
7. You MUST include at least one 'living_room', one 'kitchen', and one 'bathroom'.
8. You MUST include exactly the requested number of 'bedroom's.
9. **Architectural Flow:** Ensure a logical flow. The living room should be near the entrance. The kitchen should be adjacent to or near the living room.
10. **Privacy:** Group bedrooms together and separate them from the main living areas if possible. Bathrooms should be accessible.

Return exactly this JSON structure:
{
  "floor_count": 1,
  "total_built_up_area_sqft": 1200,
  "rooms": [
    {
      "room_type": "living_room",
      "floor": 1,
      "x": 0,
      "y": 0,
      "width": 15,
      "length": 20
    }
  ]
}
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

    user_prompt = f"""
Please generate a floor plan with the following constraints:
- Bedrooms: {bedrooms}
- Floors: {floors}
- Terrain: {terrain_type}
- Max Buildable Area (sqft): {max_area}
- Selected template: {template_id}
- Use the template as the starting concept but adapt room dimensions and placement within the allowed ranges.
- Keep all rooms within the template's total plan bounds: width <= {template['max_width']} ft and length <= {template['max_length']} ft.
- Proposed room pattern starting point: {json.dumps(template['layout'])}
- Allowed room ranges: {json.dumps(template['dimension_ranges'])}
"""
    if previous_design and revision_reason:
        user_prompt += f"\nPREVIOUS REVISION FAILED VALIDATION:\nReason: {revision_reason}\nPlease fix the layout to avoid this error within the selected template bounds."

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
