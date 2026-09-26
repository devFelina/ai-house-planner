from __future__ import annotations

"""Validated base-plan catalog used as the primary design knowledge source."""

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path

from app.design.geometry.adjacency import exterior_segments, graph_for
from app.design.quality.architectural_quality import validate_architectural_quality
from app.design.generation.diversity import geometry_fingerprint
from app.design.program.models import Requirements
from app.design.generation.plan_adapter import transform_design
from app.design.catalogue.plan_suitability import accessibility_details, suitability_breakdown
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.quality.quality_metrics import calculate_quality_metrics
from app.design.program.room_counts import count_bathrooms
from app.design.program.room_rules import room_kind
from app.schemas.design_result import DesignResult

CATALOG_MIN_SIZE = 20
logger = logging.getLogger(__name__)
SEED_PATH = Path(__file__).resolve().parents[4] / 'HousePlanner.API' / 'Data' / 'Seed' / 'pre-designed-plans.json'


@dataclass(frozen=True)
class BasePlanRecord:
    plan_code: str
    name: str
    bedrooms: int
    bathrooms: int
    floors: int
    topology_family: str
    minimum_land_perches: float
    maximum_land_perches: float | None
    minimum_plot_width_ft: float | None
    minimum_plot_length_ft: float | None
    supported_plot_shapes: list[str]
    supported_terrains: list[str]
    supported_styles: list[str]
    capabilities: dict[str, bool]
    architectural_metrics: dict[str, float]
    layout_json: str
    is_active: bool = True

    @cached_property
    def geometry_fingerprint(self) -> str:
        return geometry_fingerprint(self.design)

    @cached_property
    def design(self) -> DesignResult:
        return DesignResult.model_validate_json(self.layout_json)

    @cached_property
    def primary_entrance_wall(self) -> str | None:
        return self.design.entrances[0].wall if self.design.entrances else None

    @cached_property
    def accessibility_score(self) -> float:
        return accessibility_details(self.design)[1]

    @cached_property
    def average_bedroom_area(self) -> float:
        rooms = [room for room in self.design.rooms if 'bedroom' in room.room_type]
        return sum(room.width * room.length for room in rooms) / max(1, len(rooms))

    @cached_property
    def public_room_area(self) -> float:
        return sum(room.width * room.length for room in self.design.rooms
                   if room.room_type in {'living', 'dining', 'kitchen'})

    def compact_metadata(self) -> dict:
        return {
            'plan_code': self.plan_code,
            'name': self.name,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'floors': self.floors,
            'topology_family': self.topology_family,
            'geometry_fingerprint': self.geometry_fingerprint,
            'minimum_land_perches': self.minimum_land_perches,
            'maximum_land_perches': self.maximum_land_perches,
            'minimum_plot_width_ft': self.minimum_plot_width_ft,
            'minimum_plot_length_ft': self.minimum_plot_length_ft,
            'supported_plot_shapes': self.supported_plot_shapes,
            'supported_terrains': self.supported_terrains,
            'supported_styles': self.supported_styles,
            'capabilities': self.capabilities,
            'architectural_metrics': self.architectural_metrics,
        }


def _supported_plot_shapes(topology_family: str) -> list[str]:
    mapping = {
        'LINEAR': ['NARROW', 'BALANCED'],
        'COMPACT_RECTANGLE': ['COMPACT', 'BALANCED', 'NARROW'],
        'L_SHAPE': ['BALANCED', 'LARGE'],
        'T_SHAPE': ['BALANCED', 'LARGE'],
        'CENTRAL_CORE': ['COMPACT', 'BALANCED'],
        'SPLIT_ZONE': ['BALANCED', 'LARGE'],
        'DUPLEX_STACKED': ['COMPACT', 'BALANCED', 'LARGE', 'MEDIUM'],
        'HILLSIDE_STEPPED': ['COMPACT', 'BALANCED', 'LARGE', 'MEDIUM'],
        'COASTAL_RAISED_COMPACT': ['COMPACT', 'BALANCED', 'MEDIUM'],
    }
    return mapping.get(topology_family, ['COMPACT', 'NARROW', 'WIDE', 'SMALL', 'MEDIUM', 'LARGE'])


