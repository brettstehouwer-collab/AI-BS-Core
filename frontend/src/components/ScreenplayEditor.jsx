import { paginateScreenplayBlocks } from '/utils/screenplayPagination.js';
import { useRef, useState, useEffect, useCallback } from "react";

const TYPE_CYCLE = ["Scene Heading", "Action", "Character", "Parenthetical", "Dialogue", "Transition"];

/** @type {Record<string, string>} */
const TYPE_SHORTCUTS = {
  '1': 'Scene Heading',
  '2': 'Action',
  '3': 'Character',
  '4': 'Parenthetical',
  '5': 'Dialogue',
  '6': 'Transition',
};

/** @type {Record<string, {"label": string, "color": string, "bg": string, "border": string}>} */
const TYPE_BADGES = {
  'Scene Heading': { label: 'SCENE', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)', border: '#0284c7' },
  'Action': { label: 'ACTION', color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)', border: '#475569' },
  'Character': { label: 'CHAR', color: '#facc15', bg: 'rgba(250, 204, 21, 0.15)', border: '#ca8a04' },
  'Parenthetical': { label: 'PAREN', color: '#c084fc', bg: 'rgba(192, 132, 252, 0.15)', border: '#9333ea' },
  'Dialogue': { label: 'DIAL', color: '#4ade80', bg: 'rgba(74, 222, 128, 0.15)', border: '#16a34a' },
  'Transition': { label: 'TRANS', color: '#f472b6', bg: 'rgba(244, 114, 182, 0.15)', border: '#db2777' },
};


/** @param {{ast?: import('/types/domain').ScreenplayBlock[], onChange: (blocks: import('/types/domain').ScreenplayBlock[]) => void, zoomLevel?: number, onGhostwriter?: (index: number) => void, characters?: Array<{name: string}>, currentPage?: number, onPageChange?: (page: number) => void, onProofPage?: (page: number) => void, onUndoExternal?: () => void, onRedoExternal?: () => void, isRevisionMode?: boolean, revisionColor?: string}} props */
export default function ScreenplayEditor({ ast = [], onChange, zoomLevel = 100, onGhostwriter, characters = [], onPageChange, onProofPage, onUndoExternal, onRedoExternal, isRevisionMode = false, revisionColor = 'pink' }) {
  const editorRefs = useRef(/** @type {Record<string, HTMLDivElement | null>} */ ({}));
  const containerRef = useRef(/** @type {HTMLDivElement | null} */ (null));
  const debounceTimerRef = useRef(/** @type {ReturnType<typeof setTimeout> | null} */ (null));

  // Undo / Redo Stack State
  const [history, setHistory] = useState([ast]);
  const [historyIndex, setHistoryIndex] = useState(0);

  // Autocomplete state with keyboard navigation
  const [autocomplete, setAutocomplete] = useState(/** @type {{show: boolean, type: string, blockId: string | null, text: string, selectedIndex: number, x: number, y: number, items: string[]}} */ ({
    show: false,
    type: 'character', // 'character' | 'scene'
    blockId: null,
    text: '',
    selectedIndex: 0,
    x: 0,
    y: 0,
    items: []
  }));

  // Focused Block tracking
  const [focusedBlockId, setFocusedBlockId] = useState(/** @type {string | null} */ (null));
  const [hoveredBlockId, setHoveredBlockId] = useState(/** @type {string | null} */ (null));

  // Telemetry HUD
  const [lastWheelEvent, setLastWheelEvent] = useState(/** @type {{"deltaY": number, "targetTag": string, "scrollTop": number, "scrollHeight": number, "clientHeight": number} | null} */ (null));

  // Synchronize external AST changes into history if completely new script
  useEffect(() => {
    if (ast && ast.length > 0 && history.length === 1 && history[0].length === 0) {
      setHistory([ast]);
      setHistoryIndex(0);
    }
  }, [ast, history]);

  // Push new state to undo/redo history
  const pushHistory = useCallback(
/** @param {import('/types/domain').ScreenplayBlock[]} newAst */
( newAst) => {
    setHistory(prev => {
      const upToCurrent = prev.slice(0, historyIndex + 1);
      const updated = [...upToCurrent, newAst];
      if (updated.length > 100) updated.shift(); // keep max 100 history states
      return updated;
    });
    setHistoryIndex(prev => Math.min(prev + 1, 99));
  }, [historyIndex]);

  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const targetIndex = historyIndex - 1;
      const targetAst = history[targetIndex];
      setHistoryIndex(targetIndex);
      if (onChange) onChange(targetAst);
      if (onUndoExternal) onUndoExternal();
    }
  }, [historyIndex, history, onChange, onUndoExternal]);

  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const targetIndex = historyIndex + 1;
      const targetAst = history[targetIndex];
      setHistoryIndex(targetIndex);
      if (onChange) onChange(targetAst);
      if (onRedoExternal) onRedoExternal();
    }
  }, [historyIndex, history, onChange, onRedoExternal]);

  // Extract known Scene Locations from existing AST
  const getKnownSceneLocations = useCallback(() => {
    const locations = new Set();
    locations.add('INT. ');
    locations.add('EXT. ');
    locations.add('INT./EXT. ');
    locations.add('EST. ');

    (ast || []).forEach(b => {
      if (b.type === 'Scene Heading' && b.text) {
        const clean = b.text.trim().toUpperCase();
        if (clean) locations.add(clean);
      }
    });
    return Array.from(locations);
  }, [ast]);

  // Extract all known Character names from Character Vault + existing AST
  const getAllCharacterNames = useCallback(() => {
    const charNames = new Set();
    characters.forEach(c => {
      if (c.name) charNames.add(c.name.trim().toUpperCase());
    });
    (ast || []).forEach(b => {
      if (b.type === 'Character' && b.text) {
        const clean = b.text.replace(/\s*\(.*?\)\s*/g, '').replace(/\s*\^/g, '').trim().toUpperCase();
        if (clean) charNames.add(clean);
      }
    });
    return Array.from(charNames);
  }, [characters, ast]);

  // Scroll handler
  
