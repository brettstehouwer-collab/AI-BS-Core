import { useState, useEffect, useRef } from "react";
import { auth } from '/src/firebase.js';
import { onAuthStateChanged } from 'firebase/auth';

/** @param {Response} response */
async function readReply(response) {
  const data = await response.json();
  if (!response.ok) throw new Error(data?.detail?.message || data?.detail || data?.message || `Request failed (${response.status}).`);
  return data;
}

/** @param {any} receipt */
function verifiedReceipt(receipt) {
  return receipt?.schema === 'aibs.project_rag_snapshot.v2' && receipt.complete === true
    && /^[a-f0-9]{64}$/.test(receipt.snapshot_sha256) && Array.isArray(receipt.sources);
}

/** @param {import('react').ComponentProps<typeof ScriptAssistantSession>} props */
export default function ScriptAssistantDrawer( props) {
  // Each project owns a separate mounted session. Pending results remain with
  // their original session when a project switch unmounts it.
  const [identity, setIdentity] = useState(auth.currentUser?.uid || 'signed-out');
  useEffect(() => onAuthStateChanged(auth, user => setIdentity(user?.uid || 'signed-out')), []);
  return <ScriptAssistantSession key={JSON.stringify([identity, props.backendUrl || '', props.projectName || 'Default Project'])} {...props} />;
}

