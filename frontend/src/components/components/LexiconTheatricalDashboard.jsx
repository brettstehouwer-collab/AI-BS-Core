import React, { useState, useEffect } from 'react';

export default function LexiconTheatricalDashboard() {
  const [inputText, setInputText] = useState("We need to synergize our paradigms for optimal ROI.");
  const [enrichmentData, setEnrichmentData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [synonymLookupWord, setSynonymLookupWord] = useState("");
  const [synonymResults, setSynonymResults] = useState(null);

  const handleEnrich = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8080/lexicon/enrich', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: inputText })
      });
      const data = await res.json();
      setEnrichmentData(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleLookup = async () => {
    if (!synonymLookupWord) return;
    try {
      const res = await fetch(`http://127.0.0.1:8080/lexicon/synonyms?word=${synonymLookupWord}&limit=10`);
      const data = await res.json();
      setSynonymResults(data);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ color: '#58a6ff', marginBottom: '10px' }}>🎭 Theatrical Lexicon Engine Dashboard</h2>
      <p style={{ marginBottom: '20px', color: '#8b949e' }}>Real-time semantic expansion and Persona trigger visualization.</p>
      
      <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
        
        {/* Left Column: Input & Expansion */}
        <div style={{ flex: '1 1 500px', background: '#161b22', padding: '20px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <h3 style={{ color: '#3fb950' }}>Semantic Expansion (Live Stream Simulator)</h3>
          <textarea 
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            style={{ width: '100%', height: '100px', background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '4px', padding: '10px', marginTop: '10px', marginBottom: '10px' }}
          />
          <button 
            onClick={handleEnrich} 
            disabled={loading}
            style={{ background: '#238636', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            {loading ? 'Analyzing...' : 'Enrich & Expand'}
          </button>

          {enrichmentData && (
            <div style={{ marginTop: '20px', padding: '15px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '4px' }}>
              <h4 style={{ color: '#58a6ff' }}>Analyzed Output</h4>
              <p style={{ fontStyle: 'italic', color: '#8b949e' }}>Original: {enrichmentData.original_text}</p>
              
              <h4 style={{ marginTop: '15px', color: '#e3b341' }}>Expansion Map</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
                {Object.entries(enrichmentData.expansion_map).map(([word, expansion]) => (
                  <div key={word} style={{ border: '1px solid #444c56', padding: '10px', borderRadius: '6px', background: '#21262d' }}>
                    <strong style={{ color: '#ff7b72' }}>{word}</strong>
                    <div style={{ marginTop: '5px', fontSize: '0.85em', color: '#a5d6ff' }}>
                      Synonyms: {expansion.synonyms ? expansion.synonyms.join(', ') : 'None'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Direct Lookup & OBS Triggers */}
        <div style={{ flex: '1 1 400px', background: '#161b22', padding: '20px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <h3 style={{ color: '#d2a8ff' }}>Raw Lexicon Lookup</h3>
          <div style={{ display: 'flex', gap: '10px', marginTop: '10px', marginBottom: '10px' }}>
            <input 
              type="text" 
              value={synonymLookupWord}
              onChange={(e) => setSynonymLookupWord(e.target.value)}
              placeholder="Enter a word (e.g., synergy)"
              style={{ flex: 1, background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '4px', padding: '8px' }}
            />
            <button 
              onClick={handleLookup}
              style={{ background: '#3fb950', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}
            >
              Lookup
            </button>
          </div>

          {synonymResults && (
            <div style={{ marginTop: '20px', padding: '15px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '4px' }}>
              <h4 style={{ color: '#58a6ff' }}>Word: {synonymResults.word}</h4>
              <ul style={{ marginTop: '10px', paddingLeft: '20px', color: '#8b949e' }}>
                {synonymResults.synonyms.map((syn, idx) => (
                  <li key={idx} style={{ marginBottom: '5px' }}>{syn}</li>
                ))}
                {synonymResults.synonyms.length === 0 && <li>No synonyms found in Lexicon Vault.</li>}
              </ul>
            </div>
          )}

          <div style={{ marginTop: '30px', padding: '15px', border: '1px dashed #d2a8ff', borderRadius: '4px' }}>
            <h4 style={{ color: '#d2a8ff', marginBottom: '10px' }}>⚡ Coming in Phase 2</h4>
            <p style={{ fontSize: '0.9em', color: '#8b949e' }}>
              The expansion map data visualized here will be bound to the <strong>OBS Orchestrator</strong>. Specific semantic hits (e.g. aggressive words) will automatically trigger OBS WebSocket scene swaps and ComfyUI overlays.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
