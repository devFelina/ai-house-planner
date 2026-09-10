from pydantic import BaseModel
from typing import Optional,List,Literal,Dict,Any
from uuid import UUID

class ExecutionLogEntry(BaseModel):
    agent_name:str
    action:str
    tool_called:Optional[str]=None
    duration_ms:Optional[int]=None
    result:str
    created_at_utc:str

class CoordinatorInput(BaseModel):
    submission_id:UUID
    budget_lkr:float
    land_size_perches:float
    manual_terrain_type:Optional[str]=None
    preferences:Dict[str,Any]

class WorkflowState(BaseModel):
    workflow_id:UUID
    status:Literal["running","awaiting_approval","approved","rejected","failed"]="running"

    #Agent results
    terrain_result:Optional[Dict[str,Any]]=None
    design_result:Optional[Dict[str,Any]]=None
    cost_result:Optional[Dict[str,Any]]=None
    validation_result:Optional[Dict[str,Any]]=None

    approval_status:Literal["not_requested","pending","approved","rejected","revision_requested"]="not_requested"
    retry_count:int=0
    execution_log:List[ExecutionLogEntry]=[]

    #Internal routing data
    input_data:Optional[CoordinatorInput]=None
    current_agent:str="coordinator"