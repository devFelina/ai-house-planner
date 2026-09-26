"""G2D full-pipeline regressions; no model/provider calls in these tests."""
import json
from pathlib import Path

import pytest

from app.design.exceptions import GenerationFailure
from app.design.generation.spatial_planner import _validate_spatial_program
from app.design.geometry.adjacency import graph_for, reachable
from app.design.geometry.circulation import circulation_failures
from app.design.geometry.geometry_generator import generate_geometry, LayoutSolver
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.geometry.quality_search import MAX_COMPLETE_LAYOUT_CANDIDATES, select_candidate
from app.design.program.models import Requirements
from app.design.program.spatial_program import SpatialProgram, RoomIntent, EntranceIntent, AdjacencyIntent
from app.design.quality.architectural_quality import validate_architectural_quality
from app.schemas.design_result import DesignResult, RoomLayout
from app.validation.geometry_validator import validate_geometry

BASELINE = json.loads((Path(__file__).parent/'fixtures/g2d_4b3b_baseline.json').read_text())


def compact_program(foyer=False):
    specs = [('living', 'living', 200, 150), ('kitchen', 'kitchen', 100, 80),
             ('bed1', 'bedroom', 150, 100), ('bath', 'bathroom', 50, 40)]
    specs += [('foyer', 'foyer', 80, 64)] if foyer else [('bed2', 'bedroom', 150, 120)]
    return SpatialProgram(
        concept='Compact independent private access', floor_count=1,
        rooms=[RoomIntent(id=i, type=t, floor=1,
                          zone='CIRCULATION' if t=='foyer' else 'PRIVATE' if t=='bedroom' else 'PUBLIC',
                          target_area_sqft=a, min_area_sqft=m,
                          preferred_position='FRONT' if t=='living' else 'CENTER',
                          exterior_wall_required=t in {'living', 'bedroom'}, privacy_level='HIGH' if t=='bedroom' else 'LOW')
               for i,t,a,m in specs], adjacencies=[],
        entrance=EntranceIntent(preferred_side='SOUTH', connect_to='living'), reason_codes=[])


def compact_plot(side='south'):
    return PlotConstraints(land_size_perches=10, plot_width_ft=40, plot_length_ft=50,
                           road_side=side, setbacks={'front': 5,'rear': 5,'left': 5,'right': 5})


def assert_certified(design, program, plot):
    beds = sum('bedroom' in r.type.lower() for r in program.rooms)
    assert validate_geometry(design.rooms, beds, program.floor_count, plot.land_size_perches,
                             plot=plot, design=design).passed
    assert not circulation_failures(design)
    assert validate_architectural_quality(design, plot=plot).passed
    assert design.candidate_status == 'VALID_HIGH_QUALITY'
    assert {r.id for r in program.rooms} <= {r.room_id for r in design.rooms}
    for intent in program.rooms:
        room = next(r for r in design.rooms if r.room_id == intent.id)
        assert room.width*room.length >= intent.min_area_sqft-.01


@pytest.fixture(scope='module')
def repaired_four():
    program = SpatialProgram.model_validate(BASELINE['program'])
    plot = PlotConstraints.model_validate(BASELINE['plot'])
    _validate_spatial_program(program, Requirements(bedrooms=4,bathrooms=3,floors=2), plot.maximum_total_floor_area)
    return program, plot, *generate_geometry(program, plot)


def test_original_4b3b_private_bridge_is_reproduced():
    d = DesignResult.model_validate(BASELINE['design'])
    plot = PlotConstraints.model_validate(BASELINE['plot'])
    g = validate_geometry(d.rooms,4,2,plot.land_size_perches,plot=plot,design=d)
    assert g.failed_rules.count('privacy_access') == 4
    assert any('Bedroom requires passage through an unrelated private room' in f for f in g.failures)
    assert validate_architectural_quality(d,plot=plot).status == 'ARCHITECTURALLY_POOR'
    assert {k: sorted(v) for k,v in graph_for(d.rooms,d.connections).items()} == BASELINE['door_graph']


