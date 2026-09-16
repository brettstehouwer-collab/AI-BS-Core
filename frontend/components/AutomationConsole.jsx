import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  Folder,
  Play,
  RefreshCcw,
  ShieldCheck,
  StopCircle,
  TerminalSquare,
  XCircle,
} from 'lucide-react';

const ACTION_TEMPLATES = {
  list_directory: { path: 'C:\\AI-BS' },
  read_file: { path: 'C:\\AI-BS\\frontend\\package.json' },
  run_python_script: { script: 'C:\\AI-BS\\backend\\AI_BS_Backend.py', args: ['--help'] },
  git_status: { repo_path: 'C:\\AI-BS' },
  process_list: {},
};

const ACTION_OPTIONS = Object.keys(ACTION_TEMPLATES);

function formatStatus(status) {
  return (status || 'unknown').replace(/_/g, ' ').toUpperCase();
}

function getStatusTone(status) {
  switch (status) {
    case 'queued':
      return { bg: 'rgba(96, 165, 250, 0.14)', color: '#7dd3fc', border: '1px solid rgba(125, 211, 252, 0.5)' };
    case 'running':
      return { bg: 'rgba(34, 197, 94, 0.12)', color: '#86efac', border: '1px solid rgba(134, 239, 172, 0.45)' };
    case 'completed':
      return { bg: 'rgba(34, 197, 94, 0.16)', color: '#bbf7d0', border: '1px solid rgba(187, 247, 208, 0.5)' };
    case 'failed':
    case 'timed_out':
      return { bg: 'rgba(248, 113, 113, 0.12)', color: '#fca5a5', border: '1px solid rgba(252, 165, 165, 0.45)' };
    case 'canceled':
      return { bg: 'rgba(251, 191, 36, 0.10)', color: '#fcd34d', border: '1px solid rgba(252, 211, 77, 0.45)' };
    default:
      return { bg: 'rgba(148, 163, 184, 0.08)', color: '#cbd5e1', border: '1px solid rgba(148, 163, 184, 0.35)' };
  }
}

