import React from 'react';
import { PanelGroup, Panel, ResizeHandle } from 'react-resizable-panels';

/**
 * PaneLayout provides a macro split between the Chat (sidebar) and Workspace (main).
 * It adjusts the split proportion based on the active tab:
 *   - 'visual' : shrink chat to 15%
 *   - 'terminal' : 50/50 split
 *   - other tabs : default 30% chat, 70% workspace
 */
export default function PaneLayout({ activeTab, children }) {
  const { sidebar, main } = children;
  const getSizes = () => {
    if (activeTab === 'visual') return [15, 85];
    if (activeTab === 'terminal') return [50, 50];
    return [30, 70];
  };
  const [chatSize, mainSize] = getSizes();
  return (
    <PanelGroup direction="horizontal" className="pane-layout">
      <Panel defaultSize={chatSize} minSize={10} maxSize={90} className="chat-pane">
        {sidebar}
      </Panel>
      <ResizeHandle className="resize-handle" />
      <Panel defaultSize={mainSize} minSize={10} maxSize={90} className="workspace-pane">
        {main}
      </Panel>
    </PanelGroup>
  );
}
