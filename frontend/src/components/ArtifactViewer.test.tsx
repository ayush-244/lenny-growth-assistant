import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ArtifactViewer } from './ArtifactViewer';
import type { Artifact } from '../types';

// Mock react-markdown since we just want to test rendering path
vi.mock('react-markdown', () => {
  return {
    default: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="markdown-mock">{children}</div>
    ),
  };
});

describe('ArtifactViewer', () => {
  it('renders Markdown artifacts safely', () => {
    const artifact: Artifact = {
      id: '1',
      session_id: 's1',
      artifact_type: 'markdown',
      content: '# Hello World',
      request: 'req',
      grounded: true,
      created_at: new Date().toISOString(),
    };

    render(<ArtifactViewer artifact={artifact} />);
    
    const mock = screen.getByTestId('markdown-mock');
    expect(mock).toBeInTheDocument();
    expect(mock).toHaveTextContent('# Hello World');
    
    // Ensure no iframe is rendered
    expect(screen.queryByTestId('artifact-iframe')).not.toBeInTheDocument();
  });

  it('renders HTML artifacts in a strict sandboxed iframe', () => {
    const artifact: Artifact = {
      id: '2',
      session_id: 's1',
      artifact_type: 'html',
      content: '<h1>Hello</h1>',
      request: 'req',
      grounded: true,
      created_at: new Date().toISOString(),
      title: 'HTML Test',
    };

    render(<ArtifactViewer artifact={artifact} />);
    
    const iframe = screen.getByTestId('artifact-iframe') as HTMLIFrameElement;
    expect(iframe).toBeInTheDocument();
    
    // Security guarantees
    expect(iframe.getAttribute('sandbox')).toBe(''); // Strictest possible sandbox
    expect(iframe.getAttribute('srcDoc')).toBe('<h1>Hello</h1>');
    
    // Title is set for accessibility
    expect(iframe.getAttribute('title')).toBe('Artifact: HTML Test');
    
    // Markdown shouldn't be rendered
    expect(screen.queryByTestId('markdown-mock')).not.toBeInTheDocument();
  });
});
