from typing import Optional, Union
"""Generative AI layout planner with procedural fallback."""
import json
import uuid
from app.config import GOOGLE_API_KEY
from app.design.candidate_generator import GenerationFailure, select_best
from app.design.diversity import geometry_fingerprint, stable_seed
from app.design.geometry_engine import TERRAIN_FOUNDATION_MAP
from app.design.models import Requirements
from app.design.scoring import score_layout
from app.design.revision import apply_supported_revision, requests_another_design
from app.design.plot_constraints import PlotConstraints
from app.design.spatial_program import build_program
from app.design.topology_registry import eligible_topologies, topology_dict
from app.schemas.design_result import DesignResult
from app.tools.geometry_validator import validate_geometry
from app.tools.land_utils import SQFT_PER_PERCH, MAX_COVERAGE_RATIO

AI_CANDIDATE_COUNT = 3
MAX_AI_REVISIONS = 3

SYSTEM_PROMPT = """You are the Design Agent of an AI-Assisted Home Design & Cost Planner.
Create a realistic conceptual residential floor plan from the supplied homeowner
requirements, plot constraints, terrain, spatial program and eligible high-level
concepts. You are responsible for the spatial zoning, room arrangement, circulation,
floor distribution, dimensions and x/y coordinates. Do not copy a predefined layout.
Do not assume a two-row grid.

This is a university-level planning and estimation system. The generated design is NOT construction-ready architectural documentation. It is a conceptual floor plan used for visualization, cost estimation, validation, and design revision.

Return only JSON matching the response schema. Coordinates use architectural feet,
with (0,0) at the buildable rectangle's southwest corner. Room rectangles on the same
floor cannot overlap. Every normal room must be reachable from an exterior entrance
through declared connections. Non-stair connections require a shared wall and matching
door openings on both rooms. Multi-floor designs require aligned staircase rooms and
stair connections. Use unique stable room IDs within the candidate. Include the exact
requested bedroom and floor counts, living room, kitchen and bathroom. Keep rooms inside
buildable_width/buildable_length and total area inside maximum_total_floor_area.

Functional priorities: circulation, independent bedroom access, privacy, living/dining/
kitchen relationships, bathroom access, efficient area, terrain suitability, exterior
wall opportunities and homeowner preferences. Ground floors generally prioritize public
and service spaces; upper floors generally prioritize private spaces. These are design
preferences, not a fixed arrangement. Do not output construction materials, structure,
electrical, plumbing or approval claims. Deterministic validation is the final authority.
"""

def prepare_inputs(land_size_perches: float, terrain_type: str, preferences: dict,
                   plot_constraints: Union[dict, Optional[PlotConstraints]] = None,
                   design_seed: Optional[int] = None) -> tuple[Requirements, PlotConstraints]:
    values = dict(preferences)
    if 'architecturalStyle' in values and 'style' not in values:
        values['style'] = values.pop('architecturalStyle')
    if 'style_preference' in values and 'style' not in values:
        values['style'] = values.pop('style_preference')
    if 'accessibility_preference' in values and 'accessibility' not in values:
        values['accessibility'] = values.pop('accessibility_preference')
    if design_seed is not None:
        values['design_seed'] = design_seed
    req = Requirements.model_validate(values)
    source = plot_constraints if plot_constraints is not None else preferences.get('plot_constraints', {})
    if isinstance(source, PlotConstraints):
        source = source.model_dump(include=set(PlotConstraints.model_fields))
    raw = dict(source)
    for key in PlotConstraints.model_fields:
        if key in preferences and key not in raw:
            raw[key] = preferences[key]
    raw.update(land_size_perches=land_size_perches, terrain_type=terrain_type.lower(), parking_reserved=req.parking)
    return req, PlotConstraints.model_validate(raw)


