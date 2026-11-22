import { useState, useEffect, useMemo } from 'react';
import { chatAuthHeaders } from '/src/utils/chatAuth.js';

/** @typedef {{agent_id: string, role_index: number, name: string, responsibility: string, concrete_deliverable: string, workspace_scope: string, engine_target: string, model_name: string, completion_check_cmd: string[], check_status?: string, metadata?: {nav_tab?: string, domain_title?: string}}} SwarmSpecialist */
/** @typedef {{tier_1_domain?: {title?: string, domain_score?: number, candidate_pool_size?: number}, tier_2_specialist?: {agent_id: string, name?: string, role_index?: number}}} SwarmRoutingResult */
/** @typedef {{agent_id: string, passed: boolean, returncode?: number, duration_sec?: number, command?: string[], status?: string, details?: unknown, error?: string}} SwarmVerificationOutput */
/** @typedef {{job_id: string, verified_pass: boolean, exit_code: number, source_revision?: string, duration_sec?: number, stdout_snippet?: string}} SwarmEvidence */
/** @typedef {{chapter_id: string, title: string, word_count: number, content_sha256?: string}} SwarmChapter */
/** @typedef {{passed: true, data: {record: SwarmChapter, idempotent?: boolean}} | {passed: false, error: string}} SwarmSealStatus */

/** @param {string} url @param {RequestInit} [options] */
async function swarmRequest(url, options = {}) {
  const headers = await chatAuthHeaders(options.headers || {});
  return fetch(url, { ...options, headers });
}

/** @param {unknown} error */
function formatSwarmError(error) {
  if (typeof error === 'string') return error;
  return JSON.stringify(error) || 'The request could not be completed.';
}


/**
 * SpecialistSwarmExplorer: Native-feeling 64-Specialist Subagent Directory & Verification Hub.
 * Connects directly to FastAPI endpoints:
 * - GET  /api/v1/agents/domains
 * - GET  /api/v1/agents/specialists
 * - POST /api/v1/agents/route-hierarchical
 * - POST /api/v1/agents/specialists/{agent_id}/run-gate
 * - GET  /api/v1/agents/specialists/{agent_id}/evidence
 * - POST /api/v1/agents/immutable-scribe/verify
 * - GET  /api/v1/agents/immutable-scribe/chapters
 * - POST /api/v1/agents/immutable-scribe/seal
 */

