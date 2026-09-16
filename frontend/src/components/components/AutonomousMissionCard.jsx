import React, { useState } from 'react';
import { useAppStore } from './useAppStore';
import { getApiBase } from '../config/api';

export default function AutonomousMissionCard({ missionData: initialMission, onMissionUpdated }) {
  const storeBackendUrl = useAppStore(state => state.BACKEND_URL);
  const BACKEND_URL = storeBackendUrl || getApiBase();
  const [mission, setMission] = useState(initialMission || {});
  const [isRunning, setIsRunning] = useState(false);
  const [activeTaskRunning, setActiveTaskRunning] = useState(null);
  const [expandedTask, setExpandedTask] = useState(null);
  const [showJson, setShowJson] = useState(false);

  const PHASES = [
    { id: 1, name: 'Phase 1: Intent & Skills', icon: '🎯', desc: 'Telemetry & skill indexing' },
    { id: 2, name: 'Phase 2: Planning', icon: '📋', desc: 'Atomic blueprint deconstruction' },
    { id: 3, name: 'Phase 3: Tool Loop', icon: '⚙️', desc: 'Host file & terminal mutations' },
    { id: 4, name: 'Phase 4: Verification', icon: '🧪', desc: 'Syntax & self-healing tests' },
    { id: 5, name: 'Phase 5: Delivery', icon: '🚀', desc: '4-mirror parity & production' }
  ];

  const handleRunFull = async () => {
    if (!mission.goal) return;
    setIsRunning(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/mission/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ goal: mission.goal, mode: 'auto' })
      });
      const data = await res.json();
      if (data.status === 'success' && data.mission) {
        setMission(data.mission);
        if (onMissionUpdated) onMissionUpdated(data.mission);
      }
    } catch (err) {
      console.error('Mission run error:', err);
    } finally {
      setIsRunning(false);
    }
  };

  const handleExecuteStep = async (taskId) => {
    if (!mission.mission_id) return;
    setActiveTaskRunning(taskId);
    try {
      const res = await fetch(`${BACKEND_URL}/api/mission/execute-step`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ mission_id: mission.mission_id, task_id: taskId })
      });
      const data = await res.json();
      if (data.status === 'success' && data.task) {
        setMission(prev => ({
          ...prev,
          tasks: (prev.tasks || []).map(t => t.task_id === taskId ? data.task : t),
          completed_tasks: data.mission_progress?.completed ?? prev.completed_tasks
        }));
      }
    } catch (err) {
      console.error('Step execution error:', err);
    } finally {
      setActiveTaskRunning(null);
    }
  };

  const isCompleted = mission.status === 'completed';
  const isFailed = mission.status === 'failed';
  const completedCount = mission.completed_tasks || 0;
  const totalCount = mission.total_tasks || (mission.tasks ? mission.tasks.length : 5);

  return (
    <div style={{
      marginTop: '8px',
      marginBottom: '12px',
      background: 'linear-gradient(145deg, #090d16 0%, #0d1527 100%)',
      border: isCompleted ? '1px solid rgba(16, 185, 129, 0.4)' : (isFailed ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(59, 130, 246, 0.4)'),
      borderRadius: '12px',
      padding: '16px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      color: '#f8fafc',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
    }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.2rem' }}>🚀</span>
          <div>
            <div style={{ fontSize: '0.86rem', fontWeight: 800, letterSpacing: '0.5px', textTransform: 'uppercase', color: '#60a5fa' }}>
              Autonomous Mission Control
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              AI-BS & Antigravity Sovereign Unison Engine
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            padding: '4px 10px',
            borderRadius: '12px',
            fontSize: '0.72rem',
            fontWeight: 700,
            background: isCompleted ? 'rgba(16, 185, 129, 0.15)' : (isFailed ? 'rgba(239, 68, 68, 0.15)' : 'rgba(59, 130, 246, 0.15)'),
            color: isCompleted ? '#34d399' : (isFailed ? '#f87171' : '#60a5fa'),
            border: `1px solid ${isCompleted ? 'rgba(16, 185, 129, 0.3)' : (isFailed ? 'rgba(239, 68, 68, 0.3)' : 'rgba(59, 130, 246, 0.3)')}`
          }}>
            {isCompleted ? '✅ COMPLETED' : (isFailed ? '❌ FAILED' : (isRunning ? '⏳ RUNNING' : '📋 PLANNED'))}
          </span>
          {mission.total_duration_ms && (
            <span style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 600 }}>
              ⚡ {mission.total_duration_ms} ms
            </span>
          )}
        </div>
      </div>

      {/* Mission Goal Card */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.6)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: '8px',
        padding: '10px 12px',
        marginBottom: '12px'
      }}>
        <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, marginBottom: '2px' }}>
          🎯 Operational Mission Goal
        </div>
        <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#f1f5f9' }}>
          {mission.goal || 'Autonomous System Inspection & Parity Verification'}
        </div>
      </div>

      {/* 5-Phase Stepper */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', marginBottom: '14px' }}>
        {PHASES.map(p => {
          const taskMatch = (mission.tasks || []).find(t => t.task_id === p.id);
          const pDone = taskMatch?.status === 'completed' || isCompleted;
          const pRunning = activeTaskRunning === p.id || (isRunning && !pDone);

          return (
            <div key={p.id} style={{
              background: pDone ? 'rgba(16, 185, 129, 0.08)' : (pRunning ? 'rgba(168, 85, 247, 0.08)' : 'rgba(255, 255, 255, 0.03)'),
              border: `1px solid ${pDone ? 'rgba(16, 185, 129, 0.3)' : (pRunning ? 'rgba(168, 85, 247, 0.4)' : 'rgba(255, 255, 255, 0.06)')}`,
              borderRadius: '8px',
              padding: '8px 10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.85rem' }}>{p.icon}</span>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: pDone ? '#34d399' : (pRunning ? '#c084fc' : '#64748b') }}>
                  {pDone ? 'DONE' : (pRunning ? 'ACTIVE' : 'QUEUED')}
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', fontWeight: 700, color: pDone ? '#f1f5f9' : '#cbd5e1' }}>
                {p.name.split(':')[0]}
              </div>
              <div style={{ fontSize: '0.66rem', color: '#94a3b8', lineHeight: '1.2' }}>
                {p.desc}
              </div>
            </div>
          );
        })}
      </div>

      {/* Task Checklist */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>
          Execution Sub-Tasks ({completedCount}/{totalCount})
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {(mission.tasks || []).map(t => {
            const isDone = t.status === 'completed';
            const isTaskRunning = activeTaskRunning === t.task_id;
            const isExpanded = expandedTask === t.task_id;

            return (
              <div key={t.task_id} style={{
                background: 'rgba(15, 23, 42, 0.4)',
                border: `1px solid ${isDone ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.05)'}`,
                borderRadius: '6px',
                padding: '8px 10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0 }}>
                    <span style={{ fontSize: '0.85rem' }}>{isDone ? '✅' : (isTaskRunning ? '⏳' : '○')}</span>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#f1f5f9', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {t.title}
                      </div>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>
                        {t.phase}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {t.duration_ms && (
                      <span style={{ fontSize: '0.65rem', color: '#10b981' }}>
                        {t.duration_ms}ms
                      </span>
                    )}
                    {t.result?.output && (
                      <button
                        onClick={() => setExpandedTask(isExpanded ? null : t.task_id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#60a5fa',
                          fontSize: '0.68rem',
                          cursor: 'pointer',
                          padding: '2px 4px'
                        }}
                      >
                        {isExpanded ? '▲ Hide' : '▼ Details'}
                      </button>
                    )}
                    {!isDone && !isCompleted && (
                      <button
                        onClick={() => handleExecuteStep(t.task_id)}
                        disabled={isTaskRunning || isRunning}
                        style={{
                          background: 'rgba(59, 130, 246, 0.2)',
                          border: '1px solid rgba(59, 130, 246, 0.4)',
                          borderRadius: '4px',
                          color: '#60a5fa',
                          fontSize: '0.68rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          cursor: (isTaskRunning || isRunning) ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {isTaskRunning ? 'Running...' : '▶ Step'}
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded Output Details */}
                {isExpanded && t.result?.output && (
                  <pre style={{
                    marginTop: '6px',
                    padding: '6px 8px',
                    background: '#030712',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    color: '#86efac',
                    whiteSpace: 'pre-wrap',
                    maxHeight: '120px',
                    overflowY: 'auto',
                    border: '1px solid rgba(255, 255, 255, 0.05)'
                  }}>
                    {t.result.output}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Control Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '10px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleRunFull}
            disabled={isRunning}
            style={{
              background: isRunning ? '#1e3a8a' : 'linear-gradient(135deg, #2563eb, #1d4ed8)',
              border: '1px solid rgba(59, 130, 246, 0.5)',
              borderRadius: '6px',
              color: '#ffffff',
              fontSize: '0.76rem',
              fontWeight: 700,
              padding: '6px 14px',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 10px rgba(37, 99, 235, 0.3)'
            }}
          >
            {isRunning ? '⏳ Running Full Mission...' : (isCompleted ? '🔄 Re-Run Mission' : '▶ Run Full Mission')}
          </button>
        </div>

        <button
          onClick={() => setShowJson(!showJson)}
          style={{
            background: 'none',
            border: 'none',
            color: '#64748b',
            fontSize: '0.68rem',
            cursor: 'pointer'
          }}
        >
          {showJson ? '▲ Hide Telemetry JSON' : '🔍 Telemetry JSON'}
        </button>
      </div>

      {showJson && (
        <pre style={{
          marginTop: '10px',
          background: '#020617',
          padding: '8px',
          borderRadius: '4px',
          fontSize: '0.68rem',
          color: '#cbd5e1',
          overflowX: 'auto',
          maxHeight: '160px',
          border: '1px solid rgba(255, 255, 255, 0.05)'
        }}>
          {JSON.stringify(mission, null, 2)}
        </pre>
      )}
    </div>
  );
}
