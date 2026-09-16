import React, { useState, useRef, useEffect } from 'react';
import './WordDocsPaperCanvas.css';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export default function WordDocsPaperCanvas({
  value = '',
  onChange,
  filename = 'Untitled Document',
  onFilenameChange,
  onSave,
  autoSaveStatus = 'saved',
  lastSavedTime = '',
  placeholder = 'Type @ to insert, or begin typing your document...',
  readOnly = false,
  extraHeaderActions = null,
  onClose = null
}) {
  const [fontFamily, setFontFamily] = useState('Georgia');
  const [fontSize, setFontSize] = useState('15px');
  const [lineSpacing, setLineSpacing] = useState('1.6');
  const [textAlign, setTextAlign] = useState('left');
  const [canvasTheme, setCanvasTheme] = useState('white_paper'); // 'white_paper' | 'dark_studio' | 'focus_sepia'
  const [isBold, setIsBold] = useState(false);
  const [isItalic, setIsItalic] = useState(false);
  const [isUnderline, setIsUnderline] = useState(false);
  const [isExportingWord, setIsExportingWord] = useState(false);
  const [isExportingFdx, setIsExportingFdx] = useState(false);

  // Find & Replace State
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findQuery, setFindQuery] = useState('');
  const [replaceQuery, setReplaceQuery] = useState('');
  const [matchCount, setMatchCount] = useState(0);

  // Word Target Goal
  const [wordTarget, setWordTarget] = useState(1000);

  const textareaRef = useRef(null);

  // Compute live stats
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  const chars = value.length;
  const estimatedPages = Math.max(1, Math.ceil(words / 350));
  const readingTime = Math.max(1, Math.ceil(words / 200));
  const targetProgress = Math.min(100, Math.round((words / wordTarget) * 100));

  // Count search query matches
  useEffect(() => {
    if (!findQuery.trim() || !value) {
      setMatchCount(0);
      return;
    }
    try {
      const regex = new RegExp(findQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      const matches = value.match(regex);
      setMatchCount(matches ? matches.length : 0);
    } catch {
      setMatchCount(0);
    }
  }, [findQuery, value]);

  // Export directly to genuine formatted Microsoft Word (.docx)
  const handleExportWordDocx = async () => {
    setIsExportingWord(true);
    try {
      const res = await fetch(`${API_BASE}/api/documents/export_docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: filename || 'Document',
          content: value,
          title: filename ? filename.replace(/\.[^/.]+$/, "") : 'Document'
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cleanName = filename ? filename.replace(/\.[^/.]+$/, "") : 'Document';
        a.download = `${cleanName}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('Failed to generate Word document.');
      }
    } catch (e) {
      alert(`Export Word error: ${e.message}`);
    } finally {
      setIsExportingWord(false);
    }
  };

  // Export to Final Draft (.fdx)
  const handleExportFdx = async () => {
    setIsExportingFdx(true);
    try {
      const res = await fetch(`${API_BASE}/api/documents/export_fdx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: filename || 'Document',
          content: value,
          title: filename ? filename.replace(/\.[^/.]+$/, "") : 'Document'
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cleanName = filename ? filename.replace(/\.[^/.]+$/, "").replace(".txt", "").replace(".md", "").replace(".fountain", "") : 'Document';
        a.download = `${cleanName}.fdx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('Failed to generate Final Draft document.');
      }
    } catch (e) {
      alert(`Export FDX error: ${e.message}`);
    } finally {
      setIsExportingFdx(false);
    }
  };

  // Find & Replace Handlers
  const handleReplaceOne = () => {
    if (!findQuery || !value) return;
    const index = value.toLowerCase().indexOf(findQuery.toLowerCase());
    if (index !== -1) {
      const newContent = value.substring(0, index) + replaceQuery + value.substring(index + findQuery.length);
      if (onChange) onChange(newContent);
    }
  };

  const handleReplaceAll = () => {
    if (!findQuery || !value) return;
    try {
      const regex = new RegExp(findQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      const newContent = value.replace(regex, replaceQuery);
      if (onChange) onChange(newContent);
    } catch (e) {
      console.warn('Replace all error:', e);
    }
  };

  // Print Document
  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${filename}</title>
        <style>
          body { font-family: ${fontFamily}; font-size: ${fontSize}; line-height: ${lineSpacing}; padding: 1in; max-width: 8.5in; margin: 0 auto; color: #111; }
          h1, h2, h3 { color: #000; margin-top: 1.5em; }
          p { margin-bottom: 1em; }
          blockquote { border-left: 3px solid #ccc; padding-left: 1em; color: #555; font-style: italic; }
        </style>
      </head>
      <body>
        <h1>${filename.replace(/\.[^/.]+$/, "")}</h1>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;" />
        <div>${value.replace(/\n/g, '<br/>')}</div>
      </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 250);
  };

  // Toolbar Formatting Helpers (Markdown / Text Insertion)
  const insertFormatting = (prefix, suffix = '') => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = value.substring(start, end) || 'text';
    const before = value.substring(0, start);
    const after = value.substring(end);

    const newContent = `${before}${prefix}${selectedText}${suffix}${after}`;
    if (onChange) onChange(newContent);

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + prefix.length, start + prefix.length + selectedText.length);
    }, 10);
  };

  const insertTemplateHeading = (level) => {
    const hashes = '#'.repeat(level);
    insertFormatting(`\n${hashes} `, '\n');
  };

  const insertBullet = () => {
    insertFormatting('\n- ', '');
  };

  const insertNumbered = () => {
    insertFormatting('\n1. ', '');
  };

  const insertQuote = () => {
    insertFormatting('\n> ', '\n');
  };

  const insertHighlight = (color = '#fef08a') => {
    insertFormatting(`==`, `==`);
  };

  const insertHorizontalRule = () => {
    insertFormatting('\n\n---\n\n', '');
  };

  const insertPageBreak = () => {
    insertFormatting('\n\n<!-- PAGE BREAK -->\n\n', '');
  };

  // Keyboard Shortcuts (Ctrl+B, Ctrl+I, Ctrl+U, Ctrl+F, Ctrl+S)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'b' || e.key === 'B') {
          e.preventDefault();
          insertFormatting('**', '**');
          setIsBold((prev) => !prev);
        } else if (e.key === 'i' || e.key === 'I') {
          e.preventDefault();
          insertFormatting('*', '*');
          setIsItalic((prev) => !prev);
        } else if (e.key === 'u' || e.key === 'U') {
          e.preventDefault();
          insertFormatting('<u>', '</u>');
          setIsUnderline((prev) => !prev);
        } else if (e.key === 'f' || e.key === 'F') {
          e.preventDefault();
          setShowFindReplace((prev) => !prev);
        } else if (e.key === 's' || e.key === 'S') {
          if (onSave) {
            e.preventDefault();
            onSave();
          }
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [value, onSave]);

  return (
    <div className={`word-docs-container theme-${canvasTheme}`}>
      {/* ── 1. Top Ribbon & Formatting Toolbar (Word / Docs Style) ── */}
      <div className="word-docs-ribbon">
        {/* Document Title & Status Pill */}
        <div className="docs-ribbon-top-row">
          <div className="docs-title-group">
            <span className="docs-app-icon">📄</span>
            {onFilenameChange ? (
              <input
                type="text"
                value={filename}
                onChange={(e) => onFilenameChange(e.target.value)}
                className="docs-filename-input"
                placeholder="Untitled Document"
              />
            ) : (
              <span className="docs-filename-label">{filename}</span>
            )}
            <span className="docs-badge">Stehouwer Docs</span>
          </div>

          <div className="docs-top-actions">
            {/* Auto-Save Status Badge */}
            <div className="docs-autosave-indicator">
              <span className="dot">
                {autoSaveStatus === 'saving' ? '🟡' : autoSaveStatus === 'error' ? '🔴' : '🟢'}
              </span>
              <span>
                {autoSaveStatus === 'saving' ? 'Saving to Cloud...' : autoSaveStatus === 'error' ? 'Save Error' : `Saved ${lastSavedTime || 'to Drive'}`}
              </span>
            </div>

            {/* Canvas View Switcher (White Paper vs Dark Studio vs Sepia) */}
            <div className="docs-view-toggle">
              <button
                className={`docs-view-btn ${canvasTheme === 'white_paper' ? 'active' : ''}`}
                onClick={() => setCanvasTheme('white_paper')}
                title="White Page View (Word / Google Docs Paper Canvas)"
              >
                📄 White Page
              </button>
              <button
                className={`docs-view-btn ${canvasTheme === 'focus_sepia' ? 'active' : ''}`}
                onClick={() => setCanvasTheme('focus_sepia')}
                title="Warm Sepia Paper View (Warm Comfort Readability)"
              >
                📜 Warm Sepia
              </button>
              <button
                className={`docs-view-btn ${canvasTheme === 'dark_studio' ? 'active' : ''}`}
                onClick={() => setCanvasTheme('dark_studio')}
                title="Dark Studio Canvas"
              >
                🌙 Dark Canvas
              </button>
            </div>

            {extraHeaderActions}

            {/* Print Button */}
            <button onClick={handlePrint} className="docs-aux-btn" title="Print Document (Ctrl+P)">
              🖨️ Print
            </button>

            {/* Export Microsoft Word (.docx) */}
            <button
              onClick={handleExportWordDocx}
              disabled={isExportingWord || !value.trim()}
              className="docs-save-btn"
              style={{
                background: '#0d9488',
                color: '#ffffff',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
              title="Download formatted Microsoft Word (.docx) document"
            >
              {isExportingWord ? '⏳ Generating Word...' : '📥 Word (.docx)'}
            </button>

            {/* Export Final Draft (.fdx) */}
            <button
              onClick={handleExportFdx}
              disabled={isExportingFdx || !value.trim()}
              className="docs-save-btn"
              style={{
                background: '#3b82f6',
                color: '#ffffff',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
              title="Download Final Draft (.fdx) script"
            >
              {isExportingFdx ? '⏳ Generating FDX...' : '📥 Final Draft (.fdx)'}
            </button>

            {onSave && (
              <button onClick={onSave} className="docs-save-btn">
                💾 Save
              </button>
            )}

            {onClose && (
              <button
                onClick={onClose}
                className="docs-save-btn"
                style={{ background: '#ef4444', color: '#fff', border: 'none' }}
                title="Close Document & Return"
              >
                ✕ Close
              </button>
            )}
          </div>
        </div>

        {/* Formatting Command Ribbon */}
        <div className="docs-formatting-bar">
          {/* Font Selector */}
          <div className="toolbar-group">
            <select
              value={fontFamily}
              onChange={(e) => setFontFamily(e.target.value)}
              className="toolbar-select font-family"
              title="Font Family"
            >
              <option value="Georgia">Georgia (Classic Book)</option>
              <option value="'Times New Roman', serif">Times New Roman (Standard)</option>
              <option value="Arial, sans-serif">Arial (Modern Clean)</option>
              <option value="'Calibri', sans-serif">Calibri (Microsoft Word)</option>
              <option value="'Inter', sans-serif">Inter (Executive UI)</option>
              <option value="'Courier Prime', monospace">Courier Prime (Screenplay)</option>
              <option value="'Garamond', serif">Garamond (Literary Novel)</option>
            </select>

            <select
              value={fontSize}
              onChange={(e) => setFontSize(e.target.value)}
              className="toolbar-select font-size"
              title="Font Size"
            >
              <option value="12px">12 pt</option>
              <option value="13px">13 pt</option>
              <option value="14px">14 pt</option>
              <option value="15px">15 pt (Standard)</option>
              <option value="16px">16 pt</option>
              <option value="18px">18 pt (Large)</option>
              <option value="22px">22 pt (Heading)</option>
            </select>
          </div>

          <div className="toolbar-divider" />

          {/* Text Styling */}
          <div className="toolbar-group">
            <button
              className={`toolbar-btn ${isBold ? 'active' : ''}`}
              onClick={() => {
                insertFormatting('**', '**');
                setIsBold(!isBold);
              }}
              title="Bold (Ctrl+B)"
            >
              <strong>B</strong>
            </button>
            <button
              className={`toolbar-btn ${isItalic ? 'active' : ''}`}
              onClick={() => {
                insertFormatting('*', '*');
                setIsItalic(!isItalic);
              }}
              title="Italic (Ctrl+I)"
            >
              <em>I</em>
            </button>
            <button
              className={`toolbar-btn ${isUnderline ? 'active' : ''}`}
              onClick={() => {
                insertFormatting('<u>', '</u>');
                setIsUnderline(!isUnderline);
              }}
              title="Underline (Ctrl+U)"
            >
              <u>U</u>
            </button>
            <button
              className="toolbar-btn"
              onClick={() => insertFormatting('~~', '~~')}
              title="Strikethrough"
            >
              <s>S</s>
            </button>
            <button
              className="toolbar-btn"
              onClick={() => insertHighlight()}
              title="Highlight Text (==text==)"
            >
              🖍️
            </button>
          </div>

          <div className="toolbar-divider" />

          {/* Heading Presets */}
          <div className="toolbar-group">
            <button className="toolbar-btn text-btn" onClick={() => insertTemplateHeading(1)} title="Heading 1">
              H1
            </button>
            <button className="toolbar-btn text-btn" onClick={() => insertTemplateHeading(2)} title="Heading 2">
              H2
            </button>
            <button className="toolbar-btn text-btn" onClick={() => insertTemplateHeading(3)} title="Heading 3">
              H3
            </button>
          </div>

          <div className="toolbar-divider" />

          {/* Alignment & Spacing */}
          <div className="toolbar-group">
            <button
              className={`toolbar-btn ${textAlign === 'left' ? 'active' : ''}`}
              onClick={() => setTextAlign('left')}
              title="Align Left"
            >
              ⇤
            </button>
            <button
              className={`toolbar-btn ${textAlign === 'center' ? 'active' : ''}`}
              onClick={() => setTextAlign('center')}
              title="Align Center"
            >
              ⇥⇤
            </button>
            <button
              className={`toolbar-btn ${textAlign === 'right' ? 'active' : ''}`}
              onClick={() => setTextAlign('right')}
              title="Align Right"
            >
              ⇥
            </button>
            <button
              className={`toolbar-btn ${textAlign === 'justify' ? 'active' : ''}`}
              onClick={() => setTextAlign('justify')}
              title="Justify"
            >
              ☰
            </button>

            <select
              value={lineSpacing}
              onChange={(e) => setLineSpacing(e.target.value)}
              className="toolbar-select line-spacing"
              title="Line Spacing"
            >
              <option value="1.2">Single (1.0)</option>
              <option value="1.5">1.5 Lines</option>
              <option value="1.6">1.6 (Google Docs)</option>
              <option value="2.0">Double (2.0)</option>
            </select>
          </div>

          <div className="toolbar-divider" />

          {/* Lists & Inserts */}
          <div className="toolbar-group">
            <button className="toolbar-btn" onClick={insertBullet} title="Bulleted List">
              • List
            </button>
            <button className="toolbar-btn" onClick={insertNumbered} title="Numbered List">
              1. List
            </button>
            <button className="toolbar-btn" onClick={insertQuote} title="Blockquote">
              ❝ Quote
            </button>
            <button className="toolbar-btn" onClick={insertHorizontalRule} title="Divider Line">
              ― Line
            </button>
            <button className="toolbar-btn" onClick={insertPageBreak} title="Page Break">
              📑 Page Break
            </button>
          </div>

          <div className="toolbar-divider" />

          {/* Find & Replace Toggle */}
          <div className="toolbar-group">
            <button
              className={`toolbar-btn ${showFindReplace ? 'active' : ''}`}
              onClick={() => setShowFindReplace(!showFindReplace)}
              title="Find & Replace (Ctrl+F)"
            >
              🔍 Find
            </button>
          </div>
        </div>

        {/* Collapsible Find & Replace Strip */}
        {showFindReplace && (
          <div className="docs-find-replace-strip">
            <div className="find-input-group">
              <span className="find-label">Find:</span>
              <input
                type="text"
                value={findQuery}
                onChange={(e) => setFindQuery(e.target.value)}
                placeholder="Search word or phrase..."
                className="find-input"
                autoFocus
              />
              <span className="match-badge">{matchCount} match{matchCount === 1 ? '' : 'es'}</span>
            </div>

            <div className="find-input-group">
              <span className="find-label">Replace:</span>
              <input
                type="text"
                value={replaceQuery}
                onChange={(e) => setReplaceQuery(e.target.value)}
                placeholder="Replace with..."
                className="find-input"
              />
              <button onClick={handleReplaceOne} disabled={!matchCount} className="find-btn">
                Replace
              </button>
              <button onClick={handleReplaceAll} disabled={!matchCount} className="find-btn highlight">
                Replace All
              </button>
            </div>

            <button onClick={() => setShowFindReplace(false)} className="find-close-btn" title="Close Search">
              ✕
            </button>
          </div>
        )}
      </div>

      {/* ── 2. The Desk / Surrounding Canvas ── */}
      <div className="word-docs-viewport">
        {/* The White 8.5" × 11" Paper Sheet */}
        <div className="word-docs-paper-sheet">
          {/* Subtle Paper Top Margin Line (Google Docs style) */}
          <div className="paper-margin-ruler" />

          {/* Editable Document Prose Body */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange && onChange(e.target.value)}
            placeholder={placeholder}
            readOnly={readOnly}
            className="paper-content-textarea"
            style={{
              fontFamily: fontFamily,
              fontSize: fontSize,
              lineHeight: lineSpacing,
              textAlign: textAlign
            }}
          />
        </div>
      </div>

      {/* ── 3. Bottom Status Bar (Word & Docs Live Metric Counter) ── */}
      <div className="word-docs-statusbar">
        <div className="statusbar-left">
          <span>Page 1 of {estimatedPages}</span>
          <span className="statusbar-separator">|</span>
          <span>{words.toLocaleString()} Words</span>
          <span className="statusbar-separator">|</span>
          <span>{chars.toLocaleString()} Characters</span>
          <span className="statusbar-separator">|</span>
          <span>~{readingTime}m Read Time</span>
          <span className="statusbar-separator">|</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            🎯 Goal:
            <select
              value={wordTarget}
              onChange={(e) => setWordTarget(parseInt(e.target.value))}
              style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: 'inherit', cursor: 'pointer', fontWeight: 'bold' }}
            >
              <option value="500">500w</option>
              <option value="1000">1,000w</option>
              <option value="2500">2,500w</option>
              <option value="5000">5,000w</option>
              <option value="10000">10,000w</option>
            </select>
            <span style={{ color: targetProgress >= 100 ? '#10b981' : '#3b82f6', fontWeight: 'bold' }}>
              ({targetProgress}%)
            </span>
          </span>
        </div>

        <div className="statusbar-right">
          <span>100% Letter (8.5" × 11")</span>
          <span className="statusbar-separator">|</span>
          <span>English (US)</span>
        </div>
      </div>
    </div>
  );
}