def generate_layout(land_size_perches: float, terrain_type: str, preferences: dict,
                    previous_design: Optional[dict] = None, revision_reason: Optional[str] = None,
                    *, plot_constraints: Union[dict, Optional[PlotConstraints]] = None,
                    design_seed: Optional[int] = None) -> DesignResult:
    try:
        revised_preferences, applied_revision = apply_supported_revision(preferences, revision_reason)
        req, plot = prepare_inputs(land_size_perches, terrain_type, revised_preferences, plot_constraints, design_seed)
    except (ValueError, TypeError) as exc:
        raise GenerationFailure(f'Invalid design requirements: {exc}') from exc
        
    mode = 'procedural_demo_fallback'
    result = None

    if GOOGLE_API_KEY and plot.terrain_type != 'unknown':
        base_payload = {'plot': plot.model_dump(), 'requirements': req.model_dump(),
                        'eligible_families': [topology_dict(t) for t in eligible_topologies(req, plot)],
                        'spatial_program': build_program(req).model_dump(),
                        'previous_design': previous_design,
                        'revision_feedback': revision_reason,
                        'design_seed': req.design_seed}
        valid_candidates = []
        failures = []
        eligible_family_names = {item['name'] for item in base_payload['eligible_families']}
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GOOGLE_API_KEY, http_options=types.HttpOptions(timeout=25000))
            try:
                for candidate_index in range(AI_CANDIDATE_COUNT):
                    print(f'[Design Agent] Generating AI candidate {candidate_index + 1}/{AI_CANDIDATE_COUNT}')
                    payload = dict(base_payload, candidate_index=candidate_index,
                                   diversity_instruction='Use a genuinely different spatial strategy from prior candidates.')
                    prompt = json.dumps(payload, default=str)
                    prior = None
                    for revision in range(MAX_AI_REVISIONS):
                        try:
                            data = _parse_design_result(_call_gemini_design(client, prompt))
                            if not data:
                                raise ValueError('Invalid JSON response')
                            data.setdefault('design_id', str(uuid.uuid4()))
                            data.setdefault('template_id', data.get('template_family', 'CUSTOM_AI'))
                            data['floor_count'] = req.floors
                            data['terrain_type'] = plot.terrain_type
                            data['foundation_type'] = TERRAIN_FOUNDATION_MAP[plot.terrain_type]
                            candidate = DesignResult.model_validate(data)
                            if candidate.template_family not in eligible_family_names:
                                raise ValueError(
                                    f"template_family must be one of {sorted(eligible_family_names)}"
                                )
                            candidate.total_built_up_area_sqft = round(sum(r.width * r.length for r in candidate.rooms), 2)
                            candidate.ground_footprint_sqft = round(sum(r.width * r.length for r in candidate.rooms if r.floor == 1), 2)
                            candidate.design_seed = req.design_seed
                            candidate.plot_constraints = plot.model_dump()
                            candidate.program = build_program(req).model_dump()
                            check = validate_geometry(candidate.rooms, req.bedrooms, req.floors,
                                                      land_size_perches, plot=plot, design=candidate)
                            if check.passed:
                                candidate.design_score, breakdown = score_layout(candidate, req, plot)
                                candidate.geometry_fingerprint = geometry_fingerprint(candidate)
                                candidate.candidate_summary = {'candidate_index': candidate_index,
                                                               'revision_count': revision,
                                                               'score_breakdown': breakdown}
                                valid_candidates.append(candidate)
                                print(f'[Geometry Validator] Candidate {candidate_index + 1} passed; score={candidate.design_score}')
                                break
                            prior = candidate.model_dump()
                            failures.append({'candidate': candidate_index, 'revision': revision,
                                             'failures': check.failures})
                            print(f'[Geometry Validator] Candidate {candidate_index + 1} failed: {check.failures}')
                            prompt = json.dumps(dict(payload, previous_attempt=prior,
                                exact_validation_failures=check.failures,
                                revision_instruction='Preserve valid choices and fix every listed failure.'), default=str)
                        except (ValueError, TypeError) as exc:
                            failures.append({'candidate': candidate_index, 'revision': revision,
                                             'failures': [f'Schema error: {exc}']})
                            prompt = json.dumps(dict(payload, previous_attempt=prior,
                                exact_validation_failures=[f'Schema error: {exc}'],
                                revision_instruction='Return complete JSON matching the schema.'), default=str)
            finally:
                client.close()
        except Exception as exc:
            raise GenerationFailure(f'Gemini design generation failed: {type(exc).__name__}', failures) from exc

        unique = {}
        for candidate in valid_candidates:
            current = unique.get(candidate.geometry_fingerprint)
            if current is None or candidate.design_score > current.design_score:
                unique[candidate.geometry_fingerprint] = candidate
        if not unique:
            raise GenerationFailure('Unable to produce valid AI geometry after bounded revisions.', failures)
        result = max(unique.values(), key=lambda c: (c.design_score, c.geometry_fingerprint))
        result.candidate_summary.update({
            'generation_mode': 'ai_generative',
            'generated_count': AI_CANDIDATE_COUNT,
            'valid_count': len(valid_candidates),
            'unique_valid_count': len(unique),
            'rejected_attempt_count': len(failures),
            'validation_failures': failures,
            'candidates': [{'design_id': c.design_id, 'family': c.template_family,
                            'score': c.design_score,
                            'geometry_fingerprint': c.geometry_fingerprint}
                           for c in unique.values()],
        })
        mode = 'ai_generative'

    if result is None:
        # Explicit demo-only fallback when no API key is configured.
        if req.design_seed is None:
            req.design_seed = stable_seed({'requirements': req.model_dump(), 'plot': plot.model_dump()})
        excluded = set()
        if previous_design and requests_another_design(revision_reason):
            previous_fingerprint = previous_design.get('geometry_fingerprint')
            if previous_fingerprint:
                excluded.add(previous_fingerprint)
        result = select_best(req, plot, excluded_fingerprints=excluded)
        check = validate_geometry(result.rooms, req.bedrooms, req.floors, land_size_perches, plot=plot, design=result)
        if not check.passed:
            raise GenerationFailure('Selected candidate failed final validation.', [{'failures': check.failures}])
        result.candidate_summary['fallback_disclosure'] = (
            'Procedural demo fallback; Gemini did not create this geometry.'
        )
        mode = 'procedural_demo_fallback'

    known_extras = set(PlotConstraints.model_fields) | {'plot_constraints', 'photo_url'}
    unhandled = sorted(set(req.model_extra or {}) - known_extras)
    result.candidate_summary.update(generation_mode=mode, unhandled_preferences=unhandled)
    if unhandled:
        result.candidate_summary.setdefault('notes', []).append('Unrecognized preferences were not applied: '+', '.join(unhandled))
    if revision_reason:
        result.candidate_summary['revision_feedback'] = revision_reason
        result.candidate_summary['bounded_revision_preferences'] = applied_revision
        
    return result


