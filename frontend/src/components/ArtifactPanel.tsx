import React from 'react';
import type { Artifact } from '../types';
import { ArtifactViewer } from './ArtifactViewer';

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
          ?
        </button>
      </div>

      <div className="artifact-body">
        {isLoading && (
          <div className="artifact-loading">
            <div className="spinner"></div>
            <p>Generating your artifact. This may take a moment...</p>
          </div>
        )}

        {error && (
          <div className="artifact-error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {artifact && !isLoading && !error && (
          <ArtifactViewer artifact={artifact} />
        )}
      </div>
    </div>
  );
};
