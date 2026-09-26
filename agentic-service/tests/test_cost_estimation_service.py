"""
Unit tests for the Cost Estimation Service (Component C).

All tests mock pricing_lookup_tool() so no network calls are made.
No psycopg2 / asyncpg / sqlalchemy is imported by the agent under test.

Test naming convention:
    test_<scenario>  →  assert exact numeric results or exact failure mode.
"""
import inspect
import json
import uuid
from unittest.mock import patch

import pytest
import responses

from app.services.cost_estimation_service import (
    _persist_cost_estimate,
    cost_estimation_node,
)
from app.validation.design_validation_service import validation_node
from app.schemas.cost_result import CostResult
from app.schemas.pricing_data import PricingItem
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.workflows.house_planning_graph import route_after_cost_estimation

# ---------------------------------------------------------------------------
# Pricing fixtures (returned by the mocked pricing_lookup_tool)
# ---------------------------------------------------------------------------
#
# Material item: unit_cost_lkr = 200.0  (per_sqft)
#   flat      multiplier = 1.00  → effective rate = 200.00 /sqft
#   hillside  multiplier = 1.25  → effective rate = 250.00 /sqft
#   coastal   multiplier = 1.35  → effective rate = 270.00 /sqft
#
# Labour factor:  unit_cost_lkr = 0.30  (factor)
#   labour_cost = material_cost × 0.30
# ---------------------------------------------------------------------------

MATERIAL_ITEM = PricingItem.model_validate(
    {
        "id": 1,
        "itemName": "Concrete Block",
        "category": "material",
        "unitCostLkr": 200.0,
        "unit": "per_sqft",
        "terrainMultiplier": {"flat": 1.00, "hillside": 1.25, "coastal": 1.35},
    }
)

LABOUR_ITEM = PricingItem.model_validate(
    {
        "id": 2,
        "itemName": "Labour Rate",
        "category": "labour",
        "unitCostLkr": 0.30,
        "unit": "factor",
        "terrainMultiplier": {"flat": 1.00, "hillside": 1.00, "coastal": 1.00},
    }
)

STANDARD_PRICING: list[PricingItem] = [MATERIAL_ITEM, LABOUR_ITEM]

# ---------------------------------------------------------------------------
# Helper — build a minimal valid WorkflowState
# ---------------------------------------------------------------------------

ROOM_A = {
    "room_id": "r1",
    "room_type": "living_room",
    "floor": 1,
    "x": 0.0,
    "y": 0.0,
    "width": 20.0,
    "length": 15.0,
    "area_sqft": 300.0,  # explicit — 20 × 15
    "wall_height": 9.0,
    "doors": [],
    "windows": [],
}

ROOM_B = {
    "room_id": "r2",
    "room_type": "bedroom",
    "floor": 1,
    "x": 20.0,
    "y": 0.0,
    "width": 12.0,
    "length": 10.0,
    "area_sqft": 120.0,  # explicit — 12 × 10
    "wall_height": 9.0,
    "doors": [],
    "windows": [],
}

# Total area = 300 + 120 = 420 sqft


def _make_state(
    terrain_type: str = "flat",
    rooms=None,
    budget_lkr: float = 5_000_000.0,
    terrain_result_override=None,
    design_result_override=None,
    no_terrain: bool = False,
    no_design: bool = False,
    no_budget: bool = False,
) -> WorkflowState:
    """Return a minimal valid WorkflowState for cost estimation tests."""
    if rooms is None:
        rooms = [ROOM_A, ROOM_B]

    terrain = (
        None
        if no_terrain
        else (
            terrain_result_override
            if terrain_result_override is not None
            else {"terrain_type": terrain_type}
        )
    )

    design = (
        None
        if no_design
        else (
            design_result_override
            if design_result_override is not None
            else {
                "design_id": "d1",
                "floor_count": 1,
                "total_built_up_area_sqft": 420.0,
                "foundation_type": "slab",
                "terrain_type": terrain_type,
                "template_id": "T1",
                "rooms": rooms,
            }
        )
    )

    return WorkflowState(
        workflow_id=uuid.uuid4(),
        status="running",
        terrain_result=terrain,
        design_result=design,
        input_data=CoordinatorInput(
            submission_id=uuid.uuid4(),
            budget_lkr=None if no_budget else budget_lkr,
            land_size_perches=10.0,
            preferences={"bedrooms": 2, "floors": 1},
        ),
        current_agent="cost_estimation",
    )


