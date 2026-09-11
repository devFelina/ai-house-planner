from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Door(BaseModel):
    wall:Literal["north","south","east","west"]
    offset:float
    width:float

class Window(BaseModel):
    wall:Literal["north","south","east","west"]
    offset:float
    width:float
    
class Room(BaseModel):
    room_id:str=Field(description="Unique UUID for the room")
    room_type:str = Field(description="e.g., living_room, kitchen, bedroom")
    floor:int
    x:float
    y:float
    width:float
    length:float
    wall_height:float=9.0
    doors:List[Door]=[]
    windows:List[Window]=[]

class DesignResult(BaseModel):
    design_id: str
    floor_count: int
    total_built_up_area_sqft: float
    foundation_type:str=Field(description="Must match the terrain(e.g., terraced for hillside, slab for flat)")
    rooms: List[Room]