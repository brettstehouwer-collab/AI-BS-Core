import React, { useState, useEffect, useRef } from 'react';
import { Fountain } from 'fountain-js';
const fountainParser = new Fountain();
import { useAppStore } from './useAppStore';
import CharacterVaultModal from './CharacterVaultModal';
import CoverageReportModal from './CoverageReportModal';
import ScreenplayEditor from './ScreenplayEditor';
import ScreenplayViewer from './ScreenplayViewer';
import AdaptationStatusBar from './AdaptationStatusBar';
import ScriptAssistantDrawer from './ScriptAssistantDrawer';
import ProjectAudioPlayer from './ProjectAudioPlayer';
import { parseFDX } from '../utils/FDXParser';
import { serializeFDX } from '../utils/FDXSerializer';
import { fountainToAST, astToFountain } from '../utils/FountainAdapter';
import { logTeamActivity } from './collaborationService';
import ScriptToBookNovelizerModal from './ScriptToBookNovelizerModal';
import ScreenplayTableReadModal from './ScreenplayTableReadModal';
import AnalyticsOverlay from './AnalyticsOverlay';
import ProductionBreakdownModal from './ProductionBreakdownModal';
import StagePlayBreakdownModal from './StagePlayBreakdownModal';
import ScriptTelemetryModal from './ScriptTelemetryModal';
import './StagePlayBreakdownModal.css';

const StoryboardModal = ({ isOpen, onClose, storyboards }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-6 text-white shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
            🎬 AI Storyboard Generator
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {storyboards.map((sb, idx) => (
            <div key={idx} className="bg-gray-800 rounded-lg p-4 border border-gray-700 shadow-lg">
              <div className="text-sm text-gray-300 mb-3 h-16 overflow-y-auto italic">"{sb.action}"</div>
              <img src={sb.image_url?.startsWith('http') || sb.image_url?.startsWith('data:') || sb.image_url?.startsWith('blob:') ? sb.image_url : `${BACKEND_URL || 'http://127.0.0.1:8000'}${sb.image_url?.startsWith('/') ? '' : '/'}${sb.image_url}`} alt="Storyboard Panel" className="w-full h-auto rounded-lg shadow-md border border-gray-600" />
            </div>
          ))}
        </div>
        
        {storyboards.length === 0 && (
          <div className="text-center text-gray-500 py-10">
            No storyboards generated.
          </div>
        )}
      </div>
    </div>
  );
};

import './ScreenwritingTab.css';

