import React, { useState, useRef, useEffect } from 'react';
import { Send, FileText, Layout, Code, Paperclip, BookOpen } from 'lucide-react';

interface ComposerProps {
  onSend: (message: string) => void;
  onGenerateEssay?: (message: string) => void;
  onGenerateArtifact?: (message: string, type: 'markdown' | 'html') => void;
  disabled?: boolean;
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
}

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  onGenerateEssay,
  onGenerateArtifact,
  disabled,
  inputRef,
}) => {
  const [input, setInput] = useState('');
  const [groundedOnly, setGroundedOnly] = useState(true);
  const localRef = useRef<HTMLTextAreaElement>(null);
  const textareaRef = inputRef ?? localRef;

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleGenerateEssay = () => {
    if (input.trim() && !disabled && onGenerateEssay) {
      onGenerateEssay(input.trim());
      setInput('');
    }
  };

  const handleGenerateArtifact = (type: 'markdown' | 'html') => {
    if (input.trim() && !disabled && onGenerateArtifact) {
      onGenerateArtifact(input.trim(), type);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height =
        scrollHeight > 56 ? `${Math.min(scrollHeight, 200)}px` : '56px';
    }
  }, [input, textareaRef]);

  return (
    <div className="composer-container">
      <div className="composer-inner">
        <button
          type="button"
          className="composer-attach"
          disabled
          title="File attachments are not available yet"
          aria-label="Attach document"
        >
          <Paperclip size={18} />
        </button>
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Lenny about growth, retention, teams..."
          disabled={disabled}
          rows={1}
        />
        <div className="composer-actions">
          {onGenerateEssay && (
            <button
              className="composer-essay"
              onClick={handleGenerateEssay}
              disabled={disabled || !input.trim()}
              aria-label="Create Ship 30 essay"
              title="Create Ship 30 essay"
              type="button"
            >
              <FileText size={18} />
            </button>
          )}
          {onGenerateArtifact && (
            <>
              <button
                className="composer-artifact"
                onClick={() => handleGenerateArtifact('markdown')}
                disabled={disabled || !input.trim()}
                aria-label="Create Markdown Artifact"
                title="Create Markdown Artifact"
                type="button"
              >
                <Layout size={18} />
              </button>
              <button
                className="composer-artifact html"
                onClick={() => handleGenerateArtifact('html')}
                disabled={disabled || !input.trim()}
                aria-label="Create HTML Artifact"
                title="Create HTML Artifact"
                type="button"
              >
                <Code size={18} />
              </button>
            </>
          )}
          <label className="grounded-toggle" title="The assistant already answers from the knowledge base">
            <BookOpen size={16} />
            <span>Grounded answers only</span>
            <input
              type="checkbox"
              checked={groundedOnly}
              onChange={(e) => setGroundedOnly(e.target.checked)}
              aria-label="Grounded answers only"
            />
            <span className={`switch ${groundedOnly ? 'on' : ''}`} />
          </label>
          <button
            className="composer-send"
            onClick={handleSubmit}
            disabled={disabled || !input.trim()}
            aria-label="Send message"
            type="button"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};
