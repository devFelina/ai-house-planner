from app.schemas.workflow_state import WorkflowState
def validation_node(state: WorkflowState) -> WorkflowState:
    print(f"[Validation Agent] Validating constraints for workflow {state.workflow_id}...")
    
    budget = state.input_data.budget_lkr
    estimated_cost = state.cost_result.get("estimated_total_lkr", 0) if state.cost_result else 0
    
    is_valid = True
    reason = "Design meets all budget and space constraints."
    
    if budget is not None and estimated_cost > budget * 1.15: # Allow 15% buffer flexibility
        is_valid = False
        reason = f"Estimated cost ({estimated_cost:,.2f} LKR) exceeds budget ({budget:,.2f} LKR)."
        
    state.validation_result = {
        "is_valid": is_valid,
        "reason": reason
    }
    
    state.status = "awaiting_approval" if is_valid else "rejected"
    state.current_agent = "rendering"
    return state