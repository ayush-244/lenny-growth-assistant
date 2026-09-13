import React from 'react';
import {
  MessageSquare,
  BookOpen,
  Sparkles,
  History,
  Settings,
  Sun,
  Menu,
  ChevronDown,
  Bot,
  Check,
  LoaderCircle,
} from 'lucide-react';

export type AppView = 'chat' | 'knowledge' | 'artifacts' | 'history';

interface TopNavProps {
  activeView: AppView;
  onChangeView: (view: AppView) => void;
  provider: string | null;
  model: string | null;
  hasSession: boolean;
  isSwitchingProvider: boolean;
  providerError: string | null;
  onChangeProvider: (provider: 'ollama' | 'anthropic') => Promise<boolean>;
  onToggleSidebar: () => void;
}

const NAV_ITEMS: { id: AppView; label: string; icon: React.ReactNode }[] = [
  { id: 'chat', label: 'Chat', icon: <MessageSquare size={20} /> },
  { id: 'knowledge', label: 'Knowledge Base', icon: <BookOpen size={20} /> },
  { id: 'artifacts', label: 'Artifacts', icon: <Sparkles size={20} /> },
  { id: 'history', label: 'History', icon: <History size={20} /> },
];

export const TopNav: React.FC<TopNavProps> = ({
  activeView,
  onChangeView,
  provider,
  model,
  hasSession,
  isSwitchingProvider,
  providerError,
  onChangeProvider,
  onToggleSidebar,
}) => {
  const [isModelMenuOpen, setIsModelMenuOpen] = React.useState(false);
  const selectedProvider = provider === 'anthropic' ? 'anthropic' : 'ollama';
  const displayModel = model || (selectedProvider === 'anthropic' ? 'Claude' : 'Ollama');

  const selectProvider = async (nextProvider: 'ollama' | 'anthropic') => {
    if (await onChangeProvider(nextProvider)) {
      setIsModelMenuOpen(false);
    }
  };

  return (
    <header className="top-nav">
      <div className="top-nav-left">
        <button
          className="icon-btn menu-toggle"
          onClick={onToggleSidebar}
          aria-label="Open menu"
          type="button"
        >
          <Menu size={20} />
        </button>
        <nav className="top-nav-links" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`top-nav-item ${activeView === item.id ? 'active' : ''}`}
              onClick={() => onChangeView(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="top-nav-right">
        <div className="model-selector">
          <button
            className="provider-badge model-selector-trigger"
            type="button"
            disabled={!hasSession || isSwitchingProvider}
            onClick={() => setIsModelMenuOpen((open) => !open)}
            aria-label="Select model"
            aria-haspopup="menu"
            aria-expanded={isModelMenuOpen}
            onKeyDown={(event) => {
              if (event.key === 'Escape') setIsModelMenuOpen(false);
            }}
          >
            {isSwitchingProvider ? <LoaderCircle className="model-spinner" size={15} /> : <Bot size={15} />}
            <span>{isSwitchingProvider ? 'Switching…' : `Model: ${selectedProvider} · ${displayModel}`}</span>
            <ChevronDown size={15} />
          </button>
          {isModelMenuOpen && (
            <div className="model-menu" role="menu" aria-label="Select model">
              <p>Select model</p>
              {(['ollama', 'anthropic'] as const).map((option) => (
                <button
                  key={option}
                  role="menuitemradio"
                  aria-checked={selectedProvider === option}
                  type="button"
                  onClick={() => selectProvider(option)}
                >
                  <span className={`model-radio ${selectedProvider === option ? 'selected' : ''}`}>
                    {selectedProvider === option && <Check size={12} />}
                  </span>
                  <span className="model-menu-copy">
                    <strong>{option === 'ollama' ? 'Ollama' : 'Anthropic'}</strong>
                    <small>{option === 'ollama' ? (selectedProvider === option ? displayModel : 'Local model') : (selectedProvider === option ? displayModel : 'Claude')}</small>
                  </span>
                </button>
              ))}
              {providerError && <span className="model-menu-error" role="alert">{providerError}</span>}
            </div>
          )}
        </div>
        <button className="icon-btn" type="button" aria-label="Settings" title="Settings">
          <Settings size={18} />
        </button>
        <button className="icon-btn" type="button" aria-label="Theme" title="Theme">
          <Sun size={18} />
        </button>
        <button className="user-chip" type="button" aria-label="Account">
          <span className="avatar">A</span>
          <span className="user-chip-name">Ayush</span>
          <ChevronDown size={16} />
        </button>
      </div>
    </header>
  );
};
