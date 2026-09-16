import React, { useState, useEffect } from 'react';
import { theme } from '../styles/theme';
import { 
  ShieldCheck, Cpu, DollarSign, Zap, Layers, Server, Sparkles, 
  Film, Music, Building2, Briefcase, Database, Terminal, ArrowRight,
  TrendingUp, CheckCircle, ExternalLink, Activity, HardDrive, Compass,
  Sliders, XCircle, Calculator, PieChart, ShieldAlert
} from 'lucide-react';

const HUBS_DATA = [
  {
    id: 'stehouwer_publishing',
    title: 'I. Stehouwer Publishing & Executive HQ',
    icon: <Building2 size={20} color="#00f0ff" />,
    badge: 'OPERATIONS & FINANCE',
    color: '#00f0ff',
    desc: 'Bare-metal operational nerve center managing physical services, client ledgers, and secure storage.',
    entities: [
      { name: 'Prestige Mobile Wash CRM', desc: 'Commercial pressure washing, chemical estimators & fleet dispatch', tab: 'power_washing' },
      { name: 'Master Accounting & Taxes', desc: 'Automated P&L balance sheets, expense classification & receipt OCR', tab: 'unified_financial' },
      { name: 'Shared Cloud Drive', desc: 'Local Google Drive-style cloud storage & document sync', tab: 'shared_cloud_drive' },
      { name: 'OSINT Recon & API Hub', desc: 'Deep intelligence, domain recon, and B2B lead discovery', tab: 'unified_osint' }
    ]
  },
  {
    id: 'hollywood_creation',
    title: 'II. Hollywood & Multimedia Creation Suite',
    icon: <Film size={20} color="#ff007f" />,
    badge: 'ENTERTAINMENT PRODUCTION',
    color: '#ff007f',
    desc: 'Full-spectrum creative studio generating industry-standard scripts, beats, and 4K video.',
    entities: [
      { name: 'Universal Screenwriting AST', desc: 'Hollywood screenplays, FDX serializer & Book-to-Script matrix', tab: 'unified_creation' },
      { name: 'FL Music Studio (DAW)', desc: '16/32-step drum sequencer, MIDI piano roll, 8-track mixer & Tone.js', tab: 'music_daw' },
      { name: 'Multimedia Video Studio', desc: 'ComfyUI Wan2.1 generative video & RTX 4090 NVENC 4K master MP4 export', tab: 'video_agent' },
      { name: 'Neural Voice & Audio Studio', desc: 'ElevenLabs zero-shot voice cloning & AI song generation', tab: 'neural_audio' }
    ]
  },
  {
    id: 'noto_hospitality',
    title: 'III. Noto Hospitality OS & Living Enclaves',
    icon: <Compass size={20} color="#a371f7" />,
    badge: 'PHYSICAL VENUES & LAND',
    color: '#a371f7',
    desc: 'Autonomous venue management, multi-bar logistics, and acoustic-agricultural enclave telemetry.',
    entities: [
      { name: 'Notō Multi-Bar Inventory', desc: 'Live bottle counting across Grand Rapids/Grand Haven & MLCC POs', tab: 'noto_inventory' },
      { name: 'Banquet Architect 2D/3D', desc: 'Interactive floorplans, seating charts & dietary registries', tab: 'banquet_architect' },
      { name: 'Project NoCo Living Stage', desc: '23-acre enclave IoT telemetry, solar balance & living stage acoustics', tab: 'project_noco' }
    ]
  },
  {
    id: 'creator_revenue',
    title: 'IV. Creator Revenue & Growth Engine',
    icon: <TrendingUp size={20} color="#5eff7b" />,
    badge: 'MONETIZATION & ADS',
    color: '#5eff7b',
    desc: 'Commercial growth infrastructure with public storefronts, ad copy generators, and lead scoring.',
    entities: [
      { name: 'Digital Storefront & Pricing', desc: 'Stripe, passes & Web3 crypto public checkout cart', tab: 'digital_storefront' },
      { name: 'Ad Campaign Studio', desc: 'AI headline copy, visual mockups & marketing funnels', tab: 'advertising' },
      { name: 'Personal Brand Studio', desc: 'Social media ghostwriter & automated content scheduler', tab: 'personal_brand' },
      { name: 'Lead Matrix Engine', desc: 'Automated B2B lead enrichment & client scoring', tab: 'leadmatrix' }
    ]
  },
  {
    id: 'neural_intelligence',
    title: 'V. Autonomous Neural Intelligence & IDE',
    icon: <Cpu size={20} color="#ffd000" />,
    badge: 'AI BRAIN & IPC CORE',
    color: '#ffd000',
    desc: 'Local AI orchestration running 13 Ollama models, multi-agent DAGs, and sub-ms shared memory.',
    entities: [
      { name: 'Multi-Agent DAG Builder', desc: 'Visual 5-node autonomous pipeline with live VRAM arbitration', tab: 'workflow_dag' },
      { name: 'BS-CHAT Developer IDE', desc: 'Split-pane code editor, virtual shell & powershell terminal', tab: 'ide' },
      { name: 'ChromaDB Vector Vault', desc: 'Semantic long-term vector memory & RAG knowledge explorer', tab: 'agent_memory' },
      { name: 'Hardware Telemetry Core', desc: '740k pkts/sec Windows SHM ring & GPU VRAM arbiter', tab: 'security_monitor' }
    ]
  },
  {
    id: 'satellite_applications',
    title: 'VI. Decoupled Satellites & Standalone App Builds',
    icon: <Server size={20} color="#00ffcc" />,
    badge: 'STANDALONE BUILDS (5 SATELLITES)',
    color: '#00ffcc',
    desc: 'Independently packageable client applications, mobile APKs, and desktop terminals linked to the AI-BS brain.',
    entities: [
      { name: 'Broadcast Studio App', desc: 'Standalone Electron + Vite streaming studio with NVENC encoding on Port 5174/8005', tab: 'broadcast_studio' },
      { name: 'Prestige Mobile Wash App', desc: 'Standalone Capacitor mobile app for Android/iOS detailing & fleet dispatch', tab: 'power_washing' },
      { name: 'Crypto-Swarm Trading Terminal', desc: 'Standalone Go Wails native desktop terminal with TWAP drip allocation', tab: 'cryptotrader' },
      { name: 'Digital Storefront & POS', desc: 'Standalone React mobile storefront & invoicing for Action Glass / Joe Hamilton', tab: 'digital_storefront' },
      { name: 'Unreal Cinematics & Julie’s Place', desc: 'Standalone Unreal Engine 5.8 virtual production sets with PixelStreaming on Port 8888', tab: 'unreal_viewport' }
    ]
  }
];

