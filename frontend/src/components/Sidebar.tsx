import React from 'react';
import { Plus, MessageSquare, ChevronDown } from 'lucide-react';
import type { Session } from '../types';
import { LennyLogo } from './branding/LennyLogo';

import { formatRelativeTime } from '../lib/format';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand">
          <LennyLogo size={40} />
          <div className="brand-copy">
            <p className="brand-name">Lenny</p>
            <p className="brand-product">Growth Assistant</p>
          </div>
        </div>
        <p className="brand-tagline">Learn. Build. Grow.</p>
      </div>

      <button className="new-chat-btn" onClick={onNewSession} type="button">
        <Plus size={18} /> New conversation
      </button>

      <ul className="session-list">
        {sessions.map((session, index) => {
          const title = session.metadata_?.title || `Conversation ${sessions.length - index}`;
          return (
            <li
              key={session.id}
              className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
              onClick={() => onSelectSession(session.id)}
            >
              <MessageSquare size={16} />
              <div className="session-copy">
                <span className="session-title">{title}</span>
                <span className="session-time">{formatRelativeTime(session.updated_at || session.created_at)}</span>
              </div>
            </li>
          );
        })}
      </ul>



      <div className="sidebar-user">
        <span className="avatar">A</span>
        <div className="sidebar-user-copy">
          <span className="user-chip-name">Ayush</span>
          <span className="user-email">ayush@example.com</span>
        </div>
        <ChevronDown size={16} />
      </div>
    </aside>
  );
};
