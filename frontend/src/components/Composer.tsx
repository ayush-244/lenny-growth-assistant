import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface ComposerProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export const Composer: React.FC<ComposerProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = scrollHeight > 56 ? `${Math.min(scrollHeight, 200)}px` : '56px';
    }
  }, [input]);

  return (
    <div className="composer-container">
      <div className="composer-inner">
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
        <button
          className="composer-send"
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          aria-label="Send message"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
};
