from langgraph.graph import StateGraph,END
from app.schemas.workflow_state import WorkflowState
from app.agents.coordinator_agent import coordinator_node

#Mock implemetation for the agents
def land_analysis_node(state:WorkflowState):
    state.current_agent="design"
    return state

def design_node(state:WorkflowState):
    state.current_agent="cost_estimation"
    return state

def cost_estimation_node(state:WorkflowState):
    state.current_agent="validation"
    return state

#Validation determines if we loop back to design/cost or finish
def validation_node(state:WorkflowState):
    state.status="awaiting_approval"
    return state

def route_from_coordinator(state: WorkflowState) -> str:
    """Conditional edge router from the Coordinator"""
    return state.current_agent

#Initialize the State Graph
workflow=StateGraph(WorkflowState)

#Add Nodes
workflow.add_node("coordinator",coordinator_node)
workflow.add_node("land_analysis", land_analysis_node)
workflow.add_node("design", design_node)
workflow.add_node("cost_estimation", cost_estimation_node)
workflow.add_node("validation", validation_node)

workflow.set_entry_point("coordinator")

#Add Edges
#Coordinator uses a conditional edge because it decides the branching logic
workflow.add_conditional_edges(
    "coordinator",
    route_from_coordinator,
    {
        "land_analysis":"land_analysis",
        "design":"design"
    }
)

workflow.add_edge("land_analysis","design")
workflow.add_edge("land_analysis","cost_estimation")
workflow.add_edge("cost_estimation","validation")
workflow.add_edge("validation",END)

app_graph=workflow.compile

