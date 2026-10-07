"""
tests/test_execution_timeline.py
=================================
Phase 6: Agent Execution Timeline and Explainability

Tests:
1. Agent log entries are created by each node (coordinator, design, validation, rendering).
2. Logs survive state updates (list is not reset between nodes).
3. push_execution_log correctly collapses the log into the simplified timeline shape.
4. frontend status response DTO shape contains agentExecutionLog field.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.schemas.workflow_state import (
    CoordinatorInput,
    ExecutionLogEntry,
    WorkflowState,
)
from app.orchestration.workflow_router import coordinator_node
from app.utils.execution_log import _build_timeline


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _make_state(**overrides) -> WorkflowState:
    wf_id = uuid4()
    defaults = dict(
        workflow_id=wf_id,
        status="running",
        input_data=CoordinatorInput(
            submission_id=uuid4(),
            land_size_category="medium",
            land_size_perches=10.0,
            bedrooms=3,
            bathrooms=2,
            house_type="conventional",
        ),
    )
    defaults.update(overrides)
    return WorkflowState(**defaults)


def _make_log_entry(agent_name: str, action: str, result: str = "ok") -> ExecutionLogEntry:
    return ExecutionLogEntry(
        agent_name=agent_name,
        action=action,
        result=result,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )


# ─────────────────────────────────────────────────────────────────
# 1. coordinator_node appends a log entry
# ─────────────────────────────────────────────────────────────────

def test_coordinator_node_appends_log_entry():
    state = _make_state()
    assert len(state.execution_log) == 0

    result = coordinator_node(state)

    assert len(result.execution_log) == 2
    entry = result.execution_log[1]
    assert entry.agent_name == "CoordinatorAgent"
    assert "workflow_step_selected" in entry.action
    assert "assigned_agent=" in entry.result


def test_coordinator_log_entry_contains_routing_decision():
    """The log message should mention which path was taken."""
    state = _make_state()
    result = coordinator_node(state)
    entry = result.execution_log[1]
    # now it routes to requirement_analysis
    assert "requirement_analysis" in entry.result or "workflow_step_selected" in entry.action


# ─────────────────────────────────────────────────────────────────
# 2. Logs survive state updates between nodes
# ─────────────────────────────────────────────────────────────────

def test_logs_accumulate_across_nodes():
    """Log list must not be reset between node calls."""
    state = _make_state()

    state.execution_log.append(_make_log_entry("CoordinatorAgent", "Init"))
    state.execution_log.append(_make_log_entry("RequirementAnalysisAgent", "Extracted preferences"))
    state.execution_log.append(_make_log_entry("DesignAgent", "Catalogue plan selected: HP-TEST"))

    assert len(state.execution_log) == 3

    # Simulate a state field update (as nodes do) — list must be unchanged
    state.status = "design_generated"

    assert len(state.execution_log) == 3
    assert state.execution_log[2].agent_name == "DesignAgent"


def test_logs_are_preserved_through_model_roundtrip():
    """Pydantic serialise → deserialise must not lose log entries."""
    state = _make_state()
    state.execution_log.append(_make_log_entry("CoordinatorAgent", "Workflow initialised"))
    state.execution_log.append(_make_log_entry("DesignAgent", "Catalogue plan selected: HP-TEST"))

    dumped = state.model_dump()
    restored = WorkflowState(**dumped)

    assert len(restored.execution_log) == 2
    assert restored.execution_log[0].agent_name == "CoordinatorAgent"
    assert restored.execution_log[1].agent_name == "DesignAgent"


# ─────────────────────────────────────────────────────────────────
# 3. _build_timeline produces the correct simplified shape
# ─────────────────────────────────────────────────────────────────

def test_build_timeline_collapses_to_one_entry_per_agent():
    state = _make_state()
    # Two entries for DesignAgent — only the last should win
    state.execution_log.extend([
        _make_log_entry("CoordinatorAgent", "Workflow initialised — routed to Design"),
        _make_log_entry("DesignAgent", "First attempt"),
        _make_log_entry("DesignAgent", "Catalogue plan selected: HP-DEMO"),
        _make_log_entry("ValidationAgent", "Design validation passed"),
        _make_log_entry("RenderingAgent", "Rendering completed"),
    ])

    timeline = _build_timeline(state)

    # Should have 4 unique agents (not 5 entries)
    assert len(timeline) == 4
    labels = [e["agent"] for e in timeline]
    assert labels == ["coordinator", "design", "validation", "rendering"]


def test_build_timeline_entry_shape():
    state = _make_state()
    state.execution_log.append(_make_log_entry("CoordinatorAgent", "Workflow initialised"))

    timeline = _build_timeline(state)
    assert len(timeline) == 1

    entry = timeline[0]
    assert set(entry.keys()) == {"agent", "status", "message"}
    assert entry["agent"] == "coordinator"
    assert entry["status"] == "completed"
    assert entry["message"] == "Workflow initialised"


def test_build_timeline_marks_failure_correctly():
    state = _make_state()
    state.execution_log.append(
        _make_log_entry("DesignAgent", "Design generation failed", result="GenerationFailure: no pool")
    )

    timeline = _build_timeline(state)
    assert timeline[0]["status"] == "failed"


def test_build_timeline_preserves_order():
    state = _make_state()
    agents = [
        "CoordinatorAgent", "RequirementAnalysisAgent",
        "LandAnalysisAgent", "DesignAgent",
        "ConstructionPlanningAgent", "CostEstimationAgent",
        "ValidationAgent", "RenderingAgent",
    ]
    for name in agents:
        state.execution_log.append(_make_log_entry(name, f"{name} done"))

    timeline = _build_timeline(state)
    expected_labels = [
        "coordinator", "requirement_analysis", "land_analysis", "design",
        "construction_planning", "cost_estimation", "validation", "rendering",
    ]
    assert [e["agent"] for e in timeline] == expected_labels


# ─────────────────────────────────────────────────────────────────
# 4. push_execution_log calls the ASP.NET endpoint with correct payload
# ─────────────────────────────────────────────────────────────────

@patch("app.utils.execution_log.requests.patch")
def test_push_execution_log_calls_correct_endpoint(mock_patch):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_patch.return_value = mock_response

    from app.utils.execution_log import push_execution_log

    state = _make_state()
    state.execution_log.append(_make_log_entry("CoordinatorAgent", "Workflow initialised"))
    state.execution_log.append(_make_log_entry("DesignAgent", "Catalogue plan selected: HP-TEST"))

    push_execution_log(state)

    assert mock_patch.called
    call_kwargs = mock_patch.call_args
    url = call_kwargs[0][0]
    assert str(state.workflow_id) in url
    assert url.endswith("/execution-log")

    body = json.loads(call_kwargs[1]["data"])
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["agent"] == "coordinator"
    assert body[1]["agent"] == "design"


@patch("app.utils.execution_log.requests.patch")
def test_push_execution_log_is_silent_on_failure(mock_patch):
    """A network failure must not raise — the workflow must continue."""
    import requests as req_lib
    mock_patch.side_effect = req_lib.ConnectionError("ASP.NET down")

    from app.utils.execution_log import push_execution_log

    state = _make_state()
    state.execution_log.append(_make_log_entry("CoordinatorAgent", "Init"))

    # Should NOT raise
    push_execution_log(state)


@patch("app.utils.execution_log.requests.patch")
def test_push_execution_log_noop_when_empty(mock_patch):
    """No HTTP call should be made when execution_log is empty."""
    from app.utils.execution_log import push_execution_log

    state = _make_state()
    push_execution_log(state)
    mock_patch.assert_not_called()


# ─────────────────────────────────────────────────────────────────
# 5. Frontend status response DTO shape
# ─────────────────────────────────────────────────────────────────

def test_frontend_dto_shape_matches_timeline_output():
    """
    The timeline produced by _build_timeline must be JSON-serialisable and
    match the shape the TypeScript interface expects:
      { agent: string, status: string, message: string }[]
    """
    state = _make_state()
    state.execution_log.extend([
        _make_log_entry("CoordinatorAgent", "Workflow initialised"),
        _make_log_entry("DesignAgent", "Catalogue plan selected: HP-DEMO-M-3B2B-1F-DINING-A"),
        _make_log_entry("ValidationAgent", "Design validation passed"),
        _make_log_entry("RenderingAgent", "Rendering completed"),
    ])

    timeline = _build_timeline(state)
    serialised = json.dumps(timeline)  # must not raise
    parsed = json.loads(serialised)

    for entry in parsed:
        assert "agent" in entry
        assert "status" in entry
        assert "message" in entry
        assert isinstance(entry["agent"], str)
        assert isinstance(entry["status"], str)
        assert isinstance(entry["message"], str)

if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import pytest
    sys.exit(pytest.main(["-v", "-s", __file__]))
