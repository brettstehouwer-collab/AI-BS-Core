import React, { useMemo } from 'react';

const AnalyticsOverlay = ({ ast, onClose }) => {
  // Compute analytics from AST
  const analytics = useMemo(() => {
    let dialogueCount = {};
    let sceneCount = 0;
    let actionBlocks = 0;

    (ast || []).forEach(block => {
      if (block.type === 'Character') {
        const name = block.text.trim();
        dialogueCount[name] = (dialogueCount[name] || 0) + 1;
      } else if (block.type === 'Scene Heading') {
        sceneCount++;
      } else if (block.type === 'Action') {
        actionBlocks++;
      }
    });

    const topCharacters = Object.entries(dialogueCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10);

    return { sceneCount, actionBlocks, topCharacters };
  }, [ast]);

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#1f2937', padding: '24px', borderRadius: '8px', minWidth: '400px', maxWidth: '600px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)', color: '#fff' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, color: '#facc15' }}>📈 Script Analytics & Pacing</h2>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '1.2rem' }}>✖</button>
        </div>
        
        <div style={{ display: 'flex', gap: '24px', marginBottom: '24px' }}>
          <div style={{ flex: 1, background: '#111827', padding: '16px', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', color: '#38bdf8', fontWeight: 'bold' }}>{analytics.sceneCount}</div>
            <div style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Total Scenes</div>
          </div>
          <div style={{ flex: 1, background: '#111827', padding: '16px', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', color: '#4ade80', fontWeight: 'bold' }}>{analytics.actionBlocks}</div>
            <div style={{ color: '#9ca3af', fontSize: '0.85rem' }}>Action Blocks</div>
          </div>
        </div>

        <h3 style={{ borderBottom: '1px solid #374151', paddingBottom: '8px', color: '#d1d5db' }}>Top Characters (Dialogue Count)</h3>
        <div style={{ maxHeight: '200px', overflowY: 'auto', paddingRight: '8px' }}>
          {analytics.topCharacters.length === 0 ? (
            <div style={{ color: '#6b7280', fontStyle: 'italic', padding: '8px 0' }}>No characters found.</div>
          ) : (
            analytics.topCharacters.map(([name, count], i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #374151' }}>
                <span style={{ fontWeight: 'bold' }}>{name}</span>
                <span style={{ color: '#facc15' }}>{count}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsOverlay;
