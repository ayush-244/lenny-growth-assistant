import React from 'react';
import type { Citation } from '../types';
import { BookOpen, Clock, User } from 'lucide-react';

interface CitationListProps {
  citations: Citation[];
}

export const CitationList: React.FC<CitationListProps> = ({ citations }) => {
  if (!citations || citations.length === 0) return null;

  const formatTimestamp = (seconds?: number | null) => {
    if (seconds == null) return null;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="citations-container">
      <div className="citations-title">
        <BookOpen size={14} /> Sources
      </div>
      <div className="citations-list">
        {citations.map((citation, idx) => {
          const tStart = formatTimestamp(citation.timestamp_start);
          const tEnd = formatTimestamp(citation.timestamp_end);
          const timeRange = tStart ? `${tStart}${tEnd ? `–${tEnd}` : ''}` : null;

          return (
            <div key={`${citation.chunk_id}-${idx}`} className="citation-card">
              <div className="citation-header">{citation.title}</div>
              <div className="citation-meta">
                {citation.guest_name && (
                  <span className="citation-meta-item">
                    <User size={12} /> {citation.guest_name}
                  </span>
                )}
                {timeRange && (
                  <span className="citation-meta-item">
                    <Clock size={12} /> {timeRange}
                  </span>
                )}
                {citation.source_url && (
                  <a 
                    href={citation.source_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="citation-link"
                  >
                    View source →
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
