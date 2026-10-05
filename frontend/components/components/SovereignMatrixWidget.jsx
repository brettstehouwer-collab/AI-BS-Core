import React, { useState } from 'react';

const SOVEREIGN_TOOLS = [
  // 1. Terminal Coding
  {
    id: 'aider',
    name: 'Aider (aider-chat)',
    category: 'Terminal Coding Agent',
    replaces: 'Claude Code / Codex CLI',
    repo: 'https://github.com/paul-gauthier/aider',
    license: 'Apache 2.0',
    engine: 'Python / Local Ollama (Port 11434)',
    desc: 'Terminal AI pair programmer with git repo mapping and multi-file automated git commits.',
    cliCmd: 'aider --model ollama/qwen2.5-coder:32b --api-base http://127.0.0.1:11434'
  },
  {
    id: 'openhands',
    name: 'OpenHands (f. OpenDevin)',
    category: 'Terminal Coding Agent',
    replaces: 'Devin / Autonomous Sweeper',
    repo: 'https://github.com/All-Hands-AI/OpenHands',
    license: 'MIT',
    engine: 'Docker Sandbox / Python / WSL2',
    desc: 'Autonomous software development agent executing shell commands, browsing docs, and writing code in sandboxes.',
    cliCmd: 'docker run -it --pull=always -e SANDBOX_USER_ID=1000 -v /var/run/docker.sock:/var/run/docker.sock -p 3000:3000 ghcr.io/all-hands-ai/openhands:main'
  },
  {
    id: 'opencode',
    name: 'OpenCodeInterpreter',
    category: 'Model Harness & Runner',
    replaces: 'DeepSeek Harness / Qwen Code',
    repo: 'https://github.com/OpenCodeInterpreter/OpenCodeInterpreter',
    license: 'Apache 2.0',
    engine: 'Python / PyTorch / Local vLLM',
    desc: 'Open-source code generation, execution, and debugging harness running open weights locally.',
    cliCmd: 'python -m opencodeinterpreter.cli --model qwen2.5-coder'
  },
  {
    id: 'plandex',
    name: 'Plandex',
    category: 'Terminal Coding Agent',
    replaces: 'Cursor Multi-File Planner',
    repo: 'https://github.com/plandex-ai/plandex',
    license: 'AGPL-3.0',
    engine: 'Go / Local Ollama Endpoint',
    desc: 'Terminal engine for complex multi-file coding tasks, branches, and version-controlled diff sets.',
    cliCmd: 'plandex new && plandex model ollama/qwen2.5-coder'
  },

  // 2. IDE Extensions
  {
    id: 'roocode',
    name: 'Roo Code (Roo-Cline)',
    category: 'Agentic IDE Extension',
    replaces: 'Cline / Copilot Workspace',
    repo: 'https://github.com/RooVetGit/Roo-Cline',
    license: 'Apache 2.0',
    engine: 'TypeScript / VS Code / Local Ollama',
    desc: 'Community fork of Cline with custom personas, mode switching, tool-use execution, and zero telemetry.',
    cliCmd: 'code --install-extension RooVeterinaryInc.roo-cline'
  },
  {
    id: 'continue',
    name: 'Continue (continue.dev)',
    category: 'Agentic IDE Extension',
    replaces: 'GitHub Copilot / Tabnine',
    repo: 'https://github.com/continuedev/continue',
    license: 'Apache 2.0',
    engine: 'TypeScript / VS Code & JetBrains',
    desc: 'Open-source AI code assistant connecting tab autocomplete and sidebar chat directly to Port 11434.',
    cliCmd: 'code --install-extension Continue.continue'
  },
  {
    id: 'void',
    name: 'Void Editor',
    category: 'Agentic IDE Extension',
    replaces: 'Cursor AI IDE',
    repo: 'https://github.com/voideditor/void',
    license: 'Apache 2.0',
    engine: 'Electron / VS Code Core / Local Models',
    desc: 'Open-source Cursor alternative enabling complete privacy, local model connections, and zero tracking.',
    cliCmd: 'winget install VoidEditor.Void'
  },

  // 3. Desktop Hubs & UI
  {
    id: 'jan',
    name: 'Jan AI (jan.ai)',
    category: 'Agentic Desktop UI',
    replaces: 'Hermes Desktop / ChatGPT App',
    repo: 'https://github.com/janhq/jan',
    license: 'AGPLv3',
    engine: 'Electron / C++ llama.cpp / Local Ollama',
    desc: '100% offline local AI desktop client running GGUF engines or routing to AI-BS Port 11434.',
    cliCmd: 'winget install Jan.Jan'
  },
  {
    id: 'librechat',
    name: 'LibreChat',
    category: 'Agentic Desktop UI',
    replaces: 'Claude.ai / ChatGPT Team Workspace',
    repo: 'https://github.com/danny-avila/LibreChat',
    license: 'MIT',
    engine: 'Node.js / React / Docker / Port 8000',
    desc: 'Comprehensive multi-model agent UI with code execution plugins, custom agent creation, and local RAG.',
    cliCmd: 'docker compose -f docker-compose.yml up -d'
  },
  {
    id: 'anythingllm',
    name: 'AnythingLLM Desktop',
    category: 'Agentic Desktop UI',
    replaces: 'NotebookLM / Custom Enterprise RAG',
    repo: 'https://github.com/Mintplex-Labs/anything-llm',
    license: 'MIT',
    engine: 'Electron / Local ChromaDB (Port 8002)',
    desc: 'Desktop workspace manager supporting local vector embeddings, document chats, and web scraping agents.',
    cliCmd: 'winget install MintplexLabs.AnythingLLM'
  },
  {
    id: 'nous_hermes',
    name: 'Nous Hermes Runners',
    category: 'Model Harness & Runner',
    replaces: 'Proprietary Function Calling APIs',
    repo: 'https://github.com/NousResearch/Hermes-Function-Calling',
    license: 'MIT',
    engine: 'Python / JSON Schema / RTX 4090',
    desc: 'Structured function calling, tool routing, and agent loops for local open-weights reasoning.',
    cliCmd: 'python -m pip install hermes-function-calling'
  }
];

