import React, { useState, useEffect, useRef } from 'react';
import { getAllToolsFlatList, masterHubs } from './navigationConfig';
import './GlobalCommandPalette.css';

export default function GlobalCommandPalette({ 
  isOpen, 
  onClose, 
  onNavigateTab, 
  onOpenGuide, 
  onStartTour,
  workspaceMode,
  onToggleWorkspaceMode 
}) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const allTools = getAllToolsFlatList();

  const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
  const [isProcessingAi, setIsProcessingAi] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);

  // Quick Action commands
  const quickActions = [
    {
      id: 'action-new-doc',
      type: 'action',
      label: '📄 New Document (Word & Google Docs White Paper Canvas)',
      icon: '📄',
      category: 'Documents',
      action: () => {
        onClose();
        if (onNavigateTab) onNavigateTab('documents');
      }
    },
    {
      id: 'action-banquet-beo',
      type: 'action',
      label: '🏛️ 3D Banquet Architect & Word BEO Contract Generator',
      icon: '🏛️',
      category: 'Hospitality',
      action: () => {
        onClose();
        if (onNavigateTab) onNavigateTab('banquet_architect');
      }
    },
    {
      id: 'action-table-read',
      type: 'action',
      label: '🎙️ Multi-Voice Screenplay AI Audio Table Read Studio',
      icon: '🎙️',
      category: 'Creative Studio',
      action: () => {
        onClose();
        if (onNavigateTab) onNavigateTab('screenwriting');
      }
    },
    {
      id: 'action-novelize',
      type: 'action',
      label: '📖 Screenplay-to-Book AI Novelizer Studio (KDP Export)',
      icon: '📖',
      category: 'Creative Studio',
      action: () => {
        onClose();
        if (onNavigateTab) onNavigateTab('screenwriting');
      }
    },
    {
      id: 'action-portal-banquet',
      type: 'action',
      label: '🌐 Open Client 3D Banquet Planner Portal (?portal=banquet)',
      icon: '🌐',
      category: 'Client Portals',
      action: () => {
        onClose();
        window.open('?portal=banquet', '_blank');
      }
    },
    {
      id: 'action-portal-wash',
      type: 'action',
      label: '🚿 Open Prestige Mobile Wash Customer Checkout Portal (?portal=service)',
      icon: '🚿',
      category: 'Client Portals',
      action: () => {
        onClose();
        window.open('?portal=service', '_blank');
      }
    },
    {
      id: 'action-tour',
      type: 'action',
      label: '🎯 Start Interactive Feature Spotlight Tour',
      icon: '🎯',
      category: 'System Action',
      action: () => {
        onClose();
        if (onStartTour) onStartTour();
      }
    },
    {
      id: 'action-guide',
      type: 'action',
      label: '💡 Open AI-BS Knowledge & Walkthrough Guide (Hotkeys: ? or F1)',
      icon: '💡',
      category: 'System Action',
      action: () => {
        onClose();
        if (onOpenGuide) onOpenGuide();
      }
    },
    {
      id: 'action-toggle-mode',
      type: 'action',
      label: workspaceMode === 'simple' ? '⚡ Switch to Pro Cockpit Mode (Unlock All Controls)' : '✨ Switch to Simple Mode (Clean & Minimal)',
      icon: workspaceMode === 'simple' ? '⚡' : '✨',
      category: 'System Action',
      action: () => {
        if (onToggleWorkspaceMode) onToggleWorkspaceMode();
        onClose();
      }
    },
    {
      id: 'action-toggle-mom-mode',
      type: 'action',
      label: '🚨 🌸 Toggle MOM Version (Big Text & High Contrast Readability)',
      icon: '🌸',
      category: 'Accessibility Action',
      action: () => {
        const toggle = window.__aibs_toggle_mom_mode;
        if (toggle) toggle();
        onClose();
      }
    }
  ];

  // Filter tools and actions
  const filteredTools = allTools.filter(tool => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return (
      tool.label.toLowerCase().includes(q) ||
      (tool.description && tool.description.toLowerCase().includes(q)) ||
      tool.hubLabel.toLowerCase().includes(q) ||
      tool.key.toLowerCase().includes(q)
    );
  });

  const filteredActions = quickActions.filter(action => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return action.label.toLowerCase().includes(q) || action.category.toLowerCase().includes(q);
  });

  const combinedItems = [...filteredActions, ...filteredTools];

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keyboard navigation inside the palette
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % Math.max(1, combinedItems.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + combinedItems.length) % Math.max(1, combinedItems.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const selectedItem = combinedItems[selectedIndex];
      if (selectedItem) {
        handleSelectItem(selectedItem);
      }
    }
  };

  const handleSelectItem = (item) => {
    if (item.type === 'action') {
      item.action();
    } else {
      if (onNavigateTab) onNavigateTab(item.key);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="cmd-palette-backdrop" onClick={onClose}>
      <div 
        className="cmd-palette-card glass-panel" 
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="cmd-palette-header">
          <span className="cmd-search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="cmd-search-input"
            placeholder="Type a tool name, hub, or action (e.g. 'power wash', 'screenplay', 'drive', 'accounting')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <span className="cmd-shortcut-badge">ESC to close</span>
        </div>

        {/* Results List */}
        <div className="cmd-palette-body" ref={listRef}>
          {combinedItems.length === 0 ? (
            <div className="cmd-empty-state">
              <span className="cmd-empty-icon">📂</span>
              <p>No matching tools found for "{query}".</p>
              <span className="cmd-empty-hint">Try searching for "cloud", "wash", "film", "tax", "ai", or "hotel".</span>
            </div>
          ) : (
            <div className="cmd-results-group">
              {filteredActions.length > 0 && (
                <div className="cmd-section-label">⚡ SYSTEM COMMANDS</div>
              )}
              {filteredActions.map((action, idx) => {
                const isSelected = selectedIndex === idx;
                return (
                  <div
                    key={action.id}
                    className={`cmd-item action-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectItem(action)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <span className="cmd-item-icon">{action.icon}</span>
                    <div className="cmd-item-info">
                      <span className="cmd-item-title">{action.label}</span>
                      <span className="cmd-item-sub">{action.category}</span>
                    </div>
                    <span className="cmd-item-badge">ACTION</span>
                  </div>
                );
              })}

              {filteredTools.length > 0 && (
                <div className="cmd-section-label">🚀 TOOLS & WORKSPACES ({filteredTools.length})</div>
              )}
              {filteredTools.map((tool, idx) => {
                const globalIdx = filteredActions.length + idx;
                const isSelected = selectedIndex === globalIdx;
                return (
                  <div
                    key={tool.key}
                    className={`cmd-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectItem(tool)}
                    onMouseEnter={() => setSelectedIndex(globalIdx)}
                  >
                    <span className="cmd-item-icon">{tool.icon || '📦'}</span>
                    <div className="cmd-item-info">
                      <span className="cmd-item-title">{tool.label}</span>
                      <span className="cmd-item-sub">{tool.description || `Tool in ${tool.hubLabel}`}</span>
                    </div>
                    <span className="cmd-item-hub-tag">{tool.hubLabel}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer info bar */}
        <div className="cmd-palette-footer">
          <div className="cmd-footer-nav">
            <span><kbd>↑</kbd> <kbd>↓</kbd> Navigate</span>
            <span><kbd>↵</kbd> Open Workspace</span>
            <span><kbd>ESC</kbd> Exit</span>
          </div>
          <div className="cmd-footer-mode">
            <span>Mode: <strong>{workspaceMode === 'simple' ? '✨ Simple' : '⚡ Pro Cockpit'}</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
}
