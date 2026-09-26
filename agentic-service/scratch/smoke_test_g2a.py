import json
from app.design.program.models import Requirements
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.generation.spatial_planner import plan_spatial_program
from app.design.geometry.geometry_generator import generate_geometry

def run():
    req = Requirements(bedrooms=3, bathrooms=2, floors=1, dining_required=True)
    plot = PlotConstraints.model_validate({
        'land_size_perches': 20,
        'plot_width_ft': 60,
        'plot_length_ft': 80,
        'road_side': 'south',
        'terrain_type': 'flat',
        'setbacks': {'front': 10, 'rear': 10, 'left': 5, 'right': 5},
    })
    
    print("Starting GPT Spatial Planning Request...")
    program, gpt_meta = plan_spatial_program(req, plot)
    
    print("Starting Deterministic Geometry Generation...")
    result, geo_meta = generate_geometry(program, plot)
    
    print("====================================")
    print("GPT METADATA:")
    print(json.dumps(gpt_meta, indent=2))
    
    print("GEOMETRY METADATA:")
    print(json.dumps(geo_meta, indent=2))
    
    print("====================================")
    print("GENERATED LAYOUT:")
    for r in result.rooms:
        print(f"{r.room_type} ({r.room_id}): x={r.x}, y={r.y}, w={r.width}, l={r.length}")

if __name__ == "__main__":
    run()
