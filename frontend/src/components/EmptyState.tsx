import React from 'react';
import { BookOpen, ShieldCheck, TrendingUp } from 'lucide-react';

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
      <p className="hero-subtitle">
        Ask questions, explore insights, and turn knowledge into action.
      </p>
      {!compact && (
        <div className="feature-pills">
          <div className="feature-pill">
            <BookOpen size={18} />
            Grounded in real content
          </div>
          <div className="feature-pill">
            <ShieldCheck size={18} />
            Citations you can trust
          </div>
          <div className="feature-pill">
            <TrendingUp size={18} />
            Built for growth
          </div>
        </div>
      )}
    </div>
  );
};
