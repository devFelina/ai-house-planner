import json
from contextlib import suppress
from unittest.mock import MagicMock, patch

import pytest

from app.agents.design_agent import _safe_failure_reason, design_node
from app.design.quality.architectural_quality import validate_architectural_quality
from app.design.catalogue.base_plan_library import BasePlanRecord
from app.design.exceptions import GenerationFailure
from app.design.program.models import Connection, Entrance
from app.schemas.design_result import DesignResult, RoomLayout
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.design.generation.generation_service import generate_layout
from app.workflows.house_planning_graph import app_graph


def state():
    return WorkflowState(workflow_id='00000000-0000-0000-0000-000000000123',
        input_data=CoordinatorInput(submission_id='00000000-0000-0000-0000-000000000123',
                                    land_size_perches=20, manual_terrain_type='flat',
                                    preferences={'bedrooms':3,'floors':1,'design_seed':1}),
        terrain_result={'terrain_type':'flat'})




def test_complete_optional_context_reaches_design_prompt():
    preferences = {
        'bedrooms': 3, 'bathrooms': 2, 'floors': 1,
        'architecturalStyle': 'Modern Minimalist', 'open_plan': True,
        'master_ensuite': True, 'separate_dining': True, 'home_office': True,
        'veranda': True, 'utility_room': True, 'parking_required': True,
        'accessibility': True, 'space_priority': 'balanced',
        'circulation_preference': 'space_efficient',
    }
    plot = {
        'plot_width_ft': 45, 'plot_length_ft': 90, 'road_side': 'south',
        'north_direction': 'east', 'entrance_side': 'west',
        'setbacks': {'front': 10, 'rear': 6, 'left': 5, 'right': 5},
    }
    mock_provider = MagicMock()
    mock_provider.generate_json.return_value = {
        "selected_plan_code": "INVALID",
        "alternative_plan_codes": [],
        "design_intent": {
            "public_zone_orientation": "south",
            "private_zone_orientation": "north",
            "service_zone_orientation": "west",
            "privacy_priority": "high",
            "circulation_preference": "short_central_hall",
        },
        "adaptations": {
            "mirror_horizontal": False,
            "mirror_vertical": False,
            "rotation_degrees": 0,
            "living_scale": 1.0,
            "bedroom_scale": 1.0,
            "entrance_side": "south",
            "preserve_stair_core": True,
            "preserve_wet_core": True,
        },
        "reason_codes": ["plot_fit"]
    }
    dummy_plan = BasePlanRecord(
        plan_code='HP-TEST', name='Test Plan', bedrooms=3, bathrooms=2, floors=1,
        topology_family='COMPACT_RECTANGLE', minimum_land_perches=5, maximum_land_perches=None,
        minimum_plot_width_ft=None, minimum_plot_length_ft=None, supported_plot_shapes=['COMPACT_RECTANGLE'],
        supported_terrains=['flat'], supported_styles=['Modern Minimalist'], capabilities={}, architectural_metrics={},
        layout_json=DesignResult(floor_count=1, foundation_type='slab').model_dump_json()
    )
    with (
        patch('app.design.generation.generation_service.filter_compatible_base_plans', return_value=[dummy_plan]),
        patch('app.design.generation.generation_service.get_available_design_provider', return_value=mock_provider),
        patch('app.design.generation.plan_adapter.PlanAdapter.adapt') as mock_adapt,
    ):
        mock_adapt.return_value = MagicMock(template_id='HP-TEST', template_family='COMPACT_RECTANGLE', rooms=[])
        with suppress(GenerationFailure, ValueError):
            generate_layout(15, 'flat', preferences, plot_constraints=plot)

    sent = json.loads(mock_provider.generate_json.call_args_list[0].args[1])
    assert 'budget_lkr' not in sent['normalized_input']
    assert sent['normalized_input']['bathrooms'] == 2
    assert sent['normalized_input']['master_ensuite'] is True
    assert sent['normalized_input']['utility_room'] is True
    assert sent['normalized_input']['north_direction'] == 'east'
    assert sent['normalized_input']['entrance_side'] == 'west'
    assert mock_provider.generate_json.call_count == 1


