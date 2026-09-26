from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Zone = Literal['PUBLIC', 'PRIVATE', 'SERVICE', 'CIRCULATION']
Position = Literal['FRONT', 'REAR', 'LEFT', 'RIGHT', 'CENTER', 'FRONT_LEFT', 'FRONT_RIGHT', 'REAR_LEFT', 'REAR_RIGHT']
PrivacyLevel = Literal['LOW', 'MEDIUM', 'HIGH']
AdjacencyType = Literal['ADJACENT', 'NEAR', 'SEPARATE']
PriorityLevel = Literal['HIGH', 'MEDIUM', 'LOW']
Direction = Literal['NORTH', 'SOUTH', 'EAST', 'WEST']


class RoomIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(min_length=1, max_length=50)
    type: str = Field(min_length=1, max_length=50)
    floor: int = Field(ge=1, le=3)
    zone: Zone
    target_area_sqft: int = Field(ge=10, le=2000)
    min_area_sqft: int = Field(ge=10, le=2000)
    preferred_position: Position
    exterior_wall_required: bool
    privacy_level: PrivacyLevel


class AdjacencyIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    room_a: str = Field(min_length=1, max_length=50)
    room_b: str = Field(min_length=1, max_length=50)
    relationship: AdjacencyType
    priority: PriorityLevel


class EntranceIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    preferred_side: Direction
    connect_to: str = Field(min_length=1, max_length=50)


class VerticalCoreIntent(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    stair_position: Position
    align_service_zones: bool


class SpatialProgram(BaseModel):
    """Semantic architectural plan output by GPT, acting as constraints for geometric generation."""
    model_config = ConfigDict(extra='forbid', strict=True)
    concept: str = Field(min_length=1, max_length=200)
    floor_count: int = Field(ge=1, le=3)
    rooms: list[RoomIntent] = Field(min_length=1, max_length=30)
    adjacencies: list[AdjacencyIntent] = Field(max_length=50)
    entrance: EntranceIntent
    vertical_core: VerticalCoreIntent | None = None
    reason_codes: list[str] = Field(max_length=10)