/** @param {{"projectName"?: string, "isOpen"?: boolean, "onClose"?: () => void, "onInsertScript"?: (arg0: string) => void, "backendUrl"?: string}} props */
function ScriptAssistantSession({
  projectName = 'Default Project',
  isOpen = false,
  onClose,
  onInsertScript,
  backendUrl = ''
}) {
  const [messages, setMessages] = useState(/** @type {Array<{id: string, role: string, content: string, sources?: Array<{type?: string, label?: string, excerpt?: string, source_revision?: string, chunk_sha256?: string, source_file?: string}>, canInsert?: boolean, coverage?: string}>} */ ([
    {
      id: 'welcome',
      role: 'assistant',
      content: `👋 **Script & Memoir Assistant for *${projectName}*.**\n\nQueries use checked excerpts from this owner's current saved project. Only a bounded selection enters the model; replies can still be mistaken.\n\nSync after saving changes, review source revisions and missing coverage, then decide whether to insert a suggestion.`,
      sources: []
    }
  ]));
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState(/** @type {{status: string, total_docs: number, receipt?: any}} */ ({ status: 'not_checked', total_docs: 0 }));
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');
  const messagesEndRef = useRef(/** @type {HTMLDivElement | null} */ (null));
  const live = useRef(true);
  const requests = useRef(new Set(/** @type {AbortController[]} */ ([])));
  useEffect(() => {
    live.current = true;
    return () => { live.current = false; requests.current.forEach(controller => controller.abort()); };
  }, []);

  const fetchStats = async () => {
    const controller = new AbortController(); requests.current.add(controller);
    try {
      const data = await readReply(await fetch(`${backendUrl}/api/screenwriting/project-assistant/stats?project_name=${encodeURIComponent(projectName)}`, { signal: controller.signal }));
      if (live.current) setStats({ ...data, status: data.status === 'success' && verifiedReceipt(data.receipt) ? 'success' : data.status === 'success' ? 'unverified' : data.status, total_docs: verifiedReceipt(data.receipt) ? data.total_docs : 0 });
    } catch (err) {
      if (live.current) { setStats({ status: 'unavailable', total_docs: 0 }); setSyncMessage(`❌ Index status: ${err instanceof Error ? err.message : String(err)}`); }
    } finally { requests.current.delete(controller); }
  };

  useEffect(() => {
    if (isOpen && projectName) {
      fetchStats();
    }
  }, [isOpen, projectName]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSync = async () => {
    const controller = new AbortController(); requests.current.add(controller);
    setIsSyncing(true);
    setSyncMessage('Checking and indexing the current saved sources...');
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/project-assistant/sync`, {
        method: 'POST',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: projectName })
      });
      const data = await readReply(res);
      if (!live.current) return;
      if (data.status === 'success' && verifiedReceipt(data.receipt)) {
        setSyncMessage(`✅ Verified ${data.indexed_docs} source chunks at ${data.receipt.snapshot_sha256.slice(0, 12)}.`);
        await fetchStats();
      } else {
        setStats({ status: data.status || 'unverified', total_docs: 0 });
        setSyncMessage(`❌ ${data.message || (data.status === 'no_source' ? 'No saved sources were found; nothing was indexed.' : 'Synchronization has no verified receipt.')}`);
      }
    } catch (err) {
      if (live.current) setSyncMessage(`❌ Sync failed: ${(err instanceof Error ? err.message : String(err))}`);
    } finally {
      requests.current.delete(controller);
      if (live.current) setIsSyncing(false);
    }
  };

  /** @param {string | null} [textToSend] */
  const handleSendMessage = async (textToSend = null) => {
    const query = (textToSend || inputValue).trim();
    if (!query || isLoading) return;

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query
    };

    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInputValue('');
    setIsLoading(true);
    const controller = new AbortController(); requests.current.add(controller);

    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/project-assistant/chat`, {
        method: 'POST',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: projectName,
          message: query,
          model: 'stehouwer_dolphin:latest'
        })
      });
      const data = await readReply(res);
      if (!live.current) return;
      if (data.status === 'success' || data.response) {
        const qualified = data.status === 'success' && data.generation_verified === true && verifiedReceipt(data.receipt) && data.sources?.length > 0;
        const missing = data.retrieval?.missing_source_indices;
        const assistantMsg = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.response || 'No response generated.',
          sources: data.sources || [],
          canInsert: qualified,
          coverage: verifiedReceipt(data.receipt) ? `Snapshot ${data.receipt.snapshot_sha256.slice(0, 12)} · ${data.context_docs_count ?? data.sources?.length ?? 0} passages. ${Array.isArray(missing) && missing.length ? `${missing.length} sources not covered by these excerpts.` : 'Bounded excerpts; this is not a full-project review.'}` : 'No verified current-source evidence; no generated suggestion is qualified.'
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        setMessages(prev => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `⚠️ Error: ${data.message || 'Could not query project database.'}`,
            sources: []
          }
        ]);
      }
    } catch (err) {
      if (!live.current) return;
      if (!textToSend) setInputValue(previous => previous || query);
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `⚠️ Connection error: ${(err instanceof Error ? err.message : String(err))}`,
          sources: []
        }
      ]);
    } finally {
      requests.current.delete(controller);
      if (live.current) setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '420px',
      maxWidth: '90vw',
      height: '100vh',
      background: '#0d1117',
      borderLeft: '1px solid #30363d',
      boxShadow: '-8px 0 30px rgba(0,0,0,0.7)',
      zIndex: 2500,
      display: 'flex',
      flexDirection: 'column',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px',
        background: '#161b22',
        borderBottom: '1px solid #30363d',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.3rem' }}>🤖</span>
            <div>
              <h3 style={{ margin: 0, color: '#f0f6fc', fontSize: '0.95rem', fontWeight: 'bold' }}>
                Script & Memoir Assistant
              </h3>
              <div style={{ color: '#8b949e', fontSize: '0.75rem' }}>
                Project: <strong style={{ color: '#58a6ff' }}>{projectName}</strong>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', fontSize: '1.2rem', cursor: 'pointer', padding: '4px' }}
          >
            ✕
          </button>
        </div>

        {/* Isolated DB Status Pill & Sync Button */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#090d16',
          padding: '6px 10px',
          borderRadius: '6px',
          border: '1px solid #1e293b',
          fontSize: '0.75rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8' }}>
            <span style={{ color: stats.status === 'success' ? '#22c55e' : '#eab308' }}>●</span>
            <span>Index: {stats.status} · <strong>{stats.total_docs || 0} source chunks</strong></span>
          </div>
          <button
            onClick={handleSync}
            disabled={isSyncing}
            style={{
              background: '#238636',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '2px 8px',
              fontSize: '0.7rem',
              fontWeight: 'bold',
              cursor: isSyncing ? 'wait' : 'pointer'
            }}
            title="Index current saved screenplay, book and transcript sources for this owner and project"
          >
            {isSyncing ? '⏳ Syncing...' : '🔄 Sync DB'}
          </button>
        </div>
        {verifiedReceipt(stats.receipt) && (
          <details style={{ fontSize: '0.7rem', color: '#8b949e', overflowWrap: 'anywhere' }}>
            <summary>Current source revisions · {stats.receipt.snapshot_sha256.slice(0, 12)}</summary>
            {stats.receipt.sources.map((/** @type {{type: string, source_file: string, revision: string}} */ source, /** @type {number} */ index) => <div key={index} title={source.revision}>{source.type} · {source.source_file} · {source.revision.slice(0, 12)}</div>)}
          </details>
        )}
        {syncMessage && (
          <div style={{ color: syncMessage.includes('❌') ? '#f87171' : '#4ade80', fontSize: '0.75rem' }}>
            {syncMessage}
          </div>
        )}
      </div>

      {/* Quick Prompt Chips */}
      <div style={{
        padding: '8px 12px',
        background: '#090d16',
        borderBottom: '1px solid #21262d',
        display: 'flex',
        gap: '6px',
        overflowX: 'auto',
        whiteSpace: 'nowrap'
      }}>
        {[
          '📖 Where in memoir is this?',
          '🎭 Character voice check',
          '🔍 Find courtroom scenes',
          '✍️ Suggest Act 2 turn'
        ].map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(chip)}
            disabled={isLoading}
            style={{
              background: '#161b22',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              borderRadius: '12px',
              padding: '3px 8px',
              fontSize: '0.72rem',
              cursor: 'pointer',
              flexShrink: 0
            }}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Message Stream */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        background: '#0d1117'
      }}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '92%'
            }}
          >
            <div style={{
              background: m.role === 'user' ? '#1f6feb' : '#161b22',
              color: '#f0f6fc',
              padding: '10px 14px',
              borderRadius: m.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
              border: m.role === 'user' ? 'none' : '1px solid #30363d',
              fontSize: '0.85rem',
              lineHeight: '1.45',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {m.content}
            </div>
            {m.coverage && <div style={{ fontSize: '0.7rem', color: '#8b949e', marginTop: '5px' }}>{m.coverage}</div>}

            {/* Action buttons on Assistant Messages */}
            {m.role === 'assistant' && m.id !== 'welcome' && (
              <div style={{ display: 'flex', gap: '8px', marginTop: '6px', alignItems: 'center' }}>
                <button
                  onClick={() => navigator.clipboard.writeText(m.content)}
                  style={{ background: 'transparent', border: '1px solid #30363d', color: '#8b949e', borderRadius: '4px', padding: '2px 6px', fontSize: '0.7rem', cursor: 'pointer' }}
                >
                  📋 Copy
                </button>
                {m.canInsert && typeof onInsertScript === 'function' && (
                  <button
                    onClick={() => onInsertScript(m.content)}
                    style={{ background: 'transparent', border: '1px solid #238636', color: '#3fb950', borderRadius: '4px', padding: '2px 6px', fontSize: '0.7rem', cursor: 'pointer' }}
                  >
                    📝 Insert in Script
                  </button>
                )}
              </div>
            )}

            {/* Source Citations Accordion */}
            {m.sources && m.sources.length > 0 && (
              <details style={{ marginTop: '6px', background: '#090d16', border: '1px solid #21262d', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}>
                <summary style={{ color: '#58a6ff', cursor: 'pointer', fontWeight: 'bold' }}>
                  📚 Sources Used ({m.sources.length})
                </summary>
                <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {m.sources.map((src, sIdx) => (
                    <div key={sIdx} style={{ background: '#161b22', padding: '6px', borderRadius: '4px', borderLeft: src.type === 'script_scene' ? '3px solid #3b82f6' : '3px solid #eab308' }}>
                      <div style={{ color: src.type === 'script_scene' ? '#93c5fd' : '#fde047', fontWeight: 'bold', fontSize: '0.7rem' }}>
                        {src.label}
                      </div>
                      <div style={{ color: '#8b949e', fontSize: '0.65rem', overflowWrap: 'anywhere' }} title={`Revision: ${src.source_revision || 'unverified'}; chunk: ${src.chunk_sha256 || 'unverified'}`}>
                        {src.source_file} · revision {src.source_revision?.slice(0, 12) || 'unverified'} · chunk {src.chunk_sha256?.slice(0, 12) || 'unverified'}
                      </div>
                      <div style={{ color: '#8b949e', fontSize: '0.7rem', marginTop: '2px', fontStyle: 'italic' }}>
                        "{src.excerpt}"
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))}
        {isLoading && (
          <div style={{ alignSelf: 'flex-start', background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '10px 14px', color: '#58a6ff', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>⏳ Searching {projectName} Vector DB & reasoning...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div style={{
        padding: '12px 14px',
        background: '#161b22',
        borderTop: '1px solid #30363d',
        display: 'flex',
        gap: '8px'
      }}>
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          placeholder="Ask about the memoir, compare book vs script..."
          rows={2}
          style={{
            flex: 1,
            background: '#0d1117',
            color: '#f0f6fc',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '8px 10px',
            fontSize: '0.85rem',
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit'
          }}
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={!inputValue.trim() || isLoading}
          style={{
            background: (!inputValue.trim() || isLoading) ? '#21262d' : '#238636',
            color: (!inputValue.trim() || isLoading) ? '#484f58' : '#fff',
            border: 'none',
            borderRadius: '6px',
            padding: '0 14px',
            fontWeight: 'bold',
            fontSize: '1rem',
            cursor: (!inputValue.trim() || isLoading) ? 'not-allowed' : 'pointer'
          }}
        >
          ➤
        </button>
      </div>
    </div>
  );
}
