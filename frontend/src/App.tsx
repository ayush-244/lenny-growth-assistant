import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { ArtifactPanel } from './components/ArtifactPanel';
import { AppShell } from './components/layout/AppShell';
import { TopNav, type AppView } from './components/layout/TopNav';
import { SourcesPanel } from './components/sources/SourcesPanel';
import { KnowledgeView, HistoryView, ArtifactsView } from './components/layout/SecondaryViews';
import type { Session, Message, SessionWithMessages, Artifact, ArtifactType, Citation } from './types';
import { api } from './api';

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedPrompt, setLastFailedPrompt] = useState<string | null>(null);

  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [isArtifactLoading, setIsArtifactLoading] = useState(false);
  const [artifactError, setArtifactError] = useState<string | null>(null);
  const [sessionArtifacts, setSessionArtifacts] = useState<Artifact[]>([]);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [artifactsListError, setArtifactsListError] = useState<string | null>(null);

  const [activeProvider, setActiveProvider] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<AppView>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const composerRef = useRef<HTMLTextAreaElement>(null);

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
    setActiveArtifact(null);
    setArtifactError(null);
    setSidebarOpen(false);
    setActiveView('chat');
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
    setActiveView('chat');
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

  const ensureSession = async (): Promise<string | null> => {
    if (activeSessionId) return activeSessionId;
    try {
      const newSession = await api.createSession();
      setActiveSessionId(newSession.id);
      setActiveProvider(newSession.model_provider);
      updateSessionsList(newSession);
      localStorage.setItem('activeSessionId', newSession.id);
      return newSession.id;
    } catch (err) {
      return null;
    }
  };

  const handleSendMessage = async (content: string) => {
    const currentSessionId = await ensureSession();
    if (!currentSessionId) {
      setError('Unable to create a session to send your message.');
      return;
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
    setLastFailedPrompt(content);
    setActiveView('chat');

    try {
      const responseMsg = await api.sendMessage(currentSessionId, content);
      setMessages(prev => [...prev, responseMsg]);
      setLastFailedPrompt(null);

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
    const currentSessionId = await ensureSession();
    if (!currentSessionId) {
      setError('Unable to create a session to generate an essay.');
      return;
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
    setLastFailedPrompt(content);
    setActiveView('chat');

    try {
      const responseMsg = await api.generateEssay(currentSessionId, content);
      setMessages(prev => [...prev, responseMsg as Message]);
      setLastFailedPrompt(null);

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
    const currentSessionId = await ensureSession();
    if (!currentSessionId) {
      setArtifactError('Unable to create a session to generate an artifact.');
      return;
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
    setActiveView('chat');

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

  const loadArtifacts = async (sessionId: string) => {
    setArtifactsLoading(true);
    setArtifactsListError(null);
    try {
      const items = await api.listArtifacts(sessionId);
      setSessionArtifacts(items);
    } catch (err) {
      setArtifactsListError(err instanceof Error ? err.message : 'Failed to load artifacts');
    } finally {
      setArtifactsLoading(false);
    }
  };

  const handleChangeView = (view: AppView) => {
    setActiveView(view);
    if (view === 'artifacts' && activeSessionId) {
      loadArtifacts(activeSessionId);
    }
  };

  const latestCitations: Citation[] = [...messages]
    .reverse()
    .find((m) => m.role === 'assistant' && m.citations && m.citations.length > 0)
    ?.citations ?? [];

  const artifactOpen = Boolean(activeArtifact || isArtifactLoading || artifactError);
  const sourcesVisible = activeView === 'chat' && !artifactOpen;

  const focusComposer = () => {
    setActiveView('chat');
    window.setTimeout(() => composerRef.current?.focus(), 0);
  };

  let mainContent: React.ReactNode = (
    <ChatArea
      messages={messages}
      isLoading={isLoading}
      error={error}
      onSendMessage={handleSendMessage}
      onGenerateEssay={handleGenerateEssay}
      onGenerateArtifact={handleGenerateArtifact}
      onRetry={lastFailedPrompt ? () => handleSendMessage(lastFailedPrompt) : undefined}
      inputRef={composerRef}
    />
  );

  if (activeView === 'knowledge') {
    mainContent = <KnowledgeView />;
  } else if (activeView === 'history') {
    mainContent = <HistoryView sessions={sessions} onSelectSession={loadSession} />;
  } else if (activeView === 'artifacts') {
    mainContent = (
      <ArtifactsView
        artifacts={sessionArtifacts}
        isLoading={artifactsLoading}
        error={artifactsListError}
        hasSession={Boolean(activeSessionId)}
        onOpen={(artifact) => {
          setActiveArtifact(artifact);
          setActiveView('chat');
        }}
      />
    );
  }

  return (
    <AppShell
      sidebarOpen={sidebarOpen}
      onCloseSidebar={() => setSidebarOpen(false)}
      sidebar={
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={loadSession}
          onNewSession={handleNewSession}
        />
      }
      topNav={
        <TopNav
          activeView={activeView}
          onChangeView={handleChangeView}
          provider={activeProvider}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
        />
      }
      sourcesVisible={sourcesVisible}
      sources={<SourcesPanel citations={latestCitations} onFocusComposer={focusComposer} />}
      artifact={
        artifactOpen ? (
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
        ) : null
      }
    >
      {mainContent}
    </AppShell>
  );
}
