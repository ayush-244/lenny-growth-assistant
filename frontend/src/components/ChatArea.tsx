import React, { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { Composer } from './Composer';
import { EmptyState } from './chat/EmptyState';
import { LoadingState } from './chat/LoadingState';
import { QuickPrompts } from './chat/QuickPrompts';
import type { Message } from '../types';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  onSendMessage: (content: string) => void;
  onGenerateEssay?: (content: string) => void;
  onGenerateArtifact?: (content: string, type: 'markdown' | 'html') => void;
  onRetry?: () => void;
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  error,
  onSendMessage,
  onGenerateEssay,
  onGenerateArtifact,
  onRetry,
  inputRef,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const showHero = messages.length === 0 && !isLoading;
  const compactHero = messages.length > 0 && messages.length < 4;

  return (
    <div className="chat-container">
      <div className="messages-area">

        <div className="messages-content">
          {showHero && <EmptyState />}
          {compactHero && !showHero && <EmptyState compact />}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && <LoadingState />}

          {error && (
            <div className="error-card" role="alert">
              <strong>Something went wrong</strong>
              <p>I couldn’t complete that request right now.</p>
              {onRetry && (
                <button type="button" className="retry-btn" onClick={onRetry}>
                  Try again
                </button>
              )}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <Composer
        onSend={onSendMessage}
        onGenerateEssay={onGenerateEssay}
        onGenerateArtifact={onGenerateArtifact}
        disabled={isLoading}
        inputRef={inputRef}
      />
      <QuickPrompts onSelect={onSendMessage} disabled={isLoading} />
    </div>
  );
};