def _supported_styles(topology_family: str, design: DesignResult) -> list[str]:
    styles = ['Modern Minimalist', 'Contemporary']
    if topology_family in {'L_SHAPE', 'T_SHAPE', 'SPLIT_ZONE'}:
        styles.append('Tropical Modernism')
    if topology_family in {'CENTRAL_CORE', 'COMPACT_RECTANGLE'}:
        styles.append('Traditional Sri Lankan')
    if design.template_family == 'DUPLEX_STACKED':
        styles.append('Contemporary')
    return sorted(set(styles))


def _capabilities(design: DesignResult) -> dict[str, bool]:
    room_types = {room.room_type for room in design.rooms}
    graph = graph_for(design.rooms, design.connections)
    master = next((room for room in design.rooms if room.room_type == 'bedroom_1'), None)
    ensuite = [room for room in design.rooms if room.room_type == 'bathroom_attached']
    balconies = [room for room in design.rooms if room_kind(room.room_type) == 'balcony']
    verandas = [room for room in design.rooms if room_kind(room.room_type) == 'veranda']
    utilities = [room for room in design.rooms if room_kind(room.room_type) == 'utility']
    kitchens = [room for room in design.rooms if room_kind(room.room_type) == 'kitchen']
    return {
        'open_plan': any(connection.kind == 'open' for connection in design.connections),
        'master_ensuite': bool(master and any(graph.get(room.room_id) == {master.room_id} for room in ensuite)),
        'separate_dining': 'dining' in room_types,
        'home_office': 'home_office' in room_types,
        'balcony': any(room.floor > 1 and exterior_segments(room, design.rooms) and
                       any(other.room_id in graph.get(room.room_id, set()) and other.floor == room.floor
                           and room_kind(other.room_type) not in {'balcony', 'veranda'} for other in design.rooms)
                       for room in balconies),
        'veranda': any(room.floor == 1 and exterior_segments(room, design.rooms) for room in verandas),
        'utility_room': any(any(kitchen.room_id in graph.get(room.room_id, set()) for kitchen in kitchens)
                            for room in utilities),
        'parking': any(feature.get('type') == 'parking' for feature in design.site_features),
        'accessibility': accessibility_details(design)[0],
    }


def _base_plot(design: DesignResult, terrain: str) -> PlotConstraints:
    max_x = max((room.x + room.width for room in design.rooms), default=40.0)
    max_y = max((room.y + room.length for room in design.rooms), default=40.0)
    return PlotConstraints.model_validate({
        'land_size_perches': 25,
        'plot_width_ft': max(60.0, max_x + 20.0),
        'plot_length_ft': max(60.0, max_y + 20.0),
        'road_side': 'south',
        'terrain_type': terrain,
        'setbacks': {'front': 10, 'rear': 7, 'left': 5, 'right': 5},
    })


def _requirements_for(design: DesignResult) -> Requirements:
    bedroom_count = sum(1 for room in design.rooms if 'bedroom' in room.room_type)
    bathroom_count = count_bathrooms(design.rooms)
    return Requirements.model_validate({
        'bedrooms': bedroom_count,
        'bathrooms': bathroom_count,
        'floors': design.floor_count,
        'style': 'Modern Minimalist',
    })


