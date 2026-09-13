import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FloorPlanViewer } from './FloorPlanViewer';

describe('FloorPlanViewer', () => {
    it('renders rooms based on data', () => {
        const testData = {
            design_id: 'test-id',
            floor_count: 1,
            total_built_up_area_sqft: 100,
            rooms: [
                {
                    room_id: 'r1',
                    room_type: 'living_room',
                    floor: 1,
                    x: 0,
                    y: 0,
                    width: 10,
                    length: 10,
                    wall_height: 9,
                    doors: [],
                    windows: []
                }
            ]
        };

        const { container } = render(<FloorPlanViewer data={testData} pixelsPerFoot={10} />);
        
        // Find the room text by room type formatting (Living Room)
        expect(screen.getByText('Living Room')).toBeDefined();
        // The rect for the room should be drawn in the SVG
        const rects = container.querySelectorAll('rect');
        expect(rects.length).toBeGreaterThan(0);
    });

    it('renders "No rooms to display" when empty or filtered', () => {
        const testData = {
            design_id: 'test-id',
            floor_count: 1,
            total_built_up_area_sqft: 0,
            rooms: []
        };

        render(<FloorPlanViewer data={testData} pixelsPerFoot={10} />);
        expect(screen.getByText('No rooms to display for this floor.')).toBeDefined();
    });
});

describe('Procedural plan rendering', () => {
  it('fits irregular offset rooms, marks entries, and separates floors', () => {
    const room = { room_id: 'hall', room_type: 'hallway', floor: 1, x: -10, y: 5,
      width: 4, length: 20, wall_height: 9 };
    const data = { design_id: 'd', floor_count: 2, total_built_up_area_sqft: 500,
      rooms: [room, { ...room, room_id: 'bed', room_type: 'bedroom_1', x: -6, y: 15, width: 12, length: 10 },
        { ...room, room_id: 'stairs', room_type: 'staircase', floor: 2 }],
      entrances: [{ room_id: 'hall', wall: 'south' as const, offset: 0.5, width: 3 }] };
    const { container, rerender } = render(<FloorPlanViewer data={data} pixelsPerFoot={10} />);
    const viewBox = container.querySelector('svg')?.getAttribute('viewBox')?.split(' ').map(Number);
    expect(viewBox?.[2]).toBeGreaterThan(160);
    expect(viewBox?.[3]).toBeGreaterThan(200);
    expect(container.querySelector('[aria-label="Main entrance"]')).not.toBeNull();
    expect(container.querySelector('[aria-label="Staircase treads"]')).toBeNull();
    rerender(<FloorPlanViewer data={data} floorFilter={2} />);
    expect(container.querySelector('[aria-label="Staircase treads"]')).not.toBeNull();
    expect(container.textContent).not.toContain('Bedroom 1');
  });
});
