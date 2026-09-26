"""Coordinate-free selection contract. Unknown fields are rejected at every level."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.design.program.models import Direction


class StrictDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)

class DesignIntent(StrictDecision):
    public_zone_orientation: Direction
    private_zone_orientation: Literal['north', 'south', 'east', 'west', 'north_east', 'north_west', 'south_east', 'south_west']
    service_zone_orientation: Direction
    privacy_priority: Literal['balanced', 'high']
    circulation_preference: Literal['short_central_hall', 'shared_lobby']

class Adaptations(StrictDecision):
    mirror_horizontal: bool
    mirror_vertical: bool
    rotation_degrees: Literal[0, 90, 180, 270]
    living_scale: float = Field(ge=1, le=1.2)
    bedroom_scale: float = Field(ge=1, le=1.15)
    entrance_side: Direction
    preserve_stair_core: Literal[True]
    preserve_wet_core: Literal[True]

class AIPlanDecision(StrictDecision):
    selected_plan_code: str = Field(min_length=1, max_length=80)
    alternative_plan_codes: list[str] = Field(max_length=6)
    design_intent: DesignIntent
    adaptations: Adaptations
    reason_codes: list[Literal['plot_fit', 'privacy', 'south_access', 'road_access',
                              'low_circulation', 'style_match', 'preference_match', 'different_concept']] = Field(max_length=6)
