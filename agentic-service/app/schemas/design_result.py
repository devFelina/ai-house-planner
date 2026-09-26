import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.design.program.models import Connection, Entrance


class Opening(BaseModel):
    wall: Literal["north", "south", "east", "west"] = Field(
        ..., description="Which wall the opening is on"
    )
    offset: float = Field(..., ge=0, description="Offset from wall origin in feet")
    width: float = Field(..., gt=0, description="Width of the opening in feet")


class RoomLayout(BaseModel):
    room_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    room_type: str = Field(..., description="Type of room (e.g., living_room, kitchen)")
    name: str | None = Field(None, description="Human-readable display name")
    floor: int = Field(..., ge=1, description="Floor number")
    x: float = Field(..., description="Bottom-left corner X coordinate in feet")
    y: float = Field(..., description="Bottom-left corner Y coordinate in feet")
    width: float = Field(..., gt=0, description="Width along X-axis in feet")
    length: float = Field(..., gt=0, description="Length along Y-axis in feet")
    area_sqft: float | None = Field(None, description="Computed room area (width × length)")
    wall_height: float = Field(default=9.0, description="Ceiling height in feet")
    doors: list[Opening] = Field(default_factory=list)
    windows: list[Opening] = Field(default_factory=list)

    def model_post_init(self, __context, /):
        """Auto-compute area and name if not set."""
        if self.area_sqft is None:
            self.area_sqft = round(self.width * self.length, 2)
        if self.name is None:
            self.name = self.room_type.replace("_", " ").title()


class DesignResult(BaseModel):
    design_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    floor_count: int = Field(..., ge=1)
    total_built_up_area_sqft: float | None = Field(None, ge=0)
    foundation_type: Literal["slab", "stepped", "pile", "raised"] = Field(
        ..., description="Foundation type suited for the terrain"
    )
    terrain_type: Literal["flat", "hillside", "coastal"] = Field(
        default="flat", description="Terrain used for this design"
    )
    template_id: str = Field(
        default="CUSTOM", description="Identifier of the layout template used"
    )
    rooms: list[RoomLayout] = Field(default_factory=list)

    template_family: str | None = None
    design_seed: int | None = None
    design_score: float | None = Field(None, ge=0, le=100)
    geometry_fingerprint: str | None = Field(None, min_length=64, max_length=64)
    ground_footprint_sqft: float | None = Field(None, ge=0)
    connections: list[Connection] = Field(default_factory=list)
    entrances: list[Entrance] = Field(default_factory=list)
    plot_constraints: dict | None = None
    program: dict | None = None
    site_features: list[dict] = Field(default_factory=list)
    candidate_status: Literal["GEOMETRICALLY_INVALID", "ARCHITECTURALLY_POOR", "VALID_HIGH_QUALITY"] | None = None
    candidate_summary: dict = Field(default_factory=dict)