/** @param {import('react').UIEvent<HTMLDivElement>} e */
const handleScroll = ( e) => {
    if (!onPageChange) return;
    const container = e.currentTarget;
    const containerTop = container.scrollTop;
    const pages = container.querySelectorAll('.screenplay-page');
    for (let i = 0; i < pages.length; i++) {
      const page = pages[i];
      if (!(page instanceof HTMLElement)) continue;
      const pageTop = page.offsetTop - container.offsetTop;
      const pageHeight = page.offsetHeight;
      if (pageTop + (pageHeight / 3) >= containerTop) {
        onPageChange(i + 1);
        break;
      }
    }
  };

  
/** @param {import('react').WheelEvent<HTMLDivElement>} e */
const handleWheel = ( e) => {
    const container = containerRef.current;
    if (!container) return;
    container.scrollTop += e.deltaY;
    
    setLastWheelEvent({
      deltaY: e.deltaY,
      targetTag: e.target instanceof Element ? e.target.tagName : 'UNKNOWN',
      scrollTop: Math.round(container.scrollTop),
      scrollHeight: container.scrollHeight,
      clientHeight: container.clientHeight
    });
  };

  // Helper to change block type
  
/** @param {number} index */
const toggleDualDialogue = ( index) => {
    if (index < 0 || index >= ast.length) return;
    const block = ast[index];
    if (block.type !== 'Character') return;
    const newAst = [...ast];
    newAst[index] = { ...block, dual: !block.dual };
    pushHistory(newAst);
    onChange(newAst);
  };

  
