from app.design.diversity import stable_seed
from app.design.geometry_engine import generate_geometry
from app.design.models import Requirements, ConceptAdvice
from app.design.plot_constraints import PlotConstraints
from app.design.scoring import family_affinity, score_layout
from app.design.spatial_program import build_program
from app.design.topology_registry import eligible_topologies
from app.schemas.design_result import DesignResult
from app.tools.geometry_validator import validate_geometry


class GenerationFailure(ValueError):
    """No valid candidate exists within this procedural search's supported limits."""

    def __init__(self, message: str, failures: list[dict] | None = None):
        super().__init__(message)
        self.failures = failures or []


def generate_candidates(req: Requirements, plot: PlotConstraints,
                        advice: ConceptAdvice | None = None) -> tuple[list[DesignResult], list[dict]]:
    if plot.terrain_type == 'unknown':
        raise GenerationFailure('Terrain is unknown; provide a manual terrain classification.')
    program = build_program(req)
    seed = req.design_seed if req.design_seed is not None else stable_seed({'requirements': req.model_dump(), 'plot': plot.model_dump()})
    families = eligible_topologies(req, plot)
    # Advice can alter search order within eligible families, never constraints or score.
    advised = advice.preferred_families if advice else []
    families.sort(key=lambda t: (-family_affinity(t.name, req, plot),
                                advised.index(t.name) if t.name in advised else 99,
                                stable_seed({'seed': seed, 'family': t.name})))
    valid, rejected = [], []
    for topology in families:
        for attempt in range(3):
            try:
                candidate = generate_geometry(program, req, plot, topology.name, seed, attempt)
                check = validate_geometry(candidate.rooms, req.bedrooms, req.floors, plot.land_size_perches,
                                          plot=plot, design=candidate)
                if not check.passed:
                    rejected.append({'family': topology.name, 'attempt': attempt, 'failures': check.failures})
                    continue
                score, breakdown = score_layout(candidate, req, plot)
                candidate.design_score = score
                candidate.candidate_summary = {'score_breakdown': breakdown}
                valid.append(candidate)
                break
            except ValueError as exc:
                rejected.append({'family': topology.name, 'attempt': attempt, 'failures': [str(exc)]})
        if len(valid) == 5:
            break
    # On constrained plots, produce alternate size concepts from eligible families.
    if 0 < len(valid) < 3:
        originals = list(valid)
        for original in originals:
            for index in (3, 4, 5):
                try:
                    candidate = generate_geometry(program, req, plot, original.template_family, seed, index)
                    check = validate_geometry(candidate.rooms, req.bedrooms, req.floors, plot.land_size_perches, plot=plot, design=candidate)
                    if check.passed:
                        candidate.design_score, parts = score_layout(candidate, req, plot)
                        candidate.candidate_summary = {'score_breakdown': parts}
                        valid.append(candidate)
                    else:
                        rejected.append({'family': original.template_family, 'attempt': index, 'failures': check.failures})
                except ValueError as exc:
                    rejected.append({'family': original.template_family, 'attempt': index, 'failures': [str(exc)]})
                if len(valid) >= 3:
                    break
            if len(valid) >= 3:
                break
    return valid, rejected


def select_best(req: Requirements, plot: PlotConstraints, advice: ConceptAdvice | None = None) -> DesignResult:
    candidates, rejected = generate_candidates(req, plot, advice)
    if not candidates:
        raise GenerationFailure('No valid conceptual layout fits the plot, room program and area limits.', rejected)
    best = max(candidates, key=lambda c: (c.design_score, c.design_id))
    best.candidate_summary.update({
        'valid_count': len(candidates), 'rejected_count': len(rejected),
        'candidates': [{'family': c.template_family, 'design_id': c.design_id, 'score': c.design_score,
                        'score_breakdown': c.candidate_summary['score_breakdown']} for c in candidates],
        'rejected': rejected,
        'notes': (best.program or {}).get('notes', []) +
                 (['Plot dimensions are estimated from land area using a conceptual 1:1.3 aspect ratio (or one supplied dimension).'] if plot.dimensions_estimated else []),
    })
    return best
