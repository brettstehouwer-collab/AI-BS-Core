import React from 'react';
import './ScreenwritingTab.css';

export default function CoverageReportModal({ coverageData, onClose }) {
  if (!coverageData) return null;

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#111827', width: '900px', maxHeight: '80vh', borderRadius: '12px', display: 'flex', flexDirection: 'column', overflow: 'hidden', border: '1px solid #374151', boxShadow: '0 10px 30px rgba(0,0,0,0.8)' }}>
        
        {/* Header */}
        <div style={{ padding: '24px', borderBottom: '1px solid #374151', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#1f2937' }}>
          <div>
            <h2 style={{ color: '#fff', margin: 0, fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              📊 AI Script Coverage & Budget Report
            </h2>
            <p style={{ color: '#9ca3af', margin: '4px 0 0 0', fontSize: '0.9rem' }}>Projected production requirements</p>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#9ca3af', fontSize: '1.5rem', cursor: 'pointer' }}>✕</button>
        </div>

        {/* Scrollable Content Area */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          
          {/* Top Level Summary (Logline, Genre, Budget) */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginBottom: '32px' }}>
            <div style={{ background: '#1f2937', padding: '16px', borderRadius: '8px', border: '1px solid #374151' }}>
              <h4 style={{ color: '#38bdf8', marginTop: 0, marginBottom: '8px', textTransform: 'uppercase', fontSize: '0.8rem' }}>Logline</h4>
              <p style={{ color: '#e5e7eb', margin: 0, fontSize: '1.1rem', fontStyle: 'italic', lineHeight: 1.5 }}>
                "{coverageData.logline || 'Not provided'}"
              </p>
            </div>
            <div style={{ background: '#1f2937', padding: '16px', borderRadius: '8px', border: '1px solid #374151' }}>
               <h4 style={{ color: '#facc15', marginTop: 0, marginBottom: '12px', textTransform: 'uppercase', fontSize: '0.8rem' }}>Production Target</h4>
               <div style={{ marginBottom: '8px' }}>
                 <span style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Genre:</span> <span style={{ color: '#fff', fontWeight: 'bold' }}>{coverageData.genre || 'N/A'}</span>
               </div>
               <div style={{ marginBottom: '8px' }}>
                 <span style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Scale:</span> <span style={{ color: '#fff', fontWeight: 'bold' }}>{coverageData.budget_tier || 'N/A'}</span>
               </div>
               <div>
                 <span style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Est. Budget:</span> <span style={{ color: '#10b981', fontWeight: 'bold', fontSize: '1.1rem' }}>{coverageData.budget_estimate_usd || 'N/A'}</span>
               </div>
            </div>
          </div>

          {/* Breakdown Columns */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px' }}>
            
            {/* Characters */}
            <div style={{ background: '#1f2937', padding: '16px', borderRadius: '8px', border: '1px solid #374151' }}>
              <h4 style={{ color: '#a78bfa', marginTop: 0, marginBottom: '16px', textTransform: 'uppercase', fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between' }}>
                <span>👥 Characters</span>
                <span style={{ background: '#4c1d95', padding: '2px 8px', borderRadius: '12px' }}>{coverageData.characters?.length || 0}</span>
              </h4>
              <ul style={{ color: '#e5e7eb', margin: 0, paddingLeft: '20px', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {coverageData.characters?.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
              {(!coverageData.characters || coverageData.characters.length === 0) && <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>None detected</div>}
            </div>

            {/* Locations */}
            <div style={{ background: '#1f2937', padding: '16px', borderRadius: '8px', border: '1px solid #374151' }}>
              <h4 style={{ color: '#4ade80', marginTop: 0, marginBottom: '16px', textTransform: 'uppercase', fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between' }}>
                <span>📍 Locations</span>
                <span style={{ background: '#064e3b', padding: '2px 8px', borderRadius: '12px' }}>{coverageData.locations?.length || 0}</span>
              </h4>
              <ul style={{ color: '#e5e7eb', margin: 0, paddingLeft: '20px', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {coverageData.locations?.map((l, i) => <li key={i}>{l}</li>)}
              </ul>
              {(!coverageData.locations || coverageData.locations.length === 0) && <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>None detected</div>}
            </div>

            {/* Props */}
            <div style={{ background: '#1f2937', padding: '16px', borderRadius: '8px', border: '1px solid #374151' }}>
              <h4 style={{ color: '#fb923c', marginTop: 0, marginBottom: '16px', textTransform: 'uppercase', fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between' }}>
                <span>🎒 Props</span>
                <span style={{ background: '#7c2d12', padding: '2px 8px', borderRadius: '12px' }}>{coverageData.props?.length || 0}</span>
              </h4>
              <ul style={{ color: '#e5e7eb', margin: 0, paddingLeft: '20px', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {coverageData.props?.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
              {(!coverageData.props || coverageData.props.length === 0) && <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>None detected</div>}
            </div>

          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #374151', display: 'flex', justifyContent: 'flex-end', background: '#1f2937' }}>
           <button onClick={() => window.print()} style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '8px 24px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
             🖨️ Print Coverage
           </button>
        </div>

      </div>
    </div>
  );
}
