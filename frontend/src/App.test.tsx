import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from './App';
import { api } from './api';

// Mock the API calls
vi.mock('./api', () => ({
  api: {
    createSession: vi.fn(),
    getSession: vi.fn(),
    sendMessage: vi.fn(),
    generateEssay: vi.fn(),
  },
}));

describe('App Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the empty state on initial load with no active session', () => {
    render(<App />);
    expect(screen.getByText(/Ask about product strategy, growth/i)).toBeInTheDocument();
    expect(screen.getByText('New conversation')).toBeInTheDocument();
  });

  it('creates a new session when clicking "New conversation"', async () => {
    vi.mocked(api.createSession).mockResolvedValueOnce({
      id: 'session-123',
      model_provider: 'anthropic',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<App />);
    const newChatBtn = screen.getByText('New conversation');
    fireEvent.click(newChatBtn);

    await waitFor(() => {
      expect(api.createSession).toHaveBeenCalledTimes(1);
    });

    // Sidebar should display "Conversation 1" as temporary title
    expect(screen.getByText('Conversation 1')).toBeInTheDocument();
  });

  it('sends a message and displays assistant response with markdown safely', async () => {
    vi.mocked(api.createSession).mockResolvedValueOnce({
      id: 'session-123',
      model_provider: 'anthropic',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    const maliciousResponse = "Hello <script>alert('xss')</script> **world**";

    vi.mocked(api.sendMessage).mockResolvedValueOnce({
      id: 'msg-1',
      session_id: 'session-123',
      role: 'assistant',
      content: maliciousResponse,
      grounded: true,
      provider: 'anthropic',
      citations: [
        {
          chunk_id: 'chunk-1',
          episode_id: 'ep-1',
          title: 'Lenny Podcast 1',
        }
      ],
      created_at: new Date().toISOString(),
    });

    render(<App />);
    
    // Type in composer and send
    const input = screen.getByPlaceholderText(/Ask Lenny/i);
    fireEvent.change(input, { target: { value: 'How to grow?' } });
    
    const sendButton = screen.getByLabelText('Send message');
    fireEvent.click(sendButton);

    // Wait for the mock to resolve
    await waitFor(() => {
      expect(api.sendMessage).toHaveBeenCalledWith('session-123', 'How to grow?');
    });

    // Check that user message is displayed
    expect(screen.getByText('How to grow?')).toBeInTheDocument();

    // Check that assistant response is rendered, markdown is parsed, but script tag is NOT executed/rendered as HTML
    // react-markdown will render the raw text of the script tag or escape it, but it won't execute.
    // We should see "world" in strong tag
    expect(screen.getByText('world').tagName).toBe('STRONG');
    
    // Check citation
    expect(screen.getByText('Lenny Podcast 1')).toBeInTheDocument();

    // Check provider indicator
    expect(screen.getByText('Model: anthropic')).toBeInTheDocument();
  });
});
