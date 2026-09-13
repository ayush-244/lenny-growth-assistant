import React from 'react';

export const QuoteCard: React.FC = () => {
  return (
    <div className="quote-card">
      <span className="quote-mark" aria-hidden="true">“</span>
      <p className="quote-text">
        Great products don’t just happen, they’re built with intent.
      </p>
      <p className="quote-author">— Alex Rivera</p>
      <span className="quote-leaf" aria-hidden="true" />
    </div>
  );
};
