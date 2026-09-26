"""Deterministic, fail-closed quality selection for the generative path only."""
import hashlib
import json
from collections import Counter
from time import perf_counter

from app.design.exceptions import GenerationFailure
from app.design.generation.diversity import geometry_fingerprint, stable_id
from app.design.geometry.circulation import (
    MAX_BANK_ROOMS, MAX_FLOOR_OPTIONS, MAX_FLOOR_PARTITIONS, MAX_SLICE_NODES, MAX_RESERVATION_NODES,
    circulation_failures, requires_circulation, reserved_layouts,
)
from app.design.geometry.finishing import finish_generative_layout
from app.design.program.room_rules import rule_for
from app.design.program.spatial_program import SpatialProgram
from app.design.quality.architectural_quality import validate_architectural_quality, _topology_geometry
from app.validation.geometry_validator import validate_geometry

MAX_COMPLETE_LAYOUT_CANDIDATES = 4


def _validate_program(program, plot):
    from app.design.geometry.geometry_generator import _normalize_room_type
    try:
        SpatialProgram.model_validate(program.model_dump())
        ids = [r.id for r in program.rooms]
        if len(ids) != len(set(ids)):
            raise ValueError('DUPLICATE_ROOM_ID')
        if program.floor_count > 2:
            raise ValueError('ONLY_UP_TO_2_FLOORS_SUPPORTED_IN_G2D')
        if {r.floor for r in program.rooms} != set(range(1, program.floor_count+1)):
            raise ValueError('NON_CONTIGUOUS_OR_MISSING_FLOORS')
        if program.entrance.connect_to not in ids:
            raise ValueError('UNKNOWN_ENTRANCE_ROOM')
        for a in program.adjacencies:
            if a.room_a not in ids or a.room_b not in ids or a.room_a == a.room_b:
                raise ValueError('INVALID_ADJACENCY_REFERENCE')
        for r in program.rooms:
            rule = rule_for(_normalize_room_type(r.type))
            if min(plot.buildable_width, plot.buildable_length) < min(rule.min_width, rule.min_length):
                raise ValueError('ROOM_MIN_DIMENSIONS_EXCEED_PLOT')
            if r.min_area_sqft > r.target_area_sqft:
                raise ValueError('ROOM_MIN_AREA_EXCEEDS_TARGET')
    except ValueError as exc:
        raise GenerationFailure(str(exc), [{'stage': 'SpatialProgram', 'reason': str(exc)}]) from exc


def _infer_topology(design):
    # This describes the generated footprint; it does not select a catalogue plan.
    families = ['DUPLEX_STACKED'] if design.floor_count > 1 else [
        'COMPACT_RECTANGLE', 'LINEAR', 'L_SHAPE', 'T_SHAPE', 'CENTRAL_CORE', 'SPLIT_ZONE']
    for family in families:
        design.template_family = family
        if _topology_geometry(design)[0]:
            return
    design.template_family = None  # Quality rejects unclassified geometry.


