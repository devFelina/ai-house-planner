import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ConstructorRequestDetails from './ConstructorRequestDetails';
import { constructorWorkflowService } from '../../../services/constructorWorkflowService';

vi.mock('../../../services/constructorWorkflowService');

const baseRequest = {
  id: 'request-1',
  status: 'Pending',
  title: 'Approved Design v1',
  customerName: 'Customer',
  requestedAt: '2026-10-03T00:00:00Z',
  bedrooms: 3,
  bathrooms: 2,
  floorCount: 1,
  area: 1200,
  cost: null,
};

const renderPage = () => render(
  <MemoryRouter initialEntries={['/constructor/requests/request-1']}>
    <Routes>
      <Route path="/constructor/requests/:requestId" element={<ConstructorRequestDetails />} />
    </Routes>
  </MemoryRouter>,
);

describe('ConstructorRequestDetails approved design', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the design visualization without using a legacy image URL', async () => {
    const signedUrl = 'https://project.supabase.co/storage/v1/object/sign/ai-visualizations/file.png?token=x';
    vi.mocked(constructorWorkflowService.getConstructorRequest).mockResolvedValue({
      ...baseRequest,
      aiVisualizationUrl: signedUrl,
      aiVisualizationStatus: 'completed',
      technicalPlanImage: 'http://localhost:8001/plans/legacy.png',
      layoutJson: '{"rooms":[{"room_type":"bedroom"}]}',
    });

    renderPage();

    expect(await screen.findByText('Design Visualization')).toBeInTheDocument();

    const img = screen.getByRole('img', { name: /Approved design visualization/i });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', signedUrl);

    expect(screen.queryByText('Floor Plan')).not.toBeInTheDocument();
  });

  it('shows a fallback when AI visualization is missing and keeps design info available', async () => {
    vi.mocked(constructorWorkflowService.getConstructorRequest).mockResolvedValue({
      ...baseRequest,
      aiVisualizationUrl: null,
      aiVisualizationStatus: 'failed',
      technicalPlanImage: '/plans/legacy.png',
      layoutJson: '{"rooms":[]}',
    });

    renderPage();

    await waitFor(() => expect(screen.getByText('Design Information')).toBeInTheDocument());
    expect(screen.getByText('Design Visualization')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText('Visualization image is not available for this design.')).toBeInTheDocument();
    expect(screen.queryByText('Floor Plan')).not.toBeInTheDocument();
  });
});
