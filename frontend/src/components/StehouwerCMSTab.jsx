import React, { useState, useEffect } from 'react';

const getApiBase = () => (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8080' : '');

export default function StehouwerCMSTab() {
  const [pages, setPages] = useState([]);
  const [selectedFile, setSelectedFile] = useState('index.html');
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [activeView, setActiveView] = useState('editor'); // 'editor' | 'preview'
  
  // AI Generator state
  const [aiTopic, setAiTopic] = useState('');
  const [aiSection, setAiSection] = useState('monolog');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiResult, setAiResult] = useState('');

  useEffect(() => {
    fetchPages();
  }, []);

  useEffect(() => {
    if (selectedFile) {
      loadFileContent(selectedFile);
    }
  }, [selectedFile]);

  const fetchPages = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${getApiBase()}/api/cms/pages`);
      const data = await res.json();
      if (data.status === 'success') {
        setPages(data.pages || []);
      }
    } catch (err) {
      console.error('Failed to fetch CMS pages:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filename) => {
    try {
      setLoading(true);
      const res = await fetch(`${getApiBase()}/api/cms/page/${filename}`);
      const data = await res.json();
      if (data.status === 'success') {
        setFileContent(data.content || '');
      } else {
        setFileContent('');
      }
    } catch (err) {
      console.error('Failed to load file content:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedFile) return;
    try {
      setSaving(true);
      setStatusMsg('');
      const res = await fetch(`${getApiBase()}/api/cms/page/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: selectedFile,
          content: fileContent
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMsg(`✅ Live website updated: ${selectedFile}`);
        fetchPages();
      } else {
        setStatusMsg(`❌ Error: ${data.message}`);
      }
    } catch (err) {
      setStatusMsg(`❌ Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleAiGenerate = async () => {
    if (!aiTopic) return;
    try {
      setAiGenerating(true);
      setAiResult('');
      const res = await fetch(`${getApiBase()}/api/cms/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: aiTopic,
          section: aiSection
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setAiResult(data.generated_content || '');
      } else {
        setAiResult('Error generating content');
      }
    } catch (err) {
      setAiResult(`Error: ${err.message}`);
    } finally {
      setAiGenerating(false);
    }
  };

  const appendAiResultToEditor = () => {
    if (!aiResult) return;
    setFileContent(prev => prev + '\n\n' + aiResult);
    setStatusMsg('✨ AI generated copy appended to editor');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: '#e0e0e0', fontFamily: 'Inter, sans-serif' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', backgroundColor: '#161922', borderBottom: '1px solid #282d3c' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', color: '#fff' }}>Stehouwer Publishing CMS</h2>
          <span style={{ fontSize: '0.85rem', color: '#8b949e' }}>Live Control & AI Content Engine for stehouwer-publishing.com</span>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <span style={{ padding: '4px 12px', borderRadius: '12px', backgroundColor: '#1b3b2b', color: '#3fb950', fontSize: '0.85rem', fontWeight: 600, border: '1px solid #238636' }}>
            ● Live on stehouwer-publishing.com
          </span>
          <span style={{ padding: '4px 12px', borderRadius: '12px', backgroundColor: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', fontSize: '0.85rem', fontWeight: 600, border: '1px solid rgba(56, 189, 248, 0.4)' }}>
            🔒 SHA-256 Wire & Wave Telemetry Active
          </span>
          <button onClick={fetchPages} style={{ padding: '6px 14px', backgroundColor: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '6px', cursor: 'pointer' }}>
            🔄 Refresh Files
          </button>
        </div>
      </div>

      {/* Main Workspace Area */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Column: File Explorer */}
        <div style={{ width: '240px', backgroundColor: '#0d1117', borderRight: '1px solid #21262d', padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <h4 style={{ marginTop: 0, marginBottom: '12px', color: '#8b949e', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.05em' }}>Site Pages & Assets</h4>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {pages.map((p) => (
              <div
                key={p.filename}
                onClick={() => setSelectedFile(p.filename)}
                style={{
                  padding: '10px 12px',
                  borderRadius: '6px',
                  marginBottom: '6px',
                  cursor: 'pointer',
                  backgroundColor: selectedFile === p.filename ? '#1f242d' : 'transparent',
                  borderLeft: selectedFile === p.filename ? '3px solid #58a6ff' : '3px solid transparent',
                  transition: 'background-color 0.15s'
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: selectedFile === p.filename ? '#58a6ff' : '#c9d1d9' }}>
                  📄 {p.filename}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '4px' }}>
                  {(p.size / 1024).toFixed(1)} KB
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center Column: Editor / Preview */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: '#161b22', borderRight: '1px solid #21262d' }}>
          
          {/* Subheader Toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 16px', backgroundColor: '#0d1117', borderBottom: '1px solid #21262d' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setActiveView('editor')}
                style={{
                  padding: '6px 16px',
                  borderRadius: '6px',
                  backgroundColor: activeView === 'editor' ? '#21262d' : 'transparent',
                  color: activeView === 'editor' ? '#58a6ff' : '#8b949e',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                📝 Code Editor
              </button>
              <button
                onClick={() => setActiveView('preview')}
                style={{
                  padding: '6px 16px',
                  borderRadius: '6px',
                  backgroundColor: activeView === 'preview' ? '#21262d' : 'transparent',
                  color: activeView === 'preview' ? '#58a6ff' : '#8b949e',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 600
                }}
              >
                👁️ Live Preview
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {statusMsg && <span style={{ fontSize: '0.85rem', color: statusMsg.includes('Error') ? '#f85149' : '#3fb950' }}>{statusMsg}</span>}
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  padding: '8px 20px',
                  backgroundColor: '#238636',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                }}
              >
                {saving ? 'Saving...' : '💾 Publish Changes Live'}
              </button>
            </div>
          </div>

          {/* Main Content Pane */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
            {activeView === 'editor' ? (
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                spellCheck={false}
                style={{
                  width: '100%',
                  height: '100%',
                  backgroundColor: '#0d1117',
                  color: '#e6edf3',
                  border: 'none',
                  padding: '16px',
                  fontFamily: 'Consolas, Monaco, "Fira Code", monospace',
                  fontSize: '0.9rem',
                  lineHeight: '1.5',
                  resize: 'none',
                  outline: 'none'
                }}
              />
            ) : (
              <iframe
                title="Live Preview"
                src={`https://stehouwer-publishing.com/${selectedFile}`}
                style={{ width: '100%', height: '100%', border: 'none', backgroundColor: '#fff' }}
              />
            )}
          </div>
        </div>

        {/* Right Column: Stehouwer LLM Copywriter */}
        <div style={{ width: '320px', backgroundColor: '#0d1117', padding: '16px', display: 'flex', flexDirection: 'column', borderLeft: '1px solid #21262d' }}>
          <h4 style={{ marginTop: 0, marginBottom: '12px', color: '#58a6ff', fontSize: '0.95rem' }}>✨ Stehouwer AI Copywriter</h4>
          
          <label style={{ fontSize: '0.8rem', color: '#8b949e', marginBottom: '4px' }}>Content Section Type</label>
          <select
            value={aiSection}
            onChange={(e) => setAiSection(e.target.value)}
            style={{ width: '100%', padding: '8px', backgroundColor: '#161b22', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '6px', marginBottom: '12px' }}
          >
            <option value="monolog">2024 Monolog / Story</option>
            <option value="book_description">Library Book Description</option>
            <option value="marketing_copy">Marketing & Press Release</option>
          </select>

          <label style={{ fontSize: '0.8rem', color: '#8b949e', marginBottom: '4px' }}>Topic or Key Details</label>
          <textarea
            value={aiTopic}
            onChange={(e) => setAiTopic(e.target.value)}
            placeholder="e.g. New monolog about inspiration and persistence in publishing..."
            rows={3}
            style={{ width: '100%', padding: '8px', backgroundColor: '#161b22', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '6px', marginBottom: '12px', resize: 'none' }}
          />

          <button
            onClick={handleAiGenerate}
            disabled={aiGenerating || !aiTopic}
            style={{ width: '100%', padding: '10px', backgroundColor: '#1f6feb', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', marginBottom: '16px' }}
          >
            {aiGenerating ? 'Generating AI Copy...' : '🤖 Generate with Stehouwer LLM'}
          </button>

          {aiResult && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontSize: '0.8rem', color: '#3fb950', marginBottom: '6px', fontWeight: 600 }}>Generated Output:</div>
              <textarea
                readOnly
                value={aiResult}
                style={{ flex: 1, width: '100%', backgroundColor: '#161b22', color: '#e6edf3', border: '1px solid #30363d', borderRadius: '6px', padding: '10px', fontSize: '0.85rem', resize: 'none', marginBottom: '10px' }}
              />
              <button
                onClick={appendAiResultToEditor}
                style={{ padding: '8px', backgroundColor: '#21262d', color: '#58a6ff', border: '1px solid #30363d', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
              >
                📋 Append Output to Editor
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
