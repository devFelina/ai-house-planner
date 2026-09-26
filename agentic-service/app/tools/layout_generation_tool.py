from __future__ import annotations

"""Validated base-plan selection with deterministic adaptation and strict quality gates."""


import json
import logging
from collections import Counter

from app.design.architectural_quality import validate_architectural_quality
from app.design.base_plan_library import (
    compact_plan_metadata,
    compatibility_rejection_reasons,
    deduplicate_base_plans,
    filter_compatible_base_plans,
    load_base_plan_catalog,
    rank_base_plans,
)
from app.design.candidate_generator import GenerationFailure
from app.design.diversity import geometry_fingerprint
from app.design.models import Requirements
from app.design.normalized_input import NormalizedDesignInput
from app.design.plan_adapter import PlanAdapter
from app.design.plan_suitability import suitability_breakdown
from app.design.plot_constraints import PlotConstraints
from app.design.revision import (
    apply_supported_revision,
    preserve_revision_preferences,
    requests_another_design,
)
from app.design.scoring import family_affinity
from app.design.topology_registry import eligible_topologies
from app.providers import get_available_design_provider, get_next_design_provider
from app.schemas.ai_plan_decision import AIPlanDecision
from app.schemas.design_result import DesignResult
from app.validation.geometry_validator import validate_geometry
from app.land.land_math import MAX_COVERAGE_RATIO, SQFT_PER_PERCH

SYSTEM_PROMPT = (

    "You are the HousePlanner design-selection agent. Choose among validated base plans only. "

    "Do not generate coordinates, room dimensions, openings, or stair locations. Return only the strict schema."

)

logger = logging.getLogger(__name__)


def prepare_inputs(

    land_size_perches: float,

    terrain_type: str,

    preferences: dict,

    plot_constraints: dict | PlotConstraints | None = None,

    design_seed: int | None = None,

) -> tuple[Requirements, PlotConstraints]:

    values = dict(preferences)

    if 'architecturalStyle' in values and 'style' not in values:

        values['style'] = values.pop('architecturalStyle')

    if 'style_preference' in values and 'style' not in values:

        values['style'] = values.pop('style_preference')

    if 'accessibility_preference' in values and 'accessibility' not in values:

        values['accessibility'] = values.pop('accessibility_preference')

    aliases = {

        'architectural_style': 'style',

        'master_ensuite': 'attached_bathroom',

        'separate_dining': 'dining_required',

        'parking_required': 'parking',

        'utility': 'utility_room',

    }

    for source_key, target_key in aliases.items():

        if source_key in values and target_key not in values:

            values[target_key] = values.pop(source_key)

    if values.get('space_priority') == 'outdoor_garden':

        values['garden_priority'] = True

    if values.get('space_priority') == 'compact_cost_efficient':

        values['compact_priority'] = True

    if values.get('attached_bathroom'):

        values['master_bedroom'] = True

    if design_seed is not None:

        values['design_seed'] = design_seed

    values = {key: value for key, value in values.items() if value is not None}

    req = Requirements.model_validate(values)

    source = plot_constraints if plot_constraints is not None else preferences.get('plot_constraints', {})

    if isinstance(source, PlotConstraints):

        source = source.model_dump(include=set(PlotConstraints.model_fields))

    raw = dict(source)

    if raw.get('entrance_side') == 'road_side':

        raw['entrance_side'] = raw.get('road_side', preferences.get('road_side', 'south'))

    for key in PlotConstraints.model_fields:

        if key in preferences and key not in raw:

            raw[key] = preferences[key]

    raw.update(

        land_size_perches=land_size_perches,

        terrain_type=terrain_type.lower(),

        parking_reserved=req.parking,

    )

    return req, PlotConstraints.model_validate(raw)



NO_DISTINCT_LAYOUT = 'No distinct compatible layout is currently available for these requirements.'


