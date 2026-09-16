import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import MonacoEditor from '@monaco-editor/react';
import AdaptationStatusBar from './AdaptationStatusBar.jsx';
import WordDocsPaperCanvas from './WordDocsPaperCanvas.jsx';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

// ═══════════════════════════════════════════════════════════════════════
// DOCUMENT TEMPLATES — Create new documents from scratch
// ═══════════════════════════════════════════════════════════════════════

const TEMPLATES = [
  {
    id: 'blank',
    label: 'Blank Document',
    icon: '📄',
    description: 'Empty document — start from scratch',
    ext: '.txt',
    mimeType: 'text/plain',
    content: '',
  },
  {
    id: 'screenplay',
    label: 'Screenplay',
    icon: '🎬',
    description: 'Standard Hollywood screenplay format (8.5" × 11")',
    ext: '.fdx',
    mimeType: 'application/xml',
    content: '<?xml version="1.0" encoding="UTF-8"?>\n<FinalDraft type="draft" name="" date="" id="">\n<PageBreaks>\n</PageBreaks>\n<Content>\n<Paragraph>\n<Text>INT. LOCATION - DAY</Text>\n</Paragraph>\n<Paragraph>\n<Text></Text>\n</Paragraph>\n</Content>\n</FinalDraft>',
  },
  {
    id: 'markdown',
    label: 'Markdown Document',
    icon: '📝',
    description: 'Rich markdown with headings, lists, and formatting',
    ext: '.md',
    mimeType: 'text/markdown',
    content: '# Untitled Document\n\n## Section\n\nStart writing your content here...\n\n- Bullet point 1\n- Bullet point 2\n- Bullet point 3\n\n### Subsection\n\nMore detailed content goes here.\n',
  },
  {
    id: 'json',
    label: 'JSON Configuration',
    icon: '⚙️',
    description: 'Structured JSON data file',
    ext: '.json',
    mimeType: 'application/json',
    content: '{\n  "name": "untitled",\n  "version": "1.0.0",\n  "description": "",\n  "settings": {}\n}',
  },
  {
    id: 'python',
    label: 'Python Script',
    icon: '🐍',
    description: 'Python source file with boilerplate',
    ext: '.py',
    mimeType: 'text/x-python',
    content: '#!/usr/bin/env python3\n"""Module docstring."""\n\ndef main():\n    """Entry point.""">\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n',
  },
  {
    id: 'html',
    label: 'HTML Page',
    icon: '🌐',
    description: 'Basic HTML5 document structure',
    ext: '.html',
    mimeType: 'text/html',
    content: '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Untitled Page</title>\n    <style>\n        body {\n            font-family: system-ui, sans-serif;\n            max-width: 800px;\n            margin: 2rem auto;\n            padding: 0 1rem;\n        }\n    </style>\n</head>\n<body>\n    <h1>Untitled Page</h1>\n    <p>Start editing this file...</p>\n</body>\n</html>',
  },
  {
    id: 'css',
    label: 'CSS Stylesheet',
    icon: '🎨',
    description: 'Cascading stylesheet with reset',
    ext: '.css',
    mimeType: 'text/css',
    content: '/* Reset */\n*, *::before, *::after {\n    box-sizing: border-box;\n    margin: 0;\n    padding: 0;\n}\n\nbody {\n    font-family: system-ui, -apple-system, sans-serif;\n    line-height: 1.6;\n    color: #333;\n}\n',
  },
  {
    id: 'readme',
    label: 'README',
    icon: '📖',
    description: 'Project documentation template',
    ext: '.md',
    mimeType: 'text/markdown',
    content: '# Project Name\n\n## Description\n\nBrief description of the project.\n\n## Installation\n\n```bash\nnpm install\n```\n\n## Usage\n\n```bash\nnpm start\n```\n\n## License\n\nMIT\n',
  },
];

// ═══════════════════════════════════════════════════════════════════════
// FILE TYPE REGISTRY
// ═══════════════════════════════════════════════════════════════════════

const FILE_TYPE_MAP = {
  '.txt': { label: 'Text', language: 'plaintext', icon: '📄' },
  '.md': { label: 'Markdown', language: 'markdown', icon: '📝' },
  '.json': { label: 'JSON', language: 'javascript', icon: '⚙️' },
  '.py': { label: 'Python', language: 'python', icon: '🐍' },
  '.html': { label: 'HTML', language: 'html', icon: '🌐' },
  '.css': { label: 'CSS', language: 'css', icon: '🎨' },
  '.js': { label: 'JavaScript', language: 'javascript', icon: '⚡' },
  '.jsx': { label: 'JSX', language: 'javascript', icon: '⚛️' },
  '.ts': { label: 'TypeScript', language: 'typescript', icon: '🔷' },
  '.tsx': { label: 'TSX', language: 'typescript', icon: '⚛️' },
  '.xml': { label: 'XML', language: 'xml', icon: '📋' },
  '.fdx': { label: 'Final Draft', language: 'xml', icon: '🎬' },
  '.pdf': { label: 'PDF', language: 'plaintext', icon: '📕' },
  '.csv': { label: 'CSV', language: 'plaintext', icon: '📊' },
  '.yaml': { label: 'YAML', language: 'yaml', icon: '⚙️' },
  '.yml': { label: 'YAML', language: 'yaml', icon: '⚙️' },
  '.log': { label: 'Log', language: 'plaintext', icon: '📃' },
};

function getLanguageForExt(ext) {
  return FILE_TYPE_MAP[ext]?.language || 'plaintext';
}

function getFileTypeInfo(ext) {
  return FILE_TYPE_MAP[ext] || { label: 'Unknown', language: 'plaintext', icon: '📄' };
}

// ═══════════════════════════════════════════════════════════════════════
// MAIN COMPONENT — DOCUMENT EDITOR & CREATOR
// ═══════════════════════════════════════════════════════════════════════

