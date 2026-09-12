from typing import Optional, Union
"""Generative AI layout planner with procedural fallback."""
import json
import uuid
from app.config import GOOGLE_API_KEY
from app.design.candidate_generator import GenerationFailure, select_best
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints
from app.design.spatial_program import build_program
from app.design.topology_registry import eligible_topologies, topology_dict
from app.schemas.design_result import DesignResult
from app.tools.geometry_validator import validate_geometry
from app.tools.land_utils import SQFT_PER_PERCH, MAX_COVERAGE_RATIO

SYSTEM_PROMPT = """You are the Design Agent of an AI-Assisted Home Design & Cost Planner.
Your responsibility is to generate a VALID conceptual 2D house floor plan based on the plot constraints, requirements, and spatial program provided.

This is a university-level planning and estimation system. The generated design is NOT construction-ready architectural documentation. It is a conceptual floor plan used for visualization, cost estimation, validation, and design revision.

IMPORTANT:
The application uses deterministic geometry validation after your response. Therefore, correctness and constraint satisfaction are more important than creativity.
Rooms on the same floor must never overlap.
Keep every room within the maximum building dimensions provided in the plot constraints.
Generate coordinates (x, y) starting from (0,0) at the bottom-left corner.
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
        req, plot = prepare_inputs(land_size_perches, terrain_type, preferences, plot_constraints, design_seed)
    except (ValueError, TypeError) as exc:
        raise GenerationFailure(f'Invalid design requirements: {exc}') from exc
        
    mode = 'procedural_no_api_key'
    result = None

    if GOOGLE_API_KEY and plot.terrain_type != 'unknown':
        prompt = json.dumps({'plot': plot.model_dump(), 'requirements': req.model_dump(),
                             'eligible_families': [topology_dict(t) for t in eligible_topologies(req, plot)],
                             'spatial_program': build_program(req).model_dump(),
                             'previous_design': previous_design,
                             'revision_feedback': revision_reason})
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=GOOGLE_API_KEY, http_options=types.HttpOptions(timeout=25000))
            try:
                for attempt in range(3):
                    try:
                        data = _parse_design_result(_call_gemini_design(client, prompt))
                        if not data:
                            raise ValueError("Invalid JSON response")
                        
                        # Populate missing required fields if LLM missed them
                        if 'design_id' not in data:
                            data['design_id'] = str(uuid.uuid4())
                        if 'template_id' not in data:
                            data['template_id'] = "CUSTOM_AI"
                            
                        candidate = DesignResult.model_validate(data)
                        check = validate_geometry(candidate.rooms, req.bedrooms, req.floors, land_size_perches, plot=plot, design=candidate)
                        
                        if check.passed:
                            result = candidate
                            mode = 'ai_generative'
                            break
                        else:
                            prompt += f'\nPrevious generation failed validation: {check.failures}. Please fix overlaps and boundary issues.'
                    except (ValueError, TypeError) as exc:
                        prompt += f'\nPrevious generation failed schema validation: {exc}. Please return valid JSON matching the schema.'
            finally:
                client.close()
        except Exception as e:
            print(f"Generative API failed: {e}")
            mode = 'procedural_api_unavailable'

    if result is None:
        # Fallback to procedural generator
        if req.design_seed is None:
            # Scramble seed if missing to introduce SOME variety in fallback
            import random
            req.design_seed = random.randint(1, 1000000)
        
        result = select_best(req, plot)
        check = validate_geometry(result.rooms, req.bedrooms, req.floors, land_size_perches, plot=plot, design=result)
        if not check.passed:
            raise GenerationFailure('Selected candidate failed final validation.', [{'failures': check.failures}])
        mode = 'procedural_fallback'

    known_extras = set(PlotConstraints.model_fields) | {'plot_constraints', 'photo_url'}
    unhandled = sorted(set(req.model_extra or {}) - known_extras)
    result.candidate_summary.update(generation_mode=mode, unhandled_preferences=unhandled)
    if unhandled:
        result.candidate_summary.setdefault('notes', []).append('Unrecognized preferences were not applied: '+', '.join(unhandled))
    if revision_reason:
        result.candidate_summary['revision_feedback'] = revision_reason
        
    return result


def _call_gemini_design(client, user_prompt: str) -> str:
    from google.genai import types
    response = client.models.generate_content(
        model='gemini-3.6-flash', contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.7,
                                          max_output_tokens=3000, response_mime_type='application/json',
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
