from langgraph.graph import StateGraph, END
from app.schemas.workflow_agent import WorkflowState
from app.agents.coordinator_agent import coordinator_node
from app.agents.land_analysis_agent import land_analysis_node
from app.agents.design_agent import design_node


def cost_estimation_node(state: WorkflowState):
    """Placeholder for Member 3's cost estimation agent."""
    state.current_agent = "validation"
    return state


def validation_node(state: WorkflowState):
    """Placeholder for Member 4's validation agent."""
    state.status = "awaiting_approval"
    return state


def route_from_coordinator(state: WorkflowState) -> str:
    """Conditional edge router from the Coordinator.
    Routes to 'land_analysis' if a photo needs processing,
    or directly to 'design' if manual terrain was provided.
    """
    return state.current_agent


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
# Coordinator decides: land_analysis (photo exists) or design (manual terrain)
workflow.add_conditional_edges(
    "coordinator",
    route_from_coordinator,
    {
        "land_analysis": "land_analysis",
        "design": "design"
    }
)

# Fixed: sequential pipeline after land_analysis
workflow.add_edge("land_analysis", "design")
workflow.add_edge("design", "cost_estimation")
workflow.add_edge("cost_estimation", "validation")
workflow.add_edge("validation", END)

app_graph = workflow.compile()
