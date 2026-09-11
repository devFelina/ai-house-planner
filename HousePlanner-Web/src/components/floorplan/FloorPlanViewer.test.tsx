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
