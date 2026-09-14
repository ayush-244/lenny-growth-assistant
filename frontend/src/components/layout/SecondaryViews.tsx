import React from 'react';
import { BookOpen, History as HistoryIcon, Sparkles } from 'lucide-react';
import type { Artifact, KnowledgeEpisode, Session } from '../../types';
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

interface KnowledgeViewProps {
  episodes: KnowledgeEpisode[];
  isLoading: boolean;
  error: string | null;
}

const formatTimestamp = (seconds: number | null) => {
  if (seconds === null) return '--:--';

  const totalSeconds = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;

  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

export const KnowledgeView: React.FC<KnowledgeViewProps> = ({
  episodes,
  isLoading,
  error,
}) => {
  if (isLoading) {
    return (
      <PlaceholderView
        icon={<BookOpen size={28} />}
        title="Knowledge Base"
        body="Loading indexed knowledge..."
      />
    );
  }

  if (error) {
    return (
      <PlaceholderView
        icon={<BookOpen size={28} />}
        title="Knowledge Base"
        body={error}
      />
    );
  }

  if (episodes.length === 0) {
    return (
      <PlaceholderView
        icon={<BookOpen size={28} />}
        title="Knowledge Base"
        body="No indexed transcript content is available yet."
      />
    );
  }

  return (
    <div className="knowledge-page">
      <div className="knowledge-page-header">
        <div>
          <h1>Knowledge Base</h1>
          <p>
            Browse the indexed transcript evidence available to the Growth
            Assistant.
          </p>
        </div>

        <div className="knowledge-page-count">
          {episodes.length} {episodes.length === 1 ? 'source' : 'sources'}
        </div>
      </div>

      <div className="knowledge-list">
        {episodes.map((episode) => (
          <article className="knowledge-card" key={episode.id}>
            <div className="knowledge-card-header">
              <div>
                <h2>{episode.title}</h2>

                {episode.guest_name && (
                  <p className="knowledge-guest">
                    Featuring {episode.guest_name}
                  </p>
                )}
              </div>

              <span className="knowledge-chunk-count">
                {episode.chunk_count} indexed chunks
              </span>
            </div>

            {episode.source_url && (
              <a
                className="knowledge-source-link"
                href={episode.source_url}
                target="_blank"
                rel="noreferrer"
              >
                View source →
              </a>
            )}

            <div className="knowledge-chunks">
              {episode.chunks.map((chunk) => (
                <details key={chunk.id} className="knowledge-chunk">
                  <summary>
                    <span>
                      {formatTimestamp(chunk.timestamp_start)} –{' '}
                      {formatTimestamp(chunk.timestamp_end)}
                    </span>

                    <span>Chunk {chunk.chunk_index + 1}</span>
                  </summary>

                  <p>{chunk.content}</p>
                </details>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
};

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
