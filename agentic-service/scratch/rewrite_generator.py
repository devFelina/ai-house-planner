import time
from typing import Any
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.spatial_program import SpatialProgram
from app.schemas.design_result import DesignResult, RoomLayout
from app.design.exceptions import GenerationFailure
from app.validation.geometry_validator import validate_geometry
from app.design.program.room_rules import rule_for, room_kind

def _normalize_room_type(gpt_type: str) -> str:
    t = gpt_type.lower().replace(' ', '_')
    if t == 'living': return 'living_room'
    if t == 'dining': return 'dining'
    if t == 'bath': return 'bathroom'
    if t == 'master_bedroom': return 'bedroom_master'
    return t

class PlacedRoom:
    def __init__(self, room_id: str, rtype: str, floor: int, x: float, y: float, w: float, h: float, target_area: float):
        self.id = room_id
        self.type = rtype
        self.floor = floor
        self.x = x
        self.y = y
        self.width = w
        self.length = h
        self.target_area = target_area

# ... implementation follows
