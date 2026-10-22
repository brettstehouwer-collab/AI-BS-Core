import os

CODE = r'''import React, { useState, useEffect, useMemo } from 'react';
import { NOCO_DUE_DILIGENCE_QUESTIONS } from './nocoDueDiligenceData.js';

// NoCo Acquisition Master Condition Engine Formula
export const evaluateNoCoProperty = (parcel) => {
  const acreage = parseFloat(parcel.acres) || 1;
  const price = parseFloat(parcel.price) || 0;
  
  // Acreage Fit (15%): Sweet spot 10-25 ac (100 pts), 5-9.9 ac (75 pts), <5 or >40 ac (40 pts)
  const acreageScore = acreage >= 10 && acreage <= 25 ? 100 : (acreage >= 5 && acreage <= 40 ? 75 : 40);
  const pricePerAcre = price / acreage;
  // Price Score (10%): <= $30,000/ac (100 pts), <= $50,000/ac (80 pts), > $50,000/ac (50 pts)
  const priceScore = pricePerAcre <= 30000 ? 100 : (pricePerAcre <= 50000 ? 80 : 50);
  
  const acousticScore = parseFloat(parcel.acousticTopographyScore) || 75;
  const waterScore = parseFloat(parcel.waterRightsScore) || 75;
  const zoningScore = parseFloat(parcel.zoningFlexibilityScore) || 75;
  const shieldScore = parseFloat(parcel.industrialShieldScore) || 75;

  const compositeScore = (
    acreageScore * 0.15 +
    acousticScore * 0.25 +
    waterScore * 0.20 +
    zoningScore * 0.15 +
    shieldScore * 0.15 +
    priceScore * 0.10
  );

  const rounded = Math.round(compositeScore * 10) / 10;
  const verdict = rounded >= 85.0 ? 'PRIME ACQUISITION TARGET' 
                : rounded >= 70.0 ? 'FEASIBLE - CONTINGENT' 
                : 'HIGH FRICTION / REJECT';

  return {
    pricePerAcre: Math.round(pricePerAcre),
    acreageScore,
    priceScore,
    compositeScore: rounded,
    verdict,
    lookupUrl: 'https://www.zillow.com/homes/' + encodeURIComponent(parcel.address) + '_rb/'
  };
};

export default function NocoPropertiesTracker() {
  const [activeSection, setActiveSection] = useState('candidates'); // 'candidates' | 'questionnaire' | 'municipalities' | 'calculator' | 'live_search'
  const [searchFilter, setSearchFilter] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('ALL');

  // Candidate Parcels Data Repository
  const [candidateParcels, setCandidateParcels] = useState([
    {
      id: 'PROP-VT-001',
      address: '63 Big Story Ln, Grafton, VT 05146',
      county: 'Windham County, VT',
      region: 'Windham_VT',
      tier: 'Tier 1 Cultural & Ecological',
      acres: 23.0,
      price: 595000,
      pricePerAcre: 25870,
      acousticTopographyScore: 96,
      waterRightsScore: 100,
      zoningFlexibilityScore: 80,
      industrialShieldScore: 98,
      compositeScore: 95.7,
      verdict: 'PRIME ACQUISITION TARGET',
      highlights: 'Natural mountain bowl amphitheater, year-round spring & perennial stream, Act 250 anti-industrial shield, <30 dBA noise floor.',
      nextStep: 'Confirm Act 250 cultural theater exemptions & winter road accessibility on Big Story Ln.',
      url: 'https://www.zillow.com/homedetails/63-Big-Story-Ln-Grafton-VT-05146/2056242318_zpid/'
    },
    {
      id: 'PROP-NY-001',
      address: 'Lot #4 Hill Rd, Danby / Ithaca, NY 14850',
      county: 'Tompkins County, NY',
      region: 'Tompkins_NY',
      tier: 'Tier 1 Academic & Agricultural',
      acres: 25.0,
      price: 172500,
      pricePerAcre: 6900,
      acousticTopographyScore: 88,
      waterRightsScore: 85,
      zoningFlexibilityScore: 92,
      industrialShieldScore: 90,
      compositeScore: 91.3,
      verdict: 'PRIME ACQUISITION TARGET',
      highlights: '25.0 contiguous acres ($6,900/ac!), 8 min to Ithaca & Cornell CEA extension, expansive wooded bowl, favorable rural agritourism zoning.',
      nextStep: 'Conduct soil perc test for 350-occupant wetland septic and verify road access grade.',
      url: 'https://www.zillow.com/homedetails/LOT-4-Hill-Rd-Ithaca-NY-14850/465219664_zpid/'
    },
    {
      id: 'PROP-NY-002',
      address: 'Danby Rd 12.1-Acre Pond Parcel, Ithaca, NY 14850',
      county: 'Tompkins County, NY',
      region: 'Tompkins_NY',
      tier: 'Tier 1 Academic & Agricultural',
      acres: 12.1,
      price: 169000,
      pricePerAcre: 13967,
      acousticTopographyScore: 82,
      waterRightsScore: 95,
      zoningFlexibilityScore: 90,
      industrialShieldScore: 80,
      compositeScore: 90.0,
      verdict: 'PRIME ACQUISITION TARGET',
      highlights: '12.1-acre sweet spot, existing natural retention pond, <$14k/ac, immediate Cornell CEA nexus proximity.',
      nextStep: 'Acoustic decibel test along Danby Rd and wetland setback delineation around pond.',
      url: 'https://www.zillow.com/ithaca-ny/land/'
    },
    {
      id: 'PROP-NY-004',
      address: '212 Hill Rd, Ithaca, NY 14850',
      county: 'Tompkins County, NY',
      region: 'Tompkins_NY',
      tier: 'Tier 1 Academic & Agricultural',
      acres: 12.5,
      price: 250000,
      pricePerAcre: 20000,
      acousticTopographyScore: 85,
      waterRightsScore: 86,
      zoningFlexibilityScore: 88,
      industrialShieldScore: 86,
      compositeScore: 89.6,
      verdict: 'PRIME ACQUISITION TARGET',
      highlights: '12.5-acre sweet spot, elevated natural knoll with amphitheater slope, direct transit corridor to Cornell.',
      nextStep: 'Confirm well recharge rate (GPM) and verify boundary markers with surveyor.',
      url: 'https://www.zillow.com/ithaca-ny/land/'
    },
    {
      id: 'PROP-NJ-001',
      address: 'Hunterdon Ag Belt Parcel, Hunterdon County, NJ 08822',
      county: 'Hunterdon County, NJ',
      region: 'Hunterdon_NJ',
      tier: 'Tier 1 Ag-Preservation & Donor Nexus',
      acres: 15.0,
      price: 495000,
      pricePerAcre: 33000,
      acousticTopographyScore: 84,
      waterRightsScore: 90,
      zoningFlexibilityScore: 88,
      industrialShieldScore: 95,
      compositeScore: 89.5,
      verdict: 'PRIME ACQUISITION TARGET',
      highlights: '110+ municipal data center bans, 42% preserved ag land, NJ Right to Farm Act, 50-yr aquifer security, 1.5 hr to NYC donors.',
      nextStep: 'Verify existing Farmland Assessment tax status and local municipal assembly permit guidelines.',
      url: 'https://www.zillow.com/hunterdon-county-nj/land/'
    },
    {
      id: 'PROP-NY-003',
      address: '0 Lower Creek Rd #36, Ithaca, NY 14850',
      county: 'Tompkins County, NY',
      region: 'Tompkins_NY',
      tier: 'Tier 1 Academic & Agricultural',
      acres: 78.5,
      price: 700000,
      pricePerAcre: 8917,
      acousticTopographyScore: 92,
      waterRightsScore: 94,
      zoningFlexibilityScore: 85,
      industrialShieldScore: 92,
      compositeScore: 84.3,
      verdict: 'FEASIBLE - CONTINGENT',
      highlights: '78.5-acre macro buffer, extensive creek frontage, wholesale bulk pricing ($8,917/ac), superb acoustic isolation.',
      nextStep: 'Evaluate agricultural cluster subdivision into separate LLC nodes or conservation easement carve-out.',
      url: 'https://www.zillow.com/homedetails/0-Lower-Creek-Rd-36-Ithaca-NY-14850/340762830_zpid/'
    },
    {
      id: 'PROP-NY-005',
      address: '75 Bush Ln, Lansing / Ithaca, NY 14882',
      county: 'Tompkins County, NY',
      region: 'Tompkins_NY',
      tier: 'Tier 1 Academic & Agricultural',
      acres: 6.97,
      price: 549000,
      pricePerAcre: 78766,
      acousticTopographyScore: 70,
      waterRightsScore: 75,
      zoningFlexibilityScore: 72,
      industrialShieldScore: 68,
      compositeScore: 69.8,
      verdict: 'HIGH FRICTION / REJECT',
      highlights: 'Cayuga Lake watershed proximity, but high $78k/ac price and suburban corridor noise floor (>45 dBA).',
      nextStep: 'Monitor for price drop or seller financing; secondary fallback parcel.',
      url: 'https://www.zillow.com/homedetails/75-Bush-Ln-Ithaca-NY-14850/32811444_zpid/'
    },
    {
      id: 'PROP-MI-001',
      address: '4680 Luce St Parcel C, Jenison, MI 49428',
      county: 'Ottawa County, MI',
      region: 'Ottawa_MI',
      tier: 'Tier 2 Regional Base',
      acres: 3.0,
      price: 225000,
      pricePerAcre: 75000,
      acousticTopographyScore: 55,
      waterRightsScore: 70,
      zoningFlexibilityScore: 60,
      industrialShieldScore: 50,
      compositeScore: 55.2,
      verdict: 'HIGH FRICTION / REJECT',
      highlights: 'Ottawa County home base baseline with Great Lakes water table, but 3.0 acres fails the 5.0 acre minimum.',
      nextStep: 'Check adjacent parcel acquisition viability to aggregate 10+ contiguous acres.',
      url: 'https://www.zillow.com/homedetails/4680-Luce-St-Jenison-MI-49428/2056382104_zpid/'
    }
  ]);

  // Municipal Defense Matrix
  const municipalities = [
    {
      id: 'hunterdon_warren_nj',
      region: 'Hunterdon & Warren Counties, NJ',
      tier: 'Tier 1 Ag-Preservation & Donor Nexus',
      badgeColor: '#10b981',
      antiIndustrialShield: 'Over 110 municipal zoning bans against hyperscale data centers & mega-warehouses. Strict impervious surface caps.',
      agCeaExemption: 'New Jersey Right to Farm Act (N.J.S.A. 4:1C-1) preempts restrictive local zoning for CEA, greenhouses, and on-farm educational activities.',
      aquiferSecurity: '50-year Highlands and unconfined aquifer recharge security; zero risk of industrial toxic drawdown.',
      acousticBaseline: '<35 dBA ambient rural baseline across farm corridors; excellent topographical ridgelines.',
      donorRadius: '1.5-hour direct transit radius to Manhattan philanthropic, donor, and patron networks.',
      keyTowns: 'Kingwood, Franklin, Delaware Twp, Alexandria, East Amwell, Hope'
    },
    {
      id: 'addison_windham_vt',
      region: 'Addison & Windham Counties, VT',
      tier: 'Tier 1 Cultural & Ecological',
      badgeColor: '#00FFFF',
      antiIndustrialShield: 'Vermont Act 250 Land Use Regulations (10 V.S.A. Ch. 151) create an aggressive statutory barrier against commercial sprawl and data center creep.',
      agCeaExemption: 'Act 250 Criterion 9(B) prioritizes primary agricultural soils while accommodating cultural and ecological farm assemblies.',
      aquiferSecurity: 'Pristine glacial recharge basins, abundant natural springs, and perennial cold-water trout streams.',
      acousticBaseline: '<30 dBA ultra-quiet acoustic noise floor; natural mountain hollows and concave depressions ideal for unamplified vocal projection.',
      donorRadius: 'Middlebury College collegiate theater & technical director nexus; 3.5 hours to Boston, 4 hours to NYC.',
      keyTowns: 'Grafton, Middlebury, Townshend, Rockingham, Chester, Newfane, Ripton'
    },
    {
      id: 'tompkins_ny',
      region: 'Tompkins County, NY (Ithaca / Finger Lakes)',
      tier: 'Tier 1 Academic & Agricultural',
      badgeColor: '#3b82f6',
      antiIndustrialShield: 'Town Code § 144-202.1(B)(1)(b) explicitly exempts agricultural buildings from stringent IECS Net-Zero energy constraints, legally shielding high-pressure aeroponics (HPA) and dual-use greenhouse stages.',
      agCeaExemption: 'New York State Ag & Markets Law § 305-a preempts unreasonably restrictive local regulations in certified Agricultural Districts.',
      aquiferSecurity: 'Cayuga Lake watershed and abundant glacial till aquifers; robust perennial agricultural well yields (>25 GPM).',
      acousticBaseline: '<35 dBA acoustic floor in Danby and Lansing rural bowls; prevailing southwesterly winds carry acoustic waves up northern rakes.',
      donorRadius: 'Direct synergy with Cornell CEA researchers and Ithaca College Department of Theatre Arts; 4 hours to NYC.',
      keyTowns: 'Ithaca, Danby, Lansing, Trumansburg, Ulysses, Newfield, Enfield'
    },
    {
      id: 'ottawa_mi',
      region: 'Ottawa County, MI (Jenison / Grand Haven)',
      tier: 'Tier 2 Regional Base',
      badgeColor: '#f59e0b',
      antiIndustrialShield: 'Michigan Right to Farm Act (PA 93 of 1981) and GAAMPs (Generally Accepted Ag Practices) protect farm activities against nuisance suits.',
      agCeaExemption: 'Township agricultural zoning allows farm markets, agritourism, and educational tours subject to site plan reviews.',
      aquiferSecurity: 'World-class Great Lakes freshwater abundance; shallow water table with consistent high-volume well output.',
      acousticBaseline: '40–48 dBA ambient noise floor due to suburban highway networks; requires substantial natural earth berms or ravine buffers.',
      donorRadius: 'Home base operational nexus; 25 minutes to Grand Rapids philanthropic corridor.',
      keyTowns: 'Jenison, Georgetown Twp, Grand Haven, Spring Lake, Allendale, Zeeland'
    }
  ];

  // 112 Due Diligence Master Questionnaire State
  const [selectedAuditPropertyId, setSelectedAuditPropertyId] = useState('PROP-VT-001');
  const [auditCategoryFilter, setAuditCategoryFilter] = useState('ALL');
  const [auditStatusFilter, setAuditStatusFilter] = useState('ALL');
  const [auditSearchQuery, setAuditSearchQuery] = useState('');
  
  // Audits dictionary stored in localStorage: { [propertyId]: { [qId]: { assessment, realtorResponse, notes } } }
  const [propertyAudits, setPropertyAudits] = useState(() => {
    try {
      const saved = localStorage.getItem('noco_property_audits_v2');
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.warn('Failed to load audits from localStorage', e);
    }
    // Default initial seed
    return {
      'PROP-VT-001': {
        'Q1': { assessment: 'Pass', notes: '23.0 surveyed contiguous acres on Big Story Ln.' },
        'Q13': { assessment: 'Pass', notes: 'Natural mountain amphitheater contour with 60+ ft elevation drop.' },
        'Q14': { assessment: 'Pass', notes: 'Concave mountain bowl facing south/southeast.' },
        'Q24': { assessment: 'Pass', notes: 'Measured ambient noise floor <30 dBA.' },
        'Q25': { assessment: 'Pass', notes: 'Perennial crystalline brook traverses lower parcel border.' },
        'Q26': { assessment: 'Pass', notes: 'Active gravity-fed mountain spring on deed.' },
        'Q49': { assessment: 'Pass', notes: 'Protected under Vermont Act 250 Criterion 9(B).' },
        'Q105': { assessment: 'Pass', notes: '$25,870/ac acquisition basis ($595k total).' }
      },
      'PROP-NY-001': {
        'Q1': { assessment: 'Pass', notes: '25.0 contiguous acres in sweet spot.' },
        'Q3': { assessment: 'Pass', notes: '129 ft public road frontage opening into wide interior bowl.' },
        'Q14': { assessment: 'Pass', notes: 'Rolling bowl depression buffering road sound.' },
        'Q61': { assessment: 'Pass', notes: 'Exempt under Town Code § 144-202.1(B)(1)(b).' },
        'Q105': { assessment: 'Pass', notes: '$6,900/ac exceptional valuation basis ($172,500 total).' }
      }
    };
  });

  // Persist audits
  useEffect(() => {
    try {
      localStorage.setItem('noco_property_audits_v2', JSON.stringify(propertyAudits));
    } catch (e) {
      console.warn('Failed to save audits to localStorage', e);
    }
  }, [propertyAudits]);

  // Current Property's Audit Responses
  const currentPropertyAudit = propertyAudits[selectedAuditPropertyId] || {};

  const handleUpdateAuditQuestion = (qId, field, value) => {
    setPropertyAudits(prev => {
      const propData = prev[selectedAuditPropertyId] || {};
      const qData = propData[qId] || { assessment: 'Pending', realtorResponse: '', notes: '' };
      return {
        ...prev,
        [selectedAuditPropertyId]: {
          ...propData,
          [qId]: {
            ...qData,
            [field]: value
          }
        }
      };
    });
  };

  // Categories in 112 Questionnaire
  const categoriesList = useMemo(() => {
    const cats = [];
    NOCO_DUE_DILIGENCE_QUESTIONS.forEach(item => {
      if (!cats.includes(item.category)) cats.push(item.category);
    });
    return cats;
  }, []);

  // Filtered Questions
  const filteredQuestions = useMemo(() => {
    return NOCO_DUE_DILIGENCE_QUESTIONS.filter(item => {
      const audit = currentPropertyAudit[item.id] || {};
      const currentAssessment = audit.assessment || item.assessment || 'Pending';

      // Category filter
      if (auditCategoryFilter !== 'ALL' && item.category !== auditCategoryFilter) return false;

      // Status filter
      if (auditStatusFilter !== 'ALL') {
        if (auditStatusFilter === 'PASS' && !(currentAssessment === 'Pass' || currentAssessment === 'Acceptable')) return false;
        if (auditStatusFilter === 'PENDING' && currentAssessment !== 'Pending') return false;
        if (auditStatusFilter === 'RED_FLAG' && currentAssessment !== 'Red Flag') return false;
      }

      // Search query
      if (auditSearchQuery.trim()) {
        const q = auditSearchQuery.toLowerCase();
        const matchesQ = item.question.toLowerCase().includes(q);
        const matchesBench = item.benchmark.toLowerCase().includes(q);
        const matchesSource = item.source.toLowerCase().includes(q);
        const matchesNotes = (audit.notes || '').toLowerCase().includes(q);
        const matchesResp = (audit.realtorResponse || '').toLowerCase().includes(q);
        if (!matchesQ && !matchesBench && !matchesSource && !matchesNotes && !matchesResp) return false;
      }

      return true;
    });
  }, [auditCategoryFilter, auditStatusFilter, auditSearchQuery, currentPropertyAudit]);

  // Audit Metrics for Current Property
  const auditMetrics = useMemo(() => {
    let passCount = 0;
    let pendingCount = 0;
    let redFlagCount = 0;

    NOCO_DUE_DILIGENCE_QUESTIONS.forEach(q => {
      const a = currentPropertyAudit[q.id]?.assessment || q.assessment || 'Pending';
      if (a === 'Pass' || a === 'Acceptable') passCount++;
      else if (a === 'Red Flag') redFlagCount++;
      else pendingCount++;
    });

    const total = NOCO_DUE_DILIGENCE_QUESTIONS.length;
    const answered = total - pendingCount;
    const progressPct = Math.round((answered / total) * 100);

    return { total, passCount, pendingCount, redFlagCount, progressPct };
  }, [currentPropertyAudit]);

  // Export audit as JSON or CSV
  const exportAuditJSON = () => {
    const selectedProp = candidateParcels.find(p => p.id === selectedAuditPropertyId) || { address: selectedAuditPropertyId };
    const exportData = {
      property: selectedProp,
      export_date: new Date().toISOString(),
      audit_metrics: auditMetrics,
      responses: NOCO_DUE_DILIGENCE_QUESTIONS.map(q => ({
        ...q,
        assessment: currentPropertyAudit[q.id]?.assessment || q.assessment || 'Pending',
        realtorResponse: currentPropertyAudit[q.id]?.realtorResponse || '',
        notes: currentPropertyAudit[q.id]?.notes || ''
      }))
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `NoCo_Due_Diligence_${selectedAuditPropertyId}_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportAuditCSV = () => {
    const rows = [
      ['Question ID', 'Category', 'Due Diligence Question', 'NoCo Benchmark', 'Verification Source', 'Assessment', 'Realtor / Seller Response', 'Action Items & Notes']
    ];
    NOCO_DUE_DILIGENCE_QUESTIONS.forEach(q => {
      const audit = currentPropertyAudit[q.id] || {};
      rows.push([
        q.id,
        `"${q.category.replace(/"/g, '""')}"`,
        `"${q.question.replace(/"/g, '""')}"`,
        `"${q.benchmark.replace(/"/g, '""')}"`,
        `"${q.source.replace(/"/g, '""')}"`,
        audit.assessment || q.assessment || 'Pending',
        `"${(audit.realtorResponse || '').replace(/"/g, '""')}"`,
        `"${(audit.notes || '').replace(/"/g, '""')}"`
      ]);
    });
    const csvContent = '\uFEFF' + rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `NoCo_Due_Diligence_Audit_${selectedAuditPropertyId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Calculator State
  const [evalAddress, setEvalAddress] = useState('New Candidate Parcel, Tompkins County, NY');
  const [evalAcres, setEvalAcres] = useState(18.5);
  const [evalPrice, setEvalPrice] = useState(320000);
  const [evalAcoustic, setEvalAcoustic] = useState(88);
  const [evalWater, setEvalWater] = useState(90);
  const [evalZoning, setEvalZoning] = useState(85);
  const [evalShield, setEvalShield] = useState(92);

  const evalResult = useMemo(() => {
    return evaluateNoCoProperty({
      address: evalAddress,
      acres: evalAcres,
      price: evalPrice,
      acousticTopographyScore: evalAcoustic,
      waterRightsScore: evalWater,
      zoningFlexibilityScore: evalZoning,
      industrialShieldScore: evalShield
    });
  }, [evalAddress, evalAcres, evalPrice, evalAcoustic, evalWater, evalZoning, evalShield]);

  const handleAddCandidate = () => {
    const newParcel = {
      id: `PROP-CUSTOM-${Date.now().toString().slice(-4)}`,
      address: evalAddress,
      county: 'Evaluated Custom Parcel',
      region: 'Custom',
      tier: 'Evaluated Prospect',
      acres: parseFloat(evalAcres),
      price: parseFloat(evalPrice),
      pricePerAcre: evalResult.pricePerAcre,
      acousticTopographyScore: evalAcoustic,
      waterRightsScore: evalWater,
      zoningFlexibilityScore: evalZoning,
      industrialShieldScore: evalShield,
      compositeScore: evalResult.compositeScore,
      verdict: evalResult.verdict,
      highlights: 'Custom parcel evaluated via NoCo condition engine.',
      nextStep: 'Initiate 112 Due Diligence Questionnaire audit.',
      url: evalResult.lookupUrl
    };
    setCandidateParcels([newParcel, ...candidateParcels]);
    setSelectedAuditPropertyId(newParcel.id);
    setActiveSection('candidates');
  };

  const filteredParcels = useMemo(() => {
    return candidateParcels.filter(p => {
      if (verdictFilter !== 'ALL' && !p.verdict.includes(verdictFilter)) return false;
      if (searchFilter.trim()) {
        const q = searchFilter.toLowerCase();
        return p.address.toLowerCase().includes(q) || p.county.toLowerCase().includes(q) || (p.highlights || '').toLowerCase().includes(q);
      }
      return true;
    });
  }, [candidateParcels, verdictFilter, searchFilter]);

  const getVerdictColor = (verdict) => {
    if (verdict.includes('PRIME')) return '#10b981';
    if (verdict.includes('FEASIBLE')) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', color: '#f8fafc' }}>
      
      {/* 1. Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(0, 255, 255, 0.12) 0%, rgba(122, 40, 138, 0.25) 100%)',
        border: '1px solid #00FFFF',
        borderRadius: '12px',
        padding: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px',
        boxShadow: '0 4px 24px rgba(0, 255, 255, 0.15)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.6rem' }}>🎭</span>
            <h2 style={{ margin: 0, fontSize: '1.4rem', color: '#ffffff', fontWeight: 800 }}>
              NoCo Land Acquisition, Municipal Defense &amp; 112 Due Diligence Hub
            </h2>
            <span style={{
              background: 'rgba(0, 255, 255, 0.2)',
              border: '1px solid #00FFFF',
              color: '#00FFFF',
              padding: '4px 10px',
              borderRadius: '20px',
              fontSize: '0.75rem',
              fontWeight: 800
            }}>
              LIVE AUDIT ENGINE ACTIVE
            </span>
          </div>
          <p style={{ margin: '6px 0 0 0', fontSize: '0.85rem', color: '#94a3b8' }}>
            Acoustic Topography &bull; Act 250 / Right to Farm Shields &bull; 10–25 Acre Sweet Spot &bull; 112 Due Diligence Gates &bull; Sean &amp; Brett Master Architecture
          </p>
        </div>

        {/* Quick Metrics */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.3)' }}>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>PRIME TARGETS</div>
            <div style={{ fontSize: '1.2rem', color: '#10b981', fontWeight: 900 }}>
              {candidateParcels.filter(p => p.verdict.includes('PRIME')).length} Parcels
            </div>
          </div>
          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(122, 40, 138, 0.4)' }}>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>DUE DILIGENCE GATES</div>
            <div style={{ fontSize: '1.2rem', color: '#00FFFF', fontWeight: 900 }}>112 Questions</div>
          </div>
          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>ACQUISITION SWEET SPOT</div>
            <div style={{ fontSize: '1.2rem', color: '#f59e0b', fontWeight: 900 }}>10–25 ac (&lt;$50k/ac)</div>
          </div>
        </div>
      </div>

      {/* 2. Mode Navigation Switcher */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '10px', overflowX: 'auto' }}>
        {[
          { id: 'candidates', label: `🎯 Candidate Parcels & Queue (${candidateParcels.length})` },
          { id: 'questionnaire', label: `📋 112 Due Diligence Master Audit` },
          { id: 'municipalities', label: `🏛️ Nationwide Municipal Defense Tracker (4 Hubs)` },
          { id: 'calculator', label: `⚖️ Live Condition Evaluation Engine (Scorer)` },
          { id: 'live_search', label: `🌐 Multi-County Live Lookup Launchpad` }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSection(tab.id)}
            style={{
              background: activeSection === tab.id ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${activeSection === tab.id ? '#00FFFF' : 'rgba(255, 255, 255, 0.1)'}`,
              color: activeSection === tab.id ? '#00FFFF' : '#94a3b8',
              borderRadius: '8px',
              padding: '10px 16px',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.85rem',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ========================================================================= */}
      {/* SECTION 1: CANDIDATE PARCELS & SNIFFER QUEUE */}
      {/* ========================================================================= */}
      {activeSection === 'candidates' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Filter Bar */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(15, 23, 42, 0.8)',
            padding: '12px 16px',
            borderRadius: '10px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Filter Verdict:</span>
              {['ALL', 'PRIME', 'FEASIBLE', 'REJECT'].map(v => (
                <button
                  key={v}
                  onClick={() => setVerdictFilter(v)}
                  style={{
                    background: verdictFilter === v ? 'rgba(0, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                    border: `1px solid ${verdictFilter === v ? '#00FFFF' : 'rgba(255, 255, 255, 0.1)'}`,
                    color: verdictFilter === v ? '#00FFFF' : '#94a3b8',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  {v}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Search address, county, criteria..."
                value={searchFilter}
                onChange={e => setSearchFilter(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  color: '#ffffff',
                  fontSize: '0.8rem',
                  width: '260px'
                }}
              />
              <button
                onClick={() => setActiveSection('calculator')}
                style={{
                  background: 'linear-gradient(135deg, #00FFFF, #7A288A)',
                  border: 'none',
                  color: '#000000',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  fontWeight: 800,
                  fontSize: '0.8rem',
                  cursor: 'pointer'
                }}
              >
                + Evaluate New Parcel
              </button>
            </div>
          </div>

          {/* Candidate Parcels Table */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.7)',
            borderRadius: '10px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            overflowX: 'auto'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: 'rgba(0, 0, 0, 0.4)', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 14px' }}>Parcel / Address</th>
                  <th style={{ padding: '12px 14px' }}>Region / County</th>
                  <th style={{ padding: '12px 14px' }}>Acreage</th>
                  <th style={{ padding: '12px 14px' }}>List Price</th>
                  <th style={{ padding: '12px 14px' }}>Price / Acre</th>
                  <th style={{ padding: '12px 14px' }}>Condition Score</th>
                  <th style={{ padding: '12px 14px' }}>Condition Verdict</th>
                  <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredParcels.map((p, idx) => {
                  const vColor = getVerdictColor(p.verdict);
                  return (
                    <tr
                      key={p.id}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                        background: idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent'
                      }}
                    >
                      <td style={{ padding: '14px', fontWeight: 700, color: '#ffffff' }}>
                        <div>{p.address}</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px', fontWeight: 400 }}>
                          {p.highlights}
                        </div>
                      </td>
                      <td style={{ padding: '14px', color: '#cbd5e1' }}>
                        <div>{p.county}</div>
                        <span style={{ fontSize: '0.7rem', color: '#00FFFF' }}>{p.tier}</span>
                      </td>
                      <td style={{ padding: '14px', fontWeight: 800, color: p.acres >= 10 && p.acres <= 25 ? '#10b981' : '#f59e0b' }}>
                        {p.acres} ac
                      </td>
                      <td style={{ padding: '14px', color: '#ffffff', fontWeight: 700 }}>
                        ${p.price.toLocaleString()}
                      </td>
                      <td style={{ padding: '14px', color: p.pricePerAcre <= 30000 ? '#10b981' : (p.pricePerAcre <= 50000 ? '#f59e0b' : '#ef4444'), fontWeight: 800 }}>
                        ${p.pricePerAcre.toLocaleString()}/ac
                      </td>
                      <td style={{ padding: '14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 900, fontSize: '1rem', color: vColor }}>
                            {p.compositeScore}%
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '14px' }}>
                        <span style={{
                          background: `${vColor}20`,
                          border: `1px solid ${vColor}`,
                          color: vColor,
                          padding: '4px 8px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: 800
                        }}>
                          {p.verdict}
                        </span>
                      </td>
                      <td style={{ padding: '14px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                          <button
                            onClick={() => {
                              setSelectedAuditPropertyId(p.id);
                              setActiveSection('questionnaire');
                            }}
                            style={{
                              background: 'rgba(0, 255, 255, 0.15)',
                              border: '1px solid #00FFFF',
                              color: '#00FFFF',
                              padding: '5px 9px',
                              borderRadius: '6px',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              cursor: 'pointer'
                            }}
                          >
                            📋 Audit 112 Qs
                          </button>
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noreferrer"
                            style={{
                              background: 'rgba(255, 255, 255, 0.08)',
                              border: '1px solid rgba(255, 255, 255, 0.2)',
                              color: '#ffffff',
                              padding: '5px 9px',
                              borderRadius: '6px',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              textDecoration: 'none'
                            }}
                          >
                            🔗 Zillow / Feed
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 2: 112 DUE DILIGENCE MASTER QUESTIONNAIRE & AUDIT */}
      {/* ========================================================================= */}
      {activeSection === 'questionnaire' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* Property Selector & Action Controls */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid rgba(0, 255, 255, 0.3)',
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '16px'
          }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Active Audit Parcel:
              </div>
              <select
                value={selectedAuditPropertyId}
                onChange={e => setSelectedAuditPropertyId(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.5)',
                  border: '1px solid #00FFFF',
                  color: '#ffffff',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  fontWeight: 700,
                  marginTop: '4px',
                  minWidth: '320px'
                }}
              >
                {candidateParcels.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.address} ({p.acres} ac &bull; {p.compositeScore}% - {p.verdict})
                  </option>
                ))}
              </select>
            </div>

            {/* Audit Scorecard Pills */}
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>AUDIT PROGRESS</div>
                <div style={{ fontSize: '1rem', color: '#00FFFF', fontWeight: 800 }}>{auditMetrics.progressPct}% Done</div>
              </div>
              <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>PASS / ACCEPTABLE</div>
                <div style={{ fontSize: '1rem', color: '#10b981', fontWeight: 800 }}>{auditMetrics.passCount} / 112</div>
              </div>
              <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>PENDING REVIEW</div>
                <div style={{ fontSize: '1rem', color: '#f59e0b', fontWeight: 800 }}>{auditMetrics.pendingCount} / 112</div>
              </div>
              <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>RED FLAGS</div>
                <div style={{ fontSize: '1rem', color: '#ef4444', fontWeight: 800 }}>{auditMetrics.redFlagCount} / 112</div>
              </div>
            </div>

            {/* Export & External Spreadsheet Links */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                onClick={exportAuditJSON}
                style={{
                  background: 'rgba(0, 255, 255, 0.15)',
                  border: '1px solid #00FFFF',
                  color: '#00FFFF',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                📥 Export JSON
              </button>
              <button
                onClick={exportAuditCSV}
                style={{
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid #10b981',
                  color: '#10b981',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                📊 Export CSV
              </button>
              <a
                href="https://docs.google.com/spreadsheets/d/1wYTCb3qyhPXn-X1301b184ET49VKA7gVjAePv-rGPys/edit"
                target="_blank"
                rel="noreferrer"
                style={{
                  background: 'rgba(122, 40, 138, 0.25)',
                  border: '1px solid #7A288A',
                  color: '#c084fc',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  textDecoration: 'none'
                }}
              >
                🔗 Google Sheets (112 Qs)
              </a>
            </div>
          </div>

          {/* Category Filter Pills (10 Master Categories) */}
          <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '6px' }}>
            <button
              onClick={() => setAuditCategoryFilter('ALL')}
              style={{
                background: auditCategoryFilter === 'ALL' ? 'rgba(0, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                border: `1px solid ${auditCategoryFilter === 'ALL' ? '#00FFFF' : 'rgba(255, 255, 255, 0.1)'}`,
                color: auditCategoryFilter === 'ALL' ? '#00FFFF' : '#94a3b8',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              All 10 Categories (112)
            </button>
            {categoriesList.map((cat, idx) => {
              const count = NOCO_DUE_DILIGENCE_QUESTIONS.filter(q => q.category === cat).length;
              return (
                <button
                  key={idx}
                  onClick={() => setAuditCategoryFilter(cat)}
                  style={{
                    background: auditCategoryFilter === cat ? 'rgba(0, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                    border: `1px solid ${auditCategoryFilter === cat ? '#00FFFF' : 'rgba(255, 255, 255, 0.1)'}`,
                    color: auditCategoryFilter === cat ? '#00FFFF' : '#94a3b8',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {cat} ({count})
                </button>
              );
            })}
          </div>

          {/* Search & Status Filters */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'rgba(15, 23, 42, 0.7)',
            padding: '10px 14px',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Filter Status:</span>
              {[
                { id: 'ALL', label: 'All Statuses' },
                { id: 'PASS', label: `Pass / Acceptable (${auditMetrics.passCount})` },
                { id: 'PENDING', label: `Pending (${auditMetrics.pendingCount})` },
                { id: 'RED_FLAG', label: `Red Flag (${auditMetrics.redFlagCount})` }
              ].map(st => (
                <button
                  key={st.id}
                  onClick={() => setAuditStatusFilter(st.id)}
                  style={{
                    background: auditStatusFilter === st.id ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                    border: `1px solid ${auditStatusFilter === st.id ? '#00FFFF' : 'rgba(255, 255, 255, 0.1)'}`,
                    color: auditStatusFilter === st.id ? '#00FFFF' : '#94a3b8',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  {st.label}
                </button>
              ))}
            </div>

            <input
              type="text"
              placeholder="Search due diligence questions, benchmark criteria, sources..."
              value={auditSearchQuery}
              onChange={e => setAuditSearchQuery(e.target.value)}
              style={{
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                padding: '6px 12px',
                color: '#ffffff',
                fontSize: '0.78rem',
                width: '320px'
              }}
            />
          </div>

          {/* Questionnaire Card Stream */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filteredQuestions.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: '#94a3b8', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '8px' }}>
                No due diligence questions match the active filters.
              </div>
            ) : (
              filteredQuestions.map(item => {
                const audit = currentPropertyAudit[item.id] || {};
                const currentAssessment = audit.assessment || item.assessment || 'Pending';
                const statusColor = currentAssessment === 'Pass' || currentAssessment === 'Acceptable'
                  ? '#10b981'
                  : (currentAssessment === 'Red Flag' ? '#ef4444' : '#f59e0b');

                return (
                  <div
                    key={item.id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.85)',
                      border: `1px solid ${statusColor}40`,
                      borderLeft: `4px solid ${statusColor}`,
                      borderRadius: '8px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px'
                    }}
                  >
                    {/* Top Row: Q ID, Category, Status Selector */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                          background: 'rgba(0, 255, 255, 0.15)',
                          border: '1px solid #00FFFF',
                          color: '#00FFFF',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 800
                        }}>
                          {item.id}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>
                          {item.category}
                        </span>
                      </div>

                      {/* Status Selector Buttons */}
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {['Pass', 'Acceptable', 'Pending', 'Red Flag'].map(opt => {
                          const isSel = currentAssessment === opt;
                          const optColor = opt === 'Pass' || opt === 'Acceptable' ? '#10b981' : (opt === 'Red Flag' ? '#ef4444' : '#f59e0b');
                          return (
                            <button
                              key={opt}
                              onClick={() => handleUpdateAuditQuestion(item.id, 'assessment', opt)}
                              style={{
                                background: isSel ? `${optColor}30` : 'rgba(255, 255, 255, 0.04)',
                                border: `1px solid ${isSel ? optColor : 'rgba(255, 255, 255, 0.1)'}`,
                                color: isSel ? optColor : '#94a3b8',
                                padding: '3px 8px',
                                borderRadius: '4px',
                                fontSize: '0.7rem',
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              {opt}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Question Text */}
                    <div style={{ fontSize: '0.92rem', color: '#ffffff', fontWeight: 700, lineHeight: 1.4 }}>
                      {item.question}
                    </div>

                    {/* Benchmark & Verification Source Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px' }}>
                      <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '10px', borderRadius: '6px', borderLeft: '2px solid #00FFFF' }}>
                        <div style={{ fontSize: '0.68rem', color: '#00FFFF', fontWeight: 800, textTransform: 'uppercase' }}>
                          🎯 NoCo Target Benchmark / Condition
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#e2e8f0', marginTop: '4px', lineHeight: 1.35 }}>
                          {item.benchmark}
                        </div>
                      </div>

                      <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '10px', borderRadius: '6px', borderLeft: '2px solid #c084fc' }}>
                        <div style={{ fontSize: '0.68rem', color: '#c084fc', fontWeight: 800, textTransform: 'uppercase' }}>
                          🏛️ Verification Source / Due Diligence Authority
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#e2e8f0', marginTop: '4px', lineHeight: 1.35 }}>
                          {item.source}
                        </div>
                      </div>
                    </div>

                    {/* Interactive Realtor / Seller Response & Action Notes */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '2px' }}>
                      <div>
                        <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px', fontWeight: 600 }}>
                          Realtor / Seller Response:
                        </div>
                        <input
                          type="text"
                          placeholder="Enter verified seller disclosure or realtor feedback..."
                          value={audit.realtorResponse || ''}
                          onChange={e => handleUpdateAuditQuestion(item.id, 'realtorResponse', e.target.value)}
                          style={{
                            width: '100%',
                            background: 'rgba(0, 0, 0, 0.4)',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            borderRadius: '4px',
                            padding: '6px 10px',
                            color: '#ffffff',
                            fontSize: '0.78rem'
                          }}
                        />
                      </div>

                      <div>
                        <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: '4px', fontWeight: 600 }}>
                          Action Items &amp; Due Diligence Notes:
                        </div>
                        <input
                          type="text"
                          placeholder="e.g. Schedule perc test, pull GIS deed plat..."
                          value={audit.notes || ''}
                          onChange={e => handleUpdateAuditQuestion(item.id, 'notes', e.target.value)}
                          style={{
                            width: '100%',
                            background: 'rgba(0, 0, 0, 0.4)',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            borderRadius: '4px',
                            padding: '6px 10px',
                            color: '#ffffff',
                            fontSize: '0.78rem'
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 3: MUNICIPALITIES REGULATORY & ENVIRONMENTAL DEFENSE TRACKER */}
      {/* ========================================================================= */}
      {activeSection === 'municipalities' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <h3 style={{ margin: '0 0 6px 0', color: '#00FFFF', fontSize: '1.1rem' }}>
              🏛️ The 4-Hub Municipal Defense &amp; Regulatory Shield Matrix
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5 }}>
              Comprehensive evaluation of legal shields against industrial creep (hyperscale data centers, mega-warehouses), statutory agricultural protections, 50-year aquifer security, and the Trojan Horse viability for dual-use theatrical greenhouse assembly.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
            {municipalities.map(m => (
              <div
                key={m.id}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: `1px solid ${m.badgeColor}50`,
                  borderRadius: '10px',
                  padding: '18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4 style={{ margin: 0, fontSize: '1.05rem', color: '#ffffff', fontWeight: 800 }}>{m.region}</h4>
                  <span style={{
                    background: `${m.badgeColor}20`,
                    border: `1px solid ${m.badgeColor}`,
                    color: m.badgeColor,
                    padding: '3px 8px',
                    borderRadius: '6px',
                    fontSize: '0.7rem',
                    fontWeight: 800
                  }}>
                    {m.tier}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
                  <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#ef4444' }}>🛡️ Anti-Industrial / Data Center Shield:</strong>
                    <div style={{ color: '#cbd5e1', marginTop: '2px' }}>{m.antiIndustrialShield}</div>
                  </div>

                  <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#10b981' }}>🚜 Ag / CEA Exemption Statutory Code:</strong>
                    <div style={{ color: '#cbd5e1', marginTop: '2px' }}>{m.agCeaExemption}</div>
                  </div>

                  <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#00FFFF' }}>💧 Aquifer Security &amp; Hydrology:</strong>
                    <div style={{ color: '#cbd5e1', marginTop: '2px' }}>{m.aquiferSecurity}</div>
                  </div>

                  <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#f59e0b' }}>🔊 Acoustic Noise Floor &amp; Topography:</strong>
                    <div style={{ color: '#cbd5e1', marginTop: '2px' }}>{m.acousticBaseline}</div>
                  </div>

                  <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px 10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#c084fc' }}>🎭 Donor Transit &amp; Cultural Integration:</strong>
                    <div style={{ color: '#cbd5e1', marginTop: '2px' }}>{m.donorRadius}</div>
                  </div>
                </div>

                <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: 'auto', paddingTop: '6px' }}>
                  Key Municipalities: {m.keyTowns}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 4: LIVE CONDITION EVALUATION ENGINE (SCORER) */}
      {/* ========================================================================= */}
      {activeSection === 'calculator' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1.2fr) minmax(320px, 1fr)', gap: '20px' }}>
          {/* Input Controls */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '10px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#00FFFF' }}>
              ⚖️ Live Condition Scoring Engine
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>
              Adjust parcel parameters to simulate condition scoring against the 6 weighted NoCo acquisition dimensions.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 600 }}>Parcel Address / Nickname:</label>
                <input
                  type="text"
                  value={evalAddress}
                  onChange={e => setEvalAddress(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    marginTop: '4px'
                  }}
                />
              </div>

              {/* Sliders */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Acreage (Target: 10–25 ac):</span>
                  <span style={{ color: '#00FFFF', fontWeight: 800 }}>{evalAcres} acres</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="80"
                  step="0.5"
                  value={evalAcres}
                  onChange={e => setEvalAcres(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#00FFFF' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Asking Price:</span>
                  <span style={{ color: '#10b981', fontWeight: 800 }}>${evalPrice.toLocaleString()} (${Math.round(evalPrice / (evalAcres || 1)).toLocaleString()}/ac)</span>
                </div>
                <input
                  type="range"
                  min="30000"
                  max="1200000"
                  step="10000"
                  value={evalPrice}
                  onChange={e => setEvalPrice(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#10b981' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Acoustic Topography &amp; Bowl Rake (25% Weight):</span>
                  <span style={{ color: '#c084fc', fontWeight: 800 }}>{evalAcoustic} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalAcoustic}
                  onChange={e => setEvalAcoustic(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#c084fc' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Water Rights, Springs &amp; Hydrology (20% Weight):</span>
                  <span style={{ color: '#38bdf8', fontWeight: 800 }}>{evalWater} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalWater}
                  onChange={e => setEvalWater(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#38bdf8' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>CEA &amp; Agritourism Zoning Flexibility (15% Weight):</span>
                  <span style={{ color: '#10b981', fontWeight: 800 }}>{evalZoning} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalZoning}
                  onChange={e => setEvalZoning(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#10b981' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1' }}>
                  <span>Industrial / Sprawl / Data Center Shield (15% Weight):</span>
                  <span style={{ color: '#ef4444', fontWeight: 800 }}>{evalShield} / 100</span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="1"
                  value={evalShield}
                  onChange={e => setEvalShield(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#ef4444' }}
                />
              </div>

              <button
                onClick={handleAddCandidate}
                style={{
                  background: 'linear-gradient(135deg, #00FFFF, #7A288A)',
                  border: 'none',
                  color: '#000000',
                  padding: '12px',
                  borderRadius: '6px',
                  fontWeight: 900,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  marginTop: '8px'
                }}
              >
                + Commit to Candidate Queue &amp; Start 112 Qs Audit
              </button>
            </div>
          </div>

          {/* Real-time Verdict Output */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.85)',
            border: `2px solid ${getVerdictColor(evalResult.verdict)}`,
            borderRadius: '10px',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '16px'
          }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Condition Engine Evaluation Output
              </div>
              <h2 style={{ margin: '8px 0 0 0', fontSize: '1.6rem', color: '#ffffff' }}>
                {evalResult.compositeScore}% Composite
              </h2>
              <div style={{
                display: 'inline-block',
                marginTop: '8px',
                background: `${getVerdictColor(evalResult.verdict)}25`,
                border: `1px solid ${getVerdictColor(evalResult.verdict)}`,
                color: getVerdictColor(evalResult.verdict),
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 900
              }}>
                {evalResult.verdict}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '4px' }}>
                <span style={{ color: '#94a3b8' }}>Price per Acre:</span>
                <span style={{ fontWeight: 800, color: '#ffffff' }}>${evalResult.pricePerAcre.toLocaleString()} / ac</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '4px' }}>
                <span style={{ color: '#94a3b8' }}>Acreage Dimension Score (15% wt):</span>
                <span style={{ fontWeight: 800, color: '#00FFFF' }}>{evalResult.acreageScore} / 100</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '4px' }}>
                <span style={{ color: '#94a3b8' }}>Acoustic Topography (25% wt):</span>
                <span style={{ fontWeight: 800, color: '#c084fc' }}>{evalAcoustic} / 100</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '4px' }}>
                <span style={{ color: '#94a3b8' }}>Water Rights &amp; Hydrology (20% wt):</span>
                <span style={{ fontWeight: 800, color: '#38bdf8' }}>{evalWater} / 100</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '4px' }}>
                <span style={{ color: '#94a3b8' }}>Zoning Flexibility (15% wt):</span>
                <span style={{ fontWeight: 800, color: '#10b981' }}>{evalZoning} / 100</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '4px' }}>
                <span style={{ color: '#94a3b8' }}>Industrial Shield (15% wt):</span>
                <span style={{ fontWeight: 800, color: '#ef4444' }}>{evalShield} / 100</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94a3b8' }}>Price Efficiency (10% wt):</span>
                <span style={{ fontWeight: 800, color: '#f59e0b' }}>{evalResult.priceScore} / 100</span>
              </div>
            </div>

            <a
              href={evalResult.lookupUrl}
              target="_blank"
              rel="noreferrer"
              style={{
                textAlign: 'center',
                background: 'rgba(0, 255, 255, 0.1)',
                border: '1px solid #00FFFF',
                color: '#00FFFF',
                padding: '10px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 700,
                textDecoration: 'none'
              }}
            >
              🔍 Live Zillow Lookup Feed for this Parcel
            </a>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SECTION 5: MULTI-COUNTY LIVE LOOKUP LAUNCHPAD */}
      {/* ========================================================================= */}
      {activeSection === 'live_search' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <h3 style={{ margin: '0 0 6px 0', color: '#00FFFF', fontSize: '1.1rem' }}>
              🌐 Multi-County Direct Live Feed &amp; GIS Launchpad
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5 }}>
              One-click pre-configured queries connecting to live MLS listings, LandWatch acreage streams, and official county GIS cadastral maps pre-filtered to the NoCo 10–40 acre sweet spot and asking prices under $600k.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {[
              {
                region: 'Tompkins County, NY (Ithaca / Danby / Lansing)',
                tags: '10–40 ac &bull; &lt;$600k &bull; Cornell CEA &bull; Town Code § 144-202.1',
                zillowQuery: 'https://www.zillow.com/tompkins-county-ny/land/',
                landWatchQuery: 'https://www.landwatch.com/new-york-land-for-sale/tompkins-county',
                countyGis: 'https://www.tompkinscountyny.gov/gis'
              },
              {
                region: 'Windham & Addison Counties, VT (Grafton / Middlebury)',
                tags: '10–35 ac &bull; Act 250 Protected &bull; Glacial Springs &bull; &lt;30 dBA',
                zillowQuery: 'https://www.zillow.com/windham-county-vt/land/',
                landWatchQuery: 'https://www.landwatch.com/vermont-land-for-sale/windham-county',
                countyGis: 'https://maps.vcgi.vermont.gov/parcelviewer/'
              },
              {
                region: 'Hunterdon & Warren Counties, NJ (Ag Preservation)',
                tags: '10–30 ac &bull; 110+ Data Center Bans &bull; NJ Right to Farm &bull; 1.5hr NYC',
                zillowQuery: 'https://www.zillow.com/hunterdon-county-nj/land/',
                landWatchQuery: 'https://www.landwatch.com/new-jersey-land-for-sale/hunterdon-county',
                countyGis: 'https://njogis-newjersey.opendata.arcgis.com/'
              },
              {
                region: 'Ottawa County, MI (Jenison / Georgetown Twp)',
                tags: '10–30 ac &bull; Great Lakes Water Table &bull; SW Lake Breezes &bull; Home Base',
                zillowQuery: 'https://www.zillow.com/ottawa-county-mi/land/',
                landWatchQuery: 'https://www.landwatch.com/michigan-land-for-sale/ottawa-county',
                countyGis: 'https://www.miottawa.org/Property/'
              }
            ].map((feed, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(0, 255, 255, 0.25)',
                  borderRadius: '10px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '12px'
                }}
              >
                <div>
                  <h4 style={{ margin: '0 0 4px 0', color: '#ffffff', fontSize: '0.95rem' }}>{feed.region}</h4>
                  <div style={{ fontSize: '0.75rem', color: '#00FFFF', marginBottom: '12px' }} dangerouslySetInnerHTML={{ __html: feed.tags }} />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <a
                    href={feed.zillowQuery}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      textAlign: 'center',
                      background: 'rgba(0, 255, 255, 0.1)',
                      border: '1px solid #00FFFF',
                      color: '#00FFFF',
                      padding: '8px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      textDecoration: 'none'
                    }}
                  >
                    🔍 Zillow Filtered Land Feed
                  </a>
                  <a
                    href={feed.landWatchQuery}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      textAlign: 'center',
                      background: 'rgba(16, 185, 129, 0.1)',
                      border: '1px solid #10b981',
                      color: '#10b981',
                      padding: '8px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      textDecoration: 'none'
                    }}
                  >
                    🚜 LandWatch Acreage Feed
                  </a>
                  <a
                    href={feed.countyGis}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      textAlign: 'center',
                      background: 'rgba(122, 40, 138, 0.2)',
                      border: '1px solid #7A288A',
                      color: '#c084fc',
                      padding: '8px',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      textDecoration: 'none'
                    }}
                  >
                    🏛️ County Official GIS &amp; Parcel Maps
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
'''

target_path = r"C:\AI-BS\frontend\src\components\NocoPropertiesTracker.jsx"
with open(target_path, "w", encoding="utf-8") as f:
    f.write(CODE)
print(f"Successfully wrote {len(CODE)} bytes to {target_path}")
