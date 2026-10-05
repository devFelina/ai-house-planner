from datetime import datetime, timezone

import requests

from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.orchestration.tool_governance import (
    ToolAuthorizationError,
    assert_tool_allowed,
    mark_tool_authorization_failure,
)
from app.orchestration.tool_audit import (
    log_tool_failure,
    log_tool_success,
    start_tool_timer,
)


def get_construction_phases()->list:
    """Return the standard construction phases and their general relationships."""
    return[
        {"id":1,"name":"Site Preparation","depends_on":[]},
         {"id": 2, "name": "Foundation", "depends_on": [1]},
        {"id": 3, "name": "Structural Work", "depends_on": [2]},
        {"id": 4, "name": "Walls", "depends_on": [3]},
        {"id": 5, "name": "Roofing", "depends_on": [3]},
        {"id": 6, "name": "Electrical", "depends_on": [3, 4]},
        {"id": 7, "name": "Plumbing", "depends_on": [3, 4]},
        {"id": 8, "name": "Flooring", "depends_on": [6, 7]},
        {"id": 9, "name": "Painting", "depends_on": [8]},
        {"id": 10, "name": "Final Inspection", "depends_on": [9]}
    ]

def estimate_phase_duration(phase_name:str,floor_count:int,total_area:float,bathrooms:int,terrain:str)->int:
    """Estimates an appropriate duration for a construction phase based on house characteristics."""
    base=7
    if "site preparation" in phase_name.lower():
        return 14 if terrain in ["hillside","coastal"] else 7
    if "foundation" in phase_name.lower():
        return 15 + (floor_count*2)
    if "structural" in phase_name.lower():
        return 20+int(total_area/200)+(floor_count*7)
    if "walls" in phase_name.lower():
        return 10+int(total_area/300)
    if "roofing" in phase_name.lower():
        return 10 + int(total_area / 400)
    if "electrical" in phase_name.lower():
        return 10 + (floor_count * 3)
    if "plumbing" in phase_name.lower():
        return 7 + (bathrooms * 4)
    if "flooring" in phase_name.lower():
        return 7 + int(total_area / 500)
    if "painting" in phase_name.lower():
        return 10 + (floor_count * 2)
    return base

def calculate_schedule(phases_list:list)->dict:
    """Calculates the overall project schedule while considering dependencies and parallel activities."""
    #A simple critical path calculation
    end_days={}
    total_duration=0

    for p in phases_list:
        start_day=1
        if p["depends_on"]:
            start_day=max([end_days.get(dep,0) for dep in p["depends_on"]])+1

        end_day=start_day+p["duration_days"]-1
        end_days[p["id"]]=end_day

        p["start_day"]=start_day
        p["end_day"]=end_day

        total_duration = max(total_duration, end_day)

    return {"phases":phases_list,"total_duration":total_duration}

def _build_construction_plan(
    floor_count: int,
    total_area: float,
    bathrooms: int,
    terrain: str,
    target_duration: int | None,
) -> dict:
    phases=get_construction_phases()
    for p in phases:
        p["duration_days"] = estimate_phase_duration(p["name"], floor_count, total_area, bathrooms, terrain)
        p["description"] = f"Estimated based on {floor_count} floors and {total_area} sqft."
        p["status"] = "planned"

    schedule_result=calculate_schedule(phases)
    estimate_duration_days=schedule_result["total_duration"]
    status="ON_SCHEDULE"
    opt_notes=[]

    if target_duration and estimate_duration_days>target_duration:
        status="DELAYED"
        opt_notes.append(f"Target is {target_duration}  days but estimate is {estimate_duration_days} days.")

    for p in schedule_result["phases"]:
        if p["name"] in ["Electrical","Plumbing","Painting"]:
            p["duration_days"]=max(5,int(p["duration_days"]*0.8))

    schedule_result=calculate_schedule(schedule_result["phases"])
    estimate_duration_days=schedule_result["total_duration"]
    opt_notes.append(f"Optimized schedule duration:{estimate_duration_days} days by parallelizing finishing work.")

    if target_duration and estimate_duration_days<=target_duration:
        status="ON_SCHEDULE"

    critical_path=[p["name"] for p in schedule_result["phases"] if p["depends_on"]]
    if "Site Preparation" not in critical_path:
        critical_path.insert(0,"Site Preparation")

    return {
        "project_summary": {
            "estimated_duration_days": estimate_duration_days,
            "estimated_duration_months": round(estimate_duration_days / 30.0, 1),
            "target_duration_days": target_duration,
            "schedule_status": status
        },
        "phases": schedule_result["phases"],
        "critical_path": critical_path,
        "assumptions": [
            "Duration estimates are AI generated approximate planning estimates.",
            "Normal working conditions assumed.",
            f"Terrain factored as: {terrain}"
        ],
        "optimization_notes": opt_notes
    }