export default function DocumentsTab({ backendUrl, sharedContent, setSharedContent, sharedActiveDoc, setSharedActiveDoc, onSwitchToScreenwriting }) {
  const baseUrl = backendUrl || 'http://127.0.0.1:8000';

  // Shared Document State
  const activeDoc = sharedActiveDoc;
  const setActiveDoc = setSharedActiveDoc;
  const content = sharedContent;
  const setContent = setSharedContent;
  const [loading, setLoading] = useState(false);

  // ── Adaptation & Conversion State ──
  const [showAdaptModal, setShowAdaptModal] = useState(false);
  const [adaptProjectName, setAdaptProjectName] = useState('');
  const [adaptBookStyle, setAdaptBookStyle] = useState('Fiction Novel / Narrative');
  const [adaptType, setAdaptType] = useState('Feature Film (Spec Script)');
  const [isAdapting, setIsAdapting] = useState(false);

  // ── UI state ──
  const [showFileTree, setShowFileTree] = useState(true);
  const [docCanvasMode, setDocCanvasMode] = useState('paper'); // 'paper' (Word/Docs White Sheet) | 'code' (Monaco IDE)
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [error, setError] = useState(null);
  const [showNewDocModal, setShowNewDocModal] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);

  // ── Signature Canvas State ──
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);

  const startDrawing = (e) => {
    const { offsetX, offsetY } = e.nativeEvent;
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#e8e8f0";
    ctx.beginPath();
    ctx.moveTo(offsetX, offsetY);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const { offsetX, offsetY } = e.nativeEvent;
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineTo(offsetX, offsetY);
    ctx.stroke();
  };

  const stopDrawing = () => {
    if (isDrawing) {
      const ctx = canvasRef.current.getContext("2d");
      ctx.closePath();
      setIsDrawing(false);
    }
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };


  const [fileTree, setFileTree] = useState([]);
  const [showTemplates, setShowTemplates] = useState(false);
  const [recentFiles, setRecentFiles] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('ai-bs-recent-files')) || [];
      return stored.filter(f => f && f !== 'undefined');
    } catch { return []; }
  });
  const [zoom, setZoom] = useState(100);
  const [viewMode, setViewMode] = useState('editor'); // 'editor' | 'preview' | 'split'
  const [showProperties, setShowProperties] = useState(false);

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: SPRINT TRACKER (Chronometric Writing Timer)
  // ═══════════════════════════════════════════════════════════════════
  const [sprintActive, setSprintActive] = useState(false);
  const [sprintPaused, setSprintPaused] = useState(false);
  const [sprintElapsed, setSprintElapsed] = useState(0); // seconds
  const [sprintWords, setSprintWords] = useState(0);
  const [sprintPages, setSprintPages] = useState(0);
  const [sprintStartTime, setSprintStartTime] = useState(null);
  const sprintTimerRef = useRef(null);

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: TYPEWRITER VIEW (Active Line Centering)
  // ═══════════════════════════════════════════════════════════════════
  const [typewriterView, setTypewriterView] = useState(false);
  const editorContainerRef = useRef(null);

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: GOAL TRACKING (Writing Milestones)
  // ═══════════════════════════════════════════════════════════════════
  const [showGoals, setShowGoals] = useState(false);
  const [goals, setGoals] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('ai-bs-writing-goals') || '[]');
    } catch { return []; }
  });
  const [dailyGoal, setDailyGoal] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('ai-bs-daily-goal') || '{"pages":1,"date":""}');
      const today = new Date().toISOString().slice(0, 10);
      return saved.date === today ? saved.pages : 1;
    } catch { return 1; }
  });

  // ── Sprint Tracker Logic ──
  useEffect(() => {
    if (sprintActive && !sprintPaused) {
      sprintTimerRef.current = setInterval(() => {
        setSprintElapsed((prev) => prev + 1);
      }, 1000);
    }
    return () => { if (sprintTimerRef.current) clearInterval(sprintTimerRef.current); };
  }, [sprintActive, sprintPaused]);

  // Track word count changes
  useEffect(() => {
    if (content) {
      const words = content.trim().split(/\s+/).filter((w) => w.length > 0).length;
      setSprintWords(words);
    }
  }, [content]);

  // Track page count (~500 words per screenplay page)
  useEffect(() => {
    if (content) {
      const pages = Math.max(1, Math.ceil(content.trim().split(/\s+/).filter((w) => w.length > 0).length / 250));
      setSprintPages(pages);
    }
  }, [content]);

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const startSprint = () => {
    setSprintActive(true);
    setSprintPaused(false);
    setSprintElapsed(0);
    setSprintStartTime(Date.now());
  };

  const pauseSprint = () => setSprintPaused(true);
  const resumeSprint = () => setSprintPaused(false);
  const stopSprint = () => {
    setSprintActive(false);
    setSprintPaused(false);
    if (sprintTimerRef.current) clearInterval(sprintTimerRef.current);
  };

  // ── Typewriter View Logic ──
  useEffect(() => {
    if (typewriterView && editorContainerRef.current) {
      const container = editorContainerRef.current;
      const scrollHeight = container.scrollHeight;
      const clientHeight = container.clientHeight;
      container.scrollTop = (scrollHeight - clientHeight) / 2;
    }
  }, [typewriterView, content]);

  // ── Goal Tracking Logic ──
  useEffect(() => {
    localStorage.setItem('ai-bs-writing-goals', JSON.stringify(goals));
  }, [goals]);

  const addGoal = (targetPages) => {
    const newGoal = {
      id: Date.now(),
      target: targetPages,
      current: 0,
      completed: false,
      createdAt: new Date().toISOString(),
    };
    setGoals((prev) => [...prev, newGoal]);
  };

  const completeGoal = (goalId) => {
    setGoals((prev) => prev.map((g) => g.id === goalId ? { ...g, completed: true } : g));
  };

  const deleteGoal = (goalId) => {
    setGoals((prev) => prev.filter((g) => g.id !== goalId));
  };

  // ── File tree refresh ──
  const refreshFileTree = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/api/tree`);
      if (res.ok) {
        const data = await res.json();
        setFileTree(data.files || []);
      }
    } catch { /* tree unavailable */ }
  }, []);

  useEffect(() => { refreshFileTree(); }, [refreshFileTree]);

  // ── Load file from backend ──
  const loadFile = useCallback(async (filePath) => {
    setLoading(true);
    setError('');
    try {
      const ext = filePath.split('.').pop().toLowerCase();
      
      if (ext === 'pdf') {
        setActiveDoc({
          name: filePath.split('/').pop().split('\\').pop(),
          path: filePath,
          ext,
          isPdf: true,
          created: new Date().toISOString(),
          modified: new Date().toISOString(),
        });
        setContent('');
        setViewMode('editor');
      } else {
        const res = await fetch(`${baseUrl}/api/read?filepath=${encodeURIComponent(filePath)}`);
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();

        setActiveDoc({
          name: filePath.split('/').pop().split('\\').pop(),
          path: filePath,
          ext,
          isPdf: false,
          created: new Date().toISOString(),
          modified: new Date().toISOString(),
        });
        setContent(data.content);
        setViewMode('editor');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Create new document from template ──
  const createDocument = useCallback((template) => {
    const timestamp = new Date().toISOString().slice(0, 10);
    const name = `untitled${template.ext}`;
    const path = `E:/AI-BS/Documents/${name}`;

    setActiveDoc({
      name,
      path,
      ext: template.ext.slice(1),
      created: new Date().toISOString(),
      modified: new Date().toISOString(),
    });
    setContent(template.content);
    setShowNewDocModal(false);
    setViewMode('editor');
  }, []);

  const [autoSaveStatus, setAutoSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'error'
  const [lastSavedTime, setLastSavedTime] = useState(null);
  const autoSaveTimerRef = useRef(null);

  const saveFile = useCallback(async () => {
    if (!activeDoc) return;
    setAutoSaveStatus('saving');
    try {
      const res = await fetch(`${baseUrl}/api/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: activeDoc.path, content }),
      });
      if (!res.ok) throw new Error('Save failed');

      setActiveDoc((prev) => ({ ...prev, modified: new Date().toISOString() }));
      setAutoSaveStatus('saved');
      setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      setUnsavedChanges(false);
    } catch (err) {
      setError(`Save failed: ${err.message}`);
      setAutoSaveStatus('error');
    }
  }, [activeDoc, content, baseUrl]);

  // 💾 Automated Continuous Auto-Save for Admins (1500ms debounced)
  useEffect(() => {
    if (!activeDoc || !content || activeDoc.isPdf) return;

    // 1. Immediate client snapshot backup
    try {
      const docKey = activeDoc.path || activeDoc.name;
      localStorage.setItem(`aibs_doc_backup_${docKey}`, content);
      localStorage.setItem(`aibs_doc_backup_time_${docKey}`, String(Date.now()));
    } catch {}

    // 2. Debounced save to backend
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setAutoSaveStatus('saving');

    autoSaveTimerRef.current = setTimeout(async () => {
      await saveFile();
    }, 1500);

    return () => {
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  }, [content, activeDoc, saveFile]);

  // ── Convert PDF ──
  const convertPdf = useCallback(async () => {
    if (!activeDoc || !activeDoc.isPdf) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${baseUrl}/api/convert-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: activeDoc.path }),
      });
      if (!res.ok) throw new Error('Conversion failed');
      const data = await res.json();
      await refreshFileTree();
      await loadFile(data.new_filepath);
    } catch (err) {
      setError(`Convert failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [activeDoc, refreshFileTree, loadFile]);

  // ── Convert & Adapt to Hollywood Screenplay ──
  const handleStartAdaptation = async () => {
    if (!adaptProjectName.trim()) {
      alert("Please specify a project name.");
      return;
    }
    setIsAdapting(true);
    try {
      let res;
      if (activeDoc?.rawFile) {
        const formData = new FormData();
        formData.append('file', activeDoc.rawFile);
        formData.append('project_name', adaptProjectName);
        formData.append('adaptation_type', adaptType);
        formData.append('book_style', adaptBookStyle);
        res = await fetch(`${baseUrl}/api/screenplay/adapt`, {
          method: 'POST',
          body: formData,
        });
      } else {
        res = await fetch(`${baseUrl}/api/screenplay/adapt/text`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_name: adaptProjectName,
            content: content,
            adaptation_type: adaptType,
            book_style: adaptBookStyle
          }),
        });
      }

      const data = await res.json();
      if (data.status === 'success') {
        setShowAdaptModal(false);
        // Immediately transition the writer to the Screenwriting tab!
        if (onSwitchToScreenwriting) {
          onSwitchToScreenwriting(content, adaptProjectName);
        }
      } else if (res.status === 409 || data.status === 'processing') {
        const forceRestart = confirm(
          `An adaptation job is already in progress for "${adaptProjectName}".\n\n` +
          `• Click OK to FORCE RESTART from the beginning.\n` +
          `• Click Cancel to attach to the live job and open the Screenwriting Editor.`
        );
        if (forceRestart) {
          // Send with force: true
          if (activeDoc?.rawFile) {
            const formData = new FormData();
            formData.append('file', activeDoc.rawFile);
            formData.append('project_name', adaptProjectName);
            formData.append('adaptation_type', adaptType);
            formData.append('book_style', adaptBookStyle);
            formData.append('force', 'true');
            await fetch(`${baseUrl}/api/screenplay/adapt`, { method: 'POST', body: formData });
          } else {
            await fetch(`${baseUrl}/api/screenplay/adapt/text`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                project_name: adaptProjectName,
                content: content,
                adaptation_type: adaptType,
                book_style: adaptBookStyle,
                force: true
              }),
            });
          }
        }
        setShowAdaptModal(false);
        if (onSwitchToScreenwriting) {
          onSwitchToScreenwriting(content, adaptProjectName);
        }
      } else {
        alert(`Adaptation notice: ${data.message || 'Unknown response'}`);
      }
    } catch (err) {
      console.error("Adaptation error:", err);
      alert(`Adaptation error: ${err.message}`);
    } finally {
      setIsAdapting(false);
    }
  };

  // ── Save As ──
  const saveAs = useCallback(() => {
    if (!activeDoc) return;
    const newName = prompt('Save as:', activeDoc.name);
    if (!newName) return;

    const ext = newName.split('.').pop();
    const newPath = `E:/AI-BS/Documents/${newName}`;

    setActiveDoc((prev) => ({ ...prev, name: newName, path: newName, ext: `.${ext}` }));
    saveFile();
  }, [activeDoc, saveFile]);

  // ── Sign & File ──
  const signDocument = useCallback(() => {
    if (!activeDoc) return;
    setShowSignModal(true);
    // We clear it after it opens, using a small timeout so the DOM has the canvas.
    setTimeout(clearCanvas, 100);
  }, [activeDoc]);

  const submitSignature = useCallback(async (includeGraphic) => {
    if (!activeDoc) return;
    try {
      let signature_image = null;
      if (includeGraphic && canvasRef.current) {
        signature_image = canvasRef.current.toDataURL('image/png');
      }

      setShowSignModal(false);

      const res = await fetch(`${baseUrl}/api/documents/sign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          filename: activeDoc.name, 
          content,
          signature_image: signature_image 
        }),
      });
      if (!res.ok) throw new Error('Signing failed');
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${activeDoc.name.split('.')[0]}_signed.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      alert("Document cryptographically signed and securely filed in vault!");
    } catch (err) {
      setError(`Signing failed: ${err.message}`);
    }
  }, [activeDoc, content]);

  // ── File Tree Management ──
  const deleteFile = useCallback(() => {
    if (!activeDoc) return;
    if (!confirm(`Delete "${activeDoc.name}"?`)) return;

    setActiveDoc(null);
    setContent('');
    refreshFileTree();
  }, [activeDoc, refreshFileTree]);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveFile();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        setShowNewDocModal(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [saveFile]);

  // ── Render file tree ──
  const renderFileTree = (files, depth = 0) => {
    if (!Array.isArray(files)) return null;
    return files.map((item) => (
      <div key={item.path} style={{ marginLeft: depth * 16 }}>
        {item.type === 'directory' ? (
          <>
            <div style={{ padding: '4px 8px', cursor: 'pointer', color: '#58a6ff', fontSize: 12, borderRadius: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              📁 {item.name}
            </div>
            {renderFileTree(item.children || [], depth + 1)}
          </>
        ) : (
          <div onClick={() => loadFile(item.path)} style={{
            padding: '3px 8px', cursor: 'pointer', color: '#c9d1d9', fontSize: 12,
            borderRadius: 4, display: 'flex', alignItems: 'center', gap: 6,
            opacity: activeDoc?.path === item.path ? 0.8 : 1,
          }}>
            {getFileTypeInfo(item.name.split('.').pop())?.icon || '📄'} {item.name}
          </div>
        )}
      </div>
    ));
  };

  // ═══════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0a0a0f' }}>
      {/* ── Top Bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 16px', background: '#1a1a2e', borderBottom: '1px solid #2a2a3e',
        fontSize: 12, color: '#8b949e',
      }}>
        <span style={{ fontWeight: 700, color: '#58a6ff' }}>📂 Document Editor & Creator</span>
        <span>{activeDoc ? activeDoc.name : 'No document open'}</span>
      </div>

      {/* ── Live AI Adaptation Status & Progress Bar ── */}
      <AdaptationStatusBar 
        backendUrl={baseUrl}
        onSwitchToProject={(proj) => {
          if (onSwitchToScreenwriting) onSwitchToScreenwriting(undefined, proj);
        }}
      />

      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
        background: '#12121e', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap',
      }}>
        {/* Create */}
        <button onClick={() => setShowNewDocModal(true)} style={{
          padding: '6px 14px', fontSize: 12, fontWeight: 600, border: '1px solid #238636',
          borderRadius: 6, background: '#238636', color: '#fff', cursor: 'pointer',
        }}>+ New Document</button>

        {/* Open / Import Multi-Format */}
        <button onClick={() => document.getElementById('file-input')?.click()} style={{
          padding: '6px 14px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 6,
          background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4
        }}>📂 Open (.pdf, .docx, .epub, .fdx, etc.)</button>
        <input 
          id="file-input" 
          type="file" 
          accept=".pdf,.docx,.doc,.epub,.txt,.rtf,.md,.markdown,.fountain,.fdx,.json,.csv,.yaml,.yml,.py,.html,.css" 
          style={{ display: 'none' }} 
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const ext = file.name.split('.').pop()?.toLowerCase() || 'txt';
            const isPdf = ext === 'pdf';
            const isWordDoc = ext === 'docx' || ext === 'doc';

            if (isPdf) {
              const pdfBlobUrl = URL.createObjectURL(file);
              setActiveDoc({
                path: `C:/Users/footb/AI-BS_Matrix/${file.name}`,
                name: file.name,
                ext: 'pdf',
                isPdf: true,
                pdfBlobUrl: pdfBlobUrl,
                rawFile: file,
                created: new Date().toISOString(),
                modified: new Date().toISOString(),
              });
              setContent('');
              setViewMode('editor');
            } else if (isWordDoc) {
              try {
                const formData = new FormData();
                formData.append('file', file);
                const res = await fetch(`${baseUrl}/api/documents/import_docx`, {
                  method: 'POST',
                  body: formData
                });
                if (res.ok) {
                  const data = await res.json();
                  setActiveDoc({
                    path: `C:/Users/footb/AI-BS_Matrix/${file.name}`,
                    name: file.name,
                    ext: 'docx',
                    isPdf: false,
                    rawFile: file,
                    created: new Date().toISOString(),
                    modified: new Date().toISOString(),
                  });
                  setContent(data.content || '');
                  setDocCanvasMode('paper');
                  setError('');
                } else {
                  throw new Error('Could not parse Word document');
                }
              } catch (err) {
                setError(`Failed to read Word document: ${err.message}`);
              }
            } else {
              try {
                const text = await file.text();
                setActiveDoc({
                  path: `C:/Users/footb/AI-BS_Matrix/${file.name}`,
                  name: file.name,
                  ext: ext,
                  isPdf: false,
                  rawFile: file,
                  created: new Date().toISOString(),
                  modified: new Date().toISOString(),
                });
                setContent(text);
                setError('');
              } catch (err) {
                setError(`Failed to read file: ${err.message}`);
              }
            }
          }} 
        />

        {/* Save & Adapt */}
        {activeDoc && (
          <>
            {activeDoc.isPdf ? (
              <button onClick={convertPdf} style={{
                padding: '6px 14px', fontSize: 12, border: '1px solid #d29922', borderRadius: 6,
                background: '#d2992222', color: '#d29922', cursor: 'pointer', fontWeight: 600,
              }}>🔄 Convert to Text</button>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(22, 27, 34, 0.9)', border: '1px solid #30363d', padding: '4px 10px', borderRadius: 6, fontSize: 11 }}>
                  <span style={{ fontSize: 9 }}>
                    {autoSaveStatus === 'saving' ? '🟡' : autoSaveStatus === 'error' ? '🔴' : '🟢'}
                  </span>
                  <span style={{ color: autoSaveStatus === 'error' ? '#f85149' : (autoSaveStatus === 'saving' ? '#d29922' : '#58a6ff'), fontWeight: 600 }}>
                    {autoSaveStatus === 'saving' ? 'Saving...' : autoSaveStatus === 'error' ? 'Autosave Failed' : `Autosaved ${lastSavedTime ? lastSavedTime : ''}`}
                  </span>
                </div>
                <button onClick={saveFile} style={{
                  padding: '6px 14px', fontSize: 12, border: '1px solid #58a6ff', borderRadius: 6,
                  background: '#1f6feb22', color: '#58a6ff', cursor: 'pointer', fontWeight: 600,
                }}>💾 Save</button>
                <button onClick={saveAs} style={{
                  padding: '6px 14px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 6,
                  background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
                }}>Save As</button>
              </>
            )}
            
            {/* Adapt & Send to Screenplay Editor */}
            <button 
              onClick={() => {
                setAdaptProjectName(activeDoc?.name?.replace(/\.[^/.]+$/, "") || "Document Adaptation");
                setShowAdaptModal(true);
              }}
              style={{
                padding: '6px 14px', fontSize: 12, border: '1px solid #facc15', borderRadius: 6,
                background: '#facc1522', color: '#facc15', cursor: 'pointer', fontWeight: 700,
                display: 'flex', alignItems: 'center', gap: 6
              }}
              title="Convert this document/book into a Hollywood screenplay"
            >
              🎬 Adapt & Send to Screenplay Editor
            </button>

            <button onClick={signDocument} style={{
              padding: '6px 14px', fontSize: 12, border: '1px solid #2ea043', borderRadius: 6,
              background: '#2ea04322', color: '#2ea043', cursor: 'pointer', fontWeight: 600,
            }}>🖋️ Sign & File</button>
            <button onClick={deleteFile} style={{
              padding: '6px 14px', fontSize: 12, border: '1px solid #f8514966', borderRadius: 6,
              background: '#da363322', color: '#f85149', cursor: 'pointer',
            }}>🗑️ Delete</button>
          </>
        )}

        <div style={{ width: 1, height: 24, background: '#3a3a4e', margin: '0 8px' }} />

        {/* View modes */}
        <span style={{ fontSize: 10, color: '#8b949e', marginRight: 4 }}>VIEW:</span>
        {['editor', 'split', 'preview'].map((mode) => (
          <button key={mode} onClick={() => setViewMode(mode)} style={{
            padding: '4px 10px', fontSize: 11, border: viewMode === mode ? '1px solid #58a6ff' : '1px solid #3a3a4e',
            borderRadius: 4, background: viewMode === mode ? '#1f6feb22' : '#1c1c2e',
            color: viewMode === mode ? '#58a6ff' : '#c9d1d9', cursor: 'pointer', textTransform: 'capitalize',
          }}>{mode}</button>
        ))}

        {/* Sprint Tracker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
          <span style={{ fontSize: 12, color: '#8b949e', minWidth: 60 }}>⏱️</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#58a6ff' }}>{formatTime(sprintElapsed)}</span>
          <div style={{ display: 'flex', gap: 4, marginLeft: 12 }}>
            <button onClick={() => startSprint()} disabled={sprintActive} style={{ padding: '4px 10px', fontSize: 11, border: sprintActive ? '1px solid #58a6ff' : '1px solid #3a3a4e', borderRadius: 4, background: sprintActive ? '#238636' : '#1c1c2e', color: sprintActive ? '#fff' : '#c9d1d9', cursor: 'pointer', opacity: sprintActive ? 0.7 : 1 }}>Start</button>
            <button onClick={() => pauseSprint()} disabled={!sprintActive} style={{ padding: '4px 10px', fontSize: 11, border: !sprintActive ? '1px solid #3a3a4e' : '1px solid #58a6ff', borderRadius: 4, background: !sprintActive ? '#1c1c2e' : '#f9b700', color: !sprintActive ? '#c9d1d9' : '#fff', cursor: 'pointer', opacity: !sprintActive ? 1 : 0.7 }}>Pause</button>
            <button onClick={() => resumeSprint()} disabled={!sprintPaused} style={{ padding: '4px 10px', fontSize: 11, border: !sprintPaused ? '1px solid #3a3a4e' : '1px solid #58a6ff', borderRadius: 4, background: !sprintPaused ? '#1c1c2e' : '#238636', color: !sprintPaused ? '#c9d1d9' : '#fff', cursor: 'pointer', opacity: !sprintPaused ? 1 : 0.7 }}>Resume</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 24, marginTop: 8, fontSize: 11, color: '#8b949e' }}>
            <span>Words: {sprintWords}</span>
            <span>Pages: {sprintPages}</span>
        </div>

        {/* Zoom */}
        <span style={{ fontSize: 10, color: '#8b949e', marginLeft: 8 }}>Zoom:</span>
        <button onClick={() => setZoom((z) => Math.max(50, z - 10))} style={{
          padding: '2px 8px', fontSize: 11, border: '1px solid #3a3a4e', borderRadius: 4,
          background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
        }}>−</button>
        <span style={{ fontSize: 11, color: '#c9d1d9', minWidth: 32, textAlign: 'center' }}>{zoom}%</span>
        <button onClick={() => setZoom((z) => Math.min(200, z + 10))} style={{
          padding: '2px 8px', fontSize: 11, border: '1px solid #3a3a4e', borderRadius: 4,
          background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
        }}>+</button>
      </div>

      {/* ── Error Display ── */}
      {error && (
        <div style={{ padding: '8px 16px', background: '#da363322', border: '1px solid #f8514966', color: '#f85149', fontSize: 12 }}>
          {error}
        </div>
      )}

      {/* ── Main Content ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* File Tree */}
        {showFileTree && (
          <div style={{
            width: 240, background: '#161b22', borderRight: '1px solid #2a2a3e',
            overflow: 'auto', display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1 }}>
              📂 Explorer
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
              {renderFileTree(fileTree)}
            </div>

            {/* Recent files */}
            {recentFiles.length > 0 && (
              <div style={{ borderTop: '1px solid #2a2a3e', padding: '12px 16px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Recent</div>
                {recentFiles.slice(0, 5).map((f, idx) => (
                  <div key={idx} onClick={() => loadFile(f)} style={{
                    padding: '3px 8px', cursor: 'pointer', color: '#c9d1d9', fontSize: 11, borderRadius: 4,
                  }}>📄 {f.split('/').pop()}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Editor / Preview Area */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Editor Panel */}
          {(viewMode === 'editor' || viewMode === 'split') && (
            <div style={{
              flex: viewMode === 'split' ? '50%' : '100%',
              minWidth: 200, position: 'relative', background: '#0d1117',
            }}>
              {activeDoc ? (
                activeDoc.isPdf ? (
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: '#1e1e2e' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', background: '#161b22', borderBottom: '1px solid #30363d' }}>
                      <span style={{ color: '#facc15', fontSize: '0.85rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        📕 PDF Document Viewer: {activeDoc.name}
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={convertPdf} style={{ background: '#d2992222', border: '1px solid #d29922', color: '#d29922', padding: '4px 10px', borderRadius: '4px', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 'bold' }}>
                          🔄 Extract to Text
                        </button>
                        <button 
                          onClick={() => {
                            setAdaptProjectName(activeDoc?.name?.replace(/\.[^/.]+$/, "") || "PDF Adaptation");
                            setShowAdaptModal(true);
                          }}
                          style={{ background: '#facc15', color: '#000', border: 'none', padding: '4px 12px', borderRadius: '4px', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 'bold' }}
                        >
                          🎬 Adapt to Screenplay
                        </button>
                      </div>
                    </div>
                    <iframe 
                      src={activeDoc.pdfBlobUrl || `${baseUrl}/api/serve-file?filepath=${encodeURIComponent(activeDoc.path)}`}
                      width="100%" 
                      height="100%" 
                      style={{ border: 'none', background: '#525659', flex: 1 }}
                      title="PDF Viewer"
                    />
                  </div>
                ) : docCanvasMode === 'paper' ? (
                  <WordDocsPaperCanvas
                    value={content}
                    onChange={setContent}
                    filename={activeDoc.name}
                    onSave={saveFile}
                    autoSaveStatus={autoSaveStatus}
                    lastSavedTime={lastSavedTime}
                    extraHeaderActions={
                      <button
                        onClick={() => setDocCanvasMode('code')}
                        style={{
                          background: 'transparent',
                          border: '1px solid #cbd5e1',
                          color: '#64748b',
                          fontSize: '0.75rem',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                        title="Switch to Raw Monaco Code IDE Mode"
                      >
                        ⌨️ Code IDE Mode
                      </button>
                    }
                  />
                ) : (
                  <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ padding: '4px 12px', background: '#161b22', borderBottom: '1px solid #30363d', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>Monaco Code IDE Active</span>
                      <button
                        onClick={() => setDocCanvasMode('paper')}
                        style={{
                          background: '#2563eb',
                          border: 'none',
                          color: '#fff',
                          fontSize: '0.75rem',
                          padding: '4px 10px',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontWeight: 'bold'
                        }}
                      >
                        📄 Switch to Word/Docs Paper View
                      </button>
                    </div>
                    <div style={{ flex: 1 }}>
                      <MonacoEditor
                        value={content}
                        language={getLanguageForExt(activeDoc.ext)}
                        theme="vs-dark"
                        onChange={setContent}
                        options={{
                          fontSize: 13,
                          fontFamily: "'JetBrains Mono', Consolas, monospace",
                          minimap: { enabled: viewMode === 'editor' },
                          scrollBeyondLastLine: false,
                          renderWhitespace: 'selection',
                          lineNumbers: showProperties ? 'on' : 'off',
                        }}
                      />
                    </div>
                  </div>
                )
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#484f58' }}>
                  <div style={{ fontSize: 64, marginBottom: 24 }}>📄</div>
                  <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No document open</div>
                  <button onClick={() => setShowNewDocModal(true)} style={{
                    padding: '10px 24px', fontSize: 13, border: '1px solid #58a6ff', borderRadius: 8,
                    background: '#1f6feb22', color: '#58a6ff', cursor: 'pointer', fontWeight: 600,
                  }}>+ Create New Document</button>
                </div>
              )}
            </div>
          )}

          {/* Resizer */}
          {viewMode === 'split' && (
            <div style={{ width: 4, cursor: 'col-resize', background: '#21262d' }} />
          )}

          {/* Preview Panel */}
          {(viewMode === 'preview' || viewMode === 'split') && (
            <div style={{
              flex: viewMode === 'split' ? '50%' : '100%',
              minWidth: 200, overflow: 'auto', background: '#0d1117',
            }}>
              <div style={{ padding: '8px 16px', borderBottom: '1px solid #2a2a3e', fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1 }}>
                Preview — {activeDoc ? getFileTypeInfo(activeDoc.ext)?.label : '—'}
              </div>
              <div style={{ padding: 20 }}>
                {activeDoc ? (
                  activeDoc.ext === '.md' ? (
                    <div dangerouslySetInnerHTML={{ __html: content }} style={{ color: '#c9d1d9', lineHeight: 1.6 }} />
                  ) : (
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: "'JetBrains Mono', Consolas, monospace", fontSize: 12, lineHeight: 1.5, color: '#c9d1d9' }}>
                      {content}
                    </pre>
                  )
                ) : (
                  <p style={{ color: '#4b5563', fontStyle: 'italic' }}>Open a document to preview</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Properties Panel */}
        {showProperties && activeDoc && (
          <div style={{
            width: 240, background: '#161b22', borderLeft: '1px solid #2a2a3e',
            overflow: 'auto', padding: 16,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>📋 Document Properties</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Name</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{activeDoc.name}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Path</label>
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4, fontFamily: 'monospace', wordBreak: 'break-all' }}>{activeDoc.path}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Type</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{getFileTypeInfo(activeDoc.ext)?.label}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Size</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{(content.length / 1024).toFixed(1)} KB</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Lines</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{content.split('\n').length}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Created</label>
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4 }}>{new Date(activeDoc.created).toLocaleString()}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Modified</label>
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4 }}>{new Date(activeDoc.modified).toLocaleString()}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Status Bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '4px 16px', background: '#161b22', borderTop: '1px solid #2a2a3e',
        fontSize: 11, color: '#8b949e',
      }}>
        <span>
          {activeDoc ? `${activeDoc.name} • ${getFileTypeInfo(activeDoc.ext)?.label}` : 'Ready — press Ctrl+N to create a new document'}
        </span>
        <span>Ctrl+S Save • Ctrl+N New • Ctrl+B Toggle Tree</span>
      </div>

      {/* ── New Document Modal ── */}
      {showNewDocModal && (
        <div style={{
          position: 'fixed', inset: 0, background: '#000000cc', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 3000,
        }} onClick={() => setShowNewDocModal(false)}>
          <div style={{
            background: '#1c1c2e', border: '1px solid #3a3a4e', borderRadius: 16,
            boxShadow: '0 16px 64px rgba(0,0,0,0.8)', width: 700, maxHeight: '80vh', overflow: 'auto',
          }} onClick={(e) => e.stopPropagation()}>
            {/* Modal header */}
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #2a2a3e' }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#e8e8f0' }}>Create New Document</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#8b949e' }}>Choose a template to get started</p>
            </div>

            {/* Template grid */}
            <div style={{ padding: 24, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              {TEMPLATES.map((template) => (
                <button key={template.id} onClick={() => createDocument(template)} style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                  padding: 20, border: '1px solid #3a3a4e', borderRadius: 12,
                  background: '#0d1117', color: '#c9d1d9', cursor: 'pointer',
                  transition: 'all 0.15s ease', textAlign: 'center',
                }}>
                  <span style={{ fontSize: 36 }}>{template.icon}</span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{template.label}</span>
                  <span style={{ fontSize: 11, color: '#8b949e' }}>{template.description}</span>
                  <span style={{ fontSize: 10, color: '#58a6ff', fontFamily: 'monospace' }}>{template.ext}</span>
                </button>
              ))}
            </div>

            {/* Modal footer */}
            <div style={{ padding: '12px 24px', borderTop: '1px solid #2a2a3e', display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowNewDocModal(false)} style={{
                padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
              }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Signature Modal */}
      {showSignModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          backdropFilter: 'blur(4px)'
        }}>
          <div style={{
            background: '#1c1c2e', border: '1px solid #3a3a4e', borderRadius: 16,
            width: 500, overflow: 'hidden', boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            display: 'flex', flexDirection: 'column'
          }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #2a2a3e' }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#e8e8f0' }}>Sign Document</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#8b949e' }}>Draw your signature below (optional)</p>
            </div>

            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <canvas 
                ref={canvasRef}
                width={400}
                height={200}
                onMouseDown={startDrawing}
                onMouseMove={draw}
                onMouseUp={stopDrawing}
                onMouseOut={stopDrawing}
                style={{ 
                  border: '1px solid #3a3a4e', 
                  borderRadius: 8, 
                  background: '#0d1117', 
                  cursor: 'crosshair',
                  touchAction: 'none'
                }}
              />
              <div style={{ width: '100%', display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                <button onClick={clearCanvas} style={{
                  background: 'none', border: 'none', color: '#58a6ff', fontSize: 12, cursor: 'pointer'
                }}>Clear Canvas</button>
              </div>
            </div>

            <div style={{ padding: '12px 24px', borderTop: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between' }}>
              <button onClick={() => setShowSignModal(false)} style={{
                padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
              }}>Cancel</button>
              
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={() => submitSignature(false)} style={{
                  padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                  background: '#232338', color: '#c9d1d9', cursor: 'pointer',
                }}>Skip & Cryptographic Sign</button>
                <button onClick={() => submitSignature(true)} style={{
                  padding: '8px 20px', fontSize: 12, border: 'none', borderRadius: 8,
                  background: '#238636', color: '#ffffff', cursor: 'pointer',
                }}>Approve & Sign</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Screenplay Adaptation & Conversion Modal ── */}
      {showAdaptModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 3000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(6px)'
        }}>
          <div style={{
            background: '#1f2937', border: '1px solid #374151', padding: '24px',
            borderRadius: '12px', width: '560px', maxWidth: '92vw',
            boxShadow: '0 16px 48px rgba(0,0,0,0.7)', color: '#fff'
          }}>
            <h3 style={{ color: '#facc15', marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem' }}>
              🎬 Adapt Book / Document to Hollywood Screenplay
            </h3>
            
            <p style={{ color: '#9ca3af', fontSize: '0.85rem', lineHeight: '1.4', marginBottom: '16px' }}>
              The AI-BS Matrix extracts dramatic actions, character arcs, and subtext from your manuscript, chunking and adapting it into a professional screenplay formatted to industry standards.
            </p>

            {/* Source Document Display */}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Source Document / Book:</label>
              <div style={{ color: '#38bdf8', fontSize: '0.85rem', padding: '8px 12px', background: '#111827', borderRadius: '6px', border: '1px solid #374151', display: 'flex', alignItems: 'center', gap: '6px' }}>
                📄 {activeDoc?.name || 'Current Studio Document'} {activeDoc?.isPdf ? '(PDF Document)' : ''}
              </div>
            </div>

            {/* Project Name */}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Screenplay Project Name:</label>
              <input 
                type="text" 
                value={adaptProjectName} 
                onChange={(e) => setAdaptProjectName(e.target.value)} 
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#fff', fontSize: '0.9rem', boxSizing: 'border-box' }} 
              />
            </div>

            {/* Book / Manuscript Style */}
            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>📖 Source Manuscript Style:</label>
              <select 
                value={adaptBookStyle} 
                onChange={(e) => setAdaptBookStyle(e.target.value)} 
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#facc15', fontSize: '0.9rem', boxSizing: 'border-box' }}
              >
                <option value="Fiction Novel / Narrative">📚 Fiction Novel / Sci-Fi / Fantasy / Thriller (Worldbuilding & Conflict)</option>
                <option value="Autobiography / Memoir / Biopic">📖 Autobiography / Memoir / Biopic (1st-Person V.O. & Flashbacks)</option>
                <option value="Non-Fiction / True Crime / Investigative">📰 Non-Fiction / True Crime / Investigative (Docudrama & Archival Cues)</option>
                <option value="Theatrical Stage Play / Drama">🏛️ Theatrical Drama / Stage Play (Acoustic Dialogues & Set Blocking)</option>
                <option value="Short Story / Flash Fiction">⚡ Short Story / Flash Fiction (Condensed Pacing & Sharp Climax)</option>
              </select>
            </div>

            {/* Target Hollywood Format */}
            <div style={{ marginBottom: '14px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>🎬 Target Screenplay Format:</label>
              <select 
                value={adaptType} 
                onChange={(e) => setAdaptType(e.target.value)} 
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#38bdf8', fontSize: '0.9rem', boxSizing: 'border-box' }}
              >
                <option value="Feature Film (Spec Script)">🎬 Feature Film (3-Act Hollywood Spec Script)</option>
                <option value="TV Pilot (1-Hour Drama)">📺 TV Pilot (1-Hour Network/Streaming Drama)</option>
                <option value="TV Pilot (30-Minute Comedy / Sitcom)">🎭 TV Pilot (30-Minute Comedy / Sitcom)</option>
                <option value="Limited / Mini-Series Episode">🎞️ Limited / Mini-Series Episodic Script</option>
                <option value="Director's Shooting Script (Camera & Lighting Cues)">🎥 Director's Shooting Script (Camera & Lighting Cues)</option>
                <option value="Theatrical Stage Play">🏛️ Theatrical Stage Play (Act/Scene & Stage Blocking)</option>
                <option value="Audio Drama / Scripted Podcast">🎙️ Audio Drama / Scripted Podcast (SFX & Spatial Audio)</option>
                <option value="Short Film">⚡ Short Film (10-15 Minute Condensed Arc)</option>
              </select>
            </div>

            {/* Dynamic Style Guidance Helper */}
            <div style={{ background: '#111827', border: '1px solid #374151', padding: '10px 14px', borderRadius: '6px', fontSize: '0.78rem', color: '#9ca3af', marginBottom: '20px', lineHeight: '1.4' }}>
              {adaptBookStyle.includes("Autobiography") && "📌 Converts 1st-person introspective prose reflections into intimate Voice-Over dialogue (V.O.) and flashback sequences with subjective visuals."}
              {adaptBookStyle.includes("Non-Fiction") && "📌 Applies docudrama precision with on-screen superimpositions (SUPER: Berlin, 1989), archival montage cues, and high-tension journalistic pacing."}
              {adaptBookStyle.includes("Theatrical") && "📌 Preserves dialogue musicality, extended character exchanges, and detailed stage directions."}
              {adaptBookStyle.includes("Short Story") && "📌 Strips extraneous subplots, plunging directly into the core crisis with a sharp visual reversal."}
              {(!adaptBookStyle.includes("Autobiography") && !adaptBookStyle.includes("Non-Fiction") && !adaptBookStyle.includes("Theatrical") && !adaptBookStyle.includes("Short Story")) && "📌 Translates dense worldbuilding, lore, and internal monologue into active visual scenes, physical blocking, and subtext dialogue."}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                onClick={() => setShowAdaptModal(false)} 
                disabled={isAdapting}
                style={{ background: 'transparent', border: '1px solid #555', color: '#fff', padding: '8px 16px', borderRadius: '6px', cursor: isAdapting ? 'not-allowed' : 'pointer' }}
              >
                Cancel
              </button>
              <button 
                onClick={handleStartAdaptation} 
                disabled={isAdapting}
                style={{ background: '#facc15', color: '#000', border: 'none', padding: '8px 18px', fontWeight: 'bold', borderRadius: '6px', cursor: isAdapting ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                {isAdapting ? '⏳ Starting Conversion...' : '🚀 Start Adaptation & Open Editor'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