def _candidate_pool(req: Requirements, plot: PlotConstraints, previous_fingerprint=None,
                    preferred_plan_code: str | None = None,
                    excluded_plan_code: str | None = None):

    compatible = filter_compatible_base_plans(req, plot)

    if excluded_plan_code:
        # We explicitly exclude this plan code if alternatives exist.
        # But if it's the ONLY plan, we might have to use it (or fail). The user requested to fail if no alternatives.
        compatible = [plan for plan in compatible if plan.plan_code != excluded_plan_code]
        if not compatible:
            raise GenerationFailure('No sufficiently different compatible design is currently available.')

    if preferred_plan_code:
        compatible = [plan for plan in compatible if plan.plan_code == preferred_plan_code]
        if not compatible:
            raise GenerationFailure('The selected base plan is not compatible with these requirements.')

    rejected = Counter(reason for plan in load_base_plan_catalog()
                       for reason in compatibility_rejection_reasons(plan, req, plot))
    logger.info('[Candidate Filter] compatible_plan_codes=%s rejected_reasons=%s',
                [plan.plan_code for plan in compatible], dict(sorted(rejected.items())))

    if not compatible:

        raise GenerationFailure('No compatible validated base plans exist for the supplied requirements.')

    ranked = deduplicate_base_plans(rank_base_plans(compatible, req, plot), previous_fingerprint)
    if not ranked:
        raise GenerationFailure(NO_DISTINCT_LAYOUT)

    logger.info('[Suitability Ranking] candidates=%s', [
        {'plan_code': plan.plan_code, 'topology': plan.topology_family,
         'suitability_score': suitability_breakdown(plan, req, plot)['score']}
        for plan in ranked
    ])

    diverse = []

    seen_families = set()

    remaining = []
    for plan in ranked:
        if plan.topology_family not in seen_families:
            diverse.append(plan)
            seen_families.add(plan.topology_family)
        else:
            remaining.append(plan)

    # Retain the complete unique pool for fallback beyond the AI shortlist.
    return diverse + remaining



def _build_ai_prompt(normalized: NormalizedDesignInput, plans, req: Requirements,
                     plot: PlotConstraints, previous_plan_code=None,

                     previous_fingerprint=None, revision_reason: str | None = None) -> str:

    payload = {

        'normalized_input': normalized.model_dump(),

        'candidate_plans': compact_plan_metadata(plans, req, plot),

        'previous_plan_code': previous_plan_code,

        'previous_fingerprint': previous_fingerprint,

        'revision_reason': revision_reason,

        'generation_mode': 'generate_another' if requests_another_design(revision_reason) else 'generate',

    }

    return json.dumps(payload, separators=(',', ':'), ensure_ascii=True)



def _fallback_decision(plans, req: Requirements, plot: PlotConstraints, previous_plan_code=None,

                       previous_fingerprint=None) -> AIPlanDecision:

    plans = deduplicate_base_plans(plans, previous_fingerprint)
    if not plans:
        raise GenerationFailure(NO_DISTINCT_LAYOUT)
    chosen = plans[0]

    alternatives = [plan.plan_code for plan in plans[1:7]]

    public_orientation = plot.road_side

    private_orientation = {'south': 'north', 'north': 'south', 'east': 'west', 'west': 'east'}[plot.road_side]

    service_orientation = {'south': 'west', 'north': 'east', 'east': 'south', 'west': 'north'}[plot.road_side]

    return AIPlanDecision.model_validate({

        'selected_plan_code': chosen.plan_code,

        'alternative_plan_codes': alternatives,

        'design_intent': {

            'public_zone_orientation': public_orientation,

            'private_zone_orientation': private_orientation,

            'service_zone_orientation': service_orientation,

            'privacy_priority': 'high' if getattr(req, 'privacy_priority', False) or getattr(req, 'attached_bathroom', False) else 'balanced',

            'circulation_preference': 'short_central_hall',

        },

        'adaptations': {

            'mirror_horizontal': False,

            'mirror_vertical': False,

            'rotation_degrees': 0,

            'living_scale': 1.0,

            'bedroom_scale': 1.0,

            'entrance_side': plot.effective_entrance_side,

            'preserve_stair_core': True,

            'preserve_wet_core': True,

        },

        'reason_codes': ['plot_fit', 'preference_match', 'low_circulation'],

    })



