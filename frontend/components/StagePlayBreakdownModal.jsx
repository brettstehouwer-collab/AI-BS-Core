import React, { useState, useEffect } from 'react';
import './ProductionBreakdownModal.css';
import './StagePlayBreakdownModal.css';

const StagePlayBreakdownModal = ({ scriptText, onClose }) => {
  const [activeTab, setActiveTab] = useState('capitalization');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const [params, setParams] = useState({
    running_time_minutes: 120,
    scene_count: 0, // 0 = auto-detect
    set_changes: 2,
    special_effects_level: 'minimal',
    venue_type: 'black_box',
    rehearsal_weeks: 4,
    performance_run_length: 16,
    load_in_days: 3,
    equity_status: 'Non_Equity',
    cast_size: 0, // 0 = auto-detect
    understudy_count: 0,
    crew_size: 3,
    creative_team_flat_fees: {
      director: 5000,
      set_designer: 3000,
      costume_designer: 2000,
      lighting_designer: 2000,
      sound_designer: 1500
    },
    royalty_structure: 'percentage_of_gross_box_office',
    script_licensing_fees: 150.0,
    insurance_and_bonding: 1500.0,
    estimated_weekly_gross: 10000.0
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${window.env?.BACKEND_URL || 'http://127.0.0.1:8000'}/api/screenwriting/stage_play_breakdown`, {
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
    a.download = 'theatrical_budget_export.csv';
    a.click();
  };

  return (
    <div className="production-breakdown-overlay">
      <div className="stage-play-breakdown-modal production-breakdown-modal">
        <div className="modal-header">
          <h2>🎭 Stage Play Budgeting & Breakdown</h2>
          <button className="close-btn" onClick={onClose}>✖</button>
        </div>

        <div className="modal-content-grid">
          {/* LEFT: Parameters Form */}
          <div className="parameters-sidebar">
            <h3>Theatrical Parameters</h3>
            
            <div className="param-group">
              <label>Rehearsal Weeks</label>
              <input type="number" min="1" max="10" value={params.rehearsal_weeks} onChange={e => setParams({...params, rehearsal_weeks: parseInt(e.target.value)})} />
            </div>

            <div className="param-group">
              <label>Performance Run (Total Shows)</label>
              <input type="number" min="1" value={params.performance_run_length} onChange={e => setParams({...params, performance_run_length: parseInt(e.target.value)})} />
            </div>

            <div className="param-group">
              <label>Union/Equity Status</label>
              <select value={params.equity_status} onChange={e => setParams({...params, equity_status: e.target.value})}>
                <option value="Non_Equity">Non-Equity</option>
                <option value="AEA_Showcase">AEA Showcase / Waiver</option>
                <option value="SPT">Small Professional Theatre (SPT)</option>
              </select>
            </div>

            <div className="param-group">
              <label>Venue Type</label>
              <select value={params.venue_type} onChange={e => setParams({...params, venue_type: e.target.value})}>
                <option value="black_box">Black Box (99-seat)</option>
                <option value="regional_proscenium">Regional Proscenium</option>
                <option value="commercial_off_broadway">Commercial Off-Broadway</option>
              </select>
            </div>
            
            <div className="param-group">
              <label>Cast Size (0 = Auto-Detect from Script)</label>
              <input type="number" min="0" value={params.cast_size} onChange={e => setParams({...params, cast_size: parseInt(e.target.value)})} />
            </div>
            
            <div className="param-group">
              <label>Understudy/Swing Count</label>
              <input type="number" min="0" value={params.understudy_count} onChange={e => setParams({...params, understudy_count: parseInt(e.target.value)})} />
            </div>

            <div className="param-group">
              <label>Running Crew Size</label>
              <input type="number" min="1" value={params.crew_size} onChange={e => setParams({...params, crew_size: parseInt(e.target.value)})} />
            </div>

            <div className="param-group">
              <label>Estimated Weekly Gross Revenue ($)</label>
              <input type="number" step="500" value={params.estimated_weekly_gross} onChange={e => setParams({...params, estimated_weekly_gross: parseFloat(e.target.value)})} />
            </div>

            <button className="csv-export-btn" onClick={handleDownloadCSV}>📥 Export Accounting CSV</button>
          </div>

          {/* RIGHT: Data Visualization */}
          <div className="visualization-area">
            <div className="tabs-header">
              <button className={activeTab === 'capitalization' ? 'active' : ''} onClick={() => setActiveTab('capitalization')}>Capitalization Budget</button>
              <button className={activeTab === 'weekly' ? 'active' : ''} onClick={() => setActiveTab('weekly')}>Weekly Operating</button>
              <button className={activeTab === 'recoupment' ? 'active' : ''} onClick={() => setActiveTab('recoupment')}>Recoupment Projection</button>
            </div>

            <div className="tab-content">
              {loading && <div className="loading-state">Computing Theatrical Breakdown...</div>}
              {!loading && data && (
                <>
                  {/* OVERVIEW / CAPITALIZATION TAB */}
                  {activeTab === 'capitalization' && (
                    <div className="budget-container">
                      <div className="metrics-row" style={{ display: 'flex', gap: '16px', marginBottom: '24px' }}>
                        <div className="metric-card" style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', flex: 1 }}>
                          <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Auto-Detected Cast Size</div>
                          <div style={{ fontSize: '1.5rem', color: '#38bdf8', fontWeight: 'bold' }}>{data.detected_cast_size}</div>
                        </div>
                        <div className="metric-card" style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', flex: 1 }}>
                          <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Detected Scenes</div>
                          <div style={{ fontSize: '1.5rem', color: '#a78bfa', fontWeight: 'bold' }}>{data.detected_scene_count}</div>
                        </div>
                      </div>

                      <table className="top-sheet-table">
                        <tbody>
                          <tr>
                            <td>1000</td>
                            <td>Creative Fees (Director, Designers)</td>
                            <td className="amount">${data.capitalization.creative_fees.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>1100</td>
                            <td>Rehearsal Labor (Cast + Stage Management)</td>
                            <td className="amount">${data.capitalization.rehearsal_labor.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>1200</td>
                            <td>Physical Production (Sets, Costumes, Props)</td>
                            <td className="amount">${data.capitalization.physical_production.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>1300</td>
                            <td>Tech & Load-in Labor</td>
                            <td className="amount">${data.capitalization.load_in_labor.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>1400</td>
                            <td>Contingency (15%)</td>
                            <td className="amount">${data.capitalization.contingency.toLocaleString()}</td>
                          </tr>
                          <tr className="total-row gross">
                            <td></td>
                            <td>TOTAL CAPITALIZATION (Pre-Opening)</td>
                            <td className="amount">${data.capitalization.total.toLocaleString()}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* WEEKLY OPERATING TAB */}
                  {activeTab === 'weekly' && (
                    <div className="budget-container">
                      <table className="top-sheet-table">
                        <tbody>
                          <tr>
                            <td>2000</td>
                            <td>Running Cast & Crew Labor</td>
                            <td className="amount">${data.weekly_operating.cast_and_crew.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>2100</td>
                            <td>Venue Rent ({params.venue_type.replace('_', ' ').toUpperCase()})</td>
                            <td className="amount">${data.weekly_operating.venue_rent.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>2200</td>
                            <td>Marketing & Advertising</td>
                            <td className="amount">${data.weekly_operating.marketing.toLocaleString()}</td>
                          </tr>
                          <tr>
                            <td>2300</td>
                            <td>Royalties (8% Gross / Flat Fee)</td>
                            <td className="amount">${data.weekly_operating.royalties.toLocaleString()}</td>
                          </tr>
                          <tr className="total-row net">
                            <td></td>
                            <td>WEEKLY OPERATING EXPENSE (Breakeven Point)</td>
                            <td className="amount">${data.weekly_operating.total.toLocaleString()}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* RECOUPMENT TAB */}
                  {activeTab === 'recoupment' && (
                    <div className="recoupment-container" style={{ color: '#e5e7eb' }}>
                      <div className="recoupment-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                        <div className="rc-card" style={{ background: '#1e293b', padding: '24px', borderRadius: '8px' }}>
                          <h3 style={{ marginTop: 0, color: '#facc15' }}>Projected Run Metrics</h3>
                          <p><strong>Total Run Length:</strong> {data.run_metrics.run_weeks} weeks ({params.performance_run_length} performances)</p>
                          <p><strong>Estimated Weekly Gross:</strong> ${params.estimated_weekly_gross.toLocaleString()}</p>
                          <p><strong>Weekly Operating Cost:</strong> ${data.weekly_operating.total.toLocaleString()}</p>
                          <p><strong>Weekly Net Operating Profit:</strong> <span style={{ color: data.run_metrics.weekly_net_profit > 0 ? '#4ade80' : '#f87171' }}>${data.run_metrics.weekly_net_profit.toLocaleString()}</span></p>
                        </div>

                        <div className="rc-card" style={{ background: '#1e293b', padding: '24px', borderRadius: '8px' }}>
                          <h3 style={{ marginTop: 0, color: '#38bdf8' }}>Capital Recoupment</h3>
                          <p><strong>Total Capitalization:</strong> ${data.capitalization.total.toLocaleString()}</p>
                          <br/>
                          {data.run_metrics.weekly_net_profit > 0 ? (
                            <>
                              <h1 style={{ margin: '0 0 8px 0', fontSize: '3rem', color: '#4ade80' }}>{data.run_metrics.weeks_to_recoup}</h1>
                              <span style={{ color: '#94a3b8' }}>Weeks to fully recoup Capitalization</span>
                            </>
                          ) : (
                            <h2 style={{ color: '#f87171' }}>Cannot Recoup. Weekly Operating Costs exceed Gross Box Office.</h2>
                          )}
                        </div>
                      </div>
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

export default StagePlayBreakdownModal;
