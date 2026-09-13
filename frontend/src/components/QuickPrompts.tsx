import React from 'react';

const PROMPTS = [
  'Growth strategy advice',
  'How to improve retention?',
  'Product-led growth',
  'Team building tips',
  'Go-to-market strategy',
];

interface QuickPromptsProps {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
}

export const QuickPrompts: React.FC<QuickPromptsProps> = ({ onSelect, disabled }) => {
  return (
    <div className="quick-prompts">
      <span className="quick-prompts-label">Try asking:</span>
      <div className="quick-prompts-list">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="quick-prompt-pill"
            disabled={disabled}
            onClick={() => onSelect(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
};