def _validate_and_finalize(design: DesignResult, req: Requirements, plot: PlotConstraints,

                           base_plan_code: str, provider_name: str | None, model_name: str | None,

                           ai_decision: AIPlanDecision, tried_codes: list[str], candidate_pool) -> DesignResult:

    quality = validate_architectural_quality(design, req=req, plot=plot)

    if not quality.passed:

        raise GenerationFailure('Architectural quality validation failed.', [{'base_plan_code': base_plan_code, 'failures': quality.failures}])

    geometry = validate_geometry(design.rooms, req.bedrooms, req.floors, plot.land_size_perches, plot=plot, design=design)

    if not geometry.passed:

        raise GenerationFailure('Local geometry validation failed.', [{'base_plan_code': base_plan_code, 'failures': geometry.failures}])

    design.design_score = quality.score

    design.candidate_status = quality.status

    design.geometry_fingerprint = geometry_fingerprint(design)

    if design.candidate_summary is None:
        design.candidate_summary = {}
    design.candidate_summary.update({

        'selected_plan_code': base_plan_code,

        'provider': provider_name,

        'model': model_name,

        'generation_mode': 'ai_adapted_template' if provider_name else 'deterministic_template_selection',

        'quality_metrics': quality.metrics,

        'quality_breakdown': quality.score_breakdown,

        'geometry_validation': geometry.to_dict(),

        'tried_plan_codes': tried_codes,

        'compatible_plan_codes': [plan.plan_code for plan in candidate_pool],

        'catalog_size': len(load_base_plan_catalog()),

    })

    return design



