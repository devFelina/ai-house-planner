"""
Validation / Safety Agent (Component D — Stage 1)
=================================================

The Validation/Safety Agent is a deterministic gatekeeper in the AI House Planner system.
It verifies whether the architectural design, cost estimates, and terrain data satisfy
established safety thresholds, project constraints, budget limits, and client preferences.

Key Rules:
1. Building / Land Ground Coverage (<= 65% standard threshold)
2. Terrain & Foundation Compatibility (Deterministic mapping table)
3. Budget Tolerance (<= Budget + 10% tolerance)
4. Client Requirement Match (Bedrooms and Floors compliance)

Author: Member 4 (Component D)
"""

from typing import Any, Dict, List, Optional, Union
from app.schemas.validation_schemas import (
    HousePlanValidationInput,
    RuleValidationResult,
    ValidationResult,
)

# ---------------------------------------------------------------------------
# Business Rule Constants & Configuration Defaults
# ---------------------------------------------------------------------------
# Standard conversion: 1 Perch = 272.25 Square Feet (Sri Lankan Land Measurement)
PERCH_TO_SQFT: float = 272.25

# Maximum allowable building ground footprint ratio (Default: 65% of total land area)
DEFAULT_MAX_COVERAGE_RATIO: float = 0.65

# Allowable budget tolerance buffer (Default: 10% above stated budget)
DEFAULT_BUDGET_TOLERANCE_RATIO: float = 0.10

# Deterministic terrain & slope to supported foundation types lookup table
TERRAIN_FOUNDATION_COMPATIBILITY_MAP: Dict[str, List[str]] = {
    "flat": ["strip", "raft", "pad", "slab", "shallow_strip", "isolated_pad"],
    "slight_slope": ["strip", "stepped_strip", "raft", "pad", "shallow_strip"],
    "moderate_slope": ["stepped_strip", "raft", "pier", "pile", "caisson"],
    "steep_slope": ["stepped_strip", "pile", "pier", "retaining_wall_integrated", "micropile", "caisson"],
    "rocky": ["pad", "strip", "anchor_pile", "rock_anchor", "isolated_pad"],
    "marshy": ["pile", "raft", "friction_pile", "screw_pile"],
    "clay": ["raft", "pile", "under_reamed_pile", "strip"],
    "sandy": ["raft", "strip", "compaction_pile", "pad"],
}


def _normalize_string(val: Optional[str]) -> str:
    """Normalizes strings for reliable dictionary key comparisons."""
    if not val:
        return ""
    return val.strip().lower().replace("-", "_").replace(" ", "_")


# ---------------------------------------------------------------------------
# Rule 1: Building / Land Ground Coverage
# ---------------------------------------------------------------------------
def validate_coverage(
    land_size_perches: Optional[float],
    ground_coverage_sqft: Optional[float],
    max_coverage_ratio: float = DEFAULT_MAX_COVERAGE_RATIO,
) -> RuleValidationResult:
    """
    Validates that the proposed building footprint does not exceed the maximum allowable
    percentage of the total land area.

    Formula:
      land_area_sqft = land_size_perches * 272.25
      coverage_ratio = ground_coverage_sqft / land_area_sqft
    """
    rule_name = "coverage"

    if land_size_perches is None or ground_coverage_sqft is None:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason="Missing required inputs: land_size_perches and ground_coverage_sqft must be provided.",
            actual=f"land_size={land_size_perches}, ground_coverage={ground_coverage_sqft}",
            expected=f"Coverage ratio <= {max_coverage_ratio:.1%}",
        )

    if land_size_perches <= 0:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason=f"Invalid land size: {land_size_perches} perches. Land size must be greater than zero.",
            actual=f"land_size={land_size_perches} perches",
            expected="land_size > 0 perches",
        )

    if ground_coverage_sqft < 0:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason=f"Invalid ground coverage: {ground_coverage_sqft} sqft. Ground coverage cannot be negative.",
            actual=f"ground_coverage={ground_coverage_sqft} sqft",
            expected="ground_coverage >= 0 sqft",
        )

    land_area_sqft = land_size_perches * PERCH_TO_SQFT
    coverage_ratio = ground_coverage_sqft / land_area_sqft
    max_allowed_sqft = land_area_sqft * max_coverage_ratio

    # Float comparison with slight tolerance for numerical precision
    is_passed = coverage_ratio <= (max_coverage_ratio + 1e-6)

    if is_passed:
        reason = (
            f"Ground coverage is {coverage_ratio:.1%} ({ground_coverage_sqft:,.1f} sqft), "
            f"which is within the maximum allowable limit of {max_coverage_ratio:.1%} "
            f"({max_allowed_sqft:,.1f} sqft on {land_size_perches} perches / {land_area_sqft:,.1f} sqft)."
        )
    else:
        reason = (
            f"Ground coverage of {coverage_ratio:.1%} ({ground_coverage_sqft:,.1f} sqft) "
            f"exceeds the maximum allowable limit of {max_coverage_ratio:.1%} "
            f"({max_allowed_sqft:,.1f} sqft on {land_size_perches} perches / {land_area_sqft:,.1f} sqft)."
        )

    return RuleValidationResult(
        rule_name=rule_name,
        passed=is_passed,
        reason=reason,
        actual=f"{coverage_ratio * 100:.2f}% ({ground_coverage_sqft:,.1f} sqft)",
        expected=f"<= {max_coverage_ratio * 100:.2f}% ({max_allowed_sqft:,.1f} sqft)",
    )


