import React, { useState } from 'react';

export default function VectorVaultManager() {
  const [collection, setCollection] = useState('stehouwer_vector_memory');
  const [queryText, setQueryText] = useState('SHM ring buffer latency');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any[]>([
    { id: 'doc_101', distance: 0.12, content: 'Sub-microsecond SHM ring buffer architecture mapped at Local\\AI_BS_IPC_SHM_RING.', source: 'ringbuffer_multitopic.h' },
    { id: 'doc_102', distance: 0.18, content: 'FastAPI WebSocket Gateway streaming telemetry at 20 Hz (50ms interval).', source: 'shm_websocket_gateway.py' },
    { id: 'doc_103', distance: 0.24, content: 'ComfyUI SDXL & Wan2.1 workflow triggers pushing GPU stats over Topic 0x0006.', source: 'comfyui_workflow_trigger.py' }
  ]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim()) return;
    setIsSearching(true);
    try {
      const res = await fetch('http://localhost:8001/api/v1/vault/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection_name: collection, query_text: queryText, top_k: 5 })
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data.results);
      }
    } catch (err) {
      console.warn('Backend vector vault query using offline baseline fallback.', err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div style={{
      backgroundColor: '#0d1117',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '16px',
      color: '#c9d1d9',
      marginTop: '12px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, color: '#00d2ff', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🧠</span> ChromaDB Vector Vault Manager (Topic 0x0005)
        </h4>
        <select
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          style={{
            backgroundColor: '#161b22',
            border: '1px solid #30363d',
            color: '#58a6ff',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px'
          }}
        >
          <option value="stehouwer_vector_memory">stehouwer_vector_memory (1,420 docs)</option>
          <option value="web_research_vault">web_research_vault (850 docs)</option>
          <option value="ast_codebase_embeddings">ast_codebase_embeddings (3,200 docs)</option>
        </select>
      </div>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          type="text"
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          placeholder="Search vector embeddings..."
          style={{
            flex: 1,
            backgroundColor: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '4px',
            color: '#f0f6fc',
            padding: '8px 12px',
            fontSize: '12px'
          }}
        />
        <button
          type="submit"
          disabled={isSearching}
          style={{
            backgroundColor: '#238636',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            padding: '8px 16px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          {isSearching ? 'Querying...' : '🔍 Vector Search'}
        </button>
      </form>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {results.map((item, idx) => (
          <div key={idx} style={{
            backgroundColor: '#161b22',
            border: '1px solid #21262d',
            borderRadius: '6px',
            padding: '10px 12px',
            fontSize: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#58a6ff', fontWeight: 600 }}>{item.id} • {item.source || item.metadata?.source}</span>
              <span style={{ color: '#7ee787', fontSize: '11px' }}>Dist: {item.distance}</span>
            </div>
            <div style={{ color: '#8b949e', fontSize: '11px', fontFamily: 'Consolas, monospace' }}>
              {item.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
