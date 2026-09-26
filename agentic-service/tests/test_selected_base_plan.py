from types import SimpleNamespace

import pytest

from app.design.exceptions import GenerationFailure
from app.design.generation import generation_service as tool


def test_preferred_plan_restricts_existing_ai_candidate_pool(monkeypatch):
    first = SimpleNamespace(plan_code='PLAN-A', topology_family='COMPACT_RECTANGLE')
    selected = SimpleNamespace(plan_code='PLAN-B', topology_family='L_SHAPE')
    monkeypatch.setattr(tool, 'filter_compatible_base_plans', lambda req, plot: [first, selected])
    monkeypatch.setattr(tool, 'load_base_plan_catalog', list)
    monkeypatch.setattr(tool, 'rank_base_plans', lambda plans, req, plot: plans)
    monkeypatch.setattr(tool, 'deduplicate_base_plans', lambda plans, excluded=None: plans)
    monkeypatch.setattr(tool, 'suitability_breakdown', lambda plan, req, plot: {'score': 1})

    result = tool._candidate_pool(object(), object(), preferred_plan_code='PLAN-B')

    assert [plan.plan_code for plan in result] == ['PLAN-B']


def test_unknown_preferred_plan_is_rejected(monkeypatch):
    monkeypatch.setattr(tool, 'filter_compatible_base_plans', lambda req, plot: [])
    monkeypatch.setattr(tool, 'load_base_plan_catalog', list)
    with pytest.raises(GenerationFailure, match='selected base plan is not compatible'):
        tool._candidate_pool(object(), object(), preferred_plan_code='MISSING')
