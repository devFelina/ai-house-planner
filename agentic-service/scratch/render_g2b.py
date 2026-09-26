import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches

with open("scratch/g2b_output.json") as f:
    data = json.load(f)

fig, axes = plt.subplots(1, 2, figsize=(16, 8))
fig.suptitle("Phase G2B Multi-Floor Geometry", fontsize=16)

colors = {
    'living_room': '#ff9999', 'kitchen': '#99ff99', 'dining': '#ffcc99',
    'bedroom': '#99ccff', 'bedroom_master': '#9999ff', 'bathroom': '#e6e6e6',
    'staircase': '#ffb3e6', 'hallway': '#d9d9d9', 'default': '#cccccc'
}

for i, floor in enumerate([1, 2]):
    ax = axes[i]
    ax.set_title(f"Floor {floor}")
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 80)
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    rooms_on_floor = [r for r in data['rooms'] if r['floor'] == floor]
    for r in rooms_on_floor:
        c = colors.get(r['room_type'], colors['default'])
        if "bedroom" in r['room_id'].lower(): c = colors['bedroom']
        if "bath" in r['room_id'].lower(): c = colors['bathroom']
        
        rect = patches.Rectangle((r['x'], r['y']), r['width'], r['length'], 
                               linewidth=1, edgecolor='black', facecolor=c, alpha=0.8)
        ax.add_patch(rect)
        
        ax.text(r['x'] + r['width']/2, r['y'] + r['length']/2, 
                f"{r['room_id']}\n{r['width']}x{r['length']}", 
                ha='center', va='center', fontsize=8)

plt.tight_layout()
plt.savefig("scratch/g2b_visualization.png")
print("Saved to scratch/g2b_visualization.png")