def construction_planning_node(state:WorkflowState)->WorkflowState:
    """LangGraph node for construction planning generation."""
    start_time=datetime.now(timezone.utc)

    if state.construction_plan_result:
        print("[Construction Planning Service] Existing plan reused")
        return state

    print(f"[Construction Planning Service] Planning for workflow {state.workflow_id}...")

    try:
        assert_tool_allowed("construction_planning", "construction_scheduler")
    except ToolAuthorizationError as exc:
        return mark_tool_authorization_failure(
            state, "ConstructionPlanningAgent", "construction_scheduler", exc
        )

    # 1.Analyze House
    floor_count = 1
    total_area = 1000
    bathrooms = 2

    if state.design_result:
        design = state.design_result
        floor_count = design.get("floor_count", 1)
        total_area = design.get("total_built_up_area_sqft", 1000)
        bathrooms = len([r for r in design.get("rooms", []) if "bath" in r.get("room_type", "").lower()])
    elif state.input_data:
        floor_count = 1
        bathrooms = getattr(state.input_data, "bathrooms", 2)
        total_area = 500 + (getattr(state.input_data, "bedrooms", 2) * 200)

    terrain=state.terrain_result.get("terrain_type","flat") if state.terrain_result else "flat"
    target_duration = getattr(state.input_data, "target_duration_days", None) if state.input_data else None
    
    room_count = 0
    if state.design_result:
        room_count = len(state.design_result.get("rooms", []))
    elif state.input_data:
        room_count = getattr(state.input_data, "bedrooms", 2) + bathrooms + 2

    tool_input = {
        "floor_count": floor_count,
        "total_area_sqft": total_area,
        "terrain_type": terrain,
        "target_duration_days": target_duration,
        "room_count": room_count,
        "bathroom_count": bathrooms,
    }
    started_at = start_tool_timer()
    try:
        construction_plan = _build_construction_plan(
            floor_count, total_area, bathrooms, terrain, target_duration
        )
    except Exception as exc:
        log_tool_failure(
            state=state,
            agent_name="construction_planning",
            tool_name="construction_scheduler",
            started_at=started_at,
            input_summary=tool_input,
            error=exc,
        )
        raise
    log_tool_success(
        state=state,
        agent_name="construction_planning",
        tool_name="construction_scheduler",
        started_at=started_at,
        input_summary=tool_input,
        output_summary={
            "phase_count": len(construction_plan["phases"]),
            "total_duration_days": construction_plan["project_summary"]["estimated_duration_days"],
            "schedule_status": construction_plan["project_summary"]["schedule_status"],
            "critical_path_length": len(construction_plan["critical_path"]),
        },
    )

    state.construction_plan_result=construction_plan

    #POST to backend ASP.NET Internal API
    api_result="api_call_skipped_local_dev"
    try:
        response=requests.patch(
            f"{ASPNET_API_URL}/internal/workflows/{state.workflow_id}/construction-plan",
            json=construction_plan,
            headers={"X-Internal-API-Key":INTERNAL_API_KEY,"Content-Type":"application/json"},
            timeout=10,
        )
        if response.ok:
            api_result="success"
        else:
            api_result=f"api_failed:{response.status_code}"
    except requests.RequestException as e:
        print(f"[Construction Planning Service] Could not reach ASP.NET:{e}")

    duration=int((datetime.now(timezone.utc)-start_time).total_seconds()*1000)

    state.execution_log.append(ExecutionLogEntry(
        agent_name="ConstructionPlanningAgent",
        action="Generated intelligent construction schedule based on architectural design.",
        duration_ms=duration,
        result=api_result,
        created_at_utc=datetime.now(timezone.utc).isoformat()
    ))

    return state
