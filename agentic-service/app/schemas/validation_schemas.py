"""
Validation schemas for Component D — Validation/Safety Agent.
Provides strongly typed Pydantic models for rule-by-rule and overall validation results.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RuleValidationResult(BaseModel):
    """Result of an individual validation rule evaluation."""
    rule_name: str = Field(..., description="Unique identifier of the validation rule")
    passed: bool = Field(..., description="Whether the rule passed or failed")
    reason: str = Field(..., description="Human-readable explanation of the validation result")
    actual: Optional[Any] = Field(None, description="Actual value extracted from design/cost/terrain data")
    expected: Optional[Any] = Field(None, description="Expected value or acceptable range/threshold")


class ValidationResult(BaseModel):
    """Structured validation outcome produced by the Validation/Safety Agent."""
    passed: bool = Field(..., description="Overall validation status (True only if all rules pass)")
    rules: List[RuleValidationResult] = Field(default_factory=list, description="Detailed results for each rule")
    errors: List[str] = Field(default_factory=list, description="List of critical error messages or failure reasons")
    summary: str = Field("", description="Summary overview of the validation outcome")


class HousePlanValidationInput(BaseModel):
    """
    Standardized input payload for the Validation/Safety Agent.
    Can be constructed directly or extracted from WorkflowState.
    """
    land_size_perches: Optional[float] = Field(None, description="Land size in perches (1 perch = 272.25 sqft)")
    ground_coverage_sqft: Optional[float] = Field(None, description="Building footprint / ground coverage in sqft")
    terrain_type: Optional[str] = Field(None, description="Terrain type (e.g., flat, slope, rocky)")
    slope_estimate: Optional[str] = Field(None, description="Slope estimate (e.g., flat, moderate_slope, steep_slope)")
    foundation_type: Optional[str] = Field(None, description="Proposed foundation type (e.g., strip, raft, stepped_strip, pile)")
    budget_lkr: Optional[float] = Field(None, description="Client stated budget in LKR")
    estimated_cost_lkr: Optional[float] = Field(None, description="Total estimated construction cost in LKR")
    requested_bedrooms: Optional[int] = Field(None, description="Bedrooms requested by the client")
    actual_bedrooms: Optional[int] = Field(None, description="Bedrooms provided in the architectural design")
    requested_floors: Optional[int] = Field(None, description="Floors requested by the client")
    actual_floors: Optional[int] = Field(None, description="Floors provided in the architectural design")
    additional_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Any extra metadata")
