import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw(result):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 80)
    ax.set_title("Generated G2A Layout")
    
    colors = {
        "PUBLIC": "lightblue",
        "PRIVATE": "lightgreen",
        "SERVICE": "lightsalmon",
        "CIRCULATION": "lightgrey"
    }
    
    for r in result:
        ax.add_patch(patches.Rectangle(
            (r['x'], r['y']), r['w'], r['l'],
            edgecolor='black', facecolor='lightblue', alpha=0.5
        ))
        ax.text(r['x'] + r['w']/2, r['y'] + r['l']/2, 
                f"{r['id']}\n{r['w']}x{r['l']}", 
                ha='center', va='center', fontsize=8)
                
    plt.grid(True)
    plt.savefig("/Users/kushancs/.gemini/antigravity-ide/brain/7f9abb0a-d2f9-4337-a809-2edd51f34427/scratch/g2a_visualization.png")
    print("Saved to scratch/g2a_visualization.png")

if __name__ == "__main__":
    import sys
    # Read the output of smoke test
    rooms = [
        {"id": "living_room", "type": "living", "x": 6.0, "y": 0.0, "w": 34.0, "l": 11.76},
        {"id": "kitchen", "type": "kitchen", "x": 40.0, "y": 8.0, "w": 10.0, "l": 25.0},
        {"id": "bedroom_1", "type": "bedroom", "x": 25.0, "y": 33.0, "w": 25.0, "l": 10.0},
        {"id": "bedroom_2", "type": "bedroom", "x": 15.0, "y": 35.0, "w": 10.0, "l": 25.0},
        {"id": "bedroom_3", "type": "bedroom", "x": 35.0, "y": 43.0, "w": 15.0, "l": 16.67},
        {"id": "dining_room", "type": "dining", "x": 23.0, "y": 12.0, "w": 17.0, "l": 11.76},
        {"id": "hallway", "type": "hallway", "x": 2.0, "y": 29.0, "w": 37.5, "l": 4.0},
        {"id": "bathroom_1", "type": "bathroom", "x": 25.0, "y": 43.0, "w": 10.0, "l": 10.0},
        {"id": "bathroom_2", "type": "bathroom", "x": 9.0, "y": 37.0, "w": 6.0, "l": 16.67},
    ]
    draw(rooms)