# ---------------------------------------------------------------------------
# Patch target
# ---------------------------------------------------------------------------

PATCH_TARGET = "app.services.cost_estimation_service.pricing_lookup_tool"
PERSIST_TARGET = "app.services.cost_estimation_service._persist_cost_estimate"


@pytest.fixture(autouse=True)
def mock_cost_persistence():
    """Keep unit tests offline while asserting persistence separately."""
    with patch(PERSIST_TARGET) as mock_persist, \
         patch("app.services.cost_estimation_service._record_run"), \
         patch("app.services.cost_estimation_service._persist_failure"):
        yield mock_persist


def test_successful_estimate_is_persisted(mock_cost_persistence):
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state())

    assert state.status != "failed"
    mock_cost_persistence.assert_called_once()
    persisted_state, persisted_result = mock_cost_persistence.call_args.args
    assert persisted_state is state
    assert persisted_result.total_cost_lkr == 109_200.0


@responses.activate
def test_persistence_posts_expected_contract():
    endpoint = "https://api.example/api/v1/internal/workflows/00000000-0000-0000-0000-000000000001/cost-estimate"
    responses.add(responses.POST, endpoint, json={"costEstimateId": "saved"}, status=200)
    state = _make_state()
    state.workflow_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    result = CostResult(
        material_cost_lkr=84_000.0,
        labour_cost_lkr=25_200.0,
        total_cost_lkr=109_200.0,
        budget_delta_percent=2.18,
        terrain_type="flat",
        room_count=2,
        total_area_sqft=420.0,
        pricing_snapshot=[{"id": 1, "itemName": "Foundation Materials", "unitCostLkr": 3000}],
    )

    with (
        patch("app.services.cost_estimation_service.ASPNET_API_URL", "https://api.example/api/v1"),
        patch("app.services.cost_estimation_service.INTERNAL_API_KEY", "test-key"),
    ):
        _persist_cost_estimate(state, result)

    request = responses.calls[0].request
    assert request.headers["X-Internal-API-Key"] == "test-key"
    assert json.loads(request.body) == {
        "materialCostLkr": 84_000.0,
        "labourCostLkr": 25_200.0,
        "totalCostLkr": 109_200.0,
        "budgetDeltaPercent": 2.18,
        "pricingSnapshot": [{"id": 1, "itemName": "Foundation Materials", "unitCostLkr": 3000}],
        "breakdown": [],
        "formulaVersion": "category-area-v1",
        "appliedAreaSqft": 420.0,
        "terrainType": "flat",
    }


def test_validation_uses_total_cost_lkr():
    state = _make_state(budget_lkr=100_000.0)
    state.cost_result = {"total_cost_lkr": 120_000.0}

    result = validation_node(state)

    assert result.status == "rejected"
    assert result.validation_result["is_valid"] is False


def test_failed_cost_estimation_stops_before_validation():
    state = _make_state()
    state.status = "failed"

    assert route_after_cost_estimation(state) == "failed"


# ===========================================================================
# Happy-path — terrain multiplier tests (exact numeric assertions)
# ===========================================================================


def test_flat_terrain_calculation():
    """
    Flat terrain multiplier = 1.00.
    material_cost = (300 + 120) × 200.0 × 1.00 = 84 000.00
    labour_cost   = 84 000.00 × 0.30           = 25 200.00
    total_cost    = 84 000.00 + 25 200.00       = 109 200.00
    budget_delta  = (109 200 / 5 000 000) × 100 = 2.18 %
    """
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(terrain_type="flat"))

    assert state.status == "running"
    assert state.current_agent == "validation"
    r = state.cost_result

    assert r["material_cost_lkr"] == pytest.approx(84_000.00, rel=1e-6)
    assert r["labour_cost_lkr"] == pytest.approx(25_200.00, rel=1e-6)
    assert r["total_cost_lkr"] == pytest.approx(109_200.00, rel=1e-6)
    assert r["budget_delta_percent"] == pytest.approx(2.18, rel=1e-4)
    assert r["terrain_type"] == "flat"
    assert r["room_count"] == 2
    assert r["total_area_sqft"] == pytest.approx(420.0, rel=1e-6)


