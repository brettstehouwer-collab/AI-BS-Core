import React, { useState, useEffect, useRef } from 'react';

/**
 * AdaptationStatusBar.jsx
 * Prominent, real-time AI Adaptation Job Status & Progress Bar.
 * Automatically discovers active jobs, listens to SSE streams, and provides cancel/restart controls.
 */
export default function AdaptationStatusBar({ backendUrl, onSwitchToProject, onRefreshScreenplay }) {
  const baseUrl = backendUrl || 'http://127.0.0.1:8000';
  const [activeJob, setActiveJob] = useState(null);
  const [isDismissed, setIsDismissed] = useState(false);
  const eventSourceRef = useRef(null);

  // Poll for active jobs on mount and when not connected to SSE
  useEffect(() => {
    let isMounted = true;

    const checkActiveJobs = async () => {
      try {
        const res = await fetch(`${baseUrl}/api/screenplay/adapt/active-jobs`);
        if (!res.ok) return;
        const data = await res.json();
        const jobs = data.jobs || {};
        
        // Find first processing or recently modified job
        const processingProject = Object.keys(jobs).find(
          (k) => jobs[k] && jobs[k].status === 'processing'
        );

        if (processingProject && isMounted) {
          const jobData = { projectName: processingProject, ...jobs[processingProject] };
          setActiveJob(jobData);
          setIsDismissed(false);
          connectStream(processingProject);
        } else if (!processingProject && isMounted) {
          // If previously active job finished or no active jobs
          if (activeJob && activeJob.status === 'processing') {
            setActiveJob((prev) => (prev ? { ...prev, status: 'complete', progress: 100 } : null));
            setTimeout(() => {
              if (isMounted) setActiveJob(null);
            }, 6000);
          }
        }
      } catch (err) {
        // Backend offline or polling error
      }
    };

    checkActiveJobs();
    const interval = setInterval(checkActiveJobs, 3500);

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [baseUrl]);

  const connectStream = (projectName) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const es = new EventSource(`${baseUrl}/api/screenplay/adapt/stream?project_name=${encodeURIComponent(projectName)}`);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && data.status && data.status !== 'not_found') {
            setActiveJob({ projectName, ...data });

            if (onRefreshScreenplay && data.status === 'processing') {
              onRefreshScreenplay(projectName);
            }

            if (data.status === 'complete' || data.status === 'error' || data.status === 'canceled') {
              es.close();
              if (onRefreshScreenplay) {
                onRefreshScreenplay(projectName);
              }
              if (data.status === 'complete') {
                setTimeout(() => setActiveJob(null), 8000);
              }
            }
          }
        } catch (e) {
          console.error("Failed to parse SSE data:", e);
        }
      };

      es.onerror = () => {
        es.close();
      };
    } catch (e) {
      console.error("SSE Connection error:", e);
    }
  };

  const handleCancel = async () => {
    if (!activeJob) return;
    try {
      await fetch(`${baseUrl}/api/screenplay/adapt/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: activeJob.projectName }),
      });
      setActiveJob((prev) => (prev ? { ...prev, status: 'canceled', error: 'Canceled by user' } : null));
      if (eventSourceRef.current) eventSourceRef.current.close();
      setTimeout(() => setActiveJob(null), 3000);
    } catch (err) {
      alert(`Failed to cancel: ${err.message}`);
    }
  };

  const handleReset = async () => {
    if (!activeJob) return;
    try {
      await fetch(`${baseUrl}/api/screenplay/adapt/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: activeJob.projectName }),
      });
      setActiveJob(null);
      if (eventSourceRef.current) eventSourceRef.current.close();
      alert(`Reset adaptation state for "${activeJob.projectName}". You can now start a fresh adaptation.`);
    } catch (err) {
      alert(`Failed to reset: ${err.message}`);
    }
  };

  if (!activeJob || isDismissed) return null;

  const isProcessing = activeJob.status === 'processing';
  const isComplete = activeJob.status === 'complete';
  const isError = activeJob.status === 'error';
  const isCanceled = activeJob.status === 'canceled';
  const progressPct = Math.min(100, Math.max(0, activeJob.progress || 0));

  let statusBg = '#161b22';
  let statusBorder = '#facc15';
  let statusText = '#facc15';
  let badgeLabel = '⚡ PROCESSING ADAPTATION';

  if (isComplete) {
    statusBorder = '#22c55e';
    statusText = '#22c55e';
    badgeLabel = '✓ ADAPTATION COMPLETE';
  } else if (isError) {
    statusBorder = '#ef4444';
    statusText = '#ef4444';
    badgeLabel = '✗ ADAPTATION FAILED';
  } else if (isCanceled) {
    statusBorder = '#9ca3af';
    statusText = '#9ca3af';
    badgeLabel = '⏹️ ADAPTATION CANCELED';
  }

  return (
    <div
      style={{
        background: statusBg,
        border: `1px solid ${statusBorder}66`,
        borderLeft: `4px solid ${statusBorder}`,
        boxShadow: `0 4px 20px rgba(0, 0, 0, 0.4), 0 0 12px ${statusBorder}22`,
        padding: '10px 16px',
        margin: '8px 12px',
        borderRadius: '8px',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        zIndex: 100,
        animation: 'fadeIn 0.3s ease-in-out',
        position: 'relative'
      }}
    >
      {/* Top Header Row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span
            style={{
              background: `${statusBorder}22`,
              color: statusText,
              border: `1px solid ${statusBorder}44`,
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '0.72rem',
              fontWeight: 'bold',
              letterSpacing: '0.5px'
            }}
          >
            {badgeLabel}
          </span>

          <span style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.88rem' }}>
            🎬 {activeJob.projectName}
          </span>

          {activeJob.adaptation_type && (
            <span style={{ background: '#38bdf822', color: '#38bdf8', padding: '1px 6px', borderRadius: '3px', fontSize: '0.7rem', border: '1px solid #38bdf844' }}>
              {activeJob.adaptation_type}
            </span>
          )}

          {activeJob.book_style && (
            <span style={{ background: '#f59e0b22', color: '#f59e0b', padding: '1px 6px', borderRadius: '3px', fontSize: '0.7rem', border: '1px solid #f59e0b44' }}>
              {activeJob.book_style}
            </span>
          )}
        </div>

        {/* Right Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {onSwitchToProject && (
            <button
              onClick={() => onSwitchToProject(activeJob.projectName)}
              style={{
                background: '#38bdf822',
                border: '1px solid #38bdf8',
                color: '#38bdf8',
                padding: '3px 10px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
              title="Open screenplay editor for this project"
            >
              🎬 Open in Editor
            </button>
          )}

          {isProcessing && (
            <button
              onClick={handleCancel}
              style={{
                background: '#ef444422',
                border: '1px solid #ef4444',
                color: '#ef4444',
                padding: '3px 10px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
              title="Stop ongoing adaptation"
            >
              ⏹️ Cancel Job
            </button>
          )}

          {(isError || isCanceled || isComplete) && (
            <button
              onClick={handleReset}
              style={{
                background: '#9ca3af22',
                border: '1px solid #9ca3af',
                color: '#9ca3af',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
              title="Clear job state"
            >
              🔄 Reset
            </button>
          )}

          <button
            onClick={() => setIsDismissed(true)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#6b7280',
              cursor: 'pointer',
              fontSize: '0.9rem',
              padding: '2px 4px'
            }}
            title="Dismiss status bar"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Progress Bar Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div
          style={{
            flex: 1,
            height: '8px',
            background: '#111827',
            borderRadius: '4px',
            overflow: 'hidden',
            border: '1px solid #374151'
          }}
        >
          <div
            style={{
              width: `${progressPct}%`,
              height: '100%',
              background: isComplete ? '#22c55e' : isError ? '#ef4444' : 'linear-gradient(90deg, #facc15 0%, #38bdf8 100%)',
              transition: 'width 0.4s ease-in-out',
              boxShadow: isProcessing ? '0 0 8px #facc1588' : 'none'
            }}
          />
        </div>

        <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: statusText, minWidth: '40px', textAlign: 'right' }}>
          {progressPct}%
        </span>
      </div>

      {/* Details Row: Chunk progress & status message */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#9ca3af' }}>
        <div>
          {isProcessing && (
            <span>
              Chunk <strong>{activeJob.current_chunk !== undefined ? activeJob.current_chunk + 1 : 1}</strong> of <strong>{activeJob.total_chunks || 1}</strong> • Converting prose into Hollywood scene headings, parentheticals, and dialogue...
            </span>
          )}
          {isComplete && <span style={{ color: '#4ade80' }}>Screenplay adaptation finished! All chunks synthesized to industry spec.</span>}
          {isError && <span style={{ color: '#f87171' }}>Error: {activeJob.error || 'Adaptation encountered an issue.'}</span>}
          {isCanceled && <span>Job was canceled. Click Reset to start over.</span>}
        </div>

        {activeJob.previous_summary && isProcessing && (
          <span style={{ fontStyle: 'italic', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            Context: {activeJob.previous_summary}
          </span>
        )}
      </div>
    </div>
  );
}
