/** @typedef {{projectName: string, job_id: string, contract: string, connectionError?: string, status: string, progress?: number, current_chunk?: number, total_chunks?: number, adaptation_type?: string, book_style?: string, error?: string, previous_summary?: string}} AdaptationJob */
import { useState, useEffect, useRef } from 'react';
import { createAuthenticatedEventSource } from '/src/utils/authenticatedEventSource.js';
import { readAdaptationJob, monitorAdaptation, isAdaptationTerminal, isAdaptationComplete, requestAdaptationAction } from '/src/utils/screenplayAdaptation.js';

/**
 * AdaptationStatusBar.jsx
 * Prominent, real-time AI Adaptation Job Status & Progress Bar.
 * Automatically discovers active jobs, listens to SSE streams, and provides cancel/restart controls.
 */
/** @param {{backendUrl?: string, onSwitchToProject?: (project: string) => void, onRefreshScreenplay?: (project: string) => void}} props */
export default function AdaptationStatusBar({ backendUrl, onSwitchToProject, onRefreshScreenplay }) {
  const baseUrl = backendUrl || 'http://127.0.0.1:8000';
  const [activeJob, setActiveJob] = useState(/** @type {AdaptationJob | null} */ (null));
  const [isDismissed, setIsDismissed] = useState(false);
  const activeJobRef = useRef(/** @type {AdaptationJob | null} */ (null));
  const monitorRef = useRef(/** @type {(() => void) | null} */ (null));
  const monitorKeyRef = useRef('');
  const failedStreamRef = useRef('');
  const actionBusyRef = useRef(false);
  const [isChanging, setIsChanging] = useState(false);
  /** @param {AdaptationJob} value */
  const updateJob = value => { activeJobRef.current = value; setActiveJob(value); };

  /** @param {AdaptationJob} job */
  const connectStream = job => {
    const key = `${job.projectName}:${job.job_id}`;
    if (monitorKeyRef.current === key || failedStreamRef.current === key || isAdaptationTerminal(job.status)) return;
    monitorRef.current?.();
    monitorKeyRef.current = key;
    monitorRef.current = monitorAdaptation({ baseUrl, projectName: job.projectName, jobId: job.job_id,
      eventSourceFactory: createAuthenticatedEventSource,
      onStatus: data => {
        if (activeJobRef.current?.job_id !== job.job_id || activeJobRef.current.projectName !== job.projectName) return;
        updateJob(data);
        if (isAdaptationTerminal(data.status)) monitorKeyRef.current = '';
        if (isAdaptationComplete(data.status)) onRefreshScreenplay?.(job.projectName);
      },
      onError: error => {
        failedStreamRef.current = key;
        monitorKeyRef.current = '';
        const current = activeJobRef.current;
        if (current?.job_id === job.job_id && current.projectName === job.projectName) {
          updateJob({ ...current, connectionError: error instanceof Error ? error.message : 'Progress connection unavailable.' });
        }
      },
    });
  };

  useEffect(() => {
    let mounted = true;
    let polling = false;
    /** @type {AbortController | null} */
    let catalogController = null;
    /** @type {ReturnType<typeof setTimeout> | null} */
    let catalogTimeout = null;
    const checkActiveJobs = async () => {
      if (!mounted || polling || actionBusyRef.current) return;
      polling = true;
      const observed = activeJobRef.current;
      const requestController = new AbortController();
      catalogController = requestController;
      const requestTimeout = setTimeout(() => requestController.abort(), 15000);
      catalogTimeout = requestTimeout;
      try {
        const res = await fetch(`${baseUrl}/api/screenplay/adapt/active-jobs`, { signal: requestController.signal });
        if (!res.ok) throw new Error(`Job status returned HTTP ${res.status}.`);
        const data = await res.json();
        if (!mounted || activeJobRef.current !== observed || actionBusyRef.current) return;
        const jobs = data.jobs;
        if (!jobs || typeof jobs !== 'object' || Array.isArray(jobs)) throw new Error('Job status is invalid.');
        const nextProject = (!observed || isAdaptationTerminal(observed.status))
          ? Object.keys(jobs).find(name => ['queued', 'processing'].includes(jobs[name]?.status)) : undefined;
        if (nextProject) {
          const job = readAdaptationJob(jobs[nextProject], nextProject);
          updateJob(job);
          setIsDismissed(false);
          connectStream(job);
        } else if (observed) {
          const raw = jobs[observed.projectName];
          if (!raw) throw new Error('This job is absent from the returned status catalog. Completion is unverified.');
          const job = readAdaptationJob(raw, observed.projectName, observed.job_id);
          updateJob(job);
          if (isAdaptationTerminal(job.status)) { monitorRef.current?.(); monitorKeyRef.current = ''; }
          else connectStream(job);
        }
      } catch (error) {
        if (mounted && observed && activeJobRef.current === observed) {
          updateJob({ ...observed, connectionError: error instanceof Error ? error.message : 'Job status unavailable.' });
        }
      } finally {
        clearTimeout(requestTimeout);
        if (catalogController === requestController) { catalogController = null; catalogTimeout = null; }
        polling = false;
      }
    };
    void checkActiveJobs();
    const interval = setInterval(checkActiveJobs, 3500);
    return () => {
      mounted = false;
      clearInterval(interval);
      catalogController?.abort();
      if (catalogTimeout !== null) clearTimeout(catalogTimeout);
      monitorRef.current?.();
      monitorKeyRef.current = '';
    };
  }, [baseUrl]);

  /** @param {'cancel' | 'reset'} action */
  const handleAction = async action => {
    const captured = activeJobRef.current;
    if (!captured || actionBusyRef.current) return;
    actionBusyRef.current = true;
    setIsChanging(true);
    try {
      const acknowledged = await requestAdaptationAction(baseUrl, captured, action);
      if (activeJobRef.current?.job_id !== captured.job_id || activeJobRef.current.projectName !== captured.projectName) return;
      monitorRef.current?.();
      monitorKeyRef.current = '';
      updateJob(acknowledged);
    } catch (error) {
      alert(`Adaptation state change not confirmed: ${error instanceof Error ? error.message : String(error)}`);
    } finally { actionBusyRef.current = false; setIsChanging(false); }
  };
  const handleCancel = () => handleAction('cancel');
  const handleReset = () => handleAction('reset');

  if (!activeJob || isDismissed) return null;

  const isProcessing = ['queued', 'processing'].includes(activeJob.status);
  const isComplete = isAdaptationComplete(activeJob.status);
  const isError = ['error', 'failed'].includes(activeJob.status);
  const isCanceled = ['canceled', 'cancelled'].includes(activeJob.status);
  const isStopped = ['interrupted', 'reset', 'not_found'].includes(activeJob.status);
  const progressPct = Math.min(100, Math.max(0, activeJob.progress || 0));

  let statusBg = '#161b22';
  let statusBorder = '#facc15';
  let statusText = '#facc15';
  let badgeLabel = '⚡ PROCESSING ADAPTATION';

  if (activeJob.connectionError) {
    statusBorder = '#f59e0b';
    statusText = '#f59e0b';
    badgeLabel = 'STATUS UNVERIFIED';
  } else if (isStopped) {
    statusBorder = '#9ca3af';
    statusText = '#9ca3af';
    badgeLabel = `ADAPTATION ${activeJob.status.toUpperCase()}`;
  } else if (isComplete) {
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
              disabled={isChanging}
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

          {(isError || isCanceled || isComplete || isStopped) && (
            <button
              onClick={handleReset}
              disabled={isChanging}
              style={{
                background: '#9ca3af22',
                border: '1px solid #9ca3af',
                color: '#9ca3af',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
              title="Release worker ownership; existing files and project names are retained"
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

      {activeJob.connectionError && <div role="status">{activeJob.connectionError} Last observed state: {activeJob.status}.</div>}

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

