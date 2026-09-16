import React, { useState, useMemo, useEffect } from 'react';
import { useAppStore } from './useAppStore.js';
import kjvData from '../data/newTestamentData.json';
import nivData from '../data/newTestamentData_NIV.json';

const CATEGORY_ICONS = {
  'All': '📜',
  'The Gospels': '✝️',
  'Church History': '🏛️',
  "Paul's Letters / Epistles": '✉️',
  'General Letters': '📜',
  'Prophecy / Apocalyptic': '🔥'
};

export default function BibleStudyTab({ backendUrl }) {
  const setActiveTab = useAppStore(state => state.setActiveTab);

  // Translation state: 'KJV' | 'NIV' | 'PARALLEL'
  const [translation, setTranslation] = useState('KJV');

  // Selection states
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedBook, setSelectedBook] = useState('Matthew');
  const [selectedChapter, setSelectedChapter] = useState(1);
  const [fontSize, setFontSize] = useState(18);
  const [fontFamily, setFontFamily] = useState('serif'); // 'serif' | 'sans'
  const [searchQuery, setSearchQuery] = useState('');
  const [searchScope, setSearchScope] = useState('all'); // 'all' | 'current'
  const [copiedVerse, setCopiedVerse] = useState(null);
  const [aiAnalysisStatus, setAiAnalysisStatus] = useState(null);

  // Active dataset based on translation
  const activeDataset = translation === 'NIV' ? nivData : kjvData;

  // Books in current category
  const visibleBooks = useMemo(() => {
    if (selectedCategory === 'All') {
      return Object.keys(activeDataset.books);
    }
    return activeDataset.categories[selectedCategory] || [];
  }, [selectedCategory, activeDataset]);

  // Ensure selected book is valid for current category
  useEffect(() => {
    if (visibleBooks.length > 0 && !visibleBooks.includes(selectedBook)) {
      setSelectedBook(visibleBooks[0]);
      setSelectedChapter(1);
    }
  }, [visibleBooks, selectedBook]);

  const currentBookData = activeDataset.books[selectedBook] || activeDataset.books['Matthew'];
  const totalChapters = currentBookData.chapters_count;

  // Ensure chapter is within range
  useEffect(() => {
    if (selectedChapter > totalChapters) {
      setSelectedChapter(1);
    }
  }, [selectedBook, totalChapters, selectedChapter]);

  // Current chapter verses for primary active translation
  const currentChapterVerses = useMemo(() => {
    if (!currentBookData.chapters || !currentBookData.chapters[selectedChapter - 1]) {
      return [];
    }
    return currentBookData.chapters[selectedChapter - 1];
  }, [currentBookData, selectedChapter]);

  // Verses for parallel comparison (KJV vs NIV)
  const parallelData = useMemo(() => {
    if (translation !== 'PARALLEL') return null;
    const kjvBook = kjvData.books[selectedBook];
    const nivBook = nivData.books[selectedBook];
    const kjvCh = kjvBook?.chapters?.[selectedChapter - 1] || [];
    const nivCh = nivBook?.chapters?.[selectedChapter - 1] || [];
    const maxLen = Math.max(kjvCh.length, nivCh.length);
    const rows = [];
    for (let i = 0; i < maxLen; i++) {
      rows.push({
        num: i + 1,
        kjv: kjvCh[i] || '',
        niv: nivCh[i] || ''
      });
    }
    return rows;
  }, [translation, selectedBook, selectedChapter]);

  // Concordance Search Results (across active dataset or both)
  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q || q.length < 2) return [];

    const results = [];
    const booksToSearch = searchScope === 'current' 
      ? [selectedBook] 
      : Object.keys(activeDataset.books);

    for (const bName of booksToSearch) {
      const bObj = activeDataset.books[bName];
      if (!bObj || !bObj.chapters) continue;

      for (let cIdx = 0; cIdx < bObj.chapters.length; cIdx++) {
        const cNum = cIdx + 1;
        const vList = bObj.chapters[cIdx];
        for (let vIdx = 0; vIdx < vList.length; vIdx++) {
          const vNum = vIdx + 1;
          const text = vList[vIdx];
          if (text.toLowerCase().includes(q)) {
            results.push({
              book: bName,
              chapter: cNum,
              verse: vNum,
              text,
              trans: translation === 'NIV' ? 'NIV' : 'KJV'
            });
            if (results.length >= 100) return results;
          }
        }
      }
    }
    return results;
  }, [searchQuery, searchScope, selectedBook, activeDataset, translation]);

  // Navigate chapters
  const prevChapter = () => {
    if (selectedChapter > 1) {
      setSelectedChapter(selectedChapter - 1);
    } else {
      const bookList = Object.keys(activeDataset.books);
      const bookIdx = bookList.indexOf(selectedBook);
      if (bookIdx > 0) {
        const prevB = bookList[bookIdx - 1];
        setSelectedBook(prevB);
        setSelectedChapter(activeDataset.books[prevB].chapters_count);
      }
    }
  };

  const nextChapter = () => {
    if (selectedChapter < totalChapters) {
      setSelectedChapter(selectedChapter + 1);
    } else {
      const bookList = Object.keys(activeDataset.books);
      const bookIdx = bookList.indexOf(selectedBook);
      if (bookIdx < bookList.length - 1) {
        const nextB = bookList[bookIdx + 1];
        setSelectedBook(nextB);
        setSelectedChapter(1);
      }
    }
  };

  // Copy full chapter
  const copyChapterText = () => {
    let payload = '';
    if (translation === 'PARALLEL' && parallelData) {
      payload = parallelData
        .map(r => `[Verse ${r.num}]\nKJV: ${r.kjv}\nNIV: ${r.niv}`)
        .join('\n\n');
      payload = `${selectedBook} Chapter ${selectedChapter} (KJV & NIV Parallel)\n\n` + payload;
    } else {
      payload = currentChapterVerses
        .map((v, i) => `${i + 1} ${v}`)
        .join('\n\n');
      payload = `${selectedBook} Chapter ${selectedChapter} (${translation})\n\n` + payload;
    }
    navigator.clipboard.writeText(payload);
    setCopiedVerse('all');
    setTimeout(() => setCopiedVerse(null), 2000);
  };

  // Copy individual verse
  const copyVerseText = (verseNum, text) => {
    navigator.clipboard.writeText(`${selectedBook} ${selectedChapter}:${verseNum} (${translation}) - "${text}"`);
    setCopiedVerse(verseNum);
    setTimeout(() => setCopiedVerse(null), 1800);
  };

  // 1-Click Send to Stehouwer LLM / BS-CHAT
  const sendToBsChat = () => {
    let prompt = '';
    if (translation === 'PARALLEL' && parallelData) {
      const parallelText = parallelData
        .map(r => `Verse ${r.num}:\n  [KJV] ${r.kjv}\n  [NIV] ${r.niv}`)
        .join('\n');
      prompt = `[SCRIPTURE COMPARATIVE ANALYSIS - KJV vs NIV] ${selectedBook} Chapter ${selectedChapter}\n\n` +
        `Please provide a rigorous theological, textual, and linguistic comparison of ${selectedBook} Chapter ${selectedChapter}:\n` +
        `1. Textual Differences: Key variations between the King James Version (Textus Receptus) and New International Version (Alexandrian / Critical Text)\n` +
        `2. Linguistic Insights: Semitic/Greek nuances in original wording\n` +
        `3. Historical Context & Narrative Structure\n` +
        `4. Cross-references across both Testaments\n\n` +
        `Parallel Verses:\n${parallelText}`;
    } else {
      const chapterContent = currentChapterVerses
        .map((v, i) => `[${i + 1}] ${v}`)
        .join('\n');
      prompt = `[SCRIPTURE ANALYSIS REQUEST - ${translation}] ${selectedBook} Chapter ${selectedChapter}\n\n` +
        `Please provide a rigorous architectural and theological breakdown of ${selectedBook} Chapter ${selectedChapter} (${translation}):\n` +
        `1. Historical Context & Authorship\n` +
        `2. Key Greek / Semitic linguistic insights & theological motifs\n` +
        `3. Verse-by-verse structural analysis\n` +
        `4. Direct cross-references throughout the Old and New Testaments\n\n` +
        `Text payload:\n${chapterContent}`;
    }

    try {
      localStorage.setItem('aibs_pending_chat_prompt', prompt);
      setAiAnalysisStatus(`Loaded ${selectedBook} ${selectedChapter} (${translation}) into BS-CHAT pipeline!`);
      setTimeout(() => {
        setActiveTab('ide');
      }, 700);
    } catch (e) {
      console.error(e);
      navigator.clipboard.writeText(prompt);
      setAiAnalysisStatus('Analysis prompt copied to clipboard!');
      setTimeout(() => setAiAnalysisStatus(null), 3000);
    }
  };

  const { summary } = activeDataset;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '100%',
      background: 'var(--bg-main, #0b0f19)',
      color: 'var(--text-main, #e2e8f0)',
      fontFamily: 'Inter, system-ui, sans-serif',
      overflow: 'hidden'
    }}>
      {/* ── TOP MISSION CONTROL & TELEMETRY HEADER ── */}
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            fontSize: '1.8rem',
            background: 'linear-gradient(135deg, #38bdf8, #818cf8)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'drop-shadow(0 2px 8px rgba(56, 189, 248, 0.4))'
          }}>
            📖
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em', color: '#f8fafc' }}>
                Sovereign Bible Hub
              </h1>

              {/* Translation Selector Pill Switches */}
              <div style={{
                display: 'flex',
                background: 'rgba(30, 41, 59, 0.7)',
                borderRadius: '8px',
                padding: '2px',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }}>
                <button
                  onClick={() => setTranslation('KJV')}
                  style={{
                    background: translation === 'KJV' ? '#0284c7' : 'transparent',
                    color: translation === 'KJV' ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '3px 10px',
                    fontSize: '0.74rem',
                    fontWeight: translation === 'KJV' ? 700 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  👑 KJV
                </button>
                <button
                  onClick={() => setTranslation('NIV')}
                  style={{
                    background: translation === 'NIV' ? '#6366f1' : 'transparent',
                    color: translation === 'NIV' ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '3px 10px',
                    fontSize: '0.74rem',
                    fontWeight: translation === 'NIV' ? 700 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  🕊️ NIV
                </button>
                <button
                  onClick={() => setTranslation('PARALLEL')}
                  style={{
                    background: translation === 'PARALLEL' ? '#10b981' : 'transparent',
                    color: translation === 'PARALLEL' ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '3px 10px',
                    fontSize: '0.74rem',
                    fontWeight: translation === 'PARALLEL' ? 700 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  ⚖️ KJV vs NIV Parallel
                </button>
              </div>

              <span style={{
                fontSize: '0.72rem',
                padding: '2px 8px',
                borderRadius: '6px',
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#34d399',
                border: '1px solid rgba(16, 185, 129, 0.3)'
              }}>
                100% Free & Local
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>
              Canonical New Testament · 27 Books · 260 Chapters · Dual KJV & NIV Concordance · Sovereign LLM Integration
            </div>
          </div>
        </div>

        {/* Quick Canonical Telemetry Metrics */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{
            background: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '6px 12px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            textAlign: 'center'
          }}>
            <div style={{ color: '#94a3b8', fontSize: '0.68rem', textTransform: 'uppercase' }}>Total Bible</div>
            <div style={{ fontWeight: 700, color: '#38bdf8' }}>{summary.total_bible_books} Books · {summary.total_bible_chapters.toLocaleString()} Ch</div>
          </div>

          <div style={{
            background: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '6px 12px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            textAlign: 'center'
          }}>
            <div style={{ color: '#94a3b8', fontSize: '0.68rem', textTransform: 'uppercase' }}>Verses Count</div>
            <div style={{ fontWeight: 700, color: '#818cf8' }}>~{summary.total_bible_verses.toLocaleString()} Verses</div>
          </div>

          <div style={{
            background: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '6px 12px',
            borderRadius: '8px',
            fontSize: '0.75rem',
            textAlign: 'center'
          }}>
            <div style={{ color: '#94a3b8', fontSize: '0.68rem', textTransform: 'uppercase' }}>Active NT ({translation})</div>
            <div style={{ fontWeight: 700, color: '#34d399' }}>27 Books · 260 Ch · {summary.nt_verses_count.toLocaleString()} V</div>
          </div>
        </div>
      </div>

      {/* ── SECONDARY BAR: CATEGORY FILTER & CONCORDANCE SEARCH ── */}
      <div style={{
        padding: '10px 24px',
        background: 'rgba(15, 23, 42, 0.6)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      }}>
        {/* Category Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          {['All', ...Object.keys(activeDataset.categories)].map((cat) => {
            const isCatActive = selectedCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  background: isCatActive 
                    ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(99, 102, 241, 0.25))' 
                    : 'rgba(30, 41, 59, 0.4)',
                  color: isCatActive ? '#38bdf8' : '#cbd5e1',
                  border: isCatActive ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                  padding: '6px 12px',
                  borderRadius: '20px',
                  fontSize: '0.78rem',
                  fontWeight: isCatActive ? 600 : 400,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.15s ease'
                }}
              >
                <span>{CATEGORY_ICONS[cat] || '📖'}</span>
                <span>{cat}</span>
                {cat !== 'All' && (
                  <span style={{
                    fontSize: '0.68rem',
                    opacity: 0.8,
                    background: 'rgba(255, 255, 255, 0.1)',
                    padding: '1px 6px',
                    borderRadius: '10px'
                  }}>
                    {activeDataset.categories[cat]?.length}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Realtime Search Box */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`Search ${translation === 'NIV' ? 'NIV' : 'KJV'} scripture...`}
              style={{
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: '8px',
                padding: '6px 12px 6px 32px',
                fontSize: '0.82rem',
                color: '#f8fafc',
                width: '260px',
                outline: 'none'
              }}
            />
            <span style={{ position: 'absolute', left: '10px', top: '7px', fontSize: '0.82rem', color: '#64748b' }}>
              🔍
            </span>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '6px',
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '0.75rem'
                }}
              >
                ✕
              </button>
            )}
          </div>

          <select
            value={searchScope}
            onChange={(e) => setSearchScope(e.target.value)}
            style={{
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '6px 10px',
              fontSize: '0.78rem',
              color: '#cbd5e1',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="all">Entire NT (27 Books)</option>
            <option value="current">In {selectedBook} Only</option>
          </select>
        </div>
      </div>

      {/* ── SEARCH RESULTS OVERLAY IF ACTIVE ── */}
      {searchQuery.trim().length >= 2 && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.98)',
          borderBottom: '2px solid #38bdf8',
          maxHeight: '300px',
          overflowY: 'auto',
          padding: '16px 24px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
          zIndex: 40
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8' }}>
              Concordance Matches for "{searchQuery}" ({searchResults.length} verses found{searchResults.length >= 100 ? '+' : ''})
            </div>
            <button
              onClick={() => setSearchQuery('')}
              style={{
                background: 'rgba(255,255,255,0.08)',
                border: 'none',
                color: '#cbd5e1',
                padding: '4px 10px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem'
              }}
            >
              Close Search
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {searchResults.length === 0 ? (
              <div style={{ color: '#94a3b8', fontSize: '0.85rem', fontStyle: 'italic' }}>
                No verses found matching "{searchQuery}". Try another keyword or synonym.
              </div>
            ) : (
              searchResults.map((res, idx) => (
                <div
                  key={`${res.book}-${res.chapter}-${res.verse}-${idx}`}
                  onClick={() => {
                    setSelectedBook(res.book);
                    setSelectedChapter(res.chapter);
                    setSearchQuery('');
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '6px',
                    background: 'rgba(30, 41, 59, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(56, 189, 248, 0.15)';
                    e.currentTarget.style.borderColor = '#38bdf8';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 700, color: '#38bdf8', fontSize: '0.82rem' }}>
                      {res.book} {res.chapter}:{res.verse}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Click to jump to chapter</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#e2e8f0', lineHeight: 1.4 }}>
                    {res.text}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── MAIN WORKSPACE: BOOK LIST + SCRIPTURE READER ── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Books Drawer */}
        <div style={{
          width: '260px',
          minWidth: '240px',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(15, 23, 42, 0.5)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{
            padding: '12px 16px',
            fontSize: '0.72rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: '#64748b',
            borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
          }}>
            {selectedCategory === 'All' ? 'Canonical Books (27)' : `${selectedCategory} (${visibleBooks.length})`}
          </div>

          <div style={{ padding: '8px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {visibleBooks.map((bName) => {
              const bInfo = activeDataset.books[bName];
              const isSelected = selectedBook === bName;
              return (
                <button
                  key={bName}
                  onClick={() => {
                    setSelectedBook(bName);
                    setSelectedChapter(1);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: isSelected ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid transparent',
                    background: isSelected 
                      ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.18), rgba(99, 102, 241, 0.18))' 
                      : 'transparent',
                    color: isSelected ? '#38bdf8' : '#cbd5e1',
                    fontWeight: isSelected ? 600 : 400,
                    fontSize: '0.84rem',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                      e.currentTarget.style.color = '#f8fafc';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#cbd5e1';
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.85rem' }}>📖</span>
                    <span>{bName}</span>
                  </div>
                  <span style={{
                    fontSize: '0.7rem',
                    color: isSelected ? '#38bdf8' : '#64748b',
                    background: isSelected ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    padding: '2px 6px',
                    borderRadius: '4px'
                  }}>
                    {bInfo?.chapters_count} ch
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Scripture Reading & Chapter Center */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden'
        }}>
          {/* Chapter Bar & Tooling Header */}
          <div style={{
            padding: '12px 24px',
            background: 'rgba(15, 23, 42, 0.7)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px'
          }}>
            {/* Book Title & Chapter Select */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc' }}>
                  {selectedBook} {selectedChapter}
                </h2>
                <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                  {translation === 'PARALLEL' ? 'KJV & NIV Parallel View' : `${translation} Translation`} · {currentChapterVerses.length} verses
                </div>
              </div>

              {/* Prev / Next chapter quick triggers */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <button
                  onClick={prevChapter}
                  title="Previous Chapter"
                  style={{
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#cbd5e1',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    cursor: 'pointer',
                    fontSize: '0.75rem'
                  }}
                >
                  ◀ Prev
                </button>
                <button
                  onClick={nextChapter}
                  title="Next Chapter"
                  style={{
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#cbd5e1',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    cursor: 'pointer',
                    fontSize: '0.75rem'
                  }}
                >
                  Next ▶
                </button>
              </div>
            </div>

            {/* Typography Controls & Action Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              {/* Font Size slider */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '4px 10px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>A-</span>
                <input
                  type="range"
                  min="14"
                  max="28"
                  value={fontSize}
                  onChange={(e) => setFontSize(parseInt(e.target.value, 10))}
                  style={{ width: '80px', cursor: 'pointer' }}
                />
                <span style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>A+</span>
                <span style={{ fontSize: '0.72rem', color: '#38bdf8', minWidth: '32px' }}>{fontSize}px</span>
              </div>

              {/* Font Serif / Sans Toggle */}
              <button
                onClick={() => setFontFamily(fontFamily === 'serif' ? 'sans' : 'serif')}
                style={{
                  background: 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#cbd5e1',
                  borderRadius: '8px',
                  padding: '5px 10px',
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
              >
                {fontFamily === 'serif' ? 'Serif' : 'Sans'}
              </button>

              {/* Copy Chapter */}
              <button
                onClick={copyChapterText}
                style={{
                  background: copiedVerse === 'all' ? '#10b981' : 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#ffffff',
                  borderRadius: '8px',
                  padding: '5px 12px',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <span>{copiedVerse === 'all' ? '✓ Copied!' : '📋 Copy Chapter'}</span>
              </button>

              {/* 1-Click Send to Stehouwer LLM / BS-CHAT */}
              <button
                onClick={sendToBsChat}
                style={{
                  background: 'linear-gradient(135deg, #0284c7, #4f46e5)',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  color: '#ffffff',
                  borderRadius: '8px',
                  padding: '6px 14px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 2px 10px rgba(56, 189, 248, 0.25)',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-1px)';
                  e.currentTarget.style.boxShadow = '0 4px 14px rgba(56, 189, 248, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 10px rgba(56, 189, 248, 0.25)';
                }}
              >
                <span>⚡ Study in BS-CHAT</span>
              </button>
            </div>
          </div>

          {/* Chapters Selector Grid / Pills */}
          <div style={{
            padding: '8px 24px',
            background: 'rgba(15, 23, 42, 0.4)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            overflowX: 'auto',
            whiteSpace: 'nowrap'
          }}>
            <span style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600, marginRight: '4px' }}>
              CHAPTER:
            </span>
            {Array.from({ length: totalChapters }, (_, i) => i + 1).map((chNum) => {
              const isActive = selectedChapter === chNum;
              return (
                <button
                  key={chNum}
                  onClick={() => setSelectedChapter(chNum)}
                  style={{
                    minWidth: '28px',
                    height: '28px',
                    padding: '0 6px',
                    borderRadius: '6px',
                    border: isActive ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.05)',
                    background: isActive 
                      ? 'linear-gradient(135deg, #0284c7, #6366f1)' 
                      : 'rgba(30, 41, 59, 0.6)',
                    color: isActive ? '#ffffff' : '#cbd5e1',
                    fontSize: '0.75rem',
                    fontWeight: isActive ? 700 : 400,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {chNum}
                </button>
              );
            })}
          </div>

          {/* AI Analysis feedback alert */}
          {aiAnalysisStatus && (
            <div style={{
              padding: '8px 24px',
              background: 'rgba(16, 185, 129, 0.2)',
              borderBottom: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#34d399',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <span>✓</span>
              <span>{aiAnalysisStatus}</span>
            </div>
          )}

          {/* Reading Canvas (Scrollable Text) */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '32px 48px',
            display: 'flex',
            justifyContent: 'center'
          }}>
            <div style={{
              maxWidth: translation === 'PARALLEL' ? '1200px' : '840px',
              width: '100%',
              lineHeight: 1.8,
              fontSize: `${fontSize}px`,
              fontFamily: fontFamily === 'serif' ? 'Georgia, "Times New Roman", serif' : 'Inter, system-ui, sans-serif'
            }}>
              {/* Chapter Title Badge */}
              <div style={{
                textAlign: 'center',
                marginBottom: '32px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                paddingBottom: '20px'
              }}>
                <div style={{
                  fontSize: '0.8rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: translation === 'NIV' ? '#818cf8' : translation === 'PARALLEL' ? '#34d399' : '#38bdf8',
                  fontFamily: 'Inter, sans-serif',
                  fontWeight: 600,
                  marginBottom: '6px'
                }}>
                  {translation === 'PARALLEL' ? 'Parallel Comparison (KJV & NIV)' : `${translation} Translation`}
                </div>
                <h1 style={{
                  margin: 0,
                  fontSize: `${fontSize * 1.6}px`,
                  fontWeight: 700,
                  color: '#f8fafc',
                  letterSpacing: '-0.02em'
                }}>
                  The Book of {selectedBook}
                </h1>
                <div style={{
                  fontSize: `${fontSize * 0.9}px`,
                  color: '#94a3b8',
                  marginTop: '6px',
                  fontStyle: 'italic'
                }}>
                  Chapter {selectedChapter}
                </div>
              </div>

              {/* ── PARALLEL VIEW MODE ── */}
              {translation === 'PARALLEL' && parallelData ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '24px',
                    padding: '8px 16px',
                    borderBottom: '2px solid rgba(255, 255, 255, 0.1)',
                    fontFamily: 'Inter, sans-serif',
                    fontWeight: 700,
                    fontSize: '0.85rem'
                  }}>
                    <div style={{ color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>👑</span> King James Version (KJV)
                    </div>
                    <div style={{ color: '#818cf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>🕊️</span> New International Version (NIV)
                    </div>
                  </div>

                  {parallelData.map((row) => {
                    const isCopied = copiedVerse === row.num;
                    return (
                      <div
                        key={row.num}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr',
                          gap: '24px',
                          padding: '12px 16px',
                          borderRadius: '8px',
                          background: 'rgba(30, 41, 59, 0.3)',
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                          position: 'relative'
                        }}
                      >
                        {/* KJV column */}
                        <div>
                          <span style={{
                            fontWeight: 700,
                            color: '#38bdf8',
                            marginRight: '8px',
                            fontSize: `${fontSize * 0.85}px`,
                            fontFamily: 'Inter, sans-serif'
                          }}>
                            {row.num}
                          </span>
                          <span style={{ color: '#f1f5f9' }}>{row.kjv}</span>
                        </div>

                        {/* NIV column */}
                        <div>
                          <span style={{
                            fontWeight: 700,
                            color: '#818cf8',
                            marginRight: '8px',
                            fontSize: `${fontSize * 0.85}px`,
                            fontFamily: 'Inter, sans-serif'
                          }}>
                            {row.num}
                          </span>
                          <span style={{ color: '#f1f5f9' }}>{row.niv}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* ── SINGLE TRANSLATION VIEW MODE ── */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {currentChapterVerses.map((verseText, vIdx) => {
                    const verseNum = vIdx + 1;
                    const isCopied = copiedVerse === verseNum;
                    return (
                      <div
                        key={verseNum}
                        style={{
                          position: 'relative',
                          padding: '6px 12px',
                          borderRadius: '8px',
                          transition: 'background 0.15s ease'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'transparent';
                        }}
                      >
                        {/* Verse number */}
                        <span style={{
                          display: 'inline-block',
                          fontWeight: 700,
                          color: translation === 'NIV' ? '#818cf8' : '#38bdf8',
                          marginRight: '10px',
                          fontSize: `${fontSize * 0.85}px`,
                          fontFamily: 'Inter, sans-serif',
                          verticalAlign: 'baseline',
                          userSelect: 'none'
                        }}>
                          {verseNum}
                        </span>

                        {/* Verse text */}
                        <span style={{ color: '#f1f5f9' }}>
                          {verseText}
                        </span>

                        {/* Hover action: Copy verse */}
                        <button
                          onClick={() => copyVerseText(verseNum, verseText)}
                          title="Copy this verse"
                          style={{
                            marginLeft: '10px',
                            background: isCopied ? '#10b981' : 'rgba(255, 255, 255, 0.06)',
                            border: 'none',
                            color: isCopied ? '#ffffff' : '#94a3b8',
                            borderRadius: '4px',
                            padding: '2px 6px',
                            fontSize: '0.68rem',
                            cursor: 'pointer',
                            opacity: isCopied ? 1 : 0.6,
                            fontFamily: 'Inter, sans-serif',
                            verticalAlign: 'middle',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          {isCopied ? '✓' : 'Copy'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Bottom chapter navigation triggers */}
              <div style={{
                marginTop: '48px',
                paddingTop: '24px',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontFamily: 'Inter, sans-serif'
              }}>
                <button
                  onClick={prevChapter}
                  style={{
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#f8fafc',
                    padding: '8px 18px',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '0.82rem',
                    fontWeight: 500
                  }}
                >
                  ◀ Previous Chapter
                </button>

                <button
                  onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    fontSize: '0.78rem'
                  }}
                >
                  ↑ Top of Chapter
                </button>

                <button
                  onClick={nextChapter}
                  style={{
                    background: 'rgba(30, 41, 59, 0.8)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#f8fafc',
                    padding: '8px 18px',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontSize: '0.82rem',
                    fontWeight: 500
                  }}
                >
                  Next Chapter ▶
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
