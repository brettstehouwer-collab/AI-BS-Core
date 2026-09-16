import React, { useState } from 'react';

interface Props {
  onToolToggle?: (tools: Record<string, boolean>) => void;
}

export default function ChatToolControlBar({ onToolToggle }: Props) {
  const [tools, setTools] = useState<Record<string, boolean>>({
    search_local_files: true,
    polyglot_runner: true,
    vector_vault: true,
    ast_shredder: true,
    auto_healer: true
  });

  const toggleTool = (name: string) => {
    const next = { ...tools, [name]: !tools[name] };
    setTools(next);
    if (onToolToggle) onToolToggle(next);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      backgroundColor: '#161b22',
      border: '1px solid #30363d',
      borderRadius: '6px',
      padding: '6px 12px',
      margin: '8px 0',
      fontSize: '11px',
      color: '#8b949e'
    }}>
      <span style={{ fontWeight: 600, color: '#58a6ff' }}>🛠️ Active Agent Tools:</span>
      {Object.entries(tools).map(([key, enabled]) => (
        <button
          key={key}
          type="button"
          onClick={() => toggleTool(key)}
          style={{
            backgroundColor: enabled ? 'rgba(56, 189, 248, 0.15)' : '#0d1117',
            color: enabled ? '#38bdf8' : '#484f58',
            border: `1px solid ${enabled ? '#38bdf8' : '#30363d'}`,
            borderRadius: '12px',
            padding: '2px 8px',
            fontSize: '10px',
            cursor: 'pointer',
            fontWeight: enabled ? 600 : 400
          }}
        >
          {enabled ? '●' : '○'} {key.replace('_', ' ')}
        </button>
      ))}
    </div>
  );
}