/** @param {number} index @param {string} targetType */
const setBlockType = ( index,  targetType) => {
    if (index < 0 || index >= ast.length) return;
    const newAst = [...ast];
    let newText = newAst[index].text || '';
    
    // Auto-formatting conversions
    if (targetType === 'Scene Heading' || targetType === 'Character' || targetType === 'Transition') {
      newText = newText.toUpperCase();
    } else if (targetType === 'Parenthetical') {
      const clean = newText.replace(/^\(+|\)+$/g, '').trim();
      newText = clean ? `(${clean})` : '()';
    }

    newAst[index] = { ...newAst[index], type: targetType, text: newText };
    pushHistory(newAst);
    onChange(newAst);

    const blockId = newAst[index].id;
    setTimeout(() => {
      const el = editorRefs.current[blockId];
      if (el) {
        el.innerText = newText;
        el.focus();
      }
    }, 0);
  };

  // Helper to update text with Smart Auto-Detection
  
/** @param {string} id @param {string} rawText */
const handleInput = ( id,  rawText, pageNumber = 1) => {
    let newText = rawText;
    const originalIndex = ast.findIndex(b => b.id === id);
    if (originalIndex === -1) return;

    const block = ast[originalIndex];
    // Blur also calls this handler. An unchanged block must not serialize the
    // whole imported draft through the formatting-normalizing AST adapter.
    if (rawText === block.text) return;
    let newType = block.type;

    // Check for !proof command
    if (newText && newText.includes('!proof')) {
      const cleaned = newText.replace('!proof', '').trim();
      const el = editorRefs.current[id];
      if (el) el.innerText = cleaned;
      
      const updatedBlock = { ...block, type: newType, text: cleaned };
      if (isRevisionMode && block.text !== cleaned) {
        updatedBlock.revision = true;
        updatedBlock.revisionColor = revisionColor;
      }
      const newAst = ast.map(b => b.id === id ? updatedBlock : b);
      pushHistory(newAst);
      onChange(newAst);
      
      if (typeof onProofPage === 'function') {
        onProofPage(pageNumber);
      }
      return;
    }

    // 1. SMART AUTO-DETECTION: Action -> Scene Heading
    if (newType === 'Action' || newType === 'General') {
      const trimmed = newText.trim();
      const upper = trimmed.toUpperCase();
      if (
        upper.startsWith('INT.') || 
        upper.startsWith('EXT.') || 
        upper.startsWith('INT./EXT.') || 
        upper.startsWith('I/E.') || 
        upper.startsWith('EST.') ||
        upper.startsWith('INT ') ||
        upper.startsWith('EXT ')
      ) {
        newType = 'Scene Heading';
        newText = upper;
        const el = editorRefs.current[id];
        if (el && el.innerText !== upper) {
          el.innerText = upper;
        }
      } else if (
        upper.endsWith(' TO:') || 
        upper.startsWith('FADE IN:') || 
        upper.startsWith('FADE OUT.') || 
        upper.startsWith('CUT TO:') ||
        upper.startsWith('DISSOLVE TO:') ||
        upper.startsWith('SMASH CUT TO:')
      ) {
        newType = 'Transition';
        newText = upper;
        const el = editorRefs.current[id];
        if (el && el.innerText !== upper) {
          el.innerText = upper;
        }
      }
    }

    // 2. Character uppercase enforcement
    if (newType === 'Character') {
      const upper = newText.toUpperCase();
      if (newText !== upper) {
        newText = upper;
        const el = editorRefs.current[id];
        if (el) el.innerText = upper;
      }
    }

    const updatedBlock = { ...block, type: newType, text: newText };
    if (isRevisionMode && block.text !== newText) {
      updatedBlock.revision = true;
      updatedBlock.revisionColor = revisionColor;
    }

    const newAst = ast.map(b => b.id === id ? updatedBlock : b);
    onChange(newAst);

    // Debounce history record for continuous typing
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      pushHistory(newAst);
    }, 600);
  };

  // Auto-complete selection handler
  
