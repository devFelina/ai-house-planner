from __future__ import annotations
import logging
from datetime import datetime, timezone
from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.schemas.workflow_plan import create_default_house_planning_plan, PlanStepStatus
from app.utils.plan_persistence import persist_workflow_plan_state, PlanPersistenceError

logger = logging.getLogger(__name__)

def is_agent_failed(state: WorkflowState) -> bool:
    """Determine if the current state indicates a failure from the last agent."""
    if state.status == "failed":
        return True
    if getattr(state, "current_agent", None) == "failed":
        return True
    return False

def coordinator_node(state: WorkflowState) -> WorkflowState:
    """
    The Coordinator Agent acts as the entry point and air traffic controller.
    """
    input_data = state.input_data
    if input_data and not state.execution_log:
        print(f"[Coordinator Agent] Processing submission: {input_data.submission_id}")

    if state.plan is None:
        try:
            # 1. natural_language_prompt, if present and non-empty
            prompt = getattr(input_data, "natural_language_prompt", None) if input_data else None
            if prompt and str(prompt).strip():
                objective = str(prompt).strip()
            else:
                # 2. deterministic objective string
                beds = getattr(input_data, "bedrooms", 3) if input_data else 3
                baths = getattr(input_data, "bathrooms", 1) if input_data else 1
                budget = getattr(input_data, "budget_lkr", None) if input_data else None
                budget_str = f" within a budget of LKR {budget:,.2f}" if budget else ""
                objective = f"Design a {beds}-bedroom, {baths}-bathroom house{budget_str}."

            state.plan = create_default_house_planning_plan(objective)
            
            state.execution_log.append(ExecutionLogEntry(
                agent_name="CoordinatorAgent",
                action="workflow_plan_created",
                result=f"step_count={len(state.plan.steps)} plan_version={state.plan.version}",
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            ))
            print(f"[Coordinator Agent] Created new workflow plan with {len(state.plan.steps)} steps.")
        except Exception as exc:
            logger.error(f"[Coordinator Agent] Failed to create plan: {exc}")
            state.status = "failed"
            state.execution_log.append(ExecutionLogEntry(
                agent_name="CoordinatorAgent",
                action="plan_creation_failed",
                result=str(exc),
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            ))
            return state

    # Finalize previous step
    if state.current_step_id is not None:
        # Find the step that just ran
        current_step = next((s for s in state.plan.steps if s.step_id == state.current_step_id), None)
        if current_step:
            if is_agent_failed(state):
                current_step.status = PlanStepStatus.FAILED
                current_step.error = "Agent execution failed."
                state.status = "failed" # ensure global state is failed
                print(f"[Coordinator Agent] Step {current_step.step_id} failed.")
            else:
                current_step.status = PlanStepStatus.COMPLETED
                current_step.error = None
                if current_step.step_id not in state.completed_step_ids:
                    state.completed_step_ids.append(current_step.step_id)
                print(f"[Coordinator Agent] Step {current_step.step_id} completed.")
        
        state.current_step_id = None # clear it

    # If workflow is failed, stop
    if is_agent_failed(state):
        try:
            persist_workflow_plan_state(state)
        except PlanPersistenceError as e:
            logger.error(str(e))
            state.execution_log.append(ExecutionLogEntry(
                agent_name="CoordinatorAgent",
                action="plan_persistence_failed",
                result=str(e),
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            ))
        return state

    # Determine next step
    next_step = None
    for step in state.plan.steps:
        if step.status == PlanStepStatus.PENDING:
            # Check dependencies
            deps_satisfied = True
            for dep in step.dependencies:
                dep_step = next((s for s in state.plan.steps if s.step_id == dep), None)
                if not dep_step or dep_step.status not in (PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED):
                    deps_satisfied = False
                    break
            if deps_satisfied:
                next_step = step
                break

    if next_step:
        next_step.status = PlanStepStatus.RUNNING
        state.current_step_id = next_step.step_id
        
        # Determine actual next_agent (for logging)
        next_agent = next_step.assigned_agent
        
        state.execution_log.append(ExecutionLogEntry(
            agent_name="CoordinatorAgent",
            action="workflow_step_selected",
            result=f"step_id={next_step.step_id} assigned_agent={next_agent}",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        ))
        print(f"[Coordinator Agent] Selected step {next_step.step_id} ({next_agent}).")
    else:
        # All steps completed or skipped, or deadlocked
        print("[Coordinator Agent] Workflow plan completed.")

    # Persist the plan (handles creation, completion, failures, and running transitions)
    try:
        persist_workflow_plan_state(state)
    except PlanPersistenceError as e:
        logger.error(str(e))
        state.status = "failed"
        state.execution_log.append(ExecutionLogEntry(
            agent_name="CoordinatorAgent",
            action="plan_persistence_failed",
            result=str(e),
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        ))
        
        # If persistence failed, we must not route to the next agent.
        # Clear current_step_id so route_from_coordinator routes to END (if failed)
        state.current_step_id = None
        if next_step:
            next_step.status = PlanStepStatus.FAILED
            next_step.error = "Plan persistence failed."

    return state
