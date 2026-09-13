import React from 'react';

interface AppShellProps {
  sidebar: React.ReactNode;
  sidebarOpen: boolean;
  onCloseSidebar: () => void;
  topNav: React.ReactNode;
  children: React.ReactNode;
  sources?: React.ReactNode;
  sourcesVisible: boolean;
  artifact?: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  sidebar,
  sidebarOpen,
  onCloseSidebar,
  topNav,
  children,
  sources,
  sourcesVisible,
  artifact,
}) => {
  return (
    <div className={`app-container ${sidebarOpen ? 'sidebar-open' : ''} ${artifact ? 'with-artifact' : ''} ${sourcesVisible ? 'with-sources' : ''}`}>
      {sidebar}
      {sidebarOpen && (
        <button className="sidebar-backdrop" aria-label="Close sidebar" type="button" onClick={onCloseSidebar} />
      )}
      <div className="workspace">
        {topNav}
        <div className="workspace-body">
          {children}
          {sourcesVisible && sources}
          {artifact}
        </div>
      </div>
    </div>
  );
};
