
from pydantic import BaseModel, ConfigDict


class NormalizedDesignInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    land_perches: float
    land_area_sqft: float
    plot_width_ft: float
    plot_length_ft: float
    dimension_source: str
    terrain: str
    road_side: str
    north_direction: str
    entrance_side: str
    setbacks: dict[str, float]
    buildable_width_ft: float
    buildable_length_ft: float
    plot_shape_class: str
    bedrooms: int
    bathrooms: int
    floors: int
    architectural_style: str
    space_priority: str
    open_plan: bool
    master_ensuite: bool
    separate_dining: bool
    home_office: bool
    balcony: bool
    veranda: bool
    utility_room: bool
    parking_required: bool
    accessibility: bool
    design_seed: int | None

    @classmethod
    def from_inputs(cls, req, plot):
        return cls(land_perches=plot.land_size_perches, land_area_sqft=plot.land_size_perches*272.25,
                   plot_width_ft=plot.plot_width_ft, plot_length_ft=plot.plot_length_ft,
                   dimension_source=plot.dimension_source, terrain=plot.terrain_type,
                   road_side=plot.road_side, north_direction=plot.north_direction,
                   entrance_side=plot.effective_entrance_side, setbacks=plot.edge_setbacks,
                   buildable_width_ft=plot.buildable_width, buildable_length_ft=plot.buildable_length,
                   plot_shape_class=plot.plot_class, bedrooms=req.bedrooms, bathrooms=req.bathrooms,
                   floors=req.floors, architectural_style=req.style, space_priority=req.space_priority,
                   open_plan=req.open_plan, master_ensuite=req.attached_bathroom,
                   separate_dining=req.dining_required, home_office=req.home_office,
                   balcony=req.balcony, veranda=req.veranda, utility_room=req.utility_room,
                   parking_required=req.parking, accessibility=req.accessibility, design_seed=req.design_seed)