def test_hillside_terrain_increases_cost():
    """
    Hillside multiplier = 1.25.
    material_cost = 420 × 200.0 × 1.25 = 105 000.00
    labour_cost   = 105 000.00 × 0.30  =  31 500.00
    total_cost    = 105 000.00 + 31 500.00 = 136 500.00
    budget_delta  = (136 500 / 5 000 000) × 100 = 2.73 %
    """
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(terrain_type="hillside"))

    assert state.status == "running"
    r = state.cost_result
    assert r["material_cost_lkr"] == pytest.approx(105_000.00, rel=1e-6)
    assert r["labour_cost_lkr"] == pytest.approx(31_500.00, rel=1e-6)
    assert r["total_cost_lkr"] == pytest.approx(136_500.00, rel=1e-6)
    assert r["budget_delta_percent"] == pytest.approx(2.73, rel=1e-4)
    assert r["terrain_type"] == "hillside"


def test_coastal_multiplier():
    """
    Coastal multiplier = 1.35.
    material_cost = 420 × 200.0 × 1.35 = 113 400.00
    labour_cost   = 113 400.00 × 0.30  =  34 020.00
    total_cost    = 113 400.00 + 34 020.00 = 147 420.00
    budget_delta  = (147 420 / 5 000 000) × 100 = 2.95 %
    """
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(terrain_type="coastal"))

    assert state.status == "running"
    r = state.cost_result
    assert r["material_cost_lkr"] == pytest.approx(113_400.00, rel=1e-6)
    assert r["labour_cost_lkr"] == pytest.approx(34_020.00, rel=1e-6)
    assert r["total_cost_lkr"] == pytest.approx(147_420.00, rel=1e-6)
    assert r["budget_delta_percent"] == pytest.approx(2.95, rel=1e-4)
    assert r["terrain_type"] == "coastal"


# ===========================================================================
# Happy-path — formula component tests
# ===========================================================================


def test_labour_factor_applied():
    """Labour cost must equal material_cost × labour_factor (0.30)."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state())

    r = state.cost_result
    assert r["labour_cost_lkr"] == pytest.approx(r["material_cost_lkr"] * 0.30, rel=1e-9)


def test_total_cost_equals_material_plus_labour():
    """total_cost must exactly equal material_cost + labour_cost."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state())

    r = state.cost_result
    assert r["total_cost_lkr"] == pytest.approx(
        r["material_cost_lkr"] + r["labour_cost_lkr"], rel=1e-9
    )


def test_budget_delta_percent_formula():
    """budget_delta_percent = (total_cost / budget_lkr) × 100, rounded to 2dp."""
    budget = 5_000_000.0
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(budget_lkr=budget))

    r = state.cost_result
    expected = round((r["total_cost_lkr"] / budget) * 100, 2)
    assert r["budget_delta_percent"] == pytest.approx(expected, rel=1e-9)


def test_room_area_computed_from_dimensions_when_area_sqft_absent():
    """
    When area_sqft is absent, the agent must compute width × length.
    Single room: width=10, length=8 → area=80 sqft.
    material_cost = 80 × 200 × 1.00 = 16 000
    labour_cost   = 16 000 × 0.30   =  4 800
    total_cost    = 20 800
    """
    room_no_area = {
        "room_id": "r3",
        "room_type": "bedroom",
        "floor": 1,
        "x": 0.0,
        "y": 0.0,
        "width": 10.0,
        "length": 8.0,
        # area_sqft intentionally absent
        "wall_height": 9.0,
        "doors": [],
        "windows": [],
    }
    input_state = _make_state(rooms=[room_no_area])
    input_state.design_result.pop("total_built_up_area_sqft", None)
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(input_state)

    assert state.status == "running"
    r = state.cost_result
    assert r["material_cost_lkr"] == pytest.approx(16_000.00, rel=1e-6)
    assert r["total_cost_lkr"] == pytest.approx(20_800.00, rel=1e-6)
    assert r["total_area_sqft"] == pytest.approx(80.0, rel=1e-6)


