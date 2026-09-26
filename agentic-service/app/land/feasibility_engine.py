"""
Deterministic feasibility engine for the Architecture Assistant.

Evaluates whether a user's design request is feasible based on:
- Normalized land dimensions and buildable envelope
- Catalogue compatibility (pre-designed-plans.json)
- Feature support validation

Does NOT use LLM for the feasibility decision.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.land.land_math import SQFT_PER_PERCH, max_buildable_area, perches_to_sqft

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATALOGUE_PATH = Path(__file__).resolve().parents[3] / 'HousePlanner.API' / 'Data' / 'Seed' / 'pre-designed-plans.json'

DEFAULT_SETBACKS = {'front': 10.0, 'rear': 7.0, 'left': 5.0, 'right': 5.0}

# Supported ranges in the system
SUPPORTED_BEDROOMS = range(2, 7)   # 2-6
SUPPORTED_BATHROOMS = range(1, 6)  # 1-5
SUPPORTED_FLOORS = range(1, 4)     # 1-3

# Minimum buildable area per bedroom (heuristic, sq ft ground floor)
MIN_SQFT_PER_BEDROOM = 120.0
# Minimum area for a parking space
MIN_PARKING_SQFT = 180.0
# Minimum buildable dimension
MIN_BUILDABLE_DIMENSION_FT = 15.0

# Capability mapping from user requirement field to catalogue capability key
CAPABILITY_MAP = {
    'open_plan': 'open_plan',
    'master_ensuite': 'master_ensuite',
    'separate_dining': 'separate_dining',
    'office': 'home_office',
    'balcony': 'balcony',
    'veranda': 'veranda',
    'utility_room': 'utility_room',
    'parking_required': 'parking',
    'accessible_friendly': 'accessibility',
}


# ---------------------------------------------------------------------------
# Land normalization
# ---------------------------------------------------------------------------

@dataclass
class NormalizedLand:
    land_size_perches: float
    land_area_sqft: float
    plot_width_ft: float
    plot_length_ft: float
    dimension_source: str  # user_supplied | partially_derived | area_estimated
    setbacks: dict[str, float]
    buildable_width_ft: float
    buildable_length_ft: float
    buildable_area_sqft: float
    max_coverage_area_sqft: float


def normalize_land(
    land_size: float | None = None,
    land_unit: str | None = None,
    plot_width_ft: float | None = None,
    plot_length_ft: float | None = None,
    setbacks: dict[str, float] | None = None,
    parking_required: bool = False,
) -> NormalizedLand:
    """Convert user-supplied land info into a normalized buildable envelope."""

    # Step 1: Convert to perches
    if land_size is not None and land_size > 0:
        unit = (land_unit or 'perch').lower().strip()
        if unit in ('sqft', 'sq ft', 'square feet', 'sq_ft'):
            land_perches = land_size / SQFT_PER_PERCH
        else:
            land_perches = land_size
    else:
        land_perches = 0.0

    area_sqft = perches_to_sqft(land_perches)

    # Step 2: Derive dimensions
    has_width = plot_width_ft is not None and plot_width_ft > 0
    has_length = plot_length_ft is not None and plot_length_ft > 0

    if has_width and has_length:
        dim_source = 'user_supplied'
        w = plot_width_ft
        l = plot_length_ft
        # If dimensions are authoritative, recalculate area from them
        dim_area = w * l
        if area_sqft > 0:
            variance = abs(dim_area - area_sqft) / area_sqft
            if variance > 0.30:
                area_sqft = dim_area
                land_perches = area_sqft / SQFT_PER_PERCH
        else:
            area_sqft = dim_area
            land_perches = area_sqft / SQFT_PER_PERCH
    elif has_width and area_sqft > 0:
        dim_source = 'partially_derived'
        w = plot_width_ft
        l = area_sqft / w
    elif has_length and area_sqft > 0:
        dim_source = 'partially_derived'
        l = plot_length_ft
        w = area_sqft / l
    elif area_sqft > 0:
        dim_source = 'area_estimated'
        aspect = 1.25
        w = math.sqrt(area_sqft / aspect)
        l = area_sqft / w
    else:
        # No land info at all
        dim_source = 'area_estimated'
        w = 0.0
        l = 0.0

    w = round(w, 1)
    l = round(l, 1)

    # Step 3: Apply setbacks
    sb = dict(DEFAULT_SETBACKS)
    if setbacks:
        for k, v in setbacks.items():
            if k in sb and v is not None and v >= 0:
                sb[k] = v

    front_sb = max(sb['front'], 18.0) if parking_required else sb['front']
    bw = w - sb['left'] - sb['right']
    bl = l - front_sb - sb['rear']

    bw = max(0.0, round(bw, 1))
    bl = max(0.0, round(bl, 1))

    return NormalizedLand(
        land_size_perches=round(land_perches, 2),
        land_area_sqft=round(area_sqft, 1),
        plot_width_ft=w,
        plot_length_ft=l,
        dimension_source=dim_source,
        setbacks=sb,
        buildable_width_ft=bw,
        buildable_length_ft=bl,
        buildable_area_sqft=round(bw * bl, 1),
        max_coverage_area_sqft=round(max_buildable_area(land_perches), 1),
    )


# ---------------------------------------------------------------------------
# Catalogue loading (lightweight, no layout parsing)
# ---------------------------------------------------------------------------

@dataclass
class CataloguePlan:
    design_code: str
    bedrooms: int
    bathrooms: int
    floors: int
    topology_family: str
    min_land_perches: float
    max_land_perches: float
    min_plot_width_ft: float
    min_plot_length_ft: float
    supported_terrains: list[str]
    supported_styles: list[str]
    capabilities: dict[str, bool]


_catalogue_cache: list[CataloguePlan] | None = None


def _load_catalogue() -> list[CataloguePlan]:
    global _catalogue_cache
    if _catalogue_cache is not None:
        return _catalogue_cache

    if not CATALOGUE_PATH.exists():
        _catalogue_cache = []
        return _catalogue_cache

    raw = json.loads(CATALOGUE_PATH.read_text())
    plans = []
    for entry in raw:
        plans.append(CataloguePlan(
            design_code=entry.get('designCode', ''),
            bedrooms=entry.get('bedrooms', 0),
            bathrooms=entry.get('bathrooms', 0),
            floors=entry.get('floors', 1),
            topology_family=entry.get('topologyFamily', ''),
            min_land_perches=float(entry.get('minimumLandSizePerches', 0) or 0),
            max_land_perches=float(entry.get('maximumLandSizePerches', 50) or 50),
            min_plot_width_ft=float(entry.get('minimumPlotWidthFt', 0) or 0),
            min_plot_length_ft=float(entry.get('minimumPlotLengthFt', 0) or 0),
            supported_terrains=[t.lower() for t in entry.get('supportedTerrains', ['flat'])],
            supported_styles=[s.lower() for s in entry.get('supportedStyles', [])],
            capabilities=entry.get('capabilities', {}),
        ))
    _catalogue_cache = plans
    return _catalogue_cache


# ---------------------------------------------------------------------------
# Catalogue compatibility check
# ---------------------------------------------------------------------------

def _check_plan_compatibility(
    plan: CataloguePlan,
    land: NormalizedLand,
    bedrooms: int | None,
    bathrooms: int | None,
    floors: int | None,
    style: str | None,
    terrain: str | None,
    required_capabilities: dict[str, bool],
) -> list[str]:
    """Return list of rejection reason codes for a single plan."""
    reasons = []

    if bedrooms is not None and plan.bedrooms != bedrooms:
        reasons.append('BEDROOM_COUNT_MISMATCH')
    if bathrooms is not None and plan.bathrooms < bathrooms:
        reasons.append('BATHROOM_COUNT_INSUFFICIENT')
    if floors is not None and plan.floors != floors:
        reasons.append('FLOOR_COUNT_MISMATCH')

    if land.land_size_perches > 0:
        if land.land_size_perches < plan.min_land_perches:
            reasons.append('LAND_TOO_SMALL')
        if plan.max_land_perches and land.land_size_perches > plan.max_land_perches:
            reasons.append('LAND_TOO_LARGE')

    if land.plot_width_ft > 0 and plan.min_plot_width_ft > 0 and land.plot_width_ft < plan.min_plot_width_ft:
        reasons.append('PLOT_WIDTH_INSUFFICIENT')
    if land.plot_length_ft > 0 and plan.min_plot_length_ft > 0 and land.plot_length_ft < plan.min_plot_length_ft:
        reasons.append('PLOT_LENGTH_INSUFFICIENT')

    if terrain:
        terrain_lower = terrain.lower().replace('/', '').replace(' ', '_')
        # Normalize common terrain terms
        terrain_aliases = {
            'flat': ['flat', 'flat_urban', 'flat/urban', 'urban'],
            'hillside': ['hillside', 'sloped', 'hilly'],
            'gentle_slope': ['gentle_slope', 'gentle slope'],
        }
        matched = False
        for canon, aliases in terrain_aliases.items():
            if terrain_lower in aliases or terrain_lower == canon:
                if canon in plan.supported_terrains or any(a in plan.supported_terrains for a in aliases):
                    matched = True
                break
        if not matched and terrain_lower not in plan.supported_terrains:
            reasons.append('TERRAIN_UNSUPPORTED')

    if style:
        style_lower = style.lower().strip()
        if plan.supported_styles and style_lower not in plan.supported_styles:
            reasons.append('STYLE_UNSUPPORTED')

    for user_key, cap_key in CAPABILITY_MAP.items():
        if required_capabilities.get(user_key) and not plan.capabilities.get(cap_key, False):
            reasons.append(f'MISSING_CAPABILITY_{cap_key.upper()}')

    return reasons


def find_compatible_plans(
    land: NormalizedLand,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    floors: int | None = None,
    style: str | None = None,
    terrain: str | None = None,
    required_capabilities: dict[str, bool] | None = None,
) -> tuple[list[str], dict[str, int]]:
    """
    Return (compatible_plan_codes, rejection_summary).
    rejection_summary maps reason_code -> count.
    """
    catalogue = _load_catalogue()
    caps = required_capabilities or {}
    compatible = []
    rejections: dict[str, int] = {}

    for plan in catalogue:
        reasons = _check_plan_compatibility(plan, land, bedrooms, bathrooms, floors, style, terrain, caps)
        if not reasons:
            compatible.append(plan.design_code)
        else:
            for r in reasons:
                rejections[r] = rejections.get(r, 0) + 1

    return compatible, rejections


# ---------------------------------------------------------------------------
# Feasibility result
# ---------------------------------------------------------------------------

@dataclass
class FeasibilityResult:
    can_proceed: bool
    reason_codes: list[str] = field(default_factory=list)
    compatible_plan_count: int = 0
    compatible_plan_codes: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    land: dict[str, Any] | None = None
    rejection_summary: dict[str, int] | None = None

    def to_dict(self) -> dict:
        return {
            'can_proceed': self.can_proceed,
            'reason_codes': self.reason_codes,
            'compatible_plan_count': self.compatible_plan_count,
            'compatible_plan_codes': self.compatible_plan_codes,
            'suggestions': self.suggestions,
            'land': self.land,
            'rejection_summary': self.rejection_summary,
        }


# ---------------------------------------------------------------------------
# Core feasibility check (DESIGN_REQUEST)
# ---------------------------------------------------------------------------

def check_feasibility(requirements: dict[str, Any]) -> FeasibilityResult:
    """
    Given extracted requirements from the assistant, deterministically check feasibility.
    Returns a FeasibilityResult.
    """
    reason_codes: list[str] = []
    suggestions: list[str] = []

    # Extract fields
    land_size = requirements.get('land_size')
    land_unit = requirements.get('land_unit')
    plot_w = requirements.get('plot_width_ft')
    plot_l = requirements.get('plot_length_ft')
    bedrooms = requirements.get('bedrooms')
    bathrooms = requirements.get('bathrooms')
    floors = requirements.get('floors')
    style = requirements.get('style')
    terrain = requirements.get('terrain_type')
    parking = requirements.get('parking_spaces')

    # Gather required capabilities from booleans
    required_caps: dict[str, bool] = {}
    for key in CAPABILITY_MAP:
        val = requirements.get(key)
        if val is True:
            required_caps[key] = True
    if parking and parking > 0:
        required_caps['parking_required'] = True

    parking_reserved = required_caps.get('parking_required', False)

    # Task 1: Normalize land
    land = normalize_land(
        land_size=land_size,
        land_unit=land_unit,
        plot_width_ft=plot_w,
        plot_length_ft=plot_l,
        parking_required=parking_reserved,
    )

    land_dict = {
        'land_size_perches': land.land_size_perches,
        'land_area_sqft': land.land_area_sqft,
        'plot_width_ft': land.plot_width_ft,
        'plot_length_ft': land.plot_length_ft,
        'dimension_source': land.dimension_source,
        'setbacks': land.setbacks,
        'buildable_width_ft': land.buildable_width_ft,
        'buildable_length_ft': land.buildable_length_ft,
        'buildable_area_sqft': land.buildable_area_sqft,
        'max_coverage_area_sqft': land.max_coverage_area_sqft,
    }

    # Task 2: Validate buildable envelope
    if land.land_size_perches <= 0:
        reason_codes.append('NO_LAND_SIZE')
        suggestions.append('Provide land size in perches or square feet.')

    if land.buildable_width_ft < MIN_BUILDABLE_DIMENSION_FT and land.land_size_perches > 0:
        reason_codes.append('BUILDABLE_ENVELOPE_TOO_NARROW')
        suggestions.append(f'Buildable width is only {land.buildable_width_ft} ft after setbacks. Minimum is {MIN_BUILDABLE_DIMENSION_FT} ft.')

    if land.buildable_length_ft < MIN_BUILDABLE_DIMENSION_FT and land.land_size_perches > 0:
        reason_codes.append('BUILDABLE_ENVELOPE_TOO_SHORT')
        suggestions.append(f'Buildable length is only {land.buildable_length_ft} ft after setbacks. Minimum is {MIN_BUILDABLE_DIMENSION_FT} ft.')

    # Task 3: Check basic feasibility
    if bedrooms is not None and bedrooms not in SUPPORTED_BEDROOMS:
        reason_codes.append('BEDROOM_COUNT_UNSUPPORTED')
        suggestions.append(f'This system supports {SUPPORTED_BEDROOMS.start}–{SUPPORTED_BEDROOMS.stop - 1} bedrooms. You requested {bedrooms}.')

    if bathrooms is not None and bathrooms not in SUPPORTED_BATHROOMS:
        reason_codes.append('BATHROOM_COUNT_UNSUPPORTED')
        suggestions.append(f'This system supports {SUPPORTED_BATHROOMS.start}–{SUPPORTED_BATHROOMS.stop - 1} bathrooms. You requested {bathrooms}.')

    if floors is not None and floors not in SUPPORTED_FLOORS:
        reason_codes.append('FLOOR_COUNT_UNSUPPORTED')
        suggestions.append(f'This system supports {SUPPORTED_FLOORS.start}–{SUPPORTED_FLOORS.stop - 1} floors. You requested {floors}.')

    # Footprint check
    if bedrooms and land.buildable_area_sqft > 0:
        effective_floors = floors or 1
        available_floor_area = land.buildable_area_sqft * effective_floors
        # Conservative: living+kitchen+bath ~400 sqft base, then per bedroom
        min_needed = 400 + (bedrooms * MIN_SQFT_PER_BEDROOM)
        if parking_reserved:
            min_needed += MIN_PARKING_SQFT
        if available_floor_area < min_needed:
            reason_codes.append('BUILDABLE_ENVELOPE_TOO_SMALL')
            suggestions.append(
                f'The buildable area ({land.buildable_area_sqft:.0f} sq ft × {effective_floors} floor(s) = '
                f'{available_floor_area:.0f} sq ft) may be too small for {bedrooms} bedrooms '
                f'(estimated minimum ~{min_needed:.0f} sq ft). '
                f'Consider reducing bedrooms or adding floors.'
            )

    # Single-floor stair check
    if floors and floors == 1:
        # No stair geometry needed — OK
        pass
    elif floors and floors > 1:
        # Multi-floor needs stair core — handled by catalogue
        pass

    # Accessibility check
    if required_caps.get('accessible_friendly') and floors and floors > 1:
        suggestions.append(
            'Accessibility layout requires a ground-floor bedroom and bathroom. '
            'Multi-floor plans with accessibility support may be limited.'
        )

    # Task 4: Check catalogue
    compatible_codes, rejection_summary = find_compatible_plans(
        land=land,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        floors=floors,
        style=style,
        terrain=terrain,
        required_capabilities=required_caps,
    )

    if not compatible_codes and bedrooms is not None:
        reason_codes.append('NO_COMPATIBLE_BASE_PLAN')

        # Generate specific suggestions
        catalogue = _load_catalogue()
        available_beds = sorted(set(p.bedrooms for p in catalogue))
        available_floors = sorted(set(p.floors for p in catalogue))

        if bedrooms not in set(p.bedrooms for p in catalogue):
            suggestions.append(f'No plans available with {bedrooms} bedrooms. Available: {available_beds}.')
        if floors and floors not in set(p.floors for p in catalogue):
            suggestions.append(f'No plans available with {floors} floor(s). Available: {available_floors}.')

        # Suggest relaxations based on rejection reasons
        if rejection_summary:
            top_reasons = sorted(rejection_summary.items(), key=lambda x: -x[1])[:3]
            for code, count in top_reasons:
                if code == 'BEDROOM_COUNT_MISMATCH' and bedrooms and bedrooms > 4:
                    suggestions.append(f'Reduce bedrooms from {bedrooms} to 4 for more plan options.')
                elif code == 'FLOOR_COUNT_MISMATCH' and floors == 1 and bedrooms and bedrooms > 3:
                    suggestions.append('Use 2 floors instead of 1 to fit more bedrooms.')
                elif code == 'LAND_TOO_SMALL':
                    suggestions.append('Your land may be too small for some plans. Consider fewer bedrooms or more floors.')
                elif code.startswith('MISSING_CAPABILITY_'):
                    cap_name = code.replace('MISSING_CAPABILITY_', '').lower().replace('_', ' ')
                    suggestions.append(f'Remove the "{cap_name}" requirement for more plan options.')

    # Task 5: Decision
    can_proceed = len(reason_codes) == 0 and len(compatible_codes) > 0

    return FeasibilityResult(
        can_proceed=can_proceed,
        reason_codes=reason_codes,
        compatible_plan_count=len(compatible_codes),
        compatible_plan_codes=compatible_codes[:10],  # Limit to top 10
        suggestions=suggestions,
        land=land_dict,
        rejection_summary=rejection_summary if rejection_summary else None,
    )


# ---------------------------------------------------------------------------
# Advice mode (LAND_FEASIBILITY_ADVICE)
# ---------------------------------------------------------------------------

def generate_feasibility_advice(requirements: dict[str, Any]) -> dict[str, Any]:
    """
    For LAND_FEASIBILITY_ADVICE intent: given land info, return practical ranges
    based on actual catalogue coverage. Does NOT give one fake exact answer.
    """
    land_size = requirements.get('land_size')
    land_unit = requirements.get('land_unit')
    plot_w = requirements.get('plot_width_ft')
    plot_l = requirements.get('plot_length_ft')
    terrain = requirements.get('terrain_type')

    land = normalize_land(land_size=land_size, land_unit=land_unit, plot_width_ft=plot_w, plot_length_ft=plot_l)

    if land.land_size_perches <= 0:
        return {
            'advice_type': 'LAND_FEASIBILITY',
            'message': 'Please provide your land size to receive feasibility advice.',
            'ranges': None,
            'land': None,
        }

    catalogue = _load_catalogue()

    # Filter plans that fit this land size
    land_compatible = [
        p for p in catalogue
        if p.min_land_perches <= land.land_size_perches
        and (p.max_land_perches is None or p.max_land_perches == 0 or land.land_size_perches <= p.max_land_perches)
    ]

    if not land_compatible:
        return {
            'advice_type': 'LAND_FEASIBILITY',
            'message': f'No validated plans are available for {land.land_size_perches} perch land in the current catalogue.',
            'ranges': None,
            'land': {
                'land_size_perches': land.land_size_perches,
                'land_area_sqft': land.land_area_sqft,
                'buildable_area_sqft': land.buildable_area_sqft,
            },
        }

    # Group by floor count
    floor_options: dict[int, dict[str, Any]] = {}
    for f in sorted(set(p.floors for p in land_compatible)):
        plans_for_floor = [p for p in land_compatible if p.floors == f]
        bed_range = sorted(set(p.bedrooms for p in plans_for_floor))
        bath_range = sorted(set(p.bathrooms for p in plans_for_floor))

        # Check which capabilities are available
        available_caps = set()
        for p in plans_for_floor:
            for cap, supported in p.capabilities.items():
                if supported:
                    available_caps.add(cap)

        floor_options[f] = {
            'bedroom_range': [min(bed_range), max(bed_range)],
            'bathroom_range': [min(bath_range), max(bath_range)],
            'plan_count': len(plans_for_floor),
            'topologies': sorted(set(p.topology_family for p in plans_for_floor)),
            'available_features': sorted(available_caps),
        }

    # Build a human-readable message
    parts = [f'On {land.land_size_perches:.0f} perch ({land.land_area_sqft:.0f} sq ft) land:']
    for f, info in sorted(floor_options.items()):
        bed_lo, bed_hi = info['bedroom_range']
        bath_lo, bath_hi = info['bathroom_range']
        bed_str = f'{bed_lo}–{bed_hi}' if bed_lo != bed_hi else str(bed_lo)
        bath_str = f'{bath_lo}–{bath_hi}' if bath_lo != bath_hi else str(bath_lo)
        parts.append(
            f'• {f}-floor layout: {bed_str} bedrooms, {bath_str} bathrooms '
            f'({info["plan_count"]} validated plan(s) available)'
        )

    parts.append(f'Buildable area after default setbacks: ~{land.buildable_area_sqft:.0f} sq ft.')
    parts.append('These ranges are based on validated plans in the system catalogue, not generic estimates.')

    return {
        'advice_type': 'LAND_FEASIBILITY',
        'message': '\n'.join(parts),
        'ranges': floor_options,
        'land': {
            'land_size_perches': land.land_size_perches,
            'land_area_sqft': land.land_area_sqft,
            'plot_width_ft': land.plot_width_ft,
            'plot_length_ft': land.plot_length_ft,
            'dimension_source': land.dimension_source,
            'buildable_area_sqft': land.buildable_area_sqft,
            'max_coverage_area_sqft': land.max_coverage_area_sqft,
        },
    }
