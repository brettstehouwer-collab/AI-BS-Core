import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';

export default function ReasoningAttentionTab({ backendUrl }) {
  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;

  const [activeSubView, setActiveSubView] = useState('attention'); // 'tokenization' | 'attention' | 'graph' | 'self_solve'
  
  // Shared Input State
  const [inputText, setInputText] = useState("AI-BS self-attention transformer reasoning with dynamic autograd execution");
  const [isBidirectional, setIsBidirectional] = useState(true);

  // Response States
  const [tokensData, setTokensData] = useState([]);
  const [attentionData, setAttentionData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  
  // Self Solve State
  const [solvePrompt, setSolvePrompt] = useState("Optimize RTX 4090 autograd CUDA batch memory allocation");
  const [solveData, setSolveData] = useState(null);
  const [isSolving, setIsSolving] = useState(false);

  const fetchTokenization = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/reasoning/tokenize-encode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText })
      });
      if (res.ok) {
        const json = await res.json();
        if (json.tokens) setTokensData(json.tokens);
      }
    } catch (e) {
      console.warn('Failed to fetch tokenization:', e);
    }
  };

  const fetchAttentionMatrix = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/reasoning/attention-matrix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText, is_bidirectional: isBidirectional })
      });
      if (res.ok) {
        const json = await res.json();
        if (json.data) setAttentionData(json.data);
      }
    } catch (e) {
      console.warn('Failed to fetch attention matrix:', e);
    }
  };

  const fetchGraphReasoning = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/reasoning/graph-reasoning`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText })
      });
      if (res.ok) {
        const json = await res.json();
        if (json.graph) setGraphData(json.graph);
      }
    } catch (e) {
      console.warn('Failed to fetch graph reasoning:', e);
    }
  };

  const handleRunSelfSolver = async () => {
    setIsSolving(true);
    try {
      const res = await fetch(`${apiHost}/v1/reasoning/self-solve-refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: solvePrompt, max_iterations: 3 })
      });
      if (res.ok) {
        const json = await res.json();
        setSolveData(json);
      }
    } catch (e) {
      console.warn('Failed to run self-solver:', e);
    } finally {
      setIsSolving(false);
    }
  };

  useEffect(() => {
    fetchTokenization();
    fetchAttentionMatrix();
    fetchGraphReasoning();
  }, [inputText, isBidirectional]);

  return (
    <div style={{ padding: '24px', color: '#e6edf3', height: '100%', overflowY: 'auto', background: '#090d16', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Studio Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: '800', margin: 0, color: '#38bdf8' }}>
            🧠 AI-BS Self-Refinement, Attention & Graph Reasoning Studio
          </h1>
          <p style={{ fontSize: '13px', color: '#8b949e', margin: '4px 0 0 0' }}>
            Multi-Head Self-Attention, Contextual Token Encodings, Graph Entity Reasoning, and Autonomous Iterative Self-Correction
          </p>
        </div>
      </div>

      {/* Input Prompt Control Bar */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '16px', marginBottom: '24px' }}>
        <label style={{ fontSize: '12px', color: '#8b949e', fontWeight: '700', display: 'block', marginBottom: '6px' }}>
          Input Text / Reasoning Target:
        </label>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            style={{ flex: 1, minWidth: '280px', padding: '10px 14px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
          />

          <button
            onClick={() => setIsBidirectional(!isBidirectional)}
            style={{ padding: '10px 16px', background: isBidirectional ? '#1f6feb' : '#8957e5', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer' }}
          >
            {isBidirectional ? '🌐 Mode: Bidirectional' : '➡️ Mode: Unidirectional (Causal)'}
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', overflowX: 'auto' }}>
        <button
          onClick={() => setActiveSubView('attention')}
          style={{
            padding: '10px 20px',
            background: activeSubView === 'attention' ? '#1f6feb' : '#161b22',
            color: '#ffffff',
            border: activeSubView === 'attention' ? '1px solid #38bdf8' : '1px solid #30363d',
            borderRadius: '8px',
            fontWeight: '600',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          ⚡ Self-Attention Matrix
        </button>

        <button
          onClick={() => setActiveSubView('tokenization')}
          style={{
            padding: '10px 20px',
            background: activeSubView === 'tokenization' ? '#1f6feb' : '#161b22',
            color: '#ffffff',
            border: activeSubView === 'tokenization' ? '1px solid #38bdf8' : '1px solid #30363d',
            borderRadius: '8px',
            fontWeight: '600',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          🔤 Tokenization & Encodings ({tokensData.length} Tokens)
        </button>

        <button
          onClick={() => setActiveSubView('graph')}
          style={{
            padding: '10px 20px',
            background: activeSubView === 'graph' ? '#1f6feb' : '#161b22',
            color: '#ffffff',
            border: activeSubView === 'graph' ? '1px solid #38bdf8' : '1px solid #30363d',
            borderRadius: '8px',
            fontWeight: '600',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          🕸️ Graph Entity Reasoning ({graphData ? graphData.node_count : 0} Nodes)
        </button>

        <button
          onClick={() => setActiveSubView('self_solve')}
          style={{
            padding: '10px 20px',
            background: activeSubView === 'self_solve' ? '#1f6feb' : '#161b22',
            color: '#ffffff',
            border: activeSubView === 'self_solve' ? '1px solid #38bdf8' : '1px solid #30363d',
            borderRadius: '8px',
            fontWeight: '600',
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          🔄 Self-Problem Solving & Refinement
        </button>
      </div>

      {/* SUB-VIEW 1: SELF-ATTENTION MATRIX HEATMAP */}
      {activeSubView === 'attention' && attentionData && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h2 style={{ fontSize: '16px', margin: 0, color: '#f0f6fc' }}>
                ⚡ Scaled Dot-Product Self-Attention Weights ({attentionData.mode})
              </h2>
              <p style={{ fontSize: '12px', color: '#8b949e', margin: '2px 0 0 0' }}>
                Attention(Q, K, V) = softmax( (Q * K^T) / sqrt(d_k) ) * V
              </p>
            </div>
          </div>

          <div style={{ overflowX: 'auto', background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <table style={{ borderCollapse: 'collapse', fontSize: '12px', textAlign: 'center' }}>
              <thead>
                <tr>
                  <th style={{ padding: '8px', color: '#8b949e', textAlign: 'left' }}>Q \ K</th>
                  {attentionData.tokens.map((tok, i) => (
                    <th key={i} style={{ padding: '8px', color: '#38bdf8', fontWeight: '700' }}>{tok}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {attentionData.tokens.map((tokQ, rowIdx) => (
                  <tr key={rowIdx}>
                    <td style={{ padding: '8px', color: '#38bdf8', fontWeight: '700', textAlign: 'left' }}>{tokQ}</td>
                    {attentionData.attention_matrix[rowIdx].map((weight, colIdx) => {
                      const alpha = Math.min(1.0, weight * 3.5);
                      return (
                        <td
                          key={colIdx}
                          style={{
                            padding: '10px',
                            background: `rgba(31, 111, 235, ${alpha})`,
                            color: alpha > 0.4 ? '#ffffff' : '#8b949e',
                            fontWeight: alpha > 0.4 ? '800' : '400',
                            border: '1px solid #21262d'
                          }}
                        >
                          {weight.toFixed(3)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: TOKENIZATION & ENCODINGS */}
      {activeSubView === 'tokenization' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 12px 0', color: '#38bdf8' }}>🔤 Subword & Contextual Position Encodings</h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
            {tokensData.map(t => (
              <div key={t.id} style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '12px' }}>
                <div style={{ fontSize: '14px', fontWeight: '800', color: '#f0f6fc' }}>{t.token}</div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>Pos ID: {t.id}</div>
                <div style={{ fontSize: '11px', color: '#38bdf8', marginTop: '2px' }}>Harmonic Norm: {t.position_embedding_norm}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: GRAPH-BASED ENTITY REASONING */}
      {activeSubView === 'graph' && graphData && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 12px 0', color: '#a78bfa' }}>🕸️ Hierarchical Entity & Dependency Parse Graph</h2>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div>
              <h3 style={{ fontSize: '14px', color: '#a78bfa', margin: '0 0 10px 0' }}>Entity Nodes ({graphData.node_count})</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {graphData.nodes.map(n => (
                  <span key={n.id} style={{ padding: '6px 12px', background: '#161b22', border: '1px solid #a78bfa', borderRadius: '16px', fontSize: '12px', fontWeight: '600', color: '#e6edf3' }}>
                    {n.label}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: '14px', color: '#4ade80', margin: '0 0 10px 0' }}>Dependency Edges ({graphData.edge_count})</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '240px', overflowY: 'auto' }}>
                {graphData.edges.map((e, idx) => (
                  <div key={idx} style={{ fontSize: '11px', color: '#8b949e', background: '#161b22', padding: '6px 10px', borderRadius: '4px', border: '1px solid #21262d' }}>
                    <span style={{ color: '#38bdf8', fontWeight: '700' }}>{e.source.replace('node_', '')}</span>
                    <span style={{ color: '#f59e0b', margin: '0 6px' }}>{`──[${e.relation}]──>`}</span>

                    <span style={{ color: '#4ade80', fontWeight: '700' }}>{e.target.replace('node_', '')}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: SELF-PROBLEM SOLVING & ITERATIVE REFINEMENT CONSOLE */}
      {activeSubView === 'self_solve' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 6px 0', color: '#4ade80' }}>🔄 Autonomous Iterative Refinement & Error Correction</h2>
          <p style={{ fontSize: '12px', color: '#8b949e', margin: '0 0 14px 0' }}>
            Generates initial output, self-evaluates for flaws, adjusts parameters, and re-executes inference until verified.
          </p>

          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <input
              type="text"
              value={solvePrompt}
              onChange={(e) => setSolvePrompt(e.target.value)}
              style={{ flex: 1, padding: '10px 14px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
            />
            <button
              onClick={handleRunSelfSolver}
              disabled={isSolving}
              style={{ padding: '10px 20px', background: 'linear-gradient(90deg, #238636, #4ade80)', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer' }}
            >
              {isSolving ? '🔄 Refining Solution...' : '🚀 Execute Self-Solving Loop'}
            </button>
          </div>

          {solveData && (
            <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <span style={{ fontSize: '14px', fontWeight: '800', color: '#4ade80' }}>✓ Solution Quality Score: {solveData.final_quality_score}%</span>
                <span style={{ fontSize: '12px', color: '#8b949e' }}>Completed in {solveData.total_iterations} Iteration Steps</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {solveData.iteration_history.map(item => (
                  <div key={item.iteration} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '6px', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8', marginBottom: '4px' }}>
                      Iteration {item.iteration} — Quality Score: {item.quality_score}%
                    </div>
                    {item.detected_issues.length > 0 && (
                      <div style={{ fontSize: '11px', color: '#f59e0b', marginBottom: '6px' }}>
                        ⚠️ Detected Issues: {item.detected_issues.join(' | ')}
                      </div>
                    )}
                    <div style={{ fontSize: '12px', color: '#e6edf3', whiteSpace: 'pre-wrap', lineHeight: '1.4', background: '#0d1117', padding: '8px', borderRadius: '4px' }}>
                      {item.refined_draft}
                    </div>
                  </div>
                ))}
              </div>

              {solveData.final_solution && (
                <div style={{ marginTop: '16px', background: 'linear-gradient(180deg, #161b22, #0d1117)', border: '1px solid #238636', borderRadius: '8px', padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '14px', fontWeight: '800', color: '#4ade80' }}>💎 Final Verified Solution (Synthesized by Stehouwer LLM)</span>
                      <span style={{ fontSize: '11px', background: '#23863633', color: '#4ade80', border: '1px solid #238636', padding: '2px 8px', borderRadius: '12px', fontWeight: '700' }}>100% Converged</span>
                    </div>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(solveData.final_solution);
                        alert('Copied Final Solution to clipboard!');
                      }}
                      style={{ padding: '4px 12px', background: '#21262d', color: '#38bdf8', border: '1px solid #30363d', borderRadius: '4px', fontSize: '11px', fontWeight: '600', cursor: 'pointer' }}
                    >
                      📋 Copy Solution
                    </button>
                  </div>
                  <div style={{ fontSize: '13px', color: '#f0f6fc', whiteSpace: 'pre-wrap', lineHeight: '1.6', background: '#090d16', padding: '14px', borderRadius: '6px', border: '1px solid #30363d', maxHeight: '400px', overflowY: 'auto' }}>
                    {solveData.final_solution}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
