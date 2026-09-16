import React, { useState, useEffect } from 'react';
import './ProductionBreakdownModal.css';

const formatEighths = (eighths) => {
  if (eighths < 8) {
    return `${eighths}/8`;
  }
  const pages = Math.floor(eighths / 8);
  const remainder = eighths % 8;
  if (remainder === 0) return `${pages} pgs`;
  return `${pages} ${remainder}/8 pgs`;
};

const getStripColor = (isExt, isNight) => {
  if (isExt) {
    return isNight ? '#22c55e' : '#ffffff'; // Green : White
  } else {
    return isNight ? '#3b82f6' : '#eab308'; // Blue : Yellow
  }
};

const getStripTextColor = (isExt, isNight) => {
  if (isExt && !isNight) return '#000000';
  if (!isExt && !isNight) return '#000000';
  return '#ffffff';
};

const ProductionBreakdownModal = ({ scriptText, onClose }) => {
  const [activeTab, setActiveTab] = useState('schedule');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const [params, setParams] = useState({
    pages_per_day_target: 5.0,
    union_status: 'SAG_ULB',
    fringe_rate: 0.35,
    crew_scale: 'standard_indie',
    geographic_tier: 'incentive',
    tax_incentive_pct: 0.25,
    contingency_percentage: 0.10,
    completion_bond_required: false
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${window.env?.BACKEND_URL || 'http://127.0.0.1:8000'}/api/screenwriting/production_breakdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          script_text: scriptText,
          parameters: params
        })
      });
      const result = await response.json();
      if (result.status === 'success') {
        setData(result.breakdown);
      } else {
        console.error('Error fetching breakdown:', result.message);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (scriptText) fetchData();
  }, [scriptText, params]);

  const handleDownloadCSV = () => {
    if (!data?.csv_data) return;
    const blob = new Blob([data.csv_data], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'budget_export.csv';
    a.click();
  };

  return (
    <div className="production-breakdown-overlay">
      <div className="production-breakdown-modal">
        <div className="modal-header">
          <h2>🎬 Production Breakdown & Budget</h2>
          <button className="close-btn" onClick={onClose}>✖</button>
        </div>

        <div className="modal-content-grid">
          {/* LEFT: Parameters Form */}
          <div className="parameters-sidebar">
            <h3>Advanced Parameters</h3>
            
            <div className="param-group">
              <label>Pages Per Day Target</label>
              <input type="number" step="0.5" value={params.pages_per_day_target} onChange={e => setParams({...params, pages_per_day_target: parseFloat(e.target.value)})} />
            </div>

            <div className="param-group">
              <label>Union Status</label>
              <select value={params.union_status} onChange={e => setParams({...params, union_status: e.target.value})}>
                <option value="SAG_ULB">SAG-AFTRA ULB</option>
                <option value="SAG_MOD">SAG-AFTRA Modified</option>
                <option value="NON_UNION">Non-Union</option>
              </select>
            </div>

            <div className="param-group">
              <label>Fringe Rate (%)</label>
              <input type="number" step="0.05" value={params.fringe_rate} onChange={e => setParams({...params, fringe_rate: parseFloat(e.target.value)})} />
            </div>

            <div className="param-group">
              <label>Crew Scale</label>
              <select value={params.crew_scale} onChange={e => setParams({...params, crew_scale: e.target.value})}>
                <option value="micro_indie">Micro Indie</option>
                <option value="standard_indie">Standard Indie</option>
                <option value="studio">Studio</option>
              </select>
            </div>

            <div className="param-group">
              <label>Tax Incentive Rebate (%)</label>
              <input type="number" step="0.05" value={params.tax_incentive_pct} onChange={e => setParams({...params, tax_incentive_pct: parseFloat(e.target.value)})} />
            </div>

            <div className="param-group">
              <label>Contingency (%)</label>
              <input type="number" step="0.05" value={params.contingency_percentage} onChange={e => setParams({...params, contingency_percentage: parseFloat(e.target.value)})} />
            </div>

            <div className="param-group checkbox">
              <input type="checkbox" checked={params.completion_bond_required} onChange={e => setParams({...params, completion_bond_required: e.target.checked})} />
              <label>Completion Bond Required</label>
            </div>
            
            <button className="csv-export-btn" onClick={handleDownloadCSV}>📥 Export Movie Magic CSV</button>
          </div>

          {/* RIGHT: Data Visualization */}
          <div className="visualization-area">
            <div className="tabs-header">
              <button className={activeTab === 'schedule' ? 'active' : ''} onClick={() => setActiveTab('schedule')}>Shooting Schedule</button>
              <button className={activeTab === 'breakdown' ? 'active' : ''} onClick={() => setActiveTab('breakdown')}>Script Breakdown</button>
              <button className={activeTab === 'dood' ? 'active' : ''} onClick={() => setActiveTab('dood')}>Cast DOOD Matrix</button>
              <button className={activeTab === 'budget' ? 'active' : ''} onClick={() => setActiveTab('budget')}>Top Sheet Budget</button>
            </div>

            <div className="tab-content">
              {loading && <div className="loading-state">Computing Algorithmic Breakdown...</div>}
              {!loading && data && (
                <>
                  {/* SHOOTING SCHEDULE TAB */}
                  {activeTab === 'schedule' && (
                    <div className="stripboard-container">
                      {data.shoot_days.map((day, idx) => (
                        <div key={idx} className="shoot-day-group">
                          <div className="day-banner">Day {idx + 1}</div>
                          {day.map(sc => (
                            <div key={sc.id} className="scene-strip" style={{ 
                              backgroundColor: getStripColor(sc.is_ext, sc.is_night),
                              color: getStripTextColor(sc.is_ext, sc.is_night)
                            }}>
                              <span className="strip-id">{sc.id}</span>
                              <span className="strip-heading">{sc.heading} {sc.special_requirements ? '⚠️ (VFX/STUNT)' : ''}</span>
                              <span className="strip-eighths">{formatEighths(sc.eighths)}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* SCRIPT BREAKDOWN TAB */}
                  {activeTab === 'breakdown' && (
                    <div className="breakdown-table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Scene</th>
                            <th>INT/EXT</th>
                            <th>D/N</th>
                            <th>Location</th>
                            <th>Eighths</th>
                            <th>Characters</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.scenes.map(sc => (
                            <tr key={sc.id}>
                              <td>{sc.id}</td>
                              <td>{sc.is_ext ? 'EXT' : 'INT'}</td>
                              <td>{sc.is_night ? 'NIGHT' : 'DAY'}</td>
                              <td>{sc.location}</td>
                              <td>{formatEighths(sc.eighths)}</td>
                              <td>{sc.characters.join(', ')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* CAST DOOD TAB */}
                  {activeTab === 'dood' && (
                    <div className="dood-table-container">
                      <table className="data-table dood-table">
                        <thead>
                          <tr>
                            <th>Character</th>
                            <th>Tier</th>
                            {Array.from({length: data.total_shoot_days}).map((_, i) => (
                              <th key={i}>D{i+1}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(data.dood).map(([char, days]) => (
                            <tr key={char}>
                              <td>{char}</td>
                              <td><span className={`tier-badge ${data.cast_tiering[char].replace(' ', '').toLowerCase()}`}>{data.cast_tiering[char]}</span></td>
                              {days.map((status, i) => (
                                <td key={i} className={`dood-status ${status}`}>{status}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* TOP SHEET BUDGET TAB */}
                  {activeTab === 'budget' && (
                    <div className="budget-container">
                      <table className="top-sheet-table">
                        <tbody>
                          <tr>
                            <td>1000</td>
                            <td>Above The Line</td>
                            <td className="amount">${data.top_sheet.above_the_line.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>2000</td>
                            <td>Production</td>
                            <td className="amount">${data.top_sheet.production.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>3000</td>
                            <td>Post Production</td>
                            <td className="amount">${data.top_sheet.post_production.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>4000</td>
                            <td>Contingency ({params.contingency_percentage * 100}%)</td>
                            <td className="amount">${data.top_sheet.contingency.toLocaleString()}</td>
                          </tr>
                          <tr className="total-row gross">
                            <td></td>
                            <td>GROSS BUDGET</td>
                            <td className="amount">${data.top_sheet.gross_budget.toLocaleString()}</td>
                          </tr>
                          <tr className="total-row net">
                            <td></td>
                            <td>NET BUDGET (Post-Rebate)</td>
                            <td className="amount">${data.top_sheet.net_budget.toLocaleString()}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductionBreakdownModal;
