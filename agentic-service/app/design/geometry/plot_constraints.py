from __future__ import annotations
import random
from math import sqrt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.design.program.models import Direction, Terrain
from app.land.land_math import max_buildable_area, perches_to_sqft


class Setbacks(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    front: float = Field(10, ge=0)
    rear: float = Field(7, ge=0)
    left: float = Field(5, ge=0)
    right: float = Field(5, ge=0)


class PlotConstraints(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    land_size_perches: float = Field(gt=0)
    plot_width_ft: float | None = Field(None, gt=0)
    plot_length_ft: float | None = Field(None, gt=0)
    road_side: Direction = 'south'
    north_direction: Literal['top', 'bottom', 'left', 'right', 'north', 'east', 'south', 'west'] = 'top'
    entrance_side: Direction | None = None
    terrain_type: Terrain = 'flat'
    slope_direction: Direction | None = None
    setbacks: Setbacks = Field(default_factory=Setbacks)
    setback_source: str = "conceptual_default"
    dimension_source: str = "user_supplied"
    parking_reserved: bool = False
    design_seed: int | None = None
    notable_features: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def derive_dimensions(self) -> 'PlotConstraints':
        area = perches_to_sqft(self.land_size_perches)

        has_width = self.plot_width_ft is not None
        has_length = self.plot_length_ft is not None

        if not has_width and not has_length:
            self.dimension_source = "area_estimated"
            rng = random.Random(self.design_seed if self.design_seed is not None else int(self.land_size_perches * 10))

            # Future Guided UI Plot Shape Categories:
            # - BALANCED: aspect = 1.25 (default when no shape/dims provided)
            # - NARROW_DEEP: aspect = 2.0+ (requires explicit user selection)
            # - WIDE_SHALLOW: aspect = 0.6 (requires explicit user selection)
            aspect = 1.25
            if area < 3000 or rng.random() > 0.5:
                self.plot_width_ft = sqrt(area / aspect)
            else:
                self.plot_width_ft = sqrt(area * aspect)
            self.plot_length_ft = area / self.plot_width_ft
        elif has_width and not has_length:
            self.dimension_source = "partially_derived"
            self.plot_length_ft = area / self.plot_width_ft
        elif not has_width and has_length:
            self.dimension_source = "partially_derived"
            self.plot_width_ft = area / self.plot_length_ft
        else:
            self.dimension_source = "user_supplied"

        # Auto-correct perches if explicitly supplied dimensions vary wildly
        if has_width and has_length:
            dimension_area = self.plot_width_ft * self.plot_length_ft
            variance = abs(dimension_area - area) / area
            if variance > 0.30:
                self.land_size_perches = dimension_area / perches_to_sqft(1)

        # Avoid floating point absurdities
        self.plot_width_ft = round(self.plot_width_ft, 1)
        self.plot_length_ft = round(self.plot_length_ft, 1)

        if self.buildable_width <= 0 or self.buildable_length <= 0:
            # Try reducing setbacks to make it buildable
            min_w = min(5.0, self.plot_width_ft * 0.2)
            min_l = min(5.0, self.plot_length_ft * 0.2)
            
            w_setbacks = self.edge_setbacks['west'] + self.edge_setbacks['east']
            if w_setbacks > 0 and self.plot_width_ft - w_setbacks <= 0:
                scale = max(0, (self.plot_width_ft - min_w) / w_setbacks)
                self.setbacks.left *= scale
                self.setbacks.right *= scale

            l_setbacks = self.edge_setbacks['south'] + self.edge_setbacks['north']
            if l_setbacks > 0 and self.plot_length_ft - l_setbacks <= 0:
                scale = max(0, (self.plot_length_ft - min_l) / l_setbacks)
                self.setbacks.front *= scale
                self.setbacks.rear *= scale

            if self.buildable_width <= 0 or self.buildable_length <= 0:
                raise ValueError('Setbacks/reserved parking leave no buildable rectangle.')
                
        return self

    @computed_field
    @property
    def aspect_ratio(self) -> float:
        return max(self.plot_width_ft or 1, self.plot_length_ft or 1) / min(self.plot_width_ft or 1, self.plot_length_ft or 1)

    @computed_field
    @property
    def plot_class(self) -> str:
        area = perches_to_sqft(self.land_size_perches)
        aspect = self.aspect_ratio

        if area < 3000:
            size = "SMALL"
        elif area < 6000:
            size = "MEDIUM"
        elif area < 10000:
            size = "LARGE"
        else:
            size = "VERY_LARGE"

        if aspect <= 1.25:
            shape = "COMPACT"
        elif aspect <= 1.55:
            shape = "BALANCED"
        elif aspect <= 2.2:
            shape = "NARROW"
        else:
            shape = "VERY_NARROW"

        return f"{size}_{shape}"

    @computed_field
    @property
    def edge_setbacks(self) -> dict[str, float]:
        # Left/right are relative to looking into the plot from the road.
        order = {'south': ('south', 'north', 'west', 'east'),
                 'north': ('north', 'south', 'east', 'west'),
                 'east': ('east', 'west', 'south', 'north'),
                 'west': ('west', 'east', 'north', 'south')}[self.road_side]
        values = [max(self.setbacks.front, 18) if self.parking_reserved else self.setbacks.front,
                  self.setbacks.rear, self.setbacks.left, self.setbacks.right]
        return dict(zip(order, values))

    @computed_field
    @property
    def effective_entrance_side(self) -> Direction:
        return self.entrance_side or self.road_side

    @computed_field
    @property
    def buildable_width(self) -> float:
        return float(self.plot_width_ft or 0) - self.edge_setbacks['west'] - self.edge_setbacks['east']

    @computed_field
    @property
    def buildable_length(self) -> float:
        return float(self.plot_length_ft or 0) - self.edge_setbacks['south'] - self.edge_setbacks['north']

    @computed_field
    @property
    def buildable_polygon(self) -> list[tuple[float, float]]:
        # Local architectural feet, origin at southwest of the buildable rectangle.
        return [(0, 0), (self.buildable_width, 0),
                (self.buildable_width, self.buildable_length), (0, self.buildable_length)]

    @computed_field
    @property
    def maximum_ground_footprint(self) -> float:
        return min(self.buildable_width * self.buildable_length,
                   max_buildable_area(self.land_size_perches))

    @computed_field
    @property
    def maximum_total_floor_area(self) -> float:
        return max_buildable_area(self.land_size_perches)


# North is metadata for display; coordinates always use east +X and north +Y.
