"""Only whole-building transforms and explicitly authored boundary changes."""
from copy import deepcopy
from uuid import uuid4

from app.design.geometry.adjacency import build_connections, exterior_segments, road_access_clear
from app.design.geometry.geometry_engine import TERRAIN_FOUNDATION_MAP
from app.design.program.models import Entrance
from app.design.program.room_rules import room_kind
from app.schemas.design_result import DesignResult, Opening


def finish_layout(design, entrance_side='south', open_plan=False):
    for room in design.rooms:
        room.doors = []
        room.windows = []
        room.area_sqft = round(room.width * room.length, 2)
    design.connections = build_connections(design.rooms, open_plan)

    from app.design.geometry.adjacency import OPPOSITE, shared_wall

    attached = {room.room_id for room in design.rooms if room.room_type == 'bathroom_attached'}
    if attached:
        design.connections = [
            connection for connection in design.connections
            if not ({connection.from_room, connection.to_room} & attached)
            or any(room.room_type == 'bedroom_1' and room.room_id in (connection.from_room, connection.to_room)
                   for room in design.rooms)
        ]

    by_id = {room.room_id: room for room in design.rooms}
    for connection in design.connections:
        if connection.kind == 'stair':
            continue
        a, b = by_id[connection.from_room], by_id[connection.to_room]
        wall = shared_wall(a, b)
        if not wall:
            continue
        side, lo, hi = wall
        width = 6 if connection.kind == 'open' and hi - lo >= 6 else 3
        start = (lo + hi - width) / 2
        for room, wall_side in [(a, side), (b, OPPOSITE[side])]:
            room.doors.append(Opening(
                wall=wall_side,
                offset=start - (room.x if wall_side in ('north', 'south') else room.y),
                width=width,
            ))

    design.entrances = []
    for room in sorted(design.rooms, key=lambda item: (item.room_type != 'living_room', item.room_id)):
        if room.floor != 1 or room_kind(room.room_type) not in {'living_room', 'foyer', 'entrance', 'dining'}:
            continue
        for wall, lo, hi in exterior_segments(room, design.rooms):
            offset = (lo + hi - 3) / 2
            if wall == entrance_side and road_access_clear(room, design.rooms, wall, offset):
                room.doors.append(Opening(wall=wall, offset=offset, width=3))
                design.entrances = [Entrance(room_id=room.room_id, wall=wall, offset=offset, width=3)]
                break
        if design.entrances:
            break
    if not design.entrances:
        raise ValueError('No approved public entrance on requested side.')

    for room in design.rooms:
        if room_kind(room.room_type) in {'hallway', 'staircase'}:
            continue
        for wall, lo, hi in exterior_segments(room, design.rooms):
            width = min(4, hi - lo)
            offset = lo
            if any(d.wall == wall and min(offset + width, d.offset + d.width) > max(offset, d.offset)
                   for d in room.doors):
                continue
            room.windows = [Opening(wall=wall, offset=offset, width=width)]
            break

    design.total_built_up_area_sqft = round(sum(room.width * room.length for room in design.rooms), 2)
    design.ground_footprint_sqft = round(sum(room.width * room.length for room in design.rooms if room.floor == 1), 2)
    return design


def _bbox(design: DesignResult) -> tuple[float, float]:
    return (
        max((room.x + room.width for room in design.rooms), default=0.0),
        max((room.y + room.length for room in design.rooms), default=0.0),
    )


def transform_design(design: DesignResult, *, mirror_horizontal: bool = False,
                     mirror_vertical: bool = False, rotation_degrees: int = 0) -> DesignResult:
    transformed = deepcopy(design)
    operations = []
    if mirror_horizontal:
        operations.append('mirror_horizontal')
    if mirror_vertical:
        operations.append('mirror_vertical')
    if rotation_degrees:
        operations.append({90: 'rotate_90', 180: 'rotate_180', 270: 'rotate_270'}.get(rotation_degrees))

    for operation in operations:
        if operation is None:
            continue
        width, height = _bbox(transformed)
        next_rooms = []
        for room in transformed.rooms:
            if operation == 'mirror_horizontal':
                x = width - (room.x + room.width)
                y = room.y
                width_out, length_out = room.width, room.length
            elif operation == 'mirror_vertical':
                x = room.x
                y = height - (room.y + room.length)
                width_out, length_out = room.width, room.length
            elif operation == 'rotate_90':
                x = height - (room.y + room.length)
                y = room.x
                width_out, length_out = room.length, room.width
            elif operation == 'rotate_180':
                x = width - (room.x + room.width)
                y = height - (room.y + room.length)
                width_out, length_out = room.width, room.length
            elif operation == 'rotate_270':
                x = room.y
                y = width - (room.x + room.width)
                width_out, length_out = room.length, room.width
            else:
                raise ValueError(f'Unsupported transform operation: {operation}')
            next_rooms.append(room.model_copy(update={
                'x': round(x, 4),
                'y': round(y, 4),
                'width': round(width_out, 4),
                'length': round(length_out, 4),
                'area_sqft': round(width_out * length_out, 2),
            }))
        transformed.rooms = next_rooms
    return transformed


