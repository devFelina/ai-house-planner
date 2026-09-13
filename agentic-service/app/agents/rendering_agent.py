"""Render one centered conceptual plan panel per floor."""
import os

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from app.schemas.workflow_state import WorkflowState

ABBREVIATIONS = {
    'living_room': 'Living', 'bathroom_attached': 'Ensuite',
    'home_office': 'Office', 'staircase': 'Stairs', 'hallway': 'Hall',
}


def rendering_node(state: WorkflowState) -> WorkflowState:
    print(f"[Rendering Agent] Generating conceptual plan for workflow {state.workflow_id}...")
    if not state.design_result or not state.design_result.get('rooms') or not HAS_MATPLOTLIB:
        return state

    rooms = state.design_result['rooms']
    floors = sorted({room.get('floor', 1) for room in rooms})
    fig, axes = plt.subplots(1, len(floors), figsize=(7 * len(floors), 7), squeeze=False)
    style = state.input_data.preferences.get('architecturalStyle', 'Modern Design')
    fig.suptitle(f'Conceptual Floor Plan — {style}', fontsize=16)

    for ax, floor in zip(axes[0], floors):
        floor_rooms = [room for room in rooms if room.get('floor', 1) == floor]
        min_x = min(room['x'] for room in floor_rooms)
        min_y = min(room['y'] for room in floor_rooms)
        max_x = max(room['x'] + room['width'] for room in floor_rooms)
        max_y = max(room['y'] + room['length'] for room in floor_rooms)
        span = max(max_x - min_x, max_y - min_y)
        padding = max(2.0, span * 0.06)

        for room in floor_rooms:
            x, y, width, length = room['x'], room['y'], room['width'], room['length']
            ax.add_patch(patches.Rectangle(
                (x, y), width, length, linewidth=1.6,
                edgecolor='#334155', facecolor='#f1f5f9',
            ))
            label = room.get('name') or room.get('room_type', 'Room').replace('_', ' ').title()
            if min(width, length) < 7:
                label = ABBREVIATIONS.get(room.get('room_type'), label[:8])
            font_size = max(6, min(10, min(width, length) * 0.8))
            ax.text(x + width / 2, y + length / 2, label, ha='center', va='center',
                    fontsize=font_size, weight='semibold', clip_on=True)
            for opening in room.get('doors', []):
                ox, oy, ow, oh = get_opening_coords(x, y, width, length, opening)
                ax.add_patch(patches.Rectangle((ox, oy), ow, oh, color='#8b4513'))
            for opening in room.get('windows', []):
                ox, oy, ow, oh = get_opening_coords(x, y, width, length, opening)
                ax.add_patch(patches.Rectangle((ox, oy), ow, oh, color='#38bdf8'))

        ax.set_xlim(min_x - padding, max_x + padding)
        ax.set_ylim(min_y - padding, max_y + padding)
        ax.set_aspect('equal', adjustable='box')
        ax.set_title(f'Floor {floor}', pad=10, fontsize=12, weight='bold')
        ax.set_xlabel('Feet (x)', labelpad=8)
        ax.set_ylabel('Feet (y)', labelpad=8)
        ax.grid(True, linestyle='--', alpha=0.25)

    os.makedirs('output_plans', exist_ok=True)
    file_path = f'output_plans/plan_{state.workflow_id}.png'
    fig.tight_layout(rect=(0, 0, 1, 0.95), pad=1.2)
    fig.savefig(file_path, bbox_inches='tight', pad_inches=0.15, dpi=220)
    plt.close(fig)
    state.execution_log.append({
        'agent_name': 'RenderingAgent', 'action': f'Saved visual plan to {file_path}',
        'result': 'success', 'created_at_utc': 'now',
    })
    return state


def get_opening_coords(rx, ry, rw, rl, opening):
    wall = opening.get('wall', 'north')
    offset, width, thickness = opening.get('offset', 0), opening.get('width', 3), 0.5
    if wall == 'north':
        return rx + offset, ry + rl - thickness / 2, width, thickness
    if wall == 'south':
        return rx + offset, ry - thickness / 2, width, thickness
    if wall == 'east':
        return rx + rw - thickness / 2, ry + offset, thickness, width
    if wall == 'west':
        return rx - thickness / 2, ry + offset, thickness, width
    return rx, ry, width, thickness