/** @param {string} itemText */
const handleSelectAutocomplete = ( itemText) => {
    const { blockId } = autocomplete;
    if (!blockId) return;

    const el = editorRefs.current[blockId];
    if (el) el.innerText = itemText;

    const newAst = ast.map(b => {
      if (b.id === blockId) {
        return { ...b, text: itemText };
      }
      return b;
    });

    pushHistory(newAst);
    onChange(newAst);
    setAutocomplete({ show: false, type: 'character', blockId: null, text: '', selectedIndex: 0, x: 0, y: 0, items: [] });

    setTimeout(() => {
      if (el) {
        el.focus();
        const selection = window.getSelection();
        if (!selection) return;
        const range = document.createRange();
        range.selectNodeContents(el);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }, 0);
  };

  // KeyDown event dispatcher
  
/** @param {import('react').KeyboardEvent<HTMLDivElement>} e @param {number} index @param {import('/types/domain').ScreenplayBlock} block */
const handleKeyDown = ( e,  index,  block) => {
    // 1. Check for Undo (Ctrl+Z / Cmd+Z) & Redo (Ctrl+Y / Ctrl+Shift+Z / Cmd+Shift+Z)
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      if (e.shiftKey) {
        handleRedo();
      } else {
        handleUndo();
      }
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
      e.preventDefault();
      handleRedo();
      return;
    }

    // 2. Element Hotkeys: Ctrl+1 through Ctrl+6
    if ((e.ctrlKey || e.metaKey) && TYPE_SHORTCUTS[e.key]) {
      e.preventDefault();
      setBlockType(index, TYPE_SHORTCUTS[e.key]);
      return;
    }

    // 3. Autocomplete Navigation (ArrowUp, ArrowDown, Enter, Tab, Escape)
    if (autocomplete.show && autocomplete.blockId === block.id) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setAutocomplete(prev => ({
          ...prev,
          selectedIndex: (prev.selectedIndex + 1) % Math.max(1, prev.items.length)
        }));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setAutocomplete(prev => ({
          ...prev,
          selectedIndex: (prev.selectedIndex - 1 + prev.items.length) % Math.max(1, prev.items.length)
        }));
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        if (autocomplete.items.length > 0 && autocomplete.items[autocomplete.selectedIndex]) {
          e.preventDefault();
          handleSelectAutocomplete(autocomplete.items[autocomplete.selectedIndex]);
          return;
        } else {
          setAutocomplete(prev => ({ ...prev, show: false }));
        }
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setAutocomplete(prev => ({ ...prev, show: false }));
        return;
      }
    }

    // 4. Tab Key Handling (Cycle Element Types)
    if (e.key === 'Tab') {
      e.preventDefault();
      if (block.type === 'Dialogue') {
        // Dialogue + Tab -> Parenthetical
        setBlockType(index, 'Parenthetical');
      } else {
        const currentTypeIndex = TYPE_CYCLE.indexOf(block.type);
        const nextType = TYPE_CYCLE[(currentTypeIndex + 1) % TYPE_CYCLE.length];
        setBlockType(index, nextType);
      }
      return;
    }

    // 5. Enter Key Handling (Hollywood Flow Engine)
    if (e.key === 'Enter') {
      e.preventDefault();
      
      // Determine logical next type based on Hollywood rules
      let nextType = "Action";
      if (block.type === "Character") nextType = "Dialogue";
      else if (block.type === "Dialogue") nextType = "Action";
      else if (block.type === "Parenthetical") nextType = "Dialogue";
      else if (block.type === "Scene Heading") nextType = "Action";
      else if (block.type === "Transition") nextType = "Scene Heading";

      const newBlock = {
        id: crypto.randomUUID(),
        type: nextType,
        text: ""
      };

      const newAst = [...ast];
      newAst.splice(index + 1, 0, newBlock);
      pushHistory(newAst);
      onChange(newAst);

      // Focus the new block after render
      setTimeout(() => {
        if (editorRefs.current[newBlock.id]) {
          editorRefs.current[newBlock.id]?.focus();
        }
      }, 0);
      return;
    }

    // 6. Backspace on Empty Block (Merge / Delete Block)
    if (e.key === 'Backspace' && (block.text === '' || block.text === '()')) {
      e.preventDefault();
      if (index > 0) {
        const newAst = [...ast];
        newAst.splice(index, 1);
        pushHistory(newAst);
        onChange(newAst);

        // Focus previous block
        setTimeout(() => {
          const prevId = newAst[index - 1].id;
          if (editorRefs.current[prevId]) {
            const el = editorRefs.current[prevId];
            el.focus();
            const selection = window.getSelection();
        if (!selection) return;
            const range = document.createRange();
            range.selectNodeContents(el);
            range.collapse(false);
            selection.removeAllRanges();
            selection.addRange(range);
          }
        }, 0);
      }
      return;
    }

    // 7. AI Ghostwriter (Ctrl+J / Cmd+J)
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') {
      e.preventDefault();
      if (typeof onGhostwriter === 'function') {
        onGhostwriter(index);
      }
    }
  };

  // KeyUp event to trigger Auto-Complete for Character and Scene Headings
  
