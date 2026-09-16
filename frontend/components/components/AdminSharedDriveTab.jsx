import React, { useState, useEffect, useRef } from 'react';
import './AdminSharedDriveTab.css';
import WordDocsPaperCanvas from './WordDocsPaperCanvas.jsx';

const DEFAULT_FOLDERS = [
  '01_Screenplays_and_Scripts',
  '02_Media_and_Previs',
  '03_Audio_and_Voiceovers',
  '04_Hospitality_and_Banquets',
  '05_Corporate_and_Legal',
  '06_Marketing_and_Leads',
  '07_AI_Models_and_Backups'
];

export default function AdminSharedDriveTab({ backendUrl = 'http://localhost:8080', onNavigateTab }) {
  // Navigation & Folder State
  const [currentPath, setCurrentPath] = useState('/');
  const [breadcrumbs, setBreadcrumbs] = useState([{ name: 'Shared Cloud Drive', path: '/' }]);
  const [items, setItems] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
  const [sortBy, setSortBy] = useState('name'); // 'name' | 'modified' | 'size' | 'type'
  const [sortOrder, setSortOrder] = useState('asc'); // 'asc' | 'desc'
  const [storageStats, setStorageStats] = useState(null);

  // Drag & Drop State
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);

  // Modals & In-App Viewers
  const [showNewMenu, setShowNewMenu] = useState(false);
  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameValue, setRenameValue] = useState('');

  const [showMoveModal, setShowMoveModal] = useState(false);
  const [targetMoveFolder, setTargetMoveFolder] = useState('/');
  const [showDriveTips, setShowDriveTips] = useState(false);

  // In-Drive Document Editor State
  const [showDocEditor, setShowDocEditor] = useState(false);
  const [editingDoc, setEditingDoc] = useState({
    path: '',
    filename: '',
    content: '',
    category: 'document',
    isNew: false
  });
  const [isSavingDoc, setIsSavingDoc] = useState(false);
  const [isAiAssisting, setIsAiAssisting] = useState(false);
  const [autoSaveStatus, setAutoSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'error'
  const [lastSavedTime, setLastSavedTime] = useState(null);
  const autoSaveTimerRef = useRef(null);

  // In-Drive Media / PDF / Audio Preview Lightbox
  const [previewMedia, setPreviewMedia] = useState(null);

  // File Inputs
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const newMenuRef = useRef(null);

  // Close "+ New" dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (newMenuRef.current && !newMenuRef.current.contains(e.target)) {
        setShowNewMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch directory files & stats
  useEffect(() => {
    fetchDirectory();
    fetchStorageStats();
  }, [currentPath, searchQuery, activeCategory, sortBy, sortOrder]);

  const fetchDirectory = async () => {
    setIsLoading(true);
    setSelectedItems([]);
    try {
      const params = new URLSearchParams({
        path: currentPath,
        sort_by: sortBy,
        sort_order: sortOrder
      });
      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim());
      }
      if (activeCategory !== 'all') {
        params.append('category', activeCategory);
      }

      const res = await fetch(`${backendUrl}/api/drive/files?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
        if (data.breadcrumbs && !searchQuery.trim()) {
          setBreadcrumbs(data.breadcrumbs);
        }
      }
    } catch (err) {
      console.error('Failed to fetch shared drive files:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStorageStats = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/drive/storage_stats`);
      if (res.ok) {
        const data = await res.json();
        setStorageStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch drive storage stats:', err);
    }
  };

  // Navigation Handlers
  const handleItemClick = (item, e) => {
    if (item.is_dir) {
      setCurrentPath(item.path);
      setSearchQuery('');
    } else {
      handleOpenPreviewOrEdit(item);
    }
  };

  const handleSelect = (item, e) => {
    e.stopPropagation();
    if (e.ctrlKey || e.metaKey) {
      setSelectedItems((prev) =>
        prev.includes(item.path) ? prev.filter((p) => p !== item.path) : [...prev, item.path]
      );
    } else if (e.shiftKey && selectedItems.length > 0) {
      const lastSelected = selectedItems[selectedItems.length - 1];
      const lastIdx = items.findIndex((i) => i.path === lastSelected);
      const currIdx = items.findIndex((i) => i.path === item.path);
      if (lastIdx !== -1 && currIdx !== -1) {
        const start = Math.min(lastIdx, currIdx);
        const end = Math.max(lastIdx, currIdx);
        const range = items.slice(start, end + 1).map((i) => i.path);
        setSelectedItems(Array.from(new Set([...selectedItems, ...range])));
      }
    } else {
      setSelectedItems([item.path]);
    }
  };

  const toggleSelectAll = () => {
    if (selectedItems.length === items.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(items.map((i) => i.path));
    }
  };

  // Open Preview or In-Drive Document Editor
  const handleOpenPreviewOrEdit = async (item) => {
    const nonTextExtensions = ['.pdf', '.doc', '.docx', '.rtf', '.odt'];
    const ext = item.extension ? item.extension.toLowerCase() : '';
    const isTextDoc = (['screenplay', 'document', 'code'].includes(item.category) && !nonTextExtensions.includes(ext)) || 
      ['.txt', '.md', '.fountain', '.fdx', '.json', '.py', '.js', '.jsx', '.html', '.css', '.yaml', '.yml', '.bat', '.sh'].includes(ext);
    
    if (isTextDoc) {
      try {
        const res = await fetch(`${backendUrl}/api/drive/read_document?path=${encodeURIComponent(item.path)}`);
        if (res.ok) {
          const docData = await res.json();
          setEditingDoc({
            path: item.path,
            filename: item.name,
            content: docData.content || '',
            category: item.category,
            isNew: false
          });
          setShowDocEditor(true);
          return;
        }
      } catch (err) {
        console.error('Failed to read document:', err);
      }
    }

    // Default media/PDF preview
    setPreviewMedia({
      ...item,
      url: `${backendUrl}/api/drive/preview?path=${encodeURIComponent(item.path)}`
    });
  };

  // File Upload Handlers (Any File Type)
  const handleFilesUpload = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    setUploadProgress(`Uploading ${fileList.length} file(s)...`);

    const formData = new FormData();
    formData.append('target_path', currentPath);
    for (let i = 0; i < fileList.length; i++) {
      formData.append('files', fileList[i]);
    }

    try {
      const res = await fetch(`${backendUrl}/api/drive/upload`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        setUploadProgress('Upload complete!');
        setTimeout(() => setUploadProgress(null), 1500);
        fetchDirectory();
        fetchStorageStats();
      } else {
        setUploadProgress('Upload failed.');
        setTimeout(() => setUploadProgress(null), 2500);
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadProgress('Upload failed.');
      setTimeout(() => setUploadProgress(null), 2500);
    }
  };

  // Drag and drop event handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesUpload(e.dataTransfer.files);
    }
  };

  // Create New Folder
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    try {
      const res = await fetch(`${backendUrl}/api/drive/create_folder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_path: currentPath,
          folder_name: newFolderName.trim()
        })
      });
      if (res.ok) {
        setShowNewFolderModal(false);
        setNewFolderName('');
        fetchDirectory();
        fetchStorageStats();
      }
    } catch (err) {
      console.error('Failed to create folder:', err);
    }
  };

  // Create New Document
  const handleStartNewDocument = (docType = 'markdown') => {
    setShowNewMenu(false);
    const defaultExtensions = {
      fountain: 'Untitled_Screenplay.fountain',
      markdown: 'New_Document.md',
      text: 'Notes.txt',
      json: 'data.json',
      python: 'script.py'
    };
    const defaultTemplates = {
      fountain: 'Title: UNTITLED SCREENPLAY\nAuthor: Brett Stehouwer\n\nEXT. CITY STREET - DAY\n\nThe morning sun breaks through the skyline.\n\nBRETT\nHere is where our story begins.',
      markdown: '# Project Document\n\n**Author:** Stehouwer Publishing  \n**Date:** ' + new Date().toLocaleDateString() + '\n\n## Overview\nEnter project notes, strategy, or specifications here...',
      text: 'AI-BS Quick Notes\n------------------\n- ',
      json: '{\n  "project": "Stehouwer Publishing",\n  "status": "Active",\n  "records": []\n}',
      python: '# Stehouwer AI-BS Automation Script\nimport sys\nimport os\n\ndef main():\n    print("AI-BS Cloud Drive Hook initialized")\n\nif __name__ == "__main__":\n    main()'
    };

    setEditingDoc({
      path: '',
      filename: defaultExtensions[docType] || 'document.md',
      content: defaultTemplates[docType] || '',
      category: docType === 'fountain' ? 'screenplay' : (docType === 'python' ? 'code' : 'document'),
      docType: docType,
      isNew: true
    });
    setShowDocEditor(true);
  };

  // Save Document in Drive
  const handleSaveDocument = async () => {
    setIsSavingDoc(true);
    setAutoSaveStatus('saving');
    try {
      if (editingDoc.isNew) {
        const res = await fetch(`${backendUrl}/api/drive/create_document`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            current_path: currentPath,
            file_name: editingDoc.filename,
            content: editingDoc.content,
            doc_type: editingDoc.docType || 'markdown'
          })
        });
        if (res.ok) {
          const data = await res.json();
          setEditingDoc((prev) => ({ ...prev, path: data.path, isNew: false }));
          setAutoSaveStatus('saved');
          setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
          fetchDirectory();
          fetchStorageStats();
        } else {
          setAutoSaveStatus('error');
        }
      } else {
        const res = await fetch(`${backendUrl}/api/drive/save_document`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_path: editingDoc.path,
            content: editingDoc.content
          })
        });
        if (res.ok) {
          setAutoSaveStatus('saved');
          setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
          fetchDirectory();
          fetchStorageStats();
        } else {
          setAutoSaveStatus('error');
        }
      }
    } catch (err) {
      console.error('Failed to save document:', err);
      setAutoSaveStatus('error');
    } finally {
      setIsSavingDoc(false);
    }
  };

  // 💾 Automated Continuous Auto-Save for In-Drive Documents
  useEffect(() => {
    if (!showDocEditor || !editingDoc.content || !editingDoc.filename || editingDoc.isNew) return;

    // 1. Snapshot backup to localStorage
    try {
      const driveKey = editingDoc.path || editingDoc.filename;
      localStorage.setItem(`aibs_drive_backup_${driveKey}`, editingDoc.content);
      localStorage.setItem(`aibs_drive_backup_time_${driveKey}`, String(Date.now()));
    } catch {}

    // 2. Debounced save to backend (1500ms)
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    setAutoSaveStatus('saving');

    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/drive/save_document`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_path: editingDoc.path,
            content: editingDoc.content
          })
        });
        if (res.ok) {
          setAutoSaveStatus('saved');
          setLastSavedTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        } else {
          setAutoSaveStatus('error');
        }
      } catch (err) {
        console.warn('[Drive AutoSave] Background save error:', err.message);
        setAutoSaveStatus('error');
      }
    }, 1500);

    return () => {
      if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    };
  }, [editingDoc.content, editingDoc.path, editingDoc.filename, editingDoc.isNew, showDocEditor, backendUrl]);

  // AI Document Assistant Prompt Injection
  const handleAiPolishDoc = async (promptType) => {
    setIsAiAssisting(true);
    try {
      let promptText = '';
      if (promptType === 'expand_screenplay') {
        promptText = 'Expand the following scene description and dialogue in Hollywood screenplay standard Fountain format:\n\n' + editingDoc.content;
      } else if (promptType === 'proof_markdown') {
        promptText = 'Proofread and format this document with clean markdown headers and executive summary:\n\n' + editingDoc.content;
      } else if (promptType === 'story_bible') {
        promptText = 'Generate a character and story bible breakdown based on this text:\n\n' + editingDoc.content;
      }

      const res = await fetch(`${backendUrl}/api/screenwriting/ghostwrite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptText,
          current_text: editingDoc.content
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.generated_text) {
          setEditingDoc((prev) => ({
            ...prev,
            content: prev.content + '\n\n' + data.generated_text
          }));
        }
      }
    } catch (err) {
      console.error('AI polish failed:', err);
    } finally {
      setIsAiAssisting(false);
    }
  };

  // Delete Selected Items
  const handleDeleteSelected = async () => {
    if (selectedItems.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedItems.length} item(s)?`)) return;

    try {
      const res = await fetch(`${backendUrl}/api/drive/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_paths: selectedItems })
      });
      if (res.ok) {
        setSelectedItems([]);
        fetchDirectory();
        fetchStorageStats();
      }
    } catch (err) {
      console.error('Failed to delete items:', err);
    }
  };

  // Rename Item
  const handleRename = async () => {
    if (!renameTarget || !renameValue.trim()) return;
    try {
      const res = await fetch(`${backendUrl}/api/drive/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_path: renameTarget.path,
          new_name: renameValue.trim()
        })
      });
      if (res.ok) {
        setShowRenameModal(false);
        setRenameTarget(null);
        fetchDirectory();
        fetchStorageStats();
      }
    } catch (err) {
      console.error('Failed to rename item:', err);
    }
  };

  // Move Items
  const handleMoveItems = async () => {
    if (selectedItems.length === 0) return;
    try {
      const res = await fetch(`${backendUrl}/api/drive/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_paths: selectedItems,
          target_folder: targetMoveFolder
        })
      });
      if (res.ok) {
        setShowMoveModal(false);
        setSelectedItems([]);
        fetchDirectory();
        fetchStorageStats();
      }
    } catch (err) {
      console.error('Failed to move items:', err);
    }
  };

  // Download Single File or ZIP Bundle
  const handleDownload = (item) => {
    window.open(`${backendUrl}/api/drive/download?path=${encodeURIComponent(item.path)}`, '_blank');
  };

  const handleZipDownload = async () => {
    if (selectedItems.length === 0) return;
    try {
      const res = await fetch(`${backendUrl}/api/drive/zip_download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paths: selectedItems,
          archive_name: 'stehouwer_drive_bundle.zip'
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'stehouwer_drive_bundle.zip';
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } catch (err) {
      console.error('Failed to download zip:', err);
    }
  };

  // Cross-Studio Navigation Bridges
  const handleOpenInScreenplayStudio = (fountainPath) => {
    if (onNavigateTab) {
      onNavigateTab('unified_creation');
    }
  };

  const handleOpenInIDE = (filePath) => {
    if (onNavigateTab) {
      onNavigateTab('ide');
    }
  };

  const handleOpenInVideoStudio = (mediaPath) => {
    if (onNavigateTab) {
      onNavigateTab('video_agent');
    }
  };

  return (
    <div 
      className="admin-shared-drive-container"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* ── 1. Top Command Header Deck ── */}
      <div className="drive-header-deck">
        <div className="drive-header-left">
          <div className="drive-logo-title">
            <span className="drive-logo-icon">☁️</span>
            <div>
              <h2 className="drive-title">Admin Shared Cloud Drive</h2>
              <span className="drive-subtitle">Enterprise Storage, Assets, Screenplays & Shared Documents</span>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="drive-search-box">
          <span className="drive-search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search all files & folders across drive..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="drive-search-input"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="drive-search-clear">&times;</button>
          )}
        </div>

        {/* Header Right Action Group */}
        <div className="drive-header-actions">
          {/* "+ New" Dropdown */}
          <div className="drive-new-dropdown-wrapper" ref={newMenuRef}>
            <button 
              className="drive-new-btn"
              onClick={() => setShowNewMenu(!showNewMenu)}
            >
              <span>➕</span> New ▾
            </button>

            {showNewMenu && (
              <div className="drive-new-menu">
                <div className="drive-menu-section-label">CREATE NEW</div>
                <button onClick={() => { setShowNewMenu(false); setShowNewFolderModal(true); }}>
                  <span>📁</span> New Folder
                </button>
                <button onClick={() => handleStartNewDocument('fountain')}>
                  <span>🎬</span> New Screenplay (.fountain)
                </button>
                <button onClick={() => handleStartNewDocument('markdown')}>
                  <span>📝</span> New Markdown Document (.md)
                </button>
                <button onClick={() => handleStartNewDocument('text')}>
                  <span>📋</span> New Plain Text Note (.txt)
                </button>
                <button onClick={() => handleStartNewDocument('json')}>
                  <span>📊</span> New JSON Data File (.json)
                </button>
                <button onClick={() => handleStartNewDocument('python')}>
                  <span>🐍</span> New Python Script (.py)
                </button>

                <div className="drive-menu-divider" />
                <div className="drive-menu-section-label">UPLOAD (ANY FILE TYPE)</div>
                <button onClick={() => { setShowNewMenu(false); fileInputRef.current?.click(); }}>
                  <span>⬆️</span> Upload Files
                </button>
                <button onClick={() => { setShowNewMenu(false); folderInputRef.current?.click(); }}>
                  <span>📂</span> Upload Folder
                </button>
              </div>
            )}
          </div>

          {/* Hidden File Upload Inputs */}
          <input
            type="file"
            multiple
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={(e) => handleFilesUpload(e.target.files)}
          />
          <input
            type="file"
            webkitdirectory="true"
            directory=""
            multiple
            ref={folderInputRef}
            style={{ display: 'none' }}
            onChange={(e) => handleFilesUpload(e.target.files)}
          />

          {/* View Toggle */}
          <div className="drive-view-toggle">
            <button
              className={`drive-toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid View"
            >
              🔲
            </button>
            <button
              className={`drive-toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List Table View"
            >
              📋
            </button>
          </div>

          {/* Sort Dropdown */}
          <div className="drive-sort-group">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="drive-select-input"
            >
              <option value="name">Sort by Name</option>
              <option value="modified">Sort by Date</option>
              <option value="size">Sort by Size</option>
              <option value="type">Sort by Type</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="drive-sort-order-btn"
              title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
            >
              {sortOrder === 'asc' ? '▲' : '▼'}
            </button>
          </div>

          {/* Drive Guide & Tips Toggle Button */}
          <button
            onClick={() => setShowDriveTips(!showDriveTips)}
            className="drive-tips-btn"
            title="Toggle Shared Cloud Drive Tips & Keyboard Shortcuts"
          >
            <span>💡</span> {showDriveTips ? 'Hide Tips' : 'Drive Guide & Tips'}
          </button>
        </div>
      </div>

      {/* ── In-Tab Tips Banner ── */}
      {showDriveTips && (
        <div className="drive-tips-banner">
          <div className="drive-tips-header">
            <span>💡 ADMIN SHARED CLOUD DRIVE: OPERATIONAL TIPS & WORKFLOWS</span>
          </div>
          <div className="drive-tips-grid">
            <div className="drive-tip-card">
              <strong>📁 Universal File Ingestion:</strong>
              <p>Drag and drop any file types (scripts, video MP4s, 3D textures, audio WAVs, python scripts) directly into any folder. Entire folders can be uploaded via <em>"+ New" ➔ "Upload Folder"</em>.</p>
            </div>
            <div className="drive-tip-card">
              <strong>📝 In-Drive Document Studio:</strong>
              <p>Click <em>"+ New"</em> to create Fountain Screenplays (.fountain), Markdown (.md), JSON (.json), or Python (.py). Edit and save live with AI Co-Pilot prompt expansion.</p>
            </div>
            <div className="drive-tip-card">
              <strong>📦 Multi-Select & Batch Bundles:</strong>
              <p>Hold <kbd>Ctrl</kbd> or <kbd>Shift</kbd> while clicking items to select multiple files. Click <em>"Download Selected as ZIP"</em> to package them into a streaming ZIP archive on the fly.</p>
            </div>
            <div className="drive-tip-card">
              <strong>🚀 1-Click Studio Bridges:</strong>
              <p>Preview any media in the lightbox and click <em>"Open in Screenwriting Studio"</em>, <em>"Open in BS-CHAT IDE"</em>, or <em>"Open in Video Studio"</em> to bridge assets instantly.</p>
            </div>
          </div>
        </div>
      )}

      {/* ── 2. Storage Quota & Telemetry Ribbon ── */}
      {storageStats && (
        <div className="drive-telemetry-ribbon">
          <div className="drive-storage-pill">
            <span className="drive-telemetry-label">💾 Storage:</span>
            <span className="drive-telemetry-val">
              {storageStats.drive_total_formatted} used in Drive ({storageStats.drive_total_files} files, {storageStats.drive_total_folders} folders)
            </span>
          </div>

          <div className="drive-storage-pill">
            <span className="drive-telemetry-label">🖥️ Host Disk:</span>
            <span className="drive-telemetry-val">
              {storageStats.disk_free_formatted} free of {storageStats.disk_total_formatted} ({storageStats.disk_used_pct}% used)
            </span>
          </div>

          {/* Category Breakdown Bar */}
          <div className="drive-category-pills">
            {storageStats.categories_breakdown.map((cat) => (
              <span 
                key={cat.category}
                className={`drive-cat-badge ${activeCategory === cat.category ? 'active' : ''}`}
                onClick={() => setActiveCategory(activeCategory === cat.category ? 'all' : cat.category)}
              >
                {cat.icon} {cat.category}: {cat.count} ({cat.size_formatted})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── 3. Workspace Layout (Left Sidebar + Main Canvas) ── */}
      <div className="drive-main-workspace">
        {/* Left Navigation Sidebar */}
        <div className="drive-sidebar">
          <div className="drive-sidebar-section">
            <div className="drive-sidebar-title">QUICK FILTERS</div>
            <button 
              className={`drive-nav-item ${activeCategory === 'all' ? 'active' : ''}`}
              onClick={() => setActiveCategory('all')}
            >
              <span>📂</span> All Files
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'screenplay' ? 'active' : ''}`}
              onClick={() => setActiveCategory('screenplay')}
            >
              <span>🎬</span> Screenplays & Scripts
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'image' ? 'active' : ''}`}
              onClick={() => setActiveCategory('image')}
            >
              <span>🖼️</span> Images & Previs
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'video' ? 'active' : ''}`}
              onClick={() => setActiveCategory('video')}
            >
              <span>🎥</span> Videos & Renders
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'audio' ? 'active' : ''}`}
              onClick={() => setActiveCategory('audio')}
            >
              <span>🎙️</span> Audio & Voiceovers
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'document' ? 'active' : ''}`}
              onClick={() => setActiveCategory('document')}
            >
              <span>📄</span> Documents & Legal
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'code' ? 'active' : ''}`}
              onClick={() => setActiveCategory('code')}
            >
              <span>💻</span> Code & Configs
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'archive' ? 'active' : ''}`}
              onClick={() => setActiveCategory('archive')}
            >
              <span>📦</span> Archives & Zips
            </button>
            <button 
              className={`drive-nav-item ${activeCategory === 'unreal' ? 'active' : ''}`}
              onClick={() => setActiveCategory('unreal')}
            >
              <span>🎮</span> Unreal Engine Assets
            </button>
          </div>

          <div className="drive-sidebar-section">
            <div className="drive-sidebar-title">ENTERPRISE FOLDERS</div>
            {DEFAULT_FOLDERS.map((f) => (
              <button
                key={f}
                className={`drive-nav-item ${currentPath === `/${f}` ? 'active' : ''}`}
                onClick={() => { setCurrentPath(`/${f}`); setSearchQuery(''); }}
              >
                <span>📁</span> {f.replace(/^\d+_/g, '').replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Main Drive Canvas */}
        <div className="drive-canvas">
          {/* Breadcrumbs & Selection Actions Bar */}
          <div className="drive-breadcrumbs-bar">
            <div className="drive-breadcrumbs">
              {breadcrumbs.map((b, idx) => (
                <React.Fragment key={b.path}>
                  {idx > 0 && <span className="drive-crumb-separator">/</span>}
                  <button
                    className={`drive-crumb-btn ${idx === breadcrumbs.length - 1 ? 'active' : ''}`}
                    onClick={() => { setCurrentPath(b.path); setSearchQuery(''); }}
                  >
                    {idx === 0 ? '🏠 ' : '📁 '} {b.name}
                  </button>
                </React.Fragment>
              ))}
            </div>

            {/* Selection Actions */}
            {selectedItems.length > 0 && (
              <div className="drive-selection-actions">
                <span className="drive-selected-count">{selectedItems.length} selected</span>
                <button onClick={handleZipDownload} className="drive-action-btn" title="Download selected as ZIP archive">
                  <span>📦</span> ZIP Download
                </button>
                <button onClick={() => setShowMoveModal(true)} className="drive-action-btn" title="Move selected items">
                  <span>🚚</span> Move
                </button>
                <button onClick={handleDeleteSelected} className="drive-action-btn drive-action-delete" title="Delete selected items">
                  <span>🗑️</span> Delete
                </button>
                <button onClick={() => setSelectedItems([])} className="drive-action-btn">
                  Cancel
                </button>
              </div>
            )}
          </div>

          {/* Drag Overlay Notification */}
          {isDragging && (
            <div className="drive-drag-overlay">
              <div className="drive-drag-box">
                <span style={{ fontSize: '3rem' }}>📥</span>
                <h3>Drop files here to upload instantly to:</h3>
                <code>{currentPath}</code>
              </div>
            </div>
          )}

          {/* Upload Progress Bar */}
          {uploadProgress && (
            <div className="drive-upload-notification">
              <span>⏳ {uploadProgress}</span>
            </div>
          )}

          {/* Files Presentation: Grid or List */}
          {isLoading ? (
            <div className="drive-loading-state">
              <span>⚡</span> Loading shared cloud drive...
            </div>
          ) : items.length === 0 ? (
            <div className="drive-empty-state">
              <span style={{ fontSize: '3.5rem' }}>📂</span>
              <h3>This folder is empty</h3>
              <p>Drag and drop files here, or use the <strong>+ New</strong> button to create documents or folders.</p>
              <div style={{ display: 'flex', gap: '10px', marginTop: '14px' }}>
                <button className="drive-new-btn" onClick={() => handleStartNewDocument('fountain')}>
                  🎬 Create Screenplay
                </button>
                <button className="drive-new-btn" onClick={() => handleStartNewDocument('markdown')}>
                  📝 Create Document
                </button>
                <button className="drive-new-btn" onClick={() => fileInputRef.current?.click()}>
                  ⬆️ Upload File
                </button>
              </div>
            </div>
          ) : viewMode === 'grid' ? (
            /* ── GRID CARDS VIEW ── */
            <div className="drive-grid-view">
              {items.map((item) => {
                const isSelected = selectedItems.includes(item.path);
                return (
                  <div
                    key={item.id}
                    className={`drive-card ${isSelected ? 'selected' : ''} ${item.is_dir ? 'is-folder' : ''}`}
                    onClick={(e) => handleSelect(item, e)}
                    onDoubleClick={(e) => handleItemClick(item, e)}
                  >
                    <div className="drive-card-header">
                      <span className="drive-card-icon">{item.icon}</span>
                      <div className="drive-card-actions">
                        {!item.is_dir && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDownload(item); }}
                            className="drive-card-action-btn"
                            title="Download file"
                          >
                            ⬇️
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setRenameTarget(item);
                            setRenameValue(item.name);
                            setShowRenameModal(true);
                          }}
                          className="drive-card-action-btn"
                          title="Rename"
                        >
                          ✏️
                        </button>
                      </div>
                    </div>

                    <div className="drive-card-body">
                      <div className="drive-card-name" title={item.name}>
                        {item.name}
                      </div>
                      <div className="drive-card-meta">
                        <span>{item.size_formatted}</span>
                        <span>{item.modified_formatted}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* ── LIST TABLE VIEW ── */
            <div className="drive-list-view">
              <table className="drive-table">
                <thead>
                  <tr>
                    <th style={{ width: '36px' }}>
                      <input 
                        type="checkbox" 
                        checked={selectedItems.length === items.length && items.length > 0} 
                        onChange={toggleSelectAll} 
                      />
                    </th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Size</th>
                    <th>Last Modified</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const isSelected = selectedItems.includes(item.path);
                    return (
                      <tr 
                        key={item.id}
                        className={`drive-table-row ${isSelected ? 'selected' : ''}`}
                        onClick={(e) => handleSelect(item, e)}
                        onDoubleClick={(e) => handleItemClick(item, e)}
                      >
                        <td onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={(e) => handleSelect(item, e)}
                          />
                        </td>
                        <td className="drive-table-name-cell">
                          <span className="drive-table-icon">{item.icon}</span>
                          <span className="drive-table-name">{item.name}</span>
                        </td>
                        <td>
                          <span className="drive-table-category-pill">{item.category}</span>
                        </td>
                        <td className="drive-table-size">{item.size_formatted}</td>
                        <td className="drive-table-modified">{item.modified_formatted}</td>
                        <td className="drive-table-actions" onClick={(e) => e.stopPropagation()}>
                          {!item.is_dir && (
                            <>
                              <button onClick={() => handleOpenPreviewOrEdit(item)} className="drive-btn-sm" title="View / Edit">
                                👁️ Open
                              </button>
                              <button onClick={() => handleDownload(item)} className="drive-btn-sm" title="Download">
                                ⬇️
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => {
                              setRenameTarget(item);
                              setRenameValue(item.name);
                              setShowRenameModal(true);
                            }}
                            className="drive-btn-sm"
                            title="Rename"
                          >
                            ✏️
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── 4. IN-DRIVE INTERACTIVE DOCUMENT EDITOR MODAL ── */}
      {showDocEditor && (
        <div className="drive-modal-overlay">
          <div className="drive-doc-editor-modal" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <WordDocsPaperCanvas
              value={editingDoc.content}
              onChange={(newContent) => setEditingDoc({ ...editingDoc, content: newContent })}
              filename={editingDoc.filename}
              onFilenameChange={(newFilename) => setEditingDoc({ ...editingDoc, filename: newFilename })}
              onSave={handleSaveDocument}
              autoSaveStatus={autoSaveStatus}
              lastSavedTime={lastSavedTime}
              onClose={() => setShowDocEditor(false)}
              extraHeaderActions={
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {editingDoc.category === 'screenplay' && (
                    <button
                      onClick={() => handleOpenInScreenplayStudio(editingDoc.path)}
                      className="drive-btn-bridge"
                      title="Send to Universal Screenwriting Studio"
                      style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                    >
                      🎬 Screenplay Studio
                    </button>
                  )}
                  {editingDoc.category === 'code' && (
                    <button
                      onClick={() => handleOpenInIDE(editingDoc.path)}
                      className="drive-btn-bridge"
                      title="Open in BS-CHAT IDE"
                      style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                    >
                      💻 IDE
                    </button>
                  )}
                  <button
                    onClick={() => handleAiPolishDoc('expand_screenplay')}
                    disabled={isAiAssisting}
                    className="drive-ai-tool-btn"
                    style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                    title="AI Polish"
                  >
                    ✨ AI Co-Pilot
                  </button>
                </div>
              }
            />
          </div>
        </div>
      )}

      {/* ── 5. IN-DRIVE MEDIA / PDF / AUDIO LIGHTBOX MODAL ── */}
      {previewMedia && (
        <div className="drive-modal-overlay" onClick={() => setPreviewMedia(null)}>
          <div className="drive-preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="drive-preview-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>{previewMedia.icon}</span>
                <span className="drive-preview-filename">{previewMedia.name}</span>
                <span style={{ color: '#9ca3af', fontSize: '0.8rem' }}>({previewMedia.size_formatted})</span>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {previewMedia.category === 'video' && (
                  <button onClick={() => handleOpenInVideoStudio(previewMedia.path)} className="drive-btn-bridge">
                    🎥 Open in Video Studio
                  </button>
                )}
                <button onClick={() => handleDownload(previewMedia)} className="drive-btn-secondary">
                  ⬇️ Download
                </button>
                <button onClick={() => setPreviewMedia(null)} className="drive-btn-close">
                  ✕
                </button>
              </div>
            </div>

            <div className="drive-preview-content">
              {previewMedia.category === 'image' ? (
                <img src={previewMedia.url?.startsWith('http') || previewMedia.url?.startsWith('data:') || previewMedia.url?.startsWith('blob:') ? previewMedia.url : `${backendUrl}${previewMedia.url?.startsWith('/') ? '' : '/'}${previewMedia.url}`} alt={previewMedia.name} className="drive-preview-img" />
              ) : previewMedia.category === 'video' ? (
                <video src={previewMedia.url?.startsWith('http') || previewMedia.url?.startsWith('data:') || previewMedia.url?.startsWith('blob:') ? previewMedia.url : `${backendUrl}${previewMedia.url?.startsWith('/') ? '' : '/'}${previewMedia.url}`} controls autoPlay className="drive-preview-video" />
              ) : previewMedia.category === 'audio' ? (
                <div className="drive-preview-audio-wrapper">
                  <span style={{ fontSize: '4rem', marginBottom: '16px' }}>🎙️</span>
                  <h3>{previewMedia.name}</h3>
                  <audio src={previewMedia.url?.startsWith('http') || previewMedia.url?.startsWith('data:') || previewMedia.url?.startsWith('blob:') ? previewMedia.url : `${backendUrl}${previewMedia.url?.startsWith('/') ? '' : '/'}${previewMedia.url}`} controls autoPlay style={{ width: '100%', maxWidth: '500px', marginTop: '16px' }} />
                </div>
              ) : previewMedia.extension === '.pdf' ? (
                <iframe src={previewMedia.url?.startsWith('http') || previewMedia.url?.startsWith('data:') || previewMedia.url?.startsWith('blob:') ? previewMedia.url : `${backendUrl}${previewMedia.url?.startsWith('/') ? '' : '/'}${previewMedia.url}`} title={previewMedia.name} className="drive-preview-iframe" />
              ) : (
                <div className="drive-preview-fallback">
                  <span>📎</span>
                  <h3>Preview not available for this binary format</h3>
                  <p>You can download this asset to view or execute it on your host system.</p>
                  <button onClick={() => handleDownload(previewMedia)} className="drive-btn-primary">
                    ⬇️ Download {previewMedia.name}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── 6. CREATE FOLDER MODAL ── */}
      {showNewFolderModal && (
        <div className="drive-modal-overlay">
          <div className="drive-prompt-modal">
            <h3>📁 Create New Folder</h3>
            <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Location: <code>{currentPath}</code></p>
            <input
              type="text"
              placeholder="Folder name (e.g. Q3_Screenplays_Drafts)"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
              className="drive-modal-input"
              autoFocus
            />
            <div className="drive-modal-actions">
              <button onClick={() => setShowNewFolderModal(false)} className="drive-btn-secondary">
                Cancel
              </button>
              <button onClick={handleCreateFolder} className="drive-btn-primary">
                Create Folder
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 7. RENAME MODAL ── */}
      {showRenameModal && renameTarget && (
        <div className="drive-modal-overlay">
          <div className="drive-prompt-modal">
            <h3>✏️ Rename {renameTarget.is_dir ? 'Folder' : 'File'}</h3>
            <input
              type="text"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRename()}
              className="drive-modal-input"
              autoFocus
            />
            <div className="drive-modal-actions">
              <button onClick={() => setShowRenameModal(false)} className="drive-btn-secondary">
                Cancel
              </button>
              <button onClick={handleRename} className="drive-btn-primary">
                Rename
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 8. MOVE ITEMS MODAL ── */}
      {showMoveModal && (
        <div className="drive-modal-overlay">
          <div className="drive-prompt-modal">
            <h3>🚚 Move {selectedItems.length} Item(s)</h3>
            <p style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Select destination folder:</p>
            <select
              value={targetMoveFolder}
              onChange={(e) => setTargetMoveFolder(e.target.value)}
              className="drive-modal-input"
            >
              <option value="/">🏠 Shared Drive Root (/)</option>
              {DEFAULT_FOLDERS.map((f) => (
                <option key={f} value={`/${f}`}>📁 /{f}</option>
              ))}
            </select>
            <div className="drive-modal-actions">
              <button onClick={() => setShowMoveModal(false)} className="drive-btn-secondary">
                Cancel
              </button>
              <button onClick={handleMoveItems} className="drive-btn-primary">
                Move Items
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
