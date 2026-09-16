import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';
import './ContentGovernanceRiskModal.css';

export default function ContentGovernanceRiskModal({ 
  isOpen, 
  onClose, 
  initialText = '', 
  onApplyRefinement 
}) {
  const [text, setText] = useState(initialText);
  const [category, setCategory] = useState('marketing');
  const [audience, setAudience] = useState('external_client');
  const [threshold, setThreshold] = useState(45.0);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  useEffect(() => {
    if (initialText) {
      setText(initialText);
    }
  }, [initialText]);

  useEffect(() => {
    if (isOpen && text && text.trim()) {
      runAudit();
    }
  }, [isOpen]);

  const runAudit = async () => {
    if (!text || !text.trim()) return;
    setLoading(true);
    try {
      const response = await fetch(`${getApiBase()}/api/v1/content-governance/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          context_category: category,
          target_audience: audience,
          custom_threshold: parseFloat(threshold)
        })
      });
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      console.error('Content governance audit error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyRefinement = (refinement) => {
    let updatedText = text;
    if (refinement.original && updatedText.includes(refinement.original)) {
      updatedText = updatedText.replace(refinement.original, refinement.refined);
    } else {
      updatedText = refinement.refined;
    }
    setText(updatedText);
    if (onApplyRefinement) {
      onApplyRefinement(updatedText);
    }
    // Re-run audit with refined text
    setTimeout(() => {
      runAudit();
    }, 100);
  };

  const handleCopyRefinement = (refinedText, idx) => {
    navigator.clipboard.writeText(refinedText);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (!isOpen) return null;

  const vectorLabels = {
    litigation_legal: 'Litigation & Legal Liability',
    harassment_hr: 'Harassment & HR Policy Risk',
    pr_polarization: 'PR & Sociocultural Polarization',
    discriminatory_sentiment: 'Discriminatory Sentiment & Bias',
    confidentiality_databreach: 'Confidentiality & Data Breach Risk',
    aggressive_tone: 'Aggressive & High-Conflict Tone'
  };

  return (
    <div className="governance-modal-overlay">
      <div className="governance-modal-container">
        {/* Header */}
        <div className="governance-modal-header">
          <div className="governance-header-title">
            <h2>🛡️ Content Risk & Compliance Governance Analyzer</h2>
          </div>
          <button className="governance-close-btn" onClick={onClose} title="Close Modal">×</button>
        </div>

        {/* Body */}
        <div className="governance-modal-body">
          {/* Controls Bar */}
          <div className="governance-controls-grid">
            <div className="governance-control-group">
              <label>Department Context</label>
              <select 
                className="governance-select"
                value={category} 
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="marketing">📢 Marketing & Campaigns</option>
                <option value="sales">💼 Sales & Client Outreach</option>
                <option value="hr">👥 Human Resources & Internal</option>
                <option value="legal">⚖️ Legal & Contracts</option>
                <option value="executive">👔 Executive Correspondence</option>
              </select>
            </div>

            <div className="governance-control-group">
              <label>Target Audience</label>
              <select 
                className="governance-select"
                value={audience} 
                onChange={(e) => setAudience(e.target.value)}
              >
                <option value="external_client">🌐 External Client / Customer</option>
                <option value="internal_staff">🏢 Internal Staff / Team</option>
                <option value="public_press_release">📰 Public Press Release</option>
                <option value="executive_board">🏛️ Executive Board / Investors</option>
              </select>
            </div>

            <div className="governance-control-group">
              <label>Risk Threshold Sensitivity (τ: {threshold}%)</label>
              <input 
                type="range"
                className="governance-slider"
                min="10" 
                max="90" 
                step="5"
                value={threshold} 
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
              />
            </div>
          </div>

          {/* Text Editor Section */}
          <div className="governance-editor-section">
            <textarea
              className="governance-textarea"
              placeholder="Paste or draft outbound corporate email, campaign copy, press release, or document text to analyze latent risk..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />

            <button 
              className="governance-audit-btn"
              onClick={runAudit}
              disabled={loading}
            >
              {loading ? '⏳ Calculating Vector Scores...' : '⚡ Run Risk & Compliance Audit'}
            </button>
          </div>

          {/* Results Dashboard */}
          {analysis && (
            <div className="governance-results-grid">
              {/* Left Column: QRS Gauge & Vector Heatmap */}
              <div className="governance-card">
                <div className="governance-card-title">
                  <span>Quantifiable Risk Score (QRS)</span>
                  <span style={{ fontSize: '0.72rem', color: '#8b949e' }}>aibs_reasoning_engine.py</span>
                </div>

                <div className="governance-score-hud">
                  <div>
                    <div className="governance-score-number" style={{ color: analysis.status_color }}>
                      {analysis.quantifiable_risk_score}%
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '4px' }}>
                      Threshold (τ): {analysis.threshold}%
                    </div>
                  </div>

                  <div 
                    className="governance-status-pill" 
                    style={{ 
                      background: `${analysis.status_color}20`, 
                      color: analysis.status_color,
                      border: `1px solid ${analysis.status_color}`
                    }}
                  >
                    {analysis.status}
                  </div>
                </div>

                {/* 6 Multidimensional Risk Vectors */}
                <div className="governance-card-title" style={{ marginTop: '10px' }}>
                  <span>Multidimensional Risk Vectors</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {Object.entries(analysis.vector_breakdown).map(([vecKey, vecVal]) => {
                    const label = vectorLabels[vecKey] || vecKey;
                    const isSpike = vecVal > analysis.threshold;
                    const barColor = vecVal > 60 ? '#ef4444' : vecVal > 30 ? '#f59e0b' : '#10b981';
                    return (
                      <div key={vecKey} className="governance-vector-item">
                        <div className="governance-vector-header">
                          <span style={{ fontWeight: isSpike ? 700 : 400, color: isSpike ? '#f8fafc' : '#c9d1d9' }}>
                            {label}
                          </span>
                          <span style={{ fontWeight: 700, color: barColor }}>{vecVal}%</span>
                        </div>
                        <div className="governance-vector-bar-bg">
                          <div 
                            className="governance-vector-bar-fill"
                            style={{ width: `${Math.max(4, vecVal)}%`, background: barColor }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Terminology Optimization & Refinements */}
              <div className="governance-card">
                <div className="governance-card-title">
                  <span>Terminology Optimization & Refinements</span>
                  <span style={{ fontSize: '0.72rem', color: '#10b981' }}>
                    {analysis.refinements.length} Refinement(s) Found
                  </span>
                </div>

                <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 4px 0' }}>
                  {analysis.executive_summary}
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', maxHeight: '340px' }}>
                  {analysis.refinements.length === 0 ? (
                    <div style={{ padding: '20px', textAlign: 'center', background: '#0d1117', borderRadius: '8px', border: '1px dashed #30363d', color: '#10b981' }}>
                      ✨ No high-risk terminology detected. Communication aligns with corporate compliance standards!
                    </div>
                  ) : (
                    analysis.refinements.map((ref, idx) => (
                      <div key={idx} className="governance-refinement-box">
                        <div className="refinement-original">
                          Original: "{ref.original}"
                        </div>
                        <div className="refinement-improved">
                          Refined: "{ref.refined}"
                        </div>
                        <div className="refinement-reason">
                          💡 Rationale: {ref.reason}
                        </div>
                        <div className="refinement-actions">
                          <button 
                            className="refinement-apply-btn"
                            onClick={() => handleApplyRefinement(ref)}
                          >
                            ⚡ 1-Click Replace & Apply
                          </button>
                          <button 
                            className="refinement-apply-btn"
                            style={{ borderColor: '#64748b', color: '#cbd5e1' }}
                            onClick={() => handleCopyRefinement(ref.refined, idx)}
                          >
                            {copiedIndex === idx ? '✓ Copied' : '📋 Copy Refined Text'}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="governance-modal-footer">
          <span>Engine Initialized: aibs_reasoning_engine.py • aibs_autograd_engine.py</span>
          <span>Stehouwer Publishing Content Governance OS v5.54.0</span>
        </div>
      </div>
    </div>
  );
}