def test_cost_result_stored_in_state():
    """state.cost_result must be a dict with all required CostResult keys."""
    required_keys = {
        "material_cost_lkr",
        "labour_cost_lkr",
        "total_cost_lkr",
        "budget_delta_percent",
        "terrain_type",
        "room_count",
        "total_area_sqft",
    }
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state())

    assert state.cost_result is not None
    assert required_keys.issubset(set(state.cost_result.keys()))


# ===========================================================================
# Failure paths
# ===========================================================================


def _assert_failed(state: WorkflowState) -> None:
    """Common assertions for a safely failed state."""
    assert state.status == "failed", f"Expected 'failed', got '{state.status}'"
    assert state.current_agent == "failed"
    # At least one execution log entry with actionable message
    assert any(
        "cost estimation failed" in (e.action or "").lower()
        for e in state.execution_log
    ), "Expected a CostEstimationAgent failure entry in execution_log"


def test_missing_design_result():
    """Agent must fail safely when design_result is None."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(no_design=True))
    _assert_failed(state)
    assert state.cost_result is None


def test_missing_rooms():
    """Agent must fail safely when design_result contains no rooms."""
    design_no_rooms = {
        "design_id": "d1",
        "floor_count": 1,
        "total_built_up_area_sqft": 0.0,
        "foundation_type": "slab",
        "terrain_type": "flat",
        "template_id": "T1",
        "rooms": [],
    }
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(design_result_override=design_no_rooms))
    _assert_failed(state)


def test_missing_pricing():
    """Agent must fail safely when pricing_lookup_tool raises PricingLookupError."""
    from app.tools.pricing_lookup_tool import PricingLookupError

    with patch(PATCH_TARGET, side_effect=PricingLookupError("Backend unavailable")):
        state = cost_estimation_node(_make_state())
    _assert_failed(state)


def test_incompatible_material_unit():
    """Material with unit='bag' must trigger a controlled failure."""
    bad_material = PricingItem.model_validate(
        {
            "id": 3,
            "itemName": "Cement",
            "category": "material",
            "unitCostLkr": 1200.0,
            "unit": "bag",
            "terrainMultiplier": {"flat": 1.0, "hillside": 1.2, "coastal": 1.3},
        }
    )
    pricing = [bad_material, LABOUR_ITEM]
    with patch(PATCH_TARGET, return_value=pricing):
        state = cost_estimation_node(_make_state())
    _assert_failed(state)
    log_text = " ".join(e.action for e in state.execution_log)
    assert "incompatible unit" in log_text.lower() or "bag" in log_text.lower()


def test_missing_terrain():
    """Agent must fail safely when terrain_result is None."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(no_terrain=True))
    _assert_failed(state)


def test_unsupported_terrain():
    """terrain_type='unknown' must trigger a controlled failure."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(
            _make_state(terrain_result_override={"terrain_type": "unknown"})
        )
    _assert_failed(state)


def test_zero_budget_still_returns_cost_without_budget_percentage():
    """A legacy zero budget must not prevent the cost estimate."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(budget_lkr=0.0))
    assert state.status != "failed"
    assert state.cost_result["total_cost_lkr"] == pytest.approx(109_200.0)
    assert state.cost_result["budget_delta_percent"] is None


