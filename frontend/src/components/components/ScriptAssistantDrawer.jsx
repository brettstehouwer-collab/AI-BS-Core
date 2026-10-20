import React, { useState, useEffect, useRef } from 'react';

export default function ScriptAssistantDrawer({
  projectName = 'Default Project',
  isOpen = false,
  onClose,
  onInsertScript,
  backendUrl = ''
}) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `👋 **Hello! I am your Dedicated Script & Memoir Assistant for *${projectName}*.**\n\nI am directly connected to this project's isolated Vector Database containing **only** your original book manuscript and current screenplay draft.\n\nAsk me anything about real-life events, character voice, scene locations, or request grounded scene revisions!`,
      sources: []
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState({ total_docs: 0, book_chunks: 0, script_scenes: 0 });
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');
  const messagesEndRef = useRef(null);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/project-assistant/stats?project_name=${encodeURIComponent(projectName)}`);
      const data = await res.json();
      if (data.status === 'success') {
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch project stats:', err);
    }
  };

  useEffect(() => {
    if (isOpen && projectName) {
      fetchStats();
    }
  }, [isOpen, projectName]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncMessage('Syncing screenplay & memoir into isolated Vector DB...');
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/project-assistant/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: projectName })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setSyncMessage(`✅ Synced ${data.indexed_scenes} scenes! (${data.total_docs} total vectors)`);
        await fetchStats();
      } else {
        setSyncMessage(`❌ Sync error: ${data.message}`);
      }
    } catch (err) {
      setSyncMessage(`❌ Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
      setTimeout(() => setSyncMessage(''), 4000);
    }
  };

  const handleSendMessage = async (textToSend = null) => {
    const query = (textToSend || inputValue).trim();
    if (!query || isLoading) return;

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInputValue('');
    setIsLoading(true);

    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/project-assistant/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: projectName,
          message: query,
          model: 'stehouwer_dolphin:latest'
        })
      });
      const data = await res.json();
      if (data.status === 'success' || data.response) {
        const assistantMsg = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.response || 'No response generated.',
          sources: data.sources || []
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        setMessages(prev => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `⚠️ Error: ${data.message || 'Could not query project database.'}`,
            sources: []
          }
        ]);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `⚠️ Connection error: ${err.message}`,
          sources: []
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '420px',
      maxWidth: '90vw',
      height: '100vh',
      background: '#0d1117',
      borderLeft: '1px solid #30363d',
      boxShadow: '-8px 0 30px rgba(0,0,0,0.7)',
      zIndex: 2500,
      display: 'flex',
      flexDirection: 'column',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px',
        background: '#161b22',
        borderBottom: '1px solid #30363d',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.3rem' }}>🤖</span>
            <div>
              <h3 style={{ margin: 0, color: '#f0f6fc', fontSize: '0.95rem', fontWeight: 'bold' }}>
                Script & Memoir Assistant
              </h3>
              <div style={{ color: '#8b949e', fontSize: '0.75rem' }}>
                Project: <strong style={{ color: '#58a6ff' }}>{projectName}</strong>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', fontSize: '1.2rem', cursor: 'pointer', padding: '4px' }}
          >
            ✕
          </button>
        </div>

        {/* Isolated DB Status Pill & Sync Button */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#090d16',
          padding: '6px 10px',
          borderRadius: '6px',
          border: '1px solid #1e293b',
          fontSize: '0.75rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8' }}>
            <span style={{ color: '#22c55e' }}>●</span>
            <span>ChromaDB: <strong>{stats.total_docs || 0} vectors</strong> ({stats.book_chunks || 0} book, {stats.script_scenes || 0} scenes)</span>
          </div>
          <button
            onClick={handleSync}
            disabled={isSyncing}
            style={{
              background: '#238636',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '2px 8px',
              fontSize: '0.7rem',
              fontWeight: 'bold',
              cursor: isSyncing ? 'wait' : 'pointer'
            }}
            title="Re-index current script and book into this project's isolated Vector DB"
          >
            {isSyncing ? '⏳ Syncing...' : '🔄 Sync DB'}
          </button>
        </div>
        {syncMessage && (
          <div style={{ color: syncMessage.includes('❌') ? '#f87171' : '#4ade80', fontSize: '0.75rem' }}>
            {syncMessage}
          </div>
        )}
      </div>

      {/* Quick Prompt Chips */}
      <div style={{
        padding: '8px 12px',
        background: '#090d16',
        borderBottom: '1px solid #21262d',
        display: 'flex',
        gap: '6px',
        overflowX: 'auto',
        whiteSpace: 'nowrap'
      }}>
        {[
          '📖 Where in memoir is this?',
          '🎭 Character voice check',
          '🔍 Find courtroom scenes',
          '✍️ Suggest Act 2 turn'
        ].map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(chip)}
            disabled={isLoading}
            style={{
              background: '#161b22',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              borderRadius: '12px',
              padding: '3px 8px',
              fontSize: '0.72rem',
              cursor: 'pointer',
              flexShrink: 0
            }}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Message Stream */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        background: '#0d1117'
      }}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '92%'
            }}
          >
            <div style={{
              background: m.role === 'user' ? '#1f6feb' : '#161b22',
              color: '#f0f6fc',
              padding: '10px 14px',
              borderRadius: m.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
              border: m.role === 'user' ? 'none' : '1px solid #30363d',
              fontSize: '0.85rem',
              lineHeight: '1.45',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {m.content}
            </div>

            {/* Action buttons on Assistant Messages */}
            {m.role === 'assistant' && m.id !== 'welcome' && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '6px', alignItems: 'center' }}>
                <button
                  onClick={() => navigator.clipboard.writeText(m.content)}
                  style={{ background: 'transparent', border: '1px solid #30363d', color: '#8b949e', borderRadius: '4px', padding: '2px 6px', fontSize: '0.7rem', cursor: 'pointer' }}
                >
                  📋 Copy
                </button>
                {typeof onInsertScript === 'function' && (
                  <button
                    onClick={() => onInsertScript(m.content)}
                    style={{ background: 'transparent', border: '1px solid #238636', color: '#3fb950', borderRadius: '4px', padding: '2px 6px', fontSize: '0.7rem', cursor: 'pointer' }}
                  >
                    📝 Insert in Script
                  </button>
                )}
              </div>
            )}

            {/* Source Citations Accordion */}
            {m.sources && m.sources.length > 0 && (
              <details style={{ marginTop: '6px', background: '#090d16', border: '1px solid #21262d', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}>
                <summary style={{ color: '#58a6ff', cursor: 'pointer', fontWeight: 'bold' }}>
                  📚 Sources Used ({m.sources.length})
                </summary>
                <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {m.sources.map((src, sIdx) => (
                    <div key={sIdx} style={{ background: '#161b22', padding: '6px', borderRadius: '4px', borderLeft: src.type === 'script_scene' ? '3px solid #3b82f6' : '3px solid #eab308' }}>
                      <div style={{ color: src.type === 'script_scene' ? '#93c5fd' : '#fde047', fontWeight: 'bold', fontSize: '0.7rem' }}>
                        {src.label}
                      </div>
                      <div style={{ color: '#8b949e', fontSize: '0.7rem', marginTop: '2px', fontStyle: 'italic' }}>
                        "{src.excerpt}"
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
        {isLoading && (
          <div style={{ alignSelf: 'flex-start', background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '10px 14px', color: '#58a6ff', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>⏳ Searching {projectName} Vector DB & reasoning...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div style={{
        padding: '12px 14px',
        background: '#161b22',
        borderTop: '1px solid #30363d',
        display: 'flex',
        gap: '8px'
      }}>
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          placeholder="Ask about the memoir, compare book vs script..."
          rows={2}
          style={{
            flex: 1,
            background: '#0d1117',
            color: '#f0f6fc',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '8px 10px',
            fontSize: '0.85rem',
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit'
          }}
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={!inputValue.trim() || isLoading}
          style={{
            background: (!inputValue.trim() || isLoading) ? '#21262d' : '#238636',
            color: (!inputValue.trim() || isLoading) ? '#484f58' : '#fff',
            border: 'none',
            borderRadius: '6px',
            padding: '0 14px',
            fontWeight: 'bold',
            fontSize: '1rem',
            cursor: (!inputValue.trim() || isLoading) ? 'not-allowed' : 'pointer'
          }}
        >
          ➤
        </button>
      </div>
    </div>
  );
}
