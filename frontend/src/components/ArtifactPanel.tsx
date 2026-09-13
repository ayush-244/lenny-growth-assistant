import React from 'react';
import type { Artifact } from '../types';
import { ArtifactViewer } from './ArtifactViewer';
import { X } from 'lucide-react';

interface ArtifactPanelProps {
  artifact: Artifact | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}

export const ArtifactPanel: React.FC<ArtifactPanelProps> = ({
  artifact,
  isLoading,
  error,
  onClose,
}) => {
  if (!artifact && !isLoading && !error) return null;

  return (
    <div className="artifact-panel">
      <div className="artifact-header">
        <div className="artifact-title">
          <h3>{artifact?.title || 'Generating Artifact...'}</h3>
          {artifact && (
            <span className="artifact-type-badge">
              {artifact.artifact_type.toUpperCase()}
            </span>
          )}
        </div>
        <button className="close-btn" onClick={onClose} aria-label="Close artifact">
          <X size={18} />
        </button>
      </div>

      <div className="artifact-body">
        {isLoading && (
          <div className="artifact-loading">
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
            <p>Generating your artifact. This may take a moment...</p>
          </div>
        )}

        {error && (
          <div className="artifact-error">
            <strong>Something went wrong</strong>
            <p>I couldn’t complete that request right now.</p>
          </div>
        )}

        {artifact && !isLoading && !error && (
          <ArtifactViewer artifact={artifact} />
        )}
      </div>
    </div>
  );
};
