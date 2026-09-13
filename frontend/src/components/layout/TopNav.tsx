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
} from 'lucide-react';
import { formatProviderName } from '../../lib/format';

export type AppView = 'chat' | 'knowledge' | 'artifacts' | 'history';

interface TopNavProps {
  activeView: AppView;
  onChangeView: (view: AppView) => void;
  provider: string | null;
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
  onToggleSidebar,
}) => {
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
        {provider && (
          <div className="provider-badge">
            <span className="provider-icon" aria-hidden="true">
              <Bot size={14} />
            </span>
            <span>Model: {provider}</span>
            <span className="status-dot" title={`${formatProviderName(provider)} connected`} />
          </div>
        )}
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
