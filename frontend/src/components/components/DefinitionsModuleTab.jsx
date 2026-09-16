import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  BookOpen, History, Layers, GraduationCap, Search, Sparkles,
  CheckCircle2, XCircle, HelpCircle, ArrowRight, Shield, Zap,
  Cpu, Database, ChevronDown, ChevronRight, FileText
} from 'lucide-react';
import ContentGovernanceRiskModal from './ContentGovernanceRiskModal';

// ── Shared design tokens (GitHub dark palette matching AI-BS system) ──────────
const S = {
  page:        { padding: '28px', background: '#0b0f19', minHeight: '100vh', color: '#f0f6fc', display: 'flex', flexDirection: 'column', gap: '24px' },
  hero:        { background: 'linear-gradient(135deg, #0d1117 0%, #1a1f35 50%, #1e1330 100%)', border: '1px solid rgba(99,102,241,0.25)', borderRadius: '14px', padding: '28px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', position: 'relative', overflow: 'hidden' },
  heroBadge:   { display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '3px 12px', borderRadius: '20px', background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.35)', color: '#a5b4fc', fontSize: '0.72rem', fontFamily: 'monospace', marginBottom: '10px' },
  heroTitle:   { fontSize: '1.85rem', fontWeight: '800', background: 'linear-gradient(90deg, #60a5fa, #c084fc, #f472b6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0, letterSpacing: '-0.5px' },
  heroSub:     { color: '#8b949e', fontSize: '0.88rem', marginTop: '6px', maxWidth: '520px' },
  heroStatus:  { display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(8px)', padding: '10px 16px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)', flexShrink: 0 },
  navBar:      { display: 'flex', gap: '8px', flexWrap: 'wrap', borderBottom: '1px solid #21262d', paddingBottom: '16px' },
  card:        { background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' },
  searchWrap:  { position: 'relative', display: 'flex', alignItems: 'center' },
  searchIcon:  { position: 'absolute', left: '10px', color: '#484f58', pointerEvents: 'none' },
  input:       { background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#f0f6fc', fontSize: '0.82rem', padding: '8px 12px 8px 34px', outline: 'none', width: '220px' },
  monoBlock:   { background: '#0d1117', border: '1px solid #21262d', borderRadius: '8px', padding: '16px', fontFamily: 'monospace', fontSize: '0.78rem', color: '#c9d1d9', whiteSpace: 'pre-wrap', overflowX: 'auto', maxHeight: '500px', lineHeight: '1.65', overflowY: 'auto' },
  sectionTitle:{ color: '#f0f6fc', fontSize: '1.15rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 },
  verBadge:    { fontSize: '0.72rem', fontFamily: 'monospace', fontWeight: '700', padding: '2px 10px', borderRadius: '6px', background: 'rgba(99,102,241,0.15)', color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.3)' },
};

const tabBtn   = (active, c0, c1) => ({ display: 'flex', alignItems: 'center', gap: '7px', padding: '8px 18px', borderRadius: '8px', fontWeight: '600', fontSize: '0.82rem', cursor: 'pointer', border: active ? 'none' : '1px solid #30363d', background: active ? `linear-gradient(135deg,${c0},${c1})` : '#161b22', color: active ? '#fff' : '#8b949e', boxShadow: active ? `0 4px 14px ${c0}44` : 'none', transition: 'all 0.2s' });
const pill     = (active, color) => ({ padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600', cursor: 'pointer', border: active ? 'none' : '1px solid #30363d', background: active ? color : '#161b22', color: active ? '#fff' : '#8b949e', transition: 'all 0.15s' });
const tagChip  = (color) => ({ fontSize: '0.68rem', fontFamily: 'monospace', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '2px 8px', borderRadius: '4px', background: `${color}18`, color, border: `1px solid ${color}44` });
const ansBtn   = (state) => {
  const b = { width: '100%', textAlign: 'left', padding: '12px 16px', borderRadius: '8px', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: state === 'locked' ? 'default' : 'pointer', transition: 'all 0.15s' };
  if (state === 'correct') return { ...b, background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.5)', color: '#6ee7b7', fontWeight: '700' };
  if (state === 'wrong')   return { ...b, background: 'rgba(239,68,68,0.12)',   border: '1px solid rgba(239,68,68,0.5)',  color: '#fca5a5', fontWeight: '700' };
  if (state === 'locked')  return { ...b, background: '#0d1117', border: '1px solid #21262d', color: '#6e7681' };
  return { ...b, background: '#0d1117', border: '1px solid #30363d', color: '#c9d1d9' };
};

function StatTile({ label, value, color }) {
  return (
    <div style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: '8px', padding: '12px' }}>
      <div style={{ fontSize: '0.68rem', color: '#484f58', marginBottom: '4px' }}>{label}</div>
      <div style={{ fontSize: '1.3rem', fontWeight: '800', fontFamily: 'monospace', color }}>{value}</div>
    </div>
  );
}
function LoadingState({ color, text }) {
  return <div style={{ padding: '60px', textAlign: 'center', color, fontFamily: 'monospace', fontSize: '0.88rem' }}>⟳ {text}</div>;
}
function ErrorState({ text }) {
  return <div style={{ padding: '20px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '10px', color: '#f87171', fontSize: '0.85rem' }}>{text}</div>;
}

// ── Root ─────────────────────────────────────────────────────────────────────
export default function DefinitionsModuleTab({ backendUrl: propBackendUrl }) {
  const backendUrl = propBackendUrl || import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://ai-bs-dashboard.web.app');
  const [activeTab, setActiveTab] = useState('timeline');
  const [isGovernanceOpen, setIsGovernanceOpen] = useState(false);
  const tabs = [
    { id: 'timeline',   label: 'Architectural Timeline',  Icon: History,       c: ['#6366f1','#4f46e5'] },
    { id: 'glossary',   label: 'AI-BS Jargon Glossary',   Icon: BookOpen,      c: ['#a855f7','#9333ea'] },
    { id: 'chronology', label: 'Master Markdown Records', Icon: Layers,        c: ['#10b981','#059669'] },
    { id: 'quiz',       label: 'Interactive Study Guide', Icon: GraduationCap, c: ['#f59e0b','#d97706'] },
  ];
  return (
    <div style={S.page}>
      <div style={S.hero} className="glass-panel">
        <div style={{ position: 'absolute', top: '-60px', right: '-60px', width: '280px', height: '280px', background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={S.heroBadge}><Sparkles size={12} /> AI-BS Matrix Knowledge System</div>
          <h1 style={S.heroTitle}>Definitions, Lore &amp; Study Guide</h1>
          <p style={S.heroSub}>Master the architectural timeline, jargon dictionary, and historical chronologies of the AI-BS ecosystem.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => setIsGovernanceOpen(true)}
            style={{
              background: 'linear-gradient(135deg, #0284c7, #2563eb)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '10px 16px',
              fontSize: '0.82rem',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 14px rgba(2,132,199,0.35)'
            }}
          >
            🛡️ Content Risk &amp; Governance Analyzer
          </button>
          <div style={S.heroStatus}>
            <Shield size={18} color="#34d399" />
            <div>
              <div style={{ fontSize: '0.7rem', color: '#484f58' }}>System Manual</div>
              <div style={{ fontSize: '0.78rem', color: '#34d399', fontWeight: '700' }}>v5.54.0 Active</div>
            </div>
          </div>
        </div>
      </div>

      <div style={S.navBar}>
        {tabs.map(({ id, label, Icon, c }) => (
          <button key={id} style={tabBtn(activeTab === id, c[0], c[1])} onClick={() => setActiveTab(id)}>
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {activeTab === 'timeline'   && <ArchitecturalTimelinePanel   backendUrl={backendUrl} />}
      {activeTab === 'glossary'   && <JargonGlossaryPanel          backendUrl={backendUrl} />}
      {activeTab === 'chronology' && <MasterRecordsChronologyPanel backendUrl={backendUrl} />}
      {activeTab === 'quiz'       && <InteractiveStudyGuidePanel   backendUrl={backendUrl} />}
    </div>
  );
}

// ── 1. ARCHITECTURAL TIMELINE ─────────────────────────────────────────────────
function ArchitecturalTimelinePanel({ backendUrl }) {
  const [history, setHistory]             = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [expandedIndex, setExpandedIndex] = useState(0);
  const [searchTerm, setSearchTerm]       = useState('');

  useEffect(() => {
    fetch(`${backendUrl}/api/v1/dictionary/ledger-history`)
      .then(r => r.json())
      .then(j => { if (j.data) setHistory(j.data); else setError(j.message || 'Fetch error'); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [backendUrl]);

  const filtered = history.filter(item =>
    item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.version.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.body.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) return <LoadingState color="#6366f1" text="Parsing Master Architectural Ledger..." />;
  if (error)   return <ErrorState text={error} />;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '24px', alignItems: 'start' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <h2 style={S.sectionTitle}><History size={20} color="#6366f1" /> Evolution Milestone Timeline</h2>
          <div style={S.searchWrap}>
            <Search size={14} style={S.searchIcon} />
            <input style={S.input} placeholder="Filter milestones..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
          </div>
        </div>

        <div style={{ borderLeft: '2px solid rgba(99,102,241,0.3)', marginLeft: '14px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filtered.map((item, idx) => {
            const isOpen = expandedIndex === idx;
            return (
              <div key={idx} style={{ marginLeft: '28px', position: 'relative' }}>
                <div style={{ position: 'absolute', left: '-42px', top: '14px', width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', background: isOpen ? '#6366f1' : '#161b22', border: isOpen ? 'none' : '1px solid rgba(99,102,241,0.4)', color: isOpen ? '#fff' : '#6366f1', boxShadow: isOpen ? '0 0 14px rgba(99,102,241,0.5)' : 'none', transition: 'all 0.2s' }}>⚡</div>
                <div onClick={() => setExpandedIndex(isOpen ? -1 : idx)} style={{ ...S.card, cursor: 'pointer', border: `1px solid ${isOpen ? 'rgba(99,102,241,0.55)' : '#30363d'}`, boxShadow: isOpen ? '0 0 24px rgba(99,102,241,0.1)' : 'none', transition: 'all 0.2s' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '8px' }}>
                    <span style={S.verBadge}>{item.version}</span>
                    <span style={{ fontSize: '0.72rem', fontFamily: 'monospace', color: '#484f58' }}>{item.date}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ color: isOpen ? '#a5b4fc' : '#e6edf3', fontSize: '0.95rem', fontWeight: '700', margin: 0 }}>{item.title}</h3>
                    {isOpen ? <ChevronDown size={16} color="#6366f1" /> : <ChevronRight size={16} color="#484f58" />}
                  </div>
                  {isOpen ? (
                    <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid #21262d' }}>
                      <div className="artifact-markdown-container" style={S.monoBlock}><ReactMarkdown>{item.body}</ReactMarkdown></div>
                    </div>
                  ) : (
                    <p style={{ color: '#484f58', fontSize: '0.75rem', marginTop: '6px', fontStyle: 'italic' }}>Click to inspect technical details and design rationale...</p>
                  )}
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && <div style={{ color: '#484f58', fontSize: '0.85rem', padding: '24px', textAlign: 'center' }}>No milestones match &quot;{searchTerm}&quot;</div>}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ ...S.card, display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <h3 style={{ ...S.sectionTitle, borderBottom: '1px solid #21262d', paddingBottom: '10px' }}><Cpu size={16} color="#6366f1" /> System Ledger Overview</h3>
          <p style={{ fontSize: '0.75rem', color: '#8b949e', lineHeight: '1.6' }}>Real-time telemetry extracted from <code style={{ fontFamily: 'monospace', color: '#a5b4fc', fontSize: '0.72rem' }}>AI_BS_MASTER_ARCHITECTURAL_LEDGER.md</code>.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <StatTile label="Total Versions" value={history.length} color="#6366f1" />
            <StatTile label="Active Build"   value={history[0]?.version || 'v5.54.0'} color="#34d399" />
          </div>
          <div style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: '8px', padding: '12px' }}>
            <div style={{ fontWeight: '700', fontSize: '0.78rem', color: '#a5b4fc', marginBottom: '6px' }}>Master Ledger Guarantee</div>
            <p style={{ fontSize: '0.72rem', color: '#8b949e', lineHeight: '1.6', margin: 0 }}>All refactors automatically update timestamped entries, ports, schemas, and fallback contexts.</p>
          </div>
        </div>
        <div style={S.card}>
          <h3 style={{ ...S.sectionTitle, marginBottom: '12px' }}><Database size={16} color="#34d399" /> Legend</h3>
          {[['#34d399','Deployed to Firebase Hosting'],['#6366f1','Backend / API change'],['#f59e0b','Frontend / UI upgrade'],['#f472b6','AI / LLM integration']].map(([dot, label]) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '0.75rem', color: '#8b949e' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: dot, flexShrink: 0 }} />{label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 2. JARGON GLOSSARY ────────────────────────────────────────────────────────
const CAT_COLOR = { 'Architecture': '#6366f1', 'Memory & Storage': '#34d399', 'AI / LLM': '#f472b6', 'Security': '#f59e0b', 'Finance': '#38bdf8', 'Networking': '#a855f7' };
const catColor = cat => CAT_COLOR[cat] || '#8b949e';

function JargonGlossaryPanel({ backendUrl }) {
  const [terms, setTerms]                   = useState([]);
  const [loading, setLoading]               = useState(true);
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [search, setSearch]                 = useState('');

  useEffect(() => {
    fetch(`${backendUrl}/api/v1/dictionary/terms`)
      .then(r => r.json()).then(j => { if (j.data) setTerms(j.data); }).catch(() => {}).finally(() => setLoading(false));
  }, [backendUrl]);

  const categories = ['ALL', ...new Set(terms.map(t => t.category))];
  const filtered   = terms.filter(t => {
    const matchCat  = filterCategory === 'ALL' || t.category === filterCategory;
    const matchText = t.term.toLowerCase().includes(search.toLowerCase()) || t.definition.toLowerCase().includes(search.toLowerCase()) || t.tag.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchText;
  });

  if (loading) return <LoadingState color="#a855f7" text="Loading AI-BS Glossary..." />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h2 style={S.sectionTitle}><BookOpen size={20} color="#a855f7" /> AI-BS Jargon &amp; Terminology Glossary</h2>
          <p style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '4px' }}>Official terminology definitions and architectural impact specifications.</p>
        </div>
        <div style={S.searchWrap}>
          <Search size={14} style={S.searchIcon} />
          <input style={{ ...S.input, width: '240px' }} placeholder="Search jargon..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        {categories.map(cat => <button key={cat} style={pill(filterCategory === cat, catColor(cat))} onClick={() => setFilterCategory(cat)}>{cat}</button>)}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
        {filtered.map((t, idx) => (
          <div key={idx} style={{ ...S.card, display: 'flex', flexDirection: 'column', gap: '12px', transition: 'border-color 0.2s' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = `${catColor(t.category)}66`}
            onMouseLeave={e => e.currentTarget.style.borderColor = '#30363d'}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
              <div>
                <span style={tagChip(catColor(t.category))}>{t.category}</span>
                <h3 style={{ color: '#f0f6fc', fontSize: '1rem', fontWeight: '700', margin: '8px 0 0 0' }}>{t.term}</h3>
              </div>
              <span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: '#8b949e', background: '#0d1117', border: '1px solid #30363d', padding: '2px 8px', borderRadius: '6px', whiteSpace: 'nowrap', flexShrink: 0 }}>{t.tag}</span>
            </div>
            <div className="artifact-markdown-container" style={{ color: '#c9d1d9', fontSize: '0.82rem', lineHeight: '1.65' }}>
              <ReactMarkdown>{t.definition}</ReactMarkdown>
            </div>
            <div style={{ borderTop: '1px solid #21262d', paddingTop: '10px', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <Zap size={13} color="#34d399" style={{ flexShrink: 0, marginTop: '2px' }} />
              <span style={{ fontSize: '0.75rem', color: '#34d399', lineHeight: '1.5' }}><strong>Impact:</strong> {t.impact}</span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && <div style={{ gridColumn: '1 / -1', color: '#484f58', textAlign: 'center', padding: '40px', fontSize: '0.85rem' }}>No terms found.</div>}
      </div>
    </div>
  );
}

// ── 3. MASTER RECORDS CHRONOLOGY ─────────────────────────────────────────────
function MasterRecordsChronologyPanel({ backendUrl }) {
  const [data, setData]               = useState(null);
  const [loading, setLoading]         = useState(true);
  const [selectedRecord, setSelected] = useState('tasks_chronology');

  useEffect(() => {
    fetch(`${backendUrl}/api/v1/dictionary/master-chronology`)
      .then(r => r.json()).then(j => { if (j.data) setData(j.data); }).catch(() => {}).finally(() => setLoading(false));
  }, [backendUrl]);

  const records = [
    { key: 'tasks_chronology',   label: 'MASTER_TASKS_CHRONOLOGY.md',                icon: FileText, path: 'Agent_Tasks_History/' },
    { key: 'plans_chronology',   label: 'MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md', icon: Layers,   path: 'Agent_Implementation_Plans_History/' },
    { key: 'handoff_chronology', label: 'MASTER_HANDOFF_CHRONOLOGY.md',              icon: History,  path: 'Agent_Handoff_Summaries/' },
    { key: 'artifact_history',   label: 'artifact_history.md',                       icon: Database, path: 'NotebookLM_Records/' },
    { key: 'master_index',       label: 'MASTER_HISTORICAL_INDEX.md',                icon: BookOpen, path: 'C:\\AI-BS\\' },
  ];
  const active = records.find(r => r.key === selectedRecord);

  if (loading) return <LoadingState color="#10b981" text="Fetching Master Markdown Ledgers..." />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h2 style={S.sectionTitle}><Layers size={20} color="#10b981" /> Master Markdown Ledgers</h2>
        <p style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '4px' }}>Direct view of all centralized chronological record archives.</p>
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {records.map(rec => {
          const RecIcon = rec.icon;
          const isActive = selectedRecord === rec.key;
          return (
            <button key={rec.key} onClick={() => setSelected(rec.key)} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '8px', fontSize: '0.72rem', fontFamily: 'monospace', fontWeight: '600', cursor: 'pointer', border: isActive ? 'none' : '1px solid #30363d', background: isActive ? 'linear-gradient(135deg,#10b981,#059669)' : '#161b22', color: isActive ? '#fff' : '#8b949e', boxShadow: isActive ? '0 4px 12px rgba(16,185,129,0.3)' : 'none', transition: 'all 0.2s' }}>
              <RecIcon size={12} /> {rec.label}
            </button>
          );
        })}
      </div>

      <div style={{ ...S.card, background: '#0d1117' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', paddingBottom: '12px', borderBottom: '1px solid #21262d', flexWrap: 'wrap', gap: '8px' }}>
          <span style={{ fontSize: '0.78rem', fontFamily: 'monospace', color: '#8b949e' }}>Active: <strong style={{ color: '#34d399' }}>{active?.label}</strong></span>
          <span style={{ fontSize: '0.72rem', fontFamily: 'monospace', color: '#484f58' }}>📁 {active?.path}</span>
        </div>
        {data?.[selectedRecord] ? (
          <div className="artifact-markdown-container" style={S.monoBlock}><ReactMarkdown>{data[selectedRecord]}</ReactMarkdown></div>
        ) : (
          <div style={{ color: '#484f58', fontSize: '0.82rem', padding: '20px', textAlign: 'center' }}>No record content found — backend may be offline.</div>
        )}
      </div>
    </div>
  );
}

// ── 4. INTERACTIVE STUDY GUIDE ────────────────────────────────────────────────
function InteractiveStudyGuidePanel({ backendUrl }) {
  const [questions, setQuestions]       = useState([]);
  const [loading, setLoading]           = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelected]   = useState(null);
  const [score, setScore]               = useState(0);
  const [showExplanation, setShowExp]   = useState(false);
  const [completed, setCompleted]       = useState(false);

  useEffect(() => {
    fetch(`${backendUrl}/api/v1/dictionary/quiz`)
      .then(r => r.json()).then(j => { if (j.data) setQuestions(j.data); }).catch(() => {}).finally(() => setLoading(false));
  }, [backendUrl]);

  if (loading) return <LoadingState color="#f59e0b" text="Preparing Study Guide Quiz..." />;
  if (questions.length === 0) return <div style={{ color: '#8b949e', textAlign: 'center', padding: '60px', fontSize: '0.88rem' }}>No study guide questions available from backend.</div>;

  const q           = questions[currentIndex];
  const pct         = Math.round(((currentIndex + 1) / questions.length) * 100);
  const scorePercent = Math.round((score / questions.length) * 100);

  const handleSelect = (idx) => {
    if (selectedOption !== null) return;
    setSelected(idx); setShowExp(true);
    if (idx === q.answerIndex) setScore(s => s + 1);
  };
  const handleNext = () => {
    if (currentIndex < questions.length - 1) { setCurrentIndex(i => i + 1); setSelected(null); setShowExp(false); }
    else { setCompleted(true); }
  };
  const handleRestart = () => { setCurrentIndex(0); setSelected(null); setShowExp(false); setScore(0); setCompleted(false); };

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ ...S.sectionTitle, justifyContent: 'center', fontSize: '1.4rem' }}><GraduationCap size={24} color="#f59e0b" /> AI-BS Mastery Study Guide</h2>
        <p style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '6px' }}>Test your mastery of sub-3µs SHM latency, Thoughtful Friction gates, and ATR risk calculations.</p>
      </div>

      {!completed ? (
        <div style={{ ...S.card, display: 'flex', flexDirection: 'column', gap: '18px', boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', fontFamily: 'monospace', color: '#8b949e', borderBottom: '1px solid #21262d', paddingBottom: '12px' }}>
            <span>Question <strong style={{ color: '#f0f6fc' }}>{currentIndex + 1}</strong> of <strong style={{ color: '#f0f6fc' }}>{questions.length}</strong></span>
            <span style={{ color: '#f59e0b', fontWeight: '700' }}>Score: {score}</span>
          </div>
          <div style={{ width: '100%', height: '4px', background: '#21262d', borderRadius: '2px' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,#f59e0b,#d97706)', borderRadius: '2px', transition: 'width 0.3s ease' }} />
          </div>
          <h3 style={{ color: '#f0f6fc', fontSize: '1rem', fontWeight: '700', lineHeight: '1.5', margin: 0 }}>{q.question}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {q.options.map((opt, idx) => {
              let state = 'default';
              if (selectedOption !== null) { if (idx === q.answerIndex) state = 'correct'; else if (idx === selectedOption) state = 'wrong'; else state = 'locked'; }
              return (
                <button key={idx} style={ansBtn(state)} onClick={() => handleSelect(idx)}>
                  <span style={{ lineHeight: '1.4' }}>{opt}</span>
                  {selectedOption !== null && idx === q.answerIndex && <CheckCircle2 size={17} color="#34d399" style={{ flexShrink: 0 }} />}
                  {selectedOption !== null && idx === selectedOption && idx !== q.answerIndex && <XCircle size={17} color="#ef4444" style={{ flexShrink: 0 }} />}
                </button>
              );
            })}
          </div>
          {showExplanation && (
            <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: '8px', padding: '14px', display: 'flex', gap: '10px' }}>
              <HelpCircle size={16} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#f59e0b', marginBottom: '4px' }}>Architectural Rationale</div>
                <div className="artifact-markdown-container" style={{ fontSize: '0.78rem', color: '#d1d5db' }}><ReactMarkdown>{q.explanation}</ReactMarkdown></div>
              </div>
            </div>
          )}
          {selectedOption !== null && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={handleNext} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 22px', background: 'linear-gradient(135deg,#f59e0b,#d97706)', border: 'none', borderRadius: '8px', color: '#0b0f19', fontWeight: '800', fontSize: '0.85rem', cursor: 'pointer' }}>
                {currentIndex < questions.length - 1 ? 'Next Question' : 'View Final Score'} <ArrowRight size={15} />
              </button>
            </div>
          )}
        </div>
      ) : (
        <div style={{ ...S.card, textAlign: 'center', padding: '48px 32px', border: '1px solid rgba(245,158,11,0.3)', boxShadow: '0 8px 32px rgba(245,158,11,0.08)' }}>
          <div style={{ width: '72px', height: '72px', borderRadius: '50%', background: 'rgba(245,158,11,0.12)', border: '2px solid #f59e0b', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}><GraduationCap size={36} color="#f59e0b" /></div>
          <h3 style={{ color: '#f0f6fc', fontSize: '1.6rem', fontWeight: '800', margin: '0 0 12px' }}>Quiz Complete</h3>
          <p style={{ color: '#8b949e', fontSize: '0.88rem', marginBottom: '8px' }}>You scored <strong style={{ color: '#f59e0b', fontSize: '1.4rem', fontFamily: 'monospace' }}>{score}</strong> of <strong style={{ color: '#f0f6fc', fontSize: '1.4rem', fontFamily: 'monospace' }}>{questions.length}</strong></p>
          <div style={{ display: 'inline-block', padding: '4px 16px', borderRadius: '20px', background: scorePercent >= 80 ? 'rgba(16,185,129,0.15)' : scorePercent >= 50 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)', color: scorePercent >= 80 ? '#34d399' : scorePercent >= 50 ? '#f59e0b' : '#f87171', fontWeight: '700', fontSize: '0.82rem', marginBottom: '28px' }}>
            {scorePercent >= 80 ? '🏆 Expert Level' : scorePercent >= 50 ? '📈 Progressing' : '🔄 Keep Studying'}
          </div>
          <br />
          <button onClick={handleRestart} style={{ padding: '12px 32px', background: '#f59e0b', border: 'none', borderRadius: '8px', color: '#0b0f19', fontWeight: '800', fontSize: '0.88rem', cursor: 'pointer' }}>Restart Mastery Study Guide</button>
        </div>
      )}

      {/* Content Governance Risk Modal */}
      <ContentGovernanceRiskModal 
        isOpen={isGovernanceOpen} 
        onClose={() => setIsGovernanceOpen(false)} 
      />
    </div>
  );
}
