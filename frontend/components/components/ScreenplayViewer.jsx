import { paginateScreenplayBlocks } from '/utils/screenplayPagination.js';
import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react";

const ScreenplayViewer = forwardRef(
/** @param {{ast?: import('/types/domain').ScreenplayBlock[], beats?: import('/types/domain').ScreenplayBeat[], zoomLevel?: number, currentPage?: number, onPageChange?: (page: number) => void, searchQuery?: string, onSwitchToEditor?: (id: string) => void, fitToWidth?: boolean, showInternalHeader?: boolean}} props @param {import('react').ForwardedRef<import('/types/domain').ScreenplayViewerHandle>} ref */
function ScreenplayViewer({
  ast = [],
  beats = [],
  zoomLevel = 100,
  currentPage: externalPage,
  onPageChange,
  searchQuery: externalSearchQuery,
  onSwitchToEditor,
  fitToWidth = false,
  showInternalHeader = false
}, ref) {
  const [internalPage, setInternalPage] = useState(1);
  const [internalSearchQuery] = useState('');
  const [activeSearchIndex, setActiveSearchIndex] = useState(0);
  const [matchedBlockIds, setMatchedBlockIds] = useState(/** @type {Array<string>} */ ([]));
  const viewerContainerRef = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [previewWidth, setPreviewWidth] = useState(0);
  useEffect(() => {
    if (!fitToWidth || !viewerContainerRef.current) return;
    const element=viewerContainerRef.current;
    const read=()=>setPreviewWidth(element.clientWidth);
    const observer=new ResizeObserver(read);
    observer.observe(element);read();
    return ()=>observer.disconnect();
  },[fitToWidth]);


  const currentPage = externalPage !== undefined ? externalPage : internalPage;
  const searchQuery = externalSearchQuery !== undefined ? externalSearchQuery : internalSearchQuery;

  // 1. Pagination calculation (54-line industry standard per 8.5" x 11" page)
  const pages = paginateScreenplayBlocks(ast).map(page => page.blocks);
  const totalPages = Math.max(1, pages.length);

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

  // Element styles - Hollywood Courier Standard with balanced margins
  
/** @param {string} type @returns {import('react').CSSProperties} */
const getStyleForType = ( type, isDual = false) => {
    /** @type {import('react').CSSProperties} */
    const base = {
      fontFamily: '"Courier Prime", "Courier New", Courier, monospace',
      fontSize: '14.5px',
      lineHeight: '1.25',
      color: '#000000',
      minHeight: '1.2em',
      outline: 'none',
      whiteSpace: 'pre-wrap',
      wordBreak: 'normal',
      overflowWrap: 'break-word',
      letterSpacing: '0.02em',
      transition: 'background-color 0.2s ease',
      cursor: 'text'
    };

    if (isDual) {
      switch (type) {
        case 'Character':
          return { ...base, textTransform: 'uppercase', marginTop: '14px', textAlign: 'center', fontWeight: 'bold' };
        case 'Dialogue':
          return { ...base, marginTop: '2px', textAlign: 'left', maxWidth: '260px' };
        case 'Parenthetical':
          return { ...base, marginTop: '1px', textAlign: 'center', fontStyle: 'italic', maxWidth: '220px' };
        default:
          return base;
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

  // Safe inner-container scroll helper (Prevents window or top-bar from scrolling out of view!)
  
/** @param {HTMLElement} el */
const scrollElementIntoContainer = ( el, alignTop = false) => {
    const container = viewerContainerRef.current;
    if (!container || !el) return;
    const containerRect = container.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    const currentScrollTop = container.scrollTop;
    let targetTop = currentScrollTop + (elRect.top - containerRect.top);
    if (!alignTop) {
      targetTop -= (containerRect.height / 2) - (elRect.height / 2);
    } else {
      targetTop -= 20; // 20px padding from top
    }
    container.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
  };

  // 2. Navigation Actions
  
/** @param {number} pageNum */
const scrollToPage = ( pageNum) => {
    const validPage = Math.max(1, Math.min(pageNum, totalPages));
    if (onPageChange) {
      onPageChange(validPage);
    } else {
      setInternalPage(validPage);
    }
    const el = document.getElementById(`viewer-page-${validPage}`);
    if (el) {
      scrollElementIntoContainer(el, true);
    }
  };

  
/** @param {import('/types/domain').ScreenplayBeat} beat */
const scrollToScene = ( beat) => {
    if (!beat) return;
    const cleanHeading = (beat.heading || '').trim().toUpperCase();
    const targetBlock = ast.find(b => b.type === 'Scene Heading' && cleanHeading && b.text.trim().toUpperCase().includes(cleanHeading.substring(0, 25)));
    
    if (targetBlock) {
      const el = document.getElementById(`viewer-block-${targetBlock.id}`);
      if (el) {
        scrollElementIntoContainer(el, false);
        el.style.backgroundColor = 'rgba(250, 204, 21, 0.4)';
        el.style.outline = '2px solid #facc15';
        setTimeout(() => {
          el.style.backgroundColor = 'transparent';
          el.style.outline = 'none';
        }, 1800);
        return;
      }
    }

    if (beat.page) {
      scrollToPage(Math.floor(beat.page));
    }
  };

  // 3. Search Engine in Script
  useEffect(() => {
    if (!searchQuery || !searchQuery.trim()) {
      setMatchedBlockIds([]);
      setActiveSearchIndex(0);
      return;
    }

    const matches = ast.filter(b => b.text && b.text.toLowerCase().includes(searchQuery.toLowerCase())).map(b => b.id);
    setMatchedBlockIds(matches);
    setActiveSearchIndex(0);

    if (matches.length > 0) {
      const firstEl = document.getElementById(`viewer-block-${matches[0]}`);
      if (firstEl) {
        scrollElementIntoContainer(firstEl, false);
      }
    }
  }, [searchQuery, ast]);

  const handleNextSearch = () => {
    if (matchedBlockIds.length === 0) return;
    const nextIdx = (activeSearchIndex + 1) % matchedBlockIds.length;
    setActiveSearchIndex(nextIdx);
    const el = document.getElementById(`viewer-block-${matchedBlockIds[nextIdx]}`);
    if (el) {
      scrollElementIntoContainer(el, false);
    }
  };

  const handlePrevSearch = () => {
    if (matchedBlockIds.length === 0) return;
    const prevIdx = (activeSearchIndex - 1 + matchedBlockIds.length) % matchedBlockIds.length;
    setActiveSearchIndex(prevIdx);
    const el = document.getElementById(`viewer-block-${matchedBlockIds[prevIdx]}`);
    if (el) {
      scrollElementIntoContainer(el, false);
    }
  };

  // Expose imperative handle to parent (ScreenwritingTab)
  useImperativeHandle(ref, () => ({
    scrollToPage,
    scrollToScene,
    handleNextSearch,
    handlePrevSearch,
    totalPages,
    currentPage,
    matchedCount: matchedBlockIds.length,
    activeMatchIndex: activeSearchIndex + 1
  }));

  const fitScale = fitToWidth ? Math.min(1, Math.max(1, (previewWidth || window.innerWidth) - 16) / 816) : 1;
  const scale = (zoomLevel / 100) * fitScale;

  
/** @param {import('/types/domain').ScreenplayBlock} block */
const renderViewerBlock = ( block, isDual = false) => {
    const isMatched = matchedBlockIds.includes(block.id);
    const isActiveMatch = matchedBlockIds[activeSearchIndex] === block.id;

    return (
      <div
        key={block.id}
        id={`viewer-block-${block.id}`}
        style={{
          ...getStyleForType(block.type, isDual),
          backgroundColor: isActiveMatch ? '#fef08a' : (isMatched ? '#fef9c3' : 'transparent'),
          borderRadius: isMatched ? '3px' : '0',
          padding: isMatched ? '2px 4px' : '0',
          cursor: 'pointer'
        }}
        onDoubleClick={() => {
          if (onSwitchToEditor) onSwitchToEditor(block.id);
        }}
        title="Double-click to edit this scene in Editor"
      >
        {block.text}
      </div>
    );
  };

  
/** @param {import('react').WheelEvent<HTMLDivElement>} e */
const handleWheel = ( e) => {
    if (viewerContainerRef.current) {
      viewerContainerRef.current.scrollTop += e.deltaY;
    }
  };

  
/** @param {import('react').UIEvent<HTMLDivElement>} e */
const handleScroll = ( e) => {
    if (!onPageChange) return;
    const container = e.currentTarget;
    const containerTop = container.scrollTop;
    const pages = container.querySelectorAll(/** @type {'.screenplay-viewer-page'} */ ('.screenplay-viewer-page'));
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', maxHeight: '100%', width: '100%', minHeight: 0, background: '#0a0a0a', position: 'relative', overflow: 'hidden' }}>
      
      {/* Optional Internal Header (Only shown if showInternalHeader is true) */}
      {showInternalHeader && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 16px',
          background: '#161e2e',
          borderBottom: '1px solid #1f2937',
          color: '#e5e7eb',
          fontSize: '0.85rem',
          zIndex: 100,
          flexShrink: 0,
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          {/* Page Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button 
              onClick={() => scrollToPage(1)} 
              disabled={currentPage <= 1}
              style={{ background: '#1f2937', color: '#fff', border: '1px solid #374151', padding: '3px 8px', borderRadius: '4px', cursor: currentPage <= 1 ? 'not-allowed' : 'pointer' }}
              title="First Page"
            >⏮</button>
            <button 
              onClick={() => scrollToPage(currentPage - 1)} 
              disabled={currentPage <= 1}
              style={{ background: '#1f2937', color: '#fff', border: '1px solid #374151', padding: '3px 8px', borderRadius: '4px', cursor: currentPage <= 1 ? 'not-allowed' : 'pointer' }}
              title="Previous Page"
            >◀</button>
            
            <span style={{ color: '#9ca3af', fontSize: '0.8rem' }}>Page</span>
            <input 
              type="number"
              min="1"
              max={totalPages}
              value={currentPage}
              onChange={
( e) => {
                const val = parseInt(e.target.value);
                if (!isNaN(val)) scrollToPage(val);
              }}
              style={{ width: '48px', padding: '2px 4px', textAlign: 'center', background: '#111827', color: '#facc15', border: '1px solid #374151', borderRadius: '4px', fontWeight: 'bold' }}
            />
            <span style={{ color: '#9ca3af', fontSize: '0.8rem' }}>of {totalPages}</span>

            <button 
              onClick={() => scrollToPage(currentPage + 1)} 
              disabled={currentPage >= totalPages}
              style={{ background: '#1f2937', color: '#fff', border: '1px solid #374151', padding: '3px 8px', borderRadius: '4px', cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer' }}
              title="Next Page"
            >▶</button>
            <button 
              onClick={() => scrollToPage(totalPages)} 
              disabled={currentPage >= totalPages}
              style={{ background: '#1f2937', color: '#fff', border: '1px solid #374151', padding: '3px 8px', borderRadius: '4px', cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer' }}
              title="Last Page"
            >⏭</button>
          </div>

          {/* Scene Dropdown */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: '#9ca3af', fontSize: '0.8rem' }}>🎬 Scene:</span>
            <select 
              onChange={
( e) => {
                const selectedIndex = parseInt(e.target.value);
                if (!isNaN(selectedIndex) && beats[selectedIndex]) {
                  scrollToScene(beats[selectedIndex]);
                }
              }}
              defaultValue=""
              style={{ background: '#111827', color: '#38bdf8', border: '1px solid #374151', padding: '3px 8px', borderRadius: '4px', maxWidth: '200px', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              <option value="" disabled>Jump to Scene...</option>
              {beats.map((b, idx) => (
                <option key={idx} value={idx}>
                  {idx + 1}. {b.heading.substring(0, 30)}... (p.{Math.floor(b.page)})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* 2. Paginated Multi-Page Presentation Canvas (Isolated Scrolling) */}
      <div 
        ref={viewerContainerRef}
        onWheel={handleWheel}
        onScroll={handleScroll}
        style={{
          flex: 1,
          height: '100%',
          maxHeight: '100%',
          minHeight: 0,
          width: '100%',
          overflowY: 'auto',
          overflowX: fitToWidth ? 'auto' : 'hidden',
          boxSizing: 'border-box',
          backgroundColor: '#0a0a0a',
          padding: '24px 0',
          display: 'block',
          position: 'relative'
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', minHeight: '100%' }}>
          {groupedPages.map((pageBlocks, pageIndex) => (
            <div 
              key={`viewer-page-${pageIndex}`}
              id={`viewer-page-${pageIndex + 1}`}
              className="screenplay-viewer-page"
              style={{
                width: '816px',
                minHeight: '1056px',
                backgroundColor: '#ffffff',
                color: '#000000',
                padding: '96px 96px 96px 144px',
                boxSizing: 'border-box',
                boxShadow: '0 10px 30px rgba(0,0,0,0.7)',
                position: 'relative',
                fontFamily: '"Courier Prime", "Courier New", Courier, monospace',
                fontSize: '14.5px',
                transform: `scale(${scale})`,
                transformOrigin: 'top center',
                marginBottom: `${32 * scale + (1056 * (scale - 1))}px`,
                borderRadius: '2px',
                display: 'block',
                margin: fitToWidth ? `0 0 ${32 * scale + (1056 * (scale - 1))}px 0` : '0 auto 32px auto',
                flexShrink: 0
              }}
            >
              {/* Standard Top-Right Screenplay Page Number */}
              <div style={{ position: 'absolute', top: '48px', right: '96px', fontSize: '14.5px', fontWeight: 'bold', color: '#555' }}>
                {pageIndex + 1}.
              </div>

              {pageBlocks.map((item) => {
                 if ('isDualContainer' in item) {
                     return (
                         <div key={item.id} style={{ display: 'flex', width: '100%', marginTop: '16px', gap: '20px' }}>
                             <div style={{ flex: 1 }}>
                                 {item.leftBlocks.map( 
block => renderViewerBlock(block, true))}
                             </div>
                             <div style={{ flex: 1 }}>
                                 {item.rightBlocks.map( 
block => renderViewerBlock(block, true))}
                             </div>
                         </div>
                     );
                 } else {
                     return renderViewerBlock(item, false);
                 }
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});

export default ScreenplayViewer;
