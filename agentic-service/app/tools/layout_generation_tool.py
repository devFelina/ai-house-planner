from app.schemas.design_result import DesignResult, RoomLayout, Opening
import uuid

def generate_layout(land_size_perches: float, terrain_type: str, preferences: dict) -> DesignResult:
    """
    Rule-based layout generator.
    Avoids LLM hallucination of coordinates by adapting templates.
    """
    bedrooms = preferences.get('bedrooms', 3)
    floors = preferences.get('floors', 2)
    
    # 1 perch = 272.25 sqft
    total_land_sqft = land_size_perches * 272.25
    max_buildable_area = total_land_sqft * 0.65 # 65% coverage limit
    
    # Determine foundation based on terrain
    foundation_type = "terraced" if terrain_type == "hillside" else "slab_on_grade"
    if terrain_type == "coastal":
        foundation_type = "raised_pier"
        
    rooms = []
    
    # Base living area
    living_room = RoomLayout(
        room_type="living_room",
        floor=1,
        x=0.0, y=0.0,
        width=18.0, length=14.0,
        doors=[Opening(wall="south", offset=6.0, width=4.0)],
        windows=[Opening(wall="north", offset=4.0, width=6.0)]
    )
    rooms.append(living_room)
    
    # Base Kitchen
    kitchen = RoomLayout(
        room_type="kitchen",
        floor=1,
        x=18.0, y=0.0,
        width=12.0, length=14.0,
        doors=[Opening(wall="west", offset=5.0, width=3.0)],
        windows=[Opening(wall="east", offset=3.0, width=4.0)]
    )
    rooms.append(kitchen)
    
    # Add bedrooms based on preference
    for i in range(bedrooms):
        floor_num = 2 if floors > 1 and i > 0 else 1
        y_offset = 14.0 if floor_num == 1 else 0.0
        x_offset = i * 14.0
        
        bed = RoomLayout(
            room_type=f"bedroom_{i+1}",
            floor=floor_num,
            x=x_offset, y=y_offset,
            width=14.0, length=12.0,
            doors=[Opening(wall="south", offset=2.0, width=3.0)],
            windows=[Opening(wall="north", offset=4.0, width=4.0)]
        )
        rooms.append(bed)
        
    total_sqft = sum(r.width * r.length for r in rooms)
    
    return DesignResult(
        floor_count=floors,
        total_built_up_area_sqft=total_sqft,
        foundation_type=foundation_type,
        rooms=rooms
    )