export default function AutomationConsole({ backendUrl = 'http://127.0.0.1:8000' }) {
  const isElectron = typeof window !== 'undefined' && !!window.aibsAutomation;
  const currentUserEmail = (() => {
    try {
      const cached = JSON.parse(localStorage.getItem('aibs_cached_user') || '{}');
      return cached.email || '';
    } catch {
      return '';
    }
  })();
  const [jobs, setJobs] = useState([]);
  const [action, setAction] = useState('list_directory');
  const [cwd, setCwd] = useState('C:\\AI-BS');
  const [timeout, setTimeout] = useState(30);
  const [sandbox, setSandbox] = useState(true);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [draft, setDraft] = useState(JSON.stringify(ACTION_TEMPLATES.list_directory, null, 2));
  const [selectedJobId, setSelectedJobId] = useState(null);

  const activeJobIds = useMemo(() => jobs.filter(job => ['queued', 'running'].includes(job.status)).map(job => job.id), [jobs]);

  async function runSmokeTest() {
    try {
      setRunning(true);
      setError('');
      const payload = {
        action: 'list_directory',
        parameters: { path: cwd || 'C:\\AI-BS' },
        cwd: cwd || 'C:\\AI-BS',
        timeout: 30,
        sandbox: true,
        user_email: currentUserEmail,
      };

      let response;
      if (isElectron) {
        response = await window.aibsAutomation.runJob(payload);
      } else {
        response = await requestJson('/api/v1/jobs', {
          method: 'POST',
          headers: currentUserEmail ? { 'x-local-user-email': currentUserEmail } : {},
          body: JSON.stringify(payload),
        });
      }

      setSelectedJobId(response.id);
      await listJobs();
      setRunning(false);
    } catch (err) {
      setRunning(false);
      setError(err.message || 'Smoke test failed.');
    }
  }

  async function requestJson(path, options = {}) {
    const headers = {
      ...(options.headers || {}),
      ...(currentUserEmail ? { 'x-local-user-email': currentUserEmail } : {}),
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    };

    const response = await fetch(`${backendUrl}${path}`, {
      ...options,
      headers,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || payload.error || 'Automation request failed');
    }
    return payload;
  }

  async function listJobs() {
    try {
      let payload;
      if (isElectron) {
        payload = await window.aibsAutomation.listJobs();
      } else {
        payload = await requestJson('/api/v1/jobs');
      }
      const nextJobs = Array.isArray(payload.jobs) ? payload.jobs : [];
      setJobs(nextJobs);
      if (!selectedJobId && nextJobs.length) {
        setSelectedJobId(nextJobs[0].id);
      }
      return nextJobs;
    } catch (err) {
      setError(err.message || 'Failed to load automation jobs.');
      return [];
    }
  }

  useEffect(() => {
    listJobs();
  }, []);

  useEffect(() => {
    if (!activeJobIds.length) return undefined;
    const timer = setInterval(() => {
      listJobs();
    }, 2000);
    return () => clearInterval(timer);
  }, [activeJobIds.join(',')]);

  const selectedJob = jobs.find(job => job.id === selectedJobId) || jobs[0] || null;

  function updateActionTemplate(nextAction) {
    setAction(nextAction);
    setDraft(JSON.stringify(ACTION_TEMPLATES[nextAction] || {}, null, 2));
  }

  async function handleRunJob() {
    try {
      setRunning(true);
      setError('');
      const parameters = JSON.parse(draft || '{}');
      const body = {
        action,
        parameters,
        cwd: cwd || undefined,
        timeout: Number(timeout) || 30,
        sandbox,
        user_email: currentUserEmail,
      };

      let response;
      if (isElectron) {
        response = await window.aibsAutomation.runJob(body);
      } else {
        response = await requestJson('/api/v1/jobs', {
          method: 'POST',
          body: JSON.stringify(body),
        });
      }

      setSelectedJobId(response.id);
      await listJobs();
      setRunning(false);
    } catch (err) {
      setRunning(false);
      setError(err.message || 'Unable to create automation job.');
    }
  }

  async function handleCancel(jobId) {
    try {
      if (isElectron) {
        await window.aibsAutomation.cancelJob(jobId);
      } else {
        await requestJson(`/api/v1/jobs/${jobId}/cancel`, { method: 'POST' });
      }
      await listJobs();
    } catch (err) {
      setError(err.message || 'Cancel request failed.');
    }
  }

  return (
    <div style={{ background: '#0d1117', color: '#f0f6fc', minHeight: '100%', padding: 24 }}>
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(96, 165, 250, 0.16)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#7dd3fc' }}>
              <TerminalSquare size={22} />
            </div>
            <div>
              <div style={{ fontSize: 12, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#8b949e' }}>Trusted Local Automation</div>
              <h2 style={{ margin: 0, fontSize: 28, fontWeight: 700 }}>Automation Console</h2>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <button
              onClick={runSmokeTest}
              disabled={running}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                background: '#238636',
                color: '#f0f6fc',
                border: '1px solid rgba(34, 197, 94, 0.5)',
                borderRadius: 10,
                padding: '10px 14px',
                cursor: running ? 'not-allowed' : 'pointer',
                fontWeight: 700,
              }}
            >
              <Play size={16} />
              Run Safe Smoke Test
            </button>
            <button
              onClick={() => listJobs()}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                background: '#21262d',
                color: '#f0f6fc',
                border: '1px solid #30363d',
                borderRadius: 10,
                padding: '10px 14px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              <RefreshCcw size={16} />
              Refresh Jobs
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 18, alignItems: 'stretch' }}>
          <div style={{ background: '#111827', border: '1px solid #30363d', borderRadius: 16, padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <ShieldCheck size={18} color="#34d399" />
              <strong style={{ fontSize: 16 }}>Allowed action runner</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
              <label style={{ display: 'grid', gap: 6 }}>
                <span style={{ color: '#8b949e', fontSize: 12 }}>Action</span>
                <select value={action} onChange={(e) => updateActionTemplate(e.target.value)} style={{ background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: 10, padding: '10px 12px' }}>
                  {ACTION_OPTIONS.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>

              <label style={{ display: 'grid', gap: 6 }}>
                <span style={{ color: '#8b949e', fontSize: 12 }}>Working directory</span>
                <input value={cwd} onChange={(e) => setCwd(e.target.value)} style={{ background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: 10, padding: '10px 12px' }} />
              </label>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, marginBottom: 12 }}>
              <label style={{ display: 'grid', gap: 6 }}>
                <span style={{ color: '#8b949e', fontSize: 12 }}>Timeout (seconds)</span>
                <input type="number" min={1} max={600} value={timeout} onChange={(e) => setTimeout(Number(e.target.value) || 30)} style={{ background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: 10, padding: '10px 12px' }} />
              </label>

              <div style={{ display: 'grid', gap: 6 }}>
                <span style={{ color: '#8b949e', fontSize: 12 }}>Execution mode</span>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#0d1117', border: '1px solid #30363d', borderRadius: 10, padding: '10px 12px', height: 44 }}>
                  <input type="checkbox" checked={sandbox} onChange={(e) => setSandbox(e.target.checked)} />
                  <span>Sandboxed</span>
                </label>
              </div>

              <button
                onClick={handleRunJob}
                disabled={running}
                style={{
                  alignSelf: 'end',
                  background: running ? '#1f2937' : '#238636',
                  color: '#f0f6fc',
                  border: 'none',
                  borderRadius: 10,
                  padding: '10px 16px',
                  cursor: running ? 'not-allowed' : 'pointer',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <Play size={16} />
                {running ? 'Submitting...' : 'Run Job'}
              </button>
            </div>

            <label style={{ display: 'grid', gap: 6 }}>
              <span style={{ color: '#8b949e', fontSize: 12 }}>Parameters (JSON object)</span>
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={14} spellCheck={false} style={{ width: '100%', background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: 12, padding: 12, resize: 'vertical', fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 13 }} />
            </label>

            {error && (
              <div style={{ marginTop: 12, background: 'rgba(248, 113, 113, 0.08)', border: '1px solid rgba(248, 113, 113, 0.35)', color: '#fca5a5', borderRadius: 10, padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertTriangle size={16} />
                {error}
              </div>
            )}
          </div>

          <div style={{ background: '#111827', border: '1px solid #30363d', borderRadius: 16, padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <Activity size={18} color="#60a5fa" />
              <strong style={{ fontSize: 16 }}>Queue status</strong>
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #21262d', paddingBottom: 8 }}>
                <span style={{ color: '#8b949e' }}>Queued</span>
                <strong>{jobs.filter(job => job.status === 'queued').length}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #21262d', paddingBottom: 8 }}>
                <span style={{ color: '#8b949e' }}>Running</span>
                <strong>{jobs.filter(job => job.status === 'running').length}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #21262d', paddingBottom: 8 }}>
                <span style={{ color: '#8b949e' }}>Completed</span>
                <strong>{jobs.filter(job => job.status === 'completed').length}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#8b949e' }}>Failed</span>
                <strong>{jobs.filter(job => ['failed', 'timed_out', 'canceled'].includes(job.status)).length}</strong>
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 20, background: '#111827', border: '1px solid #30363d', borderRadius: 16, padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <FileText size={18} color="#cbd5e1" />
              <strong style={{ fontSize: 16 }}>Recent jobs</strong>
            </div>
          </div>

          {jobs.length === 0 ? (
            <div style={{ color: '#8b949e', padding: '18px 0' }}>No local automation jobs yet.</div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {jobs.map(job => {
                const tone = getStatusTone(job.status);
                const isSelected = selectedJob?.id === job.id;
                return (
                  <div key={job.id} style={{ border: isSelected ? '1px solid #58a6ff' : '1px solid #30363d', borderRadius: 12, background: '#0d1117', overflow: 'hidden' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: 12, borderBottom: '1px solid #21262d' }}>
                      <button onClick={() => setSelectedJobId(job.id)} style={{ background: 'transparent', border: 'none', color: '#f0f6fc', fontWeight: 700, textAlign: 'left', cursor: 'pointer', flex: 1 }}>
                        {job.action}
                      </button>
                      <span style={{ ...tone, borderRadius: 999, padding: '4px 10px', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>
                        {formatStatus(job.status)}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, padding: 12, alignItems: 'center' }}>
                      <div style={{ fontSize: 12, color: '#8b949e', display: 'grid', gap: 4 }}>
                        <div><strong style={{ color: '#c9d1d9' }}>ID:</strong> {job.id}</div>
                        <div><strong style={{ color: '#c9d1d9' }}>Created:</strong> {job.created_at}</div>
                        <div><strong style={{ color: '#c9d1d9' }}>CWD:</strong> {job.cwd || 'n/a'}</div>
                      </div>

                      {['queued', 'running'].includes(job.status) && (
                        <button
                          onClick={() => handleCancel(job.id)}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#7c2d12', color: '#fff7ed', border: 'none', borderRadius: 10, padding: '8px 12px', fontWeight: 700, cursor: 'pointer' }}
                        >
                          <StopCircle size={16} />
                          Cancel
                        </button>
                      )}
                    </div>

                    {selectedJob?.id === job.id && (
                      <div style={{ padding: '0 12px 12px' }}>
                        <div style={{ background: '#0b1220', border: '1px solid #21262d', borderRadius: 12, padding: 12, display: 'grid', gap: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#a5b4fc' }}>
                            <TerminalSquare size={16} />
                            Command
                          </div>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 12, color: '#e2e8f0', overflowX: 'auto' }}>
                            {job.command && job.command.length ? job.command.join(' ') : 'Command not available yet.'}
                          </pre>

                          {job.stdout && (
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#86efac', marginBottom: 6 }}>
                                <CheckCircle2 size={16} />
                                Stdout
                              </div>
                              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 12, color: '#d1fae5' }}>{job.stdout}</pre>
                            </div>
                          )}

                          {job.stderr && (
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#fca5a5', marginBottom: 6 }}>
                                <XCircle size={16} />
                                Stderr
                              </div>
                              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 12, color: '#fecaca' }}>{job.stderr}</pre>
                            </div>
                          )}

                          {(job.exit_code !== null && typeof job.exit_code !== 'undefined') && (
                            <div style={{ color: '#cbd5e1', fontSize: 12 }}>
                              <strong>Exit code:</strong> {job.exit_code}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
