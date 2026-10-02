import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { useState } from 'react';
import { beforeEach, expect, test, vi } from 'vitest';
import { AIArchitectChat } from './AIArchitectChat';

const post = vi.fn();
vi.mock('../services/apiClient', () => ({ default: { post: (...args: unknown[]) => post(...args) } }));

function ChatHarness() {
  const [prompt, setPrompt] = useState('Design a compact home');
  return (
    <BrowserRouter>
      <AIArchitectChat isOpen setIsOpen={() => undefined} prompt={prompt} setPrompt={setPrompt} />
    </BrowserRouter>
  );
}

beforeEach(() => post.mockReset());

test('blocks repeated Enter submissions while interpretation is pending', async () => {
  let resolveRequest!: (value: { data: { reply: string } }) => void;
  post.mockReturnValue(new Promise(resolve => { resolveRequest = resolve; }));
  render(<ChatHarness />);
  const input = screen.getByPlaceholderText('Message AI Architect...');

  fireEvent.submit(input.closest('form')!);
  fireEvent.submit(input.closest('form')!);

  expect(post).toHaveBeenCalledOnce();
  expect(post).toHaveBeenCalledWith('/assistant/interpret', expect.any(Object));
  resolveRequest({ data: { reply: 'Ready.' } });
  await waitFor(() => expect(screen.getByText('Ready.')).toBeTruthy());
});
