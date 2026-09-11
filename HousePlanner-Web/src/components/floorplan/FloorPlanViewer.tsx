import React from 'react';

// Interfaces matching the layout schema
export interface Opening {
  wall: 'north' | 'south' | 'east' | 'west';
  offset: number;
  width: number;
}

export interface Room {
  room_id: string;
  room_type: string;
  name?: string;
  floor: number;
  x: number;
  y: number;
  width: number;
  length: number;
  wall_height: number;
  doors: Opening[];
  windows: Opening[];
}

export interface FloorPlanData {
  design_id: string;
  floor_count: number;
  total_built_up_area_sqft: number;
  rooms: Room[];
}

interface FloorPlanViewerProps {
  data: FloorPlanData;
  pixelsPerFoot?: number;
  /** If set, only render rooms on this floor number */
  floorFilter?: number;
}

// Color palette for distinguishing rooms by type
const ROOM_COLORS: Record<string, string> = {
  living_room: '#E0F2FE',
  dining_room: '#FCE7F3',
  kitchen: '#FEF3C7',
  bedroom_1: '#DBEAFE',
  bedroom_2: '#E0E7FF',
  bedroom_3: '#EDE9FE',
  bedroom_4: '#F3E8FF',
  bathroom_1: '#D1FAE5',
  bathroom_2: '#D1FAE5',
  bathroom_3: '#D1FAE5',
  staircase: '#F1F5F9',
  staircase_upper: '#F1F5F9',
};

const DEFAULT_ROOM_COLOR = '#F8FAFC';

export const FloorPlanViewer: React.FC<FloorPlanViewerProps> = ({ data, pixelsPerFoot = 20, floorFilter }) => {
  // Filter rooms by floor if specified
  const displayRooms = floorFilter
    ? data.rooms.filter((r) => r.floor === floorFilter)
    : data.rooms;

  if (displayRooms.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#94a3b8' }}>
        No rooms to display for this floor.
      </div>
    );
  }

  // Calculate bounding box for the displayed rooms
  const minX = Math.min(...displayRooms.map((r) => r.x));
  const minY = Math.min(...displayRooms.map((r) => r.y));
  const maxX = Math.max(...displayRooms.map((r) => r.x + r.width));
  const maxY = Math.max(...displayRooms.map((r) => r.y + r.length));

  const totalWidth = (maxX - minX) * pixelsPerFoot;
  const totalHeight = (maxY - minY) * pixelsPerFoot;
  const padding = 50;

  const formatRoomLabel = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
        backgroundColor: '#f8f9fa',
        overflow: 'auto',
        padding: '20px',
      }}
    >
      <svg
        width={totalWidth + padding * 2}
        height={totalHeight + padding * 2}
        style={{
          backgroundColor: '#ffffff',
          boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
          borderRadius: '8px',
          backgroundImage: 'linear-gradient(#f0f0f0 1px, transparent 1px), linear-gradient(90deg, #f0f0f0 1px, transparent 1px)',
          backgroundSize: `${pixelsPerFoot}px ${pixelsPerFoot}px`,
          backgroundPosition: `${padding}px ${padding}px`
        }}
      >
        <g transform={`translate(${padding}, ${padding})`}>
          {displayRooms.map((room) => {
            // Transform coordinates: SVG (0,0) is top-left, JSON (0,0) is bottom-left
            const svgX = (room.x - minX) * pixelsPerFoot;
            const svgY = (maxY - (room.y + room.length)) * pixelsPerFoot;
            const svgWidth = room.width * pixelsPerFoot;
            const svgHeight = room.length * pixelsPerFoot;

            const roomCenterY = svgY + svgHeight / 2;
            const roomCenterX = svgX + svgWidth / 2;

            const fillColor = ROOM_COLORS[room.room_type] || DEFAULT_ROOM_COLOR;

            return (
              <g key={room.room_id}>
                {/* Floor fill with room-type color */}
                <rect
                  x={svgX}
                  y={svgY}
                  width={svgWidth}
                  height={svgHeight}
                  fill={fillColor}
                  stroke="none"
                />

                {/* Walls (Stroke) */}
                <rect
                  x={svgX}
                  y={svgY}
                  width={svgWidth}
                  height={svgHeight}
                  fill="none"
                  stroke="#334155"
                  strokeWidth="3"
                />

                {/* Windows (light blue gaps) */}
                {room.windows.map((win, i) => renderOpening(win, room, svgX, svgY, svgWidth, svgHeight, pixelsPerFoot, 'window', i))}

                {/* Doors (white gaps) */}
                {room.doors.map((door, i) => renderOpening(door, room, svgX, svgY, svgWidth, svgHeight, pixelsPerFoot, 'door', i))}

                {/* Room Label */}
                <text
                  x={roomCenterX}
                  y={roomCenterY - 8}
                  textAnchor="middle"
                  alignmentBaseline="middle"
                  fill="#334155"
                  fontFamily="'Inter', 'Roboto', sans-serif"
                  fontSize="13"
                  fontWeight="600"
                >
                  {room.name || formatRoomLabel(room.room_type)}
                </text>

                {/* Dimensions */}
                <text
                  x={roomCenterX}
                  y={roomCenterY + 10}
                  textAnchor="middle"
                  alignmentBaseline="middle"
                  fill="#94a3b8"
                  fontFamily="'Inter', 'Roboto', sans-serif"
                  fontSize="11"
                >
                  {room.width}&apos; × {room.length}&apos;
                </text>

                {/* Area */}
                <text
                  x={roomCenterX}
                  y={roomCenterY + 24}
                  textAnchor="middle"
                  alignmentBaseline="middle"
                  fill="#cbd5e1"
                  fontFamily="'Inter', 'Roboto', sans-serif"
                  fontSize="10"
                >
                  {Math.round(room.width * room.length)} sqft
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};

// Helper function to render a door or window opening
function renderOpening(
  opening: Opening,
  room: Room,
  svgX: number,
  svgY: number,
  svgWidth: number,
  svgHeight: number,
  scale: number,
  type: 'door' | 'window',
  index: number
) {
  const isWindow = type === 'window';
  const color = isWindow ? '#bae6fd' : '#ffffff';
  const strokeWidth = 6;

  let ox = 0;
  let oy = 0;
  let oWidth = 0;
  let oHeight = 0;

  const scaledOffset = opening.offset * scale;
  const scaledWidth = opening.width * scale;

  switch (opening.wall) {
    case 'north':
      ox = svgX + scaledOffset;
      oy = svgY - strokeWidth / 2;
      oWidth = scaledWidth;
      oHeight = strokeWidth;
      break;
    case 'south':
      ox = svgX + scaledOffset;
      oy = svgY + svgHeight - strokeWidth / 2;
      oWidth = scaledWidth;
      oHeight = strokeWidth;
      break;
    case 'east':
      ox = svgX + svgWidth - strokeWidth / 2;
      oy = svgY + svgHeight - scaledOffset - scaledWidth;
      oWidth = strokeWidth;
      oHeight = scaledWidth;
      break;
    case 'west':
      ox = svgX - strokeWidth / 2;
      oy = svgY + svgHeight - scaledOffset - scaledWidth;
      oWidth = strokeWidth;
      oHeight = scaledWidth;
      break;
  }

  return (
    <rect
      key={`${type}-${index}`}
      x={ox}
      y={oy}
      width={oWidth}
      height={oHeight}
      fill={color}
    />
  );
}
