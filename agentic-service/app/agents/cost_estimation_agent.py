from app.schemas.workflow_state import WorkflowState
def cost_estimation_node(state: WorkflowState) -> WorkflowState:
    print(f"[Cost Estimation Agent] Estimating costs for workflow {state.workflow_id}...")
    
    if not state.design_result:
        state.status = "failed"
        return state
        
    area = state.design_result.get("total_built_up_area_sqft", 1000)
    rate_per_sqft = 15000  # LKR base rate logic
    estimated_total = area * rate_per_sqft
    
    state.cost_result = {
        "estimated_total_lkr": estimated_total,
        "rate_per_sqft": rate_per_sqft,
        "breakdown": {
            "materials": estimated_total * 0.6,
            "labor": estimated_total * 0.3,
            "contingency": estimated_total * 0.1
        }
    }
    
    state.current_agent = "validation"
    return state