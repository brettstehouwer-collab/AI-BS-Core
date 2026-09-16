import React, { useState } from 'react';
import { useAppStore } from './useAppStore';
import { getApiBase } from '../config/api';

export default function GrillSessionCard({ grillData: initialGrill, onSessionUpdated, onAcceptRecommendations, onBuildSpec, onRespond, onConclude }) {
  const storeBackendUrl = useAppStore(state => state.BACKEND_URL);
  const BACKEND_URL = storeBackendUrl || getApiBase();
  const [session, setSession] = useState(initialGrill || {});
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSpecDetails, setShowSpecDetails] = useState(false);

  const isCompleted = session.status === 'completed' || session.spec_locked;

  const handleAccept = async () => {
    setIsProcessing(true);
    try {
      if (onAcceptRecommendations) {
        await onAcceptRecommendations(session.grill_id);
      } else if (onRespond) {
        await onRespond(session.grill_id, 'yes');
      } else {
        const res = await fetch(`${BACKEND_URL}/api/mission/grill-respond`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
            'X-Client-ID': 'stehouwer_publishing'
          },
          body: JSON.stringify({ grill_id: session.grill_id, response: 'yes', operator_response: 'yes' })
        });
        const data = await res.json();
        const activeSession = data.grill_session || data.session;
        if ((data.status === 'success' || data.status === 'concluded') && activeSession) {
          setSession({ ...activeSession, ...data });
          if (onSessionUpdated) onSessionUpdated(activeSession);
        }
      }
    } catch (err) {
      console.error('Grill accept error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBuild = async () => {
    setIsProcessing(true);
    try {
      if (onBuildSpec) {
        await onBuildSpec(session.grill_id);
      } else if (onConclude) {
        await onConclude(session.grill_id);
      } else {
        const res = await fetch(`${BACKEND_URL}/api/mission/grill-conclude`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
            'X-Client-ID': 'stehouwer_publishing'
          },
          body: JSON.stringify({ grill_id: session.grill_id })
        });
        const data = await res.json();
        const activeSession = data.grill_session || data.session;
        if ((data.status === 'success' || data.status === 'concluded') && activeSession) {
          setSession({ ...activeSession, ...data });
          if (onSessionUpdated) onSessionUpdated(activeSession);
        }
      }
    } catch (err) {
      console.error('Grill build error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const context = session.context_explored || {};
  const questions = session.questions || [];
  const decisions = session.decisions_agreed || [];

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(26, 17, 10, 0.95), rgba(15, 23, 42, 0.95))',
      border: '1px solid rgba(249, 115, 22, 0.35)',
      borderRadius: '12px',
      padding: '16px',
      margin: '12px 0',
      color: '#f8fafc',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      boxShadow: '0 8px 32px rgba(249, 115, 22, 0.12)'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px', borderBottom: '1px solid rgba(249, 115, 22, 0.2)', paddingBottom: '10px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '18px' }}>🔥</span>
            <span style={{ fontWeight: 700, letterSpacing: '0.05em', color: '#fb923c', fontSize: '13px', textTransform: 'uppercase' }}>
              Architectural Grill Session (/grill)
            </span>
            <span style={{
              background: isCompleted ? 'rgba(34, 197, 94, 0.2)' : 'rgba(249, 115, 22, 0.2)',
              border: `1px solid ${isCompleted ? 'rgba(34, 197, 94, 0.4)' : 'rgba(249, 115, 22, 0.4)'}`,
              color: isCompleted ? '#4ade80' : '#fb923c',
              fontSize: '10px',
              padding: '2px 8px',
              borderRadius: '999px',
              fontWeight: 600
            }}>
              {isCompleted ? 'SPEC LOCKED & VERIFIED' : 'AWAITING OPERATOR ACK'}
            </span>
          </div>
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', fontStyle: 'italic' }}>
            "{session.proposal || 'Architectural Mission Proposal'}"
          </div>
        </div>

        {/* 1-Click Fast Triggers */}
        {!isCompleted ? (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleAccept}
              disabled={isProcessing}
              style={{
                background: 'linear-gradient(135deg, #ea580c, #c2410c)',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '7px 14px',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 2px 10px rgba(234, 88, 12, 0.4)'
              }}
            >
              {isProcessing ? '⚡ Locking...' : '✅ Accept All ("yes")'}
            </button>
            <button
              onClick={handleBuild}
              disabled={isProcessing}
              style={{
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                color: '#60a5fa',
                borderRadius: '8px',
                padding: '7px 12px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              🚀 Build (/build)
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#4ade80', fontSize: '12px', fontWeight: 600 }}>
            <span>🔒 Locked in</span>
            <code style={{ background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8' }}>mission_spec.md</code>
          </div>
        )}
      </div>

      {/* Codebase Exploration Verified Box */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.6)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        padding: '10px 12px',
        marginBottom: '12px',
        fontSize: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#38bdf8', marginBottom: '6px' }}>
          <span>📦</span>
          <span>Codebase Context Verified (Exploration First)</span>
        </div>
        <div style={{ color: '#94a3b8', lineHeight: 1.5 }}>
          {context.summary || 'Inspected workspace repositories, SQLite database schemas, and configurations.'}
        </div>
        {context.verified_files && context.verified_files.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
            {context.verified_files.map((f, i) => (
              <span key={i} style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', color: '#7dd3fc', fontSize: '10px', padding: '2px 6px', borderRadius: '4px' }}>
                📄 {f.name || f.path}
              </span>
            ))}
            {context.verified_schemas && context.verified_schemas.map((s, i) => (
              <span key={i} style={{ background: 'rgba(168, 85, 247, 0.1)', border: '1px solid rgba(168, 85, 247, 0.25)', color: '#c084fc', fontSize: '10px', padding: '2px 6px', borderRadius: '4px' }}>
                🏛️ {s}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Decision Tree Traversal: Questions & Opinionated Recommendations */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '12px' }}>
        {questions.map((q, idx) => (
          <div key={idx} style={{
            background: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            borderRadius: '8px',
            padding: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#fb923c', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Branch {idx + 1}: {q.branch}
              </span>
              <span style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                background: isCompleted ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                color: isCompleted ? '#4ade80' : '#facc15'
              }}>
                {isCompleted ? 'LOCKED' : 'PROPOSED'}
              </span>
            </div>
            <div style={{ fontSize: '13px', color: '#cbd5e1', marginBottom: '8px', lineHeight: 1.4 }}>
              {q.question}
            </div>
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              borderRadius: '6px',
              padding: '8px 10px',
              fontSize: '12px',
              color: '#86efac'
            }}>
              <strong style={{ color: '#4ade80' }}>👉 Recommended Decision:</strong> {q.recommendation}
            </div>
          </div>
        ))}
      </div>

      {/* Locked Specification Transition View */}
      {isCompleted && (
        <div style={{
          background: 'rgba(34, 197, 94, 0.08)',
          border: '1px solid rgba(34, 197, 94, 0.3)',
          borderRadius: '8px',
          padding: '10px 12px',
          fontSize: '12px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ color: '#86efac', fontWeight: 600 }}>
              🚀 Transitioned directly into Stage 2 (Planning & Execution)
            </div>
            <button
              onClick={() => setShowSpecDetails(!showSpecDetails)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#38bdf8',
                fontSize: '11px',
                cursor: 'pointer',
                textDecoration: 'underline'
              }}
            >
              {showSpecDetails ? 'Hide Spec' : 'View Locked Spec'}
            </button>
          </div>
          {showSpecDetails && (
            <pre style={{
              marginTop: '8px',
              background: '#0b1120',
              padding: '8px',
              borderRadius: '4px',
              fontSize: '11px',
              overflowX: 'auto',
              color: '#cbd5e1',
              maxHeight: '200px'
            }}>
              {session.spec_content || JSON.stringify(decisions, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
