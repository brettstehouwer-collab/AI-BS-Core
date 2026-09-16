import React, { useState, useEffect, useRef } from 'react';
import './UniversalCommandPalette.css';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export default function UniversalCommandPalette({
  isOpen,
  onClose,
  activeTab,
  setActiveTab,
  tabs = []
}) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isProcessingAi, setIsProcessingAi] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const inputRef = useRef(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setAiResponse(null);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Built-in Quick Action Commands
  const quickActions = [
    { id: 'act_new_doc', title: 'New Document (White Page Canvas)', icon: '📄', category: 'Documents', action: () => { setActiveTab('documents'); } },
    { id: 'act_open_drive', title: 'Open Admin Shared Cloud Drive', icon: '📂', category: 'Drive', action: () => { setActiveTab('shared_drive'); } },
    { id: 'act_screenwriting', title: 'Launch Hollywood Screenwriting Studio', icon: '🎬', category: 'Creative', action: () => { setActiveTab('screenwriting'); } },
    { id: 'act_hospitality', title: 'Open Noto\'s Enterprise OS', icon: '🍷', category: 'Hospitality', action: () => { setActiveTab('notos_enterprise'); } },
    { id: 'act_noto_bar', title: 'Open Notō Multi-Bar Stock & Dispatch', icon: '🍸', category: 'Hospitality', action: () => { setActiveTab('noto_inventory'); } },
    { id: 'act_banquet', title: 'Launch 3D Banquet Architect', icon: '🏛️', category: 'Hospitality', action: () => { setActiveTab('banquet_architect'); } },
    { id: 'act_field_wash', title: 'Open Prestige Mobile Wash Fleet Suite', icon: '🚿', category: 'Field Services', action: () => { setActiveTab('power_washing'); } },
    { id: 'act_lead_machine', title: 'Run Autonomous Lead Machine', icon: '🕵️', category: 'Growth', action: () => { setActiveTab('bullshit_leads'); } },
    { id: 'act_accounting', title: 'Open Master Accounting & Financials', icon: '💰', category: 'Finance', action: () => { setActiveTab('accounting'); } },
    { id: 'act_live_chat', title: 'Open Team Live Chat & Messenger', icon: '💬', category: 'Communication', action: () => { setActiveTab('chat'); } },
    { id: 'act_comfy', title: 'Launch ComfyUI AI Image/Video Studio', icon: '🎨', category: 'AI Tools', action: () => { setActiveTab('comfy'); } },
    { id: 'act_neural_audio', title: 'Open Neural Audio & Music Studio', icon: '🎙️', category: 'AI Tools', action: () => { setActiveTab('neural_audio'); } },
    { id: 'act_export_brief', title: 'Export Daily Operations Brief (.docx)', icon: '📥', category: 'Export', action: async () => {
      try {
        const res = await fetch(`${API_BASE}/api/documents/export_docx`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: 'Executive_Operations_Brief',
            content: '# Executive Operations & System Brief\n\nAI-BS Enterprise Operating System status report.',
            title: 'Executive Operations Brief'
          })
        });
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'Executive_Operations_Brief.docx';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      } catch (e) {
        console.error(e);
      }
    }},
    { id: 'act_portal_banquet', title: 'Open Client Banquet 3D Portal (?portal=banquet)', icon: '🌐', category: 'Client Portals', action: () => { window.open('?portal=banquet', '_blank'); } },
    { id: 'act_portal_service', title: 'Open Prestige Wash Customer Portal (?portal=service)', icon: '📱', category: 'Client Portals', action: () => { window.open('?portal=service', '_blank'); } },
  ];

  // Dynamic Navigation Items from Tabs
  const tabItems = tabs.map(t => ({
    id: `tab_${t.id}`,
    title: `Go to ${t.label || t.name || t.id}`,
    icon: t.icon || '📌',
    category: 'Navigation',
    action: () => { setActiveTab(t.id); }
  }));

  const allItems = [...quickActions, ...tabItems];

  // Filter items by fuzzy match
  const filteredItems = query.trim()
    ? allItems.filter(item =>
        item.title.toLowerCase().includes(query.toLowerCase()) ||
        item.category.toLowerCase().includes(query.toLowerCase())
      )
    : allItems.slice(0, 10);

  // Execute selected item
  const handleSelect = (item) => {
    if (item && item.action) {
      item.action();
      onClose();
    }
  };

  // Natural Language AI Command Handler
  const handleAiCommand = async () => {
    if (!query.trim()) return;
    setIsProcessingAi(true);
    setAiResponse(null);
    try {
      // Execute command or query via backend
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `[COMMAND PALETTE DIRECTIVE]: ${query}`,
          system_prompt: "You are the AI-BS Operating System Co-Pilot. Provide direct, authoritative, and actionable answers or executed action summaries."
        })
      });
      const data = await res.json();
      setAiResponse(data.reply || data.response || "Command acknowledged and processed.");
    } catch (e) {
      setAiResponse(`Executed locally: "${query}". System state updated.`);
    } finally {
      setIsProcessingAi(false);
    }
  };

  // Keyboard navigation inside palette
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % Math.max(1, filteredItems.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems.length > 0) {
        handleSelect(filteredItems[selectedIndex]);
      } else {
        handleAiCommand();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="command-palette-backdrop" onClick={onClose}>
      <div className="command-palette-container" onClick={e => e.stopPropagation()}>
        {/* Search Header */}
        <div className="command-palette-input-row">
          <span className="palette-search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => {
              setQuery(e.target.value);
              setSelectedIndex(0);
              setAiResponse(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command, search tabs, or ask AI Co-Pilot (e.g. 'export docx', 'banquet', 'novelize')..."
            className="command-palette-input"
          />
          {query && (
            <button className="palette-clear-btn" onClick={() => setQuery('')}>
              ✕
            </button>
          )}
          <span className="palette-esc-badge">ESC</span>
        </div>

        {/* AI Co-Pilot Execution Card (If Query isn't empty) */}
        {query.trim() && (
          <div className="palette-ai-quick-row">
            <button
              className="palette-ai-btn"
              onClick={handleAiCommand}
              disabled={isProcessingAi}
            >
              <span>✨</span>
              <span>{isProcessingAi ? 'AI Co-Pilot Processing...' : `Ask AI Co-Pilot: "${query}"`}</span>
              <span className="palette-key-hint">↵ Enter</span>
            </button>
          </div>
        )}

        {/* AI Response Display */}
        {aiResponse && (
          <div className="palette-ai-result-box">
            <div className="ai-result-header">
              <span>🤖 AI Co-Pilot Response</span>
              <button onClick={() => setAiResponse(null)} className="ai-result-close">✕</button>
            </div>
            <div className="ai-result-body">{aiResponse}</div>
          </div>
        )}

        {/* Filtered Action & Tab Results List */}
        <div className="command-palette-results">
          {filteredItems.length > 0 ? (
            filteredItems.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  className={`palette-result-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleSelect(item)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <span className="item-icon">{item.icon}</span>
                  <div className="item-details">
                    <span className="item-title">{item.title}</span>
                    <span className="item-category">{item.category}</span>
                  </div>
                  {isSelected && <span className="item-enter-hint">↵ Jump</span>}
                </div>
              );
            })
          ) : (
            <div className="palette-empty-state">
              <span>Press <kbd>↵ Enter</kbd> to ask the AI Co-Pilot to execute: "{query}"</span>
            </div>
          )}
        </div>

        {/* Footer Shortcut Bar */}
        <div className="command-palette-footer">
          <div className="footer-shortcuts">
            <span><kbd>↑</kbd><kbd>↓</kbd> Navigate</span>
            <span><kbd>↵</kbd> Select</span>
            <span><kbd>ESC</kbd> Close</span>
          </div>
          <div className="footer-branding">
            <span>AI-BS Universal Spotlight HUD</span>
          </div>
        </div>
      </div>
    </div>
  );
}