def test_missing_budget_still_returns_cost_without_budget_percentage():
    """Customer budget is optional; material, labour, and total must still be calculated."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(no_budget=True))
    assert state.status != "failed"
    assert state.cost_result["material_cost_lkr"] == pytest.approx(84_000.0)
    assert state.cost_result["labour_cost_lkr"] == pytest.approx(25_200.0)
    assert state.cost_result["total_cost_lkr"] == pytest.approx(109_200.0)
    assert state.cost_result["budget_delta_percent"] is None


def test_no_material_pricing():
    """When only labour items exist, agent must fail with a clear message."""
    pricing_only_labour = [LABOUR_ITEM]
    with patch(PATCH_TARGET, return_value=pricing_only_labour):
        state = cost_estimation_node(_make_state())
    _assert_failed(state)
    log_text = " ".join(e.action for e in state.execution_log)
    assert "material" in log_text.lower()


def test_no_active_labour_factor():
    """When the active catalogue has materials but no labour factor, estimation must fail."""
    with patch(PATCH_TARGET, return_value=[MATERIAL_ITEM]):
        state = cost_estimation_node(_make_state())
    _assert_failed(state)
    log_text = " ".join(e.action for e in state.execution_log)
    assert "labour" in log_text.lower()


def test_ambiguous_labour_factor():
    """Two labour-factor records must trigger a controlled failure."""
    labour2 = PricingItem.model_validate(
        {
            "id": 5,
            "itemName": "Skilled Labour Rate",
            "category": "labour",
            "unitCostLkr": 0.45,
            "unit": "factor",
            "terrainMultiplier": {"flat": 1.0, "hillside": 1.0, "coastal": 1.0},
        }
    )
    pricing = [MATERIAL_ITEM, LABOUR_ITEM, labour2]
    with patch(PATCH_TARGET, return_value=pricing):
        state = cost_estimation_node(_make_state())
    _assert_failed(state)
    log_text = " ".join(e.action for e in state.execution_log)
    assert "ambiguous" in log_text.lower() or "labour" in log_text.lower()


def test_invalid_room_dimensions_zero_width():
    """A room with width=0 must trigger a controlled failure."""
    bad_room = {
        "room_id": "r_bad",
        "room_type": "bedroom",
        "floor": 1,
        "x": 0.0,
        "y": 0.0,
        "width": 0.0,   # invalid
        "length": 10.0,
        "wall_height": 9.0,
        "doors": [],
        "windows": [],
    }
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(rooms=[bad_room]))
    _assert_failed(state)


def test_invalid_room_area_sqft_zero():
    """A room with area_sqft=0 must trigger a controlled failure."""
    bad_room = {
        "room_id": "r_zero",
        "room_type": "kitchen",
        "floor": 1,
        "x": 0.0,
        "y": 0.0,
        "width": 10.0,
        "length": 10.0,
        "area_sqft": 0.0,  # explicitly zero — must be rejected
        "wall_height": 9.0,
        "doors": [],
        "windows": [],
    }
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(rooms=[bad_room]))
    _assert_failed(state)


def test_negative_budget():
    """Negative budget_lkr must trigger a controlled failure."""
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING):
        state = cost_estimation_node(_make_state(budget_lkr=-1.0))
    _assert_failed(state)


# ===========================================================================
# Architectural guardrail — no direct DB access
# ===========================================================================


def test_no_direct_database_access_in_agent():
    """
    The agent module must NOT import any direct database library.
    Prices must be obtained solely through pricing_lookup_tool().
    """
    import app.services.cost_estimation_service as agent_module

    source = inspect.getsource(agent_module)
    forbidden = ["psycopg2", "psycopg", "asyncpg", "sqlalchemy", "aiopg", "databases"]
    for lib in forbidden:
        assert lib not in source, (
            f"Direct database import '{lib}' found in cost_estimation_service.py. "
            "All pricing data must be fetched via pricing_lookup_tool()."
        )


def test_pricing_obtained_via_tool():
    """
    Verify pricing_lookup_tool() is the sole entry point for pricing data.
    The agent must call it (mock records the call count).
    """
    with patch(PATCH_TARGET, return_value=STANDARD_PRICING) as mock_tool:
        cost_estimation_node(_make_state())

    mock_tool.assert_called_once()


def test_agent_requests_the_selected_region_and_quality_catalogue():
    state = _make_state()
    state.input_data.region = "Colombo"
    state.input_data.quality_level = "Premium"

    with patch(PATCH_TARGET, return_value=STANDARD_PRICING) as mock_tool:
        cost_estimation_node(state)

    mock_tool.assert_called_once_with(region="Colombo", quality_level="Premium")
