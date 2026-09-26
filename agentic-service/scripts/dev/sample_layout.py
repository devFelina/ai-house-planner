from __future__ import annotations
import json

from app.design.quality.architectural_quality import validate_architectural_quality
from app.design.program.models import Requirements
from app.design.generation.plan_adapter import finish_layout
from app.design.geometry.plot_constraints import PlotConstraints
from app.schemas.design_result import DesignResult
from app.validation.geometry_validator import validate_geometry


def sample_and_report(target_beds, target_floors, data):
    plan = next(p for p in data if p['bedrooms'] == target_beds and p['floors'] == target_floors)

    print(f"\n--- Sampling Plan: {plan['designCode']} ---")
    print(f"Bedrooms (Configured): {plan['bedrooms']}")
    print(f"Bathrooms (Configured): {plan['bathrooms']}")
    print(f"Floors: {plan['floors']}")

    design = DesignResult.model_validate(plan['layout'])
    finish_layout(design)

    hallways = [r for r in design.rooms if r.room_type == 'hallway']
    for i, h in enumerate(hallways):
        print(f"Hallway {i+1} width: {h.width}")

    stairs = [r for r in design.rooms if r.room_type == 'staircase']
    if not stairs:
        print("Stairs: None")
    for i, s in enumerate(stairs):
        print(f"Stair {i+1} on floor {s.floor} at x={s.x}, y={s.y}, width={s.width}, length={s.length}")

    req = Requirements(bedrooms=target_beds, bathrooms=plan['bathrooms'], floors=target_floors, target_budget_lkr=0)
    plot = PlotConstraints(land_size_perches=20.0, plot_width_ft=44, plot_length_ft=123)

    geom_res = validate_geometry(design.rooms, target_beds, target_floors, plot.land_size_perches, plot=plot, design=design)
    print(f"Geometry Validation Passed: {geom_res.passed}")
    if not geom_res.passed:
        for fail in geom_res.failures:
            print(f" - {fail}")

    arch_res = validate_architectural_quality(design, req, plot)
    print(f"Architectural Quality Validation Passed: {arch_res.passed}")
    if not arch_res.passed:
        for fail in arch_res.failures:
            print(f" - {fail}")

with open('../HousePlanner.API/Data/Seed/pre-designed-plans.json') as f:
    data = json.load(f)

sample_and_report(2, 1, data)
sample_and_report(3, 1, data)
sample_and_report(4, 2, data)
sample_and_report(5, 2, data)
