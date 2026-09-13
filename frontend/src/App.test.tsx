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
    generateArtifact: vi.fn(),
    listArtifacts: vi.fn(),
    updateSessionProvider: vi.fn(),
  },
}));

describe('App Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the empty state on initial load with no active session', () => {
    render(<App />);
    expect(screen.getByText(/Ask questions, explore insights/i)).toBeInTheDocument();
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
    expect(screen.getByText(/Model: anthropic · Claude/i)).toBeInTheDocument();
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
    expect(screen.getAllByText('Lenny Podcast 1').length).toBeGreaterThan(0);

    // Check provider indicator
    expect(screen.getByText(/Model: anthropic · Claude/i)).toBeInTheDocument();
  });

  it('switches the selected conversation provider only after a successful PATCH', async () => {
    vi.mocked(api.createSession).mockResolvedValueOnce({
      id: 'session-123', model_provider: 'ollama', model: 'llama3.2:3b',
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
    vi.mocked(api.updateSessionProvider).mockResolvedValueOnce({
      session_id: 'session-123', provider: 'anthropic', model: 'claude-test',
    });

    render(<App />);
    fireEvent.click(screen.getByText('New conversation'));
    await screen.findByLabelText('Select model');
    fireEvent.click(screen.getByLabelText('Select model'));
    expect(screen.getByText('Ollama')).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Anthropic'));

    await waitFor(() => {
      expect(api.updateSessionProvider).toHaveBeenCalledWith('session-123', 'anthropic');
    });
    expect(screen.getByText(/Model: anthropic · claude-test/i)).toBeInTheDocument();
  });

  it('keeps the selector open and shows a friendly error when PATCH fails', async () => {
    vi.mocked(api.createSession).mockResolvedValueOnce({
      id: 'session-123', model_provider: 'ollama', model: 'llama3.2:3b',
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
    vi.mocked(api.updateSessionProvider).mockRejectedValueOnce(new Error('network unavailable'));

    render(<App />);
    fireEvent.click(screen.getByText('New conversation'));
    await screen.findByLabelText('Select model');
    fireEvent.click(screen.getByLabelText('Select model'));
    fireEvent.click(screen.getByText('Anthropic'));

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to switch model. Please try again.');
    expect(screen.getByText(/Model: ollama · llama3.2:3b/i)).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('uses the backend provider for each session when switching conversations', async () => {
    localStorage.setItem('activeSessionId', 'session-a');
    vi.mocked(api.getSession).mockResolvedValue({
      id: 'session-a', model_provider: 'ollama', model: 'llama3.2:3b', messages: [],
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
    vi.mocked(api.createSession).mockResolvedValueOnce({
      id: 'session-b', model_provider: 'anthropic', model: 'claude-test',
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });

    render(<App />);
    expect(await screen.findByText(/Model: ollama · llama3.2:3b/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText('New conversation'));
    expect(await screen.findByText(/Model: anthropic · claude-test/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Conversation 1'));
    expect(await screen.findByText(/Model: ollama · llama3.2:3b/i)).toBeInTheDocument();
  });
});
