from typing import Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

Direction = Literal['north', 'south', 'east', 'west']
Terrain = Literal['flat', 'hillside', 'coastal', 'unknown']
FamilyName = Literal['LINEAR', 'COMPACT_RECTANGLE', 'L_SHAPE', 'T_SHAPE',
                     'CENTRAL_CORE', 'SPLIT_ZONE', 'DUPLEX_STACKED',
                     'HILLSIDE_STEPPED', 'COASTAL_RAISED_COMPACT']


class Requirements(BaseModel):
    # Retain photo/plot/future fields, and report unhandled fields in the result.
    model_config = ConfigDict(extra='allow', allow_inf_nan=False)
    bedrooms: int = Field(3, ge=1, le=8)
    bathrooms: int = Field(1, ge=1, le=6)
    floors: int = Field(2, ge=1, le=3)
    style: str = 'conventional'
    open_plan: bool = False
    dining_required: bool = False
    master_bedroom: bool = False
    attached_bathroom: bool = False
    home_office: bool = False
    parking: bool = False
    balcony: bool = False
    garden_priority: bool = False
    accessibility: bool = False
    design_seed: Optional[int] = None


class RoomSpec(BaseModel):
    id: str
    room_type: str
    floor: int
    zone: Literal['public', 'private', 'service', 'circulation']
    min_width: float
    min_length: float
    max_width: float = 24
    max_length: float = 24
    target_area: float
    requires_exterior_wall: bool = False


class SpatialProgram(BaseModel):
    rooms: list[RoomSpec]
    adjacency_preferences: list[tuple[str, str, Literal['required', 'preferred']]]
    separation_preferences: list[tuple[str, str]]
    access_graph: list[tuple[str, str]]
    notes: list[str] = Field(default_factory=list)


class Connection(BaseModel):
    from_room: str
    to_room: str
    kind: Literal['door', 'open', 'stair'] = 'door'


class Entrance(BaseModel):
    room_id: str
    wall: Direction
    offset: float = Field(ge=0)
    width: float = Field(3, gt=0)


class ConceptAdvice(BaseModel):
    """No coordinates, room counts or validity claims are accepted from Gemini."""
    model_config = ConfigDict(extra='forbid', strict=True)
    preferred_families: list[FamilyName] = Field(default_factory=list, max_length=5)
    rationale: str = Field('', max_length=1500)