# ---------------------------------------------------------------------------
# Rule 2: Terrain & Foundation Compatibility
# ---------------------------------------------------------------------------
def validate_terrain_foundation(
    terrain_type: Optional[str],
    slope_estimate: Optional[str],
    foundation_type: Optional[str],
) -> RuleValidationResult:
    """
    Validates that the selected architectural foundation is physically compatible
    with the terrain slope or soil profile according to the engineering lookup table.
    """
    rule_name = "terrain_foundation"

    if not foundation_type:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason="Missing foundation type: design must specify a foundation type.",
            actual="foundation_type=None",
            expected="A valid foundation type (e.g., strip, raft, stepped_strip, pile)",
        )

    # Determine the primary terrain key: prioritize slope_estimate if available, else terrain_type
    normalized_slope = _normalize_string(slope_estimate)
    normalized_terrain = _normalize_string(terrain_type)
    normalized_foundation = _normalize_string(foundation_type)

    # Resolve terrain key against known compatibility profiles
    terrain_key = ""
    if normalized_slope in TERRAIN_FOUNDATION_COMPATIBILITY_MAP:
        terrain_key = normalized_slope
    elif normalized_terrain in TERRAIN_FOUNDATION_COMPATIBILITY_MAP:
        terrain_key = normalized_terrain
    elif normalized_slope == "flat" or normalized_terrain == "flat":
        terrain_key = "flat"
    elif "steep" in normalized_slope or "steep" in normalized_terrain:
        terrain_key = "steep_slope"
    elif "moderate" in normalized_slope or "slope" in normalized_terrain:
        terrain_key = "moderate_slope"
    elif "slight" in normalized_slope:
        terrain_key = "slight_slope"

    if not terrain_key:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason=f"Unknown or unprovided terrain characteristics (terrain='{terrain_type}', slope='{slope_estimate}').",
            actual=f"terrain='{terrain_type}', slope='{slope_estimate}', foundation='{foundation_type}'",
            expected=f"Known terrain types: {', '.join(TERRAIN_FOUNDATION_COMPATIBILITY_MAP.keys())}",
        )

    allowed_foundations = TERRAIN_FOUNDATION_COMPATIBILITY_MAP.get(terrain_key, [])

    # Check exact normalized match against allowed foundations for this terrain profile
    is_compatible = normalized_foundation in allowed_foundations

    if is_compatible:
        reason = (
            f"Foundation type '{foundation_type}' is compatible with '{terrain_key}' terrain conditions."
        )
    else:
        reason = (
            f"Foundation type '{foundation_type}' is incompatible with '{terrain_key}' terrain conditions. "
            f"Supported foundation types for this terrain are: {', '.join(allowed_foundations)}."
        )

    return RuleValidationResult(
        rule_name=rule_name,
        passed=is_compatible,
        reason=reason,
        actual=f"foundation='{foundation_type}' on terrain='{terrain_key}'",
        expected=f"Supported foundations: {', '.join(allowed_foundations)}",
    )