def test_4b3b_full_regression_and_candidate_selection(repaired_four):
    program,plot,design,meta = repaired_four
    assert_certified(design,program,plot)
    assert 2 <= meta['complete_candidates_evaluated'] <= MAX_COMPLETE_LAYOUT_CANDIDATES
    assert meta['repair_attempts'] == meta['complete_candidates_evaluated'] - 1
    evaluations = meta['candidate_evaluations_log']
    assert any(e['geometry']['passed'] and e['status']=='ARCHITECTURALLY_POOR' for e in evaluations)
    scores = [e['quality']['score'] for e in evaluations if e['status']=='VALID_HIGH_QUALITY']
    assert design.design_score == max(scores)
    assert evaluations[meta['selected_candidate_index']]['status'] == 'VALID_HIGH_QUALITY'
    assert all(r['original_failure'] and r['repair_strategy'] and r['result'] for r in meta['repairs'])
    assert all(r['generated_reason']=='CIRCULATION_REQUIRED' and r['owner']=='PYTHON'
               for r in meta['generated_circulation'])


def test_stair_landing_and_independent_upper_access(repaired_four):
    _,_,design,_ = repaired_four
    graph = graph_for(design.rooms,design.connections)
    stair = next(r for r in design.rooms if r.floor==2 and r.room_type=='staircase')
    hall = next(r for r in design.rooms if r.floor==2 and r.room_type=='hallway')
    assert hall.room_id in graph[stair.room_id]
    private = {r.room_id for r in design.rooms if r.room_type in {'bedroom','bathroom'}}
    for room in [r for r in design.rooms if r.floor==2 and r.room_type in {'bedroom','bathroom'}]:
        assert room.room_id in reachable(graph,hall.room_id,(private-{room.room_id})|{stair.room_id})


def test_single_floor_repairs_private_chain_without_model_calls(monkeypatch):
    from app.design.generation import spatial_planner
    def forbidden():
        pytest.fail('Geometry repair must never request a provider')
    monkeypatch.setattr(spatial_planner,'get_available_design_provider',forbidden)
    program,plot = compact_program(),compact_plot()
    before = program.model_dump()
    from app.design.geometry.finishing import finish_generative_layout
    naive = DesignResult(floor_count=1, foundation_type='slab', total_built_up_area_sqft=650,
                         ground_footprint_sqft=650, rooms=[
        RoomLayout(room_id=i,room_type=t,floor=1,x=x,y=y,width=w,length=h)
        for i,t,x,y,w,h in [('living','living_room',0,0,20,10),('kitchen','kitchen',20,0,10,10),
                           ('bed1','bedroom',0,10,10,15),('bed2','bedroom',0,25,10,15),
                           ('bath','bathroom',10,25,5,10)]])
    naive,_ = finish_generative_layout(naive,program)
    graph=graph_for(naive.rooms,naive.connections)
    assert 'bed1' in graph['bed2'] and 'living' in graph['bed1']
    assert 'bed2' not in reachable(graph,'living',{'bed1','bath'})
    assert 'privacy_access' in validate_geometry(naive.rooms,2,1,plot.land_size_perches,plot=plot,design=naive).failed_rules
    design,meta = generate_geometry(program,plot)
    assert_certified(design,program,plot)
    assert program.model_dump()==before
    assert meta['circulation_rejections'] >= 1
    assert meta['generated_circulation']
    assert not any(r.room_type=='staircase' for r in design.rooms)


def test_existing_foyer_needs_no_additional_hallway():
    program,plot = compact_program(foyer=True),compact_plot()
    design,meta = generate_geometry(program,plot)
    assert_certified(design,program,plot)
    assert not any(r.room_type=='hallway' for r in design.rooms)
    assert not meta.get('generated_circulation')
    assert len(design.rooms)==len(program.rooms)


def test_quality_selector_never_accepts_poor_or_invalid(repaired_four):
    _,_,good,_ = repaired_four
    poor = good.model_copy(deep=True)
    poor.candidate_status='ARCHITECTURALLY_POOR'
    poor.design_score=99  # Status takes precedence over numerical score.
    invalid=good.model_copy(deep=True)
    invalid.candidate_status='GEOMETRICALLY_INVALID'
    invalid.design_score=100
    assert select_candidate([(0,poor,{}),(1,good,{}),(2,invalid,{})])[0]==1
    assert select_candidate([(0,poor,{}),(1,invalid,{})]) is None


