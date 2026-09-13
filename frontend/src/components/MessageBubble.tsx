import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, ThumbsUp, ThumbsDown, MoreHorizontal, ShieldAlert } from 'lucide-react';
import type { Message } from '../types';
import { CitationList } from './CitationList';
import { LennyLogo } from './LennyLogo';

interface MessageBubbleProps {
  message: Message;
}

const INSUFFICIENT_PATTERN = /don't have enough evidence/i;

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const isInsufficient =
    !isUser && (!message.grounded || INSUFFICIENT_PATTERN.test(message.content));
  const essayMessage = message as Message & {
    word_count?: number;
    generation_attempts?: number;
    validation_issues?: string[];
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className={`message-wrapper ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="assistant-avatar">
          <LennyLogo size={32} />
        </div>
      )}
      <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
        {!isUser && (
          <div className="message-toolbar">
            {isInsufficient && (
              <span className="evidence-badge">
                <ShieldAlert size={14} />
                Evidence unavailable
              </span>
            )}
            <div className="message-actions">
              <button type="button" onClick={handleCopy} aria-label="Copy answer" title={copied ? 'Copied' : 'Copy'}>
                <Copy size={16} />
              </button>
              <button
                type="button"
                className={feedback === 'up' ? 'active' : ''}
                onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                aria-label="Like"
              >
                <ThumbsUp size={16} />
              </button>
              <button
                type="button"
                className={feedback === 'down' ? 'active' : ''}
                onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                aria-label="Dislike"
              >
                <ThumbsDown size={16} />
              </button>
              <button type="button" aria-label="More" title="More">
                <MoreHorizontal size={16} />
              </button>
            </div>
          </div>
        )}
        {isUser ? (
          <div className="user-message-text">{message.content}</div>
        ) : (
          <>
            <div className="markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
            {essayMessage.word_count && essayMessage.word_count > 0 && (
              <div className="essay-metadata">
                <div className="essay-meta-row">
                  <span><strong>Word Count:</strong> {essayMessage.word_count}</span>
                  <span><strong>Attempts:</strong> {essayMessage.generation_attempts ?? 0}</span>
                </div>
                {essayMessage.validation_issues && essayMessage.validation_issues.length > 0 && (
                  <div className="essay-issues">
                    <strong>Validation Issues:</strong>{' '}
                    {essayMessage.validation_issues.join(', ')}
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