export default function SovereignMatrixWidget({ onLaunchAgent }) {
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  const categories = [
    { id: 'all', label: 'All Open-Source Tools' },
    { id: 'Terminal Coding Agent', label: 'Terminal Coding' },
    { id: 'Agentic IDE Extension', label: 'IDE Extensions' },
    { id: 'Agentic Desktop UI', label: 'Desktop Hubs' },
    { id: 'Model Harness & Runner', label: 'Model Harnesses' }
  ];

  const filtered = SOVEREIGN_TOOLS.filter((tool) => {
    const matchCat = activeCategory === 'all' || tool.category === activeCategory;
    const search = searchTerm.toLowerCase();
    const matchSearch =
      tool.name.toLowerCase().includes(search) ||
      tool.replaces.toLowerCase().includes(search) ||
      tool.desc.toLowerCase().includes(search);
    return matchCat && matchSearch;
  });

  const handleCopyCmd = (id, cmd) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(cmd);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2500);
    }
  };

  return (
    <div className="glass-panel" style={{ height: '100%', overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
        <div>
          <h3 className="drag-handle cursor-move" style={{ margin: 0, fontSize: '1rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🌐 Sovereign Open-Source Matrix</span>
            <span style={{ fontSize: '0.7rem', background: '#0284c7', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
              Zero-Cost Mandate
            </span>
          </h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>
            100% self-hosted, local, and open-weights replacements for commercial coding agents and developer platforms.
          </p>
        </div>

        {/* Search */}
        <input
          type="text"
          placeholder="Filter tools or commercial targets..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-dark"
          style={{ width: '220px', padding: '5px 10px', fontSize: '0.78rem' }}
        />
      </div>

      {/* Category Pills */}
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
        {categories.map((cat) => (
          <button
            key={cat.id}
            type="button"
            onClick={() => setActiveCategory(cat.id)}
            style={{
              background: activeCategory === cat.id ? '#2563eb' : '#1e293b',
              color: activeCategory === cat.id ? '#ffffff' : '#94a3b8',
              border: '1px solid #334155',
              padding: '4px 10px',
              borderRadius: '6px',
              fontSize: '0.74rem',
              cursor: 'pointer',
              fontWeight: activeCategory === cat.id ? 700 : 500,
              transition: 'all 0.15s'
            }}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Tool Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '12px', flex: 1 }}>
        {filtered.map((tool) => (
          <div
            key={tool.id}
            style={{
              background: '#090d16',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              transition: 'border-color 0.2s',
            }}
          >
            <div>
              {/* Top row: Name + Badge */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                <a
                  href={tool.repo}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#38bdf8', fontWeight: 700, fontSize: '0.88rem', textDecoration: 'none' }}
                >
                  {tool.name} ↗
                </a>
                <span style={{ fontSize: '0.65rem', background: '#1e293b', color: '#10b981', padding: '2px 6px', borderRadius: '4px', border: '1px solid #334155' }}>
                  {tool.license}
                </span>
              </div>

              {/* Target Replaced */}
              <div style={{ fontSize: '0.72rem', color: '#f59e0b', marginBottom: '6px' }}>
                Replaces: <strong>{tool.replaces}</strong>
              </div>

              {/* Description */}
              <p style={{ fontSize: '0.75rem', color: '#cbd5e1', margin: '0 0 8px 0', lineHeight: 1.35 }}>
                {tool.desc}
              </p>

              {/* Engine Spec */}
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '8px', fontFamily: 'monospace' }}>
                ⚙️ {tool.engine}
              </div>
            </div>

            {/* CLI Command & Actions */}
            <div>
              <div style={{ background: '#020617', border: '1px solid #1e293b', borderRadius: '4px', padding: '6px 8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                <code style={{ fontSize: '0.68rem', color: '#38bdf8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  {tool.cliCmd}
                </code>
                <button
                  type="button"
                  onClick={() => handleCopyCmd(tool.id, tool.cliCmd)}
                  style={{
                    background: copiedId === tool.id ? '#10b981' : '#1e293b',
                    color: '#fff',
                    border: 'none',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.68rem',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {copiedId === tool.id ? '✓ Copied' : 'Copy'}
                </button>
              </div>

              {onLaunchAgent && (
                <button
                  type="button"
                  onClick={() => onLaunchAgent(tool.id, tool.cliCmd)}
                  style={{
                    width: '100%',
                    marginTop: '8px',
                    background: '#1e293b',
                    color: '#f8fafc',
                    border: '1px solid #334155',
                    padding: '5px',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                    cursor: 'pointer',
                    fontWeight: 600
                  }}
                >
                  🚀 Quick Launch via AI-BS
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
