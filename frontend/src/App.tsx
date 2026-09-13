import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { ArtifactPanel } from './components/ArtifactPanel';
import type { Session, Message, SessionWithMessages, Artifact, ArtifactType } from './types';
import { api } from './api';

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Artifact State
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [isArtifactLoading, setIsArtifactLoading] = useState(false);
  const [artifactError, setArtifactError] = useState<string | null>(null);

  // Track active provider for the UI based on session or latest message
  const [activeProvider, setActiveProvider] = useState<string | null>(null);

  // Initialize: load active session from local storage or wait for user to create one
  useEffect(() => {
    const savedSessionId = localStorage.getItem('activeSessionId');
    if (savedSessionId) {
      loadSession(savedSessionId);
    }
  }, []);

  const updateSessionsList = (session: Session) => {
    setSessions(prev => {
      const exists = prev.find(s => s.id === session.id);
      if (exists) return prev;
      return [session, ...prev];
    });
  };

  const loadSession = async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    setActiveArtifact(null); // Reset artifact on session change
    setArtifactError(null);
    try {
      const sessionData: SessionWithMessages = await api.getSession(sessionId);
      setMessages(sessionData.messages || []);
      setActiveSessionId(sessionId);
      setActiveProvider(sessionData.model_provider || null);
      updateSessionsList(sessionData);
      localStorage.setItem('activeSessionId', sessionId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to load session: ${msg}`);
      if (msg.includes('404')) {
        localStorage.removeItem('activeSessionId');
        setActiveSessionId(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewSession = async () => {
    setIsLoading(true);
    setError(null);
    setActiveArtifact(null);
    setArtifactError(null);
    try {
      const newSession = await api.createSession();
      setMessages([]);
      setActiveSessionId(newSession.id);
      setActiveProvider(newSession.model_provider);
      updateSessionsList(newSession);
      localStorage.setItem('activeSessionId', newSession.id);
    } catch (err) {
      setError('Unable to connect to the Growth Assistant. Please check that the backend is running and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    // If no active session, create one first implicitly
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      try {
        const newSession = await api.createSession();
        currentSessionId = newSession.id;
        setActiveSessionId(newSession.id);
        setActiveProvider(newSession.model_provider);
        updateSessionsList(newSession);
        localStorage.setItem('activeSessionId', newSession.id);
      } catch (err) {
        setError('Unable to create a session to send your message.');
        return;
      }
    }

    // Optimistically add user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: currentSessionId,
      role: 'user',
      content,
      grounded: false,
      created_at: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, tempUserMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const responseMsg = await api.sendMessage(currentSessionId, content);
      setMessages(prev => [...prev, responseMsg]);
      
      // Update provider if it changed
      if (responseMsg.provider) {
        setActiveProvider(responseMsg.provider);
      }
      
      if (messages.length === 0) {
        setSessions(prev => 
          prev.map(s => s.id === currentSessionId ? { ...s, metadata_: { title: content.slice(0, 30) + '...' } } : s)
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateEssay = async (content: string) => {
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      try {
        const newSession = await api.createSession();
        currentSessionId = newSession.id;
        setActiveSessionId(newSession.id);
        setActiveProvider(newSession.model_provider);
        updateSessionsList(newSession);
        localStorage.setItem('activeSessionId', newSession.id);
      } catch (err) {
        setError('Unable to create a session to generate an essay.');
        return;
      }
    }

    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: currentSessionId,
      role: 'user',
      content,
      grounded: false,
      created_at: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, tempUserMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const responseMsg = await api.generateEssay(currentSessionId, content);
      setMessages(prev => [...prev, responseMsg as Message]);
      
      if (responseMsg.provider) {
        setActiveProvider(responseMsg.provider);
      }
      
      if (messages.length === 0) {
        setSessions(prev => 
          prev.map(s => s.id === currentSessionId ? { ...s, metadata_: { title: content.slice(0, 30) + '...' } } : s)
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate essay');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateArtifact = async (content: string, type: ArtifactType) => {
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      try {
        const newSession = await api.createSession();
        currentSessionId = newSession.id;
        setActiveSessionId(newSession.id);
        setActiveProvider(newSession.model_provider);
        updateSessionsList(newSession);
        localStorage.setItem('activeSessionId', newSession.id);
      } catch (err) {
        setArtifactError('Unable to create a session to generate an artifact.');
        return;
      }
    }

    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: currentSessionId,
      role: 'user',
      content: `Create ${type} artifact: ${content}`,
      grounded: false,
      created_at: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, tempUserMsg]);
    setIsArtifactLoading(true);
    setArtifactError(null);
    setActiveArtifact(null);

    try {
      const artifact = await api.generateArtifact(currentSessionId, content, type);
      setActiveArtifact(artifact);
      
      if (artifact.provider) {
        setActiveProvider(artifact.provider);
      }
      
      if (messages.length === 0) {
        setSessions(prev => 
          prev.map(s => s.id === currentSessionId ? { ...s, metadata_: { title: content.slice(0, 30) + '...' } } : s)
        );
      }
    } catch (err) {
      setArtifactError(err instanceof Error ? err.message : 'Failed to generate artifact');
    } finally {
      setIsArtifactLoading(false);
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={loadSession}
        onNewSession={handleNewSession}
      />
      <div className={`main-content ${activeArtifact || isArtifactLoading || artifactError ? 'with-artifact' : ''}`}>
        <ChatArea
          messages={messages}
          isLoading={isLoading}
          error={error}
          provider={activeProvider}
          onSendMessage={handleSendMessage}
          onGenerateEssay={handleGenerateEssay}
          onGenerateArtifact={handleGenerateArtifact}
        />
        {(activeArtifact || isArtifactLoading || artifactError) && (
          <ArtifactPanel
            artifact={activeArtifact}
            isLoading={isArtifactLoading}
            error={artifactError}
            onClose={() => {
              setActiveArtifact(null);
              setIsArtifactLoading(false);
              setArtifactError(null);
            }}
          />
        )}
      </div>
    </div>
  );
}
