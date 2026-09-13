export interface Citation {
  chunk_id: string;
  episode_id: string;
  title: string;
  guest_name?: string | null;
  source_url?: string | null;
  timestamp_start?: number | null;
  timestamp_end?: number | null;
  /** Present only if the API includes it; never invented client-side. */
  similarity_score?: number | null;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[] | null;
  grounded: boolean;
  provider?: string | null;
  created_at: string;
}

export interface EssayResponse extends Message {
  word_count: number;
  generation_attempts: number;
  insufficient_evidence: boolean;
  validation_issues: string[];
}

export interface Session {
  id: string;
  model_provider: string;
  model?: string;
  metadata_?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface ProviderUpdate {
  session_id: string;
  provider: 'ollama' | 'anthropic';
  model: string;
}

export interface SessionWithMessages extends Session {
  messages: Message[];
}

export type ArtifactType = 'markdown' | 'html';

export interface Artifact {
  id: string;
  session_id: string;
  artifact_type: ArtifactType;
  content: string;
  request: string;
  grounded: boolean;
  provider?: string | null;
  title?: string | null;
  created_at: string;
}
