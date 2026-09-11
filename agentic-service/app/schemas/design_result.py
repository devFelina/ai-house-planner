import uuid
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class Opening(BaseModel):
    wall: Literal["north", "south", "east", "west"] = Field(
        ..., description="Which wall the opening is on"
    )
    offset: float = Field(..., ge=0, description="Offset from wall origin in feet")
    width: float = Field(..., gt=0, description="Width of the opening in feet")


class RoomLayout(BaseModel):
    room_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    room_type: str = Field(..., description="Type of room (e.g., living_room, kitchen)")
    name: Optional[str] = Field(None, description="Human-readable display name")
    floor: int = Field(..., ge=1, description="Floor number")
    x: float = Field(..., description="Bottom-left corner X coordinate in feet")
    y: float = Field(..., description="Bottom-left corner Y coordinate in feet")
    width: float = Field(..., gt=0, description="Width along X-axis in feet")
    length: float = Field(..., gt=0, description="Length along Y-axis in feet")
    area_sqft: Optional[float] = Field(None, description="Computed room area (width × length)")
    wall_height: float = Field(default=9.0, description="Ceiling height in feet")
    doors: List[Opening] = Field(default_factory=list)
    windows: List[Opening] = Field(default_factory=list)

    def model_post_init(self, __context):
        """Auto-compute area and name if not set."""
        if self.area_sqft is None:
            self.area_sqft = round(self.width * self.length, 2)
        if self.name is None:
            self.name = self.room_type.replace("_", " ").title()


class DesignResult(BaseModel):
    design_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    floor_count: int = Field(..., ge=1)
    total_built_up_area_sqft: float = Field(..., ge=0)
    foundation_type: Literal["slab", "stepped", "pile", "raised"] = Field(
        ..., description="Foundation type suited for the terrain"
    )
    terrain_type: Literal["flat", "hillside", "coastal"] = Field(
        default="flat", description="Terrain used for this design"
    )
    template_id: str = Field(
        default="CUSTOM", description="Identifier of the layout template used"
    )
    rooms: List[RoomLayout] = Field(default_factory=list)