/** @param {import('react').KeyboardEvent<HTMLDivElement>} e @param {import('/types/domain').ScreenplayBlock} block */
const handleKeyUp = ( e,  block) => {
    if (['ArrowUp', 'ArrowDown', 'Enter', 'Tab', 'Escape'].includes(e.key)) {
      return;
    }

    const text = (e.currentTarget.innerText || '').trim();

    // 1. Character Auto-Complete
    if (block.type === 'Character') {
      if (text.length > 0) {
        const allChars = getAllCharacterNames();
        const matches = allChars.filter(name => name.startsWith(text.toUpperCase()));
        const el = editorRefs.current[block.id];
        if (el && matches.length > 0) {
          const rect = el.getBoundingClientRect();
          setAutocomplete({
            show: true,
            type: 'character',
            blockId: block.id,
            text,
            selectedIndex: 0,
            x: rect.left,
            y: rect.bottom + 4,
            items: matches.slice(0, 6)
          });
          return;
        }
      }
    }

    // 2. Scene Heading Auto-Complete
    if (block.type === 'Scene Heading') {
      if (text.length > 0) {
        const allLocations = getKnownSceneLocations();
        const matches = allLocations.filter(loc => loc.startsWith(text.toUpperCase()));
        const el = editorRefs.current[block.id];
        if (el && matches.length > 0) {
          const rect = el.getBoundingClientRect();
          setAutocomplete({
            show: true,
            type: 'scene',
            blockId: block.id,
            text,
            selectedIndex: 0,
            x: rect.left,
            y: rect.bottom + 4,
            items: matches.slice(0, 6)
          });
          return;
        }
      }
    }

    if (autocomplete.show) {
      setAutocomplete(prev => ({ ...prev, show: false }));
    }
  };

  
