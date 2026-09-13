import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types';
import { CitationList } from './CitationList';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`message-wrapper ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
        ) : (
          <>
            <div className="markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
            {'word_count' in message && (message as any).word_count > 0 && (
              <div className="essay-metadata" style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
                  <span><strong>Word Count:</strong> {(message as any).word_count}</span>
                  <span><strong>Attempts:</strong> {(message as any).generation_attempts}</span>
                </div>
                {(message as any).validation_issues && (message as any).validation_issues.length > 0 && (
                  <div style={{ color: 'var(--color-error)' }}>
                    <strong>Validation Issues:</strong> {(message as any).validation_issues.join(', ')}
                  </div>
                )}
              </div>
            )}
            {message.citations && message.citations.length > 0 && (
              <CitationList citations={message.citations} />
            )}
          </>
        )}
      </div>
    </div>
  );
};
