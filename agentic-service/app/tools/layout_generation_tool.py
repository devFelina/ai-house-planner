"""Constrained AI concept advice followed by deterministic procedural planning."""
import json
from app.config import GOOGLE_API_KEY
from app.design.candidate_generator import GenerationFailure, select_best
from app.design.geometry_engine import TERRAIN_FOUNDATION_MAP
from app.design.models import ConceptAdvice, Requirements
from app.design.plot_constraints import PlotConstraints
from app.design.spatial_program import build_program
from app.design.topology_registry import eligible_topologies, topology_dict
from app.schemas.design_result import DesignResult
from app.tools.geometry_validator import validate_geometry
from app.tools.land_utils import SQFT_PER_PERCH, MAX_COVERAGE_RATIO

SYSTEM_PROMPT = """You advise on concepts for a university conceptual home planner.
Return only JSON matching the provided schema. Recommend eligible topology families
using plot shape, room program, adjacency, public/private zoning, entrance, terrain,
preferences, notable land features and revision feedback. No coordinates, dimensions,
structural engineering, geometry validity claims or construction/code approval.
Python generates geometry and deterministic validation is the final authority.
Preferred families only influence the bounded search; final quality scoring is deterministic.
"""


def prepare_inputs(land_size_perches: float, terrain_type: str, preferences: dict,
                   plot_constraints: dict | PlotConstraints | None = None,
                   design_seed: int | None = None) -> tuple[Requirements, PlotConstraints]:
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
                    previous_design: dict | None = None, revision_reason: str | None = None,
                    *, plot_constraints: dict | PlotConstraints | None = None,
                    design_seed: int | None = None) -> DesignResult:
    try:
        req, plot = prepare_inputs(land_size_perches, terrain_type, preferences, plot_constraints, design_seed)
    except (ValueError, TypeError) as exc:
        raise GenerationFailure(f'Invalid design requirements: {exc}') from exc
    advice = None
    mode = 'procedural_no_api_key'
    # A supplied seed is a reproducibility contract: remote nondeterminism cannot
    # change its candidate set. Unseeded requests may use AI concept advice.
    if req.design_seed is not None:
        mode = 'procedural_seeded'
    elif GOOGLE_API_KEY and plot.terrain_type != 'unknown':
        prompt = json.dumps({'plot': plot.model_dump(), 'requirements': req.model_dump(),
                             'eligible_families': [topology_dict(t) for t in eligible_topologies(req, plot)],
                             'spatial_program': build_program(req).model_dump(),
                             'previous_concept': (previous_design or {}).get('template_family'),
                             'revision_feedback': revision_reason,
                             'response_schema': ConceptAdvice.model_json_schema()})
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GOOGLE_API_KEY, http_options=types.HttpOptions(timeout=15000))
            try:
                for _ in range(2):
                    data = _parse_design_result(_call_gemini_design(client, prompt))
                    try:
                        advice = ConceptAdvice.model_validate(data)
                        eligible = {t.name for t in eligible_topologies(req, plot)}
                        if not set(advice.preferred_families) <= eligible:
                            raise ValueError('Ineligible family')
                        mode = 'ai_concept_advice'
                        break
                    except (ValueError, TypeError):
                        advice = None
                        prompt += '\nPrevious advice failed the schema/eligibility check. Return only eligible concept JSON.'
                if advice is None:
                    mode = 'procedural_invalid_ai_advice'
            finally:
                client.close()
        except Exception:
            mode = 'procedural_api_unavailable'
    result = select_best(req, plot, advice)
    # Validate again at the tool boundary, including metadata, before returning.
    check = validate_geometry(result.rooms, req.bedrooms, req.floors, land_size_perches, plot=plot, design=result)
    if not check.passed:
        raise GenerationFailure('Selected candidate failed final validation.', [{'failures': check.failures}])
    known_extras = set(PlotConstraints.model_fields) | {'plot_constraints', 'photo_url'}
    unhandled = sorted(set(req.model_extra or {}) - known_extras)
    result.candidate_summary.update(generation_mode=mode, unhandled_preferences=unhandled)
    if unhandled:
        result.candidate_summary['notes'].append('Unrecognized preferences were not applied: '+', '.join(unhandled))
    if advice:
        result.candidate_summary['concept_advice'] = advice.model_dump()
    if revision_reason:
        result.candidate_summary['revision_feedback'] = revision_reason
        if not advice:
            result.candidate_summary['notes'].append('Free-text revision feedback requires AI advice; explicit preference changes are applied deterministically.')
    return result


def _call_gemini_design(client, user_prompt: str) -> str:
    from google.genai import types
    response = client.models.generate_content(
        model='gemini-3.6-flash', contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.4,
                                          max_output_tokens=1500, response_mime_type='application/json',
                                          response_json_schema=ConceptAdvice.model_json_schema()))
    return (response.text or '').strip()


def _parse_design_result(text: str) -> dict | None:
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
                 max_area: float, template_id: str | None = None, template: dict | None = None) -> DesignResult:
    """Compatibility wrapper: the offline path uses the same validated candidate engine."""
    req, plot = prepare_inputs(max_area/(SQFT_PER_PERCH*MAX_COVERAGE_RATIO), terrain_type,
                               {'bedrooms': bedrooms, 'floors': floors, 'design_seed': 0})
    result = select_best(req, plot)
    if template_id:
        result.template_id = template_id
    return result
