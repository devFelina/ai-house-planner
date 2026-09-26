import logging
from app.design.geometry.geometry_generator import generate_geometry
from tests.test_geometry_generator_multifloor import mock_plot, SpatialProgram, RoomIntent, EntranceIntent, VerticalCoreIntent
import builtins

plot = mock_plot()
program = SpatialProgram(
    concept="Two Floor", floor_count=2,
    rooms=[
        RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=200, min_area_sqft=150, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
        RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
        RoomIntent(id="dining", type="dining", floor=1, zone="PUBLIC", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
        RoomIntent(id="bath1", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
        RoomIntent(id="bed1", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
        RoomIntent(id="bed2", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
        RoomIntent(id="bath2", type="bathroom", floor=2, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW")
    ],
    adjacencies=[],
    entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
    vertical_core=VerticalCoreIntent(stair_position="CENTER", align_service_zones=True),
    reason_codes=[]
)

from app.design.geometry.geometry_generator import LayoutSolver
solver = LayoutSolver(program, plot)

try:
    res, meta = solver.generate()
    print("SUCCESS!")
    for r in res.rooms:
        print(f"  {r.room_id}: {r.x}, {r.y}, {r.width}x{r.length}")
except Exception as e:
    print(f"Failed: {e}")
    print(f"Backtracks: {solver.global_backtracks}")
