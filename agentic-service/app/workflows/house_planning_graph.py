from langgraph.graph import StateGraph, END
from app.schemas.workflow_state import WorkflowState
from app.agents.coordinator_agent import coordinator_node
from app.agents.validation_agent import validate_house_plan

# Maximum allowed revision/retry attempts upon validation failure
MAX_VALIDATION_RETRIES = 3

# Mock implementation for the upstream agents
def land_analysis_node(state: WorkflowState):
    state.current_agent = "design"
    return state

def design_node(state: WorkflowState):
    state.current_agent = "cost_estimation"
    return state

def cost_estimation_node(state: WorkflowState):
    state.current_agent = "validation"
    return state

# Validation node: executes deterministic validation and manages revision/approval transitions
def validation_node(state: WorkflowState) -> WorkflowState:
    """
    Executes deterministic safety and compliance validation on the house planning proposal.
    Persists structured validation outcome into state and manages retry/approval state.
    """
    val_result = validate_house_plan(state)
    state.validation_result = val_result.model_dump()

    if val_result.passed:
        state.status = "awaiting_approval"
        state.approval_status = "pending"
        state.current_agent = "approval"
    else:
        if state.retry_count < MAX_VALIDATION_RETRIES:
            state.retry_count += 1
            state.current_agent = "design"
        else:
            state.status = "failed"
            state.current_agent = "failed"

    return state

def route_from_coordinator(state: WorkflowState) -> str:
    """Conditional edge router from the Coordinator"""
    if state.current_agent in ["land_analysis", "design"]:
        return state.current_agent
    if state.input_data and state.input_data.manual_terrain_type:
        return "design"
    return "land_analysis"

def route_from_validation(state: WorkflowState) -> str:
    """Conditional edge router from the Validation Agent based on pass/fail and retry limit"""
    if state.status == "awaiting_approval":
        return "awaiting_approval"
    elif state.current_agent == "design":
        return "revision_to_design"
    else:
        return "failed"

# Initialize the State Graph
workflow = StateGraph(WorkflowState)

# Add Nodes
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("land_analysis", land_analysis_node)
workflow.add_node("design", design_node)
workflow.add_node("cost_estimation", cost_estimation_node)
workflow.add_node("validation", validation_node)

workflow.set_entry_point("coordinator")

# Add Edges
# Coordinator uses a conditional edge because it decides the branching logic
workflow.add_conditional_edges(
    "coordinator",
    route_from_coordinator,
    {
        "land_analysis": "land_analysis",
        "design": "design"
    }
)

workflow.add_edge("land_analysis", "design")
workflow.add_edge("design", "cost_estimation")
workflow.add_edge("cost_estimation", "validation")

# Validation routes conditionally: to END (approval), back to design (revision), or END (failed)
workflow.add_conditional_edges(
    "validation",
    route_from_validation,
    {
        "awaiting_approval": END,
        "revision_to_design": "design",
        "failed": END,
    }
)

app_graph = workflow.compile()
