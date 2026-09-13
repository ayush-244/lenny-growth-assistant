import type { Session, SessionWithMessages, Message, EssayResponse, Artifact } from './types';

// Use standard vite environment variable convention for API URL
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' 
          ? errorData.detail 
          : JSON.stringify(errorData.detail);
      }
    } catch {
      // Failed to parse JSON error, use status text
      if (response.statusText) errorMessage += `: ${response.statusText}`;
    }
    throw new ApiError(errorMessage, response.status);
  }
  return response.json();
}

export const api = {
  async createSession(): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<Session>(response);
  },

  async getSession(sessionId: string): Promise<SessionWithMessages> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
    return handleResponse<SessionWithMessages>(response);
  },

  async sendMessage(sessionId: string, content: string): Promise<Message> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    return handleResponse<Message>(response);
  },

  async generateEssay(sessionId: string, content: string): Promise<EssayResponse> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/essay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    return handleResponse<EssayResponse>(response);
  },

  async generateArtifact(sessionId: string, request: string, artifactType: string): Promise<Artifact> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/artifacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request, artifact_type: artifactType }),
    });
    return handleResponse<Artifact>(response);
  },

  async listArtifacts(sessionId: string): Promise<Artifact[]> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/artifacts`);
    return handleResponse<Artifact[]>(response);
  },
};