def test_all_bounded_candidates_fail_closed():
    program,plot = compact_program(),compact_plot()
    # Required living-to-bedroom direct access conflicts with this path's
    # bedroom/public privacy gate; do not silently discard the requirement.
    program.adjacencies=[AdjacencyIntent(room_a='living',room_b='bed1',relationship='ADJACENT',priority='HIGH')]
    with pytest.raises(GenerationFailure) as caught:
        generate_geometry(program,plot)
    meta=caught.value.failures[0]
    assert meta['quality_status']=='NO_VALID_HIGH_QUALITY_CANDIDATE'
    assert meta['selected_candidate_index'] is None
    assert 1 <= meta['complete_candidates_evaluated'] <= MAX_COMPLETE_LAYOUT_CANDIDATES
    assert meta['candidate_evaluations_log']


def test_minimums_and_features_cannot_be_removed():
    program,plot=compact_program(),compact_plot()
    program.rooms.append(RoomIntent(id='office',type='home_office',floor=1,zone='PRIVATE',
        target_area_sqft=1500,min_area_sqft=1500,preferred_position='REAR',exterior_wall_required=True,privacy_level='HIGH'))
    with pytest.raises(GenerationFailure):
        generate_geometry(program,plot)
    assert len(program.rooms)==6


@pytest.mark.parametrize('mutation',['duplicate_id','unknown_adjacency','unknown_entrance','bad_minimum'])
def test_program_contract_is_checked_before_search(mutation):
    p=compact_program()
    if mutation=='duplicate_id': p.rooms[1].id=p.rooms[0].id
    elif mutation=='unknown_adjacency': p.adjacencies=[AdjacencyIntent(room_a='missing',room_b='living',relationship='ADJACENT',priority='HIGH')]
    elif mutation=='unknown_entrance': p.entrance.connect_to='missing'
    else: p.rooms[0].min_area_sqft=500
    with pytest.raises(GenerationFailure) as caught:
        generate_geometry(p,compact_plot())
    assert caught.value.failures[0]['stage']=='SpatialProgram'


def test_geometry_and_fingerprint_are_repeatable(repaired_four):
    program,plot,first,meta=repaired_four
    second,again=generate_geometry(program,plot)
    assert first.model_dump(exclude={'candidate_summary'})==second.model_dump(exclude={'candidate_summary'})
    assert meta['selected_candidate_index']==again['selected_candidate_index']
    assert [e['fingerprint'] for e in meta['candidate_evaluations_log']]==[e['fingerprint'] for e in again['candidate_evaluations_log']]


@pytest.mark.parametrize('side',['north','east','west'])
def test_finished_orientation_and_openings(side):
    p,plot=compact_program(),compact_plot(side)
    design,_=generate_geometry(p,plot)
    assert_certified(design,p,plot)
    assert design.entrances[0].wall==side


def test_saved_single_gpt_response_passes_without_another_request():
    data=json.loads((Path(__file__).parent/'fixtures/g2d_live_program.json').read_text())
    program=SpatialProgram.model_validate(data['program'])
    plot=PlotConstraints.model_validate(data['plot'])
    design,meta=generate_geometry(program,plot)
    assert_certified(design,program,plot)
    assert not meta['high_adjacencies_unsatisfied']
    assert len(meta['high_adjacencies_satisfied'])==3
    assert meta['complete_candidates_evaluated'] <= MAX_COMPLETE_LAYOUT_CANDIDATES


def test_topology_fingerprint_ignores_coordinates(repaired_four):
    from app.design.geometry.quality_search import topology_fingerprint
    from app.design.generation.diversity import geometry_fingerprint
    _,_,original,_=repaired_four
    moved=original.model_copy(deep=True)
    for room in moved.rooms:
        room.x += 1
    assert topology_fingerprint(moved)==topology_fingerprint(original)
    assert geometry_fingerprint(moved)!=geometry_fingerprint(original)


def test_partial_search_has_a_total_deterministic_work_budget(monkeypatch):
    from app.design.geometry import circulation
    monkeypatch.setattr(circulation, 'MAX_RESERVATION_NODES', 10)
    p=SpatialProgram.model_validate(BASELINE['program'])
    plot=PlotConstraints.model_validate(BASELINE['plot'])
    with pytest.raises(GenerationFailure) as caught:
        generate_geometry(p,plot)
    assert caught.value.failures[0]['reservation_search']['slice_nodes']==10
    assert caught.value.failures[0]['complete_candidates_evaluated']==1