export default function SpecialistSwarmExplorer({ backendUrl = 'https://api.brettstehouwer.live' }) {
  const [activeTabFilter, setActiveTabFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [specialists, setSpecialists] = useState(/** @type {SwarmSpecialist[]} */ ([]));
  const [, setDomains] = useState({});
  const [tabCounts, setTabCounts] = useState(/** @type {Record<string, number>} */ ({}));
  const [loading, setLoading] = useState(true);
  const [selectedSpecialist, setSelectedSpecialist] = useState(/** @type {SwarmSpecialist | null} */ (null));
  const [testPrompt, setTestPrompt] = useState('');
  const [routingResult, setRoutingResult] = useState(/** @type {SwarmRoutingResult | null} */ (null));
  const [routingLoading, setRoutingLoading] = useState(false);
  const [verifyingId, setVerifyingId] = useState(/** @type {string | null} */ (null));
  const [verificationOutput, setVerificationOutput] = useState(/** @type {SwarmVerificationOutput | null} */ (null));

  // Evidence History State
  const [evidenceList, setEvidenceList] = useState(/** @type {SwarmEvidence[]} */ ([]));
  const [evidenceLoading, setEvidenceLoading] = useState(false);

  // Role 49: Immutable Fire Scribe Workbench State
  const [showScribeWorkbench, setShowScribeWorkbench] = useState(false);
  const [chapterId, setChapterId] = useState('ch02_the_forge');
  const [chapterTitle, setChapterTitle] = useState('Chapter 2: The Forge');
  const [rawText, setRawText] = useState('the fire and the forge stays true without altering a single word');
  const [formattedText, setFormattedText] = useState('### Chapter 2\n- **The Fire, and the Forge** stays true without altering a single word!');
  const [sealingLoading, setSealingLoading] = useState(false);
  const [sealStatus, setSealStatus] = useState(/** @type {SwarmSealStatus | null} */ (null));
  const [sealedChapters, setSealedChapters] = useState(/** @type {SwarmChapter[]} */ ([]));

  const tabs = [
    { key: 'all', label: 'All 64 Roles', count: 64, icon: '⚡' },
    { key: 'chat', label: 'Chat (IDE)', count: tabCounts.chat || 24, icon: '💬' },
    { key: 'project_noco', label: 'NoCo (3D)', count: tabCounts.project_noco || 8, icon: '🏛️' },
    { key: 'video_streaming', label: 'VLC / Media', count: tabCounts.video_streaming || 8, icon: '🎬' },
    { key: 'executive_cockpit', label: 'Cockpit', count: tabCounts.executive_cockpit || 8, icon: '⚡' },
    { key: 'menu', label: 'All Tools', count: tabCounts.menu || 16, icon: '☰' },
  ];

  // Fetch Domains and Specialists
  useEffect(() => {
    let isMounted = true;
    async function loadSwarmData() {
      try {
        setLoading(true);
        const [domRes, specRes] = await Promise.all([
          swarmRequest(`${backendUrl}/api/v1/agents/domains`).catch(() => null),
          swarmRequest(`${backendUrl}/api/v1/agents/specialists?active_only=false`).catch(() => null),
        ]);

        if (domRes && domRes.ok) {
          const domData = await domRes.json();
          if (isMounted) {
            setDomains(domData.domains || []);
            setTabCounts(domData.nav_tab_counts || {});
          }
        }

        if (specRes && specRes.ok) {
          const specData = await specRes.json();
          if (isMounted && specData.specialists) {
            setSpecialists(specData.specialists);
            if (!selectedSpecialist && specData.specialists.length > 0) {
              setSelectedSpecialist(specData.specialists[0]);
            }
          }
        }
      } catch (err) {
        console.warn('Swarm data fetch error:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadSwarmData();
    return () => { isMounted = false; };
  }, [backendUrl]);

  // Fetch Evidence History for Selected Specialist
  useEffect(() => {
    if (!selectedSpecialist) return;
    const selectedAgentId = selectedSpecialist.agent_id;
    let isSubscribed = true;
    async function fetchEvidence() {
      try {
        setEvidenceLoading(true);
        const res = await swarmRequest(`${backendUrl}/api/v1/agents/specialists/${selectedAgentId}/evidence?limit=5`);
        if (res.ok) {
          const data = await res.json();
          if (isSubscribed) setEvidenceList(data.evidence || []);
        } else {
          if (isSubscribed) setEvidenceList([]);
        }
      } catch (e) {
        console.warn('Evidence fetch error:', e);
      } finally {
        if (isSubscribed) setEvidenceLoading(false);
      }
    }
    fetchEvidence();
    return () => { isSubscribed = false; };
  }, [selectedSpecialist, backendUrl]);

  // Fetch Sealed Chapters for Role 49
  useEffect(() => {
    if (!showScribeWorkbench) return;
    let isMounted = true;
    async function fetchChapters() {
      try {
        const res = await swarmRequest(`${backendUrl}/api/v1/agents/immutable-scribe/chapters`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setSealedChapters(data.chapters || []);
        }
      } catch (e) {
        console.warn('Failed to load chapters:', e);
      }
    }
    fetchChapters();
    return () => { isMounted = false; };
  }, [showScribeWorkbench, backendUrl]);

  // Real-time Lexical Parity Analysis for Scribe Workbench
  const scribeParity = useMemo(() => {
    if (!rawText.trim()) return null;
    /** @param {string} t */
    const tokenize = (t) => (t.toLowerCase().match(/[a-z0-9_]+/g) || []);
    const rawTokens = tokenize(rawText);
    const fmtTokens = tokenize(formattedText);
    const rawCount = rawTokens.length;
    const fmtCount = fmtTokens.length;
    const isExact = rawTokens.join(' ') === fmtTokens.join(' ');
    let firstMismatch = null;
    if (!isExact) {
      const maxLen = Math.max(rawCount, fmtCount);
      for (let i = 0; i < maxLen; i++) {
        if (rawTokens[i] !== fmtTokens[i]) {
          firstMismatch = {
            index: i + 1,
            expected: rawTokens[i] || '<End of Raw Text>',
            found: fmtTokens[i] || '<End of Formatted Text>',
          };
          break;
        }
      }
    }
    return { rawCount, fmtCount, isExact, firstMismatch };
  }, [rawText, formattedText]);

  // Filtered List
  const filteredSpecialists = useMemo(() => {
    return specialists.filter((s) => {
      const navTab = (s.metadata || {}).nav_tab || 'chat';
      const matchesTab = activeTabFilter === 'all' || navTab === activeTabFilter;
      if (!matchesTab) return false;

      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.agent_id.toLowerCase().includes(q) ||
        s.responsibility.toLowerCase().includes(q) ||
        s.concrete_deliverable.toLowerCase().includes(q) ||
        String(s.role_index).includes(q)
      );
    });
  }, [specialists, activeTabFilter, searchQuery]);

  // Handle Two-Tier Hierarchical Routing Test
  const handleTestRoute = async () => {
    if (!testPrompt.trim()) return;
    try {
      setRoutingLoading(true);
      setRoutingResult(null);
      const res = await swarmRequest(`${backendUrl}/api/v1/agents/route-hierarchical`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: testPrompt,
          active_nav_tab: activeTabFilter === 'all' ? undefined : activeTabFilter,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setRoutingResult(data);
        if (data.tier_2_specialist) {
          const matched = specialists.find(s => s.agent_id === data.tier_2_specialist.agent_id);
          if (matched) setSelectedSpecialist(matched);
        }
      }
    } catch (e) {
      console.warn('Routing test failed:', e);
    } finally {
      setRoutingLoading(false);
    }
  };

  // Run Real Verification Gate via Backend Endpoint
  /** @param {SwarmSpecialist | null} agent */
  const handleRunVerification = async (agent) => {
    if (!agent) return;
    setVerifyingId(agent.agent_id);
    setVerificationOutput(null);
    try {
      const res = await swarmRequest(`${backendUrl}/api/v1/agents/specialists/${agent.agent_id}/run-gate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority: 1 }),
      });
      if (res.ok) {
        const data = await res.json();
        const r = data.result || {};
        setVerificationOutput({
          agent_id: agent.agent_id,
          passed: !!r.verified_pass,
          status: r.status,
          returncode: r.returncode,
          duration_sec: r.duration_sec,
          command: agent.completion_check_cmd,
          details: r,
        });
        // Refresh evidence list
        const evRes = await swarmRequest(`${backendUrl}/api/v1/agents/specialists/${agent.agent_id}/evidence?limit=5`);
        if (evRes.ok) {
          const evData = await evRes.json();
          setEvidenceList(evData.evidence || []);
        }
      } else {
        const errData = await res.json();
        setVerificationOutput({
          agent_id: agent.agent_id,
          passed: false,
          error: formatSwarmError(errData.detail || 'Verification gate failed'),
        });
      }
    } catch (err) {
      setVerificationOutput({
        agent_id: agent.agent_id,
        passed: false,
        error: String(err),
      });
    } finally {
      setVerifyingId(null);
    }
  };

  // Seal Chapter (Role 49)
  const handleSealChapter = async () => {
    if (!scribeParity?.isExact) return;
    setSealingLoading(true);
    setSealStatus(null);
    try {
      const res = await swarmRequest(`${backendUrl}/api/v1/agents/immutable-scribe/seal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_id: chapterId,
          title: chapterTitle,
          raw_text: rawText,
          formatted_text: formattedText,
          author: 'Brett Adam Stehouwer',
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSealStatus({ passed: true, data });
        // Refresh chapters
        const cRes = await swarmRequest(`${backendUrl}/api/v1/agents/immutable-scribe/chapters`);
        if (cRes.ok) {
          const cData = await cRes.json();
          setSealedChapters(cData.chapters || []);
        }
      } else {
        setSealStatus({ passed: false, error: formatSwarmError(data.detail || 'Sealing rejected by lexical validator') });
      }
    } catch (e) {
      setSealStatus({ passed: false, error: String(e) });
    } finally {
      setSealingLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#0d1117',
      color: '#c9d1d9',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      overflow: 'hidden',
    }}>
      {/* Top Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #30363d',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '8px',
        background: '#161b22',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '1.25rem' }}>🤖</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '0.95rem', color: '#f0f6fc', fontWeight: 700 }}>
              AI-BS 64-Specialist Sovereign Swarm
            </h2>
            <div style={{ fontSize: '0.7rem', color: '#8b949e', marginTop: '2px' }}>
              SQLite WAL Registry (0 VRAM Idle) • 7 Domains • Deterministic Exit-Code Verification
            </div>
          </div>
        </div>

        {/* Global Action: Open Role 49 Scribe Workbench */}
        <button
          onClick={() => setShowScribeWorkbench(!showScribeWorkbench)}
          style={{
            background: showScribeWorkbench ? '#238636' : '#21262d',
            color: '#f0f6fc',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '6px 12px',
            fontSize: '0.74rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <span>🔥</span>
          <span>{showScribeWorkbench ? 'Close Scribe Workbench' : 'Role 49: Fire & Forge Workbench'}</span>
        </button>
      </div>

      {/* Role 49 Scribe Workbench Modal/Drawer */}
      {showScribeWorkbench && (
        <div style={{
          background: '#0f172a',
          borderBottom: '2px solid #f97316',
          padding: '14px 16px',
          maxHeight: '400px',
          overflowY: 'auto',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.1rem' }}>🔥</span>
              <div>
                <strong style={{ color: '#fdba74', fontSize: '0.88rem' }}>Role 49: Immutable Fire Scribe Workbench</strong>
                <span style={{ fontSize: '0.7rem', color: '#94a3b8', marginLeft: '8px' }}>
                  Zero-Tolerance Verbatim Preservation Engine (Rejects 100% of LLM Word Changes)
                </span>
              </div>
            </div>
            <button
              onClick={() => setShowScribeWorkbench(false)}
              style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1rem', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Chapter Slug ID</label>
              <input
                type="text"
                value={chapterId}
                onChange={(e) => setChapterId(e.target.value)}
                style={{ width: '100%', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#f8fafc', padding: '6px 8px', fontSize: '0.74rem', boxSizing: 'border-box' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Chapter Title</label>
              <input
                type="text"
                value={chapterTitle}
                onChange={(e) => setChapterTitle(e.target.value)}
                style={{ width: '100%', background: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#f8fafc', padding: '6px 8px', fontSize: '0.74rem', boxSizing: 'border-box' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'flex', justifyContent: 'space-between' }}>
                <span>Raw Voice Dictation (Canonical Source of Truth)</span>
                <span>{scribeParity?.rawCount || 0} words</span>
              </label>
              <textarea
                rows={4}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Paste raw spoken word transcription..."
                style={{ width: '100%', background: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#e2e8f0', padding: '8px', fontSize: '0.74rem', fontFamily: 'monospace', boxSizing: 'border-box' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'flex', justifyContent: 'space-between' }}>
                <span>Punctuated / Formatted Manuscript</span>
                <span>{scribeParity?.fmtCount || 0} words</span>
              </label>
              <textarea
                rows={4}
                value={formattedText}
                onChange={(e) => setFormattedText(e.target.value)}
                placeholder="Formatted text with markdown, capitalization, punctuation..."
                style={{ width: '100%', background: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#e2e8f0', padding: '8px', fontSize: '0.74rem', fontFamily: 'monospace', boxSizing: 'border-box' }}
              />
            </div>
          </div>

          {/* Lexical Fidelity Banner & Seal Button */}
          <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              {scribeParity ? (
                scribeParity.isExact ? (
                  <span style={{ color: '#4ade80', fontSize: '0.76rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>✅</span> 100% Lexical Parity ({scribeParity.rawCount} Words Exact Match) — Ready to Seal
                  </span>
                ) : (
                  <span style={{ color: '#f87171', fontSize: '0.74rem', fontWeight: 600 }}>
                    ❌ Parity Mismatch at Word #{scribeParity.firstMismatch?.index}: Expected "{scribeParity.firstMismatch?.expected}" but found "{scribeParity.firstMismatch?.found}"
                  </span>
                )
              ) : null}
            </div>

            <button
              onClick={handleSealChapter}
              disabled={sealingLoading || !scribeParity?.isExact}
              style={{
                background: scribeParity?.isExact ? 'linear-gradient(135deg, #ea580c, #c2410c)' : '#334155',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '7px 16px',
                fontSize: '0.76rem',
                fontWeight: 800,
                cursor: scribeParity?.isExact ? 'pointer' : 'not-allowed',
              }}
            >
              {sealingLoading ? 'Saving...' : '🔒 Save Verified Chapter'}
            </button>
          </div>

          {sealStatus && (
            <div style={{ marginTop: '8px', padding: '8px', background: sealStatus.passed ? 'rgba(74, 222, 128, 0.1)' : 'rgba(248, 113, 113, 0.1)', borderRadius: '4px', fontSize: '0.72rem' }}>
              {sealStatus.passed ? (
                <div style={{ color: '#4ade80' }}>
                  Chapter saved: <strong>{sealStatus.data.record.chapter_id}</strong>
                  {sealStatus.data.record.content_sha256 && <> (SHA-256: {sealStatus.data.record.content_sha256.slice(0, 16)}…)</>}
                </div>
              ) : (
                <div style={{ color: '#f87171' }}>{JSON.stringify(sealStatus.error)}</div>
              )}
            </div>
          )}

          {/* Sealed Chapters Vault */}
          {sealedChapters.length > 0 && (
            <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid #1e293b' }}>
              <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: '4px' }}>Sealed Vault Chapters ({sealedChapters.length}):</div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {sealedChapters.map(c => (
                  <div key={c.chapter_id} style={{ background: '#1e293b', padding: '4px 8px', borderRadius: '4px', fontSize: '0.68rem', color: '#fdba74' }}>
                    📖 {c.title} ({c.word_count} words)
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Nav Tabs Bar */}
      <div style={{
        display: 'flex',
        overflowX: 'auto',
        background: '#161b22',
        borderBottom: '1px solid #21262d',
        padding: '4px 8px 0 8px',
        gap: '4px',
      }}>
        {tabs.map((tab) => {
          const isActive = activeTabFilter === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTabFilter(tab.key)}
              style={{
                background: isActive ? '#0d1117' : 'transparent',
                color: isActive ? '#58a6ff' : '#8b949e',
                border: 'none',
                borderTop: isActive ? '2px solid #58a6ff' : '2px solid transparent',
                borderTopLeftRadius: '4px',
                borderTopRightRadius: '4px',
                padding: '8px 12px',
                fontSize: '0.76rem',
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                whiteSpace: 'nowrap',
              }}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              <span style={{
                background: isActive ? '#1f6feb' : '#21262d',
                color: isActive ? '#fff' : '#8b949e',
                borderRadius: '10px',
                padding: '1px 6px',
                fontSize: '0.68rem',
              }}>
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search Filter Strip */}
      <div style={{
        padding: '8px 16px',
        borderBottom: '1px solid #21262d',
        background: '#0d1117',
        display: 'flex',
        gap: '8px',
      }}>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter 64 roles by keyword, target scope, engine, or deliverable..."
          style={{
            flex: 1,
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '6px',
            color: '#c9d1d9',
            padding: '6px 10px',
            fontSize: '0.76rem',
            outline: 'none',
          }}
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            style={{
              background: '#21262d',
              border: '1px solid #30363d',
              color: '#8b949e',
              borderRadius: '6px',
              padding: '0 10px',
              fontSize: '0.74rem',
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Main 2-Column Content Area */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left: Subagent Cards List */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '10px',
          alignContent: 'start',
        }}>
          {loading ? (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '30px', color: '#8b949e' }}>
              Loading 64 sovereign specialists from SQLite WAL...
            </div>
          ) : filteredSpecialists.length === 0 ? (
            <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '30px', color: '#8b949e' }}>
              No specialist agents matched your filter.
            </div>
          ) : (
            filteredSpecialists.map((spec) => {
              const isSelected = selectedSpecialist?.agent_id === spec.agent_id;
              const isVerifying = verifyingId === spec.agent_id;
              const navTab = (spec.metadata || {}).nav_tab || 'chat';

              return (
                <div
                  key={spec.agent_id}
                  onClick={() => setSelectedSpecialist(spec)}
                  style={{
                    background: isSelected ? '#1c2128' : '#161b22',
                    border: isSelected ? '1px solid #58a6ff' : '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    boxShadow: isSelected ? '0 0 8px rgba(88, 166, 255, 0.2)' : 'none',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div>
                    {/* Header: Role Index + Name + Engine Badge */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          background: '#238636',
                          color: '#fff',
                          borderRadius: '4px',
                          padding: '1px 5px',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                        }}>
                          #{spec.role_index}
                        </span>
                        <strong style={{ fontSize: '0.82rem', color: '#f0f6fc' }}>
                          {spec.name}
                        </strong>
                      </div>
                      <span style={{
                        background: '#21262d',
                        color: '#7ee787',
                        borderRadius: '4px',
                        padding: '1px 5px',
                        fontSize: '0.64rem',
                        fontWeight: 600,
                      }}>
                        {spec.engine_target}
                      </span>
                    </div>

                    {/* Scope & Tab Pill */}
                    <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                      <span style={{
                        background: '#1f242c',
                        color: '#58a6ff',
                        borderRadius: '4px',
                        padding: '1px 6px',
                        fontSize: '0.66rem',
                      }}>
                        Tab: {navTab}
                      </span>
                      <span style={{
                        background: '#1f242c',
                        color: '#d29922',
                        borderRadius: '4px',
                        padding: '1px 6px',
                        fontSize: '0.66rem',
                      }}>
                        {spec.workspace_scope}
                      </span>
                    </div>

                    {/* Responsibility */}
                    <div style={{ fontSize: '0.73rem', color: '#8b949e', lineHeight: '1.3', marginBottom: '8px' }}>
                      {spec.responsibility}
                    </div>
                  </div>

                  {/* Concrete Deliverable + Run Gate Button */}
                  <div style={{ paddingTop: '8px', borderTop: '1px solid #21262d', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: '0.68rem', color: '#c9d1d9', maxWidth: '65%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      <span style={{ color: '#8b949e' }}>Output: </span>
                      <span style={{ color: '#38bdf8' }}>{spec.concrete_deliverable}</span>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRunVerification(spec);
                      }}
                      disabled={isVerifying}
                      style={{
                        background: isVerifying ? '#30363d' : '#238636',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '4px 8px',
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        cursor: isVerifying ? 'wait' : 'pointer',
                      }}
                    >
                      {isVerifying ? 'Running...' : 'Run Gate'}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right: Inspection Inspector & Evidence Log */}
        <div style={{
          width: '380px',
          borderLeft: '1px solid #30363d',
          background: '#0d1117',
          padding: '14px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}>
          {selectedSpecialist ? (
            <div>
              {/* Selected Specialist Header Card */}
              <div style={{
                background: '#161b22',
                border: '1px solid #30363d',
                borderRadius: '8px',
                padding: '14px',
                marginBottom: '14px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        background: '#1f6feb',
                        color: '#fff',
                        borderRadius: '4px',
                        padding: '1px 6px',
                        fontSize: '0.68rem',
                        fontWeight: 700,
                      }}>
                        Role #{selectedSpecialist.role_index}
                      </span>
                      <h3 style={{ margin: 0, fontSize: '1.02rem', color: '#f0f6fc' }}>
                        {selectedSpecialist.name}
                      </h3>
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#58a6ff', marginTop: '3px', fontFamily: 'monospace' }}>
                      agent_id: {selectedSpecialist.agent_id}
                    </div>
                  </div>

                  {/* Verification Gate Action */}
                  <button
                    onClick={() => handleRunVerification(selectedSpecialist)}
                    disabled={verifyingId === selectedSpecialist.agent_id || selectedSpecialist.check_status === 'unconfigured_check'}
                    style={{
                      background: 'linear-gradient(135deg, #10b981, #059669)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '7px 12px',
                      fontSize: '0.74rem',
                      fontWeight: 800,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <span>{selectedSpecialist.check_status === 'unconfigured_check' ? 'Check unavailable' : verifyingId === selectedSpecialist.agent_id ? '⏳ Running...' : '▶ Run Gate'}</span>
                  </button>
                </div>

                <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.74rem' }}>
                  <div>
                    <span style={{ color: '#8b949e' }}>Domain: </span>
                    <span style={{ color: '#e6edf3', fontWeight: 600 }}>
                      {(selectedSpecialist.metadata || {}).domain_title || 'Core'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#8b949e' }}>Target Scope: </span>
                    <span style={{ color: '#e6edf3', fontWeight: 600 }}>
                      {selectedSpecialist.workspace_scope}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#8b949e' }}>Engine Target: </span>
                    <span style={{ color: '#e6edf3', fontWeight: 600 }}>
                      {selectedSpecialist.engine_target}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#8b949e' }}>Model Affinity: </span>
                    <span style={{ color: '#e6edf3', fontWeight: 600 }}>
                      {selectedSpecialist.model_name}
                    </span>
                  </div>
                </div>

                {/* Responsibility & Deliverable */}
                <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #21262d' }}>
                  <div style={{ fontSize: '0.74rem', color: '#8b949e' }}>Responsibility:</div>
                  <div style={{ fontSize: '0.78rem', color: '#f0f6fc', marginTop: '2px' }}>
                    {selectedSpecialist.responsibility}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: '#8b949e', marginTop: '6px' }}>Concrete Deliverable:</div>
                  <div style={{ fontSize: '0.78rem', color: '#38bdf8', marginTop: '2px', fontWeight: 600 }}>
                    {selectedSpecialist.concrete_deliverable}
                  </div>
                </div>

                {/* Verification Command */}
                <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #21262d' }}>
                  <div style={{ fontSize: '0.72rem', color: '#8b949e' }}>Deterministic Check Command:</div>
                  <pre style={{
                    background: '#0d1117',
                    padding: '8px',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                    color: '#7ee787',
                    overflowX: 'auto',
                    margin: '4px 0 0 0',
                  }}>
                    {Array.isArray(selectedSpecialist.completion_check_cmd)
                      ? selectedSpecialist.completion_check_cmd.join(' ')
                      : String(selectedSpecialist.completion_check_cmd)}
                  </pre>
                </div>
              </div>

              {/* Verification Output Banner */}
              {verificationOutput && verificationOutput.agent_id === selectedSpecialist.agent_id && (
                <div style={{
                  background: verificationOutput.passed ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                  border: `1px solid ${verificationOutput.passed ? '#10b981' : '#ef4444'}`,
                  borderRadius: '6px',
                  padding: '10px 12px',
                  marginBottom: '14px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontWeight: 700, fontSize: '0.78rem' }}>
                    <span>{verificationOutput.status === 'unconfigured_check' ? '⚠ Verification check unavailable' : verificationOutput.passed ? '✅ Verification Gate Passed' : '❌ Verification Gate Failed'}</span>
                    {verificationOutput.duration_sec !== undefined && (
                      <span style={{ fontSize: '0.7rem', color: '#8b949e' }}>{verificationOutput.duration_sec.toFixed(3)}s</span>
                    )}
                  </div>
                  <pre style={{ fontSize: '0.7rem', color: '#c9d1d9', margin: '6px 0 0 0', whiteSpace: 'pre-wrap' }}>
                    {JSON.stringify(verificationOutput.details || verificationOutput.error, null, 2)}
                  </pre>
                </div>
              )}

              {/* SQLite Historical Evidence Log */}
              <div style={{
                background: '#161b22',
                border: '1px solid #30363d',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '14px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.82rem', color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>📋</span>
                    <span>SQLite Job Evidence Vault</span>
                  </div>
                  <span style={{ fontSize: '0.68rem', color: '#8b949e' }}>
                    {evidenceLoading ? 'Loading...' : `${evidenceList.length} Runs`}
                  </span>
                </div>

                {evidenceList.length === 0 ? (
                  <div style={{ fontSize: '0.72rem', color: '#8b949e', textAlign: 'center', padding: '10px' }}>
                    No historical evidence recorded yet. Click "Run Gate" to execute.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {evidenceList.map((ev) => (
                      <div
                        key={ev.job_id}
                        style={{
                          background: '#0d1117',
                          border: `1px solid ${ev.verified_pass ? '#238636' : '#da3633'}`,
                          borderRadius: '4px',
                          padding: '6px 8px',
                          fontSize: '0.7rem',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ color: '#58a6ff', fontWeight: 700 }}>{ev.job_id}</span>
                          <span style={{
                            color: ev.verified_pass ? '#7ee787' : '#f85149',
                            fontWeight: 700,
                          }}>
                            {ev.verified_pass ? 'PASSED (RC 0)' : `FAILED (RC ${ev.exit_code})`}
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e', fontSize: '0.66rem', marginTop: '2px' }}>
                          <span>Git: {ev.source_revision || 'HEAD'}</span>
                          <span>{ev.duration_sec ? `${ev.duration_sec.toFixed(3)}s` : '—'}</span>
                        </div>
                        {ev.stdout_snippet && (
                          <div style={{ marginTop: '4px', color: '#7ee787', fontFamily: 'monospace', fontSize: '0.64rem', whiteSpace: 'pre-wrap', maxHeight: '40px', overflowY: 'hidden' }}>
                            {ev.stdout_snippet.trim()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Two-Tier Routing Interactive Tester */}
              <div style={{
                background: '#161b22',
                border: '1px solid #30363d',
                borderRadius: '8px',
                padding: '14px',
              }}>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#f0f6fc', marginBottom: '4px' }}>
                  🧭 Two-Tier Hierarchical Router Sandbox
                </div>
                <div style={{ fontSize: '0.72rem', color: '#8b949e', marginBottom: '8px' }}>
                  Tests Tier 1 domain matching followed by Tier 2 specialist scoring to preserve token budget.
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    value={testPrompt}
                    onChange={(e) => setTestPrompt(e.target.value)}
                    placeholder="Enter task prompt (e.g. 'Calibrate nutrient dosing EC pH curves')..."
                    style={{
                      flex: 1,
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: '6px',
                      color: '#f0f6fc',
                      padding: '7px 10px',
                      fontSize: '0.76rem',
                      outline: 'none',
                    }}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleTestRoute(); }}
                  />
                  <button
                    onClick={handleTestRoute}
                    disabled={routingLoading || !testPrompt.trim()}
                    style={{
                      background: '#238636',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '7px 12px',
                      fontSize: '0.74rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {routingLoading ? 'Routing...' : 'Route Prompt'}
                  </button>
                </div>

                {routingResult && (
                  <div style={{ marginTop: '10px', background: '#0d1117', padding: '10px', borderRadius: '6px', border: '1px solid #30363d' }}>
                    <div style={{ fontSize: '0.72rem', color: '#38bdf8', fontWeight: 700 }}>
                      Tier 1 Domain: {routingResult.tier_1_domain?.title} (Score: {routingResult.tier_1_domain?.domain_score})
                    </div>
                    <div style={{ fontSize: '0.76rem', color: '#7ee787', fontWeight: 800, marginTop: '2px' }}>
                      Tier 2 Selected Specialist: {routingResult.tier_2_specialist?.name} (#{routingResult.tier_2_specialist?.role_index})
                    </div>
                    <div style={{ fontSize: '0.68rem', color: '#8b949e', marginTop: '4px' }}>
                      Candidate pool reduced from 64 to {routingResult.tier_1_domain?.candidate_pool_size || 8} subagents.
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#8b949e', marginTop: '40px' }}>
              Select a specialist from the left to inspect its contract.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
