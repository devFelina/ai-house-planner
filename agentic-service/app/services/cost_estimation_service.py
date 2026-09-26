"""
Cost Estimation Service — LangGraph node (Component C).

Implements a fully deterministic cost calculation driven by:
  - Room geometry from state.design_result  (Component B output)
  - Live pricing from pricing_lookup_tool()  (ASP.NET pricing catalog)
  - Terrain multipliers from state.terrain_result (Component A output)
  - Project budget from state.input_data.budget_lkr

Formula
-------
  material_cost = Σ(room_area_sqft × material_unit_cost × terrain_multiplier)
  labour_cost   = material_cost × labour_rate_factor
  total_cost    = material_cost + labour_cost
  budget_delta_percent = (total_cost / budget_lkr) × 100 when a budget is supplied

No database access, no hardcoded rates, no fallback prices.
"""
import logging
from datetime import datetime, timezone

import requests

from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from app.cost.calculator import (
    FORMULA_VERSION,
    CostCalculationError,
    calculate_cost_lines,
)
from app.schemas.cost_result import CostResult
from app.schemas.pricing_data import PricingItem
from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.tools.pricing_lookup_tool import PricingLookupError, pricing_lookup_tool

logger = logging.getLogger(__name__)

# Terrain types the agent accepts.  "unknown" is explicitly unsupported.
_SUPPORTED_TERRAINS = frozenset({"flat", "hillside", "coastal"})

# Units that express a per-square-foot cost and are therefore compatible with the
# room-area multiplication formula.
_AREA_COMPATIBLE_UNITS = frozenset({"per_sqft", "sqft"})

# Units that a labour-factor record must carry for the value to be treated as a
# dimensionless multiplier (not an LKR/day figure).
_LABOUR_FACTOR_UNITS = frozenset({"factor", "ratio"})


# ---------------------------------------------------------------------------
# Public node
# ---------------------------------------------------------------------------


