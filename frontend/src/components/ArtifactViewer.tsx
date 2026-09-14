import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Artifact } from '../types';

interface ArtifactViewerProps {
  artifact: Artifact;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact }) => {
  if (artifact.artifact_type === 'html') {
    return (
      <div className="artifact-viewer html-viewer">
        <iframe
          srcDoc={artifact.content}
          sandbox=""
          title={`Artifact: ${artifact.title || 'HTML'}`}
          className="artifact-iframe"
          data-testid="artifact-iframe"
        />
      </div>
    );
  }

  return (
    <div className="artifact-viewer markdown-viewer">
      <div className="markdown-content">
        <ReactMarkdown>{artifact.content}</ReactMarkdown>
      </div>
    </div>
  );
};