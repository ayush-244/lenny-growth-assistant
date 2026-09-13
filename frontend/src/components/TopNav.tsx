import React from 'react';
import {
  MessageSquare,
  Library,
  Sparkles,
  Clock,
  Settings,
  Sun,
  Menu,
  ChevronDown,
} from 'lucide-react';

export type AppView = 'chat' | 'knowledge' | 'artifacts' | 'history';

interface TopNavProps {
  activeView: AppView;
  onChangeView: (view: AppView) => void;
  provider: string | null;
  onToggleSidebar: () => void;
}

const NAV_ITEMS: { id: AppView; label: string; icon: React.ReactNode }[] = [
  { id: 'chat', label: 'Chat', icon: <MessageSquare size={18} /> },
  { id: 'knowledge', label: 'Knowledge Base', icon: <Library size={18} /> },
  { id: 'artifacts', label: 'Artifacts', icon: <Sparkles size={18} /> },
  { id: 'history', label: 'History', icon: <Clock size={18} /> },
];

export function formatProviderLabel(provider: string | null): string {
  if (!provider) return 'Waiting for session';
  const key = provider.toLowerCase();
  if (key === 'ollama') return 'Ollama';
  if (key === 'anthropic') return 'Anthropic';
  return provider;
}

export const TopNav: React.FC<TopNavProps> = ({
  activeView,
  onChangeView,
  provider,
  onToggleSidebar,
}) => {
  return (
    <header className="top-nav">
      <div className="top-nav-left">
        <button
          type="button"
          className="icon-btn menu-btn"
          onClick={onToggleSidebar}
          aria-label="Open conversations"
        >
          <Menu size={20} />
        </button>
        <nav className="top-nav-tabs" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-tab ${activeView === item.id ? 'active' : ''}`}
              onClick={() => onChangeView(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="top-nav-right">
        <div className="provider-badge" title={provider || undefined}>
          <span className="provider-status" aria-hidden="true" />
          <span>Model: {provider || formatProviderLabel(provider)}</span>
        </div>
        <button type="button" className="icon-btn" aria-label="Settings" title="Settings">
          <Settings size={18} />
        </button>
        <button type="button" className="icon-btn" aria-label="Theme" title="Theme">
          <Sun size={18} />
        </button>
        <div className="nav-user" aria-label="Account">
          <span className="avatar-circle">A</span>
          <span className="nav-user-name">Ayush</span>
          <ChevronDown size={16} />
        </div>
      </div>
    </header>
  );
};
