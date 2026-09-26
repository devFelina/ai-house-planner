"""
Structured result schema for the Cost Estimation Service (Component C).

Stored in WorkflowState.cost_result as a plain dict (via .model_dump()) so that
the WorkflowState type annotation (Dict[str, Any]) is preserved without modification.
"""
from typing import Any

from pydantic import BaseModel, Field


class CostBreakdownLine(BaseModel):
    item_name: str
    cost_head: str
    category: str
    unit_cost_lkr: float
    unit: str
    applied_quantity: float
    quantity_unit: str
    terrain_multiplier: float
    amount_lkr: float
    share_percent: float = 0
    provider: str | None = None
    source_reference: str | None = None
    pricing_updated_at: str | None = None


class CostResult(BaseModel):
    """
    Deterministic cost breakdown produced by the Cost Estimation Service.

    All monetary values are in Sri Lankan Rupees (LKR).
    budget_delta_percent expresses total_cost as a percentage of the submitted budget
    (100 = exactly on budget, >100 = over budget, <100 = under budget).
    """

    material_cost_lkr: float = Field(
        ...,
        description="Sum of (room_area × material_unit_cost × terrain_multiplier) across all rooms and material items.",
    )
    labour_cost_lkr: float = Field(
        ...,
        description="material_cost_lkr × labour_rate_factor.",
    )
    total_cost_lkr: float = Field(
        ...,
        description="material_cost_lkr + labour_cost_lkr.",
    )
    budget_delta_percent: float | None = Field(
        None,
        description="(total_cost_lkr / budget_lkr) × 100 when a positive budget is supplied; otherwise null.",
    )
    terrain_type: str = Field(
        ...,
        description="Terrain type used for multiplier selection (flat / hillside / coastal).",
    )
    room_count: int = Field(
        ...,
        ge=1,
        description="Number of rooms included in the calculation.",
    )
    total_area_sqft: float = Field(
        ...,
        gt=0,
        description="Sum of all room areas used in the calculation.",
    )
    pricing_region: str = "Sri Lanka"
    quality_level: str = "Standard"
    pricing_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    formula_version: str = "category-area-v1"
    breakdown: list[CostBreakdownLine] = Field(default_factory=list)