def topology_fingerprint(design):
    """Same-program topology identity for future G4; coordinates are excluded."""
    data = {
        'rooms': sorted((r.room_id, r.room_type, r.floor) for r in design.rooms),
        'connections': sorted((tuple(sorted((c.from_room, c.to_room))), c.kind) for c in design.connections),
        'entrances': sorted(e.room_id for e in design.entrances),
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def evaluate_candidate(design, program, plot):
    """Finish → full geometry → circulation → quality; never rank invalid rooms."""
    t0 = perf_counter()
    finishing_program = program.model_copy(deep=True)
    finishing_program.entrance.preferred_side = plot.effective_entrance_side.upper()
    design, finishing = finish_generative_layout(design, finishing_program, privacy_safe=True)
    finish_ms = (perf_counter()-t0)*1000
    t0 = perf_counter()
    geometry = validate_geometry(design.rooms, sum('bedroom' in r.type.lower() for r in program.rooms),
                                 program.floor_count, plot.land_size_perches, plot=plot, design=design)
    actual = {r.room_id: r for r in design.rooms}
    from app.design.geometry.geometry_generator import _normalize_room_type
    for intent in program.rooms:
        room = actual.get(intent.id)
        if room is None or room.floor != intent.floor or room.room_type != _normalize_room_type(intent.type):
            geometry.fail('spatial_program', f'Requested room {intent.id} was changed or omitted.')
        elif room.width*room.length < intent.min_area_sqft-.01:
            geometry.fail('minimum_area', f'{intent.id} is below its requested minimum area.')
    expected = Counter((_normalize_room_type(r.type), r.floor) for r in program.rooms)
    provided = Counter((r.room_type, r.floor) for r in design.rooms)
    for key, count in expected.items():
        if key[0] not in {'hallway', 'foyer', 'entrance', 'staircase'} and provided[key] != count:
            geometry.fail('spatial_program', f'Requested count for {key} changed.')
    privacy = circulation_failures(design)
    quality = None
    if geometry.passed:
        _infer_topology(design)
        quality = validate_architectural_quality(design, plot=plot)
    extras = []
    if finishing['high_adjacencies_unsatisfied']:
        extras.append('HIGH_ADJACENCY_UNSATISFIED')
    if finishing['rooms_with_required_windows'] != finishing['window_requirements_satisfied']:
        extras.append('NO_EXTERIOR_WINDOW')
    status = ('GEOMETRICALLY_INVALID' if not geometry.passed else
              'ARCHITECTURALLY_POOR' if privacy or extras or not quality.passed else 'VALID_HIGH_QUALITY')
    design.candidate_status = status
    design.design_score = quality.score if quality else None
    design.geometry_fingerprint = geometry_fingerprint(design)
    design.design_id = stable_id(design.geometry_fingerprint)
    evaluation = {
        'status': status, 'geometry': geometry.to_dict(), 'circulation_failures': privacy,
        'quality': quality.to_dict() if quality else None, 'finishing_failures': extras,
        'fingerprint': design.geometry_fingerprint, 'topology_fingerprint': topology_fingerprint(design),
    }
    return design, finishing, evaluation, geometry, quality, finish_ms, (perf_counter()-t0)*1000


def select_candidate(candidates):
    passing = [(i, design, meta) for i, design, meta in candidates
               if design.candidate_status == 'VALID_HIGH_QUALITY']
    return max(passing, key=lambda item: (item[1].design_score, -item[0])) if passing else None


def generate_quality_geometry(program, plot):
    from app.design.geometry.geometry_generator import LayoutSolver, MAX_PLACEMENT_EVALUATIONS
    started = perf_counter()
    _validate_program(program, plot)
    summary = dict(complete_candidates_evaluated=0, geometry_rejections=0,
                   circulation_rejections=0, quality_rejections=0, repair_attempts=0,
                   repair_strategies=[], best_quality_score=None, selected_candidate_index=None,
                   quality_status=None, total_geometry_ms=0., total_finishing_ms=0., total_quality_ms=0.,
                   candidate_evaluations_log=[], repairs=[],
                   search_limits={'complete_layouts': MAX_COMPLETE_LAYOUT_CANDIDATES,
                                  'placement_evaluations_per_solver': MAX_PLACEMENT_EVALUATIONS,
                                  'floor_partitions_per_width': MAX_FLOOR_PARTITIONS,
                                  'retained_options_per_floor': MAX_FLOOR_OPTIONS,
                                  'slice_nodes_per_bank': MAX_SLICE_NODES,
                                  'rooms_per_floor_reservation': MAX_BANK_ROOMS,
                                  'reservation_total_nodes': MAX_RESERVATION_NODES})
    candidates = []
    original_failure = []
    reserve = False

    def inspect(design, meta, strategy):
        nonlocal reserve, original_failure
        index = summary['complete_candidates_evaluated']
        design, finishing, ev, geometry, quality, fm, qm = evaluate_candidate(design, program, plot)
        summary['complete_candidates_evaluated'] += 1
        summary['total_finishing_ms'] += fm
        summary['total_quality_ms'] += qm
        summary['geometry_rejections'] += not geometry.passed
        summary['circulation_rejections'] += bool(ev['circulation_failures'])
        summary['quality_rejections'] += bool(quality and (not quality.passed or ev['finishing_failures']))
        ev.update(candidate_index=index, strategy=strategy)
        summary['candidate_evaluations_log'].append(ev)
        meta.update(finishing)
        candidates.append((index, design, meta))
        if strategy == 'INITIAL_PLACEMENT':
            original_failure = geometry.failed_rules + [f['code'] for f in ev['circulation_failures']] + (
                quality.failures if quality else []) + ev['finishing_failures']
            reserve = requires_circulation(design, geometry, quality)
        if strategy != 'INITIAL_PLACEMENT':
            summary['repairs'].append(dict(original_failure=sorted(set(original_failure)), repair_strategy=strategy,
                                           repair_attempt=summary['repair_attempts'], result=ev['status']))

    t0 = perf_counter()
    try:
        initial, meta = LayoutSolver(program, plot).generate()
    except GenerationFailure as exc:
        summary['total_geometry_ms'] += (perf_counter()-t0)*1000
        original_failure = [str(exc)]
        reserve = True
        summary['candidate_evaluations_log'].append({'stage': 'placement', 'reason': str(exc)})
    else:
        summary['total_geometry_ms'] += (perf_counter()-t0)*1000
        summary['initial_placement_metadata'] = dict(meta)
        inspect(initial, meta, 'INITIAL_PLACEMENT')
    # A direct-access candidate still gets one bounded alternative for ranking.
    if not reserve:
        t0 = perf_counter()
        try:
            alternative, meta = LayoutSolver(program, plot, candidate_rank=1).generate()
        except GenerationFailure as exc:
            summary['candidate_evaluations_log'].append({'stage': 'alternative_placement', 'reason': str(exc)})
            summary['total_geometry_ms'] += (perf_counter()-t0)*1000
        else:
            summary['total_geometry_ms'] += (perf_counter()-t0)*1000
            summary['repair_attempts'] += 1
            summary['repair_strategies'].append('ALTERNATE_PLACEMENT_BRANCH')
            inspect(alternative, meta, 'ALTERNATE_PLACEMENT_BRANCH')
    # Repair is conditional: a passing direct-access layout gains no corridor.
    if reserve:
        strategy = 'RESERVE_CIRCULATION_BEFORE_PLACEMENT'
        summary['repair_strategies'].append(strategy)
        search_stats = {'slice_nodes': 0}
        summary['reservation_search'] = search_stats
        iterator = iter(reserved_layouts(program, plot, search_stats))
        reservation_count = 0
        while summary['complete_candidates_evaluated'] < MAX_COMPLETE_LAYOUT_CANDIDATES:
            t0 = perf_counter()
            try:
                design, meta = next(iterator)
            except StopIteration:
                if search_stats['slice_nodes'] >= MAX_RESERVATION_NODES:
                    summary['candidate_evaluations_log'].append({'stage': 'reservation', 'reason': 'RESERVATION_NODE_LIMIT_EXCEEDED'})
                elif not reservation_count:
                    summary['candidate_evaluations_log'].append({'stage': 'reservation', 'reason': 'NO_FEASIBLE_CIRCULATION_RESERVATION'})
                summary['total_geometry_ms'] += (perf_counter()-t0)*1000
                break
            except GenerationFailure as exc:
                summary['total_geometry_ms'] += (perf_counter()-t0)*1000
                summary['candidate_evaluations_log'].append({'stage': 'reservation', 'reason': str(exc)})
                break
            summary['total_geometry_ms'] += (perf_counter()-t0)*1000
            summary['repair_attempts'] += 1
            reservation_count += 1
            inspect(design, meta, strategy)
    selected = select_candidate(candidates)
    summary['generation_ms'] = round((perf_counter()-started)*1000, 3)
    for key in ('total_geometry_ms', 'total_finishing_ms', 'total_quality_ms'):
        summary[key] = round(summary[key], 3)
    summary['best_quality_score'] = max((d.design_score for _,d,_ in candidates if d.design_score is not None), default=None)
    if selected is None:
        summary['quality_status'] = 'NO_VALID_HIGH_QUALITY_CANDIDATE'
        raise GenerationFailure('NO_VALID_HIGH_QUALITY_CANDIDATE: ' + ', '.join(sorted(set(original_failure))), [summary])
    index, design, metadata = selected
    summary.update(best_quality_score=design.design_score, selected_candidate_index=index,
                   quality_status=design.candidate_status)
    summary['generated_circulation'] = metadata.get('generated_circulation', [])
    summary['topology_fingerprint'] = topology_fingerprint(design)
    metadata.update(summary)
    design.candidate_summary = summary
    design.plot_constraints = plot.model_dump()
    return design, metadata