/** @param {string} type @returns {import('react').CSSProperties} */
const getStyleForType = ( type, isDualItem = false) => {
    /** @type {import('react').CSSProperties} */
    const base = {
      outline: 'none',
      minHeight: '16px',
      lineHeight: '16px',
      whiteSpace: 'pre-wrap',
      wordWrap: 'break-word',
      fontFamily: '"Courier Prime", "Courier New", Courier, monospace',
      fontSize: '15px',
      position: 'relative',
      transition: 'background 0.15s ease'
    };
    
    if (isDualItem) {
      switch (type) {
        case 'Character': return { ...base, textTransform: 'uppercase', marginTop: '0', textAlign: 'center', fontWeight: 'bold' };
        case 'Dialogue': return { ...base, marginTop: '0', textAlign: 'center' };
        case 'Parenthetical': return { ...base, marginTop: '0', textAlign: 'center', fontStyle: 'italic' };
        default: return base;
      }
    }
    
    switch (type) {
      case 'Scene Heading':
        // Left margin: 1.50" (0px relative to left pad), right margin: 7.50" (max-width: 576px)
        return { ...base, textTransform: 'uppercase', marginTop: '24px', marginLeft: '0px', maxWidth: '576px', fontWeight: 'bold' };
      case 'Action':
        // Left margin: 1.50" (0px relative), right margin: 7.50" (max-width: 576px)
        return { ...base, marginTop: '12px', marginLeft: '0px', maxWidth: '576px' };
      case 'Character':
        // Left margin: 3.50" (+192px relative to 1.50" left margin), right margin: 7.25" (max-width: 360px)
        return { ...base, textTransform: 'uppercase', marginTop: '14px', marginLeft: '192px', maxWidth: '360px', fontWeight: 'bold' }; 
      case 'Parenthetical':
        // Left margin: 3.00" - 0.10" first line (+144px relative), right margin: 5.50" (max-width: 240px)
        return { ...base, marginTop: '2px', marginLeft: '144px', maxWidth: '240px', fontStyle: 'italic' };
      case 'Dialogue':
        // Left margin: 2.50" (+96px relative to 1.50" left margin), right margin: 6.00" (max-width: 336px)
        return { ...base, marginTop: '2px', marginLeft: '96px', maxWidth: '336px' };
      case 'Transition':
        // Right-aligned, left margin: 5.50" (+384px relative), right margin: 7.10" (max-width: 154px)
        return { ...base, textTransform: 'uppercase', marginTop: '14px', marginLeft: '384px', maxWidth: '192px', fontWeight: 'bold' };
      default:
        return base;
    }
  };

  const pages = paginateScreenplayBlocks(ast).map(page => page.blocks);

  // Group pages for dual dialogue
  const groupedPages = pages.map(pageBlocks => {
    /** @type {Array<import('/types/domain').ScreenplayBlock | {id: string, isDualContainer: true, leftBlocks: import('/types/domain').ScreenplayBlock[], rightBlocks: import('/types/domain').ScreenplayBlock[]}>} */
    const newBlocks = [];
    let i = 0;
    while (i < pageBlocks.length) {
      if (pageBlocks[i].type === 'Character') {
         let nextCharIdx = -1;
         let j = i + 1;
         while (j < pageBlocks.length) {
             if (pageBlocks[j].type === 'Character') {
                 nextCharIdx = j;
                 break;
             }
             if (pageBlocks[j].type !== 'Dialogue' && pageBlocks[j].type !== 'Parenthetical') {
                 break;
             }
             j++;
         }
         
         if (nextCharIdx !== -1 && pageBlocks[nextCharIdx].dual) {
             let endRightIdx = nextCharIdx + 1;
             while (endRightIdx < pageBlocks.length) {
                 if (pageBlocks[endRightIdx].type !== 'Dialogue' && pageBlocks[endRightIdx].type !== 'Parenthetical') {
                     break;
                 }
                 endRightIdx++;
             }
             
             newBlocks.push({
                 isDualContainer: true,
                 leftBlocks: pageBlocks.slice(i, nextCharIdx),
                 rightBlocks: pageBlocks.slice(nextCharIdx, endRightIdx),
                 id: pageBlocks[i].id + '_dual'
             });
             i = endRightIdx;
             continue;
         }
      }
      newBlocks.push(pageBlocks[i]);
      i++;
    }
    return newBlocks;
  });

  const displayPages = groupedPages.length > 0 ? groupedPages : [[{ id: 'init_head', type: 'Scene Heading', text: 'INT. SCENE - DAY' }, { id: 'init_act', type: 'Action', text: '' }]];

  const scale = zoomLevel / 100;

  
