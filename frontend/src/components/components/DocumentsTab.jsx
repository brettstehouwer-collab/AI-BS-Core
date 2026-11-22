/** @typedef {{path: string, name?: string, ext?: string, isPdf?: boolean, isBinary?: boolean, isNew?: boolean, isRecovery?: boolean, isIntakeOriginal?: boolean, created?: string, modified?: string, rawFile?: File}} DocumentMetadata */
/** @typedef {{doc: DocumentMetadata | null, content: string}} DocumentSnapshot */
/** @typedef {(Partial<DocumentMetadata> & {path: string, implicit?: boolean}) | {implicit: boolean, path?: undefined}} DocumentDestination */
/** @typedef {{name: string, path: string, type: string, children?: DocumentTreeNode[]}} DocumentTreeNode */
/** @typedef {{id: number, target: number, current: number, completed: boolean, createdAt: string}} WritingGoal */
import { isDriveIntakeOriginal, createIntakeWorkingCopy } from '/src/utils/driveIntakeDocuments.js';
import { AuthenticatedDriveMedia, AuthenticatedDriveDownload } from '/src/components/AuthenticatedDriveMedia.jsx';
import { createDocumentDraftCoordinator, documentPathIdentity, isDocumentRevision, retainDocumentRecovery, listDocumentRecovery, documentRecoveryDraft } from '/src/utils/documentDraftSafety.js';
import { useState, useEffect, useCallback, useRef } from 'react';
import MonacoEditor from '@monaco-editor/react';
import AdaptationStatusBar from './AdaptationStatusBar.jsx';
import WordDocsPaperCanvas from './WordDocsPaperCanvas.jsx';
import './StudioLayout.css';

(import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000');

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

/** @type {Record<string, {label: string, language: string, icon: string}>} */
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
  '.fountain': { label: 'Fountain', language: 'plaintext', icon: '🎬' },
  '.docx': { label: 'Word document', language: 'plaintext', icon: '📘' },
  '.pdf': { label: 'PDF', language: 'plaintext', icon: '📕' },
  '.csv': { label: 'CSV', language: 'plaintext', icon: '📊' },
  '.yaml': { label: 'YAML', language: 'yaml', icon: '⚙️' },
  '.yml': { label: 'YAML', language: 'yaml', icon: '⚙️' },
  '.log': { label: 'Log', language: 'plaintext', icon: '📃' },
};

/** @param {string | undefined} ext */
function getLanguageForExt(ext) {
  return FILE_TYPE_MAP[ext || '']?.language || 'plaintext';
}

/** @param {string | undefined} ext */
function getFileTypeInfo(ext) {
  return FILE_TYPE_MAP[ext?.startsWith('.') ? ext : `.${ext}`] || { label: 'Unknown', language: 'plaintext', icon: '📄' };
}

// ═══════════════════════════════════════════════════════════════════════
// MAIN COMPONENT — DOCUMENT EDITOR & CREATOR
// ═══════════════════════════════════════════════════════════════════════