def test_seeded_request_still_calls_remote_advice_once():
    mock_provider = MagicMock()
    mock_provider.generate_json.return_value = {
        "selected_plan_code": "INVALID",
        "alternative_plan_codes": [],
        "design_intent": {
            "public_zone_orientation": "south",
            "private_zone_orientation": "north",
            "service_zone_orientation": "west",
            "privacy_priority": "balanced",
            "circulation_preference": "short_central_hall",
        },
        "adaptations": {
            "mirror_horizontal": False,
            "mirror_vertical": False,
            "rotation_degrees": 0,
            "living_scale": 1.0,
            "bedroom_scale": 1.0,
            "entrance_side": "south",
            "preserve_stair_core": True,
            "preserve_wet_core": True,
        },
        "reason_codes": ["plot_fit"]
    }
    with patch('app.design.generation.generation_service.get_available_design_provider', return_value=mock_provider):
        result = generate_layout(20, 'flat', {'floors':1}, design_seed=8)

    assert result.candidate_summary['generation_mode'] == 'deterministic_fallback'
    assert mock_provider.generate_json.call_count == 1


def test_failed_generation_is_not_submitted_or_approved():
    with patch('app.agents.design_agent.generate_layout', side_effect=GenerationFailure('no valid design')), \
         patch('app.agents.design_agent._submit_design') as submit, \
         patch('app.agents.design_agent._persist_failure'):
        result = app_graph.invoke(state())
    submit.assert_not_called()
    assert result['status'] == 'failed'
    assert result['design_result'] is None
    assert result['approval_status'] == 'not_requested'


def test_node_revalidates_before_persistence():
    invalid = generate_layout(20, 'flat', {'floors':1,'design_seed':1})
    invalid.rooms[0].x = 999
    with patch('app.agents.design_agent.generate_layout', return_value=invalid), \
         patch('app.agents.design_agent._submit_design') as submit, \
         patch('app.agents.design_agent._persist_failure'):
        result = design_node(state())
    submit.assert_not_called()
    assert result.status == 'failed'


def test_unknown_terrain_needs_manual_input():
    with pytest.raises(GenerationFailure, match='Terrain is unknown'):
        generate_layout(20, 'unknown', {'floors':1,'design_seed':1})


def test_safe_failure_reason_exposes_validation_without_traceback():
    failed = state()
    failed.validation_result = {
        'candidate_failures': [{'failures': ['Circulation area is 18.0%.', 'Invalid entrance.']}]
    }
    assert _safe_failure_reason(failed) == 'Circulation area is 18.0%. Invalid entrance.'


def test_architectural_quality_rejects_long_hallway_spine():
    design = DesignResult(
        floor_count=1,
        foundation_type='slab',
        terrain_type='flat',
        rooms=[
            RoomLayout(room_type='living_room', floor=1, x=0, y=0, width=14, length=12),
            RoomLayout(room_type='kitchen', floor=1, x=0, y=12, width=14, length=10),
            RoomLayout(room_type='hallway', floor=1, x=0, y=22, width=4, length=42),
            RoomLayout(room_type='bedroom_1', floor=1, x=4, y=22, width=10, length=12),
            RoomLayout(room_type='bedroom_2', floor=1, x=4, y=34, width=10, length=12),
            RoomLayout(room_type='bedroom_3', floor=1, x=4, y=46, width=10, length=12),
            RoomLayout(room_type='bathroom', floor=1, x=4, y=58, width=6, length=8),
        ],
        connections=[
            Connection(from_room='living-room', to_room='kitchen'),
        ],
        entrances=[Entrance(room_id='living-room', wall='south', offset=4, width=3)],
        template_family='LINEAR',
        template_id='LINEAR',
    )
    # Fix room IDs and explicit connections to mirror a fake corridor spine.
    for index, room in enumerate(design.rooms, start=1):
        room.room_id = f'r{index}'
    design.connections = [
        Connection(from_room='r1', to_room='r2'),
        Connection(from_room='r2', to_room='r3'),
        Connection(from_room='r3', to_room='r4'),
        Connection(from_room='r4', to_room='r5'),
        Connection(from_room='r5', to_room='r6'),
        Connection(from_room='r6', to_room='r7'),
    ]
    design.entrances = [Entrance(room_id='r1', wall='south', offset=4, width=3)]

    req = type('Req', (), {'bedrooms': 3, 'bathrooms': 1, 'floors': 1, 'home_office': False, 'utility_room': False, 'balcony': False, 'veranda': False, 'dining_required': False, 'attached_bathroom': False, 'open_plan': False, 'accessibility': False, 'parking': False, 'privacy_priority': False})()
    plot = type('Plot', (), {'road_side': 'south', 'effective_entrance_side': 'south', 'plot_width_ft': 80, 'plot_length_ft': 80, 'buildable_width': 70, 'buildable_length': 70, 'edge_setbacks': {'west': 5, 'south': 5}})()
    result = validate_architectural_quality(design, req=req, plot=plot)
    assert not result.passed
    assert 'long_hallway' in result.failures or 'excessive_circulation' in result.failures or 'public_zone_separation' in result.failures