/** @param {import('/types/domain').ScreenplayBlock} block */
const renderSingleBlock = ( block, isDualItem = false, pageNumber = 1) => {
    const originalIndex = ast.findIndex(b => b.id === block.id);
    const isFocused = focusedBlockId === block.id;
    const isHovered = hoveredBlockId === block.id;
    const badge = TYPE_BADGES[block.type] || TYPE_BADGES['Action'];

    return (
      <div 
        key={block.id} 
        style={{ position: 'relative' }}
        onMouseEnter={() => setHoveredBlockId(block.id)}
        onMouseLeave={() => setHoveredBlockId(null)}
      >
        {/* Left Gutter Element Type Tag (Appears on Hover or Focus) */}
        {(isFocused || isHovered) && !isDualItem && (
          <div 
            style={{
              position: 'absolute',
              left: block.type === 'Character' ? '-114px' : '-84px',
              top: '50%',
              transform: 'translateY(-50%)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              zIndex: 50,
              userSelect: 'none'
            }}
          >
            {block.type === 'Character' && (
              <button
                onClick={() => toggleDualDialogue(originalIndex)}
                style={{
                  background: block.dual ? '#22c55e' : 'rgba(255,255,255,0.1)',
                  color: block.dual ? '#fff' : '#aaa',
                  border: `1px solid ${block.dual ? '#16a34a' : '#555'}`,
                  borderRadius: '4px',
                  padding: '1px 5px',
                  fontSize: '0.65rem',
                  fontWeight: 'bold',
                  fontFamily: 'monospace',
                  cursor: 'pointer'
                }}
                title="Toggle Dual Dialogue"
              >
                DUAL
              </button>
            )}
            <button
              onClick={() => {
                const currentIdx = TYPE_CYCLE.indexOf(block.type);
                const nextType = TYPE_CYCLE[(currentIdx + 1) % TYPE_CYCLE.length];
                setBlockType(originalIndex, nextType);
              }}
              style={{
                background: badge.bg,
                color: badge.color,
                border: `1px solid ${badge.border}`,
                borderRadius: '4px',
                padding: '1px 5px',
                fontSize: '0.65rem',
                fontWeight: 'bold',
                fontFamily: 'monospace',
                cursor: 'pointer',
                letterSpacing: '0.5px'
              }}
              title="Click to cycle element type (or press Tab / Ctrl+1..6)"
            >
              {badge.label}
            </button>
          </div>
        )}

        <div
          id={`sw-block-${block.id}`}
          ref={el => editorRefs.current[block.id] = el}
          data-block-type={block.type}
          role="textbox"
          aria-label={`${block.type} screenplay block`}
          aria-multiline="true"
          contentEditable
          suppressContentEditableWarning
          style={{
            ...getStyleForType(block.type, isDualItem),
            backgroundColor: isFocused ? 'rgba(56, 189, 248, 0.04)' : (block.revision ? `var(--tw-colors-${block.revisionColor}-500, rgba(236,72,153,0.1))` : 'transparent'),
            borderRight: block.revision ? `4px solid var(--tw-colors-${block.revisionColor}-500, #ec4899)` : 'none',
            borderRadius: '2px'
          }}
          onFocus={() => setFocusedBlockId(block.id)}
          onKeyDown={
( e) => handleKeyDown(e, originalIndex, block)}
          onKeyUp={
( e) => handleKeyUp(e, block)}
          onBlur={
( e) => {
            setFocusedBlockId(null);
            handleInput(block.id, e.currentTarget.innerText, pageNumber);
          }}
        >
          {block.text}
        </div>
      </div>
    );
  };

  return (
    <div 
      ref={containerRef}
      onScroll={handleScroll}
      onWheel={handleWheel}
      className="sw-paginated-container" 
      style={{ 
        flex: 1,
        height: '100%',
        maxHeight: '100%',
        minHeight: 0,
        width: '100%',
        overflowY: 'auto',
        overflowX: 'hidden',
        boxSizing: 'border-box',
        backgroundColor: '#0a0a0a',
        padding: '32px 0',
        display: 'block',
        position: 'relative'
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', minHeight: '100%' }}>
        {displayPages.map((pageBlocks, pageIndex) => (
          <div 
            key={`page-${pageIndex}`}
            id={`sw-page-${pageIndex + 1}`}
            className="screenplay-page"
            style={{
              width: '816px',
              minHeight: '1056px',
              backgroundColor: '#ffffff',
              color: '#000000',
              padding: '96px 96px 96px 144px',
              boxSizing: 'border-box',
              boxShadow: '0 4px 14px rgba(0,0,0,0.6)',
              position: 'relative',
              fontFamily: '"Courier Prime", "Courier New", Courier, monospace',
              fontSize: '15px',
              transform: `scale(${scale})`,
              transformOrigin: 'top center',
              marginBottom: `${32 * scale + (1056 * (scale - 1))}px`,
              display: 'block',
              margin: '0 auto 32px auto',
              flexShrink: 0
            }}
          >
            {/* Standard Top-Right Screenplay Page Number */}
            {pageIndex > 0 && (
              <div style={{ position: 'absolute', top: '48px', right: '96px', fontSize: '15px', fontWeight: 'bold', color: '#333' }}>
                {pageIndex + 1}.
              </div>
            )}

            {pageBlocks.map((item) => {
               if ('isDualContainer' in item) {
                   return (
                       <div key={item.id} style={{ display: 'flex', width: '100%', marginTop: '16px', gap: '24px' }}>
                           <div style={{ flex: 1 }}>
                               {item.leftBlocks.map( 
block => renderSingleBlock(block, true, pageIndex + 1))}
                           </div>
                           <div style={{ flex: 1 }}>
                               {item.rightBlocks.map( 
block => renderSingleBlock(block, true, pageIndex + 1))}
                           </div>
                       </div>
                   );
               } else {
                   return renderSingleBlock(item, false, pageIndex + 1);
               }
            })}
          </div>
        ))}
      </div>
      
      {/* Enhanced Keyboard-Navigable Autocomplete Popup */}
      {autocomplete.show && autocomplete.items.length > 0 && (
          <div style={{
              position: 'fixed',
              top: `${autocomplete.y}px`,
              left: `${autocomplete.x}px`,
              background: '#111827',
              border: '1px solid #38bdf8',
              borderRadius: '6px',
              padding: '4px 0',
              zIndex: 10000,
              boxShadow: '0 8px 24px rgba(0,0,0,0.7)',
              minWidth: '220px',
              fontFamily: '"Courier Prime", Courier, monospace'
          }}>
              <div style={{ padding: '4px 10px', fontSize: '0.7rem', color: '#94a3b8', borderBottom: '1px solid #1f2937', display: 'flex', justifyContent: 'space-between' }}>
                <span>{autocomplete.type === 'character' ? '👤 CHARACTER SUGGESTIONS' : '🎬 SCENE LOCATIONS'}</span>
                <span>↑↓ / Tab</span>
              </div>
              {autocomplete.items.map((item, idx) => (
                  <div 
                      key={idx} 
                      style={{
                          padding: '6px 12px',
                          color: idx === autocomplete.selectedIndex ? '#000' : '#fff',
                          background: idx === autocomplete.selectedIndex ? '#38bdf8' : 'transparent',
                          cursor: 'pointer',
                          fontSize: '0.85rem',
                          fontWeight: idx === autocomplete.selectedIndex ? 'bold' : 'normal',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                      }}
                      onMouseEnter={() => setAutocomplete(prev => ({ ...prev, selectedIndex: idx }))}
                      onMouseDown={
( e) => {
                        e.preventDefault();
                        handleSelectAutocomplete(item);
                      }}
                  >
                      <span>{autocomplete.type === 'character' ? '👤' : '📍'}</span>
                      <span>{item}</span>
                  </div>
              ))}
          </div>
      )}

      {/* Live Scroll Telemetry Monitor HUD */}
      {lastWheelEvent && (
        <div style={{
          position: 'fixed',
          bottom: '16px',
          right: '24px',
          background: 'rgba(15, 23, 42, 0.92)',
          border: '1px solid #38bdf8',
          borderRadius: '8px',
          padding: '6px 14px',
          color: '#38bdf8',
          fontSize: '0.75rem',
          fontFamily: 'monospace',
          zIndex: 99999,
          boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          pointerEvents: 'none'
        }}>
          <span style={{ color: '#4ade80' }}>● Live Wheel:</span>
          <span>ΔY: {lastWheelEvent.deltaY}</span>
          <span style={{ color: '#94a3b8' }}>|</span>
          <span>Target: &lt;{lastWheelEvent.targetTag}&gt;</span>
          <span style={{ color: '#94a3b8' }}>|</span>
          <span style={{ color: '#facc15' }}>Scroll: {lastWheelEvent.scrollTop} / {lastWheelEvent.scrollHeight - lastWheelEvent.clientHeight}px</span>
        </div>
      )}
    </div>
  );
}
