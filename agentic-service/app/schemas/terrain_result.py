from pydantic import BaseModel, Field
from typing import List, Literal


class TerrainResult(BaseModel):
    """
    Structured output from the Land Analysis Agent.
    All values are constrained to controlled enums to prevent LLM hallucination.
    """
    terrain_type: Literal["flat", "hillside", "coastal", "unknown"] = Field(
        ..., description="Classified terrain type"
    )
    slope_estimate: Literal["flat", "gentle", "moderate", "steep", "unknown"] = Field(
        ..., description="Estimated slope severity"
    )
    notable_features: List[str] = Field(
        default_factory=list,
        description="Notable features observed (e.g., tree_cover_north, retaining_wall)"
    )
