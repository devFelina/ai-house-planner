from pydantic import BaseModel
from typing import List

class TerrainResult(BaseModel):
    terrain_type: str
    slope_estimate: str
    notable_features: List[str]

def vision_classify_tool(photo_url: str) -> TerrainResult:
    """Mock vision classify tool."""
    return TerrainResult(
        terrain_type="flat",
        slope_estimate="unknown",
        notable_features=["mocked_vision_result"]
    )
