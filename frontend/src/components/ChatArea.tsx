import React, { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { Composer } from './Composer';
import type { Message } from '../types';

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  provider: string | null;
  onSendMessage: (content: string) => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  error,
  provider,
  onSendMessage,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-container">
      <div className="chat-header">
        {provider && (
          <div className="provider-badge">Model: {provider}</div>
        )}
      </div>

      <div className="messages-area">
        <div className="messages-content">
          {messages.length === 0 && !isLoading && (
            <div className="empty-state">
              <h1 className="empty-title">Lenny Growth Assistant</h1>
              <p className="empty-subtitle">
                Ask about product strategy, growth, retention, teams, or lessons from Lenny's podcast and newsletter.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isLoading && (
            <div className="message-wrapper assistant">
              <div className="message-bubble assistant">
                <div className="typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="error-banner">
              <strong>Error:</strong> {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <Composer onSend={onSendMessage} disabled={isLoading} />
    </div>
  );
};
