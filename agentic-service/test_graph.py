import asyncio
from uuid import uuid4
from app.schemas.workflow_state import WorkflowState, CoordinatorInput
from app.workflows.house_planning_graph import app_graph

async def run_graph_demo():
    initial_state = WorkflowState(
        workflow_id=uuid4(),
        status="running",
        input_data=CoordinatorInput(
            submission_id=uuid4(),
            budget_lkr=15000000,
            land_size_perches=10,
            manual_terrain_type="flat/urban",
            preferences={"bedrooms": 3, "floors": 1, "architecturalStyle": "Modern"}
        )
    )
    print("Invoking graph...")
    try:
        res = app_graph.invoke(initial_state)
        print("Success:", res)
    except Exception as e:
        print("Graph failed:", e)

if __name__ == "__main__":
    asyncio.run(run_graph_demo())
