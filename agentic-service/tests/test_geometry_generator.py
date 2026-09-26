from app.design.geometry.geometry_generator import generate_geometry, _normalize_room_type
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.spatial_program import SpatialProgram, RoomIntent, AdjacencyIntent, EntranceIntent, VerticalCoreIntent
from app.design.exceptions import GenerationFailure
import pytest

def mock_plot(road_side='south', w=40, l=50):
    return PlotConstraints.model_validate({
        'land_size_perches': 15,
        'plot_width_ft': w,
        'plot_length_ft': l,
        'road_side': road_side,
        'terrain_type': 'flat',
        'setbacks': {'front': 5, 'rear': 5, 'left': 5, 'right': 5},
    })

def test_simple_rectangular_case():
    plot = mock_plot()
    program = SpatialProgram(
        concept="Test", floor_count=1,
        rooms=[
            RoomIntent(id="r1", type="living", floor=1, zone="PUBLIC", target_area_sqft=200, min_area_sqft=150, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="r2", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="MEDIUM"),
            RoomIntent(id="r3", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=120, preferred_position="REAR_LEFT", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="r4", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=120, preferred_position="REAR_RIGHT", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="r5", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="HIGH")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="r1"),
        reason_codes=[]
    )
    
    result, meta = generate_geometry(program, plot)
    assert len(result.rooms) == 5
    assert meta["rooms_placed"] == 5
    
    # Overlap check (should be non-overlapping)
    rooms = result.rooms
    for i, a in enumerate(rooms):
        for b in rooms[i+1:]:
            assert not (a.x < b.x + b.width - 0.01 and a.x + a.width > b.x + 0.01 and
                        a.y < b.y + b.length - 0.01 and a.y + a.length > b.y + 0.01)

def test_realistic_3b2b():
    plot = mock_plot(w=60, l=80)
    program = SpatialProgram(
        concept="3B2B", floor_count=1,
        rooms=[
            RoomIntent(id="bed1", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=120, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bed2", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=120, preferred_position="REAR_LEFT", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bed3", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=120, preferred_position="REAR_RIGHT", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bath1", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="HIGH"),
            RoomIntent(id="bath2", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="HIGH"),
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=250, min_area_sqft=200, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=150, min_area_sqft=100, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="dining", type="dining", floor=1, zone="PUBLIC", target_area_sqft=150, min_area_sqft=100, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        reason_codes=[]
    )
    
    # Determinism check
    res1, meta1 = generate_geometry(program, plot)
    res2, meta2 = generate_geometry(program, plot)
    
    for r1, r2 in zip(res1.rooms, res2.rooms):
        assert r1.x == r2.x
        assert r1.y == r2.y
        assert r1.width == r2.width
        assert r1.length == r2.length

def test_orientation():
    plot_south = mock_plot(road_side='south', w=50, l=50)
    plot_east = mock_plot(road_side='east', w=50, l=50)
    
    program = SpatialProgram(
        concept="Ori", floor_count=1,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=300, min_area_sqft=200, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bath", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        reason_codes=[]
    )
    
    res_s, _ = generate_geometry(program, plot_south)
    res_e, _ = generate_geometry(program, plot_east)
    
    # living should be near y=0 when road=south
    assert res_s.rooms[0].y < 25
    
    # living should be near x=50 when road=east
    assert res_e.rooms[0].x > 10

def test_impossible_plot():
    plot = mock_plot(w=15, l=15) # Very small buildable area
    program = SpatialProgram(
        concept="Huge", floor_count=1,
        rooms=[
            RoomIntent(id="huge", type="living", floor=1, zone="PUBLIC", target_area_sqft=600, min_area_sqft=500, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="huge"),
        reason_codes=[]
    )
    with pytest.raises(GenerationFailure, match="NO_NON_OVERLAPPING_PLACEMENT"):
        generate_geometry(program, plot)
