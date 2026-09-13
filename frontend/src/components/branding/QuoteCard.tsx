import React from 'react';

export const QuoteCard: React.FC = () => {
  return (
    <div className="quote-card">
      <span className="quote-mark" aria-hidden="true">
        “
      </span>
      <p className="quote-text">
        Great products don’t just happen, they’re built with intent.
      </p>
      <p className="quote-author">— Alex Rivera</p>
      <svg className="quote-leaf" viewBox="0 0 80 80" aria-hidden="true">
        <path
          d="M62 18c-14 2-28 14-34 30 10-4 22-6 30-16-8 14-22 22-36 26 16 2 34-8 40-24 2-6 2-12 0-16Z"
          fill="currentColor"
        />
      </svg>
    </div>
  );
};
