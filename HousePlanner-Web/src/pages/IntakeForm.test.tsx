import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { beforeEach, expect, test, vi } from 'vitest';
import IntakeForm from './IntakeForm';

const startDesign = vi.fn();
vi.mock('../services/workflowService', () => ({ workflowService: { startDesign: (...args: unknown[]) => startDesign(...args) } }));
const renderPage = () => render(<BrowserRouter><IntakeForm /></BrowserRouter>);
beforeEach(() => { startDesign.mockReset(); startDesign.mockResolvedValue({ workflowId: 'workflow-1' }); });

test('offers only supported land and room choices', () => {
  renderPage();
  expect(screen.getByRole('button', { name: /Small Plot/ })).toBeTruthy();
  expect(screen.getByRole('button', { name: /Medium Plot/ })).toBeTruthy();
  expect(screen.queryByRole('button', { name: /Large Plot/ })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /Small Plot/ }));
  fireEvent.click(screen.getByRole('button', { name: /Next/ }));
  expect(screen.getByText('How many rooms does your family need?')).toBeTruthy();
  expect(screen.getByRole('button', { name: '3 Bedrooms' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: '4 Bedrooms' })).toBeNull();
  expect(screen.getByRole('button', { name: '2 Bathrooms' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: '3 Bathrooms' })).toBeNull();
});

test('submits the five-field simplified payload', async () => {
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: /Small Plot/ }));
  fireEvent.click(screen.getByRole('button', { name: /Next/ }));
  fireEvent.click(screen.getByRole('button', { name: '3 Bedrooms' }));
  fireEvent.click(screen.getByRole('button', { name: '2 Bathrooms' }));
  fireEvent.click(screen.getByRole('button', { name: /Next/ }));
  fireEvent.click(screen.getByRole('button', { name: /Modern Family Home/ }));
  fireEvent.click(screen.getByRole('button', { name: /Generate AI Plan/ }));
  await waitFor(() => expect(startDesign).toHaveBeenCalledOnce());
  expect(startDesign).toHaveBeenCalledWith({ landSizeCategory: 'small', landSizePerches: 15, bedrooms: 3, bathrooms: 2, houseType: 'modern' });
});

test('blocks two immediate generation submissions', async () => {
  let resolveRequest!: (value: { workflowId: string }) => void;
  startDesign.mockReturnValue(new Promise(resolve => { resolveRequest = resolve; }));
  renderPage();
  fireEvent.click(screen.getByRole('button', { name: /Small Plot/ }));
  fireEvent.click(screen.getByRole('button', { name: /Next/ }));
  fireEvent.click(screen.getByRole('button', { name: '1 Bedroom' }));
  fireEvent.click(screen.getByRole('button', { name: '1 Bathroom (Recommended)' }));
  fireEvent.click(screen.getByRole('button', { name: /Next/ }));
  fireEvent.click(screen.getByRole('button', { name: /Simple Family Home/ }));
  const submit = screen.getByRole('button', { name: /Generate AI Plan/ });

  fireEvent.click(submit);
  fireEvent.click(submit);

  expect(startDesign).toHaveBeenCalledOnce();
  resolveRequest({ workflowId: 'workflow-1' });
  await waitFor(() => expect(screen.getByText('Project Created!')).toBeTruthy());
});