def _record_from_design(source: dict, design: DesignResult, suffix: str = '') -> BasePlanRecord | None:
    actual_bathrooms = count_bathrooms(design.rooms)
    if source.get('bathrooms') != actual_bathrooms:
        logger.warning('Skipping catalogue plan %s: bathroom count mismatch (declared %s, actual %s).',
                       source.get('designCode'), source.get('bathrooms'), actual_bathrooms)
        return None
    req = _requirements_for(design)
    plot = _base_plot(design, design.terrain_type)
    quality = validate_architectural_quality(design, req=req, plot=plot)
    if not quality.passed:
        return None
    metrics = calculate_quality_metrics(design)
    metrics.update({
        'circulation_ratio': quality.metrics.get('circulation_ratio', metrics.get('circulation_ratio', 0.0)),
        'compactness_score': quality.metrics.get('compactness_score', 0.0),
        'privacy_score': quality.metrics.get('privacy_score', 0.0),
        'public_zone_score': quality.metrics.get('public_zone_score', 0.0),
        'wet_core_score': quality.metrics.get('wet_core_score', 0.0),
        'topology_fidelity_score': quality.metrics.get('topology_fidelity_score', 0.0),
    })
    plan_code = f"{source['designCode']}{suffix}"
    return BasePlanRecord(
        plan_code=plan_code,
        name=f"{source['name']}{(' ' + suffix.replace('-', ' ')) if suffix else ''}".strip(),
        bedrooms=req.bedrooms,
        bathrooms=req.bathrooms,
        floors=req.floors,
        topology_family=design.template_family or design.template_id or 'COMPACT_RECTANGLE',
        minimum_land_perches=float(source.get('minimumLandSizePerches', 0) or 0),
        maximum_land_perches=None,
        minimum_plot_width_ft=float(source.get('minimumPlotWidthFt')) if source.get('minimumPlotWidthFt') is not None else None,
        minimum_plot_length_ft=float(source.get('minimumPlotLengthFt')) if source.get('minimumPlotLengthFt') is not None else None,
        supported_plot_shapes=_supported_plot_shapes(design.template_family or design.template_id or ''),
        supported_terrains=[design.terrain_type or 'flat'],
        supported_styles=_supported_styles(design.template_family or design.template_id or '', design),
        capabilities=_capabilities(design),
        architectural_metrics={
            'circulation_ratio': round(metrics.get('circulation_ratio', 0.0), 4),
            'compactness_score': round(quality.metrics.get('compactness_score', 0.0), 2),
            'privacy_score': round(quality.metrics.get('privacy_score', 0.0), 2),
            'public_zone_score': round(quality.metrics.get('public_zone_score', 0.0), 2),
            'wet_core_score': round(quality.metrics.get('wet_core_score', 0.0), 2),
            'topology_fidelity_score': round(quality.metrics.get('topology_fidelity_score', 0.0), 2),
        },
        layout_json=design.model_dump_json(),
        is_active=bool(source.get('isActive', True)),
    )


def _load_seed_records() -> list[BasePlanRecord]:
    if not SEED_PATH.exists():
        return []
    seed_data = json.loads(SEED_PATH.read_text())
    records: list[BasePlanRecord] = []
    for source in seed_data:
        layout = source.get('layout')
        if not isinstance(layout, dict):
            continue
        design = DesignResult.model_validate(layout)
        record = _record_from_design(source, design)
        if record and record.is_active:
            records.append(record)
    return records


def _derived_suffixes() -> list[tuple[str, dict[str, object]]]:
    return [
        ('-R90', {'rotation_degrees': 90}),
        ('-R180', {'rotation_degrees': 180}),
        ('-R270', {'rotation_degrees': 270}),
        ('-MH', {'mirror_horizontal': True}),
        ('-MV', {'mirror_vertical': True}),
        ('-MH-R90', {'mirror_horizontal': True, 'rotation_degrees': 90}),
        ('-MV-R90', {'mirror_vertical': True, 'rotation_degrees': 90}),
        ('-MH-MV', {'mirror_horizontal': True, 'mirror_vertical': True}),
    ]


@lru_cache(maxsize=1)
def load_base_plan_catalog() -> list[BasePlanRecord]:
    records = _load_seed_records()
    originals = list(records)
    if len(records) < CATALOG_MIN_SIZE:
        for source_record, (suffix, transform) in zip(originals * 2, _derived_suffixes()):
            if len(records) >= CATALOG_MIN_SIZE:
                break
            design = DesignResult.model_validate_json(source_record.layout_json)
            design = transform_design(design, **transform)
            source = {'designCode': source_record.plan_code, 'name': source_record.name, 'bathrooms': source_record.bathrooms, 'minimumLandSizePerches': source_record.minimum_land_perches, 'minimumPlotWidthFt': source_record.minimum_plot_width_ft, 'minimumPlotLengthFt': source_record.minimum_plot_length_ft, 'isActive': True}
            derived = _record_from_design(source, design, suffix=suffix)
            if derived is not None:
                records.append(derived)
    return records


