import React from 'react';
import { Plus, MessageSquare } from 'lucide-react';
import type { Session } from '../types';

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
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="brand">
          <MessageSquare size={20} />
          Lenny Growth Assistant
        </div>
      </div>
      
      <button className="new-chat-btn" onClick={onNewSession}>
        <Plus size={16} /> New conversation
      </button>

      <ul className="session-list">
        {sessions.map((session, index) => {
          // Derive a simple title if none exists
          const title = session.metadata_?.title || `Conversation ${sessions.length - index}`;
          return (
            <li
              key={session.id}
              className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
              onClick={() => onSelectSession(session.id)}
            >
              <MessageSquare size={14} />
              {title}
            </li>
          );
        })}
      </ul>
    </div>
  );
};