def generate_layout(

    land_size_perches: float,

    terrain_type: str,

    preferences: dict,

    previous_design: dict | None = None,

    revision_reason: str | None = None,

    *,

    plot_constraints: dict | PlotConstraints | None = None,

    design_seed: int | None = None,
    preferred_plan_code: str | None = None,
    excluded_plan_code: str | None = None,
    excluded_fingerprint_explicit: str | None = None,

) -> DesignResult:

    try:

        if previous_design is not None:
            preferences = preserve_revision_preferences(preferences, previous_design)
        revised_preferences, applied_revision = apply_supported_revision(preferences, revision_reason)

        req, plot = prepare_inputs(land_size_perches, terrain_type, revised_preferences, plot_constraints, design_seed)

        if plot.terrain_type == 'unknown':

            raise GenerationFailure('Terrain is unknown; provide a manual terrain classification.')

        if plot.plot_width_ft and plot.plot_width_ft < 15:

            raise GenerationFailure(f'Plot width ({plot.plot_width_ft} ft) is too narrow for standard construction.')

        if plot.plot_length_ft and plot.plot_length_ft < 15:

            raise GenerationFailure(f'Plot length ({plot.plot_length_ft} ft) is too shallow for standard construction.')

        if plot.buildable_width < 10 or plot.buildable_length < 10:

            raise GenerationFailure('Setbacks leave insufficient buildable area (less than 10ft).')

    except (ValueError, TypeError) as exc:

        raise GenerationFailure(f'Invalid design requirements: {exc}') from exc

    normalized = NormalizedDesignInput.from_inputs(req, plot)
    logger.info('[Design Input] normalized=%s', normalized.model_dump())

    previous_plan_code = None

    previous_fingerprint = None

    if requests_another_design(revision_reason) and previous_design is None:
        raise GenerationFailure('Cannot compare geometry: the previous design is required.')

    if previous_design is not None:

        try:

            previous_layout = DesignResult.model_validate(previous_design)

            previous_fingerprint = geometry_fingerprint(previous_layout)

            previous_plan_code = previous_layout.candidate_summary.get('selected_plan_code') if isinstance(previous_layout.candidate_summary, dict) else None

        except Exception as exc:
            if requests_another_design(revision_reason):
                raise GenerationFailure('Cannot compare geometry: the previous design is invalid.') from exc
            previous_fingerprint = None

    excluded_fingerprint = excluded_fingerprint_explicit or (previous_fingerprint if requests_another_design(revision_reason) else None)
    candidate_pool = _candidate_pool(req, plot, excluded_fingerprint, preferred_plan_code, excluded_plan_code)
    shortlist = candidate_pool[:7]

    request_type = ('generate_another' if requests_another_design(revision_reason)
                    else 'revision' if revision_reason else 'generation')
    provider = get_available_design_provider()
    provider_name = None
    model_name = None
    attempted_providers = []
    decision = None
    while provider:
        provider_name = getattr(provider, 'provider_name', None)
        model_name = getattr(provider, 'model_name', None)
        attempted_providers.append(provider_name)
        print(f'[Design Agent] Calling provider {provider.provider_name} for base-plan selection...')
        user_prompt = _build_ai_prompt(normalized, shortlist, req, plot, previous_plan_code,
                                       previous_fingerprint, revision_reason)
        try:
            decision = AIPlanDecision.model_validate(
                provider.generate_json(SYSTEM_PROMPT, user_prompt, AIPlanDecision))
            logger.info('[AI Selection] provider=%s model=%s selected_plan=%s alternatives=%s reason_codes=%s',
                        provider_name, model_name, decision.selected_plan_code,
                        decision.alternative_plan_codes, decision.reason_codes)
            break
        except Exception as exc:
            print(f'[Design Agent] {provider_name} decision failed ({type(exc).__name__}); trying next provider.')
            provider = get_next_design_provider(provider_name or '')
            provider_name = None
            model_name = None

    adapter = PlanAdapter()
    tried_codes: list[str] = []
    failures: list[dict] = []
    repeated_geometry = False

    def attempt(plan, selection, selected_provider=None, selected_model=None):
        nonlocal repeated_geometry
        tried_codes.append(plan.plan_code)
        try:
            # Keep the selected code accurate when trying an alternative.
            selection = selection.model_copy(update={'selected_plan_code': plan.plan_code})
            logger.info('[Adaptation] plan_code=%s operations=%s',
                        plan.plan_code, selection.adaptations.model_dump())
            design = adapter.adapt(plan, selection, req, plot)
            final_fingerprint = geometry_fingerprint(design)
            if excluded_fingerprint and final_fingerprint == excluded_fingerprint:
                repeated_geometry = True
                failures.append({'plan_code': plan.plan_code,
                                 'reason': 'previous_geometry_repeated',
                                 'failures': [NO_DISTINCT_LAYOUT]})
                return None
            final_design = _validate_and_finalize(
                design, req, plot, plan.plan_code, selected_provider, selected_model,
                selection, tried_codes, candidate_pool)
            logger.info('[Validation] plan_code=%s architectural_score=%s geometry_passed=%s',
                        plan.plan_code, final_design.design_score, True)
            generation_mode = ('ai_adapted_template' if selected_provider else
                               'deterministic_fallback' if attempted_providers else
                               'deterministic_template_selection')
            final_design.candidate_summary.update({
                'generation_mode': generation_mode,
                'ai_ran': bool(attempted_providers),
                'attempted_providers': attempted_providers,
                'base_plan_name': plan.name,
                'base_plan_code': plan.plan_code,
                'template_id': final_design.template_id,
                'alternative_plan_codes': selection.alternative_plan_codes,
                'reason_codes': selection.reason_codes,
                'normalized_input': normalized.model_dump(),
                'compatible_plan_count': len(candidate_pool),
            })
            if previous_fingerprint:
                final_design.candidate_summary['previous_fingerprint'] = previous_fingerprint
            if previous_plan_code:
                final_design.candidate_summary['previous_plan_code'] = previous_plan_code
            if revision_reason:
                final_design.candidate_summary['revision_feedback'] = revision_reason
                final_design.candidate_summary['bounded_revision_preferences'] = applied_revision
            logger.info('[Final Design] selected_base_plan=%s topology=%s fingerprint=%s generation_mode=%s',
                        plan.plan_code, final_design.template_family,
                        final_design.geometry_fingerprint,
                        final_design.candidate_summary.get('generation_mode'))
            logger.info('[AI Agent] request_type=%s provider=%s model=%s candidate_count=%s selected_plan=%s reason_codes=%s generation_mode=%s',
                        request_type, selected_provider or 'deterministic', selected_model or 'none',
                        len(shortlist), plan.plan_code, selection.reason_codes,
                        final_design.candidate_summary.get('generation_mode'))
            return final_design
        except GenerationFailure as exc:
            failures.extend(exc.failures or [{'plan_code': plan.plan_code, 'failures': [str(exc)]}])
        except Exception as exc:
            failures.append({'plan_code': plan.plan_code, 'failures': [str(exc)]})
        return None

    if decision is not None:
        candidate_by_code = {plan.plan_code: plan for plan in shortlist}
        for plan_code in [decision.selected_plan_code, *decision.alternative_plan_codes]:
            if plan_code in tried_codes:
                continue
            plan = candidate_by_code.get(plan_code)
            if plan is None:
                failures.append({'plan_code': plan_code, 'failures': ['plan_not_compatible']})
                continue
            result = attempt(plan, decision, provider_name, model_name)
            if result is not None:
                return result

    # Try all unique compatible geometries, including those outside the shortlist.
    # AI adaptations may have failed, so retry those plans with deterministic adaptations.
    fallback = _fallback_decision(candidate_pool, req, plot, previous_plan_code, excluded_fingerprint)
    logger.info('[AI Selection] provider=deterministic selected_plan=%s alternatives=%s reason_codes=%s',
                fallback.selected_plan_code, fallback.alternative_plan_codes, fallback.reason_codes)
    for plan in candidate_pool:
        result = attempt(plan, fallback)
        if result is not None:
            return result

    if repeated_geometry:
        raise GenerationFailure(NO_DISTINCT_LAYOUT, failures)
    if failures:
        raise GenerationFailure('No validated base plan could be adapted into a high-quality design.', failures)
    raise GenerationFailure('Candidate pool exhausted without finding a valid plan.')



