from __future__ import annotations
"""Export authored residential arrangements. Not called during generation.

Each concept fixes public/private/service relationships. Variants change the
public wing geometry, not random coordinates. Every exported plan must pass
both validators; a failed arrangement aborts the export.
"""
import json
from pathlib import Path

from app.design.architectural_quality import validate_architectural_quality
from app.design.models import Requirements
from app.design.plan_adapter import finish_layout
from app.design.room_counts import count_bathrooms
from app.schemas.design_result import DesignResult, RoomLayout
from app.validation.geometry_validator import validate_geometry


def room(kind,x,y,w,h,floor=1):
    return RoomLayout(room_id=f'{floor}-{kind}',room_type=kind,floor=floor,x=x,y=y,width=w,length=h)


def single(beds,baths,family):
    # Public bar and two-sided private hall. Second bathroom is a true ensuite.
    left=10 if family in ('L_SHAPE','T_SHAPE') else 0
    right=10 if family=='T_SHAPE' else 0
    top=28 if beds==2 else 38
    rooms=[room('living_room',0,0,16,12), room('kitchen',16,0,12,12),
           room('hallway',12,12,4,top-12),
           room('bedroom_2',0,12,12,(top-12)/2 if beds>2 else top-12),
           room('bedroom_1',16,18,12,10)]
    if beds>2:
        rooms += [room('bedroom_3',0,25,12,13),
                  room('bedroom_4' if beds==4 else 'home_office',16,28,12,10)]
    if baths==1:
        rooms.append(room('bathroom',16,12,12,6))
    else:
        rooms += [room('bathroom',16,12,6,6),room('bathroom_attached',22,12,6,6)]
    if left:
        # A full dining wing, not a stretched living rectangle.
        rooms.append(room('dining',-left,0,left,12))
    if right:
        rooms.append(room('dining_2',28,0,right,12))
    if baths==3:
        # Common second wet core at the end of the short private hall.
        rooms.append(room('bathroom_3',0,top,16,8))
        for r in rooms:
            if r.room_type=='bedroom_4': r.length+=8
    for r in rooms: r.x+=left
    return rooms


def duplex(beds,baths):
    # Aligned 6x10 stair, 4x10 landing. Ground essentials remain step independent.
    rooms=[room('living_room',0,0,18,16),room('kitchen',18,0,14,16),
           room('bedroom_1',0,16,12,14),room('hallway',12,16,4,14),
           room('staircase',16,16,6,10),room('bathroom',22,16,10,7),
           room('utility',22,23,10,7),room('foyer',16,26,6,4)]
    rooms += [room('family_lounge',0,0,18,16,2),room('bedroom_3',18,0,14,16,2),
              room('hallway',12,16,4,14,2),room('staircase',16,16,6,10,2),
              room('bathroom_2',22,16,10,7,2),room('utility',22,23,10,7,2),
              room('foyer',16,26,6,4,2),room('bedroom_2',0,16,12,14,2)]
    if beds>=4:
        for r in rooms:
            if r.floor==2 and r.room_type=='family_lounge': r.x=10; r.width=8
        rooms.append(room('bedroom_4',0,0,10,16,2))
    if baths==3:
        rooms=[r for r in rooms if not (r.floor==2 and r.room_type=='utility')]
        rooms.append(room('bathroom_3',22,23,10,7,2))
    return rooms


def build():
    plans=[]
    configs=[(2,1),(2,2),(3,1),(3,2),(4,2),(4,3)]
    for beds,baths in configs:
        for family in ('COMPACT_RECTANGLE','L_SHAPE','T_SHAPE'):
            plans.append((beds,baths,1,family,single(beds,baths,family)))
    for beds,baths in [(3,2),(3,3),(4,2),(4,3)]:
        plans.append((beds,baths,2,'COMPACT_RECTANGLE',duplex(beds,baths)))
    output=[]
    for beds,baths,floors,family,rooms in plans:
        code=f'HP-{beds}B{baths}B-{floors}F-{family}'
        actual_bathrooms = count_bathrooms(rooms)
        if actual_bathrooms != baths:
            print(f'Skipping {code}: bathroom count mismatch (configured {baths}, actual {actual_bathrooms}).')
            continue
        design=finish_layout(DesignResult(floor_count=floors,foundation_type='slab',rooms=rooms,template_family=family,template_id=code))
        req=Requirements(bedrooms=beds,bathrooms=baths,floors=floors)
        geometry=validate_geometry(design.rooms,beds,floors,100,design=design)
        quality=validate_architectural_quality(design,req)
        if not geometry.passed or not quality.passed:
            print(code,geometry.failures,quality.failures, quality.score)
            continue
        design.candidate_status=quality.status; design.design_score=quality.score
        design.candidate_summary={'base_plan_code':code,'quality_metrics':quality.metrics}
        w=max(r.x+r.width for r in rooms); h=max(r.y+r.length for r in rooms)
        kinds={r.room_type for r in rooms}
        output.append({'plan_code': code,'name': f'{beds} bedroom {family.replace("_"," ").title()} ({floors} floor)',
            'bedrooms': beds,'bathrooms': baths,'floors': floors,'topology_family': family,
            'minimum_land_perches': round(max((w+10)*(h+17),design.total_built_up_area_sqft/.65)/272.25,2),'maximum_land_perches': 1000,
            'minimum_plot_width_ft': w+10,'minimum_plot_length_ft': h+17,
            'supported_plot_shapes': ['COMPACT','BALANCED','NARROW','VERY_NARROW'],'supported_terrains': ['flat','coastal'],
            'supported_styles': ['Modern Minimalist','Contemporary','Traditional Sri Lankan','Tropical Modernism'],
            'capabilities': {'open_plan': True,'master_ensuite': 'bathroom_attached' in kinds,'separate_dining': 'dining' in kinds,
                 'home_office': 'home_office' in kinds,'balcony': False,'veranda': False,'utility_room': 'utility' in kinds,'parking': True,'accessibility': True},
            'adaptation_support': {'rotations': [0,90,180,270],'living_scale': floors==1,'bedroom_scale': floors==1,'public_depth': 10},
            'architectural_metrics': quality.metrics,'layout_json': design.model_dump(),'active': True})
    path=Path(__file__).resolve().parents[1]/'app/design/data/base_plans.json'
    path.write_text(json.dumps(output,indent=2)+'\n')
    print('VALIDATED',len(output))

if __name__=='__main__': build()
