"""
Stage 2 Integration Tests: LangGraph House Planning Workflow & Validation Gatekeeper
====================================================================================

Verifies:
1. Full workflow execution on valid proposal -> PASS -> status="awaiting_approval", approval_status="pending".
2. Validation node behavior on failure -> increments retry_count and routes to "revision_to_design".
3. Maximum retries exceeded -> transitions to status="failed" and terminates safely.
4. Persistence of structured validation result inside WorkflowState.
5. Safe failure on missing critical inputs without exceptions or false approvals.
"""

import pytest
from uuid import uuid4
from app.schemas.workflow_state import WorkflowState, CoordinatorInput
from app.workflows.house_planning_graph import (
    app_graph,
    validation_node,
    route_from_validation,
    MAX_VALIDATION_RETRIES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def valid_workflow_state() -> WorkflowState:
    """Provides a WorkflowState with compliant proposal data."""
    return WorkflowState(
        workflow_id=uuid4(),
        status="running",
        input_data=CoordinatorInput(
            submission_id=uuid4(),
            budget_lkr=20_000_000.0,
            land_size_perches=10.0,             # 10 * 272.25 = 2722.5 sqft
            manual_terrain_type="flat",
            preferences={"preferred_bedrooms": 3, "preferred_floors": 2},
        ),
        terrain_result={
            "terrain_type": "flat",
            "slope_estimate": "flat",
            "notable_features": [],
        },
        design_result={
            "ground_coverage_sqft": 1400.0,     # 1400 / 2722.5 = 51.4% <= 65% (PASS)
            "foundation_type": "strip",         # Strip on flat (PASS)
            "bedrooms": 3,
            "floors": 2,
        },
        cost_result={
            "total_estimated_cost_lkr": 19_500_000.0,  # <= 20M + 10% (PASS)
        },
    )


@pytest.fixture
def failing_workflow_state(valid_workflow_state: WorkflowState) -> WorkflowState:
    """Provides a WorkflowState that fails the ground coverage rule."""
    valid_workflow_state.design_result["ground_coverage_sqft"] = 2200.0  # 2200 / 2722.5 = 80.8% > 65%
    return valid_workflow_state


# ---------------------------------------------------------------------------
# Test 1: Full Graph Execution — Validation PASS
# ---------------------------------------------------------------------------
def test_workflow_validation_pass(valid_workflow_state: WorkflowState):
    """
    Given a valid house planning proposal, the graph should execute from
    Coordinator -> Land/Design/Cost -> Validation -> END, reaching 'awaiting_approval'.
    """
    result = app_graph.invoke(valid_workflow_state)

    # Convert to dict or access attributes based on LangGraph return type
    res_status = result["status"] if isinstance(result, dict) else result.status
    res_approval = result["approval_status"] if isinstance(result, dict) else result.approval_status
    val_res = result["validation_result"] if isinstance(result, dict) else result.validation_result

    assert val_res is not None
    assert val_res["passed"] is True
    assert res_status == "awaiting_approval"
    assert res_approval == "pending"


# ---------------------------------------------------------------------------
# Test 2: Validation FAIL with Retry Available
# ---------------------------------------------------------------------------
def test_validation_fail_routes_to_revision(failing_workflow_state: WorkflowState):
    """
    Given a state failing validation with retry_count=0 (< MAX_VALIDATION_RETRIES),
    validation_node must increment retry_count to 1 and route to revision_to_design.
    """
    failing_workflow_state.retry_count = 0
    updated_state = validation_node(failing_workflow_state)

    assert updated_state.validation_result is not None
    assert updated_state.validation_result["passed"] is False
    assert updated_state.retry_count == 1
    assert updated_state.current_agent == "design"
    assert updated_state.status == "running"  # Not awaiting_approval

    next_route = route_from_validation(updated_state)
    assert next_route == "revision_to_design"


# ---------------------------------------------------------------------------
# Test 3: Maximum Retries Exceeded -> Terminates with status="failed"
# ---------------------------------------------------------------------------
def test_validation_max_retries_exceeded_terminates_safely(failing_workflow_state: WorkflowState):
    """
    When a failing proposal has already reached MAX_VALIDATION_RETRIES (3),
    validation_node must set status='failed' and route to 'failed' (terminal END).
    """
    failing_workflow_state.retry_count = MAX_VALIDATION_RETRIES  # 3
    updated_state = validation_node(failing_workflow_state)

    assert updated_state.validation_result is not None
    assert updated_state.validation_result["passed"] is False
    assert updated_state.status == "failed"
    assert updated_state.current_agent == "failed"

    next_route = route_from_validation(updated_state)
    assert next_route == "failed"


# ---------------------------------------------------------------------------
# Test 4: Validation Result Persisted with All Rules & Details
# ---------------------------------------------------------------------------
def test_validation_result_structure_persisted(valid_workflow_state: WorkflowState):
    """
    Verifies that state.validation_result contains a complete, auditable breakdown
    including 'passed', 'rules', 'errors', and 'summary'.
    """
    updated_state = validation_node(valid_workflow_state)

    val_res = updated_state.validation_result
    assert isinstance(val_res, dict)
    assert "passed" in val_res
    assert "rules" in val_res
    assert "errors" in val_res
    assert "summary" in val_res
    assert len(val_res["rules"]) == 4

    rule_names = [r["rule_name"] for r in val_res["rules"]]
    assert "coverage" in rule_names
    assert "terrain_foundation" in rule_names
    assert "budget" in rule_names
    assert "preferences" in rule_names


# ---------------------------------------------------------------------------
# Test 5: Missing Critical Input Results in Safe Failure
# ---------------------------------------------------------------------------
def test_missing_critical_input_safe_failure():
    """
    An unpopulated or malformed state must fail validation safely without
    throwing unhandled exceptions or falsely setting status to 'awaiting_approval'.
    """
    empty_state = WorkflowState(
        workflow_id=uuid4(),
        status="running",
        input_data=CoordinatorInput(
            submission_id=uuid4(),
            budget_lkr=0.0,
            land_size_perches=0.0,
            preferences={},
        ),
    )

    updated_state = validation_node(empty_state)

    assert updated_state.validation_result is not None
    assert updated_state.validation_result["passed"] is False
    assert updated_state.status != "awaiting_approval"
    assert len(updated_state.validation_result["errors"]) > 0
