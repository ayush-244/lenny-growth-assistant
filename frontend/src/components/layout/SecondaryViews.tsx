import React from 'react';
import { BookOpen, History as HistoryIcon, Sparkles } from 'lucide-react';
import type { Artifact, Session } from '../../types';
import { formatRelativeTime } from '../../lib/format';

interface PlaceholderViewProps {
  title: string;
  body: string;
  icon: React.ReactNode;
}

export const PlaceholderView: React.FC<PlaceholderViewProps> = ({ title, body, icon }) => {
  return (
    <div className="page-placeholder">
      <div className="page-placeholder-icon">{icon}</div>
      <h1>{title}</h1>
      <p>{body}</p>
    </div>
  );
};

export const KnowledgeView: React.FC = () => (
  <PlaceholderView
    icon={<BookOpen size={28} />}
    title="Knowledge Base"
    body="Browse and search the Lenny knowledge base from Chat. A dedicated library view is not available yet."
  />
);

interface HistoryViewProps {
  sessions: Session[];
  onSelectSession: (id: string) => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({ sessions, onSelectSession }) => {
  if (sessions.length === 0) {
    return (
      <PlaceholderView
        icon={<HistoryIcon size={28} />}
        title="History"
        body="Conversations you start in this browser will appear here."
      />
    );
  }

  return (
    <div className="history-page">
      <h1>History</h1>
      <ul>
        {sessions.map((session, index) => (
          <li key={session.id}>
            <button type="button" onClick={() => onSelectSession(session.id)}>
              <span>{session.metadata_?.title || `Conversation ${sessions.length - index}`}</span>
              <span>{formatRelativeTime(session.updated_at || session.created_at)}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

interface ArtifactsViewProps {
  artifacts: Artifact[];
  isLoading: boolean;
  error: string | null;
  onOpen: (artifact: Artifact) => void;
  hasSession: boolean;
}

export const ArtifactsView: React.FC<ArtifactsViewProps> = ({
  artifacts,
  isLoading,
  error,
  onOpen,
  hasSession,
}) => {
  if (!hasSession) {
    return (
      <PlaceholderView
        icon={<Sparkles size={28} />}
        title="Artifacts"
        body="Start a conversation, then generate a markdown or HTML artifact from the composer."
      />
    );
  }

  if (isLoading) {
    return <PlaceholderView icon={<Sparkles size={28} />} title="Artifacts" body="Loading artifacts…" />;
  }

  if (error) {
    return <PlaceholderView icon={<Sparkles size={28} />} title="Artifacts" body={error} />;
  }

  if (artifacts.length === 0) {
    return (
      <PlaceholderView
        icon={<Sparkles size={28} />}
        title="Artifacts"
        body="No artifacts in this conversation yet. Use the layout or code icons in the composer to create one."
      />
    );
  }

  return (
    <div className="history-page">
      <h1>Artifacts</h1>
      <ul>
        {artifacts.map((artifact) => (
          <li key={artifact.id}>
            <button type="button" onClick={() => onOpen(artifact)}>
              <span>{artifact.title || artifact.request.slice(0, 48)}</span>
              <span>{artifact.artifact_type.toUpperCase()}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};
