import requests
from typing import Dict, Any
from app.schemas.workflow_agent import WorkflowState


def coordinator_node(state: WorkflowState) -> WorkflowState:
    """
    The Coordinator Agent acts as the entry point and air traffic controller.
    It evaluates the input data and determines the execution plan.

    Routing logic:
    - If manual_terrain_type is provided → skip Land Analysis, go to Design
    - If no manual terrain → route to Land Analysis to process the land photo
    """
    input_data = state.input_data

    # Log the start of the workflow
    print(f"[Coordinator Agent] Processing submission: {input_data.submission_id}")

    # Decision Logic: Do we need Land Analysis?
    if input_data.manual_terrain_type:
        # If client provides manual terrain, skip Land Analysis
        next_agent = "design"
        action_log = f"Routed to Design. Manual terrain provided: {input_data.manual_terrain_type}"

        # Normalize manual terrain to controlled values
        terrain_mapping = {
            "flat/urban": "flat",
            "forested": "flat",
            "flat": "flat",
            "hillside": "hillside",
            "coastal": "coastal",
        }
        normalized_terrain = terrain_mapping.get(
            input_data.manual_terrain_type.lower(), "flat"
        )

        # Pre-fill the terrain result for the Design agent
        state.terrain_result = {
            "terrain_type": normalized_terrain,
            "slope_estimate": "flat" if normalized_terrain == "flat" else "unknown",
            "notable_features": []
        }
    else:
        # No manual terrain, route to Land Analysis to process the land photo
        next_agent = "land_analysis"
        action_log = "Routed to Land Analysis. Photo requires processing."

    # Update routing state — MUST be set in BOTH branches
    state.current_agent = next_agent

    print(f"[Coordinator Agent] {action_log}")

    return state