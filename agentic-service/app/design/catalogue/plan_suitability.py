from __future__ import annotations

"""Deterministic, configurable suitability scoring for validated base plans."""

from typing import TYPE_CHECKING

from app.design.program.models import Requirements
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.room_rules import CIRCULATION_TYPES, room_kind
from app.schemas.design_result import DesignResult

if TYPE_CHECKING:
    from app.design.catalogue.base_plan_library import BasePlanRecord


SUITABILITY_WEIGHTS = {
    'plot_shape_fit': 18,
    'dimension_fit': 14,
    'land_size_fit': 10,
    'topology_fit': 16,
    'style_fit': 10,
    'space_priority_fit': 12,
    'feature_fit': 6,
    'accessibility_fit': 8,
    'entrance_road_fit': 6,
}


def _shape_token(plot: PlotConstraints) -> str:
    shape = plot.plot_class.split('_')[-1]
    return 'NARROW' if shape == 'NARROW' or plot.plot_class.endswith('VERY_NARROW') else shape


def _topology_fit(family: str, req: Requirements, plot: PlotConstraints) -> float:
    shape = _shape_token(plot)
    by_shape = {
        'NARROW': {'LINEAR': 1.0, 'COMPACT_RECTANGLE': .72, 'CENTRAL_CORE': .55,
                   'SPLIT_ZONE': .35, 'L_SHAPE': .25},
        'COMPACT': {'CENTRAL_CORE': 1.0, 'COMPACT_RECTANGLE': .95, 'SPLIT_ZONE': .72,
                    'L_SHAPE': .58, 'LINEAR': .42},
        'BALANCED': {'SPLIT_ZONE': 1.0, 'CENTRAL_CORE': .92, 'COMPACT_RECTANGLE': .88,
                     'L_SHAPE': .82, 'LINEAR': .45},
        'WIDE': {'SPLIT_ZONE': 1.0, 'L_SHAPE': .95, 'CENTRAL_CORE': .78,
                 'COMPACT_RECTANGLE': .72, 'LINEAR': .35},
    }
    score = by_shape.get(shape, {}).get(family, .55)
    if req.floors > 1 and family == 'DUPLEX_STACKED':
        score = max(score, .9)
    style = req.style.casefold()
    if req.garden_priority or req.space_priority == 'outdoor_garden':
        score = max(score, 1.0) if family in {'L_SHAPE', 'T_SHAPE'} else min(score, .75)
    if req.compact_priority or req.space_priority == 'compact_cost_efficient':
        if family == 'COMPACT_RECTANGLE':
            score = 1.0
        elif family == 'CENTRAL_CORE':
            score = max(score, .9)
        else:
            score = min(score, .62)
    if 'tropical' in style:
        score = max(score, 1.0) if family in {'L_SHAPE', 'T_SHAPE'} else min(score, .78)
    elif 'minimal' in style:
        if family in {'COMPACT_RECTANGLE', 'CENTRAL_CORE'}:
            score = max(score, .95)
        else:
            score = min(score, .72)
    return score


def _space_priority_fit(plan: BasePlanRecord, req: Requirements) -> float:
    family = plan.topology_family
    compactness = min(1.0, plan.architectural_metrics.get('compactness_score', 0) / 100)
    if req.space_priority == 'outdoor_garden' or req.garden_priority:
        return 1.0 if family in {'L_SHAPE', 'T_SHAPE'} else (.72 if family == 'SPLIT_ZONE' else .45)
    if req.space_priority == 'compact_cost_efficient' or req.compact_priority:
        return max(compactness, 1.0 if family == 'COMPACT_RECTANGLE' else
                   .88 if family == 'CENTRAL_CORE' else .45)
    if req.space_priority == 'larger_bedrooms':
        return min(1.0, .45 + plan.average_bedroom_area / 300)
    if req.space_priority == 'spacious_living':
        return min(1.0, .4 + plan.public_room_area / 450)
    return .75


def accessibility_details(design: DesignResult) -> tuple[bool, float]:
    ground = [room for room in design.rooms if room.floor == 1]
    has_bedroom = any(room_kind(room.room_type) == 'bedroom' for room in ground)
    has_bathroom = any(room_kind(room.room_type) == 'bathroom' for room in ground)
    halls = [room for room in ground if room.room_type in CIRCULATION_TYPES]
    usable_halls = all(min(room.width, room.length) >= 3.5 for room in halls)
    hall_area = sum(room.width * room.length for room in halls)
    floor_area = sum(room.width * room.length for room in ground) or 1
    circulation = max(0.0, 1.0 - hall_area / floor_area)
    capable = has_bedroom and has_bathroom and usable_halls
    return capable, circulation if capable else 0.0


def suitability_breakdown(plan: BasePlanRecord, req: Requirements,
                          plot: PlotConstraints) -> dict:
    shape = _shape_token(plot)
    shape_fit = 1.0 if shape in plan.supported_plot_shapes else .35
    width_margin = plot.buildable_width - (plan.minimum_plot_width_ft or 0)
    length_margin = plot.buildable_length - (plan.minimum_plot_length_ft or 0)
    dimension_fit = min(1.0, .65 + min(width_margin, length_margin) / 50)
    land_margin = plot.land_size_perches - plan.minimum_land_perches
    land_fit = max(.35, 1.0 - min(1.0, land_margin / max(plot.land_size_perches, 1)) * .45)
    style_fit = 1.0 if req.style.casefold() in {style.casefold() for style in plan.supported_styles} else .45
    requested = {
        'open_plan': req.open_plan, 'master_ensuite': req.master_bedroom or req.attached_bathroom,
        'separate_dining': req.dining_required, 'home_office': req.home_office,
        'balcony': req.balcony, 'veranda': req.veranda, 'utility_room': req.utility_room,
        'parking': req.parking,
    }
    wanted = [name for name, value in requested.items() if value]
    feature_fit = (sum(plan.capabilities.get(name, False) for name in wanted) / len(wanted)) if wanted else .75
    accessibility_fit = plan.accessibility_score if req.accessibility else .75
    entrance = plan.primary_entrance_wall
    entrance_fit = 1.0 if entrance == plot.effective_entrance_side else (.75 if entrance == plot.road_side else .45)
    factors = {
        'plot_shape_fit': shape_fit,
        'dimension_fit': dimension_fit,
        'land_size_fit': land_fit,
        'topology_fit': _topology_fit(plan.topology_family, req, plot),
        'style_fit': style_fit,
        'space_priority_fit': _space_priority_fit(plan, req),
        'feature_fit': feature_fit,
        'accessibility_fit': accessibility_fit,
        'entrance_road_fit': entrance_fit,
    }
    weighted = {name: round(max(0, min(1, value)) * SUITABILITY_WEIGHTS[name], 3)
                for name, value in factors.items()}
    return {
        'score': round(sum(weighted.values()), 2),
        'factors': weighted,
        'plot_fit': {
            'shape': shape,
            'shape_supported': bool(shape_fit == 1.0),
            'width_margin_ft': round(width_margin, 1),
            'length_margin_ft': round(length_margin, 1),
            'entrance_match': entrance == plot.effective_entrance_side,
        },
    }
