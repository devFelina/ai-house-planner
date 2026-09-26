from __future__ import annotations
from langgraph.graph import END, StateGraph

from app.agents.construction_planning_agent import construction_planning_node
from app.orchestration.workflow_router import coordinator_node
from app.agents.cost_estimation_agent import cost_estimation_node
from app.agents.design_agent import design_node
from app.agents.land_analysis_agent import land_analysis_node
from app.agents.rendering_agent import rendering_node
from app.validation.design_validation_service import validation_node
from app.schemas.workflow_state import WorkflowState


def route_from_coordinator(state: WorkflowState) -> str:
    """Route execution to the agent selected by the coordinator."""
    return state.current_agent


def route_after_cost_estimation(state: WorkflowState) -> str:
    """Stop when cost calculation or persistence fails."""
    return "failed" if state.status == "failed" or state.current_agent == "failed" else "validation"


def route_from_validation(state: WorkflowState) -> str:
    """Render a valid design, retry an invalid one, or stop on failure."""
    if state.validation_result and state.validation_result.get("passed", False):
        return "rendering"
    if state.status == "failed" or state.current_agent == "failed":
        return "failed"
    return "design"


workflow = StateGraph(WorkflowState)
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("land_analysis", land_analysis_node)
workflow.add_node("design", design_node)
workflow.add_node("construction_planning", construction_planning_node)
workflow.add_node("cost_estimation", cost_estimation_node)
workflow.add_node("validation", validation_node)
workflow.add_node("rendering", rendering_node)
workflow.set_entry_point("coordinator")

workflow.add_conditional_edges(
    "coordinator",
    route_from_coordinator,
    {
        "land_analysis": "land_analysis",
        "design": "design",
        "rendering": "rendering",
    },
)
workflow.add_edge("land_analysis", "design")
workflow.add_conditional_edges(
    "design",
    lambda state: "failed" if state.status == "failed" else "construction_planning",
    {"failed": END, "construction_planning": "construction_planning"},
)
workflow.add_edge("construction_planning", "cost_estimation")
workflow.add_conditional_edges(
    "cost_estimation",
    route_after_cost_estimation,
    {"failed": END, "validation": "validation"},
)
workflow.add_conditional_edges(
    "validation",
    route_from_validation,
    {"rendering": "rendering", "design": "design", "failed": END},
)
workflow.add_edge("rendering", END)

app_graph = workflow.compile()

# A selected pre-designed plan already has persisted geometry and a construction
# plan. It enters Component C directly, then follows the same validation gate.
pre_designed_workflow = StateGraph(WorkflowState)
pre_designed_workflow.add_node("cost_estimation", cost_estimation_node)
pre_designed_workflow.add_node("validation", validation_node)
pre_designed_workflow.set_entry_point("cost_estimation")
pre_designed_workflow.add_conditional_edges(
    "cost_estimation", route_after_cost_estimation,
    {"failed": END, "validation": "validation"},
)
pre_designed_workflow.add_edge("validation", END)
pre_designed_graph = pre_designed_workflow.compile()