def _call_gemini_design(client, user_prompt: str) -> str:
    from google.genai import types
    response = client.models.generate_content(
        model='gemini-3.6-flash', contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.4,
                                          max_output_tokens=6000, response_mime_type='application/json',
                                          response_json_schema=DesignResult.model_json_schema()))
    return (response.text or '').strip()


def _parse_design_result(text: str) -> Optional[dict]:
    try:
        cleaned = '\n'.join(line for line in text.strip().splitlines() if not line.strip().startswith('```'))
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError, AttributeError):
        return None


def select_template(bedrooms: int, floors: int, terrain_type: str, land_size_perches: float) -> dict:
    """Legacy helper name retained; returns topology rules, never finished coordinates."""
    req, plot = prepare_inputs(land_size_perches, terrain_type, {'bedrooms': bedrooms, 'floors': floors})
    choices = eligible_topologies(req, plot)
    if not choices:
        raise GenerationFailure('No eligible topology for the plot and requirements.')
    from app.design.scoring import family_affinity
    topology = max(choices, key=lambda t: family_affinity(t.name, req, plot))
    return {'template_id': f'{bedrooms}BR_{floors}F_{terrain_type.upper()}', **topology_dict(topology)}


def _mock_layout(bedrooms: int, floors: int, terrain_type: str, foundation_type: str,
                 max_area: float, template_id: Optional[str] = None, template: Optional[dict] = None) -> DesignResult:
    """Compatibility wrapper: the offline path uses the same validated candidate engine."""
    req, plot = prepare_inputs(max_area/(SQFT_PER_PERCH*MAX_COVERAGE_RATIO), terrain_type,
                               {'bedrooms': bedrooms, 'floors': floors, 'design_seed': 0})
    result = select_best(req, plot)
    if template_id:
        result.template_id = template_id
    return result