/** @param {{backendUrl?: string, sharedContent: string, setSharedContent: (value: string) => void, sharedActiveDoc: DocumentMetadata | null, setSharedActiveDoc: (doc: DocumentMetadata | null) => void, onSwitchToScreenwriting?: (content: string|undefined, projectName?: string) => void}} props */
export default function DocumentsTab({ backendUrl, sharedContent, setSharedContent, sharedActiveDoc, setSharedActiveDoc, onSwitchToScreenwriting }) {
  const baseUrl = backendUrl || 'http://127.0.0.1:8000';

  // Shared Document State
  const activeDoc = sharedActiveDoc;
  const setActiveDoc = setSharedActiveDoc;
  const content = sharedContent;
  const setContent = setSharedContent;
  const currentDocumentRef = useRef({ doc: activeDoc, content });
  const localEditGenerationRef = useRef(0);
  const documentIdentityRef = useRef(0);
  // External shared-state changes invalidate pending transitions too. Local
  // handlers update these refs synchronously before React schedules a render.
  if (currentDocumentRef.current.doc !== activeDoc || currentDocumentRef.current.content !== content) {
    if (currentDocumentRef.current.doc?.path !== activeDoc?.path) documentIdentityRef.current++;
    localEditGenerationRef.current++;
    currentDocumentRef.current = { doc: activeDoc, content };
  }
  const saveFileRef = useRef(/** @type {((destination?: DocumentDestination) => Promise<boolean>) | null} */ (null));
  const documentLoadSequenceRef = useRef(0);
  const documentWriteRef = useRef(/** @type {((payload: import("/types/domain").DocumentSavePayload) => Promise<import("/types/domain").DocumentSaveAck>) | null} */ (null));
  documentWriteRef.current = async (payload) => {
    const response = await fetch(`${baseUrl}/api/save`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : `HTTP ${response.status}`);
    return result;
  };
  const draftCoordinatorRef = useRef(/** @type {ReturnType<typeof createDocumentDraftCoordinator> | null} */ (null));
  if (!draftCoordinatorRef.current) draftCoordinatorRef.current = createDocumentDraftCoordinator({ write: payload => { const write = documentWriteRef.current; if (!write) throw new Error("Document writer unavailable."); return write(payload); } });
  const draftCoordinator = draftCoordinatorRef.current;
  const [loading, setLoading] = useState(false);

  // ── Adaptation & Conversion State ──
  const [showAdaptModal, setShowAdaptModal] = useState(false);
  const [adaptProjectName, setAdaptProjectName] = useState('');
  const [adaptBookStyle, setAdaptBookStyle] = useState('Fiction Novel / Narrative');
  const [adaptType, setAdaptType] = useState('Feature Film (Spec Script)');
  const [isAdapting, setIsAdapting] = useState(false);

  // ── UI state ──
  const [showFileTree, setShowFileTree] = useState(() => typeof window === 'undefined' || window.innerWidth > 900);
  const [docCanvasMode, setDocCanvasMode] = useState('paper'); // 'paper' (Word/Docs White Sheet) | 'code' (Monaco IDE)
  const [, setUnsavedChanges] = useState(false);
  const [error, setError] = useState(/** @type {string|null} */ (null));
  const [showNewDocModal, setShowNewDocModal] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);

  const [autoSaveStatus, setAutoSaveStatus] = useState('unsaved');
  const [lastSavedTime, setLastSavedTime] = useState(/** @type {string | null} */ (null));
  const autoSaveTimerRef = useRef(/** @type {ReturnType<typeof setTimeout> | null} */ (null));
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryCopies, setRecoveryCopies] = useState(/** @type {ReturnType<typeof listDocumentRecovery>} */ ([]));
  const [recoveryWarning, setRecoveryWarning] = useState('');
  const latestRecoveryRef = useRef(/** @type {{path: string, content: string} | null} */ (null));
  const recoveryTimerRef = useRef(/** @type {ReturnType<typeof setTimeout> | null} */ (null));
  const retainDraftRef = useRef(/** @type {((reason: string, snapshot?: DocumentSnapshot) => boolean) | null} */ (null));

  const refreshRecovery = useCallback(() => {
    try { setRecoveryCopies(listDocumentRecovery(localStorage)); }
    catch { setRecoveryWarning('Browser recovery storage is unavailable. Download your draft before leaving or reloading.'); }
  }, []);
  useEffect(() => { refreshRecovery(); }, [refreshRecovery]);

  const retainDraft = useCallback((/** @type {string} */ reason, snapshot = currentDocumentRef.current) => {
    if (!snapshot.doc || typeof snapshot.content !== 'string' || snapshot.doc.isPdf || snapshot.doc.isBinary) return true;
    if (reason === 'edit' && latestRecoveryRef.current?.path === snapshot.doc.path && latestRecoveryRef.current.content === snapshot.content) return true;
    try {
      retainDocumentRecovery(localStorage, { ...snapshot.doc, content: snapshot.content, reason });
      latestRecoveryRef.current = { path: snapshot.doc.path, content: snapshot.content };
      if (showRecovery) refreshRecovery();
      return true;
    } catch {
      setRecoveryWarning('Browser recovery storage failed. Download your draft now; reload is blocked until a copy can be retained.');
      return false;
    }
  }, [showRecovery, refreshRecovery]);
  retainDraftRef.current = retainDraft;

  // Coalesce typing bursts; full draft copies are immediate at mutation and
  // replacement boundaries, rather than one whole document per keystroke.
  useEffect(() => {
    if (!activeDoc || typeof content !== 'string' || activeDoc.isPdf || activeDoc.isBinary) return;
    recoveryTimerRef.current = setTimeout(() => retainDraftRef.current?.('edit'), 750);
    return () => clearTimeout(recoveryTimerRef.current ?? undefined);
  }, [content, activeDoc?.path]);
  useEffect(() => {
    const preserve = () => retainDraftRef.current?.('leaving Documents');
    window.addEventListener('beforeunload', preserve);
    window.addEventListener('pagehide', preserve);
    return () => {
      window.removeEventListener('beforeunload', preserve);
      window.removeEventListener('pagehide', preserve);
      clearTimeout(recoveryTimerRef.current ?? undefined);
      preserve();
    };
  }, []);

  const handleContentChange = useCallback((/** @type {unknown} */ value) => {
    const text = typeof value === 'string' ? value : '';
    localEditGenerationRef.current++;
    currentDocumentRef.current = { ...currentDocumentRef.current, content: text };
    setContent(text);
    setUnsavedChanges(true);
  }, [setContent]);

  const installDocument = useCallback((/** @type {DocumentMetadata | null} */ doc, /** @type {string} */ text) => {
    documentIdentityRef.current++;
    localEditGenerationRef.current++;
    ++documentLoadSequenceRef.current;
    currentDocumentRef.current = { doc, content: text };
    setActiveDoc(doc);
    setContent(text);
    setLoading(false);
    setLastSavedTime(null);
    const dirty = !!doc && !doc.isPdf && !doc.isBinary && draftCoordinator.isDirty(doc.path, text);
    setUnsavedChanges(dirty);
    setAutoSaveStatus(dirty ? 'unsaved' : 'saved');
  }, [setActiveDoc, setContent]);

  const beginDocumentTransition = () => ({ sequence: ++documentLoadSequenceRef.current, generation: localEditGenerationRef.current, identity: documentIdentityRef.current });
  const transitionIsCurrent = (/** @type {{sequence:number,generation:number,identity:number}} */ token) => token.sequence === documentLoadSequenceRef.current
    && token.generation === localEditGenerationRef.current && token.identity === documentIdentityRef.current;
  const cancelChangedTransition = (/** @type {{sequence:number,generation:number,identity:number}} */ token) => {
    if (token.sequence === documentLoadSequenceRef.current) {
      setError('Open cancelled because your draft changed while waiting. Your current edits are kept.');
      setLoading(false);
    }
  };

  const downloadRecoveryText = (/** @type {string} */ text, /** @type {string|undefined} */ name) => {
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = name || 'document-recovery.txt';
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };


  // ── Signature Canvas State ──
  const canvasRef = useRef(/** @type {HTMLCanvasElement | null} */ (null));
  const drawingPointerRef = useRef(/** @type {number | null} */ (null));
  const filingInFlightRef = useRef(false);
  const [isFiling, setIsFiling] = useState(false);

  /** @param {import("react").PointerEvent<HTMLCanvasElement>} e @returns {[number, number]} */
