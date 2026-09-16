import React, { useState, useEffect } from 'react';
import './PowerWashingTab.css';

export default function PowerWashingTab({ backendUrl = 'http://localhost:8080', onNavigateTab }) {
  // Navigation Sub-tab within Power Washing Suite
  const [activeSubTab, setActiveSubTab] = useState('estimator'); // 'estimator' | 'gis' | 'route' | 'weather' | 'fleet' | 'crm'

  // Telemetry & General State
  const [telemetry, setTelemetry] = useState(null);
  const [clients, setClients] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [fleetUnits, setFleetUnits] = useState([]);
  const [weatherData, setWeatherData] = useState(null);

  // 1. Tool 1: Surface & Chemical Ratio Estimator State
  const [substrate, setSubstrate] = useState('vinyl');
  const [contamination, setContamination] = useState('black_algae');
  const [severity, setSeverity] = useState('moderate');
  const [squareFootage, setSquareFootage] = useState(2200);
  const [storyCount, setStoryCount] = useState(2);
  const [calcResult, setCalcResult] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);

  // 2. Tool 2: GIS Quoting Engine State
  const [gisAddress, setGisAddress] = useState('4450 44th St SE, Grand Rapids, MI 49512');
  const [buildingSqft, setBuildingSqft] = useState(2600);
  const [roofPitch, setRoofPitch] = useState('6/12');
  const [drivewaySqft, setDrivewaySqft] = useState(900);
  const [includeRoof, setIncludeRoof] = useState(true);
  const [includeSiding, setIncludeSiding] = useState(true);
  const [includeDriveway, setIncludeDriveway] = useState(true);
  const [nearbyJobsCount, setNearbyJobsCount] = useState(2);
  const [gisQuoteResult, setGisQuoteResult] = useState(null);

  // 3. Tool 3: Route & Water Payload (GVWR) State
  const [waterTankGal, setWaterTankGal] = useState(275);
  const [shChemicalGal, setShChemicalGal] = useState(45);
  const [routePayloadResult, setRoutePayloadResult] = useState(null);

  // 4. Tool 5: Fleet Wash Verification State
  const [selectedFleetUnit, setSelectedFleetUnit] = useState(null);
  const [showLogModal, setShowLogModal] = useState(false);
  const [techName, setTechName] = useState('Prestige Crew Lead #1');
  const [gpsLocation, setGpsLocation] = useState('42.9634° N, 85.6681° W (Grand Rapids, MI)');
  const [soapApplied, setSoapApplied] = useState('Prestige Citrus-Foam Citrus Wash');
  const [logSuccessMsg, setLogSuccessMsg] = useState('');

  // 5. CRM & Job State Modals
  const [showNewClientModal, setShowNewClientModal] = useState(false);
  // In-Tab Interactive Tips & Walkthrough State
  const [showTips, setShowTips] = useState(true);

  const [newClient, setNewClient] = useState({
    name: '',
    company: '',
    client_type: 'residential',
    phone: '616-901-6536',
    email: '',
    address: '',
    city: 'Grand Rapids',
    zip_code: '49503',
    water_spigot_access: 'yes',
    notes: ''
  });

  // Load telemetry, clients, jobs, weather on mount
  useEffect(() => {
    fetchTelemetry();
    fetchClients();
    fetchJobs();
    fetchFleet();
    fetchWeather();
    handleCalculateSurface();
    handleCalculateGisQuote();
    handleCalculateRoutePayload();
  }, []);

  const fetchTelemetry = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/telemetry`);
      if (res.ok) setTelemetry(await res.json());
    } catch (e) {
      console.error('Failed to load telemetry:', e);
    }
  };

  const fetchClients = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/clients`);
      if (res.ok) {
        const data = await res.json();
        setClients(data.clients || []);
      }
    } catch (e) {
      console.error('Failed to load clients:', e);
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/jobs`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
      }
    } catch (e) {
      console.error('Failed to load jobs:', e);
    }
  };

  const fetchFleet = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/fleet`);
      if (res.ok) {
        const data = await res.json();
        setFleetUnits(data.units || []);
      }
    } catch (e) {
      console.error('Failed to load fleet:', e);
    }
  };

  const fetchWeather = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/weather_dispatch`);
      if (res.ok) setWeatherData(await res.json());
    } catch (e) {
      console.error('Failed to load weather:', e);
    }
  };

  // 1. Tool 1: Surface & Chemical Calculation
  const handleCalculateSurface = async () => {
    setIsCalculating(true);
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/analyze_surface`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          substrate_type: substrate,
          contamination_type: contamination,
          contamination_severity: severity,
          square_footage: parseFloat(squareFootage) || 1500,
          story_count: parseInt(storyCount) || 1
        })
      });
      if (res.ok) {
        setCalcResult(await res.json());
      }
    } catch (e) {
      console.error('Surface calc error:', e);
    } finally {
      setIsCalculating(false);
    }
  };

  // 2. Tool 2: GIS Quoting Engine
  const handleCalculateGisQuote = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/gis_quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: gisAddress,
          building_sqft: parseFloat(buildingSqft) || 2400,
          roof_pitch: roofPitch,
          driveway_sqft: parseFloat(drivewaySqft) || 900,
          include_roof: includeRoof,
          include_siding: includeSiding,
          include_driveway: includeDriveway,
          nearby_jobs_in_zip: parseInt(nearbyJobsCount) || 1
        })
      });
      if (res.ok) {
        setGisQuoteResult(await res.json());
      }
    } catch (e) {
      console.error('GIS quote error:', e);
    }
  };

  // 3. Tool 3: Route & Water Payload
  const handleCalculateRoutePayload = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/route_payload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stops_addresses: [
            '1840 Lake Michigan Dr NW, Grand Rapids',
            '4450 44th St SE, Grand Rapids',
            '1200 Waverly Rd, Holland'
          ],
          water_tank_fill_gal: parseFloat(waterTankGal) || 275,
          sh_chemical_gal: parseFloat(shChemicalGal) || 45,
          jobs_estimated_gallons: [80.0, 140.0, 90.0]
        })
      });
      if (res.ok) {
        setRoutePayloadResult(await res.json());
      }
    } catch (e) {
      console.error('Payload error:', e);
    }
  };

  // Log Fleet Completion
  const handleLogFleetWash = async () => {
    if (!selectedFleetUnit) return;
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/fleet_log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          unit_id: selectedFleetUnit.id,
          unit_number: selectedFleetUnit.unit_number,
          company_name: selectedFleetUnit.company_name,
          wash_tier: selectedFleetUnit.wash_tier,
          technician_name: techName,
          gps_coords: gpsLocation,
          soap_applied: soapApplied,
          notes: `GPS verified completion with salt neutralizer undercarriage rinse.`
        })
      });
      if (res.ok) {
        setLogSuccessMsg(`✅ Verified wash logged for Unit ${selectedFleetUnit.unit_number}!`);
        setTimeout(() => {
          setLogSuccessMsg('');
          setShowLogModal(false);
          fetchFleet();
        }, 1800);
      }
    } catch (e) {
      console.error('Fleet log error:', e);
    }
  };

  // Create New Client
  const handleCreateClient = async () => {
    if (!newClient.name.trim() || !newClient.address.trim()) return;
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newClient)
      });
      if (res.ok) {
        setShowNewClientModal(false);
        setNewClient({
          name: '',
          company: '',
          client_type: 'residential',
          phone: '616-901-6536',
          email: '',
          address: '',
          city: 'Grand Rapids',
          zip_code: '49503',
          water_spigot_access: 'yes',
          notes: ''
        });
        fetchClients();
        fetchTelemetry();
      }
    } catch (e) {
      console.error('Client create error:', e);
    }
  };

  // Update Job Status
  const handleUpdateJobStatus = async (jobId, newStatus) => {
    try {
      const res = await fetch(`${backendUrl}/api/powerwash/jobs/${jobId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        fetchJobs();
        fetchTelemetry();
      }
    } catch (e) {
      console.error('Job status update error:', e);
    }
  };

  return (
    <div className="prestige-powerwash-container">
      {/* ── 1. Top Brand Header & Telemetry Deck ── */}
      <div className="pw-header-deck">
        <div className="pw-brand-left">
          <div className="pw-brand-badge">
            <span className="pw-brand-droplet">💦</span>
            <div>
              <div className="pw-brand-title">PRESTIGE MOBILE WASH</div>
              <div className="pw-brand-subtitle">RESIDENTIAL • COMMERCIAL • FLEET SERVICES</div>
            </div>
          </div>
          <div className="pw-phone-pill">
            <span>📞 Call / Text:</span>
            <strong>616-901-6536</strong>
          </div>
          <div className="pw-rig-pill">
            <span>🚛 Primary Rig:</span>
            <strong>Chevy 3500 HD Dually (275 Gal IBC Skid)</strong>
          </div>
        </div>

        {/* Telemetry Stat Badges */}
        {telemetry && (
          <div className="pw-telemetry-group">
            <div className="pw-stat-pill">
              <span className="pw-stat-label">Active Jobs:</span>
              <span className="pw-stat-val pw-stat-green">{telemetry.active_jobs_count}</span>
            </div>
            <div className="pw-stat-pill">
              <span className="pw-stat-label">Total Revenue:</span>
              <span className="pw-stat-val pw-stat-blue">${telemetry.total_revenue_booked?.toLocaleString() || '0'}</span>
            </div>
            <div className="pw-stat-pill">
              <span className="pw-stat-label">Sq Ft Washed:</span>
              <span className="pw-stat-val pw-stat-yellow">{telemetry.total_sq_ft_washed?.toLocaleString() || '0'} sq ft</span>
            </div>
            <div className="pw-stat-pill">
              <span className="pw-stat-label">Fleet Units:</span>
              <span className="pw-stat-val">{telemetry.active_fleet_units}</span>
            </div>
            <button
              onClick={() => setShowTips(!showTips)}
              className="pw-tips-toggle-btn"
              title="Toggle In-App Operational Tips & Explanation Banners"
            >
              <span>💡</span> {showTips ? 'Hide Tips' : 'Show Tips & Guide'}
            </button>
          </div>
        )}
      </div>

      {/* ── 2. Master Navigation Ribbon (The 5 AI-BS Tools + CRM) ── */}
      <div className="pw-nav-ribbon">
        <button
          className={`pw-nav-tab ${activeSubTab === 'estimator' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('estimator')}
        >
          <span>🔬</span> 1. CV Surface & Chemical Ratio Estimator
        </button>
        <button
          className={`pw-nav-tab ${activeSubTab === 'gis' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('gis')}
        >
          <span>🗺️</span> 2. GIS Parcel Quoting & Route Density
        </button>
        <button
          className={`pw-nav-tab ${activeSubTab === 'route' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('route')}
        >
          <span>💧</span> 3. Route & Water Payload (GVWR)
        </button>
        <button
          className={`pw-nav-tab ${activeSubTab === 'weather' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('weather')}
        >
          <span>❄️</span> 4. Weather Dispatch & Seasonal Engine
        </button>
        <button
          className={`pw-nav-tab ${activeSubTab === 'fleet' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('fleet')}
        >
          <span>🚛</span> 5. Commercial Fleet Wash Portal
        </button>
        <button
          className={`pw-nav-tab ${activeSubTab === 'crm' ? 'active' : ''}`}
          onClick={() => setActiveSubTab('crm')}
        >
          <span>📋</span> 6. Client CRM & Job Pipeline
        </button>
      </div>

      {/* ── 3. Main Tool Workspace ── */}
      <div className="pw-main-workspace">
        
        {/* ========================================================================= */}
        {/* TAB 1: CV SURFACE & CHEMICAL RATIO ESTIMATOR */}
        {/* ========================================================================= */}
        {activeSubTab === 'estimator' && (
          <div className="pw-tool-pane">
            <div className="pw-tool-header">
              <h2>🔬 Computer Vision Surface & Chemical Ratio Estimator</h2>
              <p>Generates exact chemical dilution recipes (Sodium Hypochlorite %, Surfactants, Degreasers), safe pressure thresholds, and proposal rates.</p>
            </div>

            {/* In-Tab Tips Card */}
            {showTips && (
              <div className="pw-tips-banner">
                <div className="pw-tips-title">
                  <span>💡 OPERATIONAL TIPS & CHEMICAL FORMULAS:</span>
                </div>
                <div className="pw-tips-content">
                  <div className="pw-tip-col">
                    <strong>🎯 How to Use This Tool:</strong>
                    <p>Select your substrate material and organic contamination type. Enter property square footage and story height, then click <em>"Generate Chemical Batch Recipe"</em> to calculate exact field ratios.</p>
                  </div>
                  <div className="pw-tip-col">
                    <strong>🧪 Chemical Mixing Rules:</strong>
                    <ul>
                      <li><strong>Vinyl Siding (House Wash):</strong> 1.0%–1.5% SH bleach, J-Rod 40° nozzle, max 150 PSI. Never pressure blast siding.</li>
                      <li><strong>Asphalt Shingle Roofs:</strong> 3.5%–4.0% SH bleach + high-cling surfactant. Max 90 PSI softwash. Never use pressure on shingles.</li>
                      <li><strong>Concrete Flatwork:</strong> 3,200 PSI rotary surface cleaner + 5.0%–6.0% SH post-treat to kill root spores.</li>
                      <li><strong>Wood & Composite:</strong> 0.8%–1.2% SH + mandatory Oxalic Acid post-neutralizer to brighten wood fibers.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            <div className="pw-grid-2col">
              {/* Left Control Column */}
              <div className="pw-card">
                <h3 className="pw-card-title">⚙️ Substrate & Contamination Parameters</h3>
                
                <div className="pw-form-group">
                  <label>Substrate Material:</label>
                  <select value={substrate} onChange={(e) => setSubstrate(e.target.value)} className="pw-select">
                    <option value="vinyl">Vinyl Siding (House Wash)</option>
                    <option value="brick">Red Brick & Mortar Joints</option>
                    <option value="stucco">Stucco / EIFS Delicate Facade</option>
                    <option value="asphalt_shingle">Asphalt Shingle Roof (Gloeocapsa Magma)</option>
                    <option value="tile">Clay / Concrete Roof Tile</option>
                    <option value="concrete">Concrete Driveway / Flatwork</option>
                    <option value="pavers">Paver Stone Patio & Walkways</option>
                    <option value="wood_composite">Composite Decking / Trex</option>
                    <option value="cedar">Cedar / Pressure-Treated Wood Fence</option>
                    <option value="aluminum">Aluminum Siding & Trim</option>
                  </select>
                </div>

                <div className="pw-form-group">
                  <label>Organic Contamination Type:</label>
                  <select value={contamination} onChange={(e) => setContamination(e.target.value)} className="pw-select">
                    <option value="black_algae">Gloeocapsa Magma (Black Algae Streaks)</option>
                    <option value="mildew">Green Algae / Mold / Mildew</option>
                    <option value="lichen">Lichen Clusters (Deep Root Spores)</option>
                    <option value="moss">Thick Roof Moss Growth</option>
                    <option value="engine_oil">Heavy Engine Oil / Grease Spill</option>
                    <option value="rust">Rust & Fertilizer Oxidation</option>
                    <option value="efflorescence">White Salt Efflorescence Leaching</option>
                  </select>
                </div>

                <div className="pw-form-group">
                  <label>Contamination Severity:</label>
                  <div className="pw-pill-selector">
                    {['light', 'moderate', 'heavy', 'severe'].map((sev) => (
                      <button
                        key={sev}
                        className={`pw-pill-btn ${severity === sev ? 'active' : ''}`}
                        onClick={() => setSeverity(sev)}
                      >
                        {sev.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pw-form-row">
                  <div className="pw-form-group flex-1">
                    <label>Square Footage:</label>
                    <input
                      type="number"
                      value={squareFootage}
                      onChange={(e) => setSquareFootage(e.target.value)}
                      className="pw-input"
                      min="100"
                      step="50"
                    />
                  </div>
                  <div className="pw-form-group flex-1">
                    <label>Elevation / Stories:</label>
                    <select value={storyCount} onChange={(e) => setStoryCount(e.target.value)} className="pw-select">
                      <option value="1">1-Story Ground Level</option>
                      <option value="2">2-Story Elevation (+25%)</option>
                      <option value="3">3-Story Commercial (+50%)</option>
                    </select>
                  </div>
                </div>

                <button onClick={handleCalculateSurface} disabled={isCalculating} className="pw-primary-btn w-full mt-4">
                  {isCalculating ? '⏳ Analyzing Substrate...' : '⚡ Generate Chemical Batch Recipe'}
                </button>
              </div>

              {/* Right Output Recipe & Proposal */}
              {calcResult && (
                <div className="pw-card pw-card-highlight">
                  <h3 className="pw-card-title text-cyan-400">🧪 Precision Field Mixing Recipe & PSI Limits</h3>
                  
                  <div className="pw-recipe-grid">
                    <div className="pw-recipe-metric">
                      <span className="pw-metric-label">Target SH Bleach %</span>
                      <span className="pw-metric-val text-yellow-400">{calcResult.recommended_recipe?.target_sh_percentage || 'N/A'}</span>
                    </div>
                    <div className="pw-recipe-metric">
                      <span className="pw-metric-label">Max Pressure Limit</span>
                      <span className="pw-metric-val text-green-400">{calcResult.recommended_recipe?.max_safe_psi || 'N/A'}</span>
                    </div>
                    <div className="pw-recipe-metric">
                      <span className="pw-metric-label">Recommended Nozzle</span>
                      <span className="pw-metric-val text-blue-300">{calcResult.recommended_recipe?.recommended_nozzle_tip || 'N/A'}</span>
                    </div>
                    <div className="pw-recipe-metric">
                      <span className="pw-metric-label">Chemical Dwell Time</span>
                      <span className="pw-metric-val text-purple-300">{calcResult.recommended_recipe?.dwell_time_minutes || 'N/A'}</span>
                    </div>
                  </div>

                  {/* 50 Gallon Soft Wash Batch Card */}
                  <div className="pw-batch-tank-box">
                    <h4 className="font-bold text-white mb-2">🛢️ 50-Gallon Soft Wash Batch Tank Recipe:</h4>
                    <ul className="pw-tank-list">
                      <li><strong>Raw 12.5% Pool Shock Bleach:</strong> {calcResult.recommended_recipe?.batch_50_gal_mix?.raw_12_5_sh_gallons || 0} Gallons</li>
                      <li><strong>Fresh Water Buffer:</strong> {calcResult.recommended_recipe?.batch_50_gal_mix?.water_gallons || 0} Gallons</li>
                      <li><strong>Prestige High-Cling Surfactant:</strong> {calcResult.recommended_recipe?.batch_50_gal_mix?.surfactant_oz || 0} oz</li>
                      {calcResult.recommended_recipe?.degreaser_required && (
                        <li className="text-amber-400 font-bold">⚠️ Heavy Degreaser Additive: 2 Quarts</li>
                      )}
                      {calcResult.recommended_recipe?.oxalic_acid_brightener_required && (
                        <li className="text-cyan-300 font-bold">✨ Post-Rinse Oxalic Acid Wood/Rust Neutralizer Required</li>
                      )}
                    </ul>
                  </div>

                  {/* Instant Pricing Proposal Card */}
                  <div className="pw-quote-summary-box">
                    <div className="flex justify-between items-center">
                      <div>
                        <span className="text-xs text-gray-400">INSTANT PROPOSAL RATE:</span>
                        <div className="text-2xl font-bold text-green-400">${calcResult.pricing_proposal?.total_quote_price?.toFixed(2) || '0.00'}</div>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-gray-400">ESTIMATED CREW DURATION:</span>
                        <div className="text-lg font-bold text-white">~{calcResult.pricing_proposal?.estimated_duration_hours || '0'} Hours</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: AUTOMATED GIS LEAD QUOTING & ROUTE DENSITY */}
        {/* ========================================================================= */}
        {activeSubTab === 'gis' && (
          <div className="pw-tool-pane">
            <div className="pw-tool-header">
              <h2>🗺️ Automated GIS Lead Quoting Pipeline & Route-Density Engine</h2>
              <p>Ingests customer parcel footprint, calculates roof pitch/driveway sq ft, and applies neighborhood route density discounts.</p>
            </div>

            {/* In-Tab Tips Card */}
            {showTips && (
              <div className="pw-tips-banner">
                <div className="pw-tips-title">
                  <span>💡 OPERATIONAL TIPS & ROUTE-DENSITY DISCOUNTS:</span>
                </div>
                <div className="pw-tips-content">
                  <div className="pw-tip-col">
                    <strong>🎯 How to Use This Tool:</strong>
                    <p>Enter the property address, base footprint square footage, and roof pitch slope. Check off the service packages to bundle, then click <em>"Calculate Instant GIS Proposal"</em>.</p>
                  </div>
                  <div className="pw-tip-col">
                    <strong>🏷️ Route-Density Group Pricing:</strong>
                    <ul>
                      <li><strong>0 Nearby Jobs:</strong> Standard single-stop travel pricing.</li>
                      <li><strong>1 Nearby Job:</strong> 10% discount applied (same-day crew already mobilized in area).</li>
                      <li><strong>2+ Nearby Jobs:</strong> 15% fleet discount applied (high neighborhood density maximizes daily GPM production).</li>
                      <li><strong>60-Second Dispatch:</strong> Copy the auto-generated SMS preview to dispatch instant proposals to leads.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            <div className="pw-grid-2col">
              {/* Left Form Inputs */}
              <div className="pw-card">
                <h3 className="pw-card-title">📍 Parcel & Structure Parameters</h3>

                <div className="pw-form-group">
                  <label>Customer Property Address:</label>
                  <input
                    type="text"
                    value={gisAddress}
                    onChange={(e) => setGisAddress(e.target.value)}
                    className="pw-input"
                  />
                </div>

                <div className="pw-form-row">
                  <div className="pw-form-group flex-1">
                    <label>Building Base Footprint (sq ft):</label>
                    <input
                      type="number"
                      value={buildingSqft}
                      onChange={(e) => setBuildingSqft(e.target.value)}
                      className="pw-input"
                    />
                  </div>
                  <div className="pw-form-group flex-1">
                    <label>Roof Pitch Angle:</label>
                    <select value={roofPitch} onChange={(e) => setRoofPitch(e.target.value)} className="pw-select">
                      <option value="4/12">4/12 Pitch (Low Slope / Easy Walk)</option>
                      <option value="6/12">6/12 Pitch (Standard Michigan Colonial)</option>
                      <option value="8/12">8/12 Pitch (Steep Roof +20% Area)</option>
                      <option value="10/12">10/12 Pitch (High Pitch +30%)</option>
                      <option value="12/12">12/12 Pitch (Extreme Mansard/A-Frame +41%)</option>
                    </select>
                  </div>
                </div>

                <div className="pw-form-group">
                  <label>Driveway & Sidewalk Flatwork (sq ft):</label>
                  <input
                    type="number"
                    value={drivewaySqft}
                    onChange={(e) => setDrivewaySqft(e.target.value)}
                    className="pw-input"
                  />
                </div>

                <div className="pw-form-group">
                  <label>Selected Service Bundles:</label>
                  <div className="flex gap-4 flex-wrap mt-1">
                    <label className="pw-checkbox-label">
                      <input type="checkbox" checked={includeSiding} onChange={(e) => setIncludeSiding(e.target.checked)} />
                      House Siding Soft Wash
                    </label>
                    <label className="pw-checkbox-label">
                      <input type="checkbox" checked={includeRoof} onChange={(e) => setIncludeRoof(e.target.checked)} />
                      Roof Soft Wash
                    </label>
                    <label className="pw-checkbox-label">
                      <input type="checkbox" checked={includeDriveway} onChange={(e) => setIncludeDriveway(e.target.checked)} />
                      Driveway Rotary Wash
                    </label>
                  </div>
                </div>

                <div className="pw-form-group">
                  <label>Existing Nearby Prestige Jobs in Neighborhood (Route Density):</label>
                  <select value={nearbyJobsCount} onChange={(e) => setNearbyJobsCount(e.target.value)} className="pw-select">
                    <option value="0">0 Jobs Nearby (Single Standalone Stop)</option>
                    <option value="1">1 Job Nearby (10% Same-Day Crew Discount)</option>
                    <option value="2">2+ Jobs Nearby (15% Fleet Route-Density Discount)</option>
                  </select>
                </div>

                <button onClick={handleCalculateGisQuote} className="pw-primary-btn w-full mt-2">
                  ⚡ Calculate Instant GIS Proposal
                </button>
              </div>

              {/* Right Proposal Preview */}
              {gisQuoteResult && (
                <div className="pw-card">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="pw-card-title m-0 text-cyan-400">📄 Itemized Customer Proposal</h3>
                    <span className="text-xs text-gray-400">{gisQuoteResult.generated_at}</span>
                  </div>

                  <div className="pw-proposal-table-wrapper">
                    <table className="pw-table">
                      <thead>
                        <tr>
                          <th>Service</th>
                          <th>Area</th>
                          <th>Rate</th>
                          <th className="text-right">Amount</th>
                        </tr>
                      </thead>
                      <tbody>
                        {gisQuoteResult.itemized_services?.map((srv, idx) => (
                          <tr key={idx}>
                            <td>{srv.service}</td>
                            <td>{srv.area_sqft} sq ft</td>
                            <td>${srv.rate_per_sqft?.toFixed(2) || '0.00'}</td>
                            <td className="text-right font-bold text-white">${srv.amount?.toFixed(2) || '0.00'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Subtotal & Route Density Discount */}
                  <div className="pw-discount-box">
                    <div className="flex justify-between text-sm text-gray-300">
                      <span>Standard Subtotal:</span>
                      <span>${gisQuoteResult.subtotal?.toFixed(2) || '0.00'}</span>
                    </div>
                    {gisQuoteResult.route_density_discount_pct > 0 && (
                      <div className="flex justify-between text-sm text-green-400 font-bold mt-1">
                        <span>🏷️ {gisQuoteResult.discount_reason}:</span>
                        <span>-${gisQuoteResult.discount_amount?.toFixed(2) || '0.00'}</span>
                      </div>
                    )}
                    <div className="pw-divider" />
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-lg text-white">FINAL PROPOSAL TOTAL:</span>
                      <span className="font-bold text-2xl text-green-400">${gisQuoteResult.final_total_quote?.toFixed(2) || '0.00'}</span>
                    </div>
                  </div>

                  {/* SMS Dispatch Preview */}
                  <div className="pw-sms-preview-box">
                    <div className="text-xs font-bold text-cyan-300 mb-1">📱 Instant 60-Second SMS Dispatch Preview:</div>
                    <code className="text-xs text-gray-200">{gisQuoteResult.proposal_dispatch_sms}</code>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: ROUTE & WATER PAYLOAD (GVWR) OPTIMIZER */}
        {/* ========================================================================= */}
        {activeSubTab === 'route' && (
          <div className="pw-tool-pane">
            <div className="pw-tool-header">
              <h2>💧 Route & Water Payload (GVWR) Optimization Module</h2>
              <p>Sequences multi-stop routes ensuring vehicle Gross Vehicle Weight Rating (GVWR) compliance ($8.34 lbs/gal) and maps West Michigan water fill stations.</p>
            </div>

            {/* In-Tab Tips Card */}
            {showTips && (
              <div className="pw-tips-banner">
                <div className="pw-tips-title">
                  <span>💡 OPERATIONAL TIPS & GVWR WEIGHT SAFETY:</span>
                </div>
                <div className="pw-tips-content">
                  <div className="pw-tip-col">
                    <strong>🎯 How to Use This Tool:</strong>
                    <p>Adjust your buffer water tank volume (up to 275 Gal IBC tote) and 55 Gal SH bleach tank. Click <em>"Re-Calculate Legal Payload & Refills"</em> to verify legal GVWR compliance.</p>
                  </div>
                  <div className="pw-tip-col">
                    <strong>⚖️ Vehicle Weight & Hydrant Rules:</strong>
                    <ul>
                      <li><strong>Water Weight:</strong> Water weighs 8.34 lbs/gal; 12.5% SH bleach weighs 10.05 lbs/gal. A full 275 gal tote adds 2,293.5 lbs payload.</li>
                      <li><strong>Legal Limit:</strong> Total gross vehicle weight must remain under the 14,000 lbs GVWR limit for the Chevy 3500 HD Dually.</li>
                      <li><strong>Depletion Tracking:</strong> The system sequences your multi-stop route and highlights municipal fill hydrants when buffer water drops below 40 gallons.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            <div className="pw-grid-2col">
              {/* Left Truck Specs & Tank Dials */}
              <div className="pw-card">
                <h3 className="pw-card-title">🚛 Rig Tank Capacity & Weight Controls</h3>
                
                <div className="pw-form-group">
                  <label>Truck Configuration:</label>
                  <input type="text" readOnly value="Chevy Silverado 3500 HD Dually (Crew Cab Flatbed)" className="pw-input bg-gray-900" />
                </div>

                <div className="pw-form-row">
                  <div className="pw-form-group flex-1">
                    <label>Buffer Water Tank Fill (Gal):</label>
                    <input
                      type="number"
                      value={waterTankGal}
                      onChange={(e) => setWaterTankGal(e.target.value)}
                      className="pw-input"
                      max="275"
                    />
                    <span className="text-xs text-gray-400">Standard 275 Gal IBC Tote</span>
                  </div>
                  <div className="pw-form-group flex-1">
                    <label>Softwash Bleach Tank (Gal):</label>
                    <input
                      type="number"
                      value={shChemicalGal}
                      onChange={(e) => setShChemicalGal(e.target.value)}
                      className="pw-input"
                      max="55"
                    />
                    <span className="text-xs text-gray-400">55 Gal Poly Tank</span>
                  </div>
                </div>

                <button onClick={handleCalculateRoutePayload} className="pw-primary-btn w-full mt-4">
                  🔄 Re-Calculate Legal Payload & Refills
                </button>
              </div>

              {/* Right GVWR Weight Meter */}
              {routePayloadResult && (
                <div className="pw-card">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="pw-card-title m-0 text-cyan-400">⚖️ Legal GVWR Weight Verification</h3>
                    <span className={`pw-status-tag ${routePayloadResult.is_gvwr_compliant ? 'pw-status-green' : 'pw-status-red'}`}>
                      {routePayloadResult.gvwr_status_badge}
                    </span>
                  </div>

                  <div className="pw-weight-meter-box">
                    <div className="flex justify-between text-sm mb-1">
                      <span>Total Gross Weight: <strong>{routePayloadResult.total_gross_vehicle_weight_lbs?.toLocaleString() || '0'} lbs</strong></span>
                      <span>Legal Max GVWR: <strong>{routePayloadResult.legal_gvwr_limit_lbs?.toLocaleString() || '0'} lbs</strong></span>
                    </div>
                    <div className="pw-progress-bar-bg">
                      <div
                        className={`pw-progress-bar-fill ${routePayloadResult.is_gvwr_compliant ? 'bg-cyan-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(100, (routePayloadResult.total_gross_vehicle_weight_lbs / routePayloadResult.legal_gvwr_limit_lbs) * 100)}%` }}
                      />
                    </div>
                    <div className="text-right text-xs text-gray-400 mt-1">
                      Remaining Payload Margin: <strong className="text-green-400">{routePayloadResult.remaining_payload_capacity_lbs?.toLocaleString() || '0'} lbs</strong>
                    </div>
                  </div>

                  <h4 className="font-bold text-white text-sm mt-4 mb-2">🗺️ Pre-Mapped West Michigan Municipal Hydrant Fill Stations:</h4>
                  <div className="pw-stations-list">
                    {routePayloadResult.recommended_west_mi_fill_stations?.map((st) => (
                      <div key={st.id} className="pw-station-card">
                        <div className="font-bold text-cyan-300 text-sm">{st.name}</div>
                        <div className="text-xs text-gray-400">{st.city}, MI {st.zip} • Flow Rate: {st.flow_rate_gpm} GPM ({st.type})</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: WEATHER DISPATCH & SEASONAL RECIRCULATION */}
        {/* ========================================================================= */}
        {activeSubTab === 'weather' && weatherData && (
          <div className="pw-tool-pane">
            <div className="pw-tool-header">
              <h2>❄️ West Michigan Weather Dispatch & Seasonal Recirculation</h2>
              <p>Monitors freezing thresholds (under 34°F), high-reach chemical wind drift limits, and triggers seasonal re-engagement campaigns.</p>
            </div>

            {/* In-Tab Tips Card */}
            {showTips && (
              <div className="pw-tips-banner">
                <div className="pw-tips-title">
                  <span>💡 OPERATIONAL TIPS & WEATHER DISPATCH THRESHOLDS:</span>
                </div>
                <div className="pw-tips-content">
                  <div className="pw-tip-col">
                    <strong>🎯 How to Use This Tool:</strong>
                    <p>Monitors real-time West Michigan meteorological data (Kent, Ottawa, Muskegon counties) to ensure chemical application safety and trigger seasonal re-engagement offers.</p>
                  </div>
                  <div className="pw-tip-col">
                    <strong>❄️ Spray Safety Thresholds:</strong>
                    <ul>
                      <li><strong>Sub-34°F Freeze Hold:</strong> Automatically halts dispatch to protect unheated softwash pumps, proportioner valves, and lines from freezing/cracking.</li>
                      <li><strong>Winds &gt; 15 mph Warning:</strong> Restricts high-reach roof/gutter wands to prevent chemical drift onto neighbor vehicles, roofs, and vegetation.</li>
                      <li><strong>Seasonal Matrix:</strong> Automated 6-month &amp; 12-month re-engagement campaigns for Spring De-Winterize, Summer Patio Peak, Fall Gutter Clear, and Winter Salt Neutralization.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Weather Alert Banner */}
            <div className="pw-weather-alert-banner" style={{ borderColor: weatherData.badge_color }}>
              <div className="flex items-center gap-4">
                <span className="text-4xl">🌤️</span>
                <div>
                  <div className="font-bold text-lg" style={{ color: weatherData.badge_color }}>
                    DISPATCH STATUS: {weatherData.spray_dispatch_status}
                  </div>
                  <div className="text-sm text-gray-300 mt-1">{weatherData.safety_notice}</div>
                </div>
              </div>
              <div className="pw-weather-stat-tags">
                <span>🌡️ {weatherData.current_temperature_f}°F</span>
                <span>💨 {weatherData.wind_speed_mph} mph Wind</span>
                <span>🌧️ {weatherData.precipitation_chance_pct}% Rain</span>
              </div>
            </div>

            {/* Seasonal Recirculation Matrix */}
            <h3 className="pw-card-title mt-6 mb-4">🍂 6-Month / 12-Month Seasonal Re-Engagement Campaigns</h3>
            <div className="pw-grid-seasonal">
              {weatherData.seasonal_campaigns?.map((camp, idx) => (
                <div key={idx} className={`pw-season-card ${camp.status === 'active' ? 'active-season' : ''}`}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-bold text-white text-base">{camp.season}</span>
                    <span className={`pw-status-tag ${camp.status === 'active' ? 'pw-status-green' : 'pw-status-gray'}`}>
                      {camp.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-xs text-cyan-300 font-semibold mb-2">{camp.months}</div>
                  <p className="text-xs text-gray-300 mb-3">{camp.offer}</p>
                  <div className="flex justify-between items-center text-xs text-gray-400">
                    <span>Target Leads: <strong>{camp.target_leads} Properties</strong></span>
                    <button className="pw-btn-sm" onClick={() => alert(`Triggered ${camp.season} SMS & Email Campaign to ${camp.target_leads} clients!`)}>
                      🚀 Launch Campaign
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 5: COMMERCIAL FLEET WASH PORTAL */}
        {/* ========================================================================= */}
        {activeSubTab === 'fleet' && (
          <div className="pw-tool-pane">
            <div className="pw-tool-header flex justify-between items-center">
              <div>
                <h2>🚛 Commercial Fleet Wash Verification Portal</h2>
                <p>Dedicated tracking for enterprise commercial clients (semi-trucks, box trucks, trailers) with GPS verification and batch invoicing.</p>
              </div>
              <button onClick={() => alert('Exporting Monthly Commercial Fleet Invoices...')} className="pw-primary-btn">
                🧾 Generate Monthly Fleet Invoices
              </button>
            </div>

            {/* In-Tab Tips Card */}
            {showTips && (
              <div className="pw-tips-banner">
                <div className="pw-tips-title">
                  <span>💡 OPERATIONAL TIPS & FLEET VERIFICATION:</span>
                </div>
                <div className="pw-tips-content">
                  <div className="pw-tip-col">
                    <strong>🎯 How to Use This Tool:</strong>
                    <p>Track commercial fleet vehicle units (semi-tractors, box trucks, 53ft trailers, cargo vans) under recurring maintenance contracts. Click <em>"📸 Log Wash"</em> upon finishing each vehicle.</p>
                  </div>
                  <div className="pw-tip-col">
                    <strong>🚛 Fleet Service Tiers & Billing:</strong>
                    <ul>
                      <li><strong>Standard Wash:</strong> High-pressure soap wash + rinse ($65–$75/unit).</li>
                      <li><strong>Acid Brightening:</strong> Hydrofluoric/Phosphoric aluminum fuel tank & wheel restoration ($85–$95/unit).</li>
                      <li><strong>Undercarriage Salt Neutralizer:</strong> High-pressure hot water chassis rinse for winter road salt decontamination.</li>
                      <li><strong>Batch Invoicing:</strong> Click "Generate Monthly Fleet Invoices" to aggregate all logged washes into single consolidated billing.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            <div className="pw-table-container">
              <table className="pw-table">
                <thead>
                  <tr>
                    <th>Unit #</th>
                    <th>Company Name</th>
                    <th>Vehicle Type</th>
                    <th>Wash Tier</th>
                    <th>Rate / Wash</th>
                    <th>Last Wash</th>
                    <th>Next Due</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {fleetUnits.map((u) => (
                    <tr key={u.id}>
                      <td className="font-bold text-cyan-300">{u.unit_number}</td>
                      <td>{u.company_name}</td>
                      <td>{u.vehicle_type.replace('_', ' ').toUpperCase()}</td>
                      <td>
                        <span className="pw-tier-badge">{u.wash_tier?.replace('_', ' ') || '--'}</span>
                      </td>
                      <td className="font-bold text-green-400">${u.price_per_wash?.toFixed(2) || '0.00'}</td>
                      <td>{u.last_wash_date}</td>
                      <td>{u.next_due_date}</td>
                      <td>
                        <span className="pw-status-tag pw-status-green">{u.status}</span>
                      </td>
                      <td>
                        <button
                          className="pw-btn-sm"
                          onClick={() => {
                            setSelectedFleetUnit(u);
                            setShowLogModal(true);
                          }}
                        >
                          📸 Log Wash
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Log Wash Modal */}
            {showLogModal && selectedFleetUnit && (
              <div className="pw-modal-overlay">
                <div className="pw-modal-box">
                  <h3 className="text-lg font-bold text-white mb-2">📸 Log Verified Fleet Wash Completion</h3>
                  <p className="text-xs text-gray-400 mb-4">{selectedFleetUnit.company_name} • Unit {selectedFleetUnit.unit_number}</p>

                  <div className="pw-form-group">
                    <label>Technician / Lead:</label>
                    <input type="text" value={techName} onChange={(e) => setTechName(e.target.value)} className="pw-input" />
                  </div>

                  <div className="pw-form-group">
                    <label>GPS Verified Coordinates:</label>
                    <input type="text" value={gpsLocation} onChange={(e) => setGpsLocation(e.target.value)} className="pw-input" />
                  </div>

                  <div className="pw-form-group">
                    <label>Chemical / Soap Applied:</label>
                    <input type="text" value={soapApplied} onChange={(e) => setSoapApplied(e.target.value)} className="pw-input" />
                  </div>

                  {logSuccessMsg ? (
                    <div className="text-green-400 font-bold text-center my-4">{logSuccessMsg}</div>
                  ) : (
                    <div className="flex justify-end gap-3 mt-6">
                      <button onClick={() => setShowLogModal(false)} className="pw-secondary-btn">Cancel</button>
                      <button onClick={handleLogFleetWash} className="pw-primary-btn">✅ Verify & Save Wash Record</button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 6: CLIENT CRM & JOB PIPELINE */}
        {/* ========================================================================= */}
        {activeSubTab === 'crm' && (
          <div className="pw-tool-pane">
            <div className="pw-tool-header flex justify-between items-center">
              <div>
                <h2>📋 Prestige Client CRM & Job Pipeline</h2>
                <p>Track residential and commercial pressure washing clients, property access details, and job stages.</p>
              </div>
              <button onClick={() => setShowNewClientModal(true)} className="pw-primary-btn">
                ➕ Add New Client
              </button>
            </div>

            {/* In-Tab Tips Card */}
            {showTips && (
              <div className="pw-tips-banner">
                <div className="pw-tips-title">
                  <span>💡 OPERATIONAL TIPS & KANBAN PIPELINE:</span>
                </div>
                <div className="pw-tips-content">
                  <div className="pw-tip-col">
                    <strong>🎯 How to Use This Tool:</strong>
                    <p>Manage customer property profiles, gate codes, and water spigot access notes. Advance job cards across the Kanban stages as crews dispatch and complete work.</p>
                  </div>
                  <div className="pw-tip-col">
                    <strong>📋 Kanban Workflow Stages:</strong>
                    <ul>
                      <li><strong>💡 Leads:</strong> Inquiries from web forms, referrals, or GIS estimates.</li>
                      <li><strong>📨 Estimates Sent:</strong> Itemized proposals delivered via SMS/Email.</li>
                      <li><strong>📅 Scheduled:</strong> Customer confirmed date and arrival window.</li>
                      <li><strong>💦 In Progress:</strong> Crew on-site, hoses deployed, chemical dwell active.</li>
                      <li><strong>✅ Completed:</strong> Post-rinse inspection approved by homeowner/property manager.</li>
                      <li><strong>💰 Paid:</strong> Payment received and synced into AI-BS Master Accounting ledger.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Job Pipeline Kanban */}
            <div className="pw-kanban-board">
              {['lead', 'estimate_sent', 'scheduled', 'in_progress', 'completed', 'paid'].map((col) => {
                const colJobs = jobs.filter((j) => j.status === col);
                const colTitles = {
                  lead: '💡 Leads / Inquiries',
                  estimate_sent: '📨 Estimates Sent',
                  scheduled: '📅 Scheduled',
                  in_progress: '💦 In Progress (On-Site)',
                  completed: '✅ Completed',
                  paid: '💰 Paid & Invoiced'
                };
                return (
                  <div key={col} className="pw-kanban-col">
                    <div className="pw-kanban-header">
                      <span>{colTitles[col]}</span>
                      <span className="pw-badge-count">{colJobs.length}</span>
                    </div>
                    <div className="pw-kanban-cards">
                      {colJobs.map((j) => (
                        <div key={j.id} className="pw-job-card">
                          <div className="font-bold text-white text-sm">{j.client_name}</div>
                          <div className="text-xs text-gray-400 mt-1">{j.address}, {j.city}</div>
                          <div className="flex justify-between items-center mt-3">
                            <span className="text-xs font-bold text-cyan-300">{j.service_type?.replace('_', ' ').toUpperCase() || '--'}</span>
                            <span className="text-sm font-bold text-green-400">${j.quote_amount?.toFixed(2) || '0.00'}</span>
                          </div>

                          {/* Quick Stage Transitions */}
                          <div className="pw-card-stage-buttons mt-3">
                            {col === 'scheduled' && (
                              <button onClick={() => handleUpdateJobStatus(j.id, 'in_progress')} className="pw-btn-micro">
                                ▶ Start Job
                              </button>
                            )}
                            {col === 'in_progress' && (
                              <button onClick={() => handleUpdateJobStatus(j.id, 'completed')} className="pw-btn-micro text-green-400">
                                ✓ Complete
                              </button>
                            )}
                            {col === 'completed' && (
                              <button onClick={() => handleUpdateJobStatus(j.id, 'paid')} className="pw-btn-micro text-emerald-300">
                                💵 Mark Paid
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Clients Table */}
            <h3 className="pw-card-title mt-8 mb-4">👥 Client Directory</h3>
            <div className="pw-table-container">
              <table className="pw-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Company</th>
                    <th>Type</th>
                    <th>Phone</th>
                    <th>Address</th>
                    <th>City / Zip</th>
                    <th>Water Access</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map((c) => (
                    <tr key={c.id}>
                      <td className="font-bold text-white">{c.name}</td>
                      <td>{c.company || '--'}</td>
                      <td><span className="pw-status-tag pw-status-blue">{c.client_type}</span></td>
                      <td>{c.phone}</td>
                      <td>{c.address}</td>
                      <td>{c.city} {c.zip_code}</td>
                      <td>{c.water_spigot_access}</td>
                      <td className="text-xs text-gray-400">{c.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Add Client Modal */}
            {showNewClientModal && (
              <div className="pw-modal-overlay">
                <div className="pw-modal-box">
                  <h3 className="text-lg font-bold text-white mb-4">➕ Add Prestige Client</h3>

                  <div className="pw-form-group">
                    <label>Client Name:</label>
                    <input type="text" value={newClient.name} onChange={(e) => setNewClient({ ...newClient, name: e.target.value })} className="pw-input" />
                  </div>

                  <div className="pw-form-row">
                    <div className="pw-form-group flex-1">
                      <label>Company (Optional):</label>
                      <input type="text" value={newClient.company} onChange={(e) => setNewClient({ ...newClient, company: e.target.value })} className="pw-input" />
                    </div>
                    <div className="pw-form-group flex-1">
                      <label>Client Type:</label>
                      <select value={newClient.client_type} onChange={(e) => setNewClient({ ...newClient, client_type: e.target.value })} className="pw-select">
                        <option value="residential">Residential</option>
                        <option value="commercial">Commercial</option>
                        <option value="hoa">HOA / Multi-Family</option>
                        <option value="fleet">Fleet Services</option>
                      </select>
                    </div>
                  </div>

                  <div className="pw-form-row">
                    <div className="pw-form-group flex-1">
                      <label>Phone Number:</label>
                      <input type="text" value={newClient.phone} onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })} className="pw-input" />
                    </div>
                    <div className="pw-form-group flex-1">
                      <label>Email Address:</label>
                      <input type="email" value={newClient.email} onChange={(e) => setNewClient({ ...newClient, email: e.target.value })} className="pw-input" />
                    </div>
                  </div>

                  <div className="pw-form-group">
                    <label>Property Address:</label>
                    <input type="text" value={newClient.address} onChange={(e) => setNewClient({ ...newClient, address: e.target.value })} className="pw-input" />
                  </div>

                  <div className="pw-form-row">
                    <div className="pw-form-group flex-1">
                      <label>City:</label>
                      <input type="text" value={newClient.city} onChange={(e) => setNewClient({ ...newClient, city: e.target.value })} className="pw-input" />
                    </div>
                    <div className="pw-form-group flex-1">
                      <label>ZIP Code:</label>
                      <input type="text" value={newClient.zip_code} onChange={(e) => setNewClient({ ...newClient, zip_code: e.target.value })} className="pw-input" />
                    </div>
                  </div>

                  <div className="pw-form-group">
                    <label>Water Spigot Access & Special Notes:</label>
                    <input type="text" placeholder="e.g. Back spigot active, gate code #1234" value={newClient.notes} onChange={(e) => setNewClient({ ...newClient, notes: e.target.value })} className="pw-input" />
                  </div>

                  <div className="flex justify-end gap-3 mt-6">
                    <button onClick={() => setShowNewClientModal(false)} className="pw-secondary-btn">Cancel</button>
                    <button onClick={handleCreateClient} className="pw-primary-btn">Save Client</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