# ---------------------------------------------------------------------------
# Rule 3: Budget Tolerance
# ---------------------------------------------------------------------------
def validate_budget(
    budget_lkr: Optional[float],
    estimated_cost_lkr: Optional[float],
    tolerance_ratio: float = DEFAULT_BUDGET_TOLERANCE_RATIO,
) -> RuleValidationResult:
    """
    Validates that the total estimated construction cost does not exceed the
    client's stated budget plus the allowable tolerance threshold (default +10%).
    """
    rule_name = "budget"

    if budget_lkr is None or estimated_cost_lkr is None:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason="Missing budget or estimated cost inputs.",
            actual=f"budget={budget_lkr}, estimated_cost={estimated_cost_lkr}",
            expected=f"Estimated cost <= Budget + {tolerance_ratio:.1%}",
        )

    if budget_lkr <= 0:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason=f"Invalid client budget: LKR {budget_lkr:,.2f}. Budget must be greater than zero.",
            actual=f"budget=LKR {budget_lkr:,.2f}",
            expected="budget > 0",
        )

    if estimated_cost_lkr < 0:
        return RuleValidationResult(
            rule_name=rule_name,
            passed=False,
            reason=f"Invalid estimated cost: LKR {estimated_cost_lkr:,.2f}. Cost cannot be negative.",
            actual=f"estimated_cost=LKR {estimated_cost_lkr:,.2f}",
            expected="estimated_cost >= 0",
        )

    max_allowed_cost = budget_lkr * (1.0 + tolerance_ratio)
    is_passed = estimated_cost_lkr <= (max_allowed_cost + 1e-2)
    variance_lkr = estimated_cost_lkr - budget_lkr
    variance_pct = (variance_lkr / budget_lkr) * 100.0

    if is_passed:
        if variance_lkr <= 0:
            reason = (
                f"Estimated cost of LKR {estimated_cost_lkr:,.2f} is under the budget of LKR {budget_lkr:,.2f} "
                f"(Savings: LKR {abs(variance_lkr):,.2f})."
            )
        else:
            reason = (
                f"Estimated cost of LKR {estimated_cost_lkr:,.2f} exceeds base budget (LKR {budget_lkr:,.2f}) by "
                f"{variance_pct:.1f}%, but remains within the allowable {tolerance_ratio:.1%} tolerance "
                f"(Max allowed: LKR {max_allowed_cost:,.2f})."
            )
    else:
        reason = (
            f"Estimated cost of LKR {estimated_cost_lkr:,.2f} exceeds the client budget of LKR {budget_lkr:,.2f} "
            f"by {variance_pct:.1f}%, surpassing the maximum allowable {tolerance_ratio:.1%} tolerance "
            f"limit of LKR {max_allowed_cost:,.2f} (Excess: LKR {estimated_cost_lkr - max_allowed_cost:,.2f})."
        )

    return RuleValidationResult(
        rule_name=rule_name,
        passed=is_passed,
        reason=reason,
        actual=f"LKR {estimated_cost_lkr:,.2f} ({variance_pct:+.1f}% vs budget)",
        expected=f"<= LKR {max_allowed_cost:,.2f} (Budget: LKR {budget_lkr:,.2f} + {tolerance_ratio:.1%})",
    )


# ---------------------------------------------------------------------------
# Rule 4: Client Requirement Match
# ---------------------------------------------------------------------------
def validate_preferences(
    requested_bedrooms: Optional[int],
    actual_bedrooms: Optional[int],
    requested_floors: Optional[int],
    actual_floors: Optional[int],
) -> RuleValidationResult:
    """
    Validates that the design meets the client's mandatory bedroom count and floor count preferences.
    If a preference was not specified (None), it is considered satisfied.
    """
    rule_name = "preferences"
    failures: List[str] = []

    # Validate Bedrooms
    if requested_bedrooms is not None:
        if actual_bedrooms is None:
            failures.append(f"Design output missing bedroom count (requested: {requested_bedrooms}).")
        elif actual_bedrooms != requested_bedrooms:
            failures.append(
                f"Bedroom count mismatch: client requested {requested_bedrooms} bedroom(s), but design provides {actual_bedrooms}."
            )

    # Validate Floors
    if requested_floors is not None:
        if actual_floors is None:
            failures.append(f"Design output missing floor count (requested: {requested_floors}).")
        elif actual_floors != requested_floors:
            failures.append(
                f"Floor count mismatch: client requested {requested_floors} floor(s), but design provides {actual_floors}."
            )

    is_passed = len(failures) == 0

    if is_passed:
        reason = (
            f"All specified client preferences matched successfully "
            f"(Bedrooms: {actual_bedrooms if actual_bedrooms is not None else 'N/A'}, "
            f"Floors: {actual_floors if actual_floors is not None else 'N/A'})."
        )
    else:
        reason = "; ".join(failures)

    return RuleValidationResult(
        rule_name=rule_name,
        passed=is_passed,
        reason=reason,
        actual=f"Bedrooms={actual_bedrooms}, Floors={actual_floors}",
        expected=f"Bedrooms={requested_bedrooms}, Floors={requested_floors}",
    )