def compatibility_rejection_reasons(plan: BasePlanRecord, req: Requirements,
                                    plot: PlotConstraints) -> list[str]:
    reasons = []
    if not plan.is_active:
        reasons.append('inactive')
    if plan.floors != req.floors:
        reasons.append('floor_count')
    if plan.bedrooms != req.bedrooms:
        reasons.append('bedroom_count')
    if plan.bathrooms < req.bathrooms:
        reasons.append('bathroom_count')
    if plot.land_size_perches < plan.minimum_land_perches:
        reasons.append('minimum_land')
    if plan.minimum_plot_width_ft and (plot.plot_width_ft or 0) < plan.minimum_plot_width_ft:
        reasons.append('minimum_plot_width')
    if plan.minimum_plot_length_ft and (plot.plot_length_ft or 0) < plan.minimum_plot_length_ft:
        reasons.append('minimum_plot_length')
    if plot.terrain_type not in plan.supported_terrains:
        reasons.append('terrain')
    shape = plot.plot_class.split('_')[-1]
    if plot.plot_class.endswith('VERY_NARROW'):
        shape = 'NARROW'
    if shape not in plan.supported_plot_shapes and plot.plot_class.split('_')[0] not in plan.supported_plot_shapes:
        reasons.append('plot_shape')

    min_x = min((r.x for r in plan.design.rooms), default=0)
    min_y = min((r.y for r in plan.design.rooms), default=0)
    max_x = max((r.x + r.width for r in plan.design.rooms), default=0)
    max_y = max((r.y + r.length for r in plan.design.rooms), default=0)
    if max_x - min_x > plot.buildable_width + 0.001:
        reasons.append('footprint_width')
    if max_y - min_y > plot.buildable_length + 0.001:
        reasons.append('footprint_length')

    # Hard capability requirements: if the user explicitly selected these, the plan MUST support them.
    # Note: Soft suitability preferences (like space_priority or style) only affect ranking score, not filtering.
    required_capabilities = {
        'accessibility': req.accessibility,
        'master_ensuite': req.master_bedroom or req.attached_bathroom,
        'open_plan': req.open_plan,
        'separate_dining': req.dining_required,
        'home_office': req.home_office,
        'balcony': req.balcony,
        'veranda': req.veranda,
        'utility_room': req.utility_room,
        'parking': req.parking,
    }
    reasons.extend(f'missing_{name}' for name, required in required_capabilities.items()
                   if required and not plan.capabilities.get(name, False))
    return reasons


def filter_compatible_base_plans_with_diagnostics(
        req: Requirements, plot: PlotConstraints) -> tuple[list[BasePlanRecord], dict[str, int]]:
    plans = []
    rejected: dict[str, int] = {}
    for plan in load_base_plan_catalog():
        reasons = compatibility_rejection_reasons(plan, req, plot)
        if reasons:
            for reason in reasons:
                rejected[reason] = rejected.get(reason, 0) + 1
            continue
        plans.append(plan)
    return plans, rejected


def filter_compatible_base_plans(req: Requirements, plot: PlotConstraints) -> list[BasePlanRecord]:
    plans, _ = filter_compatible_base_plans_with_diagnostics(req, plot)
    return plans


def rank_base_plans(plans: Iterable[BasePlanRecord], req: Requirements, plot: PlotConstraints) -> list[BasePlanRecord]:
    def key(plan: BasePlanRecord):
        score = suitability_breakdown(plan, req, plot)['score']
        circulation = plan.architectural_metrics.get('circulation_ratio', 0.2)
        compactness = plan.architectural_metrics.get('compactness_score', 0.0)
        return (-score, circulation, -compactness, plan.plan_code)

    return sorted(plans, key=key)


def deduplicate_base_plans(plans: Iterable[BasePlanRecord],
                           excluded_fingerprint: str | None = None) -> list[BasePlanRecord]:
    """Keep the first (highest-ranked) representative of each geometry."""
    seen = {excluded_fingerprint} if excluded_fingerprint else set()
    unique = []
    for plan in plans:
        fingerprint = plan.geometry_fingerprint
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(plan)
    return unique


def compact_plan_metadata(plans: Iterable[BasePlanRecord], req: Requirements,
                          plot: PlotConstraints) -> list[dict]:
    """Send selection evidence without coordinates or full layout JSON."""
    compact = []
    for plan in plans:
        suitability = suitability_breakdown(plan, req, plot)
        compact.append({
            'plan_code': plan.plan_code,
            'topology_family': plan.topology_family,
            'suitability_score': suitability['score'],
            'supported_features': sorted(name for name, value in plan.capabilities.items() if value),
            'plot_fit': suitability['plot_fit'],
            'geometry_fingerprint': plan.geometry_fingerprint,
        })
    return compact
