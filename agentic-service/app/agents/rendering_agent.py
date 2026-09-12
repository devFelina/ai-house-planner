import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
from app.schemas.workflow_state import WorkflowState
def rendering_node(state: WorkflowState) -> WorkflowState:
    print(f"[Rendering Agent] Generating professional architectural plan for workflow {state.workflow_id}...")
    
    if not state.design_result or "rooms" not in state.design_result:
        print("[Rendering Agent] No rooms found in design result.")
        return state
        
    # Setup Blueprint Canvas
    fig, ax = plt.subplots(figsize=(10, 10))
    style = state.input_data.preferences.get('architecturalStyle', 'Modern Design')
    ax.set_title(f"Architectural Floor Plan - {style}", fontsize=16, pad=20)
    
    rooms = state.design_result["rooms"]
    
    for room in rooms:
        x, y = room.get("x", 0), room.get("y", 0)
        w, l = room.get("width", 10), room.get("length", 10)
        room_type = room.get("room_type", "Room").replace('_', ' ').title()
        
        # Base rectangle for the room
        rect = patches.Rectangle((x, y), w, l, linewidth=2, edgecolor='black', facecolor='#f0f0f0', alpha=0.9)
        ax.add_patch(rect)
        
        # Room Label
        ax.text(x + w/2, y + l/2, room_type, 
                horizontalalignment='center', verticalalignment='center', fontsize=10, weight='bold')
                
        # Draw doors and windows
        for door in room.get("doors", []):
            dx, dy, dw, dl = get_opening_coords(x, y, w, l, door)
            ax.add_patch(patches.Rectangle((dx, dy), dw, dl, color='#8b4513')) # Brown for doors
            
        for window in room.get("windows", []):
            wx, wy, ww, wl = get_opening_coords(x, y, w, l, window)
            ax.add_patch(patches.Rectangle((wx, wy), ww, wl, color='#87ceeb')) # SkyBlue for windows
            
    ax.autoscale_view()
    ax.set_aspect('equal')
    ax.set_xlabel("Feet (x)")
    ax.set_ylabel("Feet (y)")
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Save the generated plan to disk
    os.makedirs("output_plans", exist_ok=True)
    file_path = f"output_plans/plan_{state.workflow_id}.png"
    plt.savefig(file_path, bbox_inches='tight', dpi=300)
    plt.close()
    
    print(f"[Rendering Agent] Successfully generated plan at {file_path}")
    
    state.execution_log.append({
        "agent_name": "RenderingAgent",
        "action": f"Saved visual plan to {file_path}",
        "result": "success",
        "created_at_utc": "now"
    })
    
    return state
def get_opening_coords(rx, ry, rw, rl, opening):
    wall = opening.get("wall", "north")
    offset = opening.get("offset", 0)
    width = opening.get("width", 3)
    thickness = 1.0 # Visual representation thickness
    
    if wall == "north":
        return rx + offset, ry + rl - thickness/2, width, thickness
    elif wall == "south":
        return rx + offset, ry - thickness/2, width, thickness
    elif wall == "east":
        return rx + rw - thickness/2, ry + offset, thickness, width
    elif wall == "west":
        return rx - thickness/2, ry + offset, thickness, width
    return rx, ry, width, thickness