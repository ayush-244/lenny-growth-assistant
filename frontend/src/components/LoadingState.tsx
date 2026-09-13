import React from 'react';
import { LennyLogo } from './LennyLogo';

export const LoadingState: React.FC = () => {
  return (
    <div className="message-wrapper assistant">
      <div className="assistant-avatar">
        <LennyLogo size={32} />
      </div>
      <div className="message-bubble assistant loading-bubble">
        <div className="typing-indicator" aria-label="Thinking from the knowledge base">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
        <p className="loading-copy">Thinking from the knowledge base…</p>
      </div>
    </div>
  );
};