export default function ScreenwritingTab({ backendUrl, sharedContent, setSharedContent, sharedActiveDoc, onSendToVideoStudio }) {
  const storeBackendUrl = useAppStore(state => state.BACKEND_URL);
  const BACKEND_URL = backendUrl || storeBackendUrl || 'http://127.0.0.1:8000';

  // Screenplay State uses sharedWorkspace state if available, otherwise local state
  const [localScreenplay, setLocalScreenplay] = useState('');
  const screenplay = (sharedContent !== undefined && sharedContent !== null && sharedContent !== '') ? sharedContent : localScreenplay;
  const setScreenplay = (content) => {
    setLocalScreenplay(content);
    if (setSharedContent) setSharedContent(content);
  };
  const [ast, setAst] = useState([]);
  const [isInternalChange, setIsInternalChange] = useState(false);
  const [parsed, setParsed] = useState(null);
  const [liveHtml, setLiveHtml] = useState('');
  const [projectMetadata, setProjectMetadata] = useState(null);
  const [animatingBeats, setAnimatingBeats] = useState({});
  
  // Layout State
  const [leftPanelVisible, setLeftPanelVisible] = useState(() => typeof window !== 'undefined' ? window.innerWidth >= 850 : true);
  const [navigatorVisible, setNavigatorVisible] = useState(false);
  const [outlineMode, setOutlineMode] = useState('outline1'); // outline1, outline2
  const [activeView, setActiveView] = useState('editor'); // editor, preview, beats
  const [splitMode, setSplitMode] = useState('none'); // none, vertical, horizontal
  const [zoomLevel, setZoomLevel] = useState(100);

  // Find & Replace State
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');


  // Permanent Page Viewer Navigation State
  const viewerRef = useRef(null);
  const [viewerCurrentPage, setViewerCurrentPage] = useState(1);
  const [viewerSearch, setViewerSearch] = useState('');
  const calculateTotalPages = () => {
    if (!ast || ast.length === 0) return 1;
    let lines = 0;
    ast.forEach(b => {
      const len = (b.text || '').length;
      if (b.type === 'Scene Heading' || b.type === 'Action') lines += 1 + Math.ceil(Math.max(1, len) / 58);
      else if (b.type === 'Character') lines += 1 + Math.ceil(Math.max(1, len) / 38);
      else if (b.type === 'Parenthetical') lines += Math.ceil(Math.max(1, len) / 28);
      else if (b.type === 'Dialogue') lines += Math.ceil(Math.max(1, len) / 38);
      else if (b.type === 'Transition') lines += 1 + Math.ceil(Math.max(1, len) / 20);
      else lines += 1;
    });
    return Math.max(1, Math.ceil(lines / 54));
  };
  const totalScriptPages = calculateTotalPages();

  // Real-Time Hollywood Script Telemetry & Diagnostics
  const calculateScriptDiagnostics = () => {
    if (!ast || ast.length === 0) {
      return {
        pages: 1,
        runtimeStr: '1m',
        dialogueLines: 0,
        actionLines: 0,
        dialoguePct: 0,
        actionPct: 100,
        characterCount: 0,
        sceneCount: 0
      };
    }
    let dialogueLines = 0;
    let actionLines = 0;
    const uniqueChars = new Set();
    let sceneCount = 0;

    ast.forEach(b => {
      const len = (b.text || '').length;
      if (b.type === 'Dialogue' || b.type === 'Parenthetical') {
        dialogueLines += Math.ceil(Math.max(1, len) / 38);
      } else if (b.type === 'Character') {
        const clean = b.text.replace(/\s*\(.*?\)\s*/g, '').replace(/\s*\^/g, '').trim().toUpperCase();
        if (clean) uniqueChars.add(clean);
      } else if (b.type === 'Scene Heading') {
        sceneCount += 1;
        actionLines += 1 + Math.ceil(Math.max(1, len) / 58);
      } else if (b.type === 'Action' || b.type === 'Transition') {
        actionLines += 1 + Math.ceil(Math.max(1, len) / 58);
      }
    });

    const totalLines = dialogueLines + actionLines;
    const dialoguePct = totalLines > 0 ? Math.round((dialogueLines / totalLines) * 100) : 0;
    const actionPct = 100 - dialoguePct;

    const hours = Math.floor(totalScriptPages / 60);
    const mins = totalScriptPages % 60;
    const runtimeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;

    return {
      pages: totalScriptPages,
      runtimeStr,
      dialogueLines,
      actionLines,
      dialoguePct,
      actionPct,
      characterCount: uniqueChars.size,
      sceneCount: sceneCount || parsed?.beats?.length || 0
    };
  };
  const scriptDiag = calculateScriptDiagnostics();

  // Undo / Redo Stack State
  const [history, setHistory] = useState([ast]);
  const [historyIndex, setHistoryIndex] = useState(0);

  const handleUndo = () => {
    if (historyIndex > 0) {
      const prevIdx = historyIndex - 1;
      setHistoryIndex(prevIdx);
      const prevAst = history[prevIdx];
      setAst(prevAst);
      setIsInternalChange(true);
      setScreenplay(astToFountain(prevAst));
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const nextIdx = historyIndex + 1;
      setHistoryIndex(nextIdx);
      const nextAst = history[nextIdx];
      setAst(nextAst);
      setIsInternalChange(true);
      setScreenplay(astToFountain(nextAst));
    }
  };

  // Branch & Sprint State
  const [branches, setBranches] = useState([]);
  const [currentBranch, setCurrentBranch] = useState('main');
  const [sprints, setSprints] = useState([]);
  const [activeSprint, setActiveSprint] = useState(null);
  const [sprintName, setSprintName] = useState('');
  const [newBranchName, setNewBranchName] = useState('');
  
  // Projects State
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState('');
  const fileInputRef = useRef(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const editorRef = useRef(null);
  const [draggedBeatIndex, setDraggedBeatIndex] = useState(null);
  const [isProofing, setIsProofing] = useState(false);

  // Navigation & Workspace State
  const [sceneSearch, setSceneSearch] = useState('');
  const [pageJumpInput, setPageJumpInput] = useState('');
  const [activeRibbonTab, setActiveRibbonTab] = useState('write'); // 'write' | 'elements' | 'views' | 'unreal' | 'production'
  const [zenMode, setZenMode] = useState(false);

  const handleJumpToScene = (beat) => {
    if (!beat) return;
    const cleanHeading = (beat.heading || '').trim().toUpperCase();
    const targetBlock = ast.find(b => b.type === 'Scene Heading' && cleanHeading && b.text.trim().toUpperCase().includes(cleanHeading.substring(0, 25)));
    
    // In viewer mode or split mode, forward to viewer ref
    if (viewerRef.current) {
      viewerRef.current.scrollToScene(beat);
    }
    
    if (targetBlock) {
      // In editor mode, safely scroll the editor container internally without displacing page headers
      const editorContainer = document.querySelector('.sw-paginated-container');
      const editorEl = document.getElementById(`sw-block-${targetBlock.id}`);
      if (editorContainer && editorEl) {
        const containerRect = editorContainer.getBoundingClientRect();
        const elRect = editorEl.getBoundingClientRect();
        const targetTop = editorContainer.scrollTop + (elRect.top - containerRect.top) - (containerRect.height / 2);
        editorContainer.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
        editorEl.focus();
        editorEl.style.transition = 'background-color 0.4s ease, box-shadow 0.4s ease';
        editorEl.style.backgroundColor = 'rgba(250, 204, 21, 0.25)';
        editorEl.style.boxShadow = '0 0 16px rgba(250, 204, 21, 0.5)';
        setTimeout(() => { 
          editorEl.style.backgroundColor = 'transparent'; 
          editorEl.style.boxShadow = 'none';
        }, 1600);
      }
    } else if (beat.page) {
      handleJumpToPage(Math.floor(beat.page));
    }
  };

  const handleJumpToPage = (pageNum) => {
    if (!pageNum || isNaN(pageNum)) return;
    const validPage = Math.max(1, Math.min(pageNum, totalScriptPages));
    setViewerCurrentPage(validPage);
    
    // Jump in viewer
    if (viewerRef.current) {
      viewerRef.current.scrollToPage(validPage);
    }
    
    // Jump in editor
    const editorContainer = document.querySelector('.sw-paginated-container');
    const pageEl = document.getElementById(`sw-page-${validPage}`);
    if (editorContainer && pageEl) {
      const containerRect = editorContainer.getBoundingClientRect();
      const elRect = pageEl.getBoundingClientRect();
      const targetTop = editorContainer.scrollTop + (elRect.top - containerRect.top) - 20;
      editorContainer.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
      pageEl.style.transition = 'box-shadow 0.4s ease';
      pageEl.style.boxShadow = '0 0 25px rgba(56, 189, 248, 0.7)';
      setTimeout(() => { pageEl.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)'; }, 1500);
    }
  };

  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if (e.key === 'Escape' && zenMode) {
        setZenMode(false);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [zenMode]);

  // New Project State
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showNovelizerModal, setShowNovelizerModal] = useState(false);
  const [showTableReadModal, setShowTableReadModal] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectTemplate, setNewProjectTemplate] = useState('feature');
  const [newProjectAuthor, setNewProjectAuthor] = useState('Screenwriter');

  // AI Adapter State
  const [showAdaptModal, setShowAdaptModal] = useState(false);
  const [adaptFile, setAdaptFile] = useState(null);
  const [adaptProjectName, setAdaptProjectName] = useState('');
  const [adaptType, setAdaptType] = useState('Feature Film');
  const [adaptProgress, setAdaptProgress] = useState(null);
  const [isAdapting, setIsAdapting] = useState(false);

  // AI Ghostwriter State
  const [isGhostwriting, setIsGhostwriting] = useState(false);
  const [showCoverage, setShowCoverage] = useState(false);
  const [showStoryboards, setShowStoryboards] = useState(false);
  const [storyboards, setStoryboards] = useState([]);
  const [generatingStoryboards, setGeneratingStoryboards] = useState(false);
  const [coverageData, setCoverageData] = useState(null);
  const [isGeneratingCoverage, setIsGeneratingCoverage] = useState(false);
  const [showCharacterVault, setShowCharacterVault] = useState(false);
  const [characters, setCharacters] = useState([]);

  // Professional Features State
  const [isRevisionMode, setIsRevisionMode] = useState(false);
  const [revisionColor, setRevisionColor] = useState('blue');
  const [showAnalyticsOverlay, setShowAnalyticsOverlay] = useState(false);
  const [showProductionBreakdown, setShowProductionBreakdown] = useState(false);
  const [showStagePlayBreakdown, setShowStagePlayBreakdown] = useState(false);
  const [showScriptTelemetryModal, setShowScriptTelemetryModal] = useState(false);

  // Page Review & !proof State
  const [showPageReviewModal, setShowPageReviewModal] = useState(false);
  const [reviewPageNum, setReviewPageNum] = useState(1);
  const [isReviewingPage, setIsReviewingPage] = useState(false);
  const [reviewOriginalFountain, setReviewOriginalFountain] = useState('');
  const [reviewSuggestedFountain, setReviewSuggestedFountain] = useState('');
  const [reviewPageIndices, setReviewPageIndices] = useState({ start: 0, end: 0 });
  const [reviewStatusMessage, setReviewStatusMessage] = useState('');

  // Dedicated Script & Memoir Assistant Drawer State
  const [showScriptAssistant, setShowScriptAssistant] = useState(false);

  // Dedicated Audio Adaptation Master Track State
  const [showAudioPlayer, setShowAudioPlayer] = useState(true);

  // New Project Creation Handlers
  const handleCreateNewProject = async () => {
    if (!newProjectName.trim()) {
      alert("Please enter a project name.");
      return;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: newProjectName.trim(),
          template: newProjectTemplate,
          author: newProjectAuthor.trim() || 'Screenwriter'
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setShowNewProjectModal(false);
        setNewProjectName('');
        await loadProjects();
        setCurrentProject(data.current);
        await loadScreenplay();
        await loadBranches();
        await loadSprints();
        await loadCharacters();
      } else {
        alert(`Failed to create project: ${data.message || 'Unknown error'}`);
      }
    } catch (err) {
      alert(`Error creating project: ${err.message}`);
    }
  };

  const handleDeleteCurrentProject = async () => {
    if (currentProject === 'Default Project') {
      alert("Cannot delete the Default Project.");
      return;
    }
    if (!confirm(`Are you sure you want to delete the project "${currentProject}"? This will permanently remove its script and local files.`)) {
      return;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: currentProject })
      });
      const data = await res.json();
      if (data.status === 'success') {
        await loadProjects();
        setCurrentProject(data.current || 'Default Project');
        await loadScreenplay();
      }
    } catch (err) {
      alert(`Error deleting project: ${err.message}`);
    }
  };

  // Parse Screenplay helper
  const parseScreenplay = async (contentToParse) => {
    try {
      // Local real-time fountain-js parse for split-pane preview
      const htmlOutput = fountainParser.parse(contentToParse || screenplay);
      if (htmlOutput && htmlOutput.html && htmlOutput.html.script) {
        setLiveHtml(htmlOutput.html.script);
      }

      // Backend parse for Beat Board extraction, scene analysis, CMS
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: contentToParse || screenplay }),
      });
      const data = await res.json();
      setParsed(data);
    } catch (err) {
      console.error('Parse failed:', err);
    }
  };

  // Instantaneous parse effect
  useEffect(() => {
    if (!isInternalChange && screenplay) {
        setAst(fountainToAST(screenplay));
    }
    setIsInternalChange(false);
    
    const htmlOutput = fountainParser.parse(screenplay);
    if (htmlOutput && htmlOutput.html && htmlOutput.html.script) {
        setLiveHtml(htmlOutput.html.script);
    }
  }, [screenplay]);

  const handleAstChange = (newAst) => {
    setAst(newAst);
    setIsInternalChange(true);
    setScreenplay(astToFountain(newAst));
    setHistory(prev => {
      const upToCurrent = prev.slice(0, historyIndex + 1);
      const updated = [...upToCurrent, newAst];
      if (updated.length > 100) updated.shift();
      return updated;
    });
    setHistoryIndex(prev => Math.min(prev + 1, 99));
  };

  const loadProjects = async () => {
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects`);
          const data = await res.json();
          setProjects(data.projects || []);
          setCurrentProject(data.current || '');
      } catch (err) {
          console.error('Failed to load projects:', err);
      }
  };

  const loadScreenplay = async (targetProj) => {
    try {
      const proj = targetProj || currentProject;
      if (sharedActiveDoc && typeof sharedActiveDoc === 'string') {
        setCurrentProject(sharedActiveDoc);
      }
      // If we have an active doc from the Studio Workspace, parse it directly!
      if (sharedActiveDoc && sharedContent) {
        setScreenplay(sharedContent);
        setAst(fountainToAST(sharedContent));
        await parseScreenplay(sharedContent);
        return;
      }
      
      const queryParam = proj ? `?project_name=${encodeURIComponent(proj)}` : '';
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/read${queryParam}`);
      const data = await res.json();
      if (data.content) {
        setScreenplay(data.content);
        setAst(fountainToAST(data.content));
        await parseScreenplay(data.content);
      }
      if (data.project && data.project !== currentProject) {
        setCurrentProject(data.project);
      }
      setCurrentBranch(data.metadata?.current_branch || 'main');
      setProjectMetadata(data.metadata || {});
    } catch (err) {
      console.error('Failed to load screenplay:', err);
    }
  };

  const loadBranches = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/branches`);
      const data = await res.json();
      setBranches(data.branches || []);
      setCurrentBranch(data.current || 'main');
    } catch (err) {
      console.error('Failed to load branches:', err);
    }
  };


  const loadCharacters = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/characters`);
      const data = await res.json();
      if (data.status === 'success') setCharacters(data.characters || []);
    } catch (err) {
      console.error('Failed to load characters:', err);
    }
  };

  const loadSprints = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprints`);
      const data = await res.json();
      setSprints(data.sprints || []);
    } catch (err) {
      console.error('Failed to load sprints:', err);
    }
  };

  // Initial Load
  useEffect(() => {
    loadProjects();
    loadScreenplay();
    loadBranches();
    loadSprints();
    loadCharacters();
  }, []);

  // 💾 Automated Continuous Auto-Save Engine for Admins
  const autoSaveTimerRef = useRef(null);
  const [autoSaveStatus, setAutoSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'error'
  const [lastSavedTime, setLastSavedTime] = useState(null);
  const lastActivityLogRef = useRef(0);

  useEffect(() => {
    if (!screenplay || screenplay.trim() === '') return;

    // 1. Immediate client-side snapshot backup
    const projectKey = currentProject || 'active_screenplay';
    try {
      localStorage.setItem(`aibs_script_backup_${projectKey}`, screenplay);
      localStorage.setItem(`aibs_script_backup_time_${projectKey}`, String(Date.now()));
    } catch {}

    // 2. Debounce auto-save to backend
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setAutoSaveStatus('saving');

    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/screenwriting/write`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            content: screenplay, 
            branch: currentBranch,
            project_name: currentProject 
          }),
        });
        if (res.ok) {
          setAutoSaveStatus('saved');
          setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));

          // 3. Log team activity with 45-second cooldown
          const now = Date.now();
          if (now - lastActivityLogRef.current > 45000) {
            lastActivityLogRef.current = now;
            logTeamActivity({
              action: `Autosaved screenplay: ${currentProject || 'Main Screenplay'}`,
              toolName: 'Screenwriting Studio',
              tabKey: 'unified_creation',
              details: `${totalScriptPages} pages`
            });
          }
        } else {
          setAutoSaveStatus('error');
        }
      } catch (err) {
        console.warn('[Screenplay AutoSave] Background save error:', err.message);
        setAutoSaveStatus('error');
      }
    }, 1500);

    return () => {
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  }, [screenplay, currentProject, currentBranch, BACKEND_URL, totalScriptPages]);

  const handleSaveScreenplay = async () => {
    setIsLoading(true);
    setAutoSaveStatus('saving');
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: screenplay, branch: currentBranch, project_name: currentProject }),
      });
      const data = await res.json();
      if (data.status === 'success' || res.ok) {
        setAutoSaveStatus('saved');
        setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      } else {
        setAutoSaveStatus('error');
      }
    } catch (err) {
      console.error('Save failed:', err);
      setAutoSaveStatus('error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportFDX = () => {
    const xml = serializeFDX(ast);
    const blob = new Blob([xml], { type: "text/xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${currentProject || 'screenplay'}.fdx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/export/pdf`);
      if (!res.ok) throw new Error("Failed to export PDF.");
      
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${currentProject || 'screenplay'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF Export failed:", err);
      alert("Failed to export PDF. Check if backend generates it correctly.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateBranch = async () => {
    if (!newBranchName.trim()) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/branch/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch_name: newBranchName }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        await loadBranches();
        setNewBranchName('');
      }
    } catch (err) {
      console.error('Branch creation failed:', err);
    }
  };

  const handleStartSprint = async () => {
    if (!sprintName.trim()) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprint/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sprintName, target_pages: 10 }),
      });
      const data = await res.json();
      if (data.sprint) {
        setActiveSprint(data.sprint);
        setSprintName('');
        await loadSprints();
      }
    } catch (err) {
      console.error('Sprint start failed:', err);
    }
  };

  const handleEndSprint = async () => {
    if (!activeSprint) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprint/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sprint_id: activeSprint.id }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setActiveSprint(null);
        await loadSprints();
      }
    } catch (err) {
      console.error('Sprint end failed:', err);
    }
  };

  // Drag and Drop Beat Reordering
  const handleDragStart = (e, index) => {
    setDraggedBeatIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = async (e, targetIndex) => {
    e.preventDefault();
    if (draggedBeatIndex === null || draggedBeatIndex === targetIndex) return;
    
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/beats/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_index: draggedBeatIndex, target_index: targetIndex }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setParsed(data.parsed);
        await loadScreenplay();
      }
    } catch (err) {
      console.error('Reorder failed:', err);
    } finally {
      setIsLoading(false);
      setDraggedBeatIndex(null);
    }
  };

  const handleSwitchProject = async (proj) => {
      if (!proj) return;
      setIsLoading(true);
      setCurrentProject(proj);
      try {
          await fetch(`${BACKEND_URL}/api/screenwriting/projects/switch`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ project_name: proj })
          });
          await loadProjects();
          await loadScreenplay(proj);
          await loadBranches();
          await loadSprints();
          await loadCharacters();
      } catch (e) { console.error(e); }
      setIsLoading(false);
  };

  const handleAnimateBeat = async (beat) => {
      setAnimatingBeats(prev => ({...prev, [beat.id]: true}));
      try {
          const prompt = beat.heading + " " + beat.summary;
          const res = await fetch(`${BACKEND_URL}/api/video/test_pipeline`, {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ prompt: prompt })
          });
          const data = await res.json();
          if (data.status === 'success') {
               // Hardcoded HLS stream for now as output from VLC transcoder
               const videoUrl = `${BACKEND_URL}/streams/test_output.m3u8`;
               
               await fetch(`${BACKEND_URL}/api/screenwriting/projects/scene_video`, {
                   method: 'POST',
                   headers: {'Content-Type': 'application/json'},
                   body: JSON.stringify({ beat_id: beat.id, video_url: videoUrl })
               });
               
               await loadScreenplay(); // refresh metadata
          }
      } catch(err) {
          console.error(err);
      } finally {
          setAnimatingBeats(prev => ({...prev, [beat.id]: false}));
      }
  };

  const convertFdxToFountain = (xmlString) => {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlString, "text/xml");
      const paragraphs = xmlDoc.getElementsByTagName("Paragraph");
      let fountain = "";
      
      for (let i = 0; i < paragraphs.length; i++) {
          const p = paragraphs[i];
          const type = p.getAttribute("Type");
          const texts = p.getElementsByTagName("Text");
          let content = "";
          for (let j = 0; j < texts.length; j++) {
              content += texts[j].textContent;
          }
          
          if (!content.trim()) {
              fountain += "\n";
              continue;
          }
          
          if (type === "Scene Heading") {
              fountain += content.toUpperCase() + "\n\n";
          } else if (type === "Action") {
              fountain += content + "\n\n";
          } else if (type === "Character") {
              fountain += content.toUpperCase() + "\n";
          } else if (type === "Parenthetical") {
              if (content.startsWith('(') && content.endsWith(')')) {
                  fountain += content + "\n";
              } else {
                  fountain += "(" + content + ")\n";
              }
          } else if (type === "Dialogue") {
              fountain += content + "\n\n";
          } else if (type === "Transition") {
              fountain += "> " + content.toUpperCase() + "\n\n";
          } else {
              fountain += content + "\n\n";
          }
      }
      return fountain.trim();
  };

  const handleImportClick = () => {
      fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      
      const fileName = file.name.toLowerCase();
      const validExts = ['.pdf', '.docx', '.doc', '.epub', '.txt', '.rtf', '.md', '.markdown', '.fountain', '.fdx'];
      if (!validExts.some(ext => fileName.endsWith(ext))) {
          alert("Unsupported file format. Please upload a .pdf, .docx, .epub, .txt, .rtf, .md, .fdx, or .fountain file.");
          e.target.value = '';
          return;
      }
      
      const defaultName = currentProject || "Default Project";
      
      // If it's a manuscript/book file, open the Hollywood Adaptation Modal
      if (fileName.endsWith('.pdf') || fileName.endsWith('.docx') || fileName.endsWith('.doc') || fileName.endsWith('.epub') || fileName.endsWith('.rtf') || fileName.endsWith('.txt') || fileName.endsWith('.md') || fileName.endsWith('.markdown')) {
          setAdaptFile(file);
          setAdaptProjectName(defaultName);
          setShowAdaptModal(true);
          e.target.value = '';
          return;
      }
      
      // Direct screenplay script import (.fdx or .fountain)
      const projName = prompt("Importing script into project (or type a new project name):", defaultName);
      if (!projName) {
          e.target.value = '';
          return;
      }
      
      const reader = new FileReader();
      reader.onload = async (ev) => {
          let text = ev.target.result;
          
          if (file.name.toLowerCase().endsWith('.fdx')) {
              const newAst = parseFDX(text);
              text = astToFountain(newAst);
          }
          
          setIsLoading(true);
          try {
              await fetch(`${BACKEND_URL}/api/screenwriting/projects/import`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ project_name: projName, content: text })
              });
              await loadProjects();
              await loadScreenplay();
              await loadBranches();
              await loadSprints();
              await loadCharacters();
          } catch(err) { console.error(err); }
          setIsLoading(false);
      };
      reader.readAsText(file);
      e.target.value = '';
  };

  const handleStartAdaptation = async (forceRestart = false) => {
      if (!adaptFile || !adaptProjectName) return;
      setIsAdapting(true);
      setShowAdaptModal(false);
      setAdaptProgress({ status: 'processing', progress: 0, current_chunk: 0, total_chunks: 0 });
      
      const formData = new FormData();
      formData.append('file', adaptFile);
      formData.append('project_name', adaptProjectName);
      formData.append('adaptation_type', adaptType);
      if (forceRestart) {
        formData.append('force', 'true');
      }
      
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenplay/adapt`, {
              method: 'POST',
              body: formData
          });
          const resData = await res.json();
          if (res.status === 409 || resData.status === 'processing') {
              const doForce = confirm(
                `An adaptation job is already in progress for "${adaptProjectName}".\n\n` +
                `• Click OK to FORCE RESTART from the beginning.\n` +
                `• Click Cancel to attach to the live stream.`
              );
              if (doForce) {
                handleStartAdaptation(true);
                return;
              }
          } else if (!res.ok || resData.status === 'error') {
              throw new Error(resData.message || `HTTP error! status: ${res.status}`);
          }
          startAdaptationStream(adaptProjectName);
      } catch (err) {
          console.error('Adaptation error:', err);
          setIsAdapting(false);
          setAdaptProgress(null);
          alert(`Adaptation note: ${err.message}`);
      }
  };

  const startAdaptationStream = (projName) => {
      const eventSource = new EventSource(`${BACKEND_URL}/api/screenplay/adapt/stream?project_name=${projName}`);
      let lastProgress = -1;

      eventSource.onmessage = async (event) => {
          try {
              const data = JSON.parse(event.data);
              if (data.status && data.status !== 'not_found') {
                  setAdaptProgress(data);
                  
                  if (data.status === 'processing' && data.progress !== lastProgress) {
                      lastProgress = data.progress;
                      setCurrentProject(projName);
                      await loadProjects();
                      await loadScreenplay();
                  }

                  if (data.status === 'complete' || data.status === 'error') {
                      eventSource.close();
                      setIsAdapting(false);
                      setTimeout(() => setAdaptProgress(null), 3000);
                      
                      if (data.status === 'error') {
                          alert(`AI Adaptation Failed: ${data.error || 'Unknown error'}`);
                      }
                      
                      setCurrentProject(projName);
                      await loadProjects();
                      await loadScreenplay();
                      await loadBranches();
                  }
              }
          } catch(err) {
              console.error(err);
          }
      };

      eventSource.onerror = (err) => {
          console.error("SSE Error:", err);
          eventSource.close();
          setIsAdapting(false);
      };
  };

  const insertSyntax = (syntax) => {
    const { blockId } = getActiveEditorSelection();
    let insertIdx = ast.length;
    if (blockId) {
      const idx = ast.findIndex(b => String(b.id) === String(blockId));
      if (idx !== -1) insertIdx = idx + 1;
    }
    
    let type = 'Action';
    let cleanText = syntax.replace(/^\n+|\n+$/g, '');
    if (syntax.startsWith('INT.') || syntax.startsWith('EXT.')) {
      type = 'Scene Heading';
      cleanText = syntax.trim() || 'INT. LOCATION - DAY';
    } else if (syntax.includes('CHARACTER')) {
      type = 'Character';
      cleanText = 'CHARACTER';
    } else if (syntax.includes('Dialogue')) {
      type = 'Dialogue';
      cleanText = 'Dialogue text here.';
    } else if (syntax.includes('parenthetical')) {
      type = 'Parenthetical';
      cleanText = '(whispering)';
    } else if (syntax.includes('CUT TO:')) {
      type = 'Transition';
      cleanText = 'CUT TO:';
    }

    const newBlock = {
      id: crypto.randomUUID(),
      type,
      text: cleanText
    };
    const newAst = [...ast];
    newAst.splice(insertIdx, 0, newBlock);
    handleAstChange(newAst);
  };

  const exportFDX = () => {
    window.open(`${BACKEND_URL}/api/screenwriting/export/fdx`, '_blank');
  };

  const exportPDF = () => {
    const wm = prompt("Enter watermark text (or leave blank for none):", "");
    let url = `${BACKEND_URL}/api/screenwriting/export/pdf`;
    if (wm) {
       url += `?watermark=${encodeURIComponent(wm)}`;
    }
    window.open(url, '_blank');
  };

  // Helper to extract selected text or active focused block in ScreenplayEditor
  const getActiveEditorSelection = () => {
    const selection = window.getSelection();
    let text = '';
    let blockId = null;
    let isSubSelection = false;

    if (selection && selection.toString().trim()) {
      text = selection.toString().trim();
      isSubSelection = true;
      let node = selection.anchorNode;
      if (node && node.nodeType === 3) node = node.parentElement;
      const blockEl = node?.closest('[id^="sw-block-"]');
      if (blockEl) {
        blockId = blockEl.id.replace('sw-block-', '');
      }
    } else {
      const activeEl = document.activeElement?.closest('[id^="sw-block-"]');
      if (activeEl) {
        blockId = activeEl.id.replace('sw-block-', '');
        text = activeEl.innerText.trim();
      }
    }
    return { text, blockId, isSubSelection };
  };

  const applyEditorReplacement = (blockId, oldText, newText, isSubSelection) => {
    if (!blockId && ast.length > 0) {
      blockId = ast[0].id;
    }
    if (!blockId) return;

    const newAst = ast.map(b => {
      if (String(b.id) === String(blockId)) {
        if (isSubSelection && oldText && b.text.includes(oldText)) {
          return { ...b, text: b.text.replace(oldText, newText) };
        }
        return { ...b, text: newText };
      }
      return b;
    });
    handleAstChange(newAst);
  };

  const handleClipboard = async (action) => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (action === 'copy') {
      if (text) {
        await navigator.clipboard.writeText(text);
      }
    } else if (action === 'cut') {
      if (text && blockId) {
        await navigator.clipboard.writeText(text);
        applyEditorReplacement(blockId, text, '', isSubSelection);
      }
    } else if (action === 'paste') {
      try {
        const pasteText = await navigator.clipboard.readText();
        if (blockId) {
          applyEditorReplacement(blockId, text, (text ? text + ' ' : '') + pasteText, isSubSelection);
        }
      } catch (err) {
        console.error("Paste failed", err);
      }
    }
  };

  const handleFormat = (type) => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (!text || !blockId) {
      alert("Please highlight text or click inside a block to format.");
      return;
    }
    let formatted = text;
    if (type === 'bold') formatted = `**${text.replace(/\*\*/g, '')}**`;
    else if (type === 'italic') formatted = `*${text.replace(/\*/g, '')}*`;
    else if (type === 'underline') formatted = `_${text.replace(/_/g, '')}_`;
    else if (type === 'dual') formatted = text.endsWith(' ^') ? text.slice(0, -2) : `${text} ^`;

    applyEditorReplacement(blockId, text, formatted, isSubSelection);
  };

  const handleProofing = async (mode) => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (!text || !blockId) {
      alert("Please highlight text or click inside a block to run proofing.");
      return;
    }
    setIsProofing(true);
    const prompt = mode === 'spell' 
        ? `Fix spelling and grammar for the following screenplay excerpt. Return ONLY the corrected text without introductory markdown:\n\n${text}`
        : `Suggest a better, more evocative phrasing/synonym for the following screenplay excerpt. Return ONLY the new text without introductory markdown:\n\n${text}`;
        
    try {
        const res = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: prompt, model: "stehouwer_dolphin:latest" }),
        });
        const data = await res.json();
        
        if (data.status === 'success' || data.choices || data.message) {
            const responseText = (data.choices?.[0]?.message?.content || data.message?.content || data.response || data.message || '').trim();
            if (responseText) {
                applyEditorReplacement(blockId, text, responseText, isSubSelection);
            }
        }
    } catch (err) {
        console.error(err);
        alert("Proofing failed: " + err.message);
    } finally {
        setIsProofing(false);
    }
  };


  const getCharacterContextString = () => {
      if (!characters || characters.length === 0) return "";
      let ctx = "\n\n--- CHARACTER LORE & SPEAKING STYLES ---\n";
      characters.forEach(c => {
          ctx += `Name: ${c.name}\n`;
          if (c.bio) ctx += `Bio: ${c.bio}\n`;
          if (c.speaking_style) ctx += `Speaking Style: ${c.speaking_style}\n`;
          ctx += "\n";
      });
      return ctx;
  };

  const handleGhostwriter = async (index) => {
      // Get context from the recent AST blocks
      const contextBlocks = ast.slice(Math.max(0, index - 10), index + 1);
      const textToCursor = astToFountain(contextBlocks);
      
      setIsGhostwriting(true);
      const charContext = getCharacterContextString();
      const prompt = `You are an expert Hollywood screenwriter. Continue the following screenplay excerpt. 
Provide exactly ONE logical next beat (either a short action paragraph or a character's dialogue).
If you write dialogue for an existing character, you MUST adopt their specified Speaking Style and lore.
Format it in Fountain. 
Rules:
1. ABSOLUTELY NO PREAMBLE, introductions, or conversational text.
2. ABSOLUTELY NO MARKDOWN formatting (Do NOT use ** or * for bold/italics).

${charContext}

--- SCRIPT SO FAR ---
${textToCursor}`;

      try {
          const res = await fetch(`${BACKEND_URL}/api/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: prompt, model: "llama3:latest" }),
          });
          const data = await res.json();
          
          if (data.status === 'success') {
              let responseText = data.message?.content || data.response || '';
              responseText = responseText.trim();
              
              if (responseText) {
                  const newBlocks = fountainToAST(responseText);
                  const newAst = [...ast];
                  newAst.splice(index + 1, 0, ...newBlocks);
                  handleAstChange(newAst);
              }
          }
      } catch (err) {
          console.error('Ghostwriter failed', err);
      } finally {
          setIsGhostwriting(false);
      }
  };


  
  const [isExporting, setIsExporting] = useState(false);

  const handleExportUnreal = async (type) => {
      if (!screenplay || screenplay.trim() === '') {
          alert("No script to export!");
          return;
      }
      setIsExporting(true);
      try {
          const endpoint = type === 'csv' ? '/api/screenwriting/export/unreal-csv' : '/api/screenwriting/export/unreal-python';
          const res = await fetch(`${BACKEND_URL}${endpoint}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: screenplay })
          });
          const data = await res.json();
          if (data.status === 'success') {
              const blob = new Blob([data.data], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = type === 'csv' ? 'Unreal_DataTable.csv' : 'build_scene.py';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
          } else {
              alert("Export failed: " + data.message);
          }
      } catch (err) {
          console.error(err);
          alert("Export failed.");
      } finally {
          setIsExporting(false);
      }
  };

  const handleGenerateCoverage = async () => {
      if (!screenplay || screenplay.trim() === '') {
          alert("No script to analyze!");
          return;
      }
      setIsGeneratingCoverage(true);
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenwriting/coverage`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: screenplay })
          });
          const data = await res.json();
          if (data.status === 'success') {
              setCoverageData(data.coverage);
              setShowCoverage(true);
          } else {
              alert("Failed to generate coverage: " + data.message);
          }
      } catch (err) {
          console.error("Coverage failed", err);
          alert("Failed to generate coverage.");
      } finally {
          setIsGeneratingCoverage(false);
      }
  };

  const handleAltTake = async () => {
    const { text, blockId, isSubSelection } = getActiveEditorSelection();
    if (!text || !blockId) {
      alert("Please highlight dialogue or click inside a block to generate an Alt-Take.");
      return;
    }

    setIsProofing(true);
    const charContext = getCharacterContextString();
    const prompt = `EDITORIAL DIRECTIVE:
You are an expert Hollywood dramatic screenwriter. Rewrite the following excerpt from a screenplay to provide a single, strong "Alt-Take" that is punchier, more dramatic, or emotionally compelling.
Crucially, you MUST maintain the character's exact voice, using any speaking styles provided below.
Return ONLY the Fountain syntax for the rewritten text. Do not include introductory text or explanations.
Rules:
1. ABSOLUTELY NO PREAMBLE or conversational text.
2. ABSOLUTELY NO MARKDOWN formatting (Do NOT use ** or * for bold/italics).

${charContext}

--- ORIGINAL TEXT ---
${text}`;

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt, model: "stehouwer_dolphin:latest" }),
      });
      const data = await res.json();

      if (data.status === 'success' || data.choices || data.message) {
        let responseText = (data.choices?.[0]?.message?.content || data.message?.content || data.response || data.message || '').trim();
        responseText = responseText.replace(/^```(?:fountain|markdown)?\s*\n/i, '').replace(/\n```\s*$/, '').trim();
        if (responseText) {
          applyEditorReplacement(blockId, text, responseText, isSubSelection);
        }
      }
    } catch (err) {
      console.error('Alt-Take failed', err);
      alert('Alt-Take failed: ' + err.message);
    } finally {
      setIsProofing(false);
    }
  };

  const handleTitlePage = () => {
    const hasTitle = ast.some(b => b.type === 'Title' || (b.text && b.text.startsWith('Title:')));
    if (!hasTitle) {
      const titleBlock = {
        id: crypto.randomUUID(),
        type: 'Title',
        text: `Title: ${currentProject || 'UNTITLED'}\nAuthor: Brett Stehouwer\nDraft date: ${new Date().toLocaleDateString()}`
      };
      handleAstChange([titleBlock, ...ast]);
    }
    handleJumpToPage(1);
  };

  const handleSendToVideo = () => {
    const { text, blockId } = getActiveEditorSelection();
    let targetText = text;
    if (!targetText && blockId) {
      const block = ast.find(b => String(b.id) === String(blockId));
      if (block) targetText = block.text;
    }
    
    if (!targetText || targetText.trim() === "") {
      alert("Please highlight the scene/text you want to send to Video Studio!");
      return;
    }
    
    if (onSendToVideoStudio) {
      onSendToVideoStudio(targetText);
    }
  };

  const getPageBlocks = (targetPageNum) => {
    if (!ast || ast.length === 0) return { blocks: [], startIndex: 0, endIndex: 0 };
    const pages = [];
    let currentBuildingPage = [];
    let currentLines = 0;
    const MAX_LINES = 54;

    const estimateLines = (block) => {
      const len = (block.text || '').length;
      switch (block.type) {
        case 'Scene Heading': return 2 + Math.ceil(Math.max(1, len) / 58);
        case 'Action': return 1 + Math.ceil(Math.max(1, len) / 58);
        case 'Character': return 1 + Math.ceil(Math.max(1, len) / 38);
        case 'Dialogue': return Math.ceil(Math.max(1, len) / 38);
        case 'Parenthetical': return Math.ceil(Math.max(1, len) / 28);
        case 'Transition': return 2 + Math.ceil(Math.max(1, len) / 20);
        default: return 1;
      }
    };

    let pageStartIndex = 0;
    for (let i = 0; i < ast.length; i++) {
      const block = ast[i];
      const lines = estimateLines(block);
      if (currentLines + lines > MAX_LINES && currentBuildingPage.length > 0) {
        pages.push({ blocks: currentBuildingPage, startIndex: pageStartIndex, endIndex: i });
        currentBuildingPage = [block];
        currentLines = lines;
        pageStartIndex = i;
      } else {
        currentBuildingPage.push(block);
        currentLines += lines;
      }
    }
    if (currentBuildingPage.length > 0) {
      pages.push({ blocks: currentBuildingPage, startIndex: pageStartIndex, endIndex: ast.length });
    }

    const pageIndex = Math.max(0, Math.min(targetPageNum - 1, pages.length - 1));
    return pages[pageIndex] || { blocks: [], startIndex: 0, endIndex: 0 };
  };

  const handleProofPage = async (targetPageNum = viewerCurrentPage) => {
    const validPage = Math.max(1, Math.min(targetPageNum, totalScriptPages));
    setReviewPageNum(validPage);
    const { blocks, startIndex, endIndex } = getPageBlocks(validPage);
    if (!blocks || blocks.length === 0) {
      alert(`No content found on Page ${validPage}.`);
      return;
    }

    const origFountain = astToFountain(blocks);
    setReviewOriginalFountain(origFountain);
    setReviewSuggestedFountain('');
    setReviewPageIndices({ start: startIndex, end: endIndex });
    setShowPageReviewModal(true);
    setIsReviewingPage(true);
    setReviewStatusMessage(`Analyzing and format-proofing Page ${validPage}...`);

    const charContext = getCharacterContextString();
    const prompt = `EDITORIAL DIRECTIVE:
You are an expert Hollywood Screenplay Doctor and Format Proofing Engine.
Review, format-proof, and polish the following screenplay excerpt from Page ${validPage}.

STRICT ANTI-HALLUCINATION & FACTUAL FIDELITY RULES:
1. STRICT GROUNDING: You are an editorial proofreader and format doctor, NOT a fiction author. You are strictly forbidden from inventing new characters, altering character names, changing plot events, or introducing fictional dialogue that changes the meaning of the true story.
2. FORMAT STANDARDIZATION: Standardize all SCENE HEADINGS (INT., EXT., INT./EXT. in ALL CAPS).
3. CHARACTER CUES: Ensure CHARACTER names are ALL CAPS on their own line preceding dialogue.
4. PARENTHETICALS: Place PARENTHETICALS on their own line enclosed in parentheses (e.g. "(whispering)").
5. ACTION & DIALOGUE SEPARATION: Separate combined action and dialogue paragraphs into clean, distinct blocks.
6. TRANSITIONS: Standardize TRANSITIONS (e.g., "CUT TO:", "FADE OUT." in ALL CAPS).
7. GRAMMAR & POLISH: Correct spelling, typos, grammar, and spacing while strictly preserving character dialogue voice, emotional tone, and non-fiction baseline facts.
8. ZERO PREAMBLE: Return ONLY the clean Fountain screenplay text. Do NOT include markdown code blocks, conversational greetings, or notes.

${charContext}

--- ORIGINAL PAGE ${validPage} CONTENT ---
${origFountain}`;

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: prompt, 
          model: "stehouwer_dolphin:latest",
          temperature: 0.1,
          top_p: 0.85
        }),
      });
      const data = await res.json();
      if (data.status === 'success' || data.choices || data.message) {
        let suggested = (data.choices?.[0]?.message?.content || data.message?.content || data.response || data.message || '').trim();
        suggested = suggested.replace(/^```(?:fountain|markdown)?\s*\n/i, '').replace(/\n```\s*$/, '').trim();
        setReviewSuggestedFountain(suggested);
        setReviewStatusMessage(`Page ${validPage} proofing ready for review.`);
      }
    } catch (err) {
      console.error('Page proofing error:', err);
      setReviewStatusMessage(`Error analyzing page: ${err.message}`);
    } finally {
      setIsReviewingPage(false);
    }
  };

  const handleApplyPageProof = (advanceNext = false) => {
    if (!reviewSuggestedFountain) return;
    const newBlocks = fountainToAST(reviewSuggestedFountain);
    const newAst = [...ast];
    newAst.splice(reviewPageIndices.start, reviewPageIndices.end - reviewPageIndices.start, ...newBlocks);
    handleAstChange(newAst);
    
    if (advanceNext && reviewPageNum < totalScriptPages) {
      handleProofPage(reviewPageNum + 1);
    } else {
      setShowPageReviewModal(false);
    }
  };

  const handleInsertScriptAssistantText = (textToInsert) => {
    if (!textToInsert) return;
    const newBlocks = fountainToAST(textToInsert);
    const { blockId } = getActiveEditorSelection();
    if (blockId) {
      const idx = ast.findIndex(b => String(b.id) === String(blockId));
      if (idx !== -1) {
        const newAst = [...ast];
        newAst.splice(idx + 1, 0, ...newBlocks);
        handleAstChange(newAst);
        return;
      }
    }
    handleAstChange([...ast, ...newBlocks]);
  };

  const handleEditorWillMount = (monaco) => {
    monaco.languages.register({ id: 'fountain' });

    monaco.languages.setMonarchTokensProvider('fountain', {
        tokenizer: {
            root: [
                // Scene Headings
                [/^(INT|EXT|EST|INT\/EXT|I\/E|int|ext|est)[\.\s].*$/, 'scene-heading'],
                [/^\..*$/, 'scene-heading'],
                
                // Transitions
                [/^>.*$/, 'transition'],
                [/^[A-Z\s]+ TO:$/, 'transition'],
                
                // Forced Character
                [/^@[A-Z0-9\s\.\(\)\-]+$/, 'character'],
                
                // Character Names (Heuristic: All caps line, but let's avoid matching every all-cap line perfectly, we can just do A-Z with optional parens)
                [/^[A-Z0-9\s\.\-]+(\s\(.*?\))?$/, 'character'],
                
                // Parentheticals
                [/^\s*\([^)]*\)\s*$/, 'parenthetical'],
                
                // Emphasis
                [/\*\*.*?\*\*/, 'bold'],
                [/\*.*?\*/, 'italic'],
                [/_.*?_/, 'underline'],
                
                // Notes/Boneyard
                [/\[\[.*?\]\]/, 'note'],
                [/\/\*/, 'comment', '@boneyard']
            ],
            boneyard: [
                [/[^\/*]+/, 'comment'],
                [/\*\//, 'comment', '@pop'],
                [/[\/*]/, 'comment']
            ]
        }
    });

    monaco.editor.defineTheme('fountain-theme', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'scene-heading', foreground: '58a6ff', fontStyle: 'bold' },
            { token: 'transition', foreground: 'd2a8ff', fontStyle: 'italic' },
            { token: 'character', foreground: 'facc15', fontStyle: 'bold' },
            { token: 'parenthetical', foreground: '9ca3af', fontStyle: 'italic' },
            { token: 'note', foreground: 'ff7b72' },
            { token: 'comment', foreground: '6e7681', fontStyle: 'italic' },
            { token: 'bold', fontStyle: 'bold' },
            { token: 'italic', fontStyle: 'italic' },
            { token: 'underline', fontStyle: 'underline' }
        ],
        colors: {
            'editor.background': '#0d1117'
        }
    });
  };

  const handlePublishToCMS = async () => {
      if (!parsed || !parsed.html) {
          alert("No parsed HTML available to publish.");
          return;
      }
      
      const filename = prompt("Enter the filename for the CMS (e.g. script.html):", `${currentProject || 'draft'}.html`);
      if (!filename) return;

      setIsLoading(true);
      try {
          const res = await fetch(`${BACKEND_URL}/api/cms/page/save`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  filename: filename,
                  content: `<div class="script-content" style="max-width: 800px; margin: 0 auto; font-family: 'Courier Prime', Courier, monospace; background: white; padding: 40px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">\n${parsed.html}\n</div>`
              })
          });
          const data = await res.json();
          if (data.status === 'success') {
              alert(`Successfully published ${filename} to CMS!`);
          } else {
              alert(`Error publishing to CMS: ${data.message || 'Unknown error'}`);
          }
      } catch (err) {
          console.error("Publish failed", err);
          alert("Failed to publish to CMS");
      } finally {
          setIsLoading(false);
      }
  };
  const filteredBeats = (parsed?.beats || []).filter(b => 
      !sceneSearch.trim() || 
      (b.heading && b.heading.toLowerCase().includes(sceneSearch.toLowerCase())) ||
      (b.summary && b.summary.toLowerCase().includes(sceneSearch.toLowerCase()))
  );

  return (
    <div className="screenwriting-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', maxHeight: '100%', width: '100%', minHeight: 0, overflow: 'hidden', flexWrap: 'nowrap' }}>
      {/* Coverage Modal */}
      {showCoverage && (
        <CoverageReportModal 
          coverageData={coverageData}
          onClose={() => setShowCoverage(false)}
        />
      )}

      {/* Analytics Overlay */}
      {showAnalyticsOverlay && (
        <AnalyticsOverlay 
          ast={ast} 
          onClose={() => setShowAnalyticsOverlay(false)} 
        />
      )}

      {/* Production Breakdown Modal */}
      {showProductionBreakdown && (
        <ProductionBreakdownModal 
          scriptText={screenplay || ''} 
          onClose={() => setShowProductionBreakdown(false)} 
        />
      )}

      {/* Stage Play Breakdown Modal */}
      {showStagePlayBreakdown && (
        <StagePlayBreakdownModal 
          scriptText={screenplay || ''} 
          onClose={() => setShowStagePlayBreakdown(false)} 
        />
      )}

      {/* Character Vault Modal */}
      {showCharacterVault && (
        <CharacterVaultModal 
          backendUrl={BACKEND_URL}
          onClose={() => setShowCharacterVault(false)}
          onCharactersUpdate={(chars) => {
             setCharacters(chars);
          }}
        />
      )}

      {showAdaptModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#1f2937', border: '1px solid #374151', padding: '24px', borderRadius: '10px', width: '500px', maxWidth: '90vw', boxShadow: '0 8px 32px rgba(0,0,0,0.6)' }}>
            <h3 style={{ color: '#facc15', marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              🎬 Adapt Manuscript to Hollywood Screenplay
            </h3>
            <p style={{ color: '#9ca3af', fontSize: '0.85rem', lineHeight: '1.4', marginBottom: '16px' }}>
              The AI-BS Matrix extracts character arcs, visual actions, and subtext from your manuscript (PDF, Word, EPUB, RTF, TXT, MD), chunking and adapting it into a professional screenplay.
            </p>
            
            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Source File:</label>
              <div style={{ color: '#38bdf8', fontSize: '0.85rem', padding: '6px 10px', background: '#111827', borderRadius: '4px', border: '1px solid #374151' }}>
                📄 {adaptFile?.name || 'No file selected'}
              </div>
            </div>

            <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Project Name:</label>
            <input type="text" value={adaptProjectName} onChange={e => setAdaptProjectName(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '16px', boxSizing: 'border-box' }} />
            
            <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Hollywood & Director Format Target:</label>
            <select value={adaptType} onChange={e => setAdaptType(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '10px', boxSizing: 'border-box', background: '#111827', color: '#fff' }}>
              <option value="Feature Film (Spec Script)">🎬 Feature Film (3-Act Hollywood Spec Script)</option>
              <option value="TV Pilot (1-Hour Drama)">📺 TV Pilot (1-Hour Network/Streaming Drama)</option>
              <option value="TV Pilot (30-Minute Comedy/Sitcom)">🎭 TV Pilot (30-Minute Comedy / Sitcom)</option>
              <option value="Limited / Mini-Series Episode">🎞️ Limited / Mini-Series Episodic Script</option>
              <option value="Director's Shooting Script (Previs & Camera Cues)">🎥 Director's Shooting Script (Camera & Lighting Cues)</option>
              <option value="Theatrical Stage Play">🏛️ Theatrical Stage Play (Act/Scene & Stage Blocking)</option>
              <option value="Audio Drama / Scripted Podcast">🎙️ Audio Drama / Scripted Podcast (SFX & Spatial Audio)</option>
              <option value="Short Film">⚡ Short Film (10-15 Minute Condensed Arc)</option>
            </select>

            {/* Dynamic Format Guide Helper */}
            <div style={{ background: '#111827', border: '1px solid #374151', padding: '10px', borderRadius: '6px', fontSize: '0.75rem', color: '#9ca3af', marginBottom: '20px', lineHeight: '1.4' }}>
              {adaptType.includes("1-Hour") && "📌 Structures prose into Teaser + 5/6 Acts with broadcast commercial cliffhangers and uppercase character introductions."}
              {adaptType.includes("30-Minute") && "📌 Fast-paced comedic rhythm with Cold Open, Act 1, Act 2, Tag, and punchy physical delivery parentheticals."}
              {adaptType.includes("Director") && "📌 Adds [WIDE SHOT], [CLOSE-UP], [TRACKING] camera framing, lighting notes, and physical actor blocking for 3D Unreal Engine previs."}
              {adaptType.includes("Stage Play") && "📌 Formats with ACT I / SCENE I headers, stage directions [STAGE LEFT], and physical actor blocking."}
              {adaptType.includes("Audio Drama") && "📌 Injects spatial sound design cues [SFX: ...], musical underscores [MUSIC: ...], and voiceover transitions."}
              {adaptType.includes("Short Film") && "📌 Strips exposition for rapid inciting incidents, tight visual conflict, and a sharp thematic punchline."}
              {adaptType.includes("Limited") && "📌 Serialized storytelling interleaving A-plot and B-plot character arcs with atmospheric scene depth."}
              {(!adaptType.includes("1-Hour") && !adaptType.includes("30-Minute") && !adaptType.includes("Director") && !adaptType.includes("Stage Play") && !adaptType.includes("Audio Drama") && !adaptType.includes("Short Film") && !adaptType.includes("Limited")) && "📌 Industry-standard 3-Act studio screenplay converting internal prose into visual external actions and subtext dialogue."}
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button onClick={() => setShowAdaptModal(false)} style={{ background: 'transparent', border: '1px solid #555', color: '#fff', padding: '6px 14px', cursor: 'pointer', borderRadius: '4px' }}>Cancel</button>
              <button onClick={handleStartAdaptation} style={{ background: '#facc15', color: '#000', border: 'none', padding: '6px 14px', fontWeight: 'bold', cursor: 'pointer', borderRadius: '4px' }}>🚀 Start Adaptation</button>
            </div>
          </div>
        </div>
      )}

      {/* 1. Consolidated Studio Header & Breadcrumbs */}
      {zenMode ? (
        <div style={{ position: 'fixed', top: '12px', right: '16px', zIndex: 9999, display: 'flex', gap: '8px', background: 'rgba(17, 24, 39, 0.9)', padding: '6px 14px', borderRadius: '20px', border: '1px solid #374151', backdropFilter: 'blur(8px)', boxShadow: '0 4px 16px rgba(0,0,0,0.5)' }}>
          <span style={{ color: '#facc15', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>🧘 Zen Focus Mode Active</span>
          <button onClick={() => setZenMode(false)} style={{ background: '#374151', color: '#fff', border: 'none', padding: '2px 10px', borderRadius: '12px', fontSize: '0.75rem', cursor: 'pointer' }}>
            Exit (Esc)
          </button>
        </div>
      ) : (
        <div className="sw-consolidated-header" style={{ position: 'sticky', top: 0, zIndex: 110, flexShrink: 0, background: '#111827', borderBottom: '1px solid #1f2937', padding: '6px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          
          {/* Breadcrumb Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
            <span style={{ color: '#9ca3af' }}>🎬 Creation Suite</span>
            <span style={{ color: '#4b5563' }}>/</span>
            <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>✍️ Writing Studio</span>
            <span style={{ color: '#4b5563' }}>/</span>
            <select 
              value={currentProject} 
              onChange={(e) => handleSwitchProject(e.target.value)} 
              style={{ background: '#1f2937', color: '#facc15', border: '1px solid #374151', borderRadius: '4px', padding: '2px 8px', fontSize: '0.85rem', fontWeight: 'bold', cursor: 'pointer' }}
            >
              {projects.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Ribbon Category Switcher Tabs */}
          <div style={{ display: 'flex', gap: '2px', background: '#0a0a0a', padding: '3px', borderRadius: '6px', border: '1px solid #1f2937' }}>
            {[
              { id: 'write', label: '✍️ Write' },
              { id: 'elements', label: '🧩 Elements' },
              { id: 'views', label: '👁️ Views & Split' },
              { id: 'unreal', label: '🎮 3D & Previs' },
              { id: 'production', label: '🚀 Production & CMS' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveRibbonTab(tab.id)}
                style={{
                  background: activeRibbonTab === tab.id ? '#1f2937' : 'transparent',
                  color: activeRibbonTab === tab.id ? '#facc15' : '#9ca3af',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.8rem',
                  fontWeight: activeRibbonTab === tab.id ? 'bold' : 'normal',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Quick Action Group */}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <button 
              onClick={() => setShowNewProjectModal(true)} 
              style={{ background: '#238636', color: '#fff', border: '1px solid #2ea043', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="Create a new Screenplay Project"
            >
              + New Project
            </button>
            <button 
              onClick={() => setZenMode(true)} 
              style={{ background: '#1f2937', color: '#a78bfa', border: '1px solid #374151', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="Enter Distraction-Free Fullscreen Mode (Esc to exit)"
            >
              🧘 Zen Mode
            </button>
            <button 
              onClick={() => setShowNovelizerModal(true)} 
              style={{ background: 'linear-gradient(90deg, #7c3aed 0%, #6d28d9 100%)', color: '#fff', border: '1px solid #a78bfa', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 8px rgba(124, 58, 237, 0.4)' }}
              title="Convert this Screenplay into a full-length Book / Novel / Memoir"
            >
              📖 Novelize to Book
            </button>
            <button 
              onClick={() => setShowTableReadModal(true)} 
              style={{ background: 'linear-gradient(90deg, #d97706 0%, #b45309 100%)', color: '#fff', border: '1px solid #f59e0b', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 8px rgba(217, 119, 6, 0.4)' }}
              title="Launch Multi-Voice AI Audio Table Read Studio"
            >
              🎙️ Table Read Studio
            </button>
            <button 
              onClick={() => setShowScriptTelemetryModal(true)} 
              style={{ background: 'linear-gradient(90deg, #0284c7 0%, #0369a1 100%)', color: '#fff', border: '1px solid #38bdf8', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', fontWeight: 'bold', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 8px rgba(2, 132, 199, 0.4)' }}
              title="Watch pages being written, AI thoughts & execution telemetry live"
            >
              ⚡ Thoughts & Pages Telemetry
            </button>
            <button onClick={handleImportClick} className="sw-ribbon-btn" style={{ background: 'transparent', border: '1px solid #34d399', color: '#34d399', padding: '4px 8px', fontSize: '0.8rem' }}>
              📥 Import
            </button>
            <button onClick={() => setShowFindReplace(!showFindReplace)} className="sw-ribbon-btn" style={{ background: showFindReplace ? 'rgba(168, 85, 247, 0.3)' : 'transparent', border: '1px solid #a855f7', color: '#a855f7', padding: '4px 8px', fontSize: '0.8rem' }}>
              🔍 Find & Replace
            </button>
            <button onClick={handleExportFDX} className="sw-ribbon-btn" style={{ background: 'transparent', border: '1px solid #38bdf8', color: '#38bdf8', padding: '4px 8px', fontSize: '0.8rem' }}>
              📄 Export FDX
            </button>
            <button onClick={handleExportPDF} className="sw-ribbon-btn" style={{ background: 'transparent', border: '1px solid #e11d48', color: '#e11d48', padding: '4px 8px', fontSize: '0.8rem' }}>
              📄 Export PDF
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid #334155', padding: '3px 8px', borderRadius: '6px', fontSize: '0.75rem' }} title="Continuous background autosave for admins">
              <span style={{ fontSize: '0.65rem' }}>
                {autoSaveStatus === 'saving' ? '🟡' : autoSaveStatus === 'error' ? '🔴' : '🟢'}
              </span>
              <span style={{ color: autoSaveStatus === 'error' ? '#f87171' : (autoSaveStatus === 'saving' ? '#fbbf24' : '#38bdf8'), fontWeight: 600 }}>
                {autoSaveStatus === 'saving' ? 'Saving...' : autoSaveStatus === 'error' ? 'Autosave Failed' : `Autosaved ${lastSavedTime ? lastSavedTime : ''}`}
              </span>
            </div>
            <button onClick={handleSaveScreenplay} disabled={isLoading} className="sw-save-btn" style={{ padding: '4px 12px', fontSize: '0.8rem' }}>
              {isLoading ? 'Saving...' : '💾 Save'}
            </button>
          </div>
        </div>
      )}

      {/* Find & Replace Bar */}
      {showFindReplace && (
        <div style={{ background: '#1e293b', borderBottom: '1px solid #334155', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input 
            type="text" 
            placeholder="Find text..." 
            value={findText} 
            onChange={(e) => setFindText(e.target.value)} 
            style={{ background: '#0f172a', border: '1px solid #475569', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', width: '200px' }}
          />
          <input 
            type="text" 
            placeholder="Replace with..." 
            value={replaceText} 
            onChange={(e) => setReplaceText(e.target.value)} 
            style={{ background: '#0f172a', border: '1px solid #475569', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', width: '200px' }}
          />
          <button 
            onClick={() => {
              if (!findText) return;
              let occurrences = 0;
              const newAst = ast.map(b => {
                if (b.text && b.text.includes(findText)) {
                  occurrences += (b.text.split(findText).length - 1);
                  return { ...b, text: b.text.split(findText).join(replaceText) };
                }
                return b;
              });
              if (occurrences > 0) {
                handleAstChange(newAst);
                alert(`Replaced ${occurrences} occurrences of "${findText}".`);
              } else {
                alert(`No occurrences of "${findText}" found.`);
              }
            }}
            style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '4px 12px', borderRadius: '4px', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Replace All
          </button>
          <button onClick={() => setShowFindReplace(false)} style={{ background: 'transparent', color: '#94a3b8', border: 'none', cursor: 'pointer', fontSize: '1rem' }}>
            &times;
          </button>
        </div>
      )}


      {/* 2. Dynamic Single-Deck Ribbon (Hidden in Zen Mode) */}
      {!zenMode && (
        <div className="sw-ribbon" style={{ position: 'sticky', top: 0, zIndex: 105, flexShrink: 0, padding: '6px 16px', minHeight: '42px', display: 'flex', alignItems: 'center', background: '#161e2e', borderBottom: '1px solid #1f2937', gap: '16px', overflowX: 'auto' }}>
          
          {/* TAB 1: WRITE */}
          {activeRibbonTab === 'write' && (
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className="sw-ribbon-btn" onClick={handleUndo} disabled={historyIndex <= 0} title="Undo (Ctrl+Z)" style={{ opacity: historyIndex <= 0 ? 0.4 : 1, fontWeight: 'bold' }}>↶ Undo</button>
                <button className="sw-ribbon-btn" onClick={handleRedo} disabled={historyIndex >= history.length - 1} title="Redo (Ctrl+Y)" style={{ opacity: historyIndex >= history.length - 1 ? 0.4 : 1, fontWeight: 'bold' }}>↷ Redo</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className="sw-ribbon-btn" onClick={() => handleClipboard('cut')}>✂️ Cut</button>
                <button className="sw-ribbon-btn" onClick={() => handleClipboard('copy')}>📋 Copy</button>
                <button className="sw-ribbon-btn" onClick={() => handleClipboard('paste')}>📋 Paste</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className="sw-ribbon-btn" style={{ fontWeight: 'bold' }} onClick={() => handleFormat('bold')}>B</button>
                <button className="sw-ribbon-btn" style={{ fontStyle: 'italic' }} onClick={() => handleFormat('italic')}>I</button>
                <button className="sw-ribbon-btn" style={{ textDecoration: 'underline' }} onClick={() => handleFormat('underline')}>U</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <button className="sw-ribbon-btn" onClick={() => handleProofing('spell')} disabled={isProofing}>{isProofing ? '⏳' : '📝'} Spell</button>
                <button className="sw-ribbon-btn" onClick={() => handleProofing('thesaurus')} disabled={isProofing}>{isProofing ? '⏳' : '📖'} Thesaurus</button>
                <button className="sw-ribbon-btn" onClick={handleAltTake} disabled={isProofing} style={{ color: '#facc15' }}>{isProofing ? '⏳' : '✨'} Alt-Take</button>
              </div>
            </div>
          )}

          {/* TAB 2: ELEMENTS & INSERT */}
          {activeRibbonTab === 'elements' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button onClick={() => insertSyntax('INT. ')} className="sw-ribbon-btn">🎬 Heading</button>
              <button onClick={() => insertSyntax('\n\nAction text...\n')} className="sw-ribbon-btn">📝 Action</button>
              <button onClick={() => insertSyntax('\n\nCHARACTER\n')} className="sw-ribbon-btn">👤 Character</button>
              <button onClick={() => insertSyntax('Dialogue text\n')} className="sw-ribbon-btn">💬 Dialogue</button>
              <button onClick={() => insertSyntax('(parenthetical)\n')} className="sw-ribbon-btn">🗣️ Parenthetical</button>
              <button onClick={() => handleFormat('dual')} className="sw-ribbon-btn" style={{ color: '#38bdf8' }}>👥 Dual</button>
              <button onClick={() => insertSyntax('\n\nCUT TO:\n')} className="sw-ribbon-btn">⚡ Transition</button>
              <button onClick={() => { insertSyntax('\n[  ]\n'); editorRef.current?.focus(); }} className="sw-toolbar-btn">🔖 Beat</button>
              <button onClick={() => insertSyntax('[[Note: Your note here]]\n')} className="sw-ribbon-btn">📌 ScriptNote</button>
              <button onClick={() => insertSyntax('[[Image: path/to/img.png]]\n')} className="sw-ribbon-btn">🖼️ Image</button>
            </div>
          )}

          {/* TAB 3: VIEWS & SPLIT */}
          {activeRibbonTab === 'views' && (
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '4px', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <button className={`sw-ribbon-btn ${activeView === 'editor' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('editor')}>📝 Editor</button>
                <button className={`sw-ribbon-btn ${activeView === 'preview' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('preview')}>👁️ Scene View</button>
                <button className={`sw-ribbon-btn ${activeView === 'beats' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('beats')}>🗂️ Beat Board</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', borderRight: '1px solid #374151', paddingRight: '12px' }}>
                <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>Panels:</span>
                <button className={`sw-ribbon-btn ${leftPanelVisible ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setLeftPanelVisible(!leftPanelVisible)}>{leftPanelVisible ? '◀ Outline' : '▶ Outline'}</button>
                <button className={`sw-ribbon-btn ${navigatorVisible ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setNavigatorVisible(!navigatorVisible)}>🧭 Navigator</button>
              </div>

              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>Split:</span>
                <button className={`sw-ribbon-btn ${splitMode === 'none' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('none')}>None</button>
                <button className={`sw-ribbon-btn ${splitMode === 'vertical' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('vertical')}>Split V</button>
                <button className={`sw-ribbon-btn ${splitMode === 'horizontal' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('horizontal')}>Split H</button>
              </div>
            </div>
          )}

          {/* TAB 4: 3D & PREVIS */}
          {activeRibbonTab === 'unreal' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button onClick={handleSendToVideo} className="sw-toolbar-btn" style={{ background: '#2ea043', color: '#fff' }}>
                🎥 Send to Video Studio
              </button>
              <button className="sw-ribbon-btn" onClick={() => handleExportUnreal('csv')} disabled={isExporting} style={{ background: '#2563eb', color: '#fff' }}>
                🎮 Export CSV (Data Table)
              </button>
              <button className="sw-ribbon-btn" onClick={() => handleExportUnreal('python')} disabled={isExporting} style={{ background: '#047857', color: '#fff' }}>
                🎮 Export Python (Sequencer)
              </button>
            </div>
          )}

          {/* TAB 5: PRODUCTION & CMS */}
          {activeRibbonTab === 'production' && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button className="sw-ribbon-btn" onClick={() => setShowCharacterVault(true)} style={{ color: '#facc15' }}>
                🎭 Character Vault
              </button>
              <button className="sw-ribbon-btn" onClick={handleGenerateCoverage} disabled={isGeneratingCoverage}>
                {isGeneratingCoverage ? '⏳ Analyzing...' : '📊 Script Coverage'}
              </button>
              <button className="sw-ribbon-btn" onClick={() => setShowAnalyticsOverlay(!showAnalyticsOverlay)} style={{ color: showAnalyticsOverlay ? '#facc15' : 'inherit' }}>
                📈 Analytics
              </button>
              <button className="sw-ribbon-btn" onClick={() => setShowProductionBreakdown(true)}>
                🎬 Film Budget
              </button>
              <button className="sw-ribbon-btn" onClick={() => setShowStagePlayBreakdown(true)}>
                🎭 Theatrical Budget
              </button>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', borderLeft: '1px solid #374151', paddingLeft: '8px', marginLeft: '4px' }}>
                <button 
                  className="sw-ribbon-btn" 
                  onClick={() => setIsRevisionMode(!isRevisionMode)} 
                  style={{ background: isRevisionMode ? '#374151' : 'transparent', color: isRevisionMode ? '#f87171' : 'inherit', fontWeight: isRevisionMode ? 'bold' : 'normal' }}
                >
                  {isRevisionMode ? '🔴 Revision ON' : '⚪ Revision OFF'}
                </button>
                {isRevisionMode && (
                  <select 
                    value={revisionColor} 
                    onChange={e => setRevisionColor(e.target.value)} 
                    className="sw-panel-input" 
                    style={{ background: '#111827', color: '#fff', border: '1px solid #374151', padding: '2px 4px', fontSize: '0.8rem', borderRadius: '4px' }}
                  >
                    <option value="blue">Blue</option>
                    <option value="pink">Pink</option>
                    <option value="yellow">Yellow</option>
                    <option value="green">Green</option>
                  </select>
                )}
              </div>
              <button className="sw-ribbon-btn" onClick={handleTitlePage} style={{ borderLeft: '1px solid #374151', paddingLeft: '12px', marginLeft: '4px' }}>
                📄 Title Page
              </button>
              <button className="sw-ribbon-btn" onClick={exportFDX} style={{ color: '#38bdf8' }}>
                ⬇️ Export .fdx
              </button>
              <button className="sw-ribbon-btn" onClick={exportPDF} style={{ color: '#f87171' }}>
                📄 Export .pdf
              </button>
              <button className="sw-ribbon-btn" onClick={handlePublishToCMS} style={{ background: '#238636', color: 'white', border: 'none' }}>
                🚀 Publish to CMS
              </button>
            </div>
          )}
        </div>
      )}

      {/* 2.5 Live AI Adaptation Status & Progress Bar */}
      <div style={{ flexShrink: 0 }}>
        <AdaptationStatusBar 
          backendUrl={BACKEND_URL}
          onSwitchToProject={handleSwitchProject}
          onRefreshScreenplay={async (proj) => {
            if (proj === currentProject) {
              await loadScreenplay(proj);
            }
          }}
        />
      </div>

      {/* 2.6 Dedicated Project Audio Drama Adaptation Player */}
      <ProjectAudioPlayer 
        projectName={currentProject}
        backendUrl={BACKEND_URL}
        isOpen={showAudioPlayer}
        onClose={() => setShowAudioPlayer(false)}
      />

      {/* 2.8 PERMANENT HARDCODED PAGE NAVIGATION & VIEW DECK (ALWAYS VISIBLE AT TOP) */}
      <div className="sw-permanent-page-bar" style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '5px 16px',
        background: '#0e1726',
        borderBottom: '1px solid #1f2937',
        color: '#e5e7eb',
        fontSize: '0.85rem',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        {/* Left: View Mode Quick Toggles */}
        <div style={{ display: 'flex', gap: '3px', background: '#0a0f1d', padding: '2px', borderRadius: '6px', border: '1px solid #1e293b' }}>
          <button 
            onClick={() => { setActiveView('editor'); setSplitMode('none'); }} 
            style={{
              background: activeView === 'editor' && splitMode === 'none' ? '#2563eb' : 'transparent',
              color: activeView === 'editor' && splitMode === 'none' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: activeView === 'editor' && splitMode === 'none' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Interactive AST Screenplay Editor"
          >
            📝 Editor
          </button>
          <button 
            onClick={() => { setActiveView('preview'); setSplitMode('none'); }} 
            style={{
              background: activeView === 'preview' && splitMode === 'none' ? '#2563eb' : 'transparent',
              color: activeView === 'preview' && splitMode === 'none' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: activeView === 'preview' && splitMode === 'none' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Paginated 8.5 x 11 Finished Script Page View"
          >
            📄 Page View
          </button>
          <button 
            onClick={() => { setSplitMode(splitMode === 'vertical' ? 'none' : 'vertical'); }} 
            style={{
              background: splitMode === 'vertical' ? '#3b82f6' : 'transparent',
              color: splitMode === 'vertical' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: splitMode === 'vertical' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Toggle Split View (Side-by-Side Editor & Pages)"
          >
            🪟 Split
          </button>
          <button 
            onClick={() => { setActiveView('beats'); setSplitMode('none'); }} 
            style={{
              background: activeView === 'beats' && splitMode === 'none' ? '#2563eb' : 'transparent',
              color: activeView === 'beats' && splitMode === 'none' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '3px 10px',
              borderRadius: '4px',
              fontSize: '0.8rem',
              fontWeight: activeView === 'beats' && splitMode === 'none' ? 'bold' : 'normal',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Visual Story Beat Board"
          >
            🗂️ Beat Board
          </button>
        </div>

        {/* Center: HARDCODED PERMANENT PAGE NAVIGATION TOOLS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#0a0f1d', padding: '3px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
          <button 
            onClick={() => handleJumpToPage(1)} 
            disabled={viewerCurrentPage <= 1}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage <= 1 ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="First Page (Page 1)"
          >
            ⏮ First
          </button>
          <button 
            onClick={() => handleJumpToPage(viewerCurrentPage - 1)} 
            disabled={viewerCurrentPage <= 1}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage <= 1 ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="Previous Page"
          >
            ◀ Prev
          </button>
          
          <span style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: '500' }}>Page</span>
          <input 
            type="number"
            min="1"
            max={totalScriptPages}
            value={viewerCurrentPage}
            onChange={(e) => {
              const val = parseInt(e.target.value);
              if (!isNaN(val)) {
                handleJumpToPage(val);
              }
            }}
            style={{ width: '44px', padding: '2px 4px', textAlign: 'center', background: '#020617', color: '#facc15', border: '1px solid #334155', borderRadius: '4px', fontWeight: 'bold', fontSize: '0.85rem' }}
          />
          <span style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: '500' }}>of {totalScriptPages}</span>

          <button 
            onClick={() => handleJumpToPage(viewerCurrentPage + 1)} 
            disabled={viewerCurrentPage >= totalScriptPages}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage >= totalScriptPages ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="Next Page"
          >
            Next ▶
          </button>
          <button 
            onClick={() => handleJumpToPage(totalScriptPages)} 
            disabled={viewerCurrentPage >= totalScriptPages}
            style={{ background: '#1e293b', color: '#fff', border: '1px solid #334155', padding: '3px 8px', borderRadius: '4px', cursor: viewerCurrentPage >= totalScriptPages ? 'not-allowed' : 'pointer', fontSize: '0.8rem' }}
            title="Last Page"
          >
            Last ⏭
          </button>

          {/* Quick Page Doctor / Review Trigger */}
          <button 
            onClick={() => handleProofPage(viewerCurrentPage)} 
            disabled={isReviewingPage}
            style={{
              background: 'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)',
              color: '#fff',
              border: '1px solid #a855f7',
              padding: '3px 10px',
              borderRadius: '4px',
              cursor: isReviewingPage ? 'wait' : 'pointer',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: '0 2px 8px rgba(139, 92, 246, 0.4)',
              marginLeft: '6px'
            }}
            title="Review and format-proof the current page with AI Script Doctor (or type !proof in editor)"
          >
            {isReviewingPage ? '⏳ Proofing...' : `🔍 Review Pg ${viewerCurrentPage}`}
          </button>
        </div>

        {/* Right: Scene Quick Jump Dropdown & Search */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>🎬 Scene:</span>
            <select 
              onChange={(e) => {
                const selectedIndex = parseInt(e.target.value);
                if (!isNaN(selectedIndex) && parsed?.beats?.[selectedIndex]) {
                  const beat = parsed.beats[selectedIndex];
                  if (viewerRef.current) {
                    viewerRef.current.scrollToScene(beat);
                  } else {
                    setActiveView('preview');
                    setTimeout(() => viewerRef.current?.scrollToScene(beat), 100);
                  }
                }
              }}
              defaultValue=""
              style={{ background: '#0a0f1d', color: '#38bdf8', border: '1px solid #1e293b', padding: '3px 8px', borderRadius: '4px', maxWidth: '180px', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              <option value="" disabled>Select Scene...</option>
              {(parsed?.beats || []).map((b, idx) => (
                <option key={idx} value={idx}>
                  {idx + 1}. {b.heading.substring(0, 24)}... (p.{Math.floor(b.page)})
                </option>
              ))}
            </select>
          </div>

          {/* Search Script with Match Counter & Enter / Shift+Enter Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', background: '#0a0f1d', borderRadius: '4px', border: '1px solid #1e293b', padding: '1px 6px', gap: '4px' }}>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>🔍</span>
            <input 
              type="text" 
              value={viewerSearch} 
              onChange={(e) => setViewerSearch(e.target.value)} 
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  if (e.shiftKey) {
                    viewerRef.current?.handlePrevSearch();
                  } else {
                    viewerRef.current?.handleNextSearch();
                  }
                }
              }}
              placeholder="Search (Enter/Shift+Enter)..." 
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.8rem', width: '140px', outline: 'none' }}
            />
            {viewerRef.current?.matchedCount > 0 && (
              <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 'bold' }}>
                {viewerRef.current.activeMatchIndex || 1}/{viewerRef.current.matchedCount}
              </span>
            )}
            {viewerSearch && (
              <button onClick={() => setViewerSearch('')} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '0 2px' }}>&times;</button>
            )}
          </div>

          {/* Zoom Stepper */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px', background: '#0a0f1d', padding: '2px 4px', borderRadius: '4px', border: '1px solid #1e293b' }}>
            <button 
              onClick={() => setZoomLevel(Math.max(50, zoomLevel - 10))} 
              style={{ background: 'transparent', color: '#94a3b8', border: 'none', padding: '1px 5px', cursor: 'pointer', fontSize: '0.8rem' }}
              title="Zoom Out"
            >-</button>
            <span style={{ fontSize: '0.75rem', color: '#e2e8f0', minWidth: '34px', textAlign: 'center' }}>{zoomLevel}%</span>
            <button 
              onClick={() => setZoomLevel(Math.min(175, zoomLevel + 10))} 
              style={{ background: 'transparent', color: '#94a3b8', border: 'none', padding: '1px 5px', cursor: 'pointer', fontSize: '0.8rem' }}
              title="Zoom In"
            >+</button>
          </div>

          {/* Audio Drama Toggle */}
          <button
            onClick={() => setShowAudioPlayer(!showAudioPlayer)}
            style={{
              background: showAudioPlayer ? '#1e3a8a' : '#1e293b',
              color: '#93c5fa',
              border: '1px solid #3b82f6',
              borderRadius: '4px',
              padding: '3px 10px',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Toggle ElevenLabs Audio Drama Master Player"
          >
            🎙️ Audio Drama
          </button>

          {/* Dedicated Script & Memoir Co-Pilot Assistant Toggle */}
          <button
            onClick={() => setShowScriptAssistant(!showScriptAssistant)}
            style={{
              background: showScriptAssistant ? '#2563eb' : '#1e293b',
              color: '#38bdf8',
              border: '1px solid #38bdf8',
              borderRadius: '4px',
              padding: '3px 10px',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: showScriptAssistant ? '0 0 12px rgba(56, 189, 248, 0.4)' : 'none'
            }}
            title="Open dedicated Script & Memoir AI Assistant connected to this project's isolated Vector DB"
          >
            🤖 Script Co-Pilot
          </button>
        </div>
      </div>

      {/* 3. Main Workspace */}
      <div className="sw-workspace" style={{ flex: 1, width: '100%', height: 'calc(100% - 40px)', maxHeight: '100%', minHeight: 0, display: 'flex', flexDirection: 'row', flexWrap: 'nowrap', overflow: 'hidden' }}>
        
        {/* Outline Panel (Left) */}
        {leftPanelVisible && !zenMode && (
          <div className="sw-left-panel" style={{ width: '220px', minWidth: '220px', flexShrink: 0, background: '#111827', borderRight: '1px solid #1f2937', padding: '12px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button className="sw-ribbon-btn" onClick={() => setOutlineMode('outline1')} style={{ background: outlineMode === 'outline1' ? '#1f2937' : 'transparent', flex: 1, border: '1px solid #1f2937' }}>Outline 1</button>
              <button className="sw-ribbon-btn" onClick={() => setOutlineMode('outline2')} style={{ background: outlineMode === 'outline2' ? '#1f2937' : 'transparent', flex: 1, border: '1px solid #1f2937' }}>Outline 2</button>
            </div>

            {/* Projects */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h4 className="sw-panel-header" style={{ color: '#facc15', margin: 0 }}>📁 Projects</h4>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button 
                  onClick={() => setShowNewProjectModal(true)} 
                  style={{ background: '#238636', color: '#fff', border: 'none', borderRadius: '4px', padding: '2px 8px', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}
                  title="Create a new Screenplay Project"
                >
                  + New
                </button>
                <button 
                  onClick={() => setLeftPanelVisible(false)} 
                  style={{ background: '#374151', color: '#9ca3af', border: 'none', borderRadius: '4px', padding: '2px 6px', fontSize: '0.75rem', cursor: 'pointer' }}
                  title="Close Outline Drawer"
                >
                  ✕
                </button>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', gap: '4px', marginBottom: '6px' }}>
                <select value={currentProject} onChange={(e) => handleSwitchProject(e.target.value)} className="sw-panel-input" style={{ flex: 1 }}>
                  {projects.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                {currentProject !== 'Default Project' && (
                  <button 
                    onClick={handleDeleteCurrentProject} 
                    style={{ background: '#ef444422', border: '1px solid #ef444466', color: '#ef4444', padding: '0 6px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                    title="Delete current project"
                  >
                    🗑️
                  </button>
                )}
              </div>
              <button onClick={handleImportClick} style={{ width: '100%', background: 'transparent', border: '1px solid #facc15', color: '#facc15', padding: '4px', cursor: 'pointer', fontSize: '0.8rem', borderRadius: '4px' }}>
                + Import (.pdf, .docx, .epub, .fdx, etc.)
              </button>
              <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".pdf,.docx,.doc,.epub,.txt,.rtf,.md,.markdown,.fountain,.fdx" onChange={handleFileChange} />
            </div>

            {/* Adaptation Progress */}
            {isAdapting && adaptProgress && (
              <div style={{ marginBottom: '16px', background: '#374151', padding: '12px', borderRadius: '6px' }}>
                <div style={{ color: '#facc15', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '4px' }}>AI ADAPTATION IN PROGRESS...</div>
                <div style={{ width: '100%', background: '#1f2937', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${adaptProgress.progress}%`, background: '#facc15', height: '100%', transition: 'width 0.5s' }} />
                </div>
                <div style={{ color: '#9ca3af', fontSize: '0.7rem', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Chunk {adaptProgress.current_chunk || 0} of {adaptProgress.total_chunks || 0}</span>
                  <span>{adaptProgress.progress || 0}%</span>
                </div>
              </div>
            )}

            {/* Git Branching */}
            <h4 className="sw-panel-header" style={{ color: '#4ade80', margin: '0 0 8px 0' }}>🌿 Branches</h4>
            <div style={{ marginBottom: '16px' }}>
              <select value={currentBranch} onChange={(e) => setCurrentBranch(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '8px' }}>
                {branches.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
              <div style={{ display: 'flex', gap: '4px' }}>
                <input type="text" value={newBranchName} onChange={(e) => setNewBranchName(e.target.value)} placeholder="New branch..." className="sw-panel-input" style={{ flex: 1 }} />
                <button onClick={handleCreateBranch} style={{ background: '#38bdf8', color: '#000', border: 'none', padding: '0 8px', fontWeight: 'bold', cursor: 'pointer', borderRadius: '3px' }}>+</button>
              </div>
            </div>

            {/* Sprints */}
            <h4 className="sw-panel-header" style={{ color: '#38bdf8', margin: '0 0 8px 0' }}>⏱️ Sprints</h4>
            {!activeSprint ? (
              <div style={{ marginBottom: '16px' }}>
                <input type="text" value={sprintName} onChange={(e) => setSprintName(e.target.value)} placeholder="Sprint name..." className="sw-panel-input" style={{ width: '100%', marginBottom: '4px', boxSizing: 'border-box' }} />
                <button onClick={handleStartSprint} style={{ width: '100%', background: '#a78bfa', color: '#000', padding: '4px', border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 'bold', borderRadius: '3px' }}>Start Sprint</button>
              </div>
            ) : (
              <div className="sw-sprint-active" style={{ marginBottom: '16px' }}>
                <div style={{ color: '#a78bfa', fontSize: '0.8rem', marginBottom: '4px', fontWeight: 'bold' }}>▶️ {activeSprint.name}</div>
                <button onClick={handleEndSprint} style={{ width: '100%', background: 'transparent', border: '1px solid #a78bfa', color: '#a78bfa', padding: '4px', cursor: 'pointer', fontSize: '0.8rem', borderRadius: '3px' }}>End Sprint</button>
              </div>
            )}
            
            {/* Outline Scenes with Search & Direct Jump */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <h4 className="sw-panel-header" style={{ color: '#9ca3af', margin: 0 }}>🎬 Scenes ({filteredBeats.length})</h4>
            </div>
            <input 
              type="text" 
              value={sceneSearch} 
              onChange={(e) => setSceneSearch(e.target.value)} 
              placeholder="🔍 Filter scenes..." 
              className="sw-panel-input" 
              style={{ width: '100%', marginBottom: '8px', boxSizing: 'border-box', fontSize: '0.75rem', padding: '4px 6px' }}
            />
            <div className="sw-scene-list" style={{ flex: 1, overflowY: 'auto' }}>
                {filteredBeats.map((b, i) => (
                    <div 
                      key={i} 
                      className="sw-scene-item" 
                      onClick={() => handleJumpToScene(b)}
                      style={{ cursor: 'pointer', padding: '4px 6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', borderBottom: '1px solid #1f2937', transition: 'background 0.2s ease' }}
                    >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '130px' }}>
                          {b.heading}
                        </span>
                        <span style={{ color: '#9ca3af', fontSize: '0.7rem' }}>p.{Math.floor(b.page)}</span>
                    </div>
                ))}
                {filteredBeats.length === 0 && (
                    <div style={{ color: '#6b7280', fontSize: '0.75rem', textAlign: 'center', padding: '8px' }}>
                      No matching scenes
                    </div>
                )}
            </div>
          </div>
        )}

        {/* Central Area (Supports Split) */}
        <div className="sw-central-area" style={{ flex: 1, flexShrink: 1, width: leftPanelVisible && !zenMode ? 'calc(100% - 220px)' : '100%', height: '100%', maxHeight: '100%', minHeight: 0, display: 'flex', overflow: 'hidden', flexWrap: 'nowrap', flexDirection: splitMode === 'horizontal' ? 'column' : 'row' }}>
            
            {/* Primary View (Editor) */}
            {(activeView === 'editor' || splitMode !== 'none') && (
                <div className="sw-editor-container" style={{ flex: 1, height: '100%', maxHeight: '100%', minHeight: 0, display: 'flex', overflow: 'hidden', borderRight: splitMode === 'vertical' ? '1px solid #1f2937' : 'none', borderBottom: splitMode === 'horizontal' ? '1px solid #1f2937' : 'none' }}>
                    <ScreenplayEditor
                        ast={ast}
                        onChange={handleAstChange}
                        zoomLevel={zoomLevel}
                        onGhostwriter={(index) => handleGhostwriter(index)}
                        characters={characters}
                        currentPage={viewerCurrentPage}
                        onPageChange={(p) => setViewerCurrentPage(p)}
                        onProofPage={(p) => handleProofPage(p)}
                        isRevisionMode={isRevisionMode}
                        revisionColor={revisionColor}
                    />
                </div>
            )}

            {/* Secondary View (Preview or Beats) */}
            {(activeView !== 'editor' || splitMode !== 'none') && (
                <div className="sw-preview-container" style={{ flex: 1, height: '100%', background: '#0a0a0a', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    {(activeView === 'preview' || (splitMode !== 'none' && activeView !== 'beats')) ? (
                         <ScreenplayViewer
                             ref={viewerRef}
                             ast={ast}
                             beats={parsed?.beats || []}
                             zoomLevel={zoomLevel}
                             currentPage={viewerCurrentPage}
                             onPageChange={(p) => setViewerCurrentPage(p)}
                             searchQuery={viewerSearch}
                             showInternalHeader={false}
                             onSwitchToEditor={(blockId) => {
                                 setActiveView('editor');
                                 if (blockId) {
                                     setTimeout(() => {
                                         const el = document.getElementById(`sw-block-${blockId}`);
                                         if (el) {
                                             el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                             el.focus();
                                         }
                                     }, 100);
                                 }
                             }}
                         />
                    ) : (
                         <div className="sw-beat-board" style={{ padding: `${20 * (zoomLevel / 100)}px`, gap: `${20 * (zoomLevel / 100)}px` }}>
                            <div className="sw-beat-timeline" />
                            
                            {(parsed?.beats || []).map((beat, idx) => {
                                const scale = zoomLevel / 100;
                                const isDragging = draggedBeatIndex === idx;
                                return (
                                    <div 
                                        key={idx} 
                                        draggable
                                        onDragStart={(e) => handleDragStart(e, idx)}
                                        onDragOver={handleDragOver}
                                        onDrop={(e) => handleDrop(e, idx)}
                                        onClick={() => handleJumpToScene(beat)}
                                        className="sw-beat-card"
                                        style={{
                                            width: `${140 * scale}px`,
                                            height: `${110 * scale}px`,
                                            background: isDragging ? '#1a1a1a' : '#1e1e1e',
                                            border: `2px solid ${isDragging ? '#555' : 'rgba(56, 189, 248, 0.4)'}`,
                                            padding: `${10 * scale}px`,
                                            boxShadow: isDragging ? 'none' : '0 4px 12px rgba(56, 189, 248, 0.1)',
                                            opacity: isDragging ? 0.5 : 1,
                                            cursor: 'pointer'
                                        }}
                                    >
                                        <div className="sw-beat-index" style={{ top: `-${25 * scale}px`, fontSize: `${12 * scale}px` }}>
                                            {idx + 1}
                                        </div>
                                        <div style={{ fontSize: `${18 * scale}px`, marginBottom: `${4 * scale}px` }}>{beat.emoji || '🎬'}</div>
                                        <div className="sw-beat-heading" style={{ fontSize: `${11 * scale}px` }}>
                                            {beat.heading}
                                        </div>
                                        <div className="sw-beat-page" style={{ fontSize: `${10 * scale}px` }}>
                                            p.{Math.floor(beat.page)}
                                        </div>
                                        
                                        {/* Video Attachment Logic */}
                                        <div style={{ marginTop: 'auto', borderTop: '1px solid #333', paddingTop: '4px' }}>
                                            {projectMetadata?.beat_videos?.[beat.id] ? (
                                                <div style={{ fontSize: `${9 * scale}px`, color: '#4ade80', textAlign: 'center', background: '#112211', padding: '2px', borderRadius: '4px' }}>
                                                    ✅ Video Generated
                                                </div>
                                            ) : (
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); handleAnimateBeat(beat); }}
                                                    disabled={animatingBeats[beat.id]}
                                                    style={{ width: '100%', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', fontSize: `${9 * scale}px`, padding: '2px', cursor: animatingBeats[beat.id] ? 'not-allowed' : 'pointer' }}
                                                >
                                                    {animatingBeats[beat.id] ? '⏳ Generating...' : '🎥 Animate Scene'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                         </div>
                    )}
                </div>
            )}

        </div>

        {/* Navigator Panel (Right) */}
        {navigatorVisible && !zenMode && (
          <div className="sw-left-panel" style={{ width: '240px', minWidth: '240px', background: '#111827', borderLeft: '1px solid #1f2937', borderRight: 'none', padding: '12px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h4 className="sw-panel-header" style={{ color: '#38bdf8', margin: 0 }}>🧭 Navigator ({filteredBeats.length})</h4>
              <button onClick={() => setNavigatorVisible(false)} style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '1.2rem' }}>&times;</button>
            </div>

            <input 
              type="text" 
              value={sceneSearch} 
              onChange={(e) => setSceneSearch(e.target.value)} 
              placeholder="🔍 Search scenes & characters..." 
              className="sw-panel-input" 
              style={{ width: '100%', marginBottom: '12px', boxSizing: 'border-box', fontSize: '0.8rem', padding: '4px 8px' }}
            />

            <div className="sw-scene-list" style={{ flex: 1, overflowY: 'auto' }}>
                {filteredBeats.map((b, i) => (
                    <div 
                        key={i} 
                        className="sw-scene-item" 
                        style={{ cursor: 'pointer', padding: '8px', borderBottom: '1px solid #1f2937', display: 'flex', alignItems: 'center', gap: '8px', transition: 'background 0.2s ease', borderRadius: '4px' }}
                        onClick={() => handleJumpToScene(b)}
                    >
                        <span style={{ fontSize: '1.2rem' }}>{b.emoji || '🎬'}</span>
                        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
                           <span style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                             {b.heading}
                           </span>
                           <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>Page {Math.floor(b.page)}</span>
                        </div>
                    </div>
                ))}
                {filteredBeats.length === 0 && (
                    <div style={{ color: '#6b7280', textAlign: 'center', marginTop: '20px', fontSize: '0.9rem' }}>
                        No scenes found.
                    </div>
                )}
            </div>
          </div>
        )}
      </div>

      {/* 4. Bottom Status & Diagnostics Telemetry Panel */}
      <div className="sw-bottom-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 16px', background: '#111827', borderTop: '1px solid #1f2937', fontSize: '0.8rem', color: '#9ca3af' }}>
        <div style={{ display: 'flex', gap: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ color: '#fff', fontWeight: 'bold' }}>🎬 SCRIPT TELEMETRY:</span>
          <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>📜 {scriptDiag.pages} Pages (~{scriptDiag.runtimeStr} screen time)</span>
          <span style={{ color: '#4ade80' }}>⚖️ {scriptDiag.dialoguePct}% Dialogue / {scriptDiag.actionPct}% Action</span>
          <span style={{ color: '#facc15' }}>🎭 {scriptDiag.characterCount} Roles</span>
          <span style={{ color: '#e2e8f0' }}>🎬 {scriptDiag.sceneCount} Scenes</span>
          <span style={{ color: '#a78bfa' }}>🌿 Branch: {currentBranch}</span>
          {isGhostwriting && <span style={{ color: '#facc15', fontStyle: 'italic' }}>🤖 Ghostwriter is thinking...</span>}
        </div>

        {/* Page Jump Control */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>Jump to Page:</span>
          <input 
            type="number" 
            min="1" 
            max={totalScriptPages}
            value={pageJumpInput} 
            onChange={(e) => setPageJumpInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleJumpToPage(parseInt(pageJumpInput));
              }
            }}
            placeholder="Pg #" 
            className="sw-panel-input" 
            style={{ width: '55px', padding: '2px 6px', textAlign: 'center', fontSize: '0.8rem', boxSizing: 'border-box' }}
          />
          <button 
            onClick={() => handleJumpToPage(parseInt(pageJumpInput))}
            style={{ background: '#38bdf8', color: '#000', border: 'none', borderRadius: '3px', padding: '2px 8px', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}
          >
            Go
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Zoom: {zoomLevel}%</span>
          <input 
            type="range" 
            min="50" max="200" step="10" 
            value={zoomLevel} 
            onChange={(e) => setZoomLevel(parseInt(e.target.value))} 
            style={{ width: '90px', cursor: 'pointer' }}
          />
        </div>
      </div>

      {/* ── Create New Screenplay Project Modal ── */}
      {showNewProjectModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 3000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(6px)'
        }}>
          <div style={{
            background: '#1f2937', border: '1px solid #374151', padding: '24px',
            borderRadius: '12px', width: '540px', maxWidth: '92vw',
            boxShadow: '0 16px 48px rgba(0,0,0,0.7)', color: '#fff'
          }}>
            <h3 style={{ color: '#facc15', marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem' }}>
              🎬 Create New Screenplay Project
            </h3>
            
            <p style={{ color: '#9ca3af', fontSize: '0.85rem', lineHeight: '1.4', marginBottom: '16px' }}>
              Initialize a dedicated Hollywood screenplay workspace with professional 8.5" x 11" US Letter geometry, title page metadata, and industry-standard element formatting.
            </p>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>
                Project / Script Title:
              </label>
              <input 
                type="text" 
                value={newProjectName} 
                onChange={(e) => setNewProjectName(e.target.value)} 
                placeholder="e.g. Neon Horizon, Untitled Feature"
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#fff', fontSize: '0.9rem', boxSizing: 'border-box' }} 
                autoFocus
              />
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>
                Screenwriter / Author:
              </label>
              <input 
                type="text" 
                value={newProjectAuthor} 
                onChange={(e) => setNewProjectAuthor(e.target.value)} 
                placeholder="Author Name"
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#fff', fontSize: '0.9rem', boxSizing: 'border-box' }} 
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ color: '#d1d5db', display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>
                Starting Format & Template:
              </label>
              <select 
                value={newProjectTemplate} 
                onChange={(e) => setNewProjectTemplate(e.target.value)} 
                style={{ width: '100%', padding: '8px 10px', background: '#111827', border: '1px solid #374151', borderRadius: '6px', color: '#38bdf8', fontSize: '0.9rem', boxSizing: 'border-box' }}
              >
                <option value="feature">🎬 Hollywood Feature Film (3-Act Spec Script)</option>
                <option value="tv_drama">📺 TV Pilot (1-Hour Drama with Act Breaks)</option>
                <option value="tv_comedy">🎭 TV Pilot (30-Minute Comedy / Sitcom)</option>
                <option value="stage_play">🏛️ Theatrical Stage Play (Acts & Scenes)</option>
                <option value="audio_drama">🎙️ Audio Drama / Scripted Podcast</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                onClick={() => setShowNewProjectModal(false)} 
                style={{ background: 'transparent', border: '1px solid #555', color: '#fff', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button 
                onClick={handleCreateNewProject} 
                style={{ background: '#238636', color: '#fff', border: 'none', padding: '8px 20px', fontWeight: 'bold', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                ✨ Create Project
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Page Review & Format Doctor Modal ── */}
      {showPageReviewModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.85)', zIndex: 3000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(8px)'
        }}>
          <div style={{
            background: '#111827', border: '1px solid #374151', borderRadius: '12px',
            width: '90%', maxWidth: '1100px', maxHeight: '90vh',
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            boxShadow: '0 20px 60px rgba(0,0,0,0.8)'
          }}>
            {/* Header */}
            <div style={{ padding: '16px 24px', background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '1.4rem' }}>📖</span>
                <div>
                  <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem', fontWeight: 'bold' }}>
                    AI Page Review & Format Doctor — Page {reviewPageNum} of {totalScriptPages}
                  </h3>
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '2px' }}>
                    Review, standardize Fountain formatting, capitalize character cues, and polish dialogue.
                  </div>
                </div>
              </div>

              {/* Page Stepper Navigation */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={() => handleProofPage(Math.max(1, reviewPageNum - 1))}
                  disabled={reviewPageNum <= 1 || isReviewingPage}
                  style={{ background: '#334155', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', cursor: reviewPageNum <= 1 ? 'not-allowed' : 'pointer' }}
                >
                  ◀ Prev Page
                </button>
                <span style={{ color: '#facc15', fontWeight: 'bold', fontSize: '0.85rem' }}>Page {reviewPageNum}</span>
                <button
                  onClick={() => handleProofPage(Math.min(totalScriptPages, reviewPageNum + 1))}
                  disabled={reviewPageNum >= totalScriptPages || isReviewingPage}
                  style={{ background: '#334155', color: '#fff', border: 'none', borderRadius: '4px', padding: '4px 10px', fontSize: '0.8rem', cursor: reviewPageNum >= totalScriptPages ? 'not-allowed' : 'pointer' }}
                >
                  Next Page ▶
                </button>
                <button
                  onClick={() => setShowPageReviewModal(false)}
                  style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer', marginLeft: '12px' }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Status bar */}
            <div style={{ padding: '8px 24px', background: '#0f172a', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
              <span style={{ color: isReviewingPage ? '#facc15' : '#4ade80' }}>
                {isReviewingPage ? `⏳ ${reviewStatusMessage}` : '✅ Page formatting analyzed and ready.'}
              </span>
              <span style={{ color: '#64748b' }}>Tip: Type <code>!proof</code> anywhere in a block to trigger this instantly</span>
            </div>

            {/* Main Side-by-Side Comparison Body */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', padding: '16px 24px', gap: '20px' }}>
              {/* Left: Original Page */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#090d16', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px', overflow: 'hidden' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Original Page {reviewPageNum} Content
                </div>
                <textarea
                  readOnly
                  value={reviewOriginalFountain}
                  style={{
                    flex: 1, width: '100%', background: '#020617', color: '#cbd5e1',
                    border: '1px solid #1e293b', borderRadius: '4px', padding: '12px',
                    fontFamily: '"Courier Prime", Courier, monospace', fontSize: '13px',
                    lineHeight: '1.4', resize: 'none', outline: 'none'
                  }}
                />
              </div>

              {/* Right: Suggested Proof / Format Fix */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#090d16', border: '1px solid #3b82f6', borderRadius: '8px', padding: '12px', overflow: 'hidden' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ color: '#38bdf8', fontSize: '0.8rem', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    ✨ AI Proofed & Formatted Screenplay
                  </span>
                  <span style={{ color: '#4ade80', fontSize: '0.75rem' }}>Editable preview</span>
                </div>
                <textarea
                  value={reviewSuggestedFountain}
                  onChange={(e) => setReviewSuggestedFountain(e.target.value)}
                  placeholder={isReviewingPage ? "Generating Hollywood formatted draft..." : "Formatted screenplay will appear here..."}
                  style={{
                    flex: 1, width: '100%', background: '#020617', color: '#f8fafc',
                    border: '1px solid #334155', borderRadius: '4px', padding: '12px',
                    fontFamily: '"Courier Prime", Courier, monospace', fontSize: '13px',
                    lineHeight: '1.4', resize: 'none', outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Footer / Action Buttons */}
            <div style={{ padding: '16px 24px', background: '#1e293b', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                onClick={() => handleProofPage(reviewPageNum)}
                disabled={isReviewingPage}
                style={{ background: '#334155', color: '#cbd5e1', border: 'none', borderRadius: '6px', padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                🔄 Re-Analyze Page
              </button>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => setShowPageReviewModal(false)}
                  style={{ background: 'transparent', color: '#94a3b8', border: '1px solid #475569', borderRadius: '6px', padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleApplyPageProof(false)}
                  disabled={!reviewSuggestedFountain || isReviewingPage}
                  style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', padding: '8px 16px', fontSize: '0.85rem', fontWeight: 'bold', cursor: (!reviewSuggestedFountain || isReviewingPage) ? 'not-allowed' : 'pointer' }}
                >
                  ✅ Apply to Page {reviewPageNum}
                </button>
                <button
                  onClick={() => handleApplyPageProof(true)}
                  disabled={!reviewSuggestedFountain || isReviewingPage || reviewPageNum >= totalScriptPages}
                  style={{ background: '#22c55e', color: '#000', border: 'none', borderRadius: '6px', padding: '8px 18px', fontSize: '0.85rem', fontWeight: 'bold', cursor: (!reviewSuggestedFountain || isReviewingPage || reviewPageNum >= totalScriptPages) ? 'not-allowed' : 'pointer' }}
                >
                  ⏭ Apply & Next Page ({reviewPageNum + 1})
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Dedicated Project Script & Memoir Assistant Drawer ── */}
      <ScriptAssistantDrawer
        projectName={currentProject}
        isOpen={showScriptAssistant}
        onClose={() => setShowScriptAssistant(false)}
        onInsertScript={handleInsertScriptAssistantText}
        backendUrl={BACKEND_URL}
      />

      {/* ── Screenplay-to-Book AI Novelizer Studio Modal ── */}
      <ScriptToBookNovelizerModal
        isOpen={showNovelizerModal}
        onClose={() => setShowNovelizerModal(false)}
        backendUrl={BACKEND_URL}
        currentProject={currentProject}
        activeScript={screenplay}
      />

      {/* ── Multi-Voice AI Audio Table Read Studio Modal ── */}
      <ScreenplayTableReadModal
        isOpen={showTableReadModal}
        onClose={() => setShowTableReadModal(false)}
        screenplayText={screenplay}
        projectName={currentProject?.name || currentProject || 'Active Script'}
      />

      {/* ── Live Writing & AI Thought Telemetry Modal ── */}
      <ScriptTelemetryModal
        isOpen={showScriptTelemetryModal}
        onClose={() => setShowScriptTelemetryModal(false)}
        projectName={currentProject?.name || currentProject || 'The Mafia'}
        screenplayText={screenplay}
        ast={ast}
        totalScriptPages={totalScriptPages}
        autoSaveStatus={autoSaveStatus}
        lastSavedTime={lastSavedTime}
        backendUrl={BACKEND_URL}
      />

    </div>
  );
}
