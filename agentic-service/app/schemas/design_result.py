import uuid
from pydantic import BaseModel, Field
from typing import List

class Opening(BaseModel):
    wall: str = Field(..., description="north, south, east, or west")
    offset: float = Field(..., ge=0, description="Offset from wall origin in feet")
    width: float = Field(..., gt=0, description="Width of the opening in feet")

class RoomLayout(BaseModel):
    room_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    room_type: str = Field(..., description="Type of room (e.g., living_room, kitchen)")
    floor: int = Field(..., ge=1, description="Floor number")
    x: float = Field(..., description="Bottom-left corner X coordinate in feet")
    y: float = Field(..., description="Bottom-left corner Y coordinate in feet")
    width: float = Field(..., gt=0, description="Width along X-axis in feet")
    length: float = Field(..., gt=0, description="Length along Y-axis in feet")
    wall_height: float = Field(default=9.0, description="Ceiling height in feet")
    doors: List[Opening] = Field(default_factory=list)
    windows: List[Opening] = Field(default_factory=list)

class DesignResult(BaseModel):
    design_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    floor_count: int = Field(..., ge=1)
    total_built_up_area_sqft: float = Field(..., ge=0)
    foundation_type: str = Field(..., description="Type of foundation suited for the terrain")
    rooms: List[RoomLayout] = Field(default_factory=list)