const signaturePosition = (e) => {
    const canvas = e.currentTarget;
    const bounds = canvas.getBoundingClientRect();
    return [(e.clientX - bounds.left) * canvas.width / bounds.width,
            (e.clientY - bounds.top) * canvas.height / bounds.height];
  };

  /** @param {import("react").PointerEvent<HTMLCanvasElement>} e */
const startDrawing = (e) => {
    if (isFiling || e.isPrimary === false) return;
    const canvas = e.currentTarget;
    canvas.setPointerCapture(e.pointerId);
    drawingPointerRef.current = e.pointerId;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#111111';
    ctx.beginPath();
    ctx.moveTo(...signaturePosition(e));
    e.preventDefault();
  };

  /** @param {import("react").PointerEvent<HTMLCanvasElement>} e */
const draw = (e) => {
    if (drawingPointerRef.current !== e.pointerId) return;
    const ctx = e.currentTarget.getContext('2d');
    if (!ctx) return;
    ctx.lineTo(...signaturePosition(e));
    ctx.stroke();
  };

  const stopDrawing = () => {
    if (drawingPointerRef.current !== null) {
      canvasRef.current?.getContext('2d')?.closePath();
      drawingPointerRef.current = null;
    }
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };


  const [fileTree, setFileTree] = useState(/** @type {DocumentTreeNode[]} */ ([]));
  useState(false);
  const [recentFiles] = useState(() => {
    try {
      const stored = /** @type {string[]} */ (JSON.parse(localStorage.getItem('ai-bs-recent-files') || '[]') || []);
      return stored.filter(f => f && f !== 'undefined');
    } catch { return []; }
  });
  const [zoom, setZoom] = useState(100);
  const [viewMode, setViewMode] = useState('editor'); // 'editor' | 'preview' | 'split'
  const [showProperties] = useState(false);

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: SPRINT TRACKER (Chronometric Writing Timer)
  // ═══════════════════════════════════════════════════════════════════
  const [sprintActive, setSprintActive] = useState(false);
  const [sprintPaused, setSprintPaused] = useState(false);
  const [sprintElapsed, setSprintElapsed] = useState(0); // seconds
  const [sprintWords, setSprintWords] = useState(0);
  const [sprintPages, setSprintPages] = useState(0);
  const [, setSprintStartTime] = useState(/** @type {number | null} */ (null));
  const sprintTimerRef = useRef(/** @type {ReturnType<typeof setTimeout> | null} */ (null));

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: TYPEWRITER VIEW (Active Line Centering)
  // ═══════════════════════════════════════════════════════════════════
  const [typewriterView] = useState(false);
  const editorContainerRef = useRef(/** @type {HTMLDivElement | null} */ (null));

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: GOAL TRACKING (Writing Milestones)
  // ═══════════════════════════════════════════════════════════════════
  useState(false);
  const [goals] = useState(() => {
    try {
      return /** @type {WritingGoal[]} */ (JSON.parse(localStorage.getItem('ai-bs-writing-goals') || '[]'));
    } catch { return []; }
  });
  useState(() => {
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
    if (activeDoc?.path && content) {
      const words = content.trim().split(/\s+/).filter((w) => w.length > 0).length;
      setSprintWords(words);
    } else setSprintWords(0);
  }, [content, activeDoc?.path]);

  // Document estimate only: 250 words/page, independent of screenplay layout.
  useEffect(() => {
    if (activeDoc?.path && content) {
      const pages = Math.max(1, Math.ceil(content.trim().split(/\s+/).filter((w) => w.length > 0).length / 250));
      setSprintPages(pages);
    } else setSprintPages(0);
  }, [content, activeDoc?.path]);

  /** @param {number} seconds */
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
    try { localStorage.setItem('ai-bs-writing-goals', JSON.stringify(goals)); }
    catch { setRecoveryWarning('Browser storage is unavailable. Download your draft before leaving or reloading.'); }
  }, [goals]);

  

  

  

  // ── File tree refresh ──
  const refreshFileTree = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/api/tree`);
      if (res.ok) {
        const data = await res.json();
        setFileTree(data.files || []);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || 'Unable to load documents. Check administrator sign-in.');
      }
    } catch { setError('The document service is unavailable.'); }
  }, [baseUrl]);

  useEffect(() => { refreshFileTree(); }, [refreshFileTree]);

  // ── Load file from backend ──
  /** @param {string} filePath @param {{reload?: boolean}} [options] */
const loadFile = useCallback(async (/** @type {string} */ filePath, { reload = false } = {}) => {
    const token = beginDocumentTransition(); // Includes edits made during the preceding save.
    setLoading(true); setError('');
    try {
      if (reload) {
        if (!retainDraft('before explicit reload')) { setLoading(false); return false; }
        await draftCoordinator.idle();
      } else if (saveFileRef.current && (await saveFileRef.current({ implicit: true })) === false) {
        if (token.sequence === documentLoadSequenceRef.current) setLoading(false);
        return false;
      }
      if (!transitionIsCurrent(token)) { cancelChangedTransition(token); return false; }
      const ext = (filePath.split('.').pop() || '').toLowerCase();
      const isIntakeOriginal = isDriveIntakeOriginal(filePath);
      const isBinary = ['docx', 'doc', 'odt', 'epub'].includes(ext);
      let path = filePath, text = '';
      if (ext !== 'pdf' && !isBinary) {
        const res = await fetch(`${baseUrl}/api/read?filepath=${encodeURIComponent(filePath)}`);
        const data = await res.json();
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${res.status}`);
        if (!transitionIsCurrent(token)) { cancelChangedTransition(token); return false; }
        if (typeof data.content !== 'string' || !data.path || documentPathIdentity(data.path) !== documentPathIdentity(filePath) || !isDocumentRevision(data.revision)) {
          throw new Error('Document read has no valid path, text or revision. Your current draft is kept; saving this response is disabled.');
        }
        path = data.path; text = data.content;
        draftCoordinator.load(path, text, data.revision);
      }
      if (!transitionIsCurrent(token)) { cancelChangedTransition(token); return false; }
      installDocument({ name: filePath.replace(/\\/g, '/').split('/').pop(), path, ext,
        isPdf: ext === 'pdf', isBinary, isIntakeOriginal,
        created: new Date().toISOString(), modified: new Date().toISOString() }, text);
      if (ext === 'fdx' || ext === 'fountain') setDocCanvasMode('code');
      setViewMode('editor');
      return true;
    } catch (err) {
      if (token.sequence === documentLoadSequenceRef.current) setError(errorMessage(err));
      return false;
    } finally {
      if (token.sequence === documentLoadSequenceRef.current) setLoading(false);
    }
  }, [baseUrl, retainDraft, installDocument]);

  // ── Create new document from template ──
  /** @param {(typeof TEMPLATES)[number]} template */
