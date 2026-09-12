from math import sqrt
from typing import Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator
from app.design.models import Direction, Terrain
from app.tools.land_utils import perches_to_sqft, max_buildable_area


class Setbacks(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    front: float = Field(10, ge=0)
    rear: float = Field(7, ge=0)
    left: float = Field(5, ge=0)
    right: float = Field(5, ge=0)


class PlotConstraints(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    land_size_perches: float = Field(gt=0)
    plot_width_ft: Optional[float] = Field(None, gt=0)
    plot_length_ft: Optional[float] = Field(None, gt=0)
    road_side: Direction = 'south'
    north_direction: Literal['top', 'bottom', 'left', 'right'] = 'top'
    terrain_type: Terrain = 'flat'
    slope_direction: Optional[Direction] = None
    setbacks: Setbacks = Field(default_factory=Setbacks)
    dimensions_estimated: bool = False
    parking_reserved: bool = False
    notable_features: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def derive_dimensions(self) -> 'PlotConstraints':
        area = perches_to_sqft(self.land_size_perches)
        if self.plot_width_ft is None or self.plot_length_ft is None:
            self.dimensions_estimated = True
            if self.plot_width_ft is None and self.plot_length_ft is None:
                self.plot_width_ft = sqrt(area / 1.3)
            if self.plot_width_ft is None:
                self.plot_width_ft = area / self.plot_length_ft
            if self.plot_length_ft is None:
                self.plot_length_ft = area / self.plot_width_ft
        if self.buildable_width <= 0 or self.buildable_length <= 0:
            raise ValueError('Setbacks/reserved parking leave no buildable rectangle.')
        return self

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
