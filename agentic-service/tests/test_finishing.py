import pytest
from app.design.geometry.finishing import finish_generative_layout
from app.schemas.design_result import DesignResult, RoomLayout
from app.design.program.spatial_program import SpatialProgram, RoomIntent, EntranceIntent

def test_single_floor_finishing():
    # Construct a simple geometry:
    # living (0,0, 20,20)
    # hallway (20,0, 10,20)
    # bed1 (30,0, 15,10)
    # bed2 (30,10, 15,10)
    # bath (45,0, 10,10)
    
    rooms = [
        RoomLayout(room_id="living", room_type="living_room", floor=1, x=0, y=0, width=20, length=20),
        RoomLayout(room_id="hallway", room_type="hallway", floor=1, x=20, y=0, width=10, length=20),
        RoomLayout(room_id="bed1", room_type="bedroom", floor=1, x=30, y=0, width=15, length=10),
        RoomLayout(room_id="bed2", room_type="bedroom", floor=1, x=30, y=10, width=15, length=10),
        RoomLayout(room_id="bath", room_type="bathroom", floor=1, x=45, y=0, width=10, length=10)
    ]
    design = DesignResult(floor_count=1, foundation_type="slab", rooms=rooms)
    
    program = SpatialProgram(
        concept="Test", floor_count=1,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=400, min_area_sqft=400, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="hallway", type="hallway", floor=1, zone="CIRCULATION", target_area_sqft=200, min_area_sqft=200, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bed1", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=150, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bed2", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=150, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bath", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=False, privacy_level="LOW")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        reason_codes=[]
    )
    
    finished, meta = finish_generative_layout(design, program)
    
    assert not meta["finishing_failures"]
    assert meta["entrance_room"] == "living"
    
    # Check graph
    from app.design.geometry.adjacency import graph_for
    graph = graph_for(finished.rooms, finished.connections)
    
    # bed1 and bed2 should connect to hallway, not to each other
    assert "hallway" in graph["bed1"]
    assert "hallway" in graph["bed2"]
    
    # bath should connect to bed1 (only neighbor)
    assert "bed1" in graph["bath"]

def test_failure_disconnected():
    rooms = [
        RoomLayout(room_id="living", room_type="living_room", floor=1, x=0, y=0, width=20, length=20),
        RoomLayout(room_id="bed", room_type="bedroom", floor=1, x=30, y=0, width=10, length=10), # Gap of 10ft
    ]
    design = DesignResult(floor_count=1, foundation_type="slab", rooms=rooms)
    program = SpatialProgram(
        concept="Test", floor_count=1,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=400, min_area_sqft=400, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="bed", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=100, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        reason_codes=[]
    )
    finished, meta = finish_generative_layout(design, program)
    assert "ROOM_UNREACHABLE" in meta["finishing_failures"]

def test_orientation():
    # If preferred_side is WEST
    rooms = [
        RoomLayout(room_id="living", room_type="living_room", floor=1, x=10, y=10, width=20, length=20),
    ]
    design = DesignResult(floor_count=1, foundation_type="slab", rooms=rooms)
    program = SpatialProgram(
        concept="Test", floor_count=1,
        rooms=[RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=400, min_area_sqft=400, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW")],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="WEST", connect_to="living"),
        reason_codes=[]
    )
    finished, meta = finish_generative_layout(design, program)
    assert finished.entrances[0].wall == "west"