# ---------------------------------------------------------------------------
# State Extraction Adapter
# ---------------------------------------------------------------------------
def extract_validation_input_from_state(state: Any) -> HousePlanValidationInput:
    """
    Adapter function to extract validation parameters from either:
    1. A HousePlanValidationInput instance
    2. A WorkflowState Pydantic model
    3. A raw dictionary containing agent outputs
    """
    if isinstance(state, HousePlanValidationInput):
        return state

    # If it is a Pydantic model with model_dump or dict
    state_dict: Dict[str, Any] = {}
    if hasattr(state, "model_dump"):
        state_dict = state.model_dump()
    elif hasattr(state, "dict"):
        state_dict = state.dict()
    elif isinstance(state, dict):
        state_dict = state
    else:
        # Generic object attribute access
        state_dict = {k: getattr(state, k, None) for k in dir(state) if not k.startswith("_")}

    # Extract input data (from input_data or top-level)
    input_data = state_dict.get("input_data") or {}
    if not isinstance(input_data, dict) and hasattr(input_data, "model_dump"):
        input_data = input_data.model_dump()
    elif not isinstance(input_data, dict):
        input_data = {}

    preferences = input_data.get("preferences") or state_dict.get("preferences") or {}
    if not isinstance(preferences, dict) and hasattr(preferences, "model_dump"):
        preferences = preferences.model_dump()
    elif not isinstance(preferences, dict):
        preferences = {}

    terrain_result = state_dict.get("terrain_result") or {}
    design_result = state_dict.get("design_result") or {}
    cost_result = state_dict.get("cost_result") or {}

    # Extract fields with safe fallbacks
    land_size = (
        input_data.get("land_size_perches")
        or state_dict.get("land_size_perches")
    )
    budget = (
        input_data.get("budget_lkr")
        or state_dict.get("budget_lkr")
    )
    manual_terrain = (
        input_data.get("manual_terrain_type")
        or state_dict.get("manual_terrain_type")
    )

    # Terrain attributes
    terrain_type = terrain_result.get("terrain_type") or manual_terrain or state_dict.get("terrain_type")
    slope_estimate = terrain_result.get("slope_estimate") or state_dict.get("slope_estimate")

    # Design attributes
    ground_coverage = (
        design_result.get("ground_coverage_sqft")
        or design_result.get("footprint_sqft")
        or state_dict.get("ground_coverage_sqft")
    )
    foundation_type = (
        design_result.get("foundation_type")
        or state_dict.get("foundation_type")
    )
    actual_bedrooms = (
        design_result.get("bedrooms")
        or design_result.get("bedroom_count")
        or state_dict.get("actual_bedrooms")
    )
    actual_floors = (
        design_result.get("floors")
        or design_result.get("floor_count")
        or state_dict.get("actual_floors")
    )

    # Cost attributes
    estimated_cost = (
        cost_result.get("total_estimated_cost_lkr")
        or cost_result.get("estimated_cost_lkr")
        or cost_result.get("total_cost")
        or state_dict.get("estimated_cost_lkr")
    )

    # Preference attributes
    requested_bedrooms = (
        preferences.get("preferred_bedrooms")
        or preferences.get("bedrooms")
        or input_data.get("preferred_bedrooms")
        or state_dict.get("requested_bedrooms")
    )
    requested_floors = (
        preferences.get("preferred_floors")
        or preferences.get("floors")
        or input_data.get("preferred_floors")
        or state_dict.get("requested_floors")
    )

    return HousePlanValidationInput(
        land_size_perches=float(land_size) if land_size is not None else None,
        ground_coverage_sqft=float(ground_coverage) if ground_coverage is not None else None,
        terrain_type=terrain_type,
        slope_estimate=slope_estimate,
        foundation_type=foundation_type,
        budget_lkr=float(budget) if budget is not None else None,
        estimated_cost_lkr=float(estimated_cost) if estimated_cost is not None else None,
        requested_bedrooms=int(requested_bedrooms) if requested_bedrooms is not None else None,
        actual_bedrooms=int(actual_bedrooms) if actual_bedrooms is not None else None,
        requested_floors=int(requested_floors) if requested_floors is not None else None,
        actual_floors=int(actual_floors) if actual_floors is not None else None,
    )


