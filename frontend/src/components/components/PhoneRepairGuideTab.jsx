import React, { useState, useEffect, useMemo, useRef } from 'react';
import UBreakiFixSOP from './UBreakiFixSOP';
import UBreakiFixPracticePortal from './UBreakiFixPracticePortal';
import UsbFlashRecoveryStation from './UsbFlashRecoveryStation';
import {
  DEFAULT_GUIDES,
  DEFAULT_DIAGNOSTICS,
  DEFAULT_IC_REFERENCES,
  DEFAULT_TOOLS_REF,
  DEFAULT_TICKETS,
  DEFAULT_PART_SKUS,
  DEFAULT_DC_PRESETS,
  DEFAULT_QA_CHECKPOINTS,
  DEFAULT_CHEMICALS_SAFETY
} from '../data/defaultPhoneRepairData';

export default function PhoneRepairGuideTab({ backendUrl }) {
  // Navigation & Station State
  const [activeStation, setActiveStation] = useState('guides'); // 'guides', 'diagnostics', 'ic_lab', 'tools_mat', 'calculator', 'tickets', 'sop_academy', 'practice_sim', 'sku_matrix', 'dc_lab', 'qa_cert', 'chem_safety'
  
  // Data State - Initialized with full offline-first datasets
  const [guides, setGuides] = useState(DEFAULT_GUIDES);
  const [selectedGuide, setSelectedGuide] = useState(DEFAULT_GUIDES[0] || null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [diagnosticTrees, setDiagnosticTrees] = useState(DEFAULT_DIAGNOSTICS);
  const [selectedTree, setSelectedTree] = useState(DEFAULT_DIAGNOSTICS[0] || null);
  const [icReferences, setIcReferences] = useState(DEFAULT_IC_REFERENCES);
  const [toolsRef, setToolsRef] = useState(DEFAULT_TOOLS_REF);
  const [repairTickets, setRepairTickets] = useState(DEFAULT_TICKETS);
  const [loading, setLoading] = useState(false);
  const [qaChecked, setQaChecked] = useState({});

  // Station 9: Part SKUs & Cross-Compatibility State
  const [partSkus, setPartSkus] = useState(DEFAULT_PART_SKUS);
  const [skuSearch, setSkuSearch] = useState('');
  const [selectedSkuCat, setSelectedSkuCat] = useState('all');

  // Station 10: DC Power Supply & Waveform Lab State
  const [dcPresets, setDcPresets] = useState(DEFAULT_DC_PRESETS);
  const [selectedDcPreset, setSelectedDcPreset] = useState(DEFAULT_DC_PRESETS[0]);
  const [customVoltage, setCustomVoltage] = useState(4.2);
  const [customCurrent, setCustomCurrent] = useState(0.000);
  const [isSupplyOn, setIsSupplyOn] = useState(true);

  // Station 11: 24-Point Asurion Audit & QA Certificate Generator State
  const [qaCheckpoints, setQaCheckpoints] = useState(DEFAULT_QA_CHECKPOINTS);
  const [qaAuditStatus, setQaAuditStatus] = useState(() => {
    const s = {};
    DEFAULT_QA_CHECKPOINTS.forEach(q => { s[q.id] = 'pass'; });
    return s;
  });
  const [qaCustomerName, setQaCustomerName] = useState('John Doe');
  const [qaDeviceModel, setQaDeviceModel] = useState('iPhone 15 Pro Max');
  const [qaSerialImei, setQaSerialImei] = useState('359482109482109');
  const [qaTechInitials, setQaTechInitials] = useState('BS');
  const [qaWarrantyMonths, setQaWarrantyMonths] = useState(12);

  // Station 12: Chemical Safety & Thermal MSDS State
  const [chemicalsSafety, setChemicalsSafety] = useState(DEFAULT_CHEMICALS_SAFETY);
  const [activeChemTab, setActiveChemTab] = useState('guide'); // 'guide', 'emergency'

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedRepairType, setSelectedRepairType] = useState('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState('all');

  // Interactive Screw Mat State
  const [screwMatGrid, setScrewMatGrid] = useState(() => {
    const grid = {};
    for (let r = 0; r < 6; r++) {
      for (let c = 0; c < 8; c++) {
        grid[`${r}-${c}`] = null;
      }
    }
    return grid;
  });
  const [selectedScrewColor, setSelectedScrewColor] = useState('#38bdf8'); // Cyan, Red, Green, Yellow, Purple

  // Calculator State
  const [calcModel, setCalcModel] = useState('iPhone 15 Pro Max');
  const [calcPartGrade, setCalcPartGrade] = useState('Soft OLED');
  const [calcPartCost, setCalcPartCost] = useState(75);
  const [calcLaborRate, setCalcLaborRate] = useState(80);
  const [calcCustomerName, setCalcCustomerName] = useState('');
  const [calcPhone, setCalcPhone] = useState('');
  const [calcIssue, setCalcIssue] = useState('Cracked Soft OLED & TrueTone serialization');

  const API_BASE = backendUrl || 'http://127.0.0.1:8080';

  // API Fetchers with offline-first preservation
  const fetchGuides = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/repair/guides`, {
        headers: {
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.guides && data.guides.length > 0) {
          setGuides(data.guides);
          if (!selectedGuide) {
            setSelectedGuide(data.guides[0]);
            setCurrentStepIndex(0);
          }
        }
      }
    } catch (err) {
      console.warn("Backend API offline, using embedded master guides:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDiagnostics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repair/diagnostics`, {
        headers: {
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.diagnostic_trees && data.diagnostic_trees.length > 0) {
          setDiagnosticTrees(data.diagnostic_trees);
          if (!selectedTree) {
            setSelectedTree(data.diagnostic_trees[0]);
          }
        }
      }
    } catch (err) {
      console.warn("Backend API offline, using embedded diagnostic trees:", err);
    }
  };

  const fetchIcReferences = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repair/ic_reference`, {
        headers: {
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.ic_references && data.ic_references.length > 0) {
          setIcReferences(data.ic_references);
        }
      }
    } catch (err) {
      console.warn("Backend API offline, using embedded IC reference:", err);
    }
  };

  const fetchToolsReference = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repair/tools_reference`, {
        headers: {
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.screwdrivers && data.screwdrivers.length > 0) {
          setToolsRef(data);
        }
      }
    } catch (err) {
      console.warn("Backend API offline, using embedded tools reference:", err);
    }
  };

  const fetchTickets = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repair/tickets`, {
        headers: {
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.tickets && data.tickets.length > 0) {
          setRepairTickets(data.tickets);
        }
      }
    } catch (err) {
      console.warn("Backend API offline, using local repair tickets:", err);
    }
  };

  useEffect(() => {
    fetchGuides();
    fetchDiagnostics();
    fetchIcReferences();
    fetchToolsReference();
    fetchTickets();
  }, []);

  // Filtered Guides
  const filteredGuides = useMemo(() => {
    return guides.filter(g => {
      const matchesSearch = searchQuery === '' ||
        g.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.brand.toLowerCase().includes(searchQuery.toLowerCase()) ||
        g.model_range.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCat = selectedCategory === 'all' || g.category === selectedCategory;
      const matchesType = selectedRepairType === 'all' || g.repair_type === selectedRepairType;
      const matchesDiff = selectedDifficulty === 'all' || g.difficulty === selectedDifficulty;

      return matchesSearch && matchesCat && matchesType && matchesDiff;
    });
  }, [guides, searchQuery, selectedCategory, selectedRepairType, selectedDifficulty]);

  // Filtered SKUs
  const filteredSkus = useMemo(() => {
    return partSkus.filter(s => {
      const matchesCat = selectedSkuCat === 'all' || s.category === selectedSkuCat;
      const matchesSearch = skuSearch === '' ||
        s.model.toLowerCase().includes(skuSearch.toLowerCase()) ||
        s.component.toLowerCase().includes(skuSearch.toLowerCase()) ||
        s.oem_sku.toLowerCase().includes(skuSearch.toLowerCase()) ||
        s.compatibility_rule.toLowerCase().includes(skuSearch.toLowerCase());
      return matchesCat && matchesSearch;
    });
  }, [partSkus, skuSearch, selectedSkuCat]);

  const toggleQaAuditPoint = (id, newStatus) => {
    setQaAuditStatus(prev => ({
      ...prev,
      [id]: newStatus
    }));
  };

  const markAllQa = (status) => {
    const s = {};
    qaCheckpoints.forEach(q => { s[q.id] = status; });
    setQaAuditStatus(s);
  };

  useEffect(() => {
    if (filteredGuides.length > 0) {
      if (!selectedGuide || !filteredGuides.some(g => g.id === selectedGuide.id)) {
        setSelectedGuide(filteredGuides[0]);
        setCurrentStepIndex(0);
      }
    }
  }, [filteredGuides, selectedGuide]);

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!calcCustomerName.trim() || !calcModel.trim()) return;

    const totalPrice = Number(calcPartCost) + Number(calcLaborRate);
    try {
      const res = await fetch(`${API_BASE}/api/repair/tickets/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          customer_name: calcCustomerName,
          customer_phone: calcPhone,
          device_category: selectedCategory === 'all' ? 'apple_iphone' : selectedCategory,
          device_model: calcModel,
          reported_issue: calcIssue,
          part_grade_used: calcPartGrade,
          parts_cost_usd: Number(calcPartCost),
          labor_charge_usd: Number(calcLaborRate),
          total_price_usd: totalPrice,
          status: 'Checked-In'
        })
      });
      if (res.ok) {
        alert(`✅ Repair Ticket created successfully for ${calcCustomerName}!`);
        setCalcCustomerName('');
        setCalcPhone('');
        fetchTickets();
        setActiveStation('tickets');
      }
    } catch (err) {
      console.error("Error creating repair ticket:", err);
    }
  };

  const handleUpdateTicketStatus = async (ticketId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE}/api/repair/tickets/${ticketId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        fetchTickets();
      }
    } catch (err) {
      console.error("Error updating ticket status:", err);
    }
  };

  const toggleScrewSlot = (key) => {
    setScrewMatGrid(prev => ({
      ...prev,
      [key]: prev[key] ? null : selectedScrewColor
    }));
  };

  const clearScrewMat = () => {
    const grid = {};
    for (let r = 0; r < 6; r++) {
      for (let c = 0; c < 8; c++) {
        grid[`${r}-${c}`] = null;
      }
    }
    setScrewMatGrid(grid);
  };

  const toggleQaCheck = (idx) => {
    setQaChecked(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  return (
    <div className="aibs-hub-root" style={{
      width: '100%',
      minHeight: '100%',
      background: 'linear-gradient(180deg, #070b12 0%, #04060a 100%)',
      color: '#f1f5f9',
      padding: '24px',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      boxSizing: 'border-box'
    }}>
      {/* Mobile-Friendly Responsive Stylesheet */}
      <style>{`
        .aibs-hub-root {
          box-sizing: border-box;
          max-width: 100vw;
          overflow-x: hidden;
        }
        @media (max-width: 768px) {
          .aibs-hub-root {
            padding: 12px !important;
          }
        }
        .aibs-hub-banner {
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(8, 14, 26, 0.98));
          border: 1px solid rgba(56, 189, 248, 0.35);
          border-radius: 16px;
          padding: 20px 24px;
          margin-bottom: 20px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.6), 0 0 25px rgba(56, 189, 248, 0.12);
        }
        @media (max-width: 768px) {
          .aibs-hub-banner {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 14px !important;
            padding: 16px !important;
          }
        }
        .aibs-hub-ribbon {
          display: flex;
          gap: 8px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          padding-bottom: 14px;
          margin-bottom: 20px;
          overflow-x: auto;
          flex-wrap: nowrap;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: thin;
        }
        @media (min-width: 1400px) {
          .aibs-hub-ribbon {
            flex-wrap: wrap !important;
          }
        }
        .aibs-ribbon-btn {
          white-space: nowrap !important;
          flex-shrink: 0 !important;
          min-height: 42px;
          touch-action: manipulation;
        }
        .aibs-guides-filter-grid {
          display: grid;
          grid-template-columns: 1.4fr 1fr 1fr 1fr;
          gap: 12px;
          align-items: center;
        }
        @media (max-width: 1024px) {
          .aibs-guides-filter-grid {
            grid-template-columns: 1fr 1fr !important;
          }
        }
        @media (max-width: 640px) {
          .aibs-guides-filter-grid {
            grid-template-columns: 1fr !important;
          }
        }
        .aibs-split-340 {
          display: grid;
          grid-template-columns: 340px 1fr;
          gap: 20px;
        }
        @media (max-width: 960px) {
          .aibs-split-340 {
            grid-template-columns: 1fr !important;
          }
        }
        .aibs-split-320 {
          display: grid;
          grid-template-columns: 320px 1fr;
          gap: 20px;
        }
        @media (max-width: 960px) {
          .aibs-split-320 {
            grid-template-columns: 1fr !important;
          }
        }
        .aibs-split-qa {
          display: grid;
          grid-template-columns: 1.2fr 0.8fr;
          gap: 20px;
        }
        @media (max-width: 960px) {
          .aibs-split-qa {
            grid-template-columns: 1fr !important;
          }
        }
        .aibs-split-half {
          display: grid;
          grid-template-columns: 1.2fr 1fr;
          gap: 20px;
        }
        @media (max-width: 900px) {
          .aibs-split-half {
            grid-template-columns: 1fr !important;
          }
        }
        .aibs-mat-scroll-wrap {
          max-width: 100%;
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
          padding-bottom: 6px;
        }
        .aibs-touch-input {
          font-size: 16px !important;
        }
        @media (min-width: 769px) {
          .aibs-touch-input {
            font-size: 0.84rem !important;
          }
        }
      `}</style>

      {/* ========================================================================= */}
      {/* 1. TOP HUB BANNER & STATUS */}
      {/* ========================================================================= */}
      <div className="aibs-hub-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px', flexWrap: 'wrap' }}>
          <div style={{
            width: '52px',
            height: '52px',
            borderRadius: '14px',
            background: 'linear-gradient(135deg, #0284c7, #2563eb)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.75rem',
            boxShadow: '0 0 20px rgba(2, 132, 199, 0.5)',
            flexShrink: 0
          }}>
            🔧
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h1 style={{ margin: 0, fontSize: '1.45rem', fontWeight: 900, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                AI-BS Hardware Master Repair & Diagnostics Hub
              </h1>
              <span style={{ fontSize: '0.7rem', fontWeight: 800, background: 'rgba(56, 189, 248, 0.2)', border: '1px solid #38bdf8', color: '#38bdf8', padding: '2px 8px', borderRadius: '6px' }}>
                v5.296.0 STANDALONE HUB
              </span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.84rem', color: '#94a3b8' }}>
              Master teardowns, Face ID serialization, micro-soldering IC schematics, thermal presets, and profit margin estimation.
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 800,
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#34d399',
            padding: '6px 12px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ fontSize: '0.65rem' }}>🟢</span> NVMe Local Knowledge Active
          </span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 2. HUB WORKSTATION SELECTOR RIBBON */}
      {/* ========================================================================= */}
      <div className="aibs-hub-ribbon">
        {[
          { id: 'guides', icon: '📖', label: `Master Teardowns (${filteredGuides.length})` },
          { id: 'diagnostics', icon: '🩺', label: `Bench Diagnostics (${diagnosticTrees.length})` },
          { id: 'ic_lab', icon: '🔬', label: `Micro-Soldering IC Lab (${icReferences.length})` },
          { id: 'tools_mat', icon: '🧰', label: 'Magnetic Screw Mat & Tools' },
          { id: 'calculator', icon: '💰', label: 'Quote & Profit Calculator' },
          { id: 'tickets', icon: '📋', label: `Work Order Vault (${repairTickets.length})` },
          { id: 'sop_academy', icon: '🏢', label: 'uBreakiFix Academy' },
          { id: 'practice_sim', icon: '⚡', label: 'Intake Practice Simulator' },
          { id: 'sku_matrix', icon: '🔍', label: `Part SKUs & Compatibility (${filteredSkus.length})` },
          { id: 'dc_lab', icon: '⚡', label: 'DC Waveform Simulator' },
          { id: 'qa_cert', icon: '📋', label: '24-Point QA Certificate' },
          { id: 'chem_safety', icon: '🧪', label: 'Chemical Safety & MSDS' },
          { id: 'usb_recovery', icon: '💾', label: 'USB Flash Diagnostics & Flasher' }
        ].map(station => (
          <button
            key={station.id}
            className="aibs-ribbon-btn"
            onClick={() => setActiveStation(station.id)}
            style={{
              background: activeStation === station.id ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(99, 102, 241, 0.25))' : 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${activeStation === station.id ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
              color: activeStation === station.id ? '#ffffff' : '#94a3b8',
              borderRadius: '10px',
              padding: '10px 18px',
              fontSize: '0.86rem',
              fontWeight: activeStation === station.id ? 800 : 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: activeStation === station.id ? '0 0 15px rgba(56, 189, 248, 0.2)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            <span style={{ fontSize: '1.05rem' }}>{station.icon}</span>
            <span>{station.label}</span>
          </button>
        ))}
      </div>

      {/* ========================================================================= */}
      {/* 3. CATEGORIZED DROPDOWNS & UNIVERSAL SEARCH (SHOWN ON GUIDES STATION) */}
      {/* ========================================================================= */}
      {activeStation === 'guides' && (
        <div className="aibs-guides-filter-grid" style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '12px',
          padding: '14px 18px',
          marginBottom: '20px'
        }}>
          {/* Universal Search */}
          <div>
            <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
              🔍 Real-Time Search Query
            </label>
            <input
              type="text"
              className="aibs-touch-input"
              placeholder="Search model, error code, TrueTone, or port..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                background: '#090e17',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                color: '#fff',
                padding: '10px 12px',
                borderRadius: '8px',
                boxSizing: 'border-box'
              }}
            />
          </div>

          {/* Ecosystem / Brand Dropdown */}
          <div>
            <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
              🏷️ Device Ecosystem
            </label>
            <select
              className="aibs-touch-input"
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              style={{
                width: '100%',
                background: '#090e17',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#fff',
                padding: '10px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                boxSizing: 'border-box'
              }}
            >
              <option value="all">📱 All Categories</option>
              <option value="apple_iphone">🍏 Apple iPhone</option>
              <option value="apple_ipad">📱 Apple iPad</option>
              <option value="android_phone">🤖 Android Phones (Samsung / Pixel / Moto)</option>
              <option value="android_tablet">📟 Android Tablets (Galaxy Tab / Fire)</option>
            </select>
          </div>

          {/* Repair Type Dropdown */}
          <div>
            <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
              🛠️ Repair Type
            </label>
            <select
              className="aibs-touch-input"
              value={selectedRepairType}
              onChange={e => setSelectedRepairType(e.target.value)}
              style={{
                width: '100%',
                background: '#090e17',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#fff',
                padding: '10px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                boxSizing: 'border-box'
              }}
            >
              <option value="all">⚡ All Repair Types</option>
              <option value="screen">🖥️ Screen, OLED & Digitizer</option>
              <option value="battery">🔋 Battery & BMS Welding</option>
              <option value="charge_port">🔌 Charge Port & USB-C Dock</option>
              <option value="microsoldering">🔬 Logic Board Micro-Soldering</option>
              <option value="software">💻 Software, Flashing & Unbrick</option>
            </select>
          </div>

          {/* Difficulty Dropdown */}
          <div>
            <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: '4px', fontWeight: 600 }}>
              🎯 Technician Difficulty
            </label>
            <select
              className="aibs-touch-input"
              value={selectedDifficulty}
              onChange={e => setSelectedDifficulty(e.target.value)}
              style={{
                width: '100%',
                background: '#090e17',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#fff',
                padding: '10px 12px',
                borderRadius: '8px',
                cursor: 'pointer',
                boxSizing: 'border-box'
              }}
            >
              <option value="all">All Difficulty Levels</option>
              <option value="Beginner">🟢 Beginner</option>
              <option value="Intermediate">🟡 Intermediate</option>
              <option value="Advanced">🟠 Advanced</option>
              <option value="Master Technician">🔴 Master Technician</option>
            </select>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 1: MASTER TEARDOWNS */}
      {/* ========================================================================= */}
      {activeStation === 'guides' && (
        <div className="aibs-split-340">
          {/* Guide Selector Sidebar */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.75)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderRadius: '14px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            maxHeight: '750px',
            overflowY: 'auto'
          }}>
            <h3 style={{ margin: '0 0 4px 0', fontSize: '0.88rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Filtered Master Guides ({filteredGuides.length})
            </h3>
            {loading ? (
              <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>Loading guides...</div>
            ) : filteredGuides.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                No guides match current dropdown filters.
              </div>
            ) : (
              filteredGuides.map(g => (
                <div
                  key={g.id}
                  onClick={() => {
                    setSelectedGuide(g);
                    setCurrentStepIndex(0);
                    setQaChecked({});
                  }}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '10px',
                    background: selectedGuide?.id === g.id ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(37, 99, 235, 0.15))' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${selectedGuide?.id === g.id ? '#38bdf8' : 'rgba(255, 255, 255, 0.06)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontWeight: 800 }}>{g.brand}</span>
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: g.difficulty === 'Beginner' ? 'rgba(16, 185, 129, 0.2)' :
                                 g.difficulty === 'Intermediate' ? 'rgba(234, 179, 8, 0.2)' :
                                 g.difficulty === 'Advanced' ? 'rgba(249, 115, 22, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                      color: g.difficulty === 'Beginner' ? '#34d399' :
                             g.difficulty === 'Intermediate' ? '#facc15' :
                             g.difficulty === 'Advanced' ? '#fb923c' : '#f87171'
                    }}>
                      {g.difficulty}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#f8fafc', lineHeight: '1.3' }}>
                    {g.title}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '6px' }}>
                    ⏳ ~{g.estimated_time_min} mins • 🔥 {g.heat_temp_c}°C
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Detailed Guide Presentation */}
          {selectedGuide ? (
            <div style={{
              background: 'rgba(15, 23, 42, 0.75)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '14px',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px'
            }}>
              {/* Guide Header */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase' }}>
                      {selectedGuide.model_range}
                    </span>
                    <h2 style={{ margin: '4px 0 0 0', fontSize: '1.35rem', color: '#f8fafc', fontWeight: 800 }}>
                      {selectedGuide.title}
                    </h2>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <span style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700 }}>
                      🔥 Heat Mat: {selectedGuide.heat_temp_c}°C
                    </span>
                    <span style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700 }}>
                      ⏱️ {selectedGuide.estimated_time_min} Mins
                    </span>
                  </div>
                </div>
              </div>

              {/* Tools & Safety Specs */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div style={{ background: '#090e17', border: '1px solid rgba(255, 255, 255, 0.06)', borderRadius: '10px', padding: '14px' }}>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '0.82rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    🧰 Required Screwdrivers & Tools
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                    {selectedGuide.required_tools.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ background: '#090e17', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '10px', padding: '14px' }}>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '0.82rem', color: '#f87171', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    ⚠️ Safety & Damage Prevention Rules
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.78rem', color: '#fca5a5', lineHeight: '1.6' }}>
                    {selectedGuide.safety_precautions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Interactive Step-by-Step Stepper */}
              <div style={{
                background: '#090e17',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: '12px',
                padding: '18px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <span style={{ fontSize: '0.88rem', fontWeight: 800, color: '#38bdf8' }}>
                    STEP {currentStepIndex + 1} OF {selectedGuide.steps.length}: {selectedGuide.steps[currentStepIndex]?.title}
                  </span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      disabled={currentStepIndex === 0}
                      onClick={() => setCurrentStepIndex(prev => Math.max(0, prev - 1))}
                      style={{
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        color: '#fff',
                        borderRadius: '6px',
                        padding: '6px 12px',
                        fontSize: '0.78rem',
                        cursor: currentStepIndex === 0 ? 'not-allowed' : 'pointer',
                        opacity: currentStepIndex === 0 ? 0.4 : 1
                      }}
                    >
                      ◀ Previous
                    </button>
                    <button
                      disabled={currentStepIndex === selectedGuide.steps.length - 1}
                      onClick={() => setCurrentStepIndex(prev => Math.min(selectedGuide.steps.length - 1, prev + 1))}
                      style={{
                        background: '#0284c7',
                        border: 'none',
                        color: '#fff',
                        borderRadius: '6px',
                        padding: '6px 14px',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        cursor: currentStepIndex === selectedGuide.steps.length - 1 ? 'not-allowed' : 'pointer',
                        opacity: currentStepIndex === selectedGuide.steps.length - 1 ? 0.4 : 1
                      }}
                    >
                      Next Step ▶
                    </button>
                  </div>
                </div>

                <div style={{ fontSize: '0.9rem', color: '#f1f5f9', lineHeight: '1.65', background: 'rgba(15, 23, 42, 0.85)', padding: '18px', borderRadius: '8px', borderLeft: '4px solid #38bdf8' }}>
                  {selectedGuide.steps[currentStepIndex]?.instructions}
                </div>
              </div>

              {/* Pro Tips Box */}
              {selectedGuide.pro_tips?.length > 0 && (
                <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '10px', padding: '14px' }}>
                  <h4 style={{ margin: '0 0 6px 0', fontSize: '0.84rem', color: '#34d399' }}>💡 Master Technician Pro Tips</h4>
                  {selectedGuide.pro_tips.map((tip, i) => (
                    <div key={i} style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.5' }}>
                      • {tip}
                    </div>
                  ))}
                </div>
              )}

              {/* Post-Repair QA Checklist */}
              <div style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.88rem', color: '#f8fafc' }}>
                  📋 18-Point Post-Repair Quality Assurance (QA) Checklist
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {selectedGuide.post_qa_checklist.map((item, idx) => (
                    <label key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: qaChecked[idx] ? '#34d399' : '#94a3b8', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={!!qaChecked[idx]}
                        onChange={() => toggleQaCheck(idx)}
                      />
                      <span>{item}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
              Select a repair guide from the sidebar
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 2: BENCH DIAGNOSTICS */}
      {/* ========================================================================= */}
      {activeStation === 'diagnostics' && (
        <div className="aibs-split-320">
          <div style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <h3 style={{ margin: '0 0 6px 0', fontSize: '0.88rem', color: '#94a3b8', textTransform: 'uppercase' }}>
              Diagnostic Symptoms
            </h3>
            {diagnosticTrees.map(tree => (
              <div
                key={tree.id}
                onClick={() => setSelectedTree(tree)}
                style={{
                  padding: '12px 14px',
                  borderRadius: '10px',
                  background: selectedTree?.id === tree.id ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(37, 99, 235, 0.15))' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${selectedTree?.id === tree.id ? '#38bdf8' : 'rgba(255, 255, 255, 0.06)'}`,
                  cursor: 'pointer'
                }}
              >
                <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#f8fafc' }}>
                  {tree.symptom}
                </div>
              </div>
            ))}
          </div>

          {selectedTree && (
            <div style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <h2 style={{ margin: 0, fontSize: '1.3rem', color: '#38bdf8', fontWeight: 800 }}>
                Diagnostic Tree: {selectedTree.symptom}
              </h2>

              {/* Primary Suspects */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 700 }}>Primary Suspects:</span>
                {selectedTree.primary_suspects.map((s, i) => (
                  <span key={i} style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.74rem' }}>
                    {s}
                  </span>
                ))}
              </div>

              {/* DC Bench Current Draw Analysis */}
              <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '10px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.88rem', color: '#38bdf8' }}>
                  ⚡ DC Power Supply Bench Current Draw Indicators
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {selectedTree.current_draw_analysis.map((c, i) => (
                    <div key={i} style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: '12px', fontSize: '0.8rem', background: 'rgba(255,255,255,0.02)', padding: '10px 14px', borderRadius: '6px' }}>
                      <span style={{ color: '#facc15', fontWeight: 800 }}>{c.draw}</span>
                      <span style={{ color: '#cbd5e1' }}>{c.cause}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Multimeter Probe Steps */}
              <div style={{ background: '#090e17', border: '1px solid rgba(168, 85, 247, 0.25)', borderRadius: '10px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.88rem', color: '#c084fc' }}>
                  📟 Multimeter Diode Mode Probe Steps
                </h4>
                <ol style={{ margin: 0, paddingLeft: '20px', fontSize: '0.82rem', color: '#cbd5e1', lineHeight: '1.65' }}>
                  {selectedTree.multimeter_probe_steps.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ol>
              </div>

              {/* Resolution Pathways */}
              <div style={{ background: '#090e17', border: '1px solid rgba(52, 211, 153, 0.25)', borderRadius: '10px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.88rem', color: '#34d399' }}>
                  🛠️ Recommended Resolution Pathways
                </h4>
                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.82rem', color: '#cbd5e1', lineHeight: '1.65' }}>
                  {selectedTree.resolution_pathways.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 3: MICRO-SOLDERING IC REFERENCE LAB */}
      {/* ========================================================================= */}
      {activeStation === 'ic_lab' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '14px', padding: '20px' }}>
            <h2 style={{ margin: '0 0 6px 0', fontSize: '1.25rem', color: '#c084fc' }}>
              🔬 Micro-Soldering IC Reference Catalog & Diode Pinouts
            </h2>
            <p style={{ margin: 0, fontSize: '0.82rem', color: '#94a3b8' }}>
              Cross-reference symptoms to specific BGA chips, expected diode mode voltage drops, and soldering temperatures.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '16px' }}>
            {icReferences.map(ic => (
              <div key={ic.id} style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '12px', padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#f8fafc', fontWeight: 800 }}>{ic.chip_name}</h3>
                    <div style={{ display: 'flex', gap: '4px', marginTop: '6px', flexWrap: 'wrap' }}>
                      {ic.part_numbers.map((p, i) => (
                        <span key={i} style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '1px 6px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 700 }}>
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span style={{ fontSize: '0.68rem', background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                    {ic.replacement_difficulty}
                  </span>
                </div>

                <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.5' }}>
                  {ic.function_description}
                </div>

                <div style={{ background: '#090e17', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <span style={{ fontSize: '0.72rem', color: '#facc15', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                    ⚠️ Common Failure Symptoms:
                  </span>
                  <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.75rem', color: '#94a3b8', lineHeight: '1.5' }}>
                    {ic.common_symptoms.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ background: '#090e17', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(168, 85, 247, 0.2)' }}>
                  <span style={{ fontSize: '0.72rem', color: '#c084fc', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                    📟 Expected Diode Mode Values:
                  </span>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '0.74rem' }}>
                    {Object.entries(ic.expected_diode_readings).map(([rail, val]) => (
                      <div key={rail} style={{ color: '#cbd5e1' }}>
                        {rail}: <strong style={{ color: '#34d399' }}>{val}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 4: INTERACTIVE MAGNETIC SCREW MAT & TOOLS */}
      {/* ========================================================================= */}
      {activeStation === 'tools_mat' && (
        <div className="aibs-split-half">
          {/* Interactive Screw Organizer Mat */}
          <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '14px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#38bdf8', fontWeight: 800 }}>
                  🧲 Interactive Magnetic Screw Organizer Mat
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Click grid slots to organize screws during teardown and prevent Long-Screw Damage.
                </span>
              </div>
              <button
                onClick={clearScrewMat}
                style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.4)', color: '#f87171', padding: '4px 10px', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
              >
                Clear Mat
              </button>
            </div>

            {/* Screw Color Selector */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', alignItems: 'center', overflowX: 'auto', paddingBottom: '4px' }}>
              <span style={{ fontSize: '0.75rem', color: '#cbd5e1', whiteSpace: 'nowrap' }}>Pin Color:</span>
              {[
                { color: '#38bdf8', label: '1.2mm' },
                { color: '#f87171', label: '1.5mm' },
                { color: '#34d399', label: '3.0mm' },
                { color: '#facc15', label: 'Standoff' },
                { color: '#c084fc', label: 'Tri-Point' }
              ].map(c => (
                <button
                  key={c.color}
                  onClick={() => setSelectedScrewColor(c.color)}
                  style={{
                    background: selectedScrewColor === c.color ? c.color : 'rgba(255,255,255,0.06)',
                    color: selectedScrewColor === c.color ? '#000' : '#fff',
                    border: `1px solid ${c.color}`,
                    borderRadius: '6px',
                    padding: '4px 10px',
                    fontSize: '0.74rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {c.label}
                </button>
              ))}
            </div>

            {/* Magnetic Grid (6x8) Wrapped in Mobile Scroll Container */}
            <div className="aibs-mat-scroll-wrap">
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(8, minmax(36px, 1fr))',
                gap: '6px',
                background: '#04060a',
                padding: '12px',
                borderRadius: '10px',
                border: '1px dashed rgba(56, 189, 248, 0.3)',
                minWidth: '320px'
              }}>
              {Object.keys(screwMatGrid).map(k => (
                <div
                  key={k}
                  onClick={() => toggleScrewSlot(k)}
                  style={{
                    height: '42px',
                    borderRadius: '6px',
                    background: screwMatGrid[k] || 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    boxShadow: screwMatGrid[k] ? `0 0 10px ${screwMatGrid[k]}` : 'none',
                    transition: 'all 0.1s ease'
                  }}
                >
                  {screwMatGrid[k] ? (
                    <span style={{ fontSize: '0.8rem' }}>🔩</span>
                  ) : (
                    <span style={{ fontSize: '0.55rem', color: '#475569' }}>{k}</span>
                  )}
                </div>
              ))}
            </div>
            </div>
          </div>

          {/* Tools & Thermal Reference */}
          {toolsRef && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '12px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '0.88rem', color: '#f87171' }}>🔥 Thermal Mat Temperature Presets</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {toolsRef.thermal_presets.map((t, i) => (
                    <div key={i} style={{ background: '#090e17', padding: '8px 10px', borderRadius: '6px', fontSize: '0.76rem', display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#cbd5e1' }}>{t.substrate}</span>
                      <strong style={{ color: '#f87171' }}>{t.temp_c}°C ({t.time_min}m)</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '12px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '0.88rem', color: '#34d399' }}>🧪 Chemical & Adhesive Guidelines</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {toolsRef.chemicals_and_adhesives.map((c, i) => (
                    <div key={i} style={{ background: '#090e17', padding: '8px 10px', borderRadius: '6px', fontSize: '0.74rem' }}>
                      <strong style={{ color: '#34d399' }}>{c.chemical}:</strong> <span style={{ color: '#94a3b8' }}>{c.usage}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 5: REPAIR QUOTE & PROFIT CALCULATOR */}
      {/* ========================================================================= */}
      {activeStation === 'calculator' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Quick Pricing Presets Header Bar */}
          <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
              <span style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                ⚡ 1-Click Asurion & Walk-In Pricing Presets (2024–2025 Industry Standards)
              </span>
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Click any preset to auto-fill parts, labor & model</span>
            </div>

            {/* Asurion Insurance Deductibles */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '0.72rem', color: '#34d399', fontWeight: 700, marginBottom: '6px' }}>🛡️ Asurion Insurance Claims:</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  { label: '$0 Glass / Battery Claim', model: 'Asurion Insured Device', part: 0, labor: 0, grade: 'OEM Refurb / Pull', issue: 'Asurion $0 Deductible Front Glass / Battery Replacement' },
                  { label: '$29 Screen Claim', model: 'iPhone / Galaxy (Asurion)', part: 0, labor: 29, grade: 'OEM Refurb / Pull', issue: 'Asurion $29 Deductible Screen Claim' },
                  { label: '$99 Tier 1 Replacement', model: 'Standard / Budget Phone', part: 0, labor: 99, grade: 'OEM Refurb / Pull', issue: 'Asurion Tier 1 BER / Whole Unit Replacement ($99)' },
                  { label: '$249 Tier 2/3 Flagship WUR', model: 'iPhone Pro Max / Ultra / Fold', part: 0, labor: 249, grade: 'OEM Refurb / Pull', issue: 'Asurion Tier 2/3 Flagship WUR Replacement ($249)' },
                  { label: '$99 Home+ Claim', model: 'Laptop / Tablet / Console', part: 0, labor: 99, grade: 'OEM Refurb / Pull', issue: 'Asurion Home+ $99 Flat Service Fee' }
                ].map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setCalcModel(p.model);
                      setCalcPartCost(p.part);
                      setCalcLaborRate(p.labor);
                      setCalcPartGrade(p.grade);
                      setCalcIssue(p.issue);
                    }}
                    style={{ background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#34d399', borderRadius: '6px', padding: '6px 10px', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Walk-In Smartphones */}
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontSize: '0.72rem', color: '#38bdf8', fontWeight: 700, marginBottom: '6px' }}>📱 Walk-In Smartphones (Retail):</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  { label: 'iPhone 11-13 Screen ($149)', model: 'iPhone 13', part: 50, labor: 99, grade: 'Soft OLED', issue: 'Cracked Screen Replacement (Aftermarket Soft OLED)' },
                  { label: 'iPhone 14-16 Screen ($299)', model: 'iPhone 15 Pro', part: 120, labor: 179, grade: 'Soft OLED', issue: 'Cracked OLED Screen Replacement' },
                  { label: 'Samsung Galaxy Base ($229)', model: 'Samsung Galaxy S23', part: 130, labor: 99, grade: 'OEM Refurb / Pull', issue: 'Samsung OEM Service Pack Chassis & Display Swap' },
                  { label: 'Samsung Ultra ($369)', model: 'Samsung Galaxy S24 Ultra', part: 220, labor: 149, grade: 'OEM Refurb / Pull', issue: 'Samsung Ultra Dynamic AMOLED Service Pack' },
                  { label: 'Samsung Z Fold/Flip ($499)', model: 'Samsung Galaxy Z Fold 5', part: 320, labor: 179, grade: 'OEM Refurb / Pull', issue: 'Foldable Inner Screen Replacement' },
                  { label: 'Google Pixel 6-7 Screen ($189)', model: 'Google Pixel 7', part: 90, labor: 99, grade: 'Soft OLED', issue: 'Pixel OLED Replacement & Optical Fingerprint Calibration' },
                  { label: 'Google Pixel 8-9 Pro ($299)', model: 'Google Pixel 9 Pro', part: 160, labor: 139, grade: 'OEM Refurb / Pull', issue: 'Pixel Pro OLED Screen Replacement' }
                ].map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setCalcModel(p.model);
                      setCalcPartCost(p.part);
                      setCalcLaborRate(p.labor);
                      setCalcPartGrade(p.grade);
                      setCalcIssue(p.issue);
                    }}
                    style={{ background: 'rgba(56, 189, 248, 0.12)', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#38bdf8', borderRadius: '6px', padding: '6px 10px', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tablets, Computers & Consoles */}
            <div>
              <div style={{ fontSize: '0.72rem', color: '#c084fc', fontWeight: 700, marginBottom: '6px' }}>🎮 Tablets, Computers & Game Consoles:</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {[
                  { label: 'iPad Glass Only ($139)', model: 'iPad 9th Gen (10.2")', part: 25, labor: 114, grade: 'Incell LCD', issue: 'Air-gap Digitizer Glass Separation & Frame Straightening' },
                  { label: 'iPad Pro Laminated ($329)', model: 'iPad Pro 11"', part: 160, labor: 169, grade: 'Soft OLED', issue: 'Fused Laminated Screen Assembly Replacement' },
                  { label: 'PS5/Xbox HDMI Port ($179)', model: 'Sony PlayStation 5', part: 15, labor: 164, grade: 'OEM Refurb / Pull', issue: 'Tier-3 Micro-soldering HDMI Port Replacement' },
                  { label: 'Console Deep Clean & Paste ($99)', model: 'Xbox Series X / PS5', part: 10, labor: 89, grade: 'OEM Refurb / Pull', issue: 'Deep Heatsink De-dusting & Thermal Paste Application' },
                  { label: 'Laptop Screen ($220)', model: 'Dell / HP / Lenovo Laptop', part: 80, labor: 140, grade: 'Incell LCD', issue: 'Laptop 1080p LED/IPS Display Replacement' },
                  { label: 'OS Reinstall / Virus ($119)', model: 'Windows PC / MacBook', part: 0, labor: 119, grade: 'OEM Refurb / Pull', issue: 'Clean OS Reinstall, Driver Updates & Virus Removal' },
                  { label: 'Data Recovery Temp Boot ($275)', model: 'Dead Motherboard (Data Retrieval)', part: 25, labor: 250, grade: 'OEM Refurb / Pull', issue: 'Board-level Micro-soldering & Bypass Jumpers for Temporary Boot' }
                ].map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setCalcModel(p.model);
                      setCalcPartCost(p.part);
                      setCalcLaborRate(p.labor);
                      setCalcPartGrade(p.grade);
                      setCalcIssue(p.issue);
                    }}
                    style={{ background: 'rgba(168, 85, 247, 0.12)', border: '1px solid rgba(168, 85, 247, 0.3)', color: '#c084fc', borderRadius: '6px', padding: '6px 10px', fontSize: '0.74rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="aibs-split-half">
            <form onSubmit={handleCreateTicket} style={{ background: 'rgba(15, 23, 42, 0.85)', border: '1px solid rgba(56, 189, 248, 0.35)', borderRadius: '14px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#38bdf8', fontWeight: 800 }}>💰 Repair Cost & Profit Margin Calculator</h3>

              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Customer Full Name</label>
                <input
                  type="text"
                  placeholder="e.g. John Doe"
                  value={calcCustomerName}
                  onChange={e => setCalcCustomerName(e.target.value)}
                  style={{ width: '100%', background: '#090e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Customer Phone</label>
                  <input
                    type="text"
                    placeholder="(616) 555-0199"
                    value={calcPhone}
                    onChange={e => setCalcPhone(e.target.value)}
                    style={{ width: '100%', background: '#090e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Device Model</label>
                  <input
                    type="text"
                    placeholder="e.g. iPhone 15 Pro Max"
                    value={calcModel}
                    onChange={e => setCalcModel(e.target.value)}
                    style={{ width: '100%', background: '#090e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Part Quality Grade</label>
                  <select
                    value={calcPartGrade}
                    onChange={e => setCalcPartGrade(e.target.value)}
                    style={{ width: '100%', background: '#090e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                  >
                    <option value="Incell LCD">Incell LCD (Budget / $35)</option>
                    <option value="Hard OLED">Hard OLED (Mid-tier / $50)</option>
                    <option value="Soft OLED">Soft OLED (OEM Equivalent / $75)</option>
                    <option value="OEM Refurb / Pull">OEM Original Pull / Service Pack ($120+)</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Reported Issue</label>
                  <input
                    type="text"
                    value={calcIssue}
                    onChange={e => setCalcIssue(e.target.value)}
                    style={{ width: '100%', background: '#090e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Parts Cost ($ USD)</label>
                  <input
                    type="number"
                    value={calcPartCost}
                    onChange={e => setCalcPartCost(e.target.value)}
                    style={{ width: '100%', background: '#090e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Labor Fee ($ USD)</label>
                  <input
                    type="number"
                    value={calcLaborRate}
                    onChange={e => setCalcLaborRate(e.target.value)}
                    style={{ width: '100%', background: '#090e17', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '8px 12px', borderRadius: '8px', fontSize: '0.85rem' }}
                  />
                </div>
              </div>

              <button
                type="submit"
                style={{
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  color: '#fff',
                  border: 'none',
                  padding: '12px',
                  borderRadius: '8px',
                  fontSize: '0.92rem',
                  fontWeight: 800,
                  cursor: 'pointer',
                  marginTop: '10px'
                }}
              >
                📥 Create & Log Repair Ticket
              </button>
            </form>

            {/* Real-time Profit & Margin Summary Card */}
            <div style={{ background: 'rgba(15, 23, 42, 0.85)', border: '1px solid rgba(52, 211, 153, 0.35)', borderRadius: '14px', padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <h3 style={{ margin: '0 0 16px 0', fontSize: '1.15rem', color: '#34d399', fontWeight: 800 }}>📊 Financial Margin Breakdown</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem' }}>
                    <span style={{ color: '#94a3b8' }}>Wholesale Part Cost:</span>
                    <span style={{ color: '#f87171', fontWeight: 700 }}>${Number(calcPartCost).toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem' }}>
                    <span style={{ color: '#94a3b8' }}>Shop Labor Charge:</span>
                    <span style={{ color: '#38bdf8', fontWeight: 700 }}>${Number(calcLaborRate).toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1.15rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '12px' }}>
                    <span style={{ color: '#f8fafc', fontWeight: 800 }}>Total Customer Quote:</span>
                    <span style={{ color: '#34d399', fontWeight: 900 }}>
                      ${(Number(calcPartCost) + Number(calcLaborRate)).toFixed(2)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem' }}>
                    <span style={{ color: '#94a3b8' }}>Net Gross Profit:</span>
                    <span style={{ color: '#34d399', fontWeight: 700 }}>${Number(calcLaborRate).toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem' }}>
                    <span style={{ color: '#94a3b8' }}>Profit Margin:</span>
                    <span style={{ color: '#34d399', fontWeight: 800 }}>
                      {((Number(calcLaborRate) / (Number(calcPartCost) + Number(calcLaborRate) || 1)) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Policy Quick Cards & Script */}
              <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '12px', fontSize: '0.76rem', color: '#94a3b8' }}>
                  🛡️ <strong>Store Guarantees:</strong> <strong>1. Free Diagnostics ($0)</strong> • <strong>2. $5 Price Match Guarantee</strong> • <strong>3. No Fix, No Fee</strong>
                </div>

                <div style={{ background: 'rgba(168, 85, 247, 0.1)', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '8px', padding: '12px', fontSize: '0.78rem', color: '#cbd5e1' }}>
                  🗣️ <strong>Price Shock Script:</strong> <em>"I understand that price feels high. Because we are an Authorized Service Center, you get a brand new screen pre-built into a new metal frame, calibrated fingerprint sensor, and 1-year nationwide warranty."</em>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 6: WORK ORDER & REPAIR TICKET VAULT */}
      {/* ========================================================================= */}
      {activeStation === 'tickets' && (
        <div style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#f8fafc', fontWeight: 800 }}>
              📋 Shop Work Order & Repair Tickets ({repairTickets.length})
            </h3>
            <button
              onClick={() => setActiveStation('calculator')}
              style={{ background: '#0284c7', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer' }}
            >
              ➕ Check In New Repair
            </button>
          </div>

          {repairTickets.length === 0 ? (
            <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
              No repair tickets created yet. Use the Quote & Profit Calculator to check in a repair.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {repairTickets.map(t => (
                <div key={t.ticket_id} style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ color: '#38bdf8', fontWeight: 900, fontSize: '0.9rem' }}>#{t.ticket_id}</span>
                      <span style={{ color: '#f8fafc', fontWeight: 700, fontSize: '0.95rem' }}>{t.customer_name}</span>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>({t.customer_phone || 'No Phone'})</span>
                    </div>
                    <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '6px' }}>
                      Device: <strong>{t.device_model}</strong> • Issue: {t.reported_issue} • Part: {t.part_grade_used}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '1.05rem', fontWeight: 900, color: '#34d399' }}>${t.total_price_usd.toFixed(2)}</div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Cost: ${t.parts_cost_usd} • Labor: ${t.labor_charge_usd}</div>
                    </div>

                    {/* Status Lifecycle Dropdown */}
                    <select
                      value={t.status}
                      onChange={e => handleUpdateTicketStatus(t.ticket_id, e.target.value)}
                      style={{
                        background: t.status === 'Completed' || t.status === 'Picked Up' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.15)',
                        color: t.status === 'Completed' || t.status === 'Picked Up' ? '#34d399' : '#38bdf8',
                        border: `1px solid ${t.status === 'Completed' || t.status === 'Picked Up' ? '#10b981' : '#38bdf8'}`,
                        padding: '6px 12px',
                        borderRadius: '6px',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      <option value="Checked-In">Checked-In</option>
                      <option value="Diagnosing">Diagnosing</option>
                      <option value="Awaiting Parts">Awaiting Parts</option>
                      <option value="In Repair">In Repair</option>
                      <option value="Testing QA">Testing QA</option>
                      <option value="Completed">Completed</option>
                      <option value="Picked Up">Picked Up</option>
                    </select>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {/* ========================================================================= */}
      {/* STATION 7: UBREAKIFIX ACADEMY & SOPs */}
      {/* ========================================================================= */}
      {activeStation === 'sop_academy' && (
        <UBreakiFixSOP />
      )}

      {/* ========================================================================= */}
      {/* STATION 8: INTAKE PRACTICE SIMULATOR */}
      {/* ========================================================================= */}
      {activeStation === 'practice_sim' && (
        <UBreakiFixPracticePortal />
      )}

      {/* ========================================================================= */}
      {/* STATION 9: PART SKUS & CROSS-COMPATIBILITY MATRIX */}
      {/* ========================================================================= */}
      {activeStation === 'sku_matrix' && (
        <div style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 800 }}>
                🔍 Part SKUs & Cross-Compatibility Matrix ({filteredSkus.length})
              </h3>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                Verify OEM part interchangeability, display connector pinouts, and aftermarket quality grade tiers.
              </p>
            </div>
            
            {/* Search & Ecosystem Filters */}
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Search model, SKU, or rule..."
                value={skuSearch}
                onChange={e => setSkuSearch(e.target.value)}
                style={{
                  background: '#090e17',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  color: '#fff',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  minWidth: '220px'
                }}
              />
              <select
                value={selectedSkuCat}
                onChange={e => setSelectedSkuCat(e.target.value)}
                style={{
                  background: '#090e17',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#fff',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Ecosystems</option>
                <option value="apple_iphone">🍏 Apple iPhone</option>
                <option value="apple_ipad">📱 Apple iPad</option>
                <option value="android_phone">🤖 Android Phone</option>
                <option value="consoles_computers">🎮 Consoles & PC</option>
              </select>
            </div>
          </div>

          {/* SKU Cards Grid */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {filteredSkus.map(sku => (
              <div key={sku.id} style={{
                background: '#090e17',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '12px',
                padding: '18px 22px',
                boxShadow: '0 4px 15px rgba(0,0,0,0.4)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '1.1rem', fontWeight: 900, color: '#38bdf8' }}>{sku.model}</span>
                      <span style={{ fontSize: '0.75rem', fontWeight: 800, background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px' }}>
                        {sku.component}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '4px', fontFamily: 'monospace' }}>
                      OEM SKU: {sku.oem_sku}
                    </div>
                  </div>
                </div>

                {/* Compatibility Rule */}
                <div style={{
                  background: sku.compatibility_rule.includes('NOT') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                  border: `1px solid ${sku.compatibility_rule.includes('NOT') ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '0.84rem',
                  color: sku.compatibility_rule.includes('NOT') ? '#fca5a5' : '#86efac',
                  marginBottom: '14px',
                  lineHeight: '1.4'
                }}>
                  {sku.compatibility_rule}
                </div>

                {/* Quality Grades Matrix */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginBottom: '12px' }}>
                  {sku.grades.map((g, idx) => (
                    <div key={idx} style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      borderRadius: '8px',
                      padding: '10px 12px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#f8fafc' }}>{g.grade}</span>
                        <span style={{ fontSize: '0.75rem', color: '#eab308' }}>{g.rating}</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 700 }}>
                        Cost: {g.cost_range}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: '#94a3b8', marginTop: '4px', lineHeight: '1.3' }}>
                        {g.pros}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pitfalls & Technician Warning */}
                {sku.pitfalls && (
                  <div style={{ fontSize: '0.76rem', color: '#cbd5e1', background: 'rgba(234, 179, 8, 0.08)', border: '1px solid rgba(234, 179, 8, 0.2)', padding: '8px 12px', borderRadius: '6px' }}>
                    💡 <strong>Tech Advisory:</strong> {sku.pitfalls}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 10: DC POWER SUPPLY & CURRENT DRAW WAVEFORM LAB */}
      {/* ========================================================================= */}
      {activeStation === 'dc_lab' && (
        <div style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 800 }}>
                ⚡ DC Bench Power Supply & Waveform Diagnostic Lab
              </h3>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                Simulate motherboard current draw curves, detect VDD_MAIN shorts, and verify diode mode multimeter probe points.
              </p>
            </div>
            <button
              onClick={() => setIsSupplyOn(!isSupplyOn)}
              style={{
                background: isSupplyOn ? '#ef4444' : '#10b981',
                color: '#fff',
                border: 'none',
                padding: '8px 18px',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: 800,
                cursor: 'pointer'
              }}
            >
              {isSupplyOn ? '🛑 CUT POWER' : '⚡ OUTPUT ON'}
            </button>
          </div>

          <div className="aibs-split-320">
            {/* Left: Digital Bench Power Supply Panel */}
            <div style={{ background: '#090e17', border: '2px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ fontSize: '0.78rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 800 }}>
                🎛️ Digital Bench Supply (4-Digit)
              </div>

              {/* 7-Segment Style LED Readout */}
              <div style={{ background: '#020617', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '8px', padding: '16px', textAlign: 'center' }}>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '2px' }}>VOLTAGE (V)</div>
                <div style={{ fontFamily: 'monospace', fontSize: '2.2rem', fontWeight: 900, color: isSupplyOn ? '#38bdf8' : '#334155', letterSpacing: '2px' }}>
                  {isSupplyOn ? selectedDcPreset.voltage.toFixed(2) : '0.00'} V
                </div>

                <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '10px', marginBottom: '2px' }}>CURRENT (A)</div>
                <div style={{ fontFamily: 'monospace', fontSize: '2.2rem', fontWeight: 900, color: !isSupplyOn ? '#334155' : selectedDcPreset.current_amp > 1.5 ? '#ef4444' : selectedDcPreset.current_amp > 0.1 ? '#facc15' : '#34d399', letterSpacing: '2px' }}>
                  {isSupplyOn ? selectedDcPreset.current_amp.toFixed(3) : '0.000'} A
                </div>

                <div style={{ marginTop: '8px', fontSize: '0.74rem', color: '#94a3b8' }}>
                  POWER: <strong>{isSupplyOn ? (selectedDcPreset.voltage * selectedDcPreset.current_amp).toFixed(2) : '0.00'} W</strong>
                </div>
              </div>

              {/* Presets List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '0.74rem', color: '#94a3b8', fontWeight: 700 }}>Signature Fault Presets:</div>
                {dcPresets.map(p => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedDcPreset(p)}
                    style={{
                      background: selectedDcPreset.id === p.id ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                      border: `1px solid ${selectedDcPreset.id === p.id ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
                      color: selectedDcPreset.id === p.id ? '#ffffff' : '#94a3b8',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      textAlign: 'left',
                      fontSize: '0.8rem',
                      fontWeight: selectedDcPreset.id === p.id ? 700 : 500,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Right: Detailed Diagnostic Analysis */}
            <div style={{ background: '#090e17', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f8fafc' }}>
                  {selectedDcPreset.primary_fault}
                </span>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 800,
                  padding: '3px 8px',
                  borderRadius: '6px',
                  background: selectedDcPreset.status_type === 'short' ? 'rgba(239, 68, 68, 0.2)' :
                             selectedDcPreset.status_type === 'bootloop' ? 'rgba(249, 115, 22, 0.2)' :
                             selectedDcPreset.status_type === 'leak' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                  color: selectedDcPreset.status_type === 'short' ? '#f87171' :
                         selectedDcPreset.status_type === 'bootloop' ? '#fb923c' :
                         selectedDcPreset.status_type === 'leak' ? '#facc15' : '#38bdf8'
                }}>
                  {selectedDcPreset.status_type.toUpperCase()}
                </span>
              </div>

              {/* Waveform Behavior Summary */}
              <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.06)', borderRadius: '8px', padding: '12px 14px' }}>
                <div style={{ fontSize: '0.74rem', color: '#94a3b8', fontWeight: 700, marginBottom: '2px' }}>📊 Oscilloscope Curve Behavior:</div>
                <div style={{ fontSize: '0.84rem', color: '#38bdf8', fontWeight: 600 }}>{selectedDcPreset.waveform}</div>
              </div>

              {/* Probable Root Causes */}
              <div>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 700, marginBottom: '6px' }}>🔍 Probable Root Causes:</div>
                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.82rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {selectedDcPreset.root_causes.map((rc, idx) => (
                    <li key={idx}>{rc}</li>
                  ))}
                </ul>
              </div>

              {/* Multimeter Diode Mode Probe Table */}
              <div>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 700, marginBottom: '6px' }}>🔬 Multimeter Diode Mode Test Points (Red Probe on Ground):</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {selectedDcPreset.probe_points.map((pt, idx) => (
                    <div key={idx} style={{ background: '#020617', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '6px', padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 700, fontFamily: 'monospace' }}>{pt.rail}</span>
                      <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>{pt.test_step}</span>
                      <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 800, fontFamily: 'monospace' }}>{pt.expected_diode}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Step-by-Step Resolution */}
              <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '8px', padding: '12px 14px' }}>
                <div style={{ fontSize: '0.76rem', color: '#34d399', fontWeight: 800, marginBottom: '4px' }}>🛠️ Resolution Pathway:</div>
                <div style={{ fontSize: '0.82rem', color: '#f1f5f9', lineHeight: '1.4' }}>{selectedDcPreset.resolution}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 11: 24-POINT ASURION AUDIT & QA CERTIFICATE GENERATOR */}
      {/* ========================================================================= */}
      {activeStation === 'qa_cert' && (
        <div style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 800 }}>
                📋 24-Point Asurion Audit & QA Inspection Certificate
              </h3>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                Execute the standard 24-point pre/post IQC inspection and generate official customer handoff certificates.
              </p>
            </div>
            
            {/* Quick Action Buttons */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => markAllQa('pass')}
                style={{ background: '#0284c7', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer' }}
              >
                ✅ Pass All (24/24)
              </button>
              <button
                onClick={() => markAllQa('fail')}
                style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '1px solid #ef4444', padding: '6px 14px', borderRadius: '6px', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer' }}
              >
                ⚠️ Reset All
              </button>
            </div>
          </div>

          <div className="aibs-split-qa">
            {/* Left: 24-Point Checklist */}
            <div style={{ background: '#090e17', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '12px', padding: '16px', maxHeight: '720px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {qaCheckpoints.map(chk => (
                <div key={chk.id} style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '12px'
                }}>
                  <div>
                    <div style={{ fontSize: '0.72rem', color: '#38bdf8', fontWeight: 700 }}>{chk.group}</div>
                    <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#f8fafc' }}>{chk.name}</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '2px' }}>{chk.desc}</div>
                  </div>

                  {/* Status Toggle Buttons */}
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button
                      onClick={() => toggleQaAuditPoint(chk.id, 'pass')}
                      style={{
                        background: qaAuditStatus[chk.id] === 'pass' ? '#10b981' : 'rgba(255, 255, 255, 0.05)',
                        color: '#fff',
                        border: 'none',
                        padding: '4px 10px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      PASS
                    </button>
                    <button
                      onClick={() => toggleQaAuditPoint(chk.id, 'fail')}
                      style={{
                        background: qaAuditStatus[chk.id] === 'fail' ? '#ef4444' : 'rgba(255, 255, 255, 0.05)',
                        color: '#fff',
                        border: 'none',
                        padding: '4px 10px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      FAIL
                    </button>
                    <button
                      onClick={() => toggleQaAuditPoint(chk.id, 'na')}
                      style={{
                        background: qaAuditStatus[chk.id] === 'na' ? '#64748b' : 'rgba(255, 255, 255, 0.05)',
                        color: '#fff',
                        border: 'none',
                        padding: '4px 10px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      N/A
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Right: Customer Handout Warranty Certificate Card */}
            <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ textAlign: 'center', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 900, color: '#38bdf8' }}>UBREAKIFIX / ASURION</div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Certificate of Quality Assurance
                </div>
              </div>

              {/* Editable Fields */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Customer Name:</label>
                  <input
                    type="text"
                    value={qaCustomerName}
                    onChange={e => setQaCustomerName(e.target.value)}
                    style={{ width: '100%', background: '#020617', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#fff', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Device Model:</label>
                  <input
                    type="text"
                    value={qaDeviceModel}
                    onChange={e => setQaDeviceModel(e.target.value)}
                    style={{ width: '100%', background: '#020617', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#fff', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#94a3b8' }}>IMEI / Serial Number:</label>
                  <input
                    type="text"
                    value={qaSerialImei}
                    onChange={e => setQaSerialImei(e.target.value)}
                    style={{ width: '100%', background: '#020617', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#fff', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', fontFamily: 'monospace' }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Lead Tech Initials:</label>
                    <input
                      type="text"
                      value={qaTechInitials}
                      onChange={e => setQaTechInitials(e.target.value)}
                      style={{ width: '100%', background: '#020617', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#fff', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem' }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Warranty Period:</label>
                    <select
                      value={qaWarrantyMonths}
                      onChange={e => setQaWarrantyMonths(Number(e.target.value))}
                      style={{ width: '100%', background: '#020617', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#fff', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem' }}
                    >
                      <option value={1}>30-Day Limited</option>
                      <option value={3}>90-Day Standard</option>
                      <option value={12}>1-Year Nationwide</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Compliance Summary */}
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 800 }}>
                  🛡️ 100% QUALITY ASSURANCE PASS VERIFIED
                </div>
                <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px' }}>
                  Hardware calibrated to OEM specifications. Valid for nationwide franchise warranty coverage.
                </div>
              </div>

              {/* Print / Copy Button */}
              <button
                onClick={() => {
                  const slip = `UBREAKIFIX / ASURION QA CERTIFICATE\nCustomer: ${qaCustomerName}\nDevice: ${qaDeviceModel}\nIMEI: ${qaSerialImei}\nWarranty: ${qaWarrantyMonths} Months\nTech Initials: ${qaTechInitials}\nStatus: 24/24 IQC Points Verified`;
                  navigator.clipboard.writeText(slip);
                  alert("📋 QA Certificate copied to clipboard!");
                }}
                style={{
                  background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                  color: '#fff',
                  border: 'none',
                  padding: '10px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 800,
                  cursor: 'pointer'
                }}
              >
                🖨️ Copy Certificate Slip to Clipboard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 12: CHEMICAL SAFETY, MSDS & THERMAL RUNAWAY PROTOCOL */}
      {/* ========================================================================= */}
      {activeStation === 'chem_safety' && (
        <div style={{ background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '14px', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: 800 }}>
                🧪 Chemical Safety, MSDS Flashcards & Hazardous Battery Isolation
              </h3>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                Standard operating procedures for chemical solvents, elastomeric adhesives, and thermal runaway protocols.
              </p>
            </div>

            {/* Toggle Tabs */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setActiveChemTab('guide')}
                style={{
                  background: activeChemTab === 'guide' ? '#0284c7' : 'rgba(255, 255, 255, 0.05)',
                  color: '#fff',
                  border: 'none',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                📘 Chemical Guidelines
              </button>
              <button
                onClick={() => setActiveChemTab('emergency')}
                style={{
                  background: activeChemTab === 'emergency' ? '#ef4444' : 'rgba(239, 68, 68, 0.15)',
                  color: activeChemTab === 'emergency' ? '#fff' : '#f87171',
                  border: '1px solid #ef4444',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                🚨 Emergency Battery Runaway
              </button>
            </div>
          </div>

          {activeChemTab === 'guide' ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {chemicalsSafety.map((chem, idx) => (
                <div key={idx} style={{ background: '#090e17', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.92rem', fontWeight: 800, color: '#38bdf8' }}>{chem.chemical}</span>
                    <span style={{ fontSize: '0.68rem', fontWeight: 800, background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', padding: '2px 6px', borderRadius: '4px' }}>
                      {chem.hazard_class}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    <strong>Purpose:</strong> {chem.purpose}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#eab308' }}>
                    <strong>Required PPE:</strong> {chem.ppe}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.4', marginTop: '4px' }}>
                    {chem.usage_guidelines}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '2px solid rgba(239, 68, 68, 0.4)', borderRadius: '12px', padding: '24px' }}>
              <div style={{ fontSize: '1.15rem', fontWeight: 900, color: '#f87171', marginBottom: '8px' }}>
                🚨 EMERGENCY LITHIUM-ION THERMAL RUNAWAY ACTION PROTOCOL
              </div>
              <p style={{ fontSize: '0.84rem', color: '#fecaca', margin: '0 0 16px 0', lineHeight: '1.4' }}>
                Lithium-ion cells in thermal runaway generate toxic electrolyte vapor (hydrofluoric acid) and self-oxidizing fires exceeding 600°C. Never throw water on a punctured battery.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
                <div style={{ background: '#090e17', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '14px' }}>
                  <div style={{ fontSize: '0.86rem', fontWeight: 800, color: '#f87171', marginBottom: '4px' }}>Step 1: Immediate Triage</div>
                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                    Detect sweet metallic chemical odor (bubblegum/acetone), hissing sound, or swelling. Stop all work and isolate device immediately.
                  </div>
                </div>

                <div style={{ background: '#090e17', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '14px' }}>
                  <div style={{ fontSize: '0.86rem', fontWeight: 800, color: '#f87171', marginBottom: '4px' }}>Step 2: Sand Bucket Submersion</div>
                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                    Use non-conductive fire tongs to drop battery/device directly into the dry sand bucket. Fully bury under 4+ inches of dry sand to starve oxygen.
                  </div>
                </div>

                <div style={{ background: '#090e17', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '14px' }}>
                  <div style={{ fontSize: '0.86rem', fontWeight: 800, color: '#f87171', marginBottom: '4px' }}>Step 3: Fume Evacuation</div>
                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                    Turn on active shop fume extraction to 100%. Evacuate technicians and customers from the immediate repair bench area.
                  </div>
                </div>

                <div style={{ background: '#090e17', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '14px' }}>
                  <div style={{ fontSize: '0.86rem', fontWeight: 800, color: '#f87171', marginBottom: '4px' }}>Step 4: Hazardous Disposal</div>
                  <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                    Allow 48 hours for cell cooling in sand. Transfer to certified hazardous waste containment for franchise recycling.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* STATION 13: USB FLASH DIAGNOSTICS & FLASHER */}
      {/* ========================================================================= */}
      {activeStation === 'usb_recovery' && (
        <UsbFlashRecoveryStation backendUrl={backendUrl} />
      )}

    </div>
  );
}

