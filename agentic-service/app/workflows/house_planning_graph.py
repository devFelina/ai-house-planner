from langgraph.graph import StateGraph, END
from app.schemas.workflow_state import WorkflowState
# Import all actual agent logic
from app.agents.coordinator_agent import coordinator_node
from app.agents.land_analysis_agent import land_analysis_node
from app.agents.design_agent import design_node
from app.agents.cost_estimation_agent import cost_estimation_node
from app.agents.validation_agent import validation_node
from app.agents.rendering_agent import rendering_node

def route_from_coordinator(state: WorkflowState) -> str:
    """Conditional edge router from the Coordinator"""
    return state.current_agent

# Initialize the State Graph
workflow = StateGraph(WorkflowState)
# Add Nodes
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("land_analysis", land_analysis_node)
workflow.add_node("design", design_node)
workflow.add_node("cost_estimation", cost_estimation_node)
workflow.add_node("validation", validation_node)
workflow.add_node("rendering", rendering_node)
workflow.set_entry_point("coordinator")

# Add Edges
workflow.add_conditional_edges(
    "coordinator",
    route_from_coordinator,
    {
        "land_analysis": "land_analysis",
        "design": "design"
    }
)

workflow.add_edge("land_analysis", "design")
workflow.add_conditional_edges(
    "design", lambda state: "failed" if state.status == "failed" else "cost_estimation",
    {"failed": END, "cost_estimation": "cost_estimation"},
)
workflow.add_edge("cost_estimation", "validation")
workflow.add_edge("validation", "rendering")  # Output plan regardless of validation success
workflow.add_edge("rendering", END)
app_graph = workflow.compile()
