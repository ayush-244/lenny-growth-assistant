import React from 'react';
import { LennyLogo } from '../branding/LennyLogo';

export const LoadingState: React.FC = () => {
  return (
    <div className="message-wrapper assistant">
      <LennyLogo size={32} />
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