const createDocument = useCallback(async (/** @type {(typeof TEMPLATES)[number]} */ template) => {
    const token = beginDocumentTransition();
    if (saveFileRef.current && (await saveFileRef.current({ implicit: true })) === false) return;
    if (!transitionIsCurrent(token)) { cancelChangedTransition(token); return; }
    const name = `untitled-${Date.now()}-${crypto.randomUUID().slice(0, 8)}${template.ext}`;
    const doc = { name, path: `Documents/${name}`, isNew: true, ext: template.ext.slice(1),
      created: new Date().toISOString(), modified: new Date().toISOString() };
    draftCoordinator.registerNew(doc.path);
    installDocument(doc, template.content);
    retainDraft('new document');
    setShowNewDocModal(false); setViewMode('editor');
  }, [installDocument, retainDraft]);

  /** @param {DocumentDestination} [destination] */
const saveFile = useCallback(async (/** @type {DocumentDestination | undefined} */ destination = undefined) => {
    const snapshot = currentDocumentRef.current;
    const doc = destination?.path ? destination : snapshot.doc;
    if (!doc || doc.isPdf || doc.isBinary) return true;
    if (doc.isRecovery && destination?.implicit) return retainDraft('before leaving unsaved recovery', snapshot);
    if (isDriveIntakeOriginal(doc.path)) return !destination?.path;
    const text = snapshot.content;
    if (typeof text !== 'string') return false;
    const sourceIdentity = documentIdentityRef.current;
    if (destination?.path) {
      if (documentPathIdentity(destination.path) === documentPathIdentity(snapshot.doc?.path)) {
        setError('Save As needs a new filename. Use Save for the current document.'); return false;
      }
      // A reused Save As destination is never treated as an acknowledged existing file.
      if (draftCoordinator.snapshot(doc.path)) {
        setError('This destination is already known. Choose a new filename.'); return false;
      }
      draftCoordinator.registerNew(doc.path);
    } else if (doc.isNew) draftCoordinator.registerNew(doc.path);
    retainDraft('before save', { doc, content: text });
    setAutoSaveStatus('saving');
    try {
      const data = await draftCoordinator.save(doc.path, text);
      const current = currentDocumentRef.current;
      if (documentIdentityRef.current !== sourceIdentity || documentPathIdentity(current.doc?.path) !== documentPathIdentity(snapshot.doc?.path)) return true;
      const savedDoc = { ...current.doc, ...doc, path: data.path, isNew: false, isRecovery: false, modified: new Date().toISOString() };
      // Acknowledged text may be older than the editor. Keep the newer text dirty.
      currentDocumentRef.current = { doc: savedDoc, content: current.content };
      setActiveDoc(savedDoc);
      const dirty = draftCoordinator.isDirty(data.path, current.content);
      setAutoSaveStatus(dirty ? 'unsaved' : 'saved');
      setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      setUnsavedChanges(dirty);
      if (destination?.path) { documentIdentityRef.current++; localEditGenerationRef.current++; }
      await refreshFileTree();
      return true;
    } catch (err) {
      if (documentIdentityRef.current === sourceIdentity) {
        setError(`Save failed: ${errorMessage(err)}`); setAutoSaveStatus('error');
      }
      return false;
    }
  }, [refreshFileTree, setActiveDoc, retainDraft]);
  saveFileRef.current = saveFile;

  // Browser copies are retained before writes. A failed or uncertain write pauses
  // this path until an explicit reload; no automatic read/rebase/retry occurs.
  useEffect(() => {
    if (!activeDoc || typeof content !== 'string' || activeDoc.isPdf || activeDoc.isBinary || isDriveIntakeOriginal(activeDoc.path) || loading) return;
    if (!draftCoordinator.isDirty(activeDoc.path, content)) return;
    setUnsavedChanges(true);
    if (draftCoordinator.snapshot(activeDoc.path)?.blocked) { setAutoSaveStatus('error'); return; }
    if (activeDoc.isRecovery) { setAutoSaveStatus('unsaved'); return; }
    setAutoSaveStatus('unsaved');
    autoSaveTimerRef.current = setTimeout(() => { saveFile(); }, 1500);
    return () => clearTimeout(autoSaveTimerRef.current ?? undefined);
  }, [content, activeDoc, saveFile, loading, retainDraft]);

  const openRecoveryCopy = (/** @type {ReturnType<typeof listDocumentRecovery>[number]} */ copy) => {
    if (!retainDraft('before opening recovery')) return;
    const recovered = documentRecoveryDraft(copy);
    draftCoordinator.registerNew(recovered.doc.path);
    installDocument(recovered.doc, recovered.content);
    retainDraft('opened recovery copy');
    setShowRecovery(false); setViewMode('editor'); setError('');
  };

  const handleImportFile = useCallback(async (/** @type {File|null|undefined} */ file) => {
    if (!file) return;
    const token = beginDocumentTransition();
    setLoading(true); setError('');
    try {
      if (saveFileRef.current && (await saveFileRef.current({ implicit: true })) === false) return;
      if (!transitionIsCurrent(token)) { cancelChangedTransition(token); return; }
      const ext = file.name.split('.').pop()?.toLowerCase() || 'txt';
      let doc, text = '';
      if (ext === 'pdf') {
        const formData = new FormData();
        formData.append('files', file);
        formData.append('target_path', `Documents/PDF-Imports/${crypto.randomUUID()}`);
        const res = await fetch(`${baseUrl}/api/drive/upload`, { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'PDF upload failed');
        const uploaded = data.uploaded?.[0];
        if (!uploaded?.path) throw new Error('The server did not return a saved PDF path');
        doc = { path: uploaded.path.replace(/^\/+/, ''), name: uploaded.name || file.name, ext: 'pdf', isPdf: true };
        await refreshFileTree();
      } else {
        let name = file.name;
        if (ext === 'docx' || ext === 'doc') {
          const formData = new FormData(); formData.append('file', file);
          const res = await fetch(`${baseUrl}/api/documents/import_docx`, { method: 'POST', body: formData });
          const data = await res.json();
          if (!res.ok || typeof data.content !== 'string') throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not parse Word document');
          text = data.content; name = name.replace(/\.(docx|doc)$/i, '.md');
        } else { text = await file.text(); }
        doc = { path: `Documents/imported-${crypto.randomUUID()}-${name}`, name,
          ext: ext === 'docx' || ext === 'doc' ? 'md' : ext, isNew: true, isPdf: false };
      }
      if (!transitionIsCurrent(token)) { cancelChangedTransition(token); return; }
      if (doc.isNew) draftCoordinator.registerNew(doc.path);
      installDocument({ ...doc, rawFile: file, created: new Date().toISOString(), modified: new Date().toISOString() }, text);
      retainDraft('imported document'); setViewMode('editor');
      if (ext === 'docx' || ext === 'doc') setDocCanvasMode('paper');
    } catch (err) {
      if (token.sequence === documentLoadSequenceRef.current) setError(`Import failed: ${errorMessage(err)}`);
    } finally {
      if (token.sequence === documentLoadSequenceRef.current) setLoading(false);
    }
  }, [baseUrl, refreshFileTree, installDocument, retainDraft]);

  const createEditableIntakeCopy = async () => {
    const original = activeDoc;
    if (!original || !isDriveIntakeOriginal(original.path) || loading) return;
    const token = beginDocumentTransition();
    setLoading(true); setError('');
    try {
      const path = await createIntakeWorkingCopy({ backendUrl: baseUrl, path: original.path });
      await refreshFileTree();
      if (transitionIsCurrent(token)) await loadFile(path);
      else cancelChangedTransition(token);
    } catch (error) {
      if (token.sequence === documentLoadSequenceRef.current) setError(errorMessage(error));
    } finally {
      if (token.sequence === documentLoadSequenceRef.current) setLoading(false);
    }
  };

  // ── Convert PDF ──
  const convertPdf = useCallback(async () => {
    if (!activeDoc || !activeDoc.isPdf) return;
    const token = beginDocumentTransition();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${baseUrl}/api/convert-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: activeDoc.path }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Conversion failed');
      await refreshFileTree();
      if (transitionIsCurrent(token)) await loadFile(data.new_filepath);
      else cancelChangedTransition(token);
    } catch (err) {
      if (token.sequence === documentLoadSequenceRef.current) setError(`Convert failed: ${errorMessage(err)}`);
    } finally {
      if (token.sequence === documentLoadSequenceRef.current) setLoading(false);
    }
  }, [baseUrl, activeDoc, refreshFileTree, loadFile]);

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
      alert(`Adaptation error: ${errorMessage(err)}`);
    } finally {
      setIsAdapting(false);
    }
  };

  // ── Save As ──
  const saveAs = useCallback(async () => {
    if (!activeDoc) return;
    const newName = prompt('Save as:', activeDoc.name);
    if (!newName) return;

    if (/[<>:"/\\|?*]/.test(newName) || newName.trim() !== newName || /[. ]$/.test(newName)) {
      setError('Choose a filename without path separators or reserved characters.');
      return;
    }
    const ext = (newName.split('.').pop() || '').toLowerCase();
    const newPath = `Documents/${newName}`;
    await saveFile({ ...activeDoc, name: newName, path: newPath, ext, isNew: true });
  }, [activeDoc, saveFile]);

  // ── Sign & File ──
  const signDocument = useCallback(() => {
    if (!activeDoc) return;
    setShowSignModal(true);
    // We clear it after it opens, using a small timeout so the DOM has the canvas.
    setTimeout(clearCanvas, 100);
  }, [activeDoc]);

  /** @param {boolean} includeGraphic */
const submitSignature = useCallback(async (/** @type {boolean} */ includeGraphic) => {
    if (!activeDoc || activeDoc.isPdf || filingInFlightRef.current) return;
    filingInFlightRef.current = true;
    setIsFiling(true);
    setError('');
    let saved = null;
    try {
      const signature_image = includeGraphic && canvasRef.current
        ? canvasRef.current.toDataURL('image/png') : null;
      if (includeGraphic && !signature_image) throw new Error('Signature canvas is unavailable');
      if (saveFileRef.current && (await saveFileRef.current()) === false) {
        throw new Error('Save the current draft successfully before filing a PDF');
      }
      const res = await fetch(`${baseUrl}/api/documents/sign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: activeDoc.name, content, signature_image }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'PDF filing failed');
      if (!data.path || !data.filename || data.media_type !== 'application/pdf') {
        throw new Error('The server did not return a saved PDF');
      }
      saved = data;
      setShowSignModal(false);
      await refreshFileTree();
      const download = await fetch(`${baseUrl}/api/drive/preview?path=${encodeURIComponent(data.path)}`);
      if (!download.ok) throw new Error(`Download returned HTTP ${download.status}`);
      const blob = await download.blob();
      if ((await blob.slice(0, 5).text()) !== '%PDF-') throw new Error('Download was not a PDF');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
      alert(`PDF saved to ${data.path}. Download requested. ${data.signature_type === 'drawn_mark' ? 'Your drawn signature is included.' : 'Filed without a signature.'} No certificate-based digital signature was applied.`);
    } catch (err) {
      setError(saved ? `PDF saved to ${saved.path}, but download failed: ${errorMessage(err)}. Open it from the file tree.`
        : `PDF filing failed: ${errorMessage(err)}`);
    } finally {
      filingInFlightRef.current = false;
      setIsFiling(false);
    }
  }, [baseUrl, activeDoc, content, refreshFileTree]);

  // ── File Tree Management ──
  const deleteFile = useCallback(() => {
    if (!activeDoc) return;
    if (!confirm(`Delete "${activeDoc.name}"?`)) return;

    if (!retainDraft('before closing document')) return;
    installDocument(null, '');
    refreshFileTree();
  }, [activeDoc, refreshFileTree, retainDraft, installDocument]);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    /** @param {KeyboardEvent} e */
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
  /** @param {DocumentTreeNode[]} files @param {number} [depth] @returns {import("react").ReactNode} */
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
            {getFileTypeInfo(item.name.split('.').pop())?.icon || '📄'} {item.name}{isDriveIntakeOriginal(item.path) ? ' · Original (read only)' : ''}
          </div>
        )}
      </div>
    ));
  };

  // ═══════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════

  return (
    <div className="documents-workspace" style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0a0a0f' }}>
      {/* ── Top Bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 16px', background: '#1a1a2e', borderBottom: '1px solid #2a2a3e',
        fontSize: 12, color: '#8b949e',
      }}>
        <span style={{ fontWeight: 700, color: '#58a6ff' }}>📂 Document Editor & Creator</span>
        <span title={activeDoc?.name}>{activeDoc ? activeDoc.name : 'No document open'}</span>
        <button type="button" className="documents-explorer-toggle" aria-expanded={showFileTree}
          onClick={() => setShowFileTree(value => !value)}>Files</button>
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
          onChange={e => {
            const file = e.target.files?.[0];
            e.target.value = '';
            handleImportFile(file);
          }} 
        />

        <button type="button" onClick={() => { refreshRecovery(); setShowRecovery(value => !value); }} style={{ padding: '6px 12px', fontSize: 12 }}>Recovery copies</button>
        {activeDoc && !activeDoc.isPdf && !activeDoc.isBinary && (
          <button type="button" onClick={() => { const path = currentDocumentRef.current.doc?.path; if (path) loadFile(path, { reload: true }); }} style={{ padding: '6px 12px', fontSize: 12 }} title="Retain your current draft, then read the latest saved version">Reload latest</button>
        )}

        {/* Save & Adapt */}
        {activeDoc && !activeDoc.isBinary && !isDriveIntakeOriginal(activeDoc.path) && (
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
                    {autoSaveStatus === 'saving' ? 'Saving...' : autoSaveStatus === 'error' ? 'Autosave paused' : autoSaveStatus === 'unsaved' ? 'Unsaved draft' : `Saved ${lastSavedTime || ''}`}
                  </span>
                </div>
                <button onClick={() => saveFile()} style={{
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
            <span title="Document estimate at 250 words per page; not screenplay pagination">Estimated pages: {sprintPages}</span>
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

      {recoveryWarning && (
        <div role="alert" style={{ padding: '8px 16px', background: '#5c430f', color: '#fff2c2', fontSize: 12 }}>
          {recoveryWarning} <button type="button" onClick={() => downloadRecoveryText(currentDocumentRef.current.content || '', currentDocumentRef.current.doc?.name)}>Download current draft</button>
        </div>
      )}
      {showRecovery && (
        <section aria-label="Document recovery copies" style={{ padding: 12, maxHeight: 240, overflow: 'auto', border: '1px solid #48566b', background: '#172033', color: '#e2e8f0', fontSize: 12 }}>
          <strong>Retained browser copies</strong>
          <p>Open a copy as a new unsaved text document. It stays unsaved until you choose Save or Save As. Download copies before clearing browser storage.</p>
          {!recoveryCopies.length && <p>No readable browser copies are available.</p>}
          {recoveryCopies.map(copy => (
            <div key={copy.storageKey} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
              <span style={{ flex: 1, overflowWrap: 'anywhere' }}>{copy.name || copy.path} — {Number.isNaN(Date.parse(copy.savedAt)) ? 'time unknown' : new Date(copy.savedAt).toLocaleString()} ({copy.reason || 'saved copy'})</span>
              <button type="button" onClick={() => downloadRecoveryText(copy.content, copy.name)}>Download</button>
              <button type="button" onClick={() => openRecoveryCopy(copy)}>Open as new unsaved</button>
            </div>
          ))}
        </section>
      )}

      {/* ── Main Content ── */}
      <div className="documents-workspace-body" style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* File Tree */}
        {showFileTree && (
          <div className="documents-explorer" style={{
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
                (isDriveIntakeOriginal(activeDoc.path) || activeDoc.isBinary) ? (
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: '#e2e8f0' }}>
                    <div style={{ padding: '12px', borderBottom: '1px solid #334155', background: '#172033' }}>
                      <strong>{isDriveIntakeOriginal(activeDoc.path) ? 'Preserved original — read only' : 'Word / binary document — download to open'}</strong>
                      <p>{activeDoc.name}</p>
                      <AuthenticatedDriveDownload backendUrl={baseUrl} path={activeDoc.path}>Download original</AuthenticatedDriveDownload>
                      {isDriveIntakeOriginal(activeDoc.path) && activeDoc.isPdf && (
                        <button type="button" disabled={loading} onClick={convertPdf} style={{ marginLeft: '12px' }}>Extract text to working copy</button>
                      )}
                      {isDriveIntakeOriginal(activeDoc.path) && ['docx', 'txt', 'md', 'markdown', 'fdx', 'fountain'].includes(activeDoc.ext || '') && (
                        <button type="button" disabled={loading} onClick={createEditableIntakeCopy} style={{ marginLeft: '12px' }}>Create editable working copy</button>
                      )}
                      <p>Originals and earlier versions stay unchanged. Editable copies are saved separately in Working_Copies.</p>
                      {activeDoc.ext === 'docx' && <p>Word conversion extracts text into Markdown. Images, tables, page layout, and some formatting are not preserved in that working copy. Use the original DOCX or paired PDF to review the layout.</p>}
                      {['fdx', 'fountain'].includes(activeDoc.ext || '') && <p>For screenplay formatting, use Screenwriting → Import and choose a new project name. No AI adaptation is needed.</p>}
                    </div>
                    {activeDoc.isPdf ? <AuthenticatedDriveMedia backendUrl={baseUrl} path={activeDoc.path} title="Original PDF preview" width="100%" height="100%" style={{ border: 0, flex: 1 }} />
                      : activeDoc.isBinary ? <p style={{ padding: '16px' }}>This file is preserved in its native format. Download it to open in Word or another compatible application.</p>
                      : <pre style={{ padding: '16px', whiteSpace: 'pre-wrap', overflow: 'auto', flex: 1 }}>{content}</pre>}
                  </div>
                ) : activeDoc.isPdf ? (
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
                    <AuthenticatedDriveMedia
                      backendUrl={baseUrl} path={activeDoc.path}
                      width="100%" 
                      height="100%" 
                      style={{ border: 'none', background: '#525659', flex: 1 }}
                      title="PDF Viewer"
                    />
                  </div>
                ) : docCanvasMode === 'paper' ? (
                  <WordDocsPaperCanvas
                    value={content}
                    onChange={handleContentChange}
                    filename={activeDoc.name}
                    onSave={saveFile}
                    autoSaveStatus={autoSaveStatus}
                    lastSavedTime={lastSavedTime || undefined}
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
                        onChange={handleContentChange}
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
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4 }}>{activeDoc.created ? new Date(activeDoc.created).toLocaleString() : 'Not recorded'}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Modified</label>
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4 }}>{activeDoc.modified ? new Date(activeDoc.modified).toLocaleString() : 'Not recorded'}</div>
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
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#8b949e' }}>Save a PDF copy with an optional drawn signature. No certificate-based digital signature is applied.</p>
            </div>

            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <canvas 
                ref={canvasRef}
                width={400}
                height={200}
                onPointerDown={startDrawing}
                onPointerMove={draw}
                onPointerUp={stopDrawing}
                onPointerCancel={stopDrawing}
                onLostPointerCapture={stopDrawing}
                style={{ 
                  border: '1px solid #3a3a4e', 
                  borderRadius: 8, 
                  background: '#ffffff',
                  maxWidth: '100%',
                  cursor: 'crosshair',
                  touchAction: 'none'
                }}
              />
              <div style={{ width: '100%', display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                <button disabled={isFiling} onClick={clearCanvas} style={{
                  background: 'none', border: 'none', color: '#58a6ff', fontSize: 12, cursor: 'pointer'
                }}>Clear Canvas</button>
              </div>
            </div>

            <div style={{ padding: '12px 24px', borderTop: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between' }}>
              <button disabled={isFiling} onClick={() => setShowSignModal(false)} style={{
                padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
              }}>Cancel</button>
              
              <div style={{ display: 'flex', gap: 12 }}>
                <button disabled={isFiling} onClick={() => submitSignature(false)} style={{
                  padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                  background: '#232338', color: '#c9d1d9', cursor: 'pointer',
                }}>File without signature</button>
                <button disabled={isFiling} onClick={() => submitSignature(true)} style={{
                  padding: '8px 20px', fontSize: 12, border: 'none', borderRadius: 8,
                  background: '#238636', color: '#ffffff', cursor: 'pointer',
                }}>{isFiling ? 'Saving PDF…' : 'Sign & File PDF'}</button>
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

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
