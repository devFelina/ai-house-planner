from pydantic import BaseModel, Field
from typing import List

class TerrainResult(BaseModel):
    terrain_type: str = Field(..., description="The type of terrain (e.g., hillside, flat, coastal)")
    slope_estimate: str = Field(..., description="Estimated slope (e.g., moderate, steep, flat)")
    notable_features: List[str] = Field(..., description="List of notable features extracted from the image")
