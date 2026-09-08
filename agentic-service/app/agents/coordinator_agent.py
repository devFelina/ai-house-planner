import requests
from typing import Dict, Any
from app.schemas.workflow_state import WorkflowState

def coordinator_node(state:WorkflowState)->WorkflowState:
    """
    The Coordinator Agent acts as the entry point and air traffic controller.
    It evaluates teh input data and determines the execution plan.
    """
    input_data=state.input_data

    #Log the start of the workflow 
    print(f"[Coordinator Agent] Processing submission:{input_data.submission_id}")

    #Decision Logic:Do we need Land Analysis?
    if input_data.manual_terrain_type:
        #If client provides manual terain, skip Land Analysis
        next_agent="design"
        action_log=f"Routed to Design. Manual terrain provided:{input_data.manual_terrain_type}"

        #Pre-fill the terrain result for the Design agent
        state.terrain_result={
            "terrain_type":input_data.manual_terrain_type,
            "slope_estimate":"flat",
            "notable_features":[]
        }
    else:
        #No manual terrain, route to Land Analysis to process the land photo
        next_agent="land_analysis"
        action_log="Routed to Land Analysis. Photo requires processing."

        #Update routing state
        state.current_agent=next_agent

        try:
            headers={"X-Internal-API-Key":"shared-internal-secret"}
            update_payload={
                "AgentName":"Coordinator",
                "Action":action_log,
                "Result":"success"
            }
            requests.patch(
                f"http://aspnet-api:8080/api/v1/internal/workflows/{state.workflow_id}/state",
                json=update_payload,
                headers=headers,
                timeout=5
            )

        except Exception as e:
            print(f"Failed to callback ASP.NET Core:{e}")
        return state