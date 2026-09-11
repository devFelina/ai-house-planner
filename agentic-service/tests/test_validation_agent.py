"""
Unit and Integration Tests for Validation/Safety Agent (Component D — Stage 1)
==============================================================================

Tests deterministic validation rules, safe failure handling, boundary cases,
multi-failure reporting, and state adapter compatibility.
"""

import pytest
from uuid import uuid4
from app.schemas.validation_schemas import (
    HousePlanValidationInput,
    ValidationResult,
)
from app.agents.validation_agent import (
    PERCH_TO_SQFT,
    DEFAULT_MAX_COVERAGE_RATIO,
    DEFAULT_BUDGET_TOLERANCE_RATIO,
    validate_coverage,
    validate_terrain_foundation,
    validate_budget,
    validate_preferences,
    validate_house_plan,
    ValidationAgent,
)
from app.schemas.workflow_agent import (
    WorkflowState,
    CoordinatorInput,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def valid_input() -> HousePlanValidationInput:
    """Fixture providing a baseline 100% valid proposal input."""
    return HousePlanValidationInput(
        land_size_perches=10.0,            # 10 * 272.25 = 2722.5 sqft
        ground_coverage_sqft=1200.0,       # 1200 / 2722.5 = 44.08% <= 65% (PASS)
        terrain_type="flat",
        slope_estimate="flat",
        foundation_type="strip",           # strip on flat (PASS)
        budget_lkr=15_000_000.0,
        estimated_cost_lkr=14_500_000.0,   # 14.5M <= 15M + 10% = 16.5M (PASS)
        requested_bedrooms=3,
        actual_bedrooms=3,                 # matches (PASS)
        requested_floors=2,
        actual_floors=2,                   # matches (PASS)
    )


# ---------------------------------------------------------------------------
# Test 1: Completely Valid Proposal -> PASS
# ---------------------------------------------------------------------------
def test_valid_house_plan_passes(valid_input: HousePlanValidationInput):
    """Verifies that a well-formed proposal meeting all safety criteria passes all rules."""
    result: ValidationResult = validate_house_plan(valid_input)

    assert result.passed is True
    assert len(result.errors) == 0
    assert "PASSED" in result.summary
    assert len(result.rules) == 4

    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["coverage"].passed is True
    assert rule_dict["terrain_foundation"].passed is True
    assert rule_dict["budget"].passed is True
    assert rule_dict["preferences"].passed is True


# ---------------------------------------------------------------------------
# Test 2: Coverage Exceeds Maximum -> FAIL
# ---------------------------------------------------------------------------
def test_coverage_exceeds_maximum_fails(valid_input: HousePlanValidationInput):
    """
    10 perches = 2722.5 sqft. Max 65% = 1769.625 sqft.
    If ground coverage is 2000 sqft (73.46%), it must fail.
    """
    valid_input.ground_coverage_sqft = 2000.0
    result: ValidationResult = validate_house_plan(valid_input)

    assert result.passed is False
    assert len(result.errors) == 1

    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["coverage"].passed is False
    assert "exceeds the maximum allowable limit" in rule_dict["coverage"].reason
    assert rule_dict["terrain_foundation"].passed is True
    assert rule_dict["budget"].passed is True
    assert rule_dict["preferences"].passed is True


# ---------------------------------------------------------------------------
# Test 3: Budget Exceeds Tolerance -> FAIL
# ---------------------------------------------------------------------------
def test_budget_exceeds_tolerance_fails(valid_input: HousePlanValidationInput):
    """
    Budget = 10,000,000. 10% tolerance = 11,000,000 max.
    Estimated cost = 12,000,000 (+20%). Must fail.
    """
    valid_input.budget_lkr = 10_000_000.0
    valid_input.estimated_cost_lkr = 12_000_000.0
    result: ValidationResult = validate_house_plan(valid_input)

    assert result.passed is False
    assert len(result.errors) == 1

    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["budget"].passed is False
    assert "surpassing the maximum allowable 10.0% tolerance" in rule_dict["budget"].reason


# ---------------------------------------------------------------------------
# Test 4: Incompatible Terrain / Foundation -> FAIL
# ---------------------------------------------------------------------------
def test_incompatible_terrain_foundation_fails(valid_input: HousePlanValidationInput):
    """
    Steep slope with basic shallow 'strip' foundation is unsafe and must fail.
    Supported types on steep slope: stepped_strip, pile, pier, retaining_wall_integrated.
    """
    valid_input.slope_estimate = "steep_slope"
    valid_input.foundation_type = "strip"
    result: ValidationResult = validate_house_plan(valid_input)

    assert result.passed is False
    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["terrain_foundation"].passed is False
    assert "incompatible with 'steep_slope' terrain" in rule_dict["terrain_foundation"].reason


# ---------------------------------------------------------------------------
# Test 5: Bedroom Requirement Mismatch -> FAIL
# ---------------------------------------------------------------------------
def test_bedroom_requirement_mismatch_fails(valid_input: HousePlanValidationInput):
    """Client requested 4 bedrooms, but design only provides 3 bedrooms."""
    valid_input.requested_bedrooms = 4
    valid_input.actual_bedrooms = 3
    result: ValidationResult = validate_house_plan(valid_input)

    assert result.passed is False
    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["preferences"].passed is False
    assert "Bedroom count mismatch" in rule_dict["preferences"].reason


# ---------------------------------------------------------------------------
# Test 6: Floor Requirement Mismatch -> FAIL
# ---------------------------------------------------------------------------
def test_floor_requirement_mismatch_fails(valid_input: HousePlanValidationInput):
    """Client requested a 2-storey house, but design provides a 3-storey house."""
    valid_input.requested_floors = 2
    valid_input.actual_floors = 3
    result: ValidationResult = validate_house_plan(valid_input)

    assert result.passed is False
    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["preferences"].passed is False
    assert "Floor count mismatch" in rule_dict["preferences"].reason


# ---------------------------------------------------------------------------
# Test 7: Multiple Validation Failures Reported Simultaneously
# ---------------------------------------------------------------------------
def test_multiple_validation_failures_reported(valid_input: HousePlanValidationInput):
    """
    Verifies that all failing rules are captured in a single validation pass
    rather than aborting on the first error.
    """
    valid_input.ground_coverage_sqft = 2500.0        # Fails coverage (91.8%)
    valid_input.estimated_cost_lkr = 25_000_000.0     # Fails budget (15M budget)
    valid_input.actual_bedrooms = 5                  # Fails bedrooms (requested 3)

    result: ValidationResult = validate_house_plan(valid_input)

    assert result.passed is False
    assert len(result.errors) == 3
    assert "3 rule(s) failed" in result.summary

    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["coverage"].passed is False
    assert rule_dict["budget"].passed is False
    assert rule_dict["preferences"].passed is False
    assert rule_dict["terrain_foundation"].passed is True


# ---------------------------------------------------------------------------
# Test 8: Missing Critical Input -> Safe Failure
# ---------------------------------------------------------------------------
def test_missing_critical_input_safe_failure():
    """Missing land size, ground coverage, budget, and terrain must fail safely without throwing unhandled exceptions."""
    empty_input = HousePlanValidationInput()
    result: ValidationResult = validate_house_plan(empty_input)

    assert result.passed is False
    assert len(result.errors) >= 3

    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["coverage"].passed is False
    assert "Missing required inputs" in rule_dict["coverage"].reason
    assert rule_dict["budget"].passed is False
    assert "Missing budget" in rule_dict["budget"].reason
    assert rule_dict["terrain_foundation"].passed is False


# ---------------------------------------------------------------------------
# Test 9: Invalid Numeric Inputs -> Safe Failure
# ---------------------------------------------------------------------------
def test_invalid_numeric_inputs_safe_failure(valid_input: HousePlanValidationInput):
    """Negative or zero land size and negative budget/costs must be rejected."""
    # Zero land size
    valid_input.land_size_perches = 0.0
    result_zero_land = validate_house_plan(valid_input)
    assert result_zero_land.passed is False
    assert "Invalid land size" in result_zero_land.errors[0]

    # Negative budget
    valid_input.land_size_perches = 10.0
    valid_input.budget_lkr = -500_000.0
    result_neg_budget = validate_house_plan(valid_input)
    assert result_neg_budget.passed is False
    assert "Invalid client budget" in result_neg_budget.errors[0]

    # Negative ground coverage
    valid_input.budget_lkr = 15_000_000.0
    valid_input.ground_coverage_sqft = -100.0
    result_neg_cov = validate_house_plan(valid_input)
    assert result_neg_cov.passed is False
    assert "Invalid ground coverage" in result_neg_cov.errors[0]


# ---------------------------------------------------------------------------
# Test 10: Boundary Conditions
# ---------------------------------------------------------------------------
def test_boundary_conditions():
    """
    Exact boundary tests:
    - Coverage exactly at 65.0% -> PASS
    - Budget exactly at Budget + 10.0% -> PASS
    - Budget at Budget + 10.0% + 1 Rupee -> FAIL
    """
    # 10 perches = 2722.5 sqft. 65% of 2722.5 = 1769.625 sqft.
    exact_coverage = 10.0 * PERCH_TO_SQFT * 0.65
    res_cov = validate_coverage(10.0, exact_coverage, max_coverage_ratio=0.65)
    assert res_cov.passed is True

    # 1 sqft over limit
    res_cov_over = validate_coverage(10.0, exact_coverage + 1.0, max_coverage_ratio=0.65)
    assert res_cov_over.passed is False

    # Budget 10,000,000. 10% tolerance = 11,000,000.0
    res_budget_exact = validate_budget(10_000_000.0, 11_000_000.0, tolerance_ratio=0.10)
    assert res_budget_exact.passed is True

    # Budget 11,000,001.0 -> FAIL
    res_budget_over = validate_budget(10_000_000.0, 11_000_001.0, tolerance_ratio=0.10)
    assert res_budget_over.passed is False


# ---------------------------------------------------------------------------
# Test 11: WorkflowState Object & Dict Extraction Adapter
# ---------------------------------------------------------------------------
def test_workflow_state_adapter_integration():
    """Verifies that the validation agent can ingest a WorkflowState Pydantic object directly."""
    state = WorkflowState(
        workflow_id=uuid4(),
        status="running",
        input_data=CoordinatorInput(
            submission_id=uuid4(),
            budget_lkr=20_000_000.0,
            land_size_perches=12.0,
            manual_terrain_type="rocky",
            preferences={"preferred_bedrooms": 4, "preferred_floors": 2},
        ),
        terrain_result={
            "terrain_type": "rocky",
            "slope_estimate": "slight_slope",
            "notable_features": ["granite outcrop"],
        },
        design_result={
            "ground_coverage_sqft": 1800.0,    # 1800 / (12 * 272.25 = 3267) = 55.1% <= 65%
            "foundation_type": "pad",          # Pad foundation on rocky terrain (PASS)
            "bedrooms": 4,
            "floors": 2,
        },
        cost_result={
            "total_estimated_cost_lkr": 21_500_000.0, # 21.5M <= 20M + 10% (22M) (PASS)
        },
    )

    result = validate_house_plan(state)
    assert result.passed is True
    assert len(result.rules) == 4
    assert all(r.passed for r in result.rules)


# ---------------------------------------------------------------------------
# Test 12: ValidationAgent Class Wrapper & Custom Thresholds
# ---------------------------------------------------------------------------
def test_validation_agent_class_custom_thresholds(valid_input: HousePlanValidationInput):
    """Verifies that custom thresholds (e.g. 5% budget tolerance, 40% coverage) work via ValidationAgent."""
    agent = ValidationAgent(max_coverage_ratio=0.40, budget_tolerance_ratio=0.05)

    # valid_input has coverage ~44% (> 40%), so it should fail with custom 40% threshold
    result = agent.validate(valid_input)
    assert result.passed is False
    rule_dict = {r.rule_name: r for r in result.rules}
    assert rule_dict["coverage"].passed is False
    assert "exceeds the maximum allowable limit of 40.0%" in rule_dict["coverage"].reason