def cost_estimation_node(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node for deterministic cost estimation.

    On success  → populates state.cost_result and routes to 'validation'.
    On failure  → sets state.status = 'failed', state.current_agent = 'failed',
                  appends an ExecutionLogEntry, and returns without crashing.
    """
    print(f"[Cost Estimation Service] Starting for workflow {state.workflow_id} …")

    started_at = datetime.now(timezone.utc)
    try:
        result = _run_estimation(state)
        _persist_cost_estimate(state, result)
    except _CostEstimationFailure as exc:
        _record_run(state, "failed", started_at, failure_reason=str(exc))
        _persist_failure(state, str(exc))
        return _fail(state, str(exc))

    _record_run(state, "success", started_at, result=result)

    state.cost_result = result.model_dump()
    state.current_agent = "validation"
    budget_message = (
        f" ({result.budget_delta_percent:.2f}% of budget)"
        if result.budget_delta_percent is not None
        else " (no customer budget supplied)"
    )
    print(f"[Cost Estimation Service] Done — total {result.total_cost_lkr:,.2f} LKR{budget_message}.")
    return state


def _persist_cost_estimate(state: WorkflowState, result: CostResult) -> None:
    """Persist the successful estimate through the ASP.NET internal API."""
    endpoint = (
        f"{ASPNET_API_URL.rstrip('/')}/internal/workflows/"
        f"{state.workflow_id}/cost-estimate"
    )
    payload = {
        "materialCostLkr": result.material_cost_lkr,
        "labourCostLkr": result.labour_cost_lkr,
        "totalCostLkr": result.total_cost_lkr,
        "budgetDeltaPercent": result.budget_delta_percent,
        "pricingSnapshot": result.pricing_snapshot,
        "breakdown": [line.model_dump(mode="json") for line in result.breakdown],
        "formulaVersion": result.formula_version,
        "appliedAreaSqft": result.total_area_sqft,
        "terrainType": result.terrain_type,
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"X-Internal-API-Key": INTERNAL_API_KEY},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise _CostEstimationFailure(
            f"Could not persist the cost estimate: {type(exc).__name__}."
        ) from exc

    if not response.ok:
        raise _CostEstimationFailure(
            f"Cost estimate persistence returned HTTP {response.status_code}."
        )


def _record_run(state: WorkflowState, status: str, started_at: datetime,
                result: CostResult | None = None, failure_reason: str | None = None) -> None:
    endpoint = f"{ASPNET_API_URL.rstrip('/')}/internal/workflows/{state.workflow_id}/cost-estimation-runs"
    payload = {
        "status": status,
        "formulaVersion": result.formula_version if result else FORMULA_VERSION,
        "pricingRecordCount": len(result.pricing_snapshot) if result else 0,
        "appliedAreaSqft": result.total_area_sqft if result else None,
        "terrainType": result.terrain_type if result else None,
        "failureReason": failure_reason,
        "startedAt": started_at.isoformat(),
        "completedAt": datetime.now(timezone.utc).isoformat(),
    }
    try:
        requests.post(endpoint, json=payload, headers={"X-Internal-API-Key": INTERNAL_API_KEY}, timeout=10)
    except requests.RequestException:
        logger.warning("Could not persist cost estimation run audit", exc_info=True)


def _persist_failure(state: WorkflowState, reason: str) -> None:
    endpoint = f"{ASPNET_API_URL.rstrip('/')}/internal/workflows/{state.workflow_id}/status"
    try:
        requests.patch(endpoint, json={"status": "failed", "reason": reason},
                       headers={"X-Internal-API-Key": INTERNAL_API_KEY}, timeout=10)
    except requests.RequestException:
        logger.warning("Could not persist cost estimation failure", exc_info=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _CostEstimationFailure(Exception):
    """Controlled failure that aborts estimation without crashing the service."""


def _fail(state: WorkflowState, reason: str) -> WorkflowState:
    """Mark state as failed with a concise, actionable log entry."""
    print(f"[Cost Estimation Service] FAILED — {reason}")
    logger.error("[Cost Estimation Service] FAILED — %s", reason)
    state.status = "failed"
    state.current_agent = "failed"
    state.execution_log.append(
        ExecutionLogEntry(
            agent_name="CostEstimationAgent",
            action=f"Cost estimation failed: {reason}",
            tool_called="pricing_lookup_tool",
            result="failed",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
    )
    return state


def _run_estimation(state: WorkflowState) -> CostResult:
    """
    Core estimation logic.  Raises _CostEstimationFailure on any invalid input.
    """
    # ------------------------------------------------------------------
    # 1. Design data — rooms
    # ------------------------------------------------------------------
    if not state.design_result:
        raise _CostEstimationFailure(
            "Missing design_result: design agent must complete successfully before cost estimation."
        )

    rooms_raw = state.design_result.get("rooms")
    if not rooms_raw:
        raise _CostEstimationFailure(
            "design_result contains no rooms: cannot calculate material cost without room geometry."
        )

    room_areas: list[float] = []
    for idx, room in enumerate(rooms_raw):
        area = _extract_room_area(room, idx)
        room_areas.append(area)

    calculated_room_area = sum(room_areas)
    authoritative_area = state.design_result.get("total_built_up_area_sqft")
    try:
        total_area_sqft = float(authoritative_area) if authoritative_area is not None else calculated_room_area
    except (TypeError, ValueError):
        raise _CostEstimationFailure("Design total_built_up_area_sqft is not a valid number.")
    if total_area_sqft <= 0:
        raise _CostEstimationFailure("Design total_built_up_area_sqft must be greater than zero.")

    # ------------------------------------------------------------------
    # 2. Terrain — authoritative source is state.terrain_result
    # ------------------------------------------------------------------
    terrain_type = _resolve_terrain(state)

    # ------------------------------------------------------------------
    # 3. Pricing lookup
    # ------------------------------------------------------------------
    pricing_region, quality_level = _resolve_pricing_context(state)
    try:
        pricing_items: list[PricingItem] = pricing_lookup_tool(
            region=pricing_region,
            quality_level=quality_level,
        )
    except PricingLookupError as exc:
        raise _CostEstimationFailure(
            f"Pricing lookup failed; cannot proceed without live pricing data: {exc}"
        ) from exc

    try:
        breakdown, material_cost, labour_cost, total_cost = calculate_cost_lines(
            total_area_sqft, terrain_type, pricing_items
        )
    except CostCalculationError as exc:
        raise _CostEstimationFailure(str(exc)) from exc

    # ------------------------------------------------------------------
    # 9. Budget
    # ------------------------------------------------------------------
    budget_lkr = state.input_data.budget_lkr if state.input_data else None
    if budget_lkr is not None and budget_lkr < 0:
        raise _CostEstimationFailure(
            f"Invalid budget_lkr={budget_lkr!r}: budget cannot be negative."
        )

    budget_delta_percent = (total_cost / budget_lkr) * 100 if budget_lkr and budget_lkr > 0 else None

    # ------------------------------------------------------------------
    # 10. Build structured result
    # ------------------------------------------------------------------
    return CostResult(
        material_cost_lkr=round(material_cost, 2),
        labour_cost_lkr=round(labour_cost, 2),
        total_cost_lkr=round(total_cost, 2),
        budget_delta_percent=round(budget_delta_percent, 2) if budget_delta_percent is not None else None,
        terrain_type=terrain_type,
        room_count=len(room_areas),
        total_area_sqft=round(total_area_sqft, 2),
        pricing_region=pricing_region,
        quality_level=quality_level,
        pricing_snapshot=[item.model_dump(by_alias=True, mode="json") for item in pricing_items],
        formula_version=FORMULA_VERSION,
        breakdown=breakdown,
    )


def _resolve_pricing_context(state: WorkflowState) -> tuple[str, str]:
    """Resolve optional catalogue dimensions without changing the cost formula."""
    input_data = state.input_data
    preferences = input_data.preferences if input_data and input_data.preferences else {}
    region = (
        (input_data.region if input_data else None)
        or preferences.get("region")
        or "Sri Lanka"
    )
    quality = (
        (input_data.quality_level if input_data else None)
        or preferences.get("quality_level")
        or preferences.get("qualityLevel")
        or "Standard"
    )
    quality_normalized = str(quality).strip().title()
    if quality_normalized not in {"Basic", "Standard", "Premium", "Luxury"}:
        raise _CostEstimationFailure(
            f"Unsupported pricing quality level '{quality}'. Accepted values are Basic, Standard, Premium, and Luxury."
        )
    return str(region).strip() or "Sri Lanka", quality_normalized


# ---------------------------------------------------------------------------
# Room area extraction
# ---------------------------------------------------------------------------


def _extract_room_area(room: dict, idx: int) -> float:
    """
    Return the usable area (sqft) for a single room dict.

    Preference order:
      1. Explicit 'area_sqft' field (if present and positive).
      2. Computed width × length (both must be present and positive).

    Raises _CostEstimationFailure for any invalid/missing geometry.
    """
    room_label = room.get("room_type", room.get("name", f"room[{idx}]"))

    area = room.get("area_sqft")
    if area is not None:
        try:
            area = float(area)
        except (TypeError, ValueError):
            raise _CostEstimationFailure(
                f"Room '{room_label}': area_sqft={area!r} is not a valid number."
            )
        if area <= 0:
            raise _CostEstimationFailure(
                f"Room '{room_label}': area_sqft={area} is zero or negative; "
                "cannot use this room for cost calculation."
            )
        return area

    # Fall back to width × length
    width = room.get("width")
    length = room.get("length")
    if width is None or length is None:
        raise _CostEstimationFailure(
            f"Room '{room_label}': neither area_sqft nor width/length dimensions are present."
        )
    try:
        width = float(width)
        length = float(length)
    except (TypeError, ValueError):
        raise _CostEstimationFailure(
            f"Room '{room_label}': width={width!r} or length={length!r} is not a valid number."
        )
    if width <= 0 or length <= 0:
        raise _CostEstimationFailure(
            f"Room '{room_label}': width={width} and length={length} must both be positive; "
            "zero or negative dimensions are rejected."
        )
    return width * length


# ---------------------------------------------------------------------------
# Terrain resolution
# ---------------------------------------------------------------------------


def _resolve_terrain(state: WorkflowState) -> str:
    """
    Extract terrain_type from state.terrain_result.

    state.terrain_result is stored as a plain dict (model_dump() in the land agent).
    Raises _CostEstimationFailure if missing or unsupported.
    """
    if not state.terrain_result:
        raise _CostEstimationFailure(
            "state.terrain_result is None: land analysis agent must complete before cost estimation. "
            "Cannot select terrain multiplier without a classified terrain type."
        )

    terrain_type = state.terrain_result.get("terrain_type")
    if not terrain_type:
        raise _CostEstimationFailure(
            "state.terrain_result is present but 'terrain_type' key is missing or empty."
        )

    terrain_norm = str(terrain_type).strip().lower()
    if terrain_norm not in _SUPPORTED_TERRAINS:
        raise _CostEstimationFailure(
            f"Unsupported terrain_type='{terrain_type}'. "
            f"Accepted values: {sorted(_SUPPORTED_TERRAINS)}. "
            "Update the land analysis result before running cost estimation."
        )

    return terrain_norm


# ---------------------------------------------------------------------------
# Labour factor resolution
# ---------------------------------------------------------------------------


def _resolve_labour_factor(pricing_items: list[PricingItem]) -> float:
    """
    Find exactly one labour pricing item whose unit is 'factor' or 'ratio'.

    Returns the dimensionless multiplier value.
    Raises _CostEstimationFailure if the result is ambiguous or missing.
    """
    labour_items = [
        item for item in pricing_items if item.category.strip().lower() == "labour"
    ]

    factor_items = [
        item
        for item in labour_items
        if item.unit.strip().lower().replace(" ", "_").replace("-", "_")
        in _LABOUR_FACTOR_UNITS
    ]

    if not factor_items:
        non_factor_units = [i.unit for i in labour_items]
        raise _CostEstimationFailure(
            f"No labour pricing item with a dimensionless unit ({sorted(_LABOUR_FACTOR_UNITS)}) "
            f"found. Labour items present have units: {non_factor_units}. "
            "A single 'factor' or 'ratio' record is required to compute labour cost."
        )

    if len(factor_items) > 1:
        names = [i.item_name for i in factor_items]
        raise _CostEstimationFailure(
            f"Ambiguous labour factor: {len(factor_items)} items qualify ({names}). "
            "Exactly one labour-factor pricing record is required."
        )

    factor_item = factor_items[0]
    factor_value = factor_item.unit_cost_lkr
    if factor_value <= 0:
        raise _CostEstimationFailure(
            f"Labour factor item '{factor_item.item_name}' has unit_cost_lkr={factor_value}, "
            "which is not a positive multiplier."
        )

    return factor_value


# ---------------------------------------------------------------------------
# Terrain multiplier value access (PricingItem is a Pydantic model)
# ---------------------------------------------------------------------------


def _terrain_multiplier_value(item: PricingItem, terrain_type: str) -> float:
    """
    Return the terrain multiplier for the given terrain_type from a PricingItem.

    item.terrain_multiplier is a TerrainMultiplier Pydantic model instance,
    so attributes are accessed directly (not via dict subscript).
    """
    tm = item.terrain_multiplier  # TerrainMultiplier instance
    if terrain_type == "flat":
        return tm.flat
    elif terrain_type == "hillside":
        return tm.hillside
    elif terrain_type == "coastal":
        return tm.coastal
    else:
        # Should never reach here because terrain was validated before this call
        raise _CostEstimationFailure(
            f"Internal error: terrain_type='{terrain_type}' reached multiplier lookup "
            "but was not caught by earlier validation."
        )


def _get_terrain_multiplier_for_items(
    material_items: list[PricingItem], terrain_type: str
) -> float:
    """
    Not used in the summation loop (each item has its own multiplier),
    but kept as a sanity-check helper for tests that want a single scalar.
    Returns the terrain multiplier of the first material item.
    """
    return _terrain_multiplier_value(material_items[0], terrain_type)