export default function EcosystemBlueprintTab() {
  const [activeHub, setActiveHub] = useState('stehouwer_publishing');
  
  // Interactive Financial ROI Calculator State
  const [toolCount, setToolCount] = useState(25);
  const [costPerTool, setCostPerTool] = useState(133);
  const [laborHoursWk, setLaborHoursWk] = useState(10);
  const [maintMonthly, setMaintMonthly] = useState(2000);

  // Theatrical Gateway State
  const [theatricalMode, setTheatricalMode] = useState(false);
  const [plays, setPlays] = useState([]);
  const [newPlayName, setNewPlayName] = useState('');

  // Matrix Doctor State
  const [matrixDoctorData, setMatrixDoctorData] = useState(null);
  const [isDoctorProbing, setIsDoctorProbing] = useState(false);
  const [isDoctorHealing, setIsDoctorHealing] = useState(false);
  const [doctorHealMsg, setDoctorHealMsg] = useState(null);

  const fetchMatrixDoctorStatus = async () => {
    setIsDoctorProbing(true);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/system/matrix/doctor');
      if (res.ok) {
        setMatrixDoctorData(await res.json());
      }
    } catch (e) {
      console.warn('Matrix Doctor API offline:', e);
    } finally {
      setIsDoctorProbing(false);
    }
  };

  const handleTriggerMatrixDoctorHeal = async () => {
    setIsDoctorHealing(true);
    setDoctorHealMsg('Running automated self-healing routines across 18 ports & lockfiles...');
    try {
      const res = await fetch('http://127.0.0.1:8080/api/system/matrix/doctor/heal', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setDoctorHealMsg(`✅ Auto-Heal Complete: Cleared ${data.actions_taken?.length || 0} dead locks. Health score: ${data.post_diagnosis?.health_score || 100}%`);
        setMatrixDoctorData(data.post_diagnosis);
      }
    } catch (e) {
      setDoctorHealMsg(`❌ Heal error: ${e.message}`);
    } finally {
      setIsDoctorHealing(false);
      setTimeout(() => setDoctorHealMsg(null), 7000);
    }
  };

  // Fetch theatrical plays & matrix doctor on load
  useEffect(() => {
    fetch('http://localhost:8001/theatrical/plays')
      .then(res => {
        if (!res.ok) return null;
        return res.json();
      })
      .then(data => {
        if (data?.plays) setPlays(data.plays);
      })
      .catch(() => {
        // Theatrical Gateway on port 8001 is offline or uninitialized; silent fallback
      });

    fetchMatrixDoctorStatus();
  }, []);

  const toggleTheatricalMode = async () => {
    try {
      const newState = !theatricalMode;
      await fetch('http://localhost:8001/theatrical/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: newState })
      });
      setTheatricalMode(newState);
    } catch (err) {
      console.error('Error toggling theatrical mode:', err);
    }
  };

  const createPlay = async () => {
    if (!newPlayName.trim()) return;
    try {
      const res = await fetch('http://localhost:8001/theatrical/plays/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ play_name: newPlayName })
      });
      if (res.ok) {
        setPlays([...plays, newPlayName]);
        setNewPlayName('');
      }
    } catch (err) {
      console.error('Error creating play:', err);
    }
  };

  const SETUP_FEE = 45000;
  const POWER_COST_MO = 40;
  const HOURLY_LABOR_RATE = 25;
  const SALES_TAX_RATE = 0.075;
  const MIDDLEWARE_API_COST = 550;
  const TAX_BRACKET = 0.30;

  // Real-time Calculations
  const saasBaseMo = toolCount * costPerTool;
  const salesTaxMo = saasBaseMo * SALES_TAX_RATE;
  const laborCostMo = (laborHoursWk * 52 * HOURLY_LABOR_RATE) / 12;
  const totalSaasMo = saasBaseMo + salesTaxMo + laborCostMo + MIDDLEWARE_API_COST;
  const totalAibsMo = maintMonthly + POWER_COST_MO;

  // 5-Year Projections (5% annual inflation on SaaS)
  let cumulativeSaas = 0;
  let currentYearSaas = totalSaasMo * 12;
  for (let yr = 0; yr < 5; yr++) {
    cumulativeSaas += currentYearSaas;
    currentYearSaas *= 1.05;
  }

  const cumulativeAibs = SETUP_FEE + (totalAibsMo * 12 * 5);
  const netSavings5Yr = cumulativeSaas - cumulativeAibs;
  const fiveYearTaxSaved = (salesTaxMo * 12) * 5;
  const sec179Shield = SETUP_FEE * TAX_BRACKET;

  const monthlyNetSavings = totalSaasMo - totalAibsMo;
  const breakEvenMonth = monthlyNetSavings > 0 ? Math.ceil(SETUP_FEE / monthlyNetSavings) : 0;

  const formatUSD = (val) => '$' + Math.round(val).toLocaleString();

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#07090e',
      color: '#c9d1d9',
      fontFamily: 'Inter, system-ui, sans-serif',
      overflowY: 'auto'
    }}>
      {/* Top Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.08) 0%, rgba(122, 40, 138, 0.15) 50%, rgba(0, 0, 0, 0.95) 100%)',
        borderBottom: `1px solid ${theme.colors.border}`,
        padding: '24px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span style={{ fontSize: '11px', background: 'rgba(0, 240, 255, 0.15)', color: '#00f0ff', padding: '3px 8px', borderRadius: '4px', border: '1px solid #00f0ff', fontWeight: 'bold' }}>
              FINANCIAL ARCHITECTURE & SYSTEMS CONSOLIDATION
            </span>
            <span style={{ fontSize: '11px', color: '#888' }}>AI-BS Matrix OS v5.147.0</span>
          </div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: '900', color: '#ffffff', letterSpacing: '-0.5px' }}>
            YOUR BUSINESS. YOUR HARDWARE.
          </h1>
          <h2 style={{ margin: '4px 0 0 0', fontSize: '14px', fontWeight: '600', color: '#f59e0b' }}>
            ELIMINATE THE SCATTERED SOFTWARE TAX & UNIFY OPERATIONS
          </h2>
        </div>

        {/* Bare-Metal Telemetry HUD */}
        <div style={{
          background: 'rgba(0, 0, 0, 0.75)',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '10px 16px',
          display: 'flex',
          gap: '16px',
          alignItems: 'center'
        }}>
          <div>
            <div style={{ fontSize: '9px', color: '#888', textTransform: 'uppercase' }}>CPU ENGINE</div>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#fff' }}>Ryzen 9 9950X</div>
          </div>
          <div style={{ height: '20px', width: '1px', background: '#30363d' }} />
          <div>
            <div style={{ fontSize: '9px', color: '#888', textTransform: 'uppercase' }}>GPU ACCELERATOR</div>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#5eff7b' }}>RTX 4090 (24GB)</div>
          </div>
          <div style={{ height: '20px', width: '1px', background: '#30363d' }} />
          <div>
            <div style={{ fontSize: '9px', color: '#888', textTransform: 'uppercase' }}>ZERO-COPY IPC</div>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#00f0ff' }}>742k Pkts/Sec</div>
          </div>
        </div>
      </div>

      <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 1: INTERACTIVE TCO & ROI SIMULATOR                          */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div style={{
          background: '#111827',
          border: '1px solid #334155',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ fontSize: '13px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '1px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Calculator size={16} /> Dynamic TCO & ROI Simulator
            </span>
            <span style={{ fontSize: '11px', color: '#9ca3af' }}>Adjust sliders to simulate target business model</span>
          </div>

          {/* Sliders Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px 24px' }}>
            
            {/* Slider 1: Tool Count */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#9ca3af', marginBottom: '4px' }}>
                <span>SaaS Tool Count:</span>
                <span style={{ color: '#fff', fontWeight: '700' }}>{toolCount} Tools</span>
              </div>
              <input 
                type="range" 
                min="5" 
                max="50" 
                value={toolCount} 
                onChange={(e) => setToolCount(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#3b82f6', cursor: 'pointer' }}
              />
            </div>

            {/* Slider 2: Cost per Tool */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#9ca3af', marginBottom: '4px' }}>
                <span>Avg. Cost / Tool / Mo:</span>
                <span style={{ color: '#fff', fontWeight: '700' }}>${costPerTool} / mo</span>
              </div>
              <input 
                type="range" 
                min="30" 
                max="300" 
                step="5"
                value={costPerTool} 
                onChange={(e) => setCostPerTool(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#3b82f6', cursor: 'pointer' }}
              />
            </div>

            {/* Slider 3: Labor Hours Sync */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#9ca3af', marginBottom: '4px' }}>
                <span>Manual Data Sync (Labor):</span>
                <span style={{ color: '#fff', fontWeight: '700' }}>{laborHoursWk} hrs/wk</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="40" 
                value={laborHoursWk} 
                onChange={(e) => setLaborHoursWk(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#3b82f6', cursor: 'pointer' }}
              />
            </div>

            {/* Slider 4: AI-BS Maintenance Tier */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: '600', color: '#9ca3af', marginBottom: '4px' }}>
                <span>AI-BS Maintenance Tier:</span>
                <span style={{ color: '#fff', fontWeight: '700' }}>${maintMonthly.toLocaleString()} / mo</span>
              </div>
              <input 
                type="range" 
                min="1500" 
                max="3500" 
                step="250"
                value={maintMonthly} 
                onChange={(e) => setMaintMonthly(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#3b82f6', cursor: 'pointer' }}
              />
            </div>

          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 2: COMPARISON GRID (Legacy SaaS vs Unified AI-BS)          */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          
          {/* Legacy SaaS Nightmare Card */}
          <div style={{
            background: '#111827',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid #1f2937',
            borderTop: '4px solid #ef4444'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '15px', fontWeight: '800', textTransform: 'uppercase', color: '#ef4444' }}>
                {toolCount} Disconnected Programs
              </span>
              <XCircle size={18} color="#ef4444" />
            </div>

            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: '#9ca3af', padding: 0 }}>
              <li>• <strong style={{ color: '#fff' }}>Monthly Software Drain:</strong> {formatUSD(saasBaseMo)} base + {formatUSD(salesTaxMo)} sales tax.</li>
              <li>• <strong style={{ color: '#fff' }}>Middleware & API Metering:</strong> ~${MIDDLEWARE_API_COST} / mo in Zapier & cloud tokens.</li>
              <li>• <strong style={{ color: '#fff' }}>Manual Bridging Labor:</strong> {formatUSD(laborCostMo)} / mo in lost staff hours.</li>
              <li>• <strong style={{ color: '#fff' }}>Real Monthly Cost:</strong> <strong style={{ color: '#ef4444', fontSize: '14px' }}>{formatUSD(totalSaasMo)} / mo</strong></li>
              <li>• <strong style={{ color: '#fff' }}>Data Security Risk:</strong> Client assets held in external third-party silos.</li>
            </ul>
          </div>

          {/* Unified AI-BS Solution Card */}
          <div style={{
            background: 'linear-gradient(180deg, rgba(16, 185, 129, 0.05) 0%, #111827 100%)',
            borderRadius: '12px',
            padding: '20px',
            border: '1px solid #1f2937',
            borderTop: '4px solid #10b981'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span style={{ fontSize: '15px', fontWeight: '800', textTransform: 'uppercase', color: '#10b981' }}>
                Unified AI-BS Platform
              </span>
              <CheckCircle size={18} color="#10b981" />
            </div>

            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: '#9ca3af', padding: 0 }}>
              <li>• <strong style={{ color: '#fff' }}>1 Unified Command Center:</strong> CRM, media engine, accounting & AI agents.</li>
              <li>• <strong style={{ color: '#fff' }}>Total Monthly Overhead:</strong> <strong style={{ color: '#10b981', fontSize: '14px' }}>{formatUSD(totalAibsMo)} / mo</strong></li>
              <li>• <strong style={{ color: '#fff' }}>Zero Sales Tax on SaaS:</strong> Hardware deployed locally on owned NVMe.</li>
              <li>• <strong style={{ color: '#fff' }}>Automatic Sync:</strong> Native event bus cuts manual data entry to 0 hrs.</li>
              <li>• <strong style={{ color: '#fff' }}>100% Data Sovereignty:</strong> Offline-capable, zero external data tracking.</li>
            </ul>
          </div>

        </div>

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 3: 5-YEAR CUMULATIVE METRICS & TAX ACCELERATION             */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div style={{
          background: '#1e293b',
          borderRadius: '12px',
          padding: '20px 24px',
          border: '1px solid #334155'
        }}>
          <div style={{ textAlign: 'center', fontSize: '12px', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '1px', color: '#94a3b8', marginBottom: '16px' }}>
            5-Year Cumulative Cash Outflow & ROI
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', textAlign: 'center', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '10px', fontWeight: '600', color: '#9ca3af', marginBottom: '4px', textTransform: 'uppercase' }}>Legacy SaaS Outflow (5% Infl.)</div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#ef4444' }}>{formatUSD(cumulativeSaas)}</div>
            </div>
            <div>
              <div style={{ fontSize: '10px', fontWeight: '600', color: '#9ca3af', marginBottom: '4px', textTransform: 'uppercase' }}>AI-BS Outflow (Setup + Maint.)</div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#ffffff' }}>{formatUSD(cumulativeAibs)}</div>
            </div>
            <div>
              <div style={{ fontSize: '10px', fontWeight: '600', color: '#9ca3af', marginBottom: '4px', textTransform: 'uppercase' }}>5-Year Net Cash Retained</div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#10b981' }}>+{formatUSD(netSavings5Yr)}</div>
            </div>
          </div>
        </div>

        {/* Tax Breakdown Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
          <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '8px', padding: '14px' }}>
            <h4 style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8', marginBottom: '4px' }}>1. Sales Tax Eradicated</h4>
            <p style={{ fontSize: '11px', color: '#9ca3af', lineHeight: '1.4', margin: 0 }}>Permanently keeps <strong style={{ color: '#fff' }}>{formatUSD(fiveYearTaxSaved)}</strong> in consumption taxes over 5 years.</p>
          </div>

          <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '8px', padding: '14px' }}>
            <h4 style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8', marginBottom: '4px' }}>2. Sec. 179 Accelerated Write-Off</h4>
            <p style={{ fontSize: '11px', color: '#9ca3af', lineHeight: '1.4', margin: 0 }}>Immediate Year-1 deduction of <strong style={{ color: '#fff' }}>{formatUSD(sec179Shield)}</strong> to offset active income taxes.</p>
          </div>

          <div style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '8px', padding: '14px' }}>
            <h4 style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8', marginBottom: '4px' }}>3. Capital Efficiency</h4>
            <p style={{ fontSize: '11px', color: '#9ca3af', lineHeight: '1.4', margin: 0 }}>Reaches full break-even at <strong style={{ color: '#fff' }}>Month {breakEvenMonth}</strong>, retaining pure cash every month thereafter.</p>
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 4: THE 5 OPERATING HUBS EXPLORER                            */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 'bold', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} color="#00f0ff" /> 5 Core Operating Hubs
            </h2>
            <span style={{ fontSize: '11px', color: '#888' }}>SELECT A HUB TO EXPLORE SUBSYSTEMS:</span>
          </div>

          {/* Hub Selector Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginBottom: '16px' }}>
            {HUBS_DATA.map(hub => {
              const isSelected = activeHub === hub.id;
              return (
                <div
                  key={hub.id}
                  onClick={() => setActiveHub(hub.id)}
                  style={{
                    background: isSelected ? 'rgba(0, 240, 255, 0.1)' : 'rgba(255, 255, 255, 0.02)',
                    border: isSelected ? `2px solid ${hub.color}` : '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: isSelected ? `0 0 15px ${hub.color}33` : 'none'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    {hub.icon}
                    <span style={{ fontSize: '9px', fontWeight: 'bold', color: hub.color, background: 'rgba(0,0,0,0.5)', padding: '2px 6px', borderRadius: '3px' }}>
                      {hub.badge}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#fff', marginBottom: '4px' }}>
                    {hub.title}
                  </div>
                  <div style={{ fontSize: '10px', color: '#8b949e', lineHeight: '1.4' }}>
                    {hub.desc}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Hub Subsystem Entity Cards */}
          {(() => {
            const current = HUBS_DATA.find(h => h.id === activeHub);
            if (!current) return null;

            return (
              <div style={{
                background: 'rgba(13, 16, 24, 0.95)',
                border: `1px solid ${theme.colors.border}`,
                borderRadius: '8px',
                padding: '20px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                  {current.icon}
                  <h3 style={{ margin: 0, fontSize: '14px', color: '#fff', fontWeight: 'bold' }}>
                    Active Subsystems in {current.title}
                  </h3>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
                  {current.entities.map((ent, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        borderRadius: '6px',
                        padding: '12px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: 'bold', color: current.color, marginBottom: '4px' }}>
                          {ent.name}
                        </div>
                        <div style={{ fontSize: '11px', color: '#8b949e', lineHeight: '1.4', marginBottom: '10px' }}>
                          {ent.desc}
                        </div>
                      </div>

                      <a
                        href={`/?tab=${ent.tab}`}
                        style={{
                          fontSize: '10px',
                          color: '#fff',
                          background: 'rgba(255, 255, 255, 0.06)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          textDecoration: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontWeight: 'bold',
                          width: 'fit-content'
                        }}
                      >
                        Launch Tab <ExternalLink size={10} style={{ marginLeft: '4px' }} />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 5: THEATRICAL FILM HUB (NOCO VISION)                        */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        <div style={{
          background: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: '12px',
          padding: '20px',
          marginTop: '10px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ fontSize: '15px', fontWeight: '800', textTransform: 'uppercase', color: '#ff007f', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Film size={20} /> Theatrical Film Hub & Virtual Production
            </span>
            <button 
              onClick={toggleTheatricalMode}
              style={{
                background: theatricalMode ? '#ef4444' : '#10b981',
                color: '#fff',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Activity size={16} /> 
              {theatricalMode ? 'DISABLE THEATRICAL OVERRIDE' : 'ENABLE THEATRICAL OVERRIDE (PAUSE ECO)'}
            </button>
          </div>

          <div style={{ display: 'flex', gap: '20px' }}>
            {/* Play Management */}
            <div style={{ flex: 1, background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '8px' }}>
              <h3 style={{ fontSize: '13px', color: '#888', marginTop: 0, marginBottom: '12px' }}>VIRTUAL SET SCRIPTS (CHROMADB)</h3>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                <input 
                  type="text" 
                  value={newPlayName}
                  onChange={(e) => setNewPlayName(e.target.value)}
                  placeholder="New Play Name (e.g. JuliesPlace_S1E1)"
                  style={{ flex: 1, padding: '8px', background: '#000', border: '1px solid #30363d', color: '#fff', borderRadius: '4px' }}
                />
                <button onClick={createPlay} style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}>
                  Create
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {plays.length === 0 ? (
                  <div style={{ fontSize: '12px', color: '#666' }}>No active plays in database.</div>
                ) : (
                  plays.map(play => (
                    <div key={play} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px', background: '#000', border: '1px solid #222', borderRadius: '4px' }}>
                      <Database size={14} color="#00f0ff" />
                      <span style={{ fontSize: '12px', color: '#e2e8f0' }}>{play}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Unreal Engine Status */}
            <div style={{ flex: 1, background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '8px' }}>
              <h3 style={{ fontSize: '13px', color: '#888', marginTop: 0, marginBottom: '12px' }}>UNREAL ENGINE 5.8 TELEMETRY</h3>
              <div style={{ fontSize: '12px', color: '#9ca3af', lineHeight: '1.6' }}>
                <strong>Director Daemon:</strong> {theatricalMode ? <span style={{ color: '#10b981' }}>ACTIVE</span> : <span style={{ color: '#ef4444' }}>SUSPENDED</span>}<br/>
                <strong>Signaling Server:</strong> 127.0.0.1:8888<br/>
                <strong>Active Scene:</strong> Julie's Place - Master Sequence<br/>
                <strong>Asset Pipeline:</strong> C:\AI-BS\JuliesPlace\RawAssets<br/><br/>
                <span style={{ color: '#f59e0b', fontSize: '11px' }}>
                  * Theatrical override suspends background Crypto TWAP mining to allocate RTX 4090 VRAM entirely to Unreal Engine Path Tracing.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Matrix Doctor Diagnostic & Self-Healing Deck */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '32px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#00f0ff', boxShadow: '0 0 8px #00f0ff' }} />
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                🩺 MATRIX DOCTOR: 18-PORT DIAGNOSTIC & SELF-HEALING SUITE
              </h2>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button
                onClick={fetchMatrixDoctorStatus}
                disabled={isDoctorProbing}
                style={{
                  background: '#1e293b',
                  color: '#00f0ff',
                  border: '1px solid #00f0ff',
                  padding: '8px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                {isDoctorProbing ? 'Probing...' : '🔄 Probe 18 Ports'}
              </button>

              <button
                onClick={handleTriggerMatrixDoctorHeal}
                disabled={isDoctorHealing}
                style={{
                  background: 'linear-gradient(90deg, #059669 0%, #0284c7 100%)',
                  color: '#ffffff',
                  border: 'none',
                  padding: '8px 18px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  boxShadow: '0 0 15px rgba(5, 150, 105, 0.4)'
                }}
              >
                {isDoctorHealing ? 'Healing System...' : '⚡ Run Automated Self-Heal'}
              </button>
            </div>
          </div>

          {doctorHealMsg && (
            <div style={{ padding: '12px', background: 'rgba(5, 150, 105, 0.2)', border: '1px solid #059669', borderRadius: '8px', fontSize: '12px', color: '#6ee7b7', marginBottom: '16px' }}>
              {doctorHealMsg}
            </div>
          )}

          {matrixDoctorData && (
            <div>
              {/* Score strip */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                <div style={{ background: '#0b1120', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>Ecosystem Health Score</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: matrixDoctorData.health_score >= 80 ? '#10b981' : '#f59e0b' }}>
                    {matrixDoctorData.health_score}% ({matrixDoctorData.system_status})
                  </div>
                </div>

                <div style={{ background: '#0b1120', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>Online Ports</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#00f0ff' }}>
                    {matrixDoctorData.online_ports} / {matrixDoctorData.total_ports} Online
                  </div>
                </div>

                <div style={{ background: '#0b1120', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>Critical Services</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#10b981' }}>
                    {matrixDoctorData.critical_online} / {matrixDoctorData.total_critical} (100%)
                  </div>
                </div>

                <div style={{ background: '#0b1120', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>Stale Locks / PIDs</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: matrixDoctorData.orphan_locks?.length > 0 ? '#f59e0b' : '#10b981' }}>
                    {matrixDoctorData.orphan_locks?.length || 0} Managed
                  </div>
                </div>
              </div>

              {/* Ports Matrix Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '8px' }}>
                {Object.entries(matrixDoctorData.ports || {}).map(([port, info]) => (
                  <div key={port} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    background: info.online ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)',
                    border: `1px solid ${info.online ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.2)'}`,
                    borderRadius: '6px',
                    fontSize: '11px'
                  }}>
                    <div>
                      <div style={{ fontWeight: 'bold', color: '#ffffff' }}>{info.name}</div>
                      <div style={{ color: '#94a3b8', fontSize: '10px' }}>Port {port} • {info.category}</div>
                    </div>
                    <span style={{
                      fontWeight: 'bold',
                      fontSize: '10px',
                      color: info.online ? '#10b981' : '#ef4444',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: info.online ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'
                    }}>
                      {info.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Callout */}
        <div style={{
          textAlign: 'center',
          background: 'linear-gradient(90deg, #1e3a8a 0%, #065f46 100%)',
          borderRadius: '10px',
          padding: '16px 20px',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <h3 style={{ fontSize: '15px', fontWeight: '800', color: '#ffffff', marginBottom: '4px' }}>
            INVEST IN AI-BS: ONE PLATFORM. ZERO SUBSCRIPTIONS.
          </h3>
          <p style={{ fontSize: '12px', color: '#e2e8f0', margin: 0 }}>
            Keep your critical business data private. Keep your revenue in your company.
          </p>
        </div>

      </div>
    </div>
  );
}





