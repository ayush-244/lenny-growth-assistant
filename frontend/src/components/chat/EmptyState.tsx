import React from 'react';
import { BookOpen, Shield, LineChart } from 'lucide-react';

interface EmptyStateProps {
  compact?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ compact = false }) => {
  return (
    <div className={`hero-section ${compact ? 'compact' : ''}`}>
      <p className="hero-eyebrow">Your AI partner for</p>
      <h1 className="hero-title">
        Smarter <span>Growth</span> Decisions
      </h1>
      {!compact && (
        <>
          <p className="hero-subtitle">
            Ask questions, explore insights, and turn knowledge into action.
          </p>
          <div className="feature-pills">
            <div className="feature-pill">
              <BookOpen size={22} />
              <span>Grounded in real content</span>
            </div>
            <div className="feature-pill">
              <Shield size={22} />
              <span>Citations you can trust</span>
            </div>
            <div className="feature-pill">
              <LineChart size={22} />
              <span>Built for growth</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