# ---------------------------------------------------------------------------
# Core Public Validation Function & Agent Interface
# ---------------------------------------------------------------------------
def validate_house_plan(
    data: Union[HousePlanValidationInput, Any],
    max_coverage_ratio: float = DEFAULT_MAX_COVERAGE_RATIO,
    budget_tolerance_ratio: float = DEFAULT_BUDGET_TOLERANCE_RATIO,
) -> ValidationResult:
    """
    Main public entrypoint for the Validation/Safety Agent.
    Evaluates all 4 deterministic safety & compliance rules and returns a structured ValidationResult.

    Args:
        data: HousePlanValidationInput, WorkflowState, or raw state dictionary.
        max_coverage_ratio: Maximum allowed ground coverage percentage (default 0.65).
        budget_tolerance_ratio: Maximum allowed budget overrun percentage (default 0.10).

    Returns:
        ValidationResult: Contains overall passed status, list of RuleValidationResults, and errors.
    """
    # 1. Normalize input using the state adapter
    val_input = extract_validation_input_from_state(data)

    # 2. Evaluate all 4 deterministic rules
    rule_results: List[RuleValidationResult] = [
        validate_coverage(
            land_size_perches=val_input.land_size_perches,
            ground_coverage_sqft=val_input.ground_coverage_sqft,
            max_coverage_ratio=max_coverage_ratio,
        ),
        validate_terrain_foundation(
            terrain_type=val_input.terrain_type,
            slope_estimate=val_input.slope_estimate,
            foundation_type=val_input.foundation_type,
        ),
        validate_budget(
            budget_lkr=val_input.budget_lkr,
            estimated_cost_lkr=val_input.estimated_cost_lkr,
            tolerance_ratio=budget_tolerance_ratio,
        ),
        validate_preferences(
            requested_bedrooms=val_input.requested_bedrooms,
            actual_bedrooms=val_input.actual_bedrooms,
            requested_floors=val_input.requested_floors,
            actual_floors=val_input.actual_floors,
        ),
    ]

    # 3. Determine overall pass/fail status
    overall_passed = all(r.passed for r in rule_results)
    errors = [r.reason for r in rule_results if not r.passed]

    # 4. Generate human-readable summary
    if overall_passed:
        summary = "Validation PASSED: Proposal satisfies all safety, land coverage, budget, and preference rules."
    else:
        summary = f"Validation FAILED: {len(errors)} rule(s) failed compliance verification."

    return ValidationResult(
        passed=overall_passed,
        rules=rule_results,
        errors=errors,
        summary=summary,
    )


class ValidationAgent:
    """
    Object-oriented wrapper for the Validation/Safety Agent.
    Provides encapsulated validation functionality with configurable thresholds.
    """

    def __init__(
        self,
        max_coverage_ratio: float = DEFAULT_MAX_COVERAGE_RATIO,
        budget_tolerance_ratio: float = DEFAULT_BUDGET_TOLERANCE_RATIO,
    ):
        self.max_coverage_ratio = max_coverage_ratio
        self.budget_tolerance_ratio = budget_tolerance_ratio

    def validate(self, data: Union[HousePlanValidationInput, Any]) -> ValidationResult:
        """Executes the validation pipeline on the given input."""
        return validate_house_plan(
            data=data,
            max_coverage_ratio=self.max_coverage_ratio,
            budget_tolerance_ratio=self.budget_tolerance_ratio,
        )