def select_template(bedrooms: int, floors: int, terrain_type: str, land_size_perches: float) -> dict:

    """Legacy helper name retained; returns a validated base-plan summary, never coordinates."""

    import math

    side = round(math.sqrt(land_size_perches * 272.25), 1)

    req, plot = prepare_inputs(

        land_size_perches,

        terrain_type,

        {'bedrooms': bedrooms, 'floors': floors},

        plot_constraints={'plot_width_ft': side, 'plot_length_ft': side},

    )

    choices = eligible_topologies(req, plot)

    if not choices:

        raise GenerationFailure('No eligible topology for the plot and requirements.')

    topology = max(choices, key=lambda topo: family_affinity(topo.name, req, plot))

    return {

        'name': topology.name,

        'plan_code': topology.name,

        'min_width': topology.min_width,

        'min_length': topology.min_length,

        'supported_floors': list(topology.supported_floors),

        'bedroom_range': list(topology.bedroom_range),

        'zoning': topology.zoning,

        'adjacency': list(topology.adjacency),

    }





def _mock_layout(
    bedrooms: int,
    floors: int,
    terrain_type: str,
    foundation_type: str,
    max_area: float,
    template_id: str | None = None,
    template: dict | None = None,
) -> DesignResult:
    """Compatibility wrapper: the offline path uses the same validated base-plan engine."""
    import math
    perches = max_area / (SQFT_PER_PERCH * MAX_COVERAGE_RATIO)
    side = round(math.sqrt(perches * 272.25), 1)

    result = generate_layout(
        land_size_perches=perches,
        terrain_type=terrain_type,
        preferences={'bedrooms': bedrooms, 'floors': floors, 'design_seed': 0},
        plot_constraints={'plot_width_ft': side, 'plot_length_ft': side}
    )

    if template_id:
        result.template_id = template_id
    result.foundation_type = foundation_type
    return result
