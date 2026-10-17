import React, { useState } from 'react';

export default function ChatToolControlBar({ onToolToggle, onQuickCommand }) {
  const [tools, setTools] = useState({
    plan_and_review: false,
    shadow_coder: true,
    media_studio: true,
    unreal_3d_engine: true,
    search_local_files: true,
    polyglot_runner: true,
    vector_vault: true,
    ast_blast_graph: true,
    qlora_distiller: true,
    auto_healer: true
  });

  const TOOL_LABELS = {
    plan_and_review: '📋 Mode: Plan & Review',
    shadow_coder: '⚡ Shadow Coder',
    media_studio: '🎬 Media Studio (v5.323.0)',
    unreal_3d_engine: '🎮 Unreal 3D Engine',
    search_local_files: '🔍 Search Local Files',
    polyglot_runner: '🐚 Polyglot Runner (/ps /wsl /cmd)',
    vector_vault: '🧠 1M+ Vector Vault',
    ast_blast_graph: '🕸️ AST Blast Graph (/blast)',
    qlora_distiller: '🧬 QLoRA Distiller (/distill)',
    auto_healer: '🩺 Stage 1 Auto-Healer (3x)'
  };

  const toggleTool = (name) => {
    const next = { ...tools, [name]: !tools[name] };
    setTools(next);
    if (onToolToggle) onToolToggle(next);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      flexWrap: 'wrap',
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
          {enabled ? '●' : '○'} {TOOL_LABELS[key] || key.replace(/_/g, ' ')}
        </button>
      ))}
    </div>
  );
}
