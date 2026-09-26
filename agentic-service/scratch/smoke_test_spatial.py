import json
from app.design.program.models import Requirements
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.generation.spatial_planner import plan_spatial_program

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
    
    print("Starting Spatial Planning Request...")
    program, meta = plan_spatial_program(req, plot)
    print("====================================")
    print("METADATA:")
    print(json.dumps(meta, indent=2))
    print("====================================")
    print("SPATIAL PROGRAM:")
    print(program.model_dump_json(indent=2))
    
if __name__ == "__main__":
    run()