def _plan_field(plan, key):
    if hasattr(plan, key):
        return getattr(plan, key)
    if hasattr(plan, 'get'):
        return plan.get(key)
    return None


class PlanAdapter:
    def adapt(self, plan, decision, req, plot):
        layout_data = _plan_field(plan, 'layout_json')
        if isinstance(layout_data, str):
            design = DesignResult.model_validate_json(layout_data).model_copy(deep=True)
        else:
            design = DesignResult.model_validate(layout_data).model_copy(deep=True)
        design.design_id = str(uuid4())

        design.design_id = str(uuid4())
        if decision.adaptations.rotation_degrees not in (0, 90, 180, 270):
            raise ValueError('Rotation must be a right angle.')

        design = transform_design(
            design,
            mirror_horizontal=decision.adaptations.mirror_horizontal,
            mirror_vertical=decision.adaptations.mirror_vertical,
            rotation_degrees=decision.adaptations.rotation_degrees,
        )

        if abs(decision.adaptations.living_scale - 1.0) > 1e-6:
            # self._scale_zone(design, {'living_room', 'dining', 'kitchen', 'foyer', 'entrance'}, decision.adaptations.living_scale)
            pass
        if abs(decision.adaptations.bedroom_scale - 1.0) > 1e-6:
            # self._scale_zone(design, {'bedroom', 'bedroom_1', 'bedroom_2', 'bedroom_3', 'bedroom_4', 'bedroom_5'}, decision.adaptations.bedroom_scale)
            pass

        design.terrain_type = plot.terrain_type
        design.foundation_type = TERRAIN_FOUNDATION_MAP[plot.terrain_type]
        design.plot_constraints = plot.model_dump()
        design.design_seed = req.design_seed
        design.template_family = _plan_field(plan, 'topology_family')
        design.template_id = _plan_field(plan, 'template_id') or _plan_field(plan, 'topology_family')
        finish_layout(design, decision.adaptations.entrance_side, req.open_plan)

        design.candidate_summary = {
            'base_plan_code': _plan_field(plan, 'plan_code'),
            'base_plan_name': _plan_field(plan, 'name'),
            'selected_plan_code': decision.selected_plan_code,
            'alternative_plan_codes': decision.alternative_plan_codes,
            'reason_codes': decision.reason_codes,
            'design_intent': decision.design_intent.model_dump(),
            'adaptations': decision.adaptations.model_dump(),
            'generation_mode': 'ai_adapted_template',
        }

        if req.parking:
            width, length = (9, 18) if plot.road_side in ('north', 'south') else (18, 9)
            design.site_features = [{
                'type': 'parking', 'coordinate_space': 'plot', 'road_side': plot.road_side,
                'x': plot.plot_width_ft - width if plot.road_side == 'east' else 0,
                'y': plot.plot_length_ft - length if plot.road_side == 'north' else 0,
                'width': width, 'length': length,
            }]
        return design

    @staticmethod
    def _scale_zone(design: DesignResult, kinds: set[str], factor: float) -> None:
        if factor <= 0:
            raise ValueError('Scale factor must be positive.')
        if factor == 1:
            return
        target_rooms = [room for room in design.rooms if room.room_type in kinds or room_kind(room.room_type) in kinds]
        if not target_rooms:
            return
        centre_x = sum(room.x + room.width / 2 for room in target_rooms) / len(target_rooms)
        centre_y = sum(room.y + room.length / 2 for room in target_rooms) / len(target_rooms)
        for room in target_rooms:
            room.x = round(centre_x + (room.x - centre_x) * factor, 4)
            room.y = round(centre_y + (room.y - centre_y) * factor, 4)
            room.width = round(room.width * factor, 4)
            room.length = round(room.length * factor, 4)
            room.area_sqft = round(room.width * room.length, 2)
