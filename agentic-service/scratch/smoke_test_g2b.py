import asyncio
from app.design.generation.spatial_planner import plan_spatial_program
from app.design.geometry.geometry_generator import generate_geometry
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.models import Requirements
import time

async def run_smoke():
    req = Requirements(
        bedrooms=4, bathrooms=3, floors=2, open_plan=True
    )
    plot = PlotConstraints(
        land_size_perches=20,
        plot_width_ft=60,
        plot_length_ft=80,
        road_side="south"
    )
    
    print("Calling SpatialPlanner...")
    t0 = time.time()
    program, meta_gpt = plan_spatial_program(req, plot)
    t1 = time.time()
    
    print(f"GPT returned {program.floor_count} floors with {len(program.rooms)} rooms. Latency: {int((t1-t0)*1000)}ms")
    
    print("Calling GeometryGenerator...")
    t2 = time.time()
    try:
        res, meta_geo = generate_geometry(program, plot)
        t3 = time.time()
        print(f"Success in {meta_geo['generation_ms']}ms.")
        print(f"Eval: {meta_geo['candidate_evaluations']}, Backtracks: {meta_geo['backtracks']}, Core Cands: {meta_geo['core_candidates_evaluated']}")
        print(f"Rooms Placed: {meta_geo['rooms_placed']}")
        print(f"Upper Footprint: {meta_geo['upper_footprint_area']} / {meta_geo['ground_footprint_area']} sqft")
        
        # Save output for visualization
        with open("scratch/g2b_output.json", "w") as f:
            f.write(res.model_dump_json(indent=2))
    except Exception as e:
        print(f"Failed geometry generation: {e}")

if __name__ == "__main__":
    asyncio.run(run_smoke())
