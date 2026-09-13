import React from 'react';
import {
  ArrowUpRight,
  Target,
  Users,
  TrendingUp,
  Lightbulb,
  Leaf,
  ArrowRight,
} from 'lucide-react';
import type { Citation } from '../types';

interface SourcesPanelProps {
  citations: Citation[];
  insights: string[];
  insufficientEvidence: boolean;
  onAction?: () => void;
}

function formatTimestamp(seconds?: number | null): string | null {
  if (seconds == null) return null;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const INSIGHT_ICONS = [Target, Users, TrendingUp];

export const SourcesPanel: React.FC<SourcesPanelProps> = ({
  citations,
  insights,
  insufficientEvidence,
  onAction,
}) => {
  return (
    <aside className="sources-panel" aria-label="Sources and insights">
      <section className="panel-card">
        <div className="panel-card-header">
          <h2>Sources Used</h2>
          <span className="panel-count">{citations.length}</span>
        </div>
        {citations.length === 0 ? (
          <p className="panel-empty">Sources from grounded answers will appear here.</p>
        ) : (
          <ol className="source-list">
            {citations.map((citation, idx) => {
              const tStart = formatTimestamp(citation.timestamp_start);
              const tEnd = formatTimestamp(citation.timestamp_end);
              const timeRange = tStart ? `${tStart}${tEnd ? ` – ${tEnd}` : ''}` : null;
              return (
                <li key={`${citation.chunk_id}-${idx}`} className="source-row">
                  <span className="source-index">{idx + 1}</span>
                  <div className="source-row-body">
                    <p className="source-title">{citation.title}</p>
                    <p className="source-meta">
                      {citation.guest_name || 'Lenny’s Podcast'}
                      {timeRange ? ` · ${timeRange}` : ''}
                    </p>
                  </div>
                  {citation.source_url && (
                    <a
                      href={citation.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="source-open"
                      aria-label="Open source"
                    >
                      <ArrowUpRight size={16} />
                    </a>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <section className="panel-card">
        <div className="panel-card-header">
          <h2>
            <Lightbulb size={16} /> Key Insights
          </h2>
        </div>
        <p className="panel-note">From this answer — not additional retrieved evidence.</p>
        {insufficientEvidence || insights.length === 0 ? (
          <p className="panel-empty">Insights appear after a grounded answer.</p>
        ) : (
          <ul className="insight-list">
            {insights.map((insight, idx) => {
              const Icon = INSIGHT_ICONS[idx % INSIGHT_ICONS.length];
              return (
                <li key={idx} className="insight-row">
                  <span className="insight-icon">
                    <Icon size={16} />
                  </span>
                  <p>{insight}</p>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="action-card">
        <div className="action-card-icon">
          <Leaf size={22} />
        </div>
        <div>
          <h2>Knowledge into Action</h2>
          <p>Learn from the best. Build what’s next.</p>
        </div>
        <button
          type="button"
          className="action-card-btn"
          onClick={onAction}
          aria-label="Ask a follow-up question"
        >
          <ArrowRight size={18} />
        </button>
      </section>
    </aside>
  );
};
