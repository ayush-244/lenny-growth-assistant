import React from 'react';
import { FileText, ExternalLink, Lightbulb, Target, Users, LineChart, Leaf, ArrowRight } from 'lucide-react';
import type { Citation } from '../../types';
import { formatTimeRange } from '../../lib/format';

interface SourcesPanelProps {
  citations: Citation[];
  onFocusComposer: () => void;
}

const PRINCIPLES = [
  {
    icon: <Target size={16} />,
    text: 'Product strategy aligns customer needs with business growth.',
  },
  {
    icon: <Users size={16} />,
    text: 'Focus on solving real problems.',
  },
  {
    icon: <LineChart size={16} />,
    text: 'Drives adoption, retention, and long-term success.',
  },
];

export const SourcesPanel: React.FC<SourcesPanelProps> = ({ citations, onFocusComposer }) => {
  return (
    <aside className="sources-panel" aria-label="Sources and insights">
      <section className="panel-card">
        <div className="panel-card-header">
          <h2>Sources Used</h2>
          <span className="count-badge">{citations.length}</span>
        </div>
        {citations.length === 0 ? (
          <p className="panel-empty">Sources from grounded answers will appear here.</p>
        ) : (
          <ol className="source-list">
            {citations.map((citation, idx) => {
              const timeRange = formatTimeRange(citation.timestamp_start, citation.timestamp_end);
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
                  {citation.source_url ? (
                    <a
                      className="icon-btn source-open"
                      href={citation.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label="Open source"
                    >
                      <ExternalLink size={16} />
                    </a>
                  ) : (
                    <FileText size={16} className="source-doc-icon" />
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
        <p className="panel-caption">Guiding principles — not retrieved evidence.</p>
        <ul className="insight-list">
          {PRINCIPLES.map((item) => (
            <li key={item.text}>
              <span className="insight-icon">{item.icon}</span>
              <span>{item.text}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel-card action-card">
        <Leaf size={22} />
        <h2>
          Knowledge
          <br />
          into Action
        </h2>
        <p>Learn from the best. Build what’s next.</p>
        <button type="button" className="action-arrow" onClick={onFocusComposer} aria-label="Ask Lenny">
          <ArrowRight size={18} />
        </button>
      </section>
    </aside>
  );
};
