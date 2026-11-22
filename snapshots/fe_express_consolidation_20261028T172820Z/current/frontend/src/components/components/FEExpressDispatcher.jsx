/** @jsxRuntime classic */
import FEExpressDriverReports from '/src/components/FEExpressDriverReports.jsx';
import { boardForSource } from '/src/utils/feExpressBoardSources.mjs';
import { PortalWorkspace, PortalSaveButton, usePortalState } from '/src/utils/feExpressWorkspace.jsx';
import { rankLoads } from '/src/utils/feExpressLoadSearch.mjs';
import dispatchProfile from '/src/config/feExpressProfile.json';
import React, { useState, useEffect } from '/src/utils/applicationReact.js';

function classifyEquipmentLocally(equipmentStr, weight = 0) {
  const eqLower = (equipmentStr || '').toLowerCase();
  const semiKeywords = ["53'", "semi", "tractor", "double drop", "heavy haul", "lowboy"];
  const isSemi = semiKeywords.some(s => eqLower.includes(s)) && !['box', 'van', 'straight'].some(k => eqLower.includes(k));

  const vanKeywords = ['cargo van', 'sprinter', 'transit', 'promaster', 'cube van', 'van'];
  const boxKeywords = ["24'", "26'", 'box truck', 'straight truck', 'boxtruck', 'box', 'straight'];

  let isVan = vanKeywords.some(v => eqLower.includes(v)) && !["53'", 'dry van', 'reefer'].some(b => eqLower.includes(b));
  let isBox = boxKeywords.some(b => eqLower.includes(b)) && !isSemi;

  if (!isVan && !isBox && !isSemi) {
    if (eqLower.includes('hotshot') || eqLower.includes('partial')) {
      if (weight > 0 && weight <= 4500) {
        isVan = true;
      } else if (weight > 0 && weight <= 10000) {
        isBox = true;
      }
    }
  }

  let vehicleType = 'UNKNOWN';
  if (isBox) vehicleType = 'BOX_TRUCK';
  else if (isVan) vehicleType = 'CARGO_VAN';

  const requiresLiftgate = ['liftgate', 'lift gate', 'lift-gate', 'lg req', 'needs lg'].some(k => eqLower.includes(k)) && !['no liftgate', 'no lift gate', 'no lift-gate'].some(k => eqLower.includes(k));

  return { isBox, isVan, vehicleType, isSemi, requiresLiftgate };
}

function evaluateLocally(payload) {
  const weight = Number(payload.weight_lbs ?? 0);
  const { isBox, isVan, vehicleType, isSemi, requiresLiftgate } = classifyEquipmentLocally(payload.equipment_type, weight);
  const underWeight = (isBox && weight <= 10000.0) || (isVan && weight <= 4500.0);
  const miles = Number(payload.total_miles);
  const deadhead = Number(payload.deadhead_miles ?? 0);
  const pay = Number(payload.flat_rate_pay ?? 0);
  if (![weight, Number(payload.total_miles), Number(payload.deadhead_miles ?? 0), pay].every(Number.isFinite) || weight <= 0 || Number(payload.total_miles) <= 0 || Number(payload.deadhead_miles ?? 0) < 0 || pay < 0) {
    throw new Error('Enter positive weight and loaded miles, with nonnegative deadhead and pay.');
  }
  const rpm = Number((pay / miles).toFixed(2));
  const true_rpm = Number((pay / (miles + deadhead)).toFixed(2));

  let score = 'Reject';
  let priority_tier = 3;
  const matchedFleet = isBox || isVan;

  if (matchedFleet && underWeight && !isSemi) {
    if (requiresLiftgate) {
      score = 'Reject';
      priority_tier = 3;
    } else if (true_rpm >= 2.50) {
      score = 'Greenlight';
      priority_tier = 1;
    } else if (true_rpm >= 2.00) {
      score = 'Caution';
      priority_tier = 2;
    }
  }
  return {
    ...payload,
    rpm,
    true_rpm,
    score,
    priority_tier,
    is_valid_box_truck: isBox,
    is_valid_cargo_van: isVan,
    vehicle_match: vehicleType,
    under_weight_limit: underWeight,
    requires_liftgate: requiresLiftgate
  };
}

function getLocalBrokerCredit(brokerName) {
  const name = (brokerName || '').toLowerCase();
  if (name.includes('sureway') || name.includes('anderson trucking')) {
    return { score: 96, rating: 'A+', days_to_pay: 22, factoring: 'APPROVED', color: '#10B981' };
  }
  if (name.includes('echo global')) {
    return { score: 98, rating: 'A+', days_to_pay: 20, factoring: 'APPROVED', color: '#10B981' };
  }
  if (name.includes('robinson')) {
    return { score: 99, rating: 'A+', days_to_pay: 19, factoring: 'APPROVED', color: '#10B981' };
  }
  if (name.includes('allen lund')) {
    return { score: 95, rating: 'A+', days_to_pay: 21, factoring: 'APPROVED', color: '#10B981' };
  }
  if (name.includes('atlantic')) {
    return { score: 91, rating: 'A', days_to_pay: 25, factoring: 'APPROVED', color: '#10B981' };
  }
  if (name.includes('ampersand')) {
    return { score: 85, rating: 'B+', days_to_pay: 34, factoring: 'CONDITIONAL', color: '#F59E0B' };
  }
  if (name.includes('dsf toad')) {
    return { score: 88, rating: 'B+', days_to_pay: 31, factoring: 'APPROVED', color: '#10B981' };
  }
  return { score: 82, rating: 'B', days_to_pay: 35, factoring: 'VERIFY', color: '#94A3B8' };
}

function getLocalSpotBenchmark(origin, dest, currentRpm, miles) {
  const avg = 2.45;
  const high = 3.20;
  const current = parseFloat(currentRpm || 0);
  const diff = (current - avg).toFixed(2);
  let assessment = 'TARGET';
  let badgeColor = '#38BDF8';
  if (current >= high) {
    assessment = 'PREMIUM';
    badgeColor = '#10B981';
  } else if (current >= avg) {
    assessment = 'ABOVE TARGET';
    badgeColor = '#34D399';
  } else if (current < 2.00) {
    assessment = 'LOWBALL';
    badgeColor = '#EF4444';
  }
  return { avg_rpm: avg, high_rpm: high, diff, assessment, badgeColor, source: 'Fixed illustrative targets; not measured market rates' };
}

// Official free board destinations. These links do not import or post loads.
const FREE_LOAD_BOARDS = [
  { id: 'trulos', name: 'Trulos', url: 'https://www.trulos.com/load-board/', access: 'Free search · No account required', note: 'Open the provider board. Existing Trulos refresh is available above.' },
  { id: 'freightfinder', name: 'FreightFinder', url: 'https://www.freightfinder.com/', access: 'Free search · No account required', note: 'Search by origin, destination and equipment. Most listings are full truckloads; confirm box-truck suitability.' },
  { id: 'directfreight', name: 'Direct Freight', url: 'https://www.directfreight.com/home/', access: 'Free account available', note: 'Search on the provider website. Some tools or contact details may require an account or paid plan.' },
];

export const DEVIN_DISPATCH_PROFILE = dispatchProfile;

function buildDevinMailto(brokerEmail, load, bidSubject, bidBody) {
  const to = (brokerEmail && brokerEmail.includes('@')) ? brokerEmail.trim() : '';
  const subject = encodeURIComponent(bidSubject || `FE Express LLC - Load ${load.load_id} (${load.origin_city_state} -> ${load.dest_city_state})`);
  const body = encodeURIComponent(bidBody || `Hello ${load.broker_name},\n\nWe have a 26' Box Truck (Dock High - No Liftgate) ready near ${load.origin_city_state}.\nCan lock down load ${load.load_id}.\n\nDirect Dispatch: ${DEVIN_DISPATCH_PROFILE.name}\nPhone: ${DEVIN_DISPATCH_PROFILE.phone}\nEmail: ${DEVIN_DISPATCH_PROFILE.email}\n${DEVIN_DISPATCH_PROFILE.company} | ${DEVIN_DISPATCH_PROFILE.mc} | ${DEVIN_DISPATCH_PROFILE.usdot}\nVerify carrier details and broker terms before sending.`);
  return `mailto:${to}?subject=${subject}&body=${body}`;
}

function DispatcherContent({ BACKEND_URL = 'http://127.0.0.1:8080', request = fetch }) {
  const baseUrl = BACKEND_URL || 'http://127.0.0.1:8080';
  const [loads, setLoads] = useState(/** @type {any[]} */ ([]));
  const [status, setStatus] = useState({
    status: 'CONNECTING',
    total_loads: 0,
    greenlight_loads: 0
  });
  const [loading, setLoading] = useState(false);
  const [filterScore, setFilterScore] = usePortalState('filterScore', 'ALL');
  const [selectedBoard, setSelectedBoard] = usePortalState('selectedBoard', 'all');
  const [reportDriver, setReportDriver] = usePortalState('reportDriver', 'OWNER-DEVIN');
  const [reportsOpened, setReportsOpened] = usePortalState('reportsOpened', false);
  const [logRequest, setLogRequest] = useState(0);
  const [tripForReport, setTripForReport] = usePortalState('tripForReport', '');

  // Ad-hoc Quick Calculator
  const [calcOrigin, setCalcOrigin] = usePortalState('calcOrigin', '');
  const [calcDest, setCalcDest] = usePortalState('calcDest', '');
  const [calcEquip, setCalcEquip] = usePortalState('calcEquip', '');
  const [calcMiles, setCalcMiles] = usePortalState('calcMiles', '');
  const [calcDeadhead, setCalcDeadhead] = usePortalState('calcDeadhead', '');
  const [calcPay, setCalcPay] = usePortalState('calcPay', '');
  const [calcWeight, setCalcWeight] = usePortalState('calcWeight', '');
  const [calcBroker, setCalcBroker] = usePortalState('calcBroker', '');
  const [evalResult, setEvalResult] = useState(null);
  const [homeBase, setHomeBase] = usePortalState('homeBase', 'Grand Rapids, MI');
  const [syncingLive, setSyncingLive] = useState(false);
  const [feedError, setFeedError] = useState('');
  const [lastBoardRead, setLastBoardRead] = useState('');
  const [lastPublicSync, setLastPublicSync] = useState('');
  const [selectedBidLoad, setSelectedBidLoad] = useState(null);
  const [bidData, setBidData] = useState(null);

  // Phase 1: Smart Backhaul Radar & Alert Sentinel States
  const [selectedBackhaulLoad, setSelectedBackhaulLoad] = useState(null);
  const [backhaulsList, setBackhaulsList] = useState(/** @type {any[]} */ ([]));
  const [loadingBackhauls, setLoadingBackhauls] = useState(false);
  const [activeAlertBanner, setActiveAlertBanner] = useState(null);

  const handleOpenBackhaulModal = async (load) => {
    setSelectedBackhaulLoad(load);
    setLoadingBackhauls(true);
    setBackhaulsList([]);
    try {
      const res = await request(`${baseUrl}/api/v1/fe-express/loads/${load.load_id}/backhauls?home_base=${encodeURIComponent(homeBase)}`);
      if (res.ok) {
        const data = await res.json();
        setBackhaulsList(data.backhauls || []);
        return;
      }
    } catch {}
    // Fallback: local backhaul match
    const dest = load.dest_city_state || '';
    const destState = dest.includes(',') ? dest.split(',')[1].trim().toUpperCase() : '';
    const matches = loads.filter(l => {
      if (l.load_id === load.load_id) return false;
      const lOrig = l.origin_city_state || '';
      return destState && (lOrig.toUpperCase().includes(destState) || lOrig.toUpperCase().includes(dest.toUpperCase()));
    });
    setBackhaulsList(matches.length > 0 ? matches : loads.slice(0, 3));
    setLoadingBackhauls(false);
  };

  // Search & Filter Bar Variables (Live Querying)
  const [searchOrigin, setSearchOrigin] = usePortalState('searchOrigin', '');
  const [searchEquipment, setSearchEquipment] = usePortalState('searchEquipment', '');
  const [searchMiles, setSearchMiles] = usePortalState('searchMiles', '');
  const [searchBroker, setSearchBroker] = usePortalState('searchBroker', '');
  const [searchDest, setSearchDest] = usePortalState('searchDest', '');
  const [minRpm, setMinRpm] = usePortalState('minRpm', '');
  const [minFlatPay, setMinFlatPay] = usePortalState('minFlatPay', '');
  const [maxWeight, setMaxWeight] = usePortalState('maxWeight', '');
  const [maxDeadhead, setMaxDeadhead] = usePortalState('maxDeadhead', '');
  const [vehicleFilter, setVehicleFilter] = usePortalState('vehicleFilter', 'ALL'); // 'ALL' | 'BOX_TRUCK' | 'CARGO_VAN'
  const [viewMode, setViewMode] = usePortalState('viewMode', () => (typeof window !== 'undefined' && window.innerWidth < 768 ? 'cards' : 'table')); // 'table' | 'cards'
  const [showEvaluator, setShowEvaluator] = usePortalState('showEvaluator', () => (typeof window !== 'undefined' && window.innerWidth < 768 ? false : true));

  // Phase 3 & 4: Active Loads, BOL Photos, Profit & Driver Settlements States
  const [activeSubTab, setActiveSubTab] = usePortalState('activeSubTab', 'board'); // 'board' | 'active_dispatches' | 'profit_ledger' | 'drivers_ledger'
  const [activeDispatches, setActiveDispatches] = useState(/** @type {any[]} */ ([]));

  // Subcontractor 1099 Drivers & Payroll State
  const [driversList, setDriversList] = useState(/** @type {any[]} */ ([]));
  const [settlementsList, setSettlementsList] = useState(/** @type {any[]} */ ([]));
  const [showAddDriverModal, setShowAddDriverModal] = useState(false);
  const [showAddSettlementModal, setShowAddSettlementModal] = useState(false);
  const [selectedDriverForSettlement, setSelectedDriverForSettlement] = useState(null);

  // New Driver Form State
  const [newDriverName, setNewDriverName] = usePortalState('newDriverName', '');
  const [newDriverPhone, setNewDriverPhone] = usePortalState('newDriverPhone', '');
  const [newDriverEmail, setNewDriverEmail] = usePortalState('newDriverEmail', '');
  const [newDriverSSN4, setNewDriverSSN4] = usePortalState('newDriverSSN4', '');
  const [newDriverDL, setNewDriverDL] = usePortalState('newDriverDL', '');
  const [newDriverDLState, setNewDriverDLState] = usePortalState('newDriverDLState', 'MI');
  const [newDriverPayModel, setNewDriverPayModel] = usePortalState('newDriverPayModel', 'PERCENT_GROSS'); // 'PERCENT_GROSS' | 'PER_MILE' | 'FLAT_DAY'
  const [newDriverPayRate, setNewDriverPayRate] = usePortalState('newDriverPayRate', '25'); // 25% or 0.55/mi or 200/day
  const [newDriverMedCardExp, setNewDriverMedCardExp] = usePortalState('newDriverMedCardExp', '2027-01-01');
  const [newDriverMVRStatus, setNewDriverMVRStatus] = usePortalState('newDriverMVRStatus', 'CLEARED');
  const [newDriverW9Status, setNewDriverW9Status] = usePortalState('newDriverW9Status', 1);
  const [newDriverNotes, setNewDriverNotes] = usePortalState('newDriverNotes', '');

  // New Settlement Form State
  const [settleDate, setSettleDate] = usePortalState('settleDate', new Date().toISOString().slice(0, 10));
  const [settleLane, setSettleLane] = usePortalState('settleLane', '');
  const [settleMiles, setSettleMiles] = usePortalState('settleMiles', '');
  const [settleGrossPay, setSettleGrossPay] = usePortalState('settleGrossPay', '');
  const [settleFuelDeduct, setSettleFuelDeduct] = usePortalState('settleFuelDeduct', '0');
  const [settleAdvance, setSettleAdvance] = usePortalState('settleAdvance', '0');
  const [settlePayMethod, setSettlePayMethod] = usePortalState('settlePayMethod', 'ZELLE');
  const [settleNotes, setSettleNotes] = usePortalState('settleNotes', '');

  // Owner-Operator High-ROI State
  const [triangulationChains, setTriangulationChains] = useState(/** @type {any[]} */ ([]));
  const [loadingChains, setLoadingChains] = useState(false);
  const [iftaSummary, setIftaSummary] = useState(null);
  const [factoringSubmissions, setFactoringSubmissions] = useState(/** @type {any[]} */ ([]));
  const [navHazards, setNavHazards] = useState(null);
  const [dvirDashboard, setDvirDashboard] = useState(null);

  // Apex Dispatcher Cockpit 5-Pillar States
  const [selectedLoadForBlast, setSelectedLoadForBlast] = useState(null);
  const [blastBidAmount, setBlastBidAmount] = usePortalState('blastBidAmount', '');
  const [blastStatus, setBlastStatus] = useState(null);
  const [horizonMapModal, setHorizonMapModal] = useState(null);
  const [detentionEscrowModal, setDetentionEscrowModal] = useState(null);

  // Apex Logistics Missing Suite States (Dock Intelligence, Live CPM, Accessorial Claims)
  const [dockIntelModal, setDockIntelModal] = useState(null);
  const [cpmCalibrationModal, setCpmCalibrationModal] = useState(null);
  const [accessorialClaimModal, setAccessorialClaimModal] = useState(null);
  const [cpmParams, setCpmParams] = usePortalState('cpmParams', { diesel_price: 3.85, truck_mpg: 9.5, driver_cpm: 0.60, target_margin: 25.0 });
  const [claimParams, setClaimParams] = usePortalState('claimParams', { claim_type: 'DETENTION', units: 2.5, rate: 75.0 });
  const [claimResult, setClaimResult] = useState(null);

  // Elite Tier Scaling Suite (Fuel Arbitrage, Capacity Broadcast, Lumper Escrow)
  const [fuelOptimizerModal, setFuelOptimizerModal] = useState(null);
  const [capacityBroadcastModal, setCapacityBroadcastModal] = useState(null);
  const [broadcastStatus, setBroadcastStatus] = useState(null);

  // Next-Gen 5 Enterprise Modules States
  const [meshModal, setMeshModal] = useState(null);
  const [meshMatchResult, setMeshMatchResult] = useState(null);
  const [fatigueModal, setFatigueModal] = useState(null);
  const [fatigueResult, setFatigueResult] = useState(null);
  const [scope3Modal, setScope3Modal] = useState(null);
  const [scope3Result, setScope3Result] = useState(null);
  const [blackSwanModal, setBlackSwanModal] = useState(null);
  const [blackSwanResult, setBlackSwanResult] = useState(null);
  const [arHudModal, setArHudModal] = useState(null);
  const [arHudData, setArHudData] = useState(null);




  const openShipmentPaperwork = (dispatch) => {
    setTripForReport(dispatch.dispatch_id);
    setReportsOpened(true);
    setActiveSubTab('driver_reports');
  };

  const handleBookLoad = async (load) => {
    if (!window.confirm(`Save load ${load.load_id} to the active dispatch queue? Broker confirmation remains separate.`)) return;
    try {
      const res = await request(`${baseUrl}/api/v1/fe-express/book-load`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(load)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success !== true || !data.dispatch_id) throw new Error('Missing saved dispatch confirmation');
      await refreshDispatchesAfterUpdate();
      setActiveSubTab('active_dispatches');
      alert(`Load ${load.load_id} saved to the dispatch queue. Confirm the booking with the broker separately.`);
    } catch (error) {
      alert('Booking was not confirmed. Refresh the dispatch list before retrying; no local booking has been created.');
    }
  };
  const triggerLivePublicSync = async () => {
    try {
      setSyncingLive(true);
      const res = await request(`${baseUrl}/api/v1/fe-express/loads/sync-public?home_base=${encodeURIComponent(homeBase)}`, { method: 'POST' });
      if (!res.ok) throw new Error(`Public board refresh returned HTTP ${res.status}`);
      const result = await res.json();
      if (result.success !== true || !Array.isArray(result.loads) || result.loads.length === 0) {
        throw new Error('No fresh public listings were confirmed. The provider may be unavailable.');
      }
      setLastPublicSync(new Date().toLocaleString());
      setFeedError('');
      await fetchLoads();
    } catch (e) {
      setFeedError(e instanceof Error ? e.message : 'Public board refresh failed.');
    } finally {
      setSyncingLive(false);
    }
  };

  const handleOpenBidModal = async (load) => {
    setSelectedBidLoad(load);
    setBidData(null);
    try {
      const res = await request(`${baseUrl}/api/v1/fe-express/loads/${load.load_id}/bid`);
      if (res.ok) {
        const data = await res.json();
        setBidData(data.bid);
        return;
      }
    } catch {}
    // Local bid generation fallback using Devin's direct dispatch contacts
    const targetBid = Math.round((load.flat_rate_pay || 600) * 1.10);
    setBidData({
      subject: `RATE CONFIRMATION / TRUCK IN HAND: ${load.origin_city_state} -> ${load.dest_city_state} [${load.load_id}] - FE Express LLC`,
      email_body: `Hello ${load.broker_name} Team,\n\nWe have an empty 26' Box Truck (Dock High - No Liftgate) & Pallet Jack ready near ${load.origin_city_state} (Home: ${homeBase}) and can lock down load ${load.load_id} immediately.\n\n• Origin: ${load.origin_city_state}\n• Destination: ${load.dest_city_state}\n• Trip: ${load.total_miles} loaded miles\n• Posted Pay: $${load.flat_rate_pay}\n• Our All-In Rate Bid: $${targetBid} (Clean rate)\n\nAuthority: ${DEVIN_DISPATCH_PROFILE.mc} | ${DEVIN_DISPATCH_PROFILE.usdot}\nInsurance: $1,000,000 Auto Liability / $100,000 Cargo\n\nPlease send rate confirmation to Devin.feexpress@gmail.com or call Devin directly at (616) 315-7483.\n\nThank you,\nDevin | FE Express Dispatch\nDirect: (616) 315-7483\nEmail: Devin.feexpress@gmail.com`,
      sms_text: `FE Express (${DEVIN_DISPATCH_PROFILE.mc}) has a 26' box truck empty at ${load.origin_city_state} for load ${load.load_id} (${load.origin_city_state}->${load.dest_city_state}). Can take for $${targetBid} all-in. Call or text Devin at (616) 315-7483.`
    });
  };

  const fetchActiveDispatches = async () => {
    const response = await request(`${baseUrl}/api/v1/fe-express/active-dispatches`);
    if (!response.ok) throw new Error(`Dispatch refresh returned HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data.dispatches)) throw new Error('Dispatch response is missing its list.');
    setActiveDispatches(data.dispatches);
  };

  // A failed refresh after a successful update must not suggest repeating the update.
  const refreshDispatchesAfterUpdate = async () => {
    try {
      await fetchActiveDispatches();
    } catch (error) {
      console.warn('Dispatch updated; the list could not be refreshed:', error);
      alert('The dispatch update completed, but the list could not be refreshed. Refresh the list before making another update.');
    }
  };

  const fetchLoads = async () => {
    try {
      setLoading(true);
      const res = await request(`${baseUrl}/api/v1/fe-express/loads?limit=50`);
      if (!res.ok) throw new Error(`Board read returned HTTP ${res.status}`);
      const data = await res.json();
      if (!Array.isArray(data.loads)) throw new Error('Board response is missing its list.');
      setLoads(data.loads.map(load => ({ ...load, source: String(load.source || 'Saved listing').replace(/\(Live\)/gi, '(cached)'), status: 'CACHED' })));
      setLastBoardRead(new Date().toLocaleTimeString());
      const stRes = await request(`${baseUrl}/api/v1/fe-express/status`);
      if (stRes.ok) {
        const stData = await stRes.json();
        setStatus(stData);
      }

      // Use the same dispatch reader for polling and post-update refreshes.
      await fetchActiveDispatches();

      // Fetch 1099 Drivers
      const drvRes = await request(`${baseUrl}/api/v1/fe-express/drivers`);
      if (drvRes.ok) {
        const drvData = await drvRes.json();
        if (drvData.drivers) {
          setDriversList(drvData.drivers);
        }
      }

      // Fetch Driver Settlements
      const stlRes = await request(`${baseUrl}/api/v1/fe-express/settlements`);
      if (stlRes.ok) {
        const stlData = await stlRes.json();
        if (stlData.settlements) {
          setSettlementsList(stlData.settlements);
        }
      }
    } catch (error) {
      setFeedError(error instanceof Error ? error.message : 'Board connection unavailable.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDriver = async (e) => {
    e.preventDefault();
    if (!newDriverName.trim()) {
      alert('Driver name is required.');
      return;
    }
    const newDriverObj = {
      driver_id: `DRV-${Date.now().toString().slice(-6)}`,
      full_name: newDriverName.trim(),
      phone: newDriverPhone.trim(),
      email: newDriverEmail.trim(),
      tax_id_or_ssn_last4: newDriverSSN4.trim() || 'XXXX',
      driver_license_num: newDriverDL.trim(),
      driver_license_state: newDriverDLState.trim(),
      pay_model: newDriverPayModel,
      pay_rate: parseFloat(newDriverPayRate) || 25,
      medical_card_exp: newDriverMedCardExp,
      mvr_check_status: newDriverMVRStatus,
      w9_on_file: parseInt(newDriverW9Status, 10),
      notes: newDriverNotes.trim()
    };

    try {
      const res = await request(`${baseUrl}/api/v1/fe-express/drivers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newDriverObj)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const saved = await res.json();
      if (saved.success !== true) throw new Error('Save not confirmed');
      {
        alert(`Subcontract driver ${newDriverName} saved successfully to database!`);
      }
    } catch (error) {
      alert('Driver save was not confirmed. Your entries have been kept; refresh before retrying.');
      return;
    }

    setDriversList(prev => [newDriverObj, ...prev.filter(d => d.driver_id !== newDriverObj.driver_id)]);
    setShowAddDriverModal(false);
    // Reset form
    setNewDriverName('');
    setNewDriverPhone('');
    setNewDriverEmail('');
    setNewDriverSSN4('');
    setNewDriverDL('');
    setNewDriverNotes('');
  };

  const handleRecordSettlement = async (e) => {
    e.preventDefault();
    if (!selectedDriverForSettlement) {
      alert('Please select a driver to settle.');
      return;
    }

    const gross = parseFloat(settleGrossPay) || 0;
    const miles = parseFloat(settleMiles) || 0;
    const fuelDeduct = parseFloat(settleFuelDeduct) || 0;
    const advance = parseFloat(settleAdvance) || 0;

    let contractorEarned = 0;
    if (selectedDriverForSettlement.pay_model === 'PERCENT_GROSS') {
      contractorEarned = Math.round(gross * (selectedDriverForSettlement.pay_rate / 100));
    } else if (selectedDriverForSettlement.pay_model === 'PER_MILE') {
      contractorEarned = Math.round(miles * selectedDriverForSettlement.pay_rate);
    } else {
      contractorEarned = selectedDriverForSettlement.pay_rate; // Flat Day
    }

    const net1099 = Math.round(contractorEarned - fuelDeduct - advance);

    const settlementObj = {
      settlement_id: `SETTLE-${Date.now().toString().slice(-6)}`,
      driver_id: selectedDriverForSettlement.driver_id,
      driver_name: selectedDriverForSettlement.full_name,
      dispatch_id: `DISP-${Date.now().toString().slice(-4)}`,
      trip_date: settleDate,
      origin_dest: settleLane.trim() || 'Custom Dispatch Lane',
      total_miles: miles,
      gross_load_pay: gross,
      contractor_pay: contractorEarned,
      fuel_deduction: fuelDeduct,
      cash_advance: advance,
      net_1099_payout: net1099,
      payment_status: 'PAID',
      payment_method: settlePayMethod,
      notes: settleNotes.trim()
    };

    try {
      const res = await request(`${baseUrl}/api/v1/fe-express/settlements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settlementObj)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const saved = await res.json();
      if (saved.success !== true) throw new Error('Save not confirmed');
      {
        alert(`1099 settlement of $${net1099} recorded for ${selectedDriverForSettlement.full_name}!`);
      }
    } catch (error) {
      alert('Settlement save was not confirmed. Your entries have been kept; refresh before retrying.');
      return;
    }

    setSettlementsList(prev => [settlementObj, ...prev]);
    setShowAddSettlementModal(false);
    // Reset form
    setSettleLane('');
    setSettleMiles('');
    setSettleGrossPay('');
    setSettleFuelDeduct('0');
    setSettleAdvance('0');
    setSettleNotes('');
  };

  useEffect(() => {
    fetchLoads();
    const interval = setInterval(fetchLoads, 5000); // High-speed 5-second polling
    return () => clearInterval(interval);
  }, []);

  const handleCalculate = async (e) => {
    e.preventDefault();
    const unknown = [calcOrigin, calcDest, calcEquip, calcWeight, calcMiles, calcDeadhead, calcPay].some(value => String(value).trim() === '');
    if (unknown) {
      setSearchOrigin(calcOrigin.trim()); setSearchDest(calcDest.trim());
      setSearchMiles(calcMiles); setSearchEquipment(calcEquip.trim()); setSearchBroker(calcBroker.trim());
      setMaxWeight(String(calcWeight)); setMaxDeadhead(String(calcDeadhead));
      setMinFlatPay(String(calcPay)); setMinRpm(''); setFilterScore('ALL');
      setVehicleFilter('ALL'); setSelectedBoard('all'); setEvalResult(null);
      setActiveSubTab('board');
      return;
    }
    const payload = {
      load_id: `FE-${Math.floor(100 + Math.random() * 900)}`,
      origin_city_state: calcOrigin,
      dest_city_state: calcDest,
      equipment_type: calcEquip,
      weight_lbs: parseFloat(calcWeight),
      total_miles: parseFloat(calcMiles),
      deadhead_miles: parseFloat(calcDeadhead),
      flat_rate_pay: parseFloat(calcPay),
      broker_name: calcBroker
    };
    try { evaluateLocally(payload); } catch (error) { alert(error instanceof Error ? error.message : "Invalid load values"); return; }
    try {
      const res = await request(`${baseUrl}/api/v1/fe-express/loads/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        setEvalResult(data.evaluated);
        setLoads(prev => [data.evaluated, ...prev]);
        return;
      }
    } catch {
      // Local evaluation fallback
    }
    const localEval = evaluateLocally(payload);
    setEvalResult(localEval);
    if (localEval.is_valid_box_truck && localEval.under_weight_limit) {
      setLoads(prev => [localEval, ...prev]);
    }
  };

  const filteredLoads = rankLoads(loads, { selectedBoard, filterScore, searchOrigin, searchDest, searchEquipment, searchBroker, searchMiles, minRpm, minFlatPay, maxWeight, maxDeadhead, vehicleFilter });


  return (
    <div className="fe-express-container" style={{ padding: '24px', backgroundColor: '#0B0F19', color: '#F8FAFC', minHeight: '100%', overflowY: 'auto', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <PortalSaveButton />
      <div className="fe-express-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #1E293B', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 800, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '10px' }}>
            🚚 FE EXPRESS | Box Truck Automation Hub
          </h1>
          <p style={{ margin: '4px 0 0', color: '#94A3B8', fontSize: '13px' }}>
            Real-Time RPM Scoring, Deadhead Analysis, and Automated Expediter Lead Filtering (24&apos;/26&apos; Box &amp; Straight Trucks ≤ 10,000 lbs)
          </p>
        </div>
        <div className="fe-express-header-actions" style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#1E293B', padding: '4px 10px', borderRadius: '6px', border: '1px solid #334155' }}>
            <span style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600 }}>Home Base (for Deadhead):</span>
            <input
              type="text"
              value={homeBase}
              onChange={e => setHomeBase(e.target.value)}
              style={{ backgroundColor: '#0F172A', border: '1px solid #475569', color: '#F8FAFC', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', width: '130px' }}
            />
          </div>
          <button
            onClick={triggerLivePublicSync}
            disabled={syncingLive}
            style={{
              padding: '8px 16px',
              backgroundColor: syncingLive ? '#065F46' : '#059669',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '6px',
              cursor: syncingLive ? 'not-allowed' : 'pointer',
              fontWeight: 700,
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {syncingLive ? '⏳ Refreshing Trulos...' : '🌐 Pull connected boards'}
          </button>
          <button
            onClick={fetchLoads}
            style={{ padding: '8px 14px', backgroundColor: '#1E293B', color: '#38BDF8', border: '1px solid #38BDF8', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '13px' }}
          >
            🔄 Refresh saved results
          </button>
        </div>
      </div>

      <p role="status" style={{ color: feedError ? '#FCA5A5' : '#CBD5E1' }}>
        Free public listings · Saved board checked: {lastBoardRead || 'not yet'} · Public refresh confirmed: {lastPublicSync || 'not this session'}.
        {' '}Saved listings refresh every 5 seconds while this page is open; availability and route mileage require confirmation.
        {feedError && ` ${feedError} Previously saved listings may be stale.`}
      </p>

      <section aria-label="Free load boards" style={{ marginBottom: '24px', padding: '16px', border: '1px solid #334155', borderRadius: '8px', backgroundColor: '#111827' }}>
        <h2 style={{ margin: '0 0 8px', fontSize: '18px', color: '#F8FAFC' }}>Load boards — organized by source</h2>
        <p style={{ margin: '0 0 14px', color: '#CBD5E1', fontSize: '13px' }}>
          Pull connected boards requests fresh Trulos listings. Refresh saved results reloads stored records; it does not contact every provider. Select a board below to show only its saved loads. FreightFinder and Direct Freight currently open on their own websites.
          {' '}Use the Quick Calculator below to check a load before contacting its broker. Confirm availability, equipment, weight and rate with the provider.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: '12px' }}>
          {FREE_LOAD_BOARDS.map(board => (
            <article key={board.name} style={{ padding: '14px', backgroundColor: '#0F172A', border: '1px solid #334155', borderRadius: '6px' }}>
              <h3 style={{ margin: '0 0 6px', fontSize: '16px', color: '#F8FAFC' }}>{board.name}</h3>
              <p style={{ margin: '0 0 8px', color: '#6EE7B7', fontSize: '12px' }}>{board.access}</p>
              <p style={{ color: '#CBD5E1', fontSize: 13 }}>
                {board.id === 'trulos' ? (syncingLive ? 'Pulling listings…' : feedError ? 'Refresh failed — saved results retained' : 'Importer available') : 'Website search only — import not connected'}
                <br />{loads.filter(l => boardForSource(l.source) === board.id).length} saved records loaded
                {board.id === 'trulos' && <><br />Last successful pull: {lastPublicSync || 'not this session'}</>}
              </p>
              <button type="button" aria-pressed={selectedBoard === board.id} onClick={() => { setSelectedBoard(board.id); setActiveSubTab('board'); }} style={{ padding: 9, background: selectedBoard === board.id ? '#0369a1' : '#1e293b', color: 'white', border: '1px solid #64748b', borderRadius: 5 }}>Show {board.name} loads</button>
              {board.id === 'trulos' && <button type="button" disabled={syncingLive} onClick={triggerLivePublicSync} style={{ padding: 9, marginLeft: 6 }}>Pull Trulos</button>}
              <p style={{ margin: '0 0 12px', color: '#CBD5E1', fontSize: '12px' }}>{board.note}</p>
              <a href={board.url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer"
                aria-label={`Search ${board.name} (opens in a new tab)`}
                style={{ display: 'inline-block', color: '#7DD3FC', fontWeight: 700, padding: '8px 0' }}>
                Search {board.name} ↗
              </a>
            </article>
          ))}
        </div>
        <div role="group" aria-label="Load board filter" style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 12 }}>
          {[['all', 'All boards'], ['other', 'Other / manually saved'], ['sylectus', 'Sylectus (pending)']].map(([id, title]) => <button key={id} type="button" aria-pressed={selectedBoard === id} onClick={() => { setSelectedBoard(id); setActiveSubTab('board'); }} style={{ padding: 10, background: selectedBoard === id ? '#0369a1' : '#1e293b', color: 'white', border: '1px solid #64748b', borderRadius: 5 }}>{title} ({id === 'all' ? loads.length : loads.filter(l => boardForSource(l.source) === id).length})</button>)}
        </div>
        <p role="status">Showing: {selectedBoard === 'all' ? 'All boards' : selectedBoard}. {filteredLoads.length} results from this board. Closest matches first when searching; otherwise newest received first. Unknown details require confirmation. Counts cover the records loaded on this page.</p>
        <p style={{ margin: '12px 0 0', color: '#94A3B8', fontSize: '12px' }}>
          Automatic access to additional boards requires a provider-approved feed. Sylectus remains pending; no paid plan or trial has been started.
        </p>
      </section>

      {/* KPI Cards */}
      <div className="fe-express-kpi-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Active Hub Status</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#10B981', marginTop: '4px' }}>{lastBoardRead ? 'Connected to saved board' : 'Connecting to board'}</div>
        </div>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Greenlight Loads</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#38BDF8', marginTop: '4px' }}>
            {loads.filter(l => l.score === 'Greenlight').length}
          </div>
        </div>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Total Qualified Loads</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#F3F4F6', marginTop: '4px' }}>
            {loads.length}
          </div>
        </div>
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', padding: '16px', borderRadius: '8px' }}>
          <div style={{ color: '#9CA3AF', fontSize: '12px', textTransform: 'uppercase' }}>Greenlight Threshold</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#F59E0B', marginTop: '4px' }}>≥ $2.50 / True Mi</div>
        </div>
      </div>

      {/* Telemetry Strip - 100% Native Desktop Parity */}
      <div className="fe-express-telemetry-strip" style={{
        backgroundColor: '#064E3B',
        color: '#A7F3D0',
        border: '1px solid #10B981',
        borderRadius: '6px',
        padding: '10px 14px',
        fontWeight: 'bold',
        fontSize: '13px',
        marginBottom: '12px'
      }}>
        SAVED LISTINGS (all loaded sources) | Box Truck / Light Freight: {loads.length} loads | 🌟 {loads.filter(l => l.score === 'Greenlight').length} Greenlight (≥ $2.50/mi) | ⚠️ {loads.filter(l => l.score === 'Caution').length} Caution | Terminal Home Base: {homeBase}
      </div>

      {/* Devin Dispatch Profile & Quick Contact Header */}
      <div className="fe-express-profile-card" style={{
        backgroundColor: '#0F172A',
        border: '1px solid #2563EB',
        borderRadius: '8px',
        padding: '12px 16px',
        marginBottom: '16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            backgroundColor: '#2563EB',
            color: '#FFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '15px'
          }}>
            D
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              FE Express Dispatcher: <span style={{ color: '#38BDF8' }}>Devin</span> 
              <span style={{ backgroundColor: '#1E293B', color: '#93C5FD', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', border: '1px solid #3B82F6' }}>
                {DEVIN_DISPATCH_PROFILE.mc} • {DEVIN_DISPATCH_PROFILE.usdot}
              </span>
              <span style={{ backgroundColor: '#064E3B', color: '#34D399', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', border: '1px solid #059669', fontWeight: 800 }}>
                🛡️ FMCSA VERIFIED: ACTIVE &amp; IN GOOD STANDING ({DEVIN_DISPATCH_PROFILE.powerUnits} Units • {DEVIN_DISPATCH_PROFILE.annualMiles} mi)
              </span>
              <span style={{ backgroundColor: '#1E293B', color: '#FCD34D', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', border: '1px solid #F59E0B', fontWeight: 800 }}>
                🚚 Unit: 26' Box Truck (Dock High • No Liftgate)
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '3px' }}>
              Terminal: <strong style={{ color: '#CBD5E1' }}>{DEVIN_DISPATCH_PROFILE.address}</strong> | Direct: <strong style={{ color: '#10B981' }}>{DEVIN_DISPATCH_PROFILE.phone}</strong> | Office: <strong style={{ color: '#94A3B8' }}>{DEVIN_DISPATCH_PROFILE.officePhone}</strong> | Unit: <strong style={{ color: '#FCD34D' }}>26' Box Truck (Dock High • No Liftgate)</strong>
            </div>
          </div>
        </div>

        <div className="fe-express-profile-actions" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <a
            href={`tel:${DEVIN_DISPATCH_PROFILE.phoneDigits}`}
            style={{
              padding: '6px 12px',
              backgroundColor: '#059669',
              color: '#FFF',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '11px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            📞 Call Devin
          </a>
          <a
            href={`sms:${DEVIN_DISPATCH_PROFILE.phoneDigits}`}
            style={{
              padding: '6px 12px',
              backgroundColor: '#0284C7',
              color: '#FFF',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '11px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            💬 SMS Devin
          </a>
          <a
            href={`mailto:${DEVIN_DISPATCH_PROFILE.email}`}
            style={{
              padding: '6px 12px',
              backgroundColor: '#4F46E5',
              color: '#FFF',
              borderRadius: '6px',
              textDecoration: 'none',
              fontSize: '11px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            ✉️ Email Devin
          </a>
        </div>
      </div>

      {/* Phase 3 Dispatch & Accounting Navigation Tabs */}
      <div className="fe-express-subtabs mobile-scroll-ribbon" style={{
        display: 'flex',
        gap: '8px',
        marginBottom: '16px',
        borderBottom: '1px solid #1E293B',
        paddingBottom: '8px',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={() => setActiveSubTab('board')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeSubTab === 'board' ? '#2563EB' : '#1E293B',
            color: activeSubTab === 'board' ? '#FFF' : '#94A3B8',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          📋 Live Load Board ({loads.length})
        </button>
        <button
          onClick={() => setActiveSubTab('active_dispatches')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeSubTab === 'active_dispatches' ? '#059669' : '#1E293B',
            color: activeSubTab === 'active_dispatches' ? '#FFF' : '#94A3B8',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          🚚 Devin's Active Hauls ({activeDispatches.filter(d => d.status !== 'DELIVERED').length})
        </button>
        <button
          onClick={() => setActiveSubTab('profit_ledger')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeSubTab === 'profit_ledger' ? '#7C3AED' : '#1E293B',
            color: activeSubTab === 'profit_ledger' ? '#FFF' : '#94A3B8',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          💰 Trip Profit &amp; BOL Ledger (${activeDispatches.reduce((acc, d) => acc + (d.net_profit || 0), 0).toLocaleString()})
        </button>
        <button onClick={() => { setReportsOpened(true); setActiveSubTab('driver_reports'); }} style={{padding:'8px 16px', background:activeSubTab === 'driver_reports' ? '#2563EB' : '#1E293B', color:'#FFF', border:0, borderRadius:6, cursor:'pointer'}}>Daily logs &amp; weekly reports</button>
        <button
          onClick={() => setActiveSubTab('drivers_ledger')}
          style={{
            padding: '8px 16px',
            backgroundColor: activeSubTab === 'drivers_ledger' ? '#D97706' : '#1E293B',
            color: activeSubTab === 'drivers_ledger' ? '#FFF' : '#94A3B8',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          👥 1099 Drivers &amp; Tax Spreadsheet ({driversList.length} Drivers | ${settlementsList.reduce((acc, s) => acc + (Number(s.net_1099_payout) || 0), 0).toLocaleString()} Paid)
        </button>
        <button
          onClick={() => {
            setActiveSubTab('owner_operator');
            if (triangulationChains.length === 0) {
              setLoadingChains(true);
              request(`${baseUrl}/api/v1/fe-express/triangulation-chains`)
                .then(r => r.json())
                .then(d => { if (d.success) setTriangulationChains(d.chains); setLoadingChains(false); })
                .catch(() => setLoadingChains(false));
            }
            if (!iftaSummary) {
              request(`${baseUrl}/api/v1/fe-express/ifta/summary`)
                .then(r => r.json())
                .then(d => { if (d.success) setIftaSummary(d.ifta_summary); })
                .catch(() => {});
            }
            if (!dvirDashboard) {
              request(`${baseUrl}/api/v1/fe-express/maintenance/dvir`)
                .then(r => r.json())
                .then(d => { if (d.success) setDvirDashboard(d.maintenance_dashboard); })
                .catch(() => {});
            }
          }}
          style={{
            padding: '8px 16px',
            backgroundColor: activeSubTab === 'owner_operator' ? '#EC4899' : '#1E293B',
            color: activeSubTab === 'owner_operator' ? '#FFF' : '#94A3B8',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          🚀 Owner-Operator Yield &amp; Uptime Cockpit
        </button>
        <button
          onClick={() => {
            setCapacityBroadcastModal({
              location: homeBase || 'Grand Rapids, MI',
              destination: 'Midwest Regional',
              available_time: 'Immediately'
            });
            setBroadcastStatus(null);
          }}
          style={{
            padding: '8px 16px',
            backgroundColor: '#0284C7',
            color: '#FFF',
            border: 'none',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title="Prepare a local capacity draft; load board posting is not connected"
        >
          Prepare capacity posting draft
        </button>
        <button
          onClick={async () => {
            setMeshModal({ carrier_b: 'Midwest Peer Freight', lane: ['Grand Rapids, MI', 'Chicago, IL'] });
            setMeshMatchResult(null);
            try {
              const r = await request(`${baseUrl}/api/v1/fe-express/mesh-haul/match`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  carrier_a_id: 'FE-EXPRESS-UNIT-01',
                  carrier_b_id: 'MIDWEST-PEER-FREIGHT',
                  lane_coordinates: ['Grand Rapids, MI', 'Chicago, IL'],
                  truck_length_ft: 26.0,
                  used_linear_ft: 16.0,
                  cargo_weight_lbs: 4500,
                  total_linehaul_usd: 950.0
                })
              });
              const d = await r.json();
              if (d.success) setMeshMatchResult(d.mesh_match);
            } catch (e) { console.error(e); }
          }}
          style={{
            padding: '8px 14px',
            backgroundColor: '#1E1B4B',
            color: '#A5B4FC',
            border: '1px solid #6366F1',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title="Decentralized Mesh-Haul: Peer-to-peer capacity exchange with cryptographic smart contracts"
        >
          ⛓️ Mesh-Haul P2P
        </button>
        <button
          onClick={async () => {
            setFatigueModal({ driver: 'Devin', unit: 'UNIT-26FT-01' });
            setFatigueResult(null);
            try {
              const r = await request(`${baseUrl}/api/v1/fe-express/fatigue-catalyst`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  driver_id: 'DRV-DEVIN',
                  unit_id: 'UNIT-26FT-01',
                  blink_duration_ms: 385.0,
                  micro_saccade_velocity_deg_s: 175.0,
                  head_tilt_angle_deg: 15.0,
                  hrv_drop_percentage: 26.5,
                  hos_remaining_minutes: 180
                })
              });
              const d = await r.json();
              if (d.success) setFatigueResult(d.fatigue_analysis);
            } catch (e) { console.error(e); }
          }}
          style={{
            padding: '8px 14px',
            backgroundColor: '#450A0A',
            color: '#FCA5A5',
            border: '1px solid #DC2626',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title="Biometric Fatigue Catalyst: Predictive computer-vision eye tracking & proactive appointment buffering"
        >
          👁️ Fatigue &amp; HOS Sentinel
        </button>
        <button
          onClick={async () => {
            setScope3Modal({ dispatch: 'DISP-2026-001', lane: 'Grand Rapids ➔ Chicago' });
            setScope3Result(null);
            try {
              const r = await request(`${baseUrl}/api/v1/fe-express/scope3-carbon`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  dispatch_id: 'DISP-2026-001',
                  origin: 'Grand Rapids, MI',
                  destination: 'Chicago, IL',
                  miles_traveled: 180.0,
                  cargo_weight_lbs: 4200,
                  steady_throttle_pct: 79.2
                })
              });
              const d = await r.json();
              if (d.success) setScope3Result(d.carbon_ledger);
            } catch (e) { console.error(e); }
          }}
          style={{
            padding: '8px 14px',
            backgroundColor: '#064E3B',
            color: '#6EE7B7',
            border: '1px solid #059669',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title="Scope 3 Emissions: Audit-proof carbon credit certificate generator for enterprise shippers"
        >
          🌱 Scope 3 Carbon Ledger
        </button>
        <button
          onClick={async () => {
            setBlackSwanModal({ corridor: 'Midwest / I-80 & I-94' });
            setBlackSwanResult(null);
            try {
              const r = await request(`${baseUrl}/api/v1/fe-express/black-swan-radar`);
              const d = await r.json();
              if (d.success) setBlackSwanResult(d.macro_radar);
            } catch (e) { console.error(e); }
          }}
          style={{
            padding: '8px 14px',
            backgroundColor: '#3B0764',
            color: '#D8B4FE',
            border: '1px solid #9333EA',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title="Black Swan Radar: Anonymized telematics velocity sinks & macro corridor disruption alerts"
        >
          🌪️ Black Swan Radar
        </button>
        <button
          onClick={async () => {
            setArHudModal({ unit: 'UNIT-26FT-01', driver: 'Devin' });
            setArHudData(null);
            try {
              const r = await request(`${baseUrl}/api/v1/fe-express/ar-hud?unit_id=UNIT-26FT-01&driver_id=DRV-DEVIN`);
              const d = await r.json();
              if (d.success) setArHudData(d.hud_telemetry);
            } catch (e) { console.error(e); }
          }}
          style={{
            padding: '8px 14px',
            backgroundColor: '#0F172A',
            color: '#38BDF8',
            border: '1px solid #0284C7',
            borderRadius: '6px',
            fontWeight: 800,
            fontSize: '12px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title="AR HUD Windshield Mode: Inverted high-contrast text projection for nighttime windshield reflection"
        >
          🕶️ AR HUD Windshield
        </button>
      </div>

      {/* TAB 1: LIVE LOAD BOARD & FILTER CONTROLS */}
      {['profit_ledger', 'driver_reports'].includes(activeSubTab) && <section aria-label="Employee work file" style={{ padding: 16, marginBottom: 14, background: '#142033', border: '1px solid #475569', borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Employee logs &amp; trip files</h2>
        <label>Employee / driver<select aria-label="Employee / driver" value={reportDriver} onChange={e => setReportDriver(e.target.value)} style={{ padding: 10, margin: 10, color: 'white', background: '#0f172a', maxWidth: '100%' }}><option value="OWNER-DEVIN">Devin (owner)</option>{driversList.map(d => <option key={d.driver_id} value={d.driver_id}>{d.full_name}</option>)}</select></label>
        <button type="button" onClick={() => setActiveSubTab('profit_ledger')} style={{ padding: 10, margin: 5 }}>Trip ledger</button>
        <button type="button" onClick={() => { setReportsOpened(true); setActiveSubTab('driver_reports'); }} style={{ padding: 10, margin: 5 }}>Employee weekly file</button>
        <button type="button" onClick={() => { setReportsOpened(true); setActiveSubTab('driver_reports'); setLogRequest(n => n + 1); }} style={{ padding: 10, margin: 5 }}>Add employee log</button>
        <button type="button" onClick={() => setActiveSubTab('drivers_ledger')} style={{ padding: 10, margin: 5 }}>Manage drivers</button>
        <p style={{ marginBottom: 0 }}>Logs and shipment files belong to the selected driver. The trip ledger shows all recorded trips. Link a trip explicitly using its Employee file button.</p>
      </section>}
      {(reportsOpened || activeSubTab === 'driver_reports') && <div hidden={activeSubTab !== 'driver_reports'}><FEExpressDriverReports baseUrl={baseUrl} request={request} activeDispatches={activeDispatches} driverId={reportDriver} onDriverChange={setReportDriver} logRequest={logRequest} selectedDispatch={tripForReport} /></div>}

      {activeSubTab === 'board' && (
        <>
          {/* Search & Filter Bar - Devin Lead Criteria Controls */}
          <div className="fe-express-filter-card" style={{
        backgroundColor: '#111827',
        border: '1px solid #1F2937',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '20px'
      }}>
        <div className="fe-express-filter-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '15px', fontWeight: 800, color: '#38BDF8' }}>🔍 Lead Search &amp; Filter Controls</span>
            <span style={{ fontSize: '12px', color: '#94A3B8' }}>
              ({filteredLoads.length} matching of {loads.length} total)
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {/* Fleet Vehicle Automation Switcher: Box Truck vs Cargo/Sprinter Van */}
            <div style={{ display: 'flex', backgroundColor: '#0F172A', borderRadius: '6px', padding: '2px', border: '1px solid #334155' }}>
              <button
                onClick={() => setVehicleFilter('ALL')}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: vehicleFilter === 'ALL' ? '#3B82F6' : 'transparent',
                  color: vehicleFilter === 'ALL' ? '#FFF' : '#94A3B8'
                }}
              >
                🌐 All Fleet
              </button>
              <button
                onClick={() => setVehicleFilter('BOX_TRUCK')}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: vehicleFilter === 'BOX_TRUCK' ? '#059669' : 'transparent',
                  color: vehicleFilter === 'BOX_TRUCK' ? '#FFF' : '#94A3B8'
                }}
              >
                🚚 Box Truck (24'/26')
              </button>
              <button
                onClick={() => setVehicleFilter('CARGO_VAN')}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: vehicleFilter === 'CARGO_VAN' ? '#7C3AED' : 'transparent',
                  color: vehicleFilter === 'CARGO_VAN' ? '#FFF' : '#94A3B8'
                }}
              >
                🚐 Cargo / Sprinter Van
              </button>
            </div>

            {/* View Mode Toggle: Cards vs Table */}
            <div style={{ display: 'flex', backgroundColor: '#1E293B', borderRadius: '6px', padding: '2px', border: '1px solid #334155' }}>
              <button
                onClick={() => setViewMode('cards')}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: viewMode === 'cards' ? '#2563EB' : 'transparent',
                  color: viewMode === 'cards' ? '#FFF' : '#94A3B8'
                }}
              >
                📱 Phone Cards
              </button>
              <button
                onClick={() => setViewMode('table')}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: viewMode === 'table' ? '#2563EB' : 'transparent',
                  color: viewMode === 'table' ? '#FFF' : '#94A3B8'
                }}
              >
                🖥️ Data Table
              </button>
            </div>

            <button
              onClick={() => setShowEvaluator(!showEvaluator)}
              style={{
                padding: '4px 10px',
                fontSize: '12px',
                fontWeight: 600,
                borderRadius: '6px',
                border: '1px solid #374151',
                backgroundColor: showEvaluator ? '#1E293B' : '#0F172A',
                color: showEvaluator ? '#38BDF8' : '#64748B',
                cursor: 'pointer'
              }}
            >
              {showEvaluator ? '⚡ Hide Evaluator' : '⚡ Show Evaluator'}
            </button>

            {(searchOrigin || searchDest || minRpm || minFlatPay || maxWeight || maxDeadhead || filterScore !== 'ALL' || vehicleFilter !== 'ALL') && (
              <button
                onClick={() => {
                  setSearchOrigin(''); setSearchMiles(''); setSearchEquipment(''); setSearchBroker('');
                  setSearchDest('');
                  setMinRpm('');
                  setMinFlatPay('');
                  setMaxWeight('');
                  setMaxDeadhead('');
                  setVehicleFilter('ALL');
                  setFilterScore('ALL');
                }}
                style={{
                  padding: '4px 10px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: '#991B1B',
                  color: '#FFF',
                  cursor: 'pointer'
                }}
              >
                ✕ Clear All
              </button>
            )}
          </div>
        </div>

        {/* Dynamic Input Grid */}
        <div className="fe-express-filter-grid" style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '12px'
        }}>
          <div>
            <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Origin / State</label>
            <input
              type="text"
              placeholder="e.g. MI, Chicago, OH"
              value={searchOrigin}
              onChange={e => setSearchOrigin(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 8px',
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '4px',
                color: '#FFF',
                fontSize: '12px'
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Destination / State</label>
            <input
              type="text"
              placeholder="e.g. TX, Dallas, Atlanta"
              value={searchDest}
              onChange={e => setSearchDest(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 8px',
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '4px',
                color: '#FFF',
                fontSize: '12px'
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Min Rate ($/mi)</label>
            <input
              type="number"
              step="0.10"
              placeholder="e.g. 2.00 or 2.50"
              value={minRpm}
              onChange={e => setMinRpm(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 8px',
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '4px',
                color: '#10B981',
                fontWeight: 600,
                fontSize: '12px'
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Min Flat Pay ($)</label>
            <input
              type="number"
              step="50"
              placeholder="e.g. 800"
              value={minFlatPay}
              onChange={e => setMinFlatPay(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 8px',
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '4px',
                color: '#10B981',
                fontWeight: 600,
                fontSize: '12px'
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Max Weight (lbs)</label>
            <input
              type="number"
              step="500"
              placeholder="e.g. 10000"
              value={maxWeight}
              onChange={e => setMaxWeight(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 8px',
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '4px',
                color: '#FFF',
                fontSize: '12px'
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#9CA3AF', display: 'block', marginBottom: '4px' }}>Max Deadhead (mi)</label>
            <input
              type="number"
              step="10"
              placeholder="e.g. 100"
              value={maxDeadhead}
              onChange={e => setMaxDeadhead(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 8px',
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '4px',
                color: '#38BDF8',
                fontWeight: 600,
                fontSize: '12px'
              }}
            />
          </div>
        </div>
      </div>

      {/* Quick Load Calculator & Feed Section */}
      <div className="fe-express-main-grid" style={{ display: 'grid', gridTemplateColumns: showEvaluator ? 'minmax(300px, 340px) 1fr' : '1fr', gap: '20px' }}>
        {/* Left: Quick Evaluator */}
        {showEvaluator && (
          <div className="fe-express-evaluator-card" style={{ backgroundColor: '#111827', border: '1px solid #1F2937', borderRadius: '8px', padding: '18px', height: 'fit-content' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#38BDF8', margin: '0 0 16px' }}>⚡ Instant Lane Evaluator</h2>
            <p style={{ color: '#94a3b8', fontSize: 12 }}>Every search field is optional. Blank means unknown. Partial entries find closest saved loads without adding a load or calculating an unsupported rate.</p>
            <form onSubmit={handleCalculate} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Origin</label>
                <input type="text" aria-label="Origin (optional)" placeholder="Unknown" value={calcOrigin} onChange={e => setCalcOrigin(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Destination</label>
                <input type="text" aria-label="Destination (optional)" placeholder="Unknown" value={calcDest} onChange={e => setCalcDest(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Loaded Miles</label>
                  <input type="number" aria-label="Loaded miles (optional)" placeholder="Unknown" value={calcMiles} onChange={e => setCalcMiles(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Deadhead Miles</label>
                  <input type="number" aria-label="Deadhead miles (optional)" placeholder="Unknown" value={calcDeadhead} onChange={e => setCalcDeadhead(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Flat Rate Pay ($)</label>
                  <input type="number" aria-label="Flat rate pay (optional)" placeholder="Unknown" value={calcPay} onChange={e => setCalcPay(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Weight (lbs)</label>
                  <input type="number" aria-label="Weight (optional)" placeholder="Unknown" value={calcWeight} onChange={e => setCalcWeight(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
                </div>
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Equipment String</label>
                <input type="text" aria-label="Equipment (optional)" placeholder="Unknown" value={calcEquip} onChange={e => setCalcEquip(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#9CA3AF' }}>Broker Name</label>
                <input type="text" aria-label="Broker (optional)" placeholder="Unknown" value={calcBroker} onChange={e => setCalcBroker(e.target.value)} style={{ width: '100%', padding: '8px', backgroundColor: '#1F2937', border: '1px solid #374151', color: '#FFF', borderRadius: '4px' }} />
              </div>
              <button type="submit" style={{ marginTop: '8px', padding: '10px', backgroundColor: '#2563EB', color: '#FFF', border: 'none', borderRadius: '4px', fontWeight: 700, cursor: 'pointer' }}>
                ⚡ Evaluate / find closest loads
              </button>
            </form>

            {evalResult && (
              <div style={{ marginTop: '16px', padding: '12px', backgroundColor: evalResult.score === 'Greenlight' ? '#064E3B' : evalResult.score === 'Caution' ? '#78350F' : '#7F1D1D', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.2)' }}>
                <div style={{ fontSize: '16px', fontWeight: 800 }}>Decision: {evalResult.score.toUpperCase()}</div>
                <div style={{ fontSize: '13px', marginTop: '4px' }}>True RPM (w/ Deadhead): <strong>${evalResult.true_rpm} / mi</strong></div>
                <div style={{ fontSize: '13px' }}>Loaded RPM: ${evalResult.rpm} / mi</div>
                <div style={{ fontSize: '12px', color: '#E2E8F0', marginTop: '4px' }}>
                  Box Truck Match: {evalResult.is_valid_box_truck ? '✅ Yes' : '❌ No'} | Under 10k lbs: {evalResult.under_weight_limit ? '✅ Yes' : '❌ No'} | Liftgate: <strong style={{ color: evalResult.requires_liftgate ? '#EF4444' : '#10B981' }}>{evalResult.requires_liftgate ? '❌ Required by Load (Devin: No Liftgate)' : '✅ Not Required (Dock High)'}</strong>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Right: Filtered Live Board Stream */}
        <div className="fe-express-leads-card" style={{ backgroundColor: '#111827', border: '1px solid #1F2937', borderRadius: '8px', padding: '18px', minWidth: 0 }}>
          <div className="fe-express-leads-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: '#F3F4F6', margin: 0 }}>
              📋 Qualified Box Truck Leads ({filteredLoads.length})
            </h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              {['ALL', 'Greenlight', 'Caution', 'Reject'].map(t => (
                <button
                  key={t}
                  onClick={() => setFilterScore(t)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '12px',
                    borderRadius: '4px',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: 600,
                    backgroundColor: filterScore === t ? '#38BDF8' : '#1F2937',
                    color: filterScore === t ? '#000' : '#94A3B8'
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* VIEW MODE 1: MOBILE CARDS VIEW (Clean Touch-Friendly Layout for Devin) */}
          {viewMode === 'cards' ? (
            <div className="fe-express-cards-grid" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))',
              gap: '14px',
              maxHeight: 'calc(100vh - 280px)',
              overflowY: 'auto',
              padding: '4px'
            }}>
              {filteredLoads.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#6B7280', gridColumn: '1 / -1' }}>
                  {loading ? 'Refreshing loads...' : 'No loads matching your search criteria.'}
                </div>
              ) : (
                filteredLoads.map(load => (
                  <div
                    key={load.load_id}
                    className="fe-express-lead-card"
                    style={{
                      backgroundColor: '#1E293B',
                      border: `1px solid ${load.score === 'Greenlight' ? '#10B981' : load.score === 'Caution' ? '#F59E0B' : '#374151'}`,
                      borderRadius: '8px',
                      padding: '14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 800,
                        backgroundColor: load.score === 'Greenlight' ? '#065F46' : load.score === 'Caution' ? '#92400E' : '#991B1B',
                        color: '#FFF'
                      }}>
                        {load.score.toUpperCase()}
                      </span>
                      <span style={{ fontSize: '11px', color: '#38BDF8', fontWeight: 600 }}>
                        {load.created_at ? `Received: ${load.created_at}` : 'Received time unknown'}
                      </span>
                    </div>

                    <div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#F8FAFC' }}>
                        {load.origin_city_state} ➡️ {load.dest_city_state}
                      </div>
                      <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                        Trip: {load.total_miles} loaded mi (+{load.deadhead_miles || 0} mi DH)
                      </div>
                    </div>

                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      backgroundColor: '#0F172A',
                      padding: '8px 10px',
                      borderRadius: '6px'
                    }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Flat Pay</div>
                        <div style={{ fontSize: '16px', fontWeight: 800, color: '#10B981' }}>
                          ${Number(load.flat_rate_pay).toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>True RPM</div>
                        <div style={{ fontSize: '16px', fontWeight: 800, color: '#38BDF8' }}>
                          ${load.true_rpm}/mi
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Weight</div>
                        <div style={{ fontSize: '14px', fontWeight: 700, color: '#CBD5E1', marginTop: '2px' }}>
                          {Number(load.weight_lbs).toLocaleString()} lbs
                        </div>
                      </div>
                    </div>

                    {/* 7-Day Spot Market Benchmark & Position */}
                    {(() => {
                      const bench = getLocalSpotBenchmark(load.origin_city_state, load.dest_city_state, load.true_rpm, load.total_miles);
                      return (
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          backgroundColor: '#0B132B',
                          border: `1px solid ${bench.badgeColor}40`,
                          padding: '6px 8px',
                          borderRadius: '6px',
                          fontSize: '11px'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{
                              backgroundColor: bench.badgeColor,
                              color: '#000',
                              fontWeight: 800,
                              fontSize: '10px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              textTransform: 'uppercase'
                            }}>
                              {bench.assessment}
                            </span>
                            <span style={{ color: '#94A3B8' }}>
                              Illustrative Target: <strong style={{ color: '#E2E8F0' }}>${bench.avg_rpm.toFixed(2)}/mi</strong>
                            </span>
                          </div>
                          <div style={{
                            fontWeight: 700,
                            color: Number(bench.diff) >= 0 ? '#10B981' : '#EF4444'
                          }}>
                            {Number(bench.diff) >= 0 ? `+${bench.diff}` : bench.diff} $/mi
                          </div>
                        </div>
                      );
                    })()}

                    <div style={{ fontSize: '11px', color: '#CBD5E1', lineHeight: '1.4', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px' }}>
                      <div><strong>Equipment:</strong> {load.equipment_type}</div>
                      {(() => {
                        const eqStr = ((load.equipment_type || '') + ' ' + (load.broker_email || '')).toLowerCase();
                        const reqLg = ['liftgate', 'lift gate', 'lift-gate', 'lg req'].some(k => eqStr.includes(k));
                        if (reqLg) {
                          return (
                            <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 6px', borderRadius: '4px', backgroundColor: '#7F1D1D', color: '#FCA5A5', border: '1px solid #DC2626' }}>
                              ⚠️ LIFTGATE REQ (DEVIN: NO LIFTGATE)
                            </span>
                          );
                        }
                        return null;
                      })()}
                      {(() => {
                        const match = load.vehicle_match || classifyEquipmentLocally(load.equipment_type, load.weight_lbs).vehicleType;
                        if (match === 'BOX_TRUCK') {
                          return (
                            <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 6px', borderRadius: '4px', backgroundColor: '#064E3B', color: '#6EE7B7', border: '1px solid #059669' }}>
                              🚚 24'/26' BOX TRUCK
                            </span>
                          );
                        } else if (match === 'CARGO_VAN') {
                          return (
                            <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 6px', borderRadius: '4px', backgroundColor: '#4C1D95', color: '#C4B5FD', border: '1px solid #7C3AED' }}>
                              🚐 CARGO / SPRINTER VAN
                            </span>
                          );
                        }
                        return null;
                      })()}
                    </div>

                    {/* Broker Credit Sentinel & Factoring Status */}
                    {(() => {
                      const credit = getLocalBrokerCredit(load.broker_name);
                      return (
                        <div style={{ fontSize: '11px', color: '#94A3B8', borderTop: '1px solid #334155', paddingTop: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 600, color: '#E2E8F0' }}>{load.broker_name}</span>
                            <span style={{
                              fontSize: '10px',
                              fontWeight: 700,
                              padding: '2px 6px',
                              borderRadius: '4px',
                              backgroundColor: credit.color + '20',
                              color: credit.color,
                              border: `1px solid ${credit.color}`
                            }}>
                              {credit.factoring === 'APPROVED' ? 'Example factor rating' : credit.factoring === 'CONDITIONAL' ? '🟡 Factor Cond.' : '⚪ Verify Factor'}
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '10px', marginTop: '4px', fontSize: '10px', color: '#94A3B8' }}>
                            <span>Credit: <strong style={{ color: credit.color }}>{credit.score} ({credit.rating})</strong></span>
                            <span>Avg Pay: <strong style={{ color: '#F1F5F9' }}>{credit.days_to_pay} Days</strong></span>
                            <span>RTS/Triumph: <strong style={{ color: '#10B981' }}>Tier 1</strong></span>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Quick Action Dial, Auto-Bid, Direct Email/SMS & Smart Backhaul Buttons */}
                    <div className="fe-express-card-actions" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '6px', marginTop: '4px' }}>
                      {load.broker_phone && (
                        <a
                          href={`tel:${load.broker_phone.replace(/[^0-9]/g, '')}`}
                          style={{
                            padding: '8px 4px',
                            backgroundColor: '#059669',
                            color: '#FFF',
                            textAlign: 'center',
                            borderRadius: '6px',
                            fontWeight: 700,
                            fontSize: '11px',
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '3px'
                          }}
                          title={`Call Broker: ${load.broker_phone}`}
                        >
                          📞 Call
                        </a>
                      )}
                      {load.broker_phone && (
                        <a
                          href={`sms:${load.broker_phone.replace(/[^0-9]/g, '')}?body=${encodeURIComponent(`FE Express (Devin): We have a 26' box truck empty near ${load.origin_city_state} ready for load ${load.load_id} (${load.origin_city_state} -> ${load.dest_city_state}). Call/text Devin at (616) 315-7483.`)}`}
                          style={{
                            padding: '8px 4px',
                            backgroundColor: '#0284C7',
                            color: '#FFF',
                            textAlign: 'center',
                            borderRadius: '6px',
                            fontWeight: 700,
                            fontSize: '11px',
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '3px'
                          }}
                          title={`Text Broker from Devin (${DEVIN_DISPATCH_PROFILE.phone})`}
                        >
                          💬 SMS
                        </a>
                      )}
                      <a
                        href={buildDevinMailto(load.broker_email, load)}
                        style={{
                          padding: '8px 4px',
                          backgroundColor: '#4F46E5',
                          color: '#FFF',
                          textAlign: 'center',
                          borderRadius: '6px',
                          fontWeight: 700,
                          fontSize: '11px',
                          textDecoration: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '3px'
                        }}
                        title={`Email Broker from Devin (${DEVIN_DISPATCH_PROFILE.email})`}
                      >
                        ✉️ Email
                      </a>
                      <button
                        onClick={() => handleOpenBidModal(load)}
                        style={{
                          padding: '8px 4px',
                          backgroundColor: '#2563EB',
                          color: '#FFF',
                          border: 'none',
                          borderRadius: '6px',
                          fontWeight: 700,
                          fontSize: '11px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '3px'
                        }}
                      >
                        💼 Bid
                      </button>
                      <button
                        onClick={() => handleOpenBackhaulModal(load)}
                        style={{
                          padding: '8px 4px',
                          backgroundColor: '#7C3AED',
                          color: '#FFF',
                          border: 'none',
                          borderRadius: '6px',
                          fontWeight: 700,
                          fontSize: '11px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '3px'
                        }}
                      >
                        🔄 Backhaul
                      </button>
                      <button
                        onClick={() => handleBookLoad(load)}
                        style={{
                          padding: '8px 4px',
                          backgroundColor: '#10B981',
                          color: '#000',
                          border: 'none',
                          borderRadius: '6px',
                          fontWeight: 800,
                          fontSize: '11px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '3px'
                        }}
                        title="Book Load and add to Devin's Active Haul Queue"
                      >
                        ⚡ Book Haul
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            /* VIEW MODE 2: DATA TABLE VIEW (Sticky Header & Auto-Wrap) */
            <div className="fe-express-table-wrapper" style={{
              maxHeight: 'calc(100vh - 280px)',
              minHeight: '400px',
              overflowY: 'auto',
              overflowX: 'auto',
              borderRadius: '6px',
              border: '1px solid #1F2937'
            }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead style={{ position: 'sticky', top: 0, zIndex: 10, backgroundColor: '#1F2937' }}>
                  <tr style={{ textAlign: 'left', color: '#9CA3AF' }}>
                    <th style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>Tier / Score</th>
                    <th style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>Posted Time</th>
                    <th style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>Load ID</th>
                    <th style={{ padding: '10px 8px', minWidth: '180px' }}>Origin ➡️ Destination</th>
                    <th style={{ padding: '10px 8px', minWidth: '180px' }}>Equipment &amp; Pickup Date</th>
                    <th style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>Weight (lbs)</th>
                    <th style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>Posted Pay ($)</th>
                    <th style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>Loaded Mi / RPM</th>
                    <th style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>True RPM (w/ DH)</th>
                    <th style={{ padding: '10px 8px', minWidth: '220px' }}>Broker &amp; Direct Phone</th>
                    <th style={{ padding: '10px 8px', textAlign: 'center', whiteSpace: 'nowrap' }}>Dispatch Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLoads.length === 0 ? (
                    <tr>
                      <td colSpan="11" style={{ textAlign: 'center', padding: '24px', color: '#6B7280' }}>
                        {loading ? 'Refreshing loads...' : 'No loads matching current filter.'}
                      </td>
                    </tr>
                  ) : (
                    filteredLoads.map(load => (
                      <tr key={load.load_id} style={{ borderBottom: '1px solid #1F2937' }}>
                        <td style={{ padding: '8px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 700,
                            backgroundColor: load.score === 'Greenlight' ? '#065F46' : load.score === 'Caution' ? '#92400E' : '#991B1B',
                            color: '#FFF'
                          }}>
                            {load.score}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#38BDF8', fontWeight: 600, fontSize: '12px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                          {load.created_at ? `Received: ${load.created_at}` : 'Received time unknown'}
                        </td>
                        <td style={{ padding: '8px', fontWeight: 600, verticalAlign: 'top', whiteSpace: 'nowrap' }}>{load.load_id}</td>
                        <td style={{ padding: '8px', verticalAlign: 'top', wordBreak: 'break-word', maxWidth: '200px' }}>
                          <strong>{load.origin_city_state}</strong> ➡️ <strong>{load.dest_city_state}</strong> ({load.total_miles} mi)
                        </td>
                        <td style={{ padding: '8px', color: '#CBD5E1', verticalAlign: 'top', wordBreak: 'break-word', maxWidth: '200px' }}>
                          <div>{load.equipment_type}</div>
                          {(() => {
                            const eqStr = ((load.equipment_type || '') + ' ' + (load.broker_email || '')).toLowerCase();
                            const reqLg = ['liftgate', 'lift gate', 'lift-gate', 'lg req'].some(k => eqStr.includes(k));
                            if (reqLg) {
                              return (
                                <span style={{ display: 'inline-block', marginTop: '4px', fontSize: '9px', fontWeight: 800, padding: '1px 5px', borderRadius: '3px', backgroundColor: '#7F1D1D', color: '#FCA5A5', border: '1px solid #DC2626' }}>
                                  ⚠️ LIFTGATE REQ
                                </span>
                              );
                            }
                            return null;
                          })()}
                          {(() => {
                            const match = load.vehicle_match || classifyEquipmentLocally(load.equipment_type, load.weight_lbs).vehicleType;
                            if (match === 'BOX_TRUCK') {
                              return (
                                <span style={{ display: 'inline-block', marginTop: '4px', fontSize: '9px', fontWeight: 800, padding: '1px 5px', borderRadius: '3px', backgroundColor: '#064E3B', color: '#6EE7B7', border: '1px solid #059669' }}>
                                  🚚 24'/26' BOX
                                </span>
                              );
                            } else if (match === 'CARGO_VAN') {
                              return (
                                <span style={{ display: 'inline-block', marginTop: '4px', fontSize: '9px', fontWeight: 800, padding: '1px 5px', borderRadius: '3px', backgroundColor: '#4C1D95', color: '#C4B5FD', border: '1px solid #7C3AED' }}>
                                  🚐 CARGO VAN
                                </span>
                              );
                            }
                            return null;
                          })()}
                        </td>
                        <td style={{ padding: '8px', color: '#9CA3AF', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                          {Number(load.weight_lbs).toLocaleString()} lbs
                        </td>
                        <td style={{ padding: '8px', color: '#10B981', fontWeight: 700, verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                          ${Number(load.flat_rate_pay).toLocaleString()}
                        </td>
                        <td style={{ padding: '8px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                          {load.total_miles} mi (${load.rpm}/mi)
                        </td>
                        <td style={{ padding: '8px', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                          <div style={{ fontWeight: 700, color: '#38BDF8' }}>
                            ${load.true_rpm}/mi (+{load.deadhead_miles || 0} DH)
                          </div>
                          {(() => {
                            const bench = getLocalSpotBenchmark(load.origin_city_state, load.dest_city_state, load.true_rpm, load.total_miles);
                            return (
                              <div style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <span style={{
                                  backgroundColor: bench.badgeColor,
                                  color: '#000',
                                  fontWeight: 800,
                                  fontSize: '9px',
                                  padding: '1px 5px',
                                  borderRadius: '3px',
                                  textTransform: 'uppercase'
                                }}>
                                  {bench.assessment}
                                </span>
                                <span style={{ fontSize: '10px', color: Number(bench.diff) >= 0 ? '#10B981' : '#EF4444', fontWeight: 600 }}>
                                  {Number(bench.diff) >= 0 ? `+${bench.diff}` : bench.diff} $/mi vs avg
                                </span>
                              </div>
                            );
                          })()}
                        </td>
                        <td style={{ padding: '8px', fontSize: '12px', verticalAlign: 'top', wordBreak: 'break-word', maxWidth: '240px' }}>
                          <div style={{ lineHeight: '1.4', fontWeight: 600, color: '#E2E8F0' }}>{load.broker_name}</div>
                          {(() => {
                            const credit = getLocalBrokerCredit(load.broker_name);
                            return (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px' }}>
                                <span style={{
                                  fontSize: '9px',
                                  fontWeight: 700,
                                  padding: '1px 5px',
                                  borderRadius: '3px',
                                  backgroundColor: credit.color + '20',
                                  color: credit.color,
                                  border: `1px solid ${credit.color}`
                                }}>
                                  {credit.factoring === 'APPROVED' ? 'Example factor rating' : credit.factoring === 'CONDITIONAL' ? '🟡 Factor Cond.' : '⚪ Verify'}
                                </span>
                                <span style={{ fontSize: '10px', color: '#94A3B8' }}>
                                  Score: <strong style={{ color: credit.color }}>{credit.score}</strong> ({credit.days_to_pay}d pay)
                                </span>
                              </div>
                            );
                          })()}
                          {load.broker_phone && (
                            <a
                              href={`tel:${load.broker_phone.replace(/[^0-9]/g, '')}`}
                              style={{ color: '#10B981', fontWeight: 600, marginTop: '4px', display: 'inline-block', textDecoration: 'none', fontSize: '11px' }}
                            >
                              📞 {load.broker_phone}
                            </a>
                          )}
                        </td>
                        <td style={{ padding: '8px', textAlign: 'center', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'flex', gap: '4px', justifyContent: 'center', alignItems: 'center' }}>
                            {load.broker_phone && (
                              <a
                                href={`tel:${load.broker_phone.replace(/[^0-9]/g, '')}`}
                                style={{
                                  padding: '4px 7px',
                                  backgroundColor: '#059669',
                                  color: '#FFF',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  textDecoration: 'none'
                                }}
                                title={`Call Broker: ${load.broker_phone}`}
                              >
                                📞 Call
                              </a>
                            )}
                            {load.broker_phone && (
                              <a
                                href={`sms:${load.broker_phone.replace(/[^0-9]/g, '')}?body=${encodeURIComponent(`FE Express (Devin): 26ft box truck empty near ${load.origin_city_state} ready for load ${load.load_id} (${load.origin_city_state}->${load.dest_city_state}). Call/text Devin at (616) 315-7483.`)}`}
                                style={{
                                  padding: '4px 7px',
                                  backgroundColor: '#0284C7',
                                  color: '#FFF',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  textDecoration: 'none'
                                }}
                                title={`Text Broker from Devin (${DEVIN_DISPATCH_PROFILE.phone})`}
                              >
                                💬 SMS
                              </a>
                            )}
                            <a
                              href={buildDevinMailto(load.broker_email, load)}
                              style={{
                                padding: '4px 7px',
                                backgroundColor: '#4F46E5',
                                color: '#FFF',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                textDecoration: 'none'
                              }}
                              title={`Email Broker from Devin (${DEVIN_DISPATCH_PROFILE.email})`}
                            >
                              ✉️ Email
                            </a>
                            <button
                              onClick={() => handleOpenBidModal(load)}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#2563EB',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                            >
                              💼 Bid
                            </button>
                            <button
                              onClick={() => {
                                setSelectedLoadForBlast(load);
                                setBlastBidAmount(load.flat_rate_pay || '');
                                setBlastStatus(null);
                              }}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#BE185D',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 800,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                              title="Prepare a bid draft for manual sending; providers not connected"
                            >
                              Prepare bid draft
                            </button>
                            <button
                              onClick={() => {
                                request(`${baseUrl}/api/v1/fe-express/horizon-map?destination=${encodeURIComponent(load.dest_city_state)}&hours_ahead=14`)
                                  .then(r => r.json())
                                  .then(d => {
                                    if (d.success) setHorizonMapModal(d.horizon_map);
                                  })
                                  .catch(err => alert(`Error: ${err.message}`));
                              }}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#0284C7',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                              title="Temporal Heat Map: Project destination capacity & outbound RPM for tomorrow"
                            >
                              🌅 Horizon
                            </button>
                            <button
                              onClick={() => {
                                request(`${baseUrl}/api/v1/fe-express/dock-intelligence?query=${encodeURIComponent(load.dest_city_state || load.dest_address || 'Joliet')}`)
                                  .then(r => r.json())
                                  .then(d => {
                                    if (d.success) setDockIntelModal(d.dock_facility);
                                  })
                                  .catch(err => alert(`Error: ${err.message}`));
                              }}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#475569',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                              title="Consignee & Shipper Dock Delay Intelligence, Lumper Fees & Parking"
                            >
                              🏢 Dock
                            </button>
                            <button
                              onClick={() => {
                                request(`${baseUrl}/api/v1/fe-express/cpm-calibration?diesel_price=${cpmParams.diesel_price}&truck_mpg=${cpmParams.truck_mpg}&driver_cpm=${cpmParams.driver_cpm}&target_margin=${cpmParams.target_margin}`)
                                  .then(r => r.json())
                                  .then(d => {
                                    if (d.success) setCpmCalibrationModal({ ...d.cpm_calibration, targetLoad: load });
                                  })
                                  .catch(err => alert(`Error: ${err.message}`));
                              }}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#059669',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                              title="Dynamic Live Cost-Per-Mile (CPM) Calibration Engine: True Break-Even Floor"
                            >
                              📊 CPM Floor
                            </button>
                            <button
                              onClick={() => {
                                request(`${baseUrl}/api/v1/fe-express/fuel-optimizer?origin=${encodeURIComponent(load.origin_city_state || 'Grand Rapids, MI')}&destination=${encodeURIComponent(load.dest_city_state || 'Chicago, IL')}&miles=${load.loaded_miles || 180}`)
                                  .then(r => r.json())
                                  .then(d => {
                                    if (d.success) setFuelOptimizerModal(d.fuel_optimization);
                                  })
                                  .catch(err => alert(`Error: ${err.message}`));
                              }}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#D97706',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                              title="Dynamic Fuel Route Optimizer: Exploit wholesale diesel price arbitrage to save $50-$150"
                            >
                              ⛽ Fuel Stop
                            </button>
                            <button
                              onClick={() => {
                                setAccessorialClaimModal(load);
                                setClaimResult(null);
                              }}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#DC2626',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                              title="Automated Accessorial Claims Builder: 1-Click TONU, Layover, or Detention Dispute Packet"
                            >
                              ⚖️ Claim
                            </button>
                            <button
                              onClick={() => handleOpenBackhaulModal(load)}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#7C3AED',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                            >
                              🔄 Backhaul
                            </button>
                            <button
                              onClick={() => handleBookLoad(load)}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#10B981',
                                color: '#000',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 800,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                              }}
                              title="Book load and lock in Devin's active haul queue"
                            >
                              ⚡ Book
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      </>
    )}

      {/* TAB 2: DEVIN'S ACTIVE HAULS & BOL PHOTO UPLOADER */}
      {activeSubTab === 'active_dispatches' && (
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#38BDF8', margin: 0 }}>
                🚚 Devin's Active Hauls &amp; Real-Time Trip Dispatches
              </h3>
              <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                Driver: <strong>Devin</strong> (616) 315-7483 | Equipment: <strong style={{ color: '#FCD34D' }}>26' Box Truck (Dock High - No Liftgate)</strong>
              </div>
            </div>
            <button
              onClick={() => setActiveSubTab('board')}
              style={{ padding: '6px 12px', backgroundColor: '#2563EB', color: '#FFF', border: 'none', borderRadius: '6px', fontWeight: 700, fontSize: '12px', cursor: 'pointer' }}
            >
              ➕ Book Another Load
            </button>
          </div>

          {/* NOTICE BANNER FOR DEVIN */}
          <div style={{
            backgroundColor: '#1E1B4B',
            border: '1px solid #6366F1',
            borderRadius: '6px',
            padding: '10px 14px',
            marginBottom: '14px',
            fontSize: '12px',
            color: '#C7D2FE',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '10px'
          }}>
            <div>
              <strong style={{ color: '#A5B4FC' }}>ℹ️ Dispatcher Notice for Devin:</strong> This list contains saved dispatch records. Saving a dispatch does not confirm a booking with the broker.
            </div>

          </div>

          <div className="fe-express-dispatches-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '14px' }}>
            {activeDispatches.map(dispatch => (
              <div
                key={dispatch.dispatch_id}
                style={{
                  backgroundColor: '#1E293B',
                  border: dispatch.dispatch_id === 'DISP-2026-001' ? '1px dashed #6366F1' : '1px solid #334155',
                  borderRadius: '8px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  position: 'relative'
                }}
              >
                {dispatch.dispatch_id === 'DISP-2026-001' && (
                  <div style={{
                    position: 'absolute',
                    top: '-9px',
                    right: '12px',
                    backgroundColor: '#4338CA',
                    color: '#EEF2FF',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: 800,
                    letterSpacing: '0.5px'
                  }}>
                    EXAMPLE PREVIEW
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 800,
                    backgroundColor: dispatch.status === 'DELIVERED' ? '#065F46' : dispatch.status === 'EN_ROUTE_DELIVERY' ? '#1E40AF' : '#854D0E',
                    color: '#FFF'
                  }}>
                    {dispatch.status}
                  </span>
                  <span style={{ fontSize: '12px', color: '#94A3B8' }}>{dispatch.dispatch_id}</span>
                </div>

                <div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: '#F8FAFC' }}>
                    {dispatch.origin} ➡️ {dispatch.destination}
                  </div>
                  <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                    Trip: {dispatch.loaded_miles} loaded mi (+{dispatch.deadhead_miles || 0} mi DH)
                  </div>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  backgroundColor: '#0F172A',
                  padding: '8px 10px',
                  borderRadius: '6px'
                }}>
                  <div>
                    <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Gross Pay</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#10B981' }}>
                      ${Number(dispatch.gross_pay).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Est Fuel/Tolls</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#EF4444' }}>
                      -${Number(dispatch.fuel_cost + dispatch.tolls_cost).toFixed(0)}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Net Profit</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#38BDF8' }}>
                      ${Number(dispatch.net_profit).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: '12px', color: '#CBD5E1', borderTop: '1px solid #334155', paddingTop: '8px' }}>
                  <div><strong>Broker:</strong> {dispatch.broker_name} {dispatch.broker_phone && `(${dispatch.broker_phone})`}</div>
                  {dispatch.bol_notes && (
                    <div style={{ marginTop: '4px', color: '#94A3B8', fontSize: '11px' }}>
                      📝 <em>"{dispatch.bol_notes}"</em>
                    </div>
                  )}
                  {dispatch.bol_photo_url && (
                    <div style={{ marginTop: '6px' }}>
                      <span style={{ fontSize: '11px', color: '#10B981', fontWeight: 700 }}>Legacy BOL reference — verify the stored file in shipment paperwork</span>
                    </div>
                  )}
                </div>

                {/* Dispatch & Delivery Mobile Buttons */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '6px', marginTop: '4px' }}>
                  {dispatch.broker_phone && (
                    <a
                      href={`tel:${dispatch.broker_phone.replace(/[^0-9]/g, '')}`}
                      style={{ padding: '6px', backgroundColor: '#059669', color: '#FFF', borderRadius: '4px', textAlign: 'center', textDecoration: 'none', fontSize: '11px', fontWeight: 700 }}
                    >
                      📞 Call Broker
                    </a>
                  )}
                  <button
                    onClick={() => {
                      openShipmentPaperwork(dispatch);
                    }}
                    style={{ padding: '6px', backgroundColor: '#7C3AED', color: '#FFF', border: 'none', borderRadius: '4px', fontSize: '11px', fontWeight: 700, cursor: 'pointer' }}
                  >
                    📄 Shipment paperwork
                  </button>
                  {dispatch.status !== 'DELIVERED' && (
                    <button
                      onClick={() => {
                        openShipmentPaperwork(dispatch);
                      }}
                      style={{ padding: '6px', backgroundColor: '#10B981', color: '#000', border: 'none', borderRadius: '4px', fontSize: '11px', fontWeight: 800, cursor: 'pointer' }}
                    >
                      Review delivery status
                    </button>
                  )}
                  <button
                    onClick={async () => {
                      const fee = 2.5;
                      const advance = 97.5;
                      const gross = Number(dispatch.gross_pay || 0);
                      const netP = (gross * (advance / 100) - (gross * (fee / 100))).toFixed(2);
                      const conf = window.confirm(
                        `Prepare a local factoring draft\n\n` +
                        `• Invoice: INV-${dispatch.dispatch_id}\n` +
                        `• Gross Freight: $${gross.toLocaleString()}\n` +
                        `• Factoring Partner: Triumph Business Capital\n` +
                        `• Advance Rate: 97.5% (Fee: 2.5%)\n` +
                        `• Estimated payout: $${netP} (illustrative terms)\n\n` +
                        `Save this estimate locally? Provider not connected. No documents will be sent or funding requested.`
                      );
                      if (!conf) return;

                      try {
                        const r = await request(`${baseUrl}/api/v1/fe-express/factoring/submit`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ dispatch_id: dispatch.dispatch_id, fee_pct: fee, advance_pct: advance })
                        });
                        const data = await r.json();
                        if (r.ok && data.success) {
                          alert(`Factoring draft prepared locally.\n\nDraft ID: ${data.factoring_package.submission_id}\nEstimated payout: $${netP}\nProvider not connected. Documents not verified or sent; approval and deposit are not confirmed.`);
                          await refreshDispatchesAfterUpdate();
                        } else {
                          alert(`Factoring Error: ${data.error || 'Gateway timed out'}`);
                        }
                      } catch (err) {
                        alert(`Network Error: ${err.message}`);
                      }
                    }}
                    style={{
                      padding: '6px 10px',
                      backgroundColor: '#EAB308',
                      color: '#000',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 900,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                    title="Prepare a local factoring estimate for review; provider not connected"
                  >
                    Prepare factoring draft
                  </button>
                  <button
                    onClick={async () => {
                      const lumperAmt = prompt("Enter Warehouse Lumper Unloading Fee ($):", "175.00");
                      if (!lumperAmt) return;
                      try {
                        const r = await request(`${baseUrl}/api/v1/fe-express/lumper-escrow`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            dispatch_id: dispatch.dispatch_id,
                            facility_name: dispatch.destination || 'Receiving Facility',
                            broker_name: dispatch.broker_name || 'Broker',
                            broker_night_phone: dispatch.broker_phone || '(616) 315-7483',
                            lumper_amount: parseFloat(lumperAmt),
                            payment_method: 'EFS_CODE'
                          })
                        });
                        const d = await r.json();
                        if (d.success) {
                          alert(`Lumper request prepared locally.\n\nDraft ID: ${d.lumper_escrow.escrow_id}\nAmount: $${d.lumper_escrow.lumper_amount.toFixed(2)}\n\nSMS provider not connected. Contact the broker separately; no message sent or payment code confirmed.`);
                        }
                      } catch (err) {
                        alert(`Error: ${err.message}`);
                      }
                    }}
                    style={{
                      padding: '6px 10px',
                      backgroundColor: '#6366F1',
                      color: '#FFF',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 800,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                    title="Prepare a local lumper request; contact the broker separately"
                  >
                    Prepare lumper request
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: COMPLETE PROFIT & TRIP EXPENSE LEDGER */}
      {activeSubTab === 'profit_ledger' && (
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#10B981', margin: 0 }}>
                💰 Devin's End-to-End Box Truck Profit &amp; Expense Ledger
              </h3>
              <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                FE Express LLC | Zero-Mock Real Freight Accounting
              </div>
            </div>

            {/* Total Aggregate Metrics */}
            <div style={{ display: 'flex', gap: '12px' }}>
              <div style={{ backgroundColor: '#064E3B', padding: '8px 12px', borderRadius: '6px', border: '1px solid #059669' }}>
                <div style={{ fontSize: '10px', color: '#A7F3D0', textTransform: 'uppercase' }}>Total Net Profit</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#FFF' }}>
                  ${activeDispatches.reduce((acc, d) => acc + (d.net_profit || 0), 0).toLocaleString()}
                </div>
              </div>
              <div style={{ backgroundColor: '#1E293B', padding: '8px 12px', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Gross Revenue</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#38BDF8' }}>
                  ${activeDispatches.reduce((acc, d) => acc + (d.gross_pay || 0), 0).toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          <div style={{ overflowX: 'auto', borderRadius: '6px', border: '1px solid #1F2937', marginTop: '12px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead style={{ backgroundColor: '#1F2937', color: '#9CA3AF' }}>
                <tr style={{ textAlign: 'left' }}>
                  <th style={{ padding: '10px 8px' }}>Dispatch ID</th>
                  <th style={{ padding: '10px 8px' }}>Lane</th>
                  <th style={{ padding: '10px 8px' }}>Miles</th>
                  <th style={{ padding: '10px 8px' }}>Gross Pay</th>
                  <th style={{ padding: '10px 8px' }}>Fuel Expense</th>
                  <th style={{ padding: '10px 8px' }}>Tolls / Scales</th>
                  <th style={{ padding: '10px 8px' }}>Net Take-Home</th>
                  <th style={{ padding: '10px 8px' }}>Status</th>
                  <th style={{ padding: '10px 8px' }}>Employee file</th><th style={{ padding: '10px 8px' }}>BOL Proof</th>
                </tr>
              </thead>
              <tbody>
                {activeDispatches.map(dispatch => (
                  <tr key={dispatch.dispatch_id} style={{ borderBottom: '1px solid #1F2937' }}>
                    <td style={{ padding: '10px 8px', fontWeight: 600, color: '#38BDF8' }}>{dispatch.dispatch_id}</td>
                    <td style={{ padding: '10px 8px' }}><strong>{dispatch.origin}</strong> ➡️ <strong>{dispatch.destination}</strong></td>
                    <td style={{ padding: '10px 8px' }}>{dispatch.loaded_miles} mi</td>
                    <td style={{ padding: '10px 8px', color: '#10B981', fontWeight: 700 }}>${Number(dispatch.gross_pay).toLocaleString()}</td>
                    <td style={{ padding: '10px 8px', color: '#EF4444' }}>-${Number(dispatch.fuel_cost).toFixed(2)}</td>
                    <td style={{ padding: '10px 8px', color: '#EF4444' }}>-${Number(dispatch.tolls_cost).toFixed(2)}</td>
                    <td style={{ padding: '10px 8px', color: '#34D399', fontWeight: 800, fontSize: '14px' }}>
                      ${Number(dispatch.net_profit).toLocaleString()}
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 800,
                        backgroundColor: dispatch.status === 'DELIVERED' ? '#065F46' : '#1E40AF',
                        color: '#FFF'
                      }}>
                        {dispatch.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px 8px' }}><button type="button" aria-label={`Employee file ${dispatch.dispatch_id}`} onClick={() => { setTripForReport(dispatch.dispatch_id); setReportsOpened(true); setActiveSubTab('driver_reports'); }} style={{ padding: 9 }}>Employee file</button></td>
                    <td style={{ padding: '10px 8px' }}>
                      {dispatch.bol_photo_url && <div style={{ fontSize: 11 }}>Legacy reference; file not verified</div>}
                      {(
                        <button
                          onClick={() => {
                            openShipmentPaperwork(dispatch);
                          }}
                          style={{ padding: '3px 8px', backgroundColor: '#7C3AED', color: '#FFF', border: 'none', borderRadius: '4px', fontSize: '10px', cursor: 'pointer', fontWeight: 700 }}
                        >
                          Shipment paperwork
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: 1099 SUBCONTRACT DRIVERS & ANNUAL TAX SPREADSHEET */}
      {activeSubTab === 'drivers_ledger' && (
        <div style={{ backgroundColor: '#111827', border: '1px solid #1F2937', borderRadius: '8px', padding: '16px' }}>
          {/* Header & Quick Actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#F59E0B', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                👥 Subcontractor 1099 Drivers &amp; Annual Tax Spreadsheet
              </h3>
              <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                Owner-Operator Accounting &bull; 1099-NEC Driver Compensation, Mileage &amp; Deductions &bull; FE Express LLC
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setShowAddDriverModal(true)}
                style={{
                  padding: '8px 14px',
                  backgroundColor: '#059669',
                  color: '#FFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 700,
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                ➕ Add Subcontract Driver
              </button>
              {driversList.length > 0 && (
                <button
                  onClick={() => {
                    setSelectedDriverForSettlement(driversList[0]);
                    setShowAddSettlementModal(true);
                  }}
                  style={{
                    padding: '8px 14px',
                    backgroundColor: '#D97706',
                    color: '#FFF',
                    border: 'none',
                    borderRadius: '6px',
                    fontWeight: 700,
                    fontSize: '12px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  💵 Record Trip Payout
                </button>
              )}
            </div>
          </div>

          {/* Owner-Operator Tax Compliance Notice */}
          <div style={{
            backgroundColor: '#1E1B4B',
            border: '1px solid #6366F1',
            borderRadius: '6px',
            padding: '12px 14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px'
          }}>
            <span style={{ fontSize: '20px' }}>⚖️</span>
            <div style={{ fontSize: '12px', color: '#C7D2FE', lineHeight: '1.5' }}>
              <strong style={{ color: '#FFF' }}>1099-NEC Subcontractor Tax Rule:</strong> Because Devin operates as an owner-operator subcontracting drivers, drivers are <strong>self-employed independent contractors</strong> responsible for filing their own quarterly and annual federal, state, and self-employment taxes (Schedule C). Devin keeps record of gross trip earnings, fuel deductions, and cash advances to issue Form <strong>1099-NEC</strong> at year-end.
            </div>
          </div>

          {/* Metric Summary Cards */}
          <div className="fe-express-drivers-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '20px' }}>
            <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', border: '1px solid #334155' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8', textTransform: 'uppercase' }}>Active 1099 Drivers</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
                {driversList.length}
              </div>
            </div>
            <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', border: '1px solid #334155' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8', textTransform: 'uppercase' }}>Total 1099 Comp Paid</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#10B981', marginTop: '2px' }}>
                ${settlementsList.reduce((acc, s) => acc + (Number(s.net_1099_payout) || 0), 0).toLocaleString()}
              </div>
            </div>
            <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', border: '1px solid #334155' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8', textTransform: 'uppercase' }}>Subcontract Miles Logged</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#FBBF24', marginTop: '2px' }}>
                {settlementsList.reduce((acc, s) => acc + (Number(s.total_miles) || 0), 0).toLocaleString()} mi
              </div>
            </div>
            <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', border: '1px solid #334155' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8', textTransform: 'uppercase' }}>Fuel / Advance Deductions</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#EF4444', marginTop: '2px' }}>
                ${settlementsList.reduce((acc, s) => acc + (Number(s.fuel_deduction) || 0) + (Number(s.cash_advance) || 0), 0).toLocaleString()}
              </div>
            </div>
          </div>

          {/* SECTION 1: DRIVERS DIRECTORY SPREADSHEET */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: '#38BDF8' }}>
                🪪 Subcontract Driver Roster &amp; Compliance Roster
              </h4>
              <span style={{ fontSize: '11px', color: '#64748B' }}>Drivers maintain active CDL/Med Card on file</span>
            </div>

            {driversList.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', backgroundColor: '#1E293B', borderRadius: '6px', border: '1px dashed #334155' }}>
                <div style={{ fontSize: '24px', marginBottom: '8px' }}>👤</div>
                <div style={{ color: '#94A3B8', fontSize: '13px', fontWeight: 600 }}>No subcontract drivers logged yet.</div>
                <div style={{ color: '#64748B', fontSize: '12px', marginTop: '4px' }}>Add drivers to track their mileage, agreed pay rates, medical cards, and annual 1099s.</div>
                <button
                  onClick={() => setShowAddDriverModal(true)}
                  style={{ marginTop: '12px', padding: '6px 14px', backgroundColor: '#059669', color: '#FFF', border: 'none', borderRadius: '4px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
                >
                  ➕ Add First Driver
                </button>
              </div>
            ) : (
              <div style={{ overflowX: 'auto', borderRadius: '6px', border: '1px solid #1F2937' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead style={{ backgroundColor: '#1F2937', color: '#9CA3AF' }}>
                    <tr style={{ textAlign: 'left' }}>
                      <th style={{ padding: '8px' }}>Driver Name</th>
                      <th style={{ padding: '8px' }}>Contact</th>
                      <th style={{ padding: '8px' }}>DL# / State</th>
                      <th style={{ padding: '8px' }}>SSN/Tax ID</th>
                      <th style={{ padding: '8px' }}>Agreed Pay Rate</th>
                      <th style={{ padding: '8px' }}>Med Card Exp</th>
                      <th style={{ padding: '8px' }}>W-9 / MVR</th>
                      <th style={{ padding: '8px' }}>YTD 1099 Paid</th>
                      <th style={{ padding: '8px', textAlign: 'center' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {driversList.map(driver => {
                      const driverTotalPaid = settlementsList
                        .filter(s => s.driver_id === driver.driver_id)
                        .reduce((acc, s) => acc + (Number(s.net_1099_payout) || 0), 0);

                      return (
                        <tr key={driver.driver_id} style={{ borderBottom: '1px solid #1F2937' }}>
                          <td style={{ padding: '8px', fontWeight: 700, color: '#F8FAFC' }}>
                            {driver.full_name}
                            <div style={{ fontSize: '10px', color: '#64748B' }}>ID: {driver.driver_id}</div>
                          </td>
                          <td style={{ padding: '8px' }}>
                            <div>📞 {driver.phone || 'N/A'}</div>
                            <div style={{ color: '#94A3B8', fontSize: '11px' }}>✉️ {driver.email || 'N/A'}</div>
                          </td>
                          <td style={{ padding: '8px' }}>
                            {driver.driver_license_num || 'N/A'} ({driver.driver_license_state || 'MI'})
                          </td>
                          <td style={{ padding: '8px', fontFamily: 'monospace', color: '#CBD5E1' }}>
                            ***-**-{driver.tax_id_or_ssn_last4 || 'XXXX'}
                          </td>
                          <td style={{ padding: '8px', fontWeight: 600, color: '#38BDF8' }}>
                            {driver.pay_model === 'PERCENT_GROSS' ? `${driver.pay_rate}% of Gross` : driver.pay_model === 'PER_MILE' ? `$${driver.pay_rate}/mi` : `$${driver.pay_rate}/day`}
                          </td>
                          <td style={{ padding: '8px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 700,
                              backgroundColor: '#064E3B',
                              color: '#6EE7B7'
                            }}>
                              {driver.medical_card_exp || 'Active'}
                            </span>
                          </td>
                          <td style={{ padding: '8px' }}>
                            <span style={{ color: driver.w9_on_file ? '#10B981' : '#EF4444', fontWeight: 700 }}>
                              {driver.w9_on_file ? '✅ W-9' : '❌ No W-9'}
                            </span>
                            <span style={{ marginLeft: '6px', color: '#94A3B8', fontSize: '10px' }}>({driver.mvr_check_status || 'MVR Clear'})</span>
                          </td>
                          <td style={{ padding: '8px', fontWeight: 800, color: '#10B981', fontSize: '13px' }}>
                            ${driverTotalPaid.toLocaleString()}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center' }}>
                            <button
                              onClick={() => {
                                setSelectedDriverForSettlement(driver);
                                setShowAddSettlementModal(true);
                              }}
                              style={{
                                padding: '4px 8px',
                                backgroundColor: '#2563EB',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              💵 Pay Trip
                            </button>
                            <button type="button" onClick={() => { setReportDriver(driver.driver_id); setReportsOpened(true); setActiveSubTab('driver_reports'); }} style={{ padding: 8, margin: 5 }}>Employee logs</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* SECTION 2: TRIP SETTLEMENTS & PAYOUT SPREADSHEET */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: '#10B981' }}>
                🧾 Subcontract Driver Trip Settlement &amp; Deduction Ledger
              </h4>
              <span style={{ fontSize: '11px', color: '#64748B' }}>Audit trail for annual Form 1099-NEC &amp; tax prep</span>
            </div>

            {settlementsList.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#1E293B', borderRadius: '6px', border: '1px dashed #334155' }}>
                <div style={{ color: '#94A3B8', fontSize: '13px' }}>No settlement records logged yet.</div>
                <div style={{ color: '#64748B', fontSize: '11px', marginTop: '2px' }}>Click "Record Trip Payout" above to calculate and issue compensation for a subcontract driver run.</div>
              </div>
            ) : (
              <div style={{ overflowX: 'auto', borderRadius: '6px', border: '1px solid #1F2937' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead style={{ backgroundColor: '#1F2937', color: '#9CA3AF' }}>
                    <tr style={{ textAlign: 'left' }}>
                      <th style={{ padding: '8px' }}>Trip Date</th>
                      <th style={{ padding: '8px' }}>Driver</th>
                      <th style={{ padding: '8px' }}>Lane / Dispatch</th>
                      <th style={{ padding: '8px' }}>Miles</th>
                      <th style={{ padding: '8px' }}>Gross Load</th>
                      <th style={{ padding: '8px' }}>Contractor Pay</th>
                      <th style={{ padding: '8px' }}>Fuel Deduct</th>
                      <th style={{ padding: '8px' }}>Advance</th>
                      <th style={{ padding: '8px' }}>Net 1099 Paid</th>
                      <th style={{ padding: '8px' }}>Method</th>
                      <th style={{ padding: '8px' }}>Status</th>
                      <th style={{ padding: '8px' }}>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {settlementsList.map(s => (
                      <tr key={s.settlement_id} style={{ borderBottom: '1px solid #1F2937' }}>
                        <td style={{ padding: '8px', color: '#94A3B8' }}>{s.trip_date}</td>
                        <td style={{ padding: '8px', fontWeight: 700, color: '#F8FAFC' }}>
                          {s.driver_name || driversList.find(d => d.driver_id === s.driver_id)?.full_name || s.driver_id}
                        </td>
                        <td style={{ padding: '8px', color: '#CBD5E1' }}>{s.origin_dest}</td>
                        <td style={{ padding: '8px' }}>{s.total_miles} mi</td>
                        <td style={{ padding: '8px', color: '#38BDF8', fontWeight: 600 }}>${Number(s.gross_load_pay).toLocaleString()}</td>
                        <td style={{ padding: '8px', color: '#FBBF24', fontWeight: 600 }}>${Number(s.contractor_pay).toLocaleString()}</td>
                        <td style={{ padding: '8px', color: '#EF4444' }}>-${Number(s.fuel_deduction).toFixed(2)}</td>
                        <td style={{ padding: '8px', color: '#EF4444' }}>-${Number(s.cash_advance).toFixed(2)}</td>
                        <td style={{ padding: '8px', color: '#34D399', fontWeight: 800, fontSize: '13px' }}>
                          ${Number(s.net_1099_payout).toLocaleString()}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ padding: '2px 6px', borderRadius: '4px', backgroundColor: '#1E293B', fontSize: '10px', color: '#94A3B8' }}>
                            {s.payment_method}
                          </span>
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ padding: '2px 6px', borderRadius: '4px', backgroundColor: '#064E3B', color: '#6EE7B7', fontSize: '10px', fontWeight: 700 }}>
                            {s.payment_status}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#64748B', fontSize: '11px', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.notes || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: OWNER-OPERATOR YIELD & UPTIME COCKPIT */}
      {activeSubTab === 'owner_operator' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header Banner */}
          <div style={{
            background: 'linear-gradient(135deg, #1E1B4B 0%, #311042 100%)',
            border: '1px solid #6366F1',
            borderRadius: '10px',
            padding: '18px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#A5B4FC', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🚀 Owner-Operator Yield Management &amp; Uptime Cockpit
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#CBD5E1' }}>
                Engineered for owner-operators to eliminate empty deadhead, accelerate cash velocity via instant factoring, and protect commercial vehicle assets.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ backgroundColor: '#10B981', color: '#000', padding: '4px 10px', borderRadius: '4px', fontWeight: 800, fontSize: '12px' }}>
                UNIT-26FT-01 ACTIVE
              </span>
              <span style={{ backgroundColor: '#0284C7', color: '#FFF', padding: '4px 10px', borderRadius: '4px', fontWeight: 700, fontSize: '12px' }}>
                Height Clearance: 12'6"
              </span>
            </div>
          </div>

          {/* GRID ROW 1: TRIANGULATION LOAD PLANNER */}
          <div style={{ backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '8px', padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 800, color: '#EC4899', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🔄 Multi-Leg "Triangulation" Chain Builder (True RPM Maximizer)
                </h4>
                <p style={{ margin: '2px 0 0', fontSize: '12px', color: '#94A3B8' }}>
                  Chains multiple short-haul loads together into continuous loops (Home ➡️ A ➡️ B ➡️ Home) to eliminate empty deadhead.
                </p>
              </div>
              <button
                onClick={() => {
                  setLoadingChains(true);
                  request(`${baseUrl}/api/v1/fe-express/triangulation-chains`)
                    .then(r => r.json())
                    .then(d => { if (d.success) setTriangulationChains(d.chains); setLoadingChains(false); })
                    .catch(() => setLoadingChains(false));
                }}
                style={{ padding: '6px 14px', backgroundColor: '#BE185D', color: '#FFF', border: 'none', borderRadius: '4px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
              >
                {loadingChains ? '⏳ Recalculating Loops...' : '🔄 Refresh Chains'}
              </button>
            </div>

            {triangulationChains.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#1E293B', borderRadius: '6px', color: '#94A3B8', fontSize: '13px' }}>
                {loadingChains ? 'Scanning live freight boards for multi-leg triangulation opportunities...' : 'No multi-leg loops found. Click Refresh to recalculate against active load database.'}
              </div>
            ) : (
              <div className="fe-express-triangulation-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '14px' }}>
                {triangulationChains.map((chain, i) => (
                  <div key={chain.chain_id || i} style={{
                    backgroundColor: '#1E293B',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <span style={{ backgroundColor: '#059669', color: '#FFF', fontSize: '11px', fontWeight: 800, padding: '2px 8px', borderRadius: '4px' }}>
                          LOOP #{i + 1}
                        </span>
                        <span style={{ fontSize: '16px', fontWeight: 900, color: '#10B981' }}>
                          ${chain.effective_true_rpm} / True RPM
                        </span>
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#F8FAFC', marginBottom: '8px' }}>
                        {chain.name}
                      </div>

                      {/* Legs Steps */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                        {chain.legs.map((leg, idx) => (
                          <div key={idx} style={{
                            fontSize: '11px',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            backgroundColor: leg.type === 'LOAD' ? '#064E3B' : '#334155',
                            borderLeft: leg.type === 'LOAD' ? '3px solid #10B981' : '3px solid #F59E0B',
                            display: 'flex',
                            justifyContent: 'space-between'
                          }}>
                            <span>
                              <strong>Step {leg.step}:</strong> {leg.type === 'LOAD' ? `🚚 ${leg.origin} ➡️ ${leg.dest}` : `🔄 Deadhead: ${leg.origin} ➡️ ${leg.dest}`}
                            </span>
                            <span style={{ fontWeight: 700, color: leg.type === 'LOAD' ? '#34D399' : '#CBD5E1' }}>
                              {leg.type === 'LOAD' ? `$${leg.pay} (${leg.miles} mi)` : `${leg.miles} mi`}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{ borderTop: '1px solid #334155', paddingTop: '10px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', textAlign: 'center', fontSize: '11px', marginBottom: '10px' }}>
                        <div style={{ backgroundColor: '#0F172A', padding: '6px', borderRadius: '4px' }}>
                          <div style={{ color: '#94A3B8' }}>Gross Pay</div>
                          <div style={{ fontWeight: 800, color: '#38BDF8' }}>${chain.total_gross_pay.toLocaleString()}</div>
                        </div>
                        <div style={{ backgroundColor: '#0F172A', padding: '6px', borderRadius: '4px' }}>
                          <div style={{ color: '#94A3B8' }}>Fuel Est.</div>
                          <div style={{ fontWeight: 800, color: '#EF4444' }}>-${chain.estimated_fuel_cost}</div>
                        </div>
                        <div style={{ backgroundColor: '#0F172A', padding: '6px', borderRadius: '4px' }}>
                          <div style={{ color: '#94A3B8' }}>Est. EBITDA</div>
                          <div style={{ fontWeight: 800, color: '#10B981' }}>${chain.projected_net_ebitda.toLocaleString()}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* GRID ROW 2: FACTORING & IFTA SPLIT */}
          <div className="fe-express-split-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '16px' }}>
            {/* Factoring Card */}
            <div style={{ backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '8px', padding: '16px' }}>
              <h4 style={{ margin: '0 0 4px', fontSize: '15px', fontWeight: 800, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                Factoring draft preparation
              </h4>
              <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#94A3B8' }}>
                Save an estimated factoring draft for manual review. Provider not connected; shipment documents, approval and funding require separate verification.
              </p>

              {activeDispatches.length === 0 ? (
                <div style={{ padding: '20px', textAlign: 'center', backgroundColor: '#1E293B', borderRadius: '6px', color: '#94A3B8', fontSize: '12px' }}>
                  No active dispatches available for factoring submission.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {activeDispatches.map(d => (
                    <div key={d.dispatch_id} style={{
                      backgroundColor: '#1E293B',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      padding: '12px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div>
                        <div style={{ fontWeight: 800, color: '#F8FAFC', fontSize: '13px' }}>
                          {d.dispatch_id} — {d.origin} ➡️ {d.destination}
                        </div>
                        <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '2px' }}>
                          Gross: <strong style={{ color: '#38BDF8' }}>${d.gross_pay}</strong> | Broker: {d.broker_name}
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          request(`${baseUrl}/api/v1/fe-express/factoring/submit`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ dispatch_id: d.dispatch_id, fee_pct: 2.5, advance_pct: 97.5 })
                          })
                            .then(r => r.json())
                            .then(res => {
                              if (res.success) {
                                alert(`Factoring draft ${res.factoring_package.submission_id} prepared locally.\nEstimated payout: $${res.factoring_package.expected_payout}. Provider not connected; documents not sent, approval and deposit not confirmed.`);
                              } else {
                                alert(`Submission error: ${res.error}`);
                              }
                            })
                            .catch(err => alert(`API Error: ${err.message}`));
                        }}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#0284C7',
                          color: '#FFF',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        Prepare factoring draft
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* IFTA Card */}
            <div style={{ backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '8px', padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 800, color: '#10B981', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  📊 Automated IFTA State Mileage &amp; Fuel Tax Engine
                </h4>
                <span style={{ fontSize: '11px', backgroundColor: '#064E3B', color: '#6EE7B7', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                  2026-Q4 FILING
                </span>
              </div>
              <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#94A3B8' }}>
                Correlates GPS state-line crossings with Mudflap/WEX fuel card purchases to compute quarterly IFTA tax return.
              </p>

              {iftaSummary && (
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px', textAlign: 'center' }}>
                    <div style={{ backgroundColor: '#1E293B', padding: '8px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '11px', color: '#94A3B8' }}>Total Miles</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: '#F8FAFC' }}>{iftaSummary.total_miles} mi</div>
                    </div>
                    <div style={{ backgroundColor: '#1E293B', padding: '8px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '11px', color: '#94A3B8' }}>Gallons Purchased</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: '#F8FAFC' }}>{iftaSummary.total_gallons_purchased} gal</div>
                    </div>
                    <div style={{ backgroundColor: '#1E293B', padding: '8px', borderRadius: '4px' }}>
                      <div style={{ fontSize: '11px', color: '#94A3B8' }}>Net Tax Balance</div>
                      <div style={{ fontSize: '14px', fontWeight: 800, color: iftaSummary.total_net_tax_due <= 0 ? '#10B981' : '#EF4444' }}>
                        {iftaSummary.total_net_tax_due <= 0 ? `Refund: $${Math.abs(iftaSummary.total_net_tax_due)}` : `Due: $${iftaSummary.total_net_tax_due}`}
                      </div>
                    </div>
                  </div>

                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                      <thead style={{ backgroundColor: '#1E293B', color: '#94A3B8' }}>
                        <tr style={{ textAlign: 'left' }}>
                          <th style={{ padding: '6px' }}>State</th>
                          <th style={{ padding: '6px' }}>Miles Driven</th>
                          <th style={{ padding: '6px' }}>Taxable Gals</th>
                          <th style={{ padding: '6px' }}>Paid Gals</th>
                          <th style={{ padding: '6px' }}>Tax Rate</th>
                          <th style={{ padding: '6px' }}>Net Tax</th>
                        </tr>
                      </thead>
                      <tbody>
                        {iftaSummary.states.map(s => (
                          <tr key={s.state} style={{ borderBottom: '1px solid #1E293B' }}>
                            <td style={{ padding: '6px', fontWeight: 800, color: '#38BDF8' }}>{s.state}</td>
                            <td style={{ padding: '6px' }}>{s.miles}</td>
                            <td style={{ padding: '6px' }}>{s.taxable_gallons}</td>
                            <td style={{ padding: '6px' }}>{s.purchased_gallons}</td>
                            <td style={{ padding: '6px' }}>${s.tax_rate}/gal</td>
                            <td style={{ padding: '6px', fontWeight: 700, color: s.net_tax_due <= 0 ? '#10B981' : '#EF4444' }}>
                              ${s.net_tax_due}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* GRID ROW 3: COMMERCIAL HAZARD NAVIGATION & DVIR PREVENTATIVE ASSET UPTIME */}
          <div className="fe-express-split-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '16px' }}>
            {/* Commercial Hazard & Clearance Card */}
            <div style={{ backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '8px', padding: '16px' }}>
              <h4 style={{ margin: '0 0 4px', fontSize: '15px', fontWeight: 800, color: '#F59E0B', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🛡️ Heavy Commercial Vehicle Clearance &amp; Hazard Radar
              </h4>
              <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#94A3B8' }}>
                Enforces truck-legal routing (12'6" clearance, Parkway bans, and bridge strike prevention).
              </p>

              <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', marginBottom: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#F8FAFC' }}>Current Corridor: Chicago ➡️ Milwaukee (I-94)</span>
                  <span style={{ backgroundColor: '#10B981', color: '#000', fontSize: '10px', fontWeight: 800, padding: '2px 6px', borderRadius: '4px' }}>
                    CLEARED
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: '#F87171', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div>⚠️ <strong>CRITICAL BAN:</strong> Lake Shore Drive (US-41) Commercial Trucks Prohibited.</div>
                  <div>⚠️ <strong>CLEARANCE WATCH:</strong> Metra viaducts along Chicago NW arterials vary from 12'2" to 13'6". Stick strictly to STAA routes (I-90 / I-94 / I-290).</div>
                </div>
              </div>
            </div>

            {/* DVIR & Asset Maintenance Card */}
            <div style={{ backgroundColor: '#0F172A', border: '1px solid #1E293B', borderRadius: '8px', padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 800, color: '#8B5CF6', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🔧 Asset Uptime &amp; DVIR Preventative Maintenance
                </h4>
                <span style={{ fontSize: '11px', color: '#A7F3D0', fontWeight: 700 }}>
                  Odometer: 84,200 mi
                </span>
              </div>
              <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#94A3B8' }}>
                Driver Vehicle Inspection Report (DVIR) compliance and proactive maintenance countdown.
              </p>

              {dvirDashboard && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {dvirDashboard.service_intervals.map((s, i) => (
                    <div key={i} style={{
                      backgroundColor: '#1E293B',
                      borderRadius: '4px',
                      padding: '8px 10px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '11px'
                    }}>
                      <span style={{ color: '#F8FAFC', fontWeight: 600 }}>{s.service}</span>
                      <span style={{
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontWeight: 700,
                        backgroundColor: s.status === 'GOOD' ? '#064E3B' : s.status === 'ATTENTION_SOON' ? '#78350F' : '#1E293B',
                        color: s.status === 'GOOD' ? '#34D399' : s.status === 'ATTENTION_SOON' ? '#FBBF24' : '#38BDF8'
                      }}>
                        Next Due: {typeof s.next_due === 'number' ? `${s.next_due.toLocaleString()} mi` : s.next_due}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: ADD SUBCONTRACT DRIVER */}
      {showAddDriverModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: '#0F172A',
            border: '1px solid #334155',
            borderRadius: '10px',
            padding: '24px',
            maxWidth: '560px',
            width: '92%',
            color: '#F8FAFC',
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, color: '#38BDF8', fontSize: '17px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                👤 Add 1099 Subcontract Driver
              </h3>
              <button
                onClick={() => setShowAddDriverModal(false)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveDriver} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Full Legal Name *:</label>
                <input
                  type="text"
                  required
                  value={newDriverName}
                  onChange={e => setNewDriverName(e.target.value)}
                  placeholder="e.g. Marcus Johnson"
                  style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Phone Number:</label>
                  <input
                    type="tel"
                    value={newDriverPhone}
                    onChange={e => setNewDriverPhone(e.target.value)}
                    placeholder="(616) 555-0199"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Email Address:</label>
                  <input
                    type="email"
                    value={newDriverEmail}
                    onChange={e => setNewDriverEmail(e.target.value)}
                    placeholder="driver@gmail.com"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Driver License #:</label>
                  <input
                    type="text"
                    value={newDriverDL}
                    onChange={e => setNewDriverDL(e.target.value)}
                    placeholder="M123-456-789"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>DL State:</label>
                  <input
                    type="text"
                    value={newDriverDLState}
                    onChange={e => setNewDriverDLState(e.target.value)}
                    placeholder="MI"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>SSN/Tax ID (Last 4):</label>
                  <input
                    type="text"
                    maxLength={4}
                    value={newDriverSSN4}
                    onChange={e => setNewDriverSSN4(e.target.value)}
                    placeholder="1234"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Compensation Model:</label>
                  <select
                    value={newDriverPayModel}
                    onChange={e => setNewDriverPayModel(e.target.value)}
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  >
                    <option value="PERCENT_GROSS">% of Gross Load Pay</option>
                    <option value="PER_MILE">Per Mile ($/mi)</option>
                    <option value="FLAT_DAY">Flat Daily Rate ($)</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>
                    {newDriverPayModel === 'PERCENT_GROSS' ? 'Pay Rate (% of gross, e.g. 25):' : newDriverPayModel === 'PER_MILE' ? 'Rate per Mile ($/mi, e.g. 0.55):' : 'Daily Flat Rate ($):'}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={newDriverPayRate}
                    onChange={e => setNewDriverPayRate(e.target.value)}
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Medical Card Expiration:</label>
                  <input
                    type="date"
                    value={newDriverMedCardExp}
                    onChange={e => setNewDriverMedCardExp(e.target.value)}
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>W-9 Form Status:</label>
                  <select
                    value={newDriverW9Status}
                    onChange={e => setNewDriverW9Status(e.target.value)}
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  >
                    <option value={1}>✅ Signed W-9 Form on File</option>
                    <option value={0}>❌ Pending W-9 Form</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Internal Notes:</label>
                <textarea
                  rows={2}
                  value={newDriverNotes}
                  onChange={e => setNewDriverNotes(e.target.value)}
                  placeholder="e.g. Drives night hauls, clean MVR, prefers Midwest corridor."
                  style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button
                  type="button"
                  onClick={() => setShowAddDriverModal(false)}
                  style={{ padding: '8px 14px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '8px 16px', backgroundColor: '#059669', color: '#FFF', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
                >
                  💾 Save Subcontract Driver
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: RECORD TRIP SETTLEMENT / DRIVER PAYOUT */}
      {showAddSettlementModal && selectedDriverForSettlement && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: '#0F172A',
            border: '1px solid #334155',
            borderRadius: '10px',
            padding: '24px',
            maxWidth: '560px',
            width: '92%',
            color: '#F8FAFC',
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, color: '#10B981', fontSize: '17px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                💵 Record Driver Trip Settlement
              </h3>
              <button
                onClick={() => setShowAddSettlementModal(false)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', marginBottom: '14px', fontSize: '12px' }}>
              <div><strong>Driver:</strong> <span style={{ color: '#38BDF8' }}>{selectedDriverForSettlement.full_name}</span></div>
              <div>
                <strong>Agreed Rate:</strong> {selectedDriverForSettlement.pay_model === 'PERCENT_GROSS' ? `${selectedDriverForSettlement.pay_rate}% of Gross` : selectedDriverForSettlement.pay_model === 'PER_MILE' ? `$${selectedDriverForSettlement.pay_rate}/mile` : `$${selectedDriverForSettlement.pay_rate}/day`}
              </div>
            </div>

            <form onSubmit={handleRecordSettlement} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Trip Date:</label>
                  <input
                    type="date"
                    required
                    value={settleDate}
                    onChange={e => setSettleDate(e.target.value)}
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Lane (Origin ➡️ Dest):</label>
                  <input
                    type="text"
                    required
                    value={settleLane}
                    onChange={e => setSettleLane(e.target.value)}
                    placeholder="e.g. Chicago, IL -> Detroit, MI"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Total Miles Driven:</label>
                  <input
                    type="number"
                    step="0.1"
                    required
                    value={settleMiles}
                    onChange={e => setSettleMiles(e.target.value)}
                    placeholder="e.g. 280.5"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Gross Load Pay ($):</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={settleGrossPay}
                    onChange={e => setSettleGrossPay(e.target.value)}
                    placeholder="e.g. 950"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Fuel Deductions ($):</label>
                  <input
                    type="number"
                    step="0.01"
                    value={settleFuelDeduct}
                    onChange={e => setSettleFuelDeduct(e.target.value)}
                    placeholder="0"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Cash Advance ($):</label>
                  <input
                    type="number"
                    step="0.01"
                    value={settleAdvance}
                    onChange={e => setSettleAdvance(e.target.value)}
                    placeholder="0"
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  />
                </div>
              </div>

              {/* Live Calculation Preview */}
              {settleGrossPay && (
                <div style={{ backgroundColor: '#064E3B', padding: '10px 14px', borderRadius: '6px', border: '1px solid #059669', fontSize: '12px' }}>
                  <div style={{ color: '#A7F3D0', fontWeight: 600 }}>Estimated Net Payout:</div>
                  <div style={{ fontSize: '18px', fontWeight: 800, color: '#FFF', marginTop: '2px' }}>
                    ${Math.max(0, Math.round(
                      (selectedDriverForSettlement.pay_model === 'PERCENT_GROSS'
                        ? (parseFloat(settleGrossPay) || 0) * (selectedDriverForSettlement.pay_rate / 100)
                        : selectedDriverForSettlement.pay_model === 'PER_MILE'
                          ? (parseFloat(settleMiles) || 0) * selectedDriverForSettlement.pay_rate
                          : selectedDriverForSettlement.pay_rate)
                      - (parseFloat(settleFuelDeduct) || 0)
                      - (parseFloat(settleAdvance) || 0)
                    )).toLocaleString()}
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Payment Method:</label>
                  <select
                    value={settlePayMethod}
                    onChange={e => setSettlePayMethod(e.target.value)}
                    style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                  >
                    <option value="ZELLE">Zelle (Instant)</option>
                    <option value="DIRECT_DEPOSIT">Direct Deposit (ACH)</option>
                    <option value="CHECK">Paper Check</option>
                    <option value="CASHAPP">Cash App / Venmo</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Settlement Notes:</label>
                <textarea
                  rows={2}
                  value={settleNotes}
                  onChange={e => setSettleNotes(e.target.value)}
                  placeholder="e.g. Paid via Zelle immediately after delivery receipt confirmed."
                  style={{ width: '100%', padding: '8px', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#FFF', fontSize: '12px' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button
                  type="button"
                  onClick={() => setShowAddSettlementModal(false)}
                  style={{ padding: '8px 14px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', fontSize: '12px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '8px 16px', backgroundColor: '#10B981', color: '#000', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 800, cursor: 'pointer' }}
                >
                  ✅ Record 1099 Settlement
                </button>
              </div>
            </form>
          </div>
        </div>
      )}


      {/* Auto-Bid & Rate Confirmation Modal */}
      {selectedBidLoad && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: '#0F172A',
            border: '1px solid #334155',
            borderRadius: '10px',
            padding: '24px',
            maxWidth: '650px',
            width: '90%',
            color: '#F8FAFC',
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, color: '#38BDF8', fontSize: '18px' }}>
                💼 Automated Broker Bid: {selectedBidLoad.load_id}
              </h3>
              <button
                onClick={() => setSelectedBidLoad(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '13px' }}>
              <div><strong>Lane:</strong> {selectedBidLoad.origin_city_state} ➡️ {selectedBidLoad.dest_city_state}</div>
              <div><strong>Trip Distance:</strong> {selectedBidLoad.total_miles} loaded miles | <strong>Posted Pay:</strong> ${selectedBidLoad.flat_rate_pay} (${selectedBidLoad.true_rpm}/mi w/ DH)</div>
              <div><strong>Broker:</strong> {selectedBidLoad.broker_name} {selectedBidLoad.broker_phone && `(${selectedBidLoad.broker_phone})`}</div>
            </div>

            {/* Phase 2: Broker Credit & 7-Day Spot Market Benchmarking Card */}
            {(() => {
              const bench = getLocalSpotBenchmark(selectedBidLoad.origin_city_state, selectedBidLoad.dest_city_state, selectedBidLoad.true_rpm, selectedBidLoad.total_miles);
              const credit = getLocalBrokerCredit(selectedBidLoad.broker_name);
              return (
                <div style={{
                  backgroundColor: '#091E42',
                  border: '1px solid #1E40AF',
                  borderRadius: '6px',
                  padding: '12px',
                  marginBottom: '16px',
                  fontSize: '12px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        backgroundColor: bench.badgeColor,
                        color: '#000',
                        fontWeight: 800,
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        textTransform: 'uppercase'
                      }}>
                        {bench.assessment}
                      </span>
                      <strong style={{ color: '#E2E8F0' }}>Illustrative Lane Target: ${bench.avg_rpm.toFixed(2)}/mi</strong>
                    </div>
                    <span style={{
                      fontWeight: 700,
                      color: Number(bench.diff) >= 0 ? '#10B981' : '#EF4444'
                    }}>
                      {Number(bench.diff) >= 0 ? `+${bench.diff}` : bench.diff} $/mi vs fixed target
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', backgroundColor: '#0B132B', padding: '8px', borderRadius: '4px', marginBottom: '8px' }}>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94A3B8' }}>Illustrative Broker Credit</div>
                      <div style={{ fontWeight: 700, color: credit.color }}>{credit.score} ({credit.rating})</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94A3B8' }}>Example Factoring Status</div>
                      <div style={{ fontWeight: 700, color: credit.color }}>{credit.factoring}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94A3B8' }}>Example Days to Pay</div>
                      <div style={{ fontWeight: 700, color: '#F1F5F9' }}>{credit.days_to_pay} Days</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: '#94A3B8' }}>Illustrative Counter</div>
                      <div style={{ fontWeight: 700, color: '#38BDF8' }}>
                        ${Math.round(bench.avg_rpm * selectedBidLoad.total_miles).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  <div style={{ fontSize: '11px', color: '#93C5FD' }}>
                    💡 <strong>Counter-Bid Advice:</strong> {bench.assessment === 'PREMIUM'
                      ? 'Rate exceeds the illustrative target. Verify current lane rates and broker terms before bidding.'
                      : bench.assessment === 'ABOVE TARGET'
                      ? `Above the illustrative target. If counter-bidding, request $${Math.round((selectedBidLoad.true_rpm + 0.20) * selectedBidLoad.total_miles)} to test broker flexibility.`
                      : `Rate is below the illustrative target ($${bench.avg_rpm}/mi). Counter at $${Math.round(bench.avg_rpm * selectedBidLoad.total_miles)} using a fixed illustrative target, not live market data.`
                    }
                  </div>
                </div>
              );
            })()}

            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 700 }}>Draft Bid — verify carrier profile and broker details before sending:</label>
              <textarea
                readOnly
                value={bidData?.email_body || 'Generating bid...'}
                rows={10}
                style={{
                  width: '100%',
                  backgroundColor: '#020617',
                  border: '1px solid #334155',
                  color: '#CBD5E1',
                  borderRadius: '6px',
                  padding: '10px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  marginTop: '4px'
                }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 700 }}>Compact SMS Negotiation Text (&lt;160 chars):</label>
              <input
                type="text"
                readOnly
                value={bidData?.sms_text || 'Generating SMS...'}
                style={{
                  width: '100%',
                  backgroundColor: '#020617',
                  border: '1px solid #334155',
                  color: '#38BDF8',
                  borderRadius: '6px',
                  padding: '8px',
                  fontSize: '12px',
                  fontWeight: 600,
                  marginTop: '4px'
                }}
              />
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: '8px' }}>
              {selectedBidLoad.broker_phone && (
                <a
                  href={`tel:${selectedBidLoad.broker_phone.replace(/[^0-9]/g, '')}`}
                  style={{
                    padding: '8px 14px',
                    backgroundColor: '#059669',
                    color: '#FFF',
                    borderRadius: '6px',
                    textDecoration: 'none',
                    fontWeight: 700,
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  📞 Call Broker
                </a>
              )}
              {selectedBidLoad.broker_phone && (
                <a
                  href={`sms:${selectedBidLoad.broker_phone.replace(/[^0-9]/g, '')}?body=${encodeURIComponent(bidData?.sms_text || '')}`}
                  style={{
                    padding: '8px 14px',
                    backgroundColor: '#0284C7',
                    color: '#FFF',
                    borderRadius: '6px',
                    textDecoration: 'none',
                    fontWeight: 700,
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  💬 Send SMS
                </a>
              )}
              <a
                href={buildDevinMailto(selectedBidLoad.broker_email, selectedBidLoad, bidData?.subject, bidData?.email_body)}
                style={{
                  padding: '8px 14px',
                  backgroundColor: '#4F46E5',
                  color: '#FFF',
                  borderRadius: '6px',
                  textDecoration: 'none',
                  fontWeight: 700,
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                ✉️ Send Email
              </a>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(bidData?.email_body || '');
                  alert('Email bid copied to clipboard!');
                }}
                style={{ padding: '8px 14px', backgroundColor: '#1E293B', color: '#CBD5E1', border: '1px solid #475569', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}
              >
                📋 Copy Email
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(bidData?.sms_text || '');
                  alert('SMS negotiation text copied to clipboard!');
                }}
                style={{ padding: '8px 14px', backgroundColor: '#1E293B', color: '#CBD5E1', border: '1px solid #475569', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}
              >
                📱 Copy SMS
              </button>
              <button
                onClick={() => setSelectedBidLoad(null)}
                style={{ padding: '8px 14px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Smart Backhaul & Trip-Chain Modal (Never Deadhead Home Empty) */}
      {selectedBackhaulLoad && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999,
          padding: '16px'
        }}>
          <div style={{
            backgroundColor: '#0F172A',
            border: '1px solid #7C3AED',
            borderRadius: '10px',
            padding: '24px',
            maxWidth: '780px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            color: '#F8FAFC',
            boxShadow: '0 10px 25px rgba(0,0,0,0.6)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '20px' }}>🔄</span>
                <h3 style={{ margin: 0, color: '#A78BFA', fontSize: '18px', fontWeight: 800 }}>
                  Smart Backhaul Radar &amp; Round-Trip Profit Chain
                </h3>
              </div>
              <button
                onClick={() => setSelectedBackhaulLoad(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '20px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {/* Outbound Leg Summary */}
            <div style={{ backgroundColor: '#1E293B', padding: '14px', borderRadius: '8px', marginBottom: '16px', borderLeft: '4px solid #38BDF8' }}>
              <div style={{ fontSize: '11px', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 700 }}>Outbound Run (Leg 1)</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#F8FAFC', marginTop: '2px' }}>
                {selectedBackhaulLoad.origin_city_state} ➡️ {selectedBackhaulLoad.dest_city_state} ({selectedBackhaulLoad.total_miles} mi)
              </div>
              <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '13px' }}>
                <span style={{ color: '#10B981', fontWeight: 700 }}>Pay: ${selectedBackhaulLoad.flat_rate_pay}</span>
                <span style={{ color: '#38BDF8' }}>RPM: ${selectedBackhaulLoad.true_rpm}/mi</span>
                <span style={{ color: '#CBD5E1' }}>Broker: {selectedBackhaulLoad.broker_name}</span>
              </div>
            </div>

            {/* Radar Matches */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#CBD5E1' }}>
                  🎯 Matching Return Runs from {selectedBackhaulLoad.dest_city_state} back towards {homeBase}:
                </div>
                <span style={{ fontSize: '11px', color: '#A78BFA', fontWeight: 600 }}>
                  {backhaulsList.length} backhauls located
                </span>
              </div>

              {loadingBackhauls ? (
                <div style={{ textAlign: 'center', padding: '24px', color: '#94A3B8' }}>Scanning live freight boards for backhauls...</div>
              ) : backhaulsList.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px', color: '#94A3B8', backgroundColor: '#1E293B', borderRadius: '6px' }}>
                  No exact return backhaul currently posted for this destination. Check neighboring states or widen deadhead radius.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {backhaulsList.map(bh => {
                    const combinedMiles = Number(selectedBackhaulLoad.total_miles) + Number(bh.total_miles);
                    const combinedPay = Number(selectedBackhaulLoad.flat_rate_pay) + Number(bh.flat_rate_pay);
                    const chainRpm = (combinedPay / Math.max(combinedMiles, 1)).toFixed(2);
                    return (
                      <div
                        key={bh.load_id}
                        style={{
                          backgroundColor: '#1E293B',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                          padding: '12px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{
                            padding: '2px 8px',
                            backgroundColor: bh.score === 'Greenlight' ? '#065F46' : '#92400E',
                            color: '#FFF',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 700
                          }}>
                            RETURN LEG: {bh.score.toUpperCase()}
                          </span>
                          <span style={{ fontSize: '12px', color: '#38BDF8', fontWeight: 700 }}>
                            {bh.load_id}
                          </span>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
                          <div>
                            <div style={{ fontSize: '14px', fontWeight: 700, color: '#F1F5F9' }}>
                              {bh.origin_city_state} ➡️ {bh.dest_city_state} ({bh.total_miles} mi)
                            </div>
                            <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                              Eq: {bh.equipment_type} | Wt: {bh.weight_lbs} lbs | Pay: <strong style={{ color: '#10B981' }}>${bh.flat_rate_pay}</strong> (${bh.true_rpm}/mi)
                            </div>
                          </div>

                          {/* Round-Trip Chain Profit Badge */}
                          <div style={{
                            backgroundColor: '#0F172A',
                            border: '1px solid #10B981',
                            borderRadius: '6px',
                            padding: '6px 10px',
                            textAlign: 'right'
                          }}>
                            <div style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase' }}>Round-Trip Gross</div>
                            <div style={{ fontSize: '15px', fontWeight: 800, color: '#10B981' }}>${combinedPay.toLocaleString()}</div>
                            <div style={{ fontSize: '11px', color: '#38BDF8', fontWeight: 600 }}>Avg ${chainRpm}/mi ({combinedMiles} mi)</div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #334155', paddingTop: '8px', marginTop: '4px' }}>
                          <div style={{ fontSize: '12px', color: '#CBD5E1' }}>
                            Broker: {bh.broker_name} {bh.broker_phone && `(📞 ${bh.broker_phone})`}
                          </div>
                          <div style={{ display: 'flex', gap: '6px' }}>
                            {bh.broker_phone && (
                              <a
                                href={`tel:${bh.broker_phone.replace(/[^0-9]/g, '')}`}
                                style={{
                                  padding: '4px 10px',
                                  backgroundColor: '#059669',
                                  color: '#FFF',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  textDecoration: 'none'
                                }}
                              >
                                📞 Call
                              </a>
                            )}
                            <button
                              onClick={() => {
                                setSelectedBackhaulLoad(null);
                                handleOpenBidModal(bh);
                              }}
                              style={{
                                padding: '4px 10px',
                                backgroundColor: '#2563EB',
                                color: '#FFF',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              💼 Bid Return Leg
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setSelectedBackhaulLoad(null)}
                style={{ padding: '8px 18px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
              >
                Close Backhaul Radar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APEX MODAL 1: MULTI-CHANNEL SINGLE-SEGMENT BLAST BIDDING */}
      {selectedLoadForBlast && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: '#0F172A',
            border: '2px solid #EC4899',
            borderRadius: '10px',
            padding: '24px',
            maxWidth: '600px',
            width: '90%',
            color: '#F8FAFC',
            boxShadow: '0 10px 35px rgba(236, 72, 153, 0.3)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ margin: 0, color: '#F472B6', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                Bid draft preparation
              </h3>
              <button
                onClick={() => setSelectedLoadForBlast(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '12px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
              <div><strong>Target Load:</strong> {selectedLoadForBlast.load_id} ({selectedLoadForBlast.origin_city_state} ➡️ {selectedLoadForBlast.dest_city_state})</div>
              <div><strong>Broker:</strong> {selectedLoadForBlast.broker_name} {selectedLoadForBlast.broker_phone && `• ${selectedLoadForBlast.broker_phone}`}</div>
              <div><strong>Posted Payout:</strong> ${selectedLoadForBlast.flat_rate_pay} (${selectedLoadForBlast.rpm}/mi)</div>
            </div>

            {/* Inbound Ghost-Booking Protection Credit Overlay */}
            <div style={{
              backgroundColor: '#064E3B',
              border: '1px solid #10B981',
              borderRadius: '6px',
              padding: '10px 14px',
              marginBottom: '14px',
              fontSize: '12px'
            }}>
              <div style={{ fontWeight: 800, color: '#6EE7B7' }}>Illustrative broker example — verify independently:</div>
              <div style={{ color: '#D1FAE5', marginTop: '3px' }}>
                Credit Score: <strong>98/100</strong> | Avg Days to Pay: <strong>21 days</strong> | Bond: <strong>$75,000 Active</strong> | RTS/Triumph: <strong>Tier 1 Approved</strong>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', color: '#CBD5E1', display: 'block', marginBottom: '6px' }}>
                <strong>Devin's Rapid Counter-Bid Amount ($):</strong>
              </label>
              <input
                type="number"
                value={blastBidAmount}
                onChange={e => setBlastBidAmount(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: '#020617',
                  border: '1px solid #EC4899',
                  borderRadius: '6px',
                  color: '#FFF',
                  fontSize: '16px',
                  fontWeight: 800
                }}
                placeholder="Enter counter offer"
              />
            </div>

            {blastStatus && (
              <div style={{ backgroundColor: '#1E1B4B', border: '1px solid #6366F1', padding: '10px', borderRadius: '6px', marginBottom: '14px', fontSize: '12px', color: '#C7D2FE' }}>
                <strong>Bid draft prepared locally.</strong><br />
                SMS, email and TMS providers are not connected. Nothing sent; no broker acceptance confirmed.
                <p style={{ whiteSpace: 'pre-wrap' }}>{blastStatus.pitch_snippet}</p>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setSelectedLoadForBlast(null)}
                style={{ padding: '8px 14px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
              >
                Close
              </button>
              <button
                onClick={() => {
                  request(`${baseUrl}/api/v1/fe-express/blast-bid`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      load: selectedLoadForBlast,
                      bid_amount: parseFloat(blastBidAmount) || selectedLoadForBlast.flat_rate_pay,
                      dispatcher_profile: DEVIN_DISPATCH_PROFILE
                    })
                  })
                    .then(r => r.json())
                    .then(d => {
                      if (d.success) {
                        setBlastStatus(d.blast_result);
                      } else {
                        alert(`Error: ${d.error}`);
                      }
                    })
                    .catch(err => alert(`Network error: ${err.message}`));
                }}
                style={{
                  padding: '8px 18px',
                  backgroundColor: '#BE185D',
                  color: '#FFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 800,
                  fontSize: '13px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                Save local bid draft
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APEX MODAL 2: PREDICTIVE HORIZON MAPPING */}
      {horizonMapModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: '#0F172A',
            border: '2px solid #0284C7',
            borderRadius: '10px',
            padding: '24px',
            maxWidth: '560px',
            width: '90%',
            color: '#F8FAFC',
            boxShadow: '0 10px 35px rgba(2, 132, 199, 0.3)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ margin: 0, color: '#38BDF8', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🌅 Predictive "Load-to-Truck" Horizon Projection
              </h3>
              <button
                onClick={() => setHorizonMapModal(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
              <div style={{ fontSize: '15px', fontWeight: 800, color: '#F8FAFC' }}>
                {horizonMapModal.destination} Dock Window
              </div>
              <div style={{ color: '#94A3B8', marginTop: '4px' }}>
                Projected Arrival: <strong style={{ color: '#38BDF8' }}>{horizonMapModal.projected_arrival_window}</strong> ({horizonMapModal.hours_until_dock} hours ahead)
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '14px', textAlign: 'center' }}>
              <div style={{ backgroundColor: '#020617', padding: '10px', borderRadius: '6px', border: '1px solid #1E293B' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Load-to-Truck</div>
                <div style={{ fontSize: '16px', fontWeight: 900, color: '#10B981', marginTop: '2px' }}>{horizonMapModal.load_to_truck_ratio}</div>
              </div>
              <div style={{ backgroundColor: '#020617', padding: '10px', borderRadius: '6px', border: '1px solid #1E293B' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Market Pressure</div>
                <div style={{ fontSize: '13px', fontWeight: 800, color: '#F59E0B', marginTop: '4px' }}>{horizonMapModal.market_pressure}</div>
              </div>
              <div style={{ backgroundColor: '#020617', padding: '10px', borderRadius: '6px', border: '1px solid #1E293B' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Projected Outbound</div>
                <div style={{ fontSize: '16px', fontWeight: 900, color: '#38BDF8', marginTop: '2px' }}>${horizonMapModal.projected_outbound_rpm}/mi</div>
              </div>
            </div>

            <div style={{ backgroundColor: '#064E3B', border: '1px solid #059669', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '12px', color: '#A7F3D0' }}>
              {horizonMapModal.recommendation}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setHorizonMapModal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
              >
                Close Horizon Projection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APEX MODAL 3: DOCK FACILITY & CONSIGNEE DELAY INTELLIGENCE */}
      {dockIntelModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10001
        }}>
          <div style={{
            backgroundColor: '#0F172A', border: '1px solid #475569', borderRadius: '8px',
            width: '540px', maxWidth: '95vw', padding: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)',
            color: '#F8FAFC'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🏢 Consignee & Dock Facility Intelligence
              </h3>
              <button
                onClick={() => setDockIntelModal(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
              <div style={{ fontSize: '15px', fontWeight: 800, color: '#F8FAFC' }}>
                {dockIntelModal.facility_name}
              </div>
              <div style={{ color: '#94A3B8', marginTop: '4px' }}>
                Address: <strong style={{ color: '#E2E8F0' }}>{dockIntelModal.address}</strong>
              </div>
              <div style={{ marginTop: '6px', display: 'inline-block', padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 800, backgroundColor: dockIntelModal.avg_dwell_minutes >= 180 ? '#7F1D1D' : (dockIntelModal.avg_dwell_minutes >= 100 ? '#78350F' : '#064E3B'), color: dockIntelModal.avg_dwell_minutes >= 180 ? '#FECACA' : (dockIntelModal.avg_dwell_minutes >= 100 ? '#FDE68A' : '#A7F3D0') }}>
                {dockIntelModal.risk_assessment}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '14px', textAlign: 'center' }}>
              <div style={{ backgroundColor: '#020617', padding: '10px', borderRadius: '6px', border: '1px solid #1E293B' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Avg Dwell</div>
                <div style={{ fontSize: '15px', fontWeight: 900, color: dockIntelModal.avg_dwell_minutes >= 180 ? '#EF4444' : '#10B981', marginTop: '2px' }}>
                  {dockIntelModal.dwell_hours} hrs
                </div>
              </div>
              <div style={{ backgroundColor: '#020617', padding: '10px', borderRadius: '6px', border: '1px solid #1E293B' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Parking</div>
                <div style={{ fontSize: '13px', fontWeight: 800, color: dockIntelModal.overnight_parking ? '#10B981' : '#EF4444', marginTop: '4px' }}>
                  {dockIntelModal.overnight_parking ? '✅ Allowed' : '❌ No'}
                </div>
              </div>
              <div style={{ backgroundColor: '#020617', padding: '10px', borderRadius: '6px', border: '1px solid #1E293B' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Lumper Fee</div>
                <div style={{ fontSize: '13px', fontWeight: 800, color: dockIntelModal.lumper_fee_required ? '#F59E0B' : '#10B981', marginTop: '4px' }}>
                  {dockIntelModal.lumper_fee_required ? `$${dockIntelModal.avg_lumper_cost}` : 'None'}
                </div>
              </div>
              <div style={{ backgroundColor: '#020617', padding: '10px', borderRadius: '6px', border: '1px solid #1E293B' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8' }}>Driver Score</div>
                <div style={{ fontSize: '15px', fontWeight: 900, color: '#38BDF8', marginTop: '2px' }}>
                  ⭐ {dockIntelModal.driver_rating}/5
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: '#020617', border: '1px solid #334155', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '12px', color: '#CBD5E1' }}>
              <strong style={{ color: '#F1F5F9' }}>Gate & Check-in Protocol:</strong>
              <div style={{ marginTop: '4px', lineHeight: '1.4' }}>{dockIntelModal.gate_access_notes}</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDockIntelModal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
              >
                Close Dock Intelligence
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APEX MODAL 4: DYNAMIC LIVE COST-PER-MILE (CPM) CALIBRATION */}
      {cpmCalibrationModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10001
        }}>
          <div style={{
            backgroundColor: '#0F172A', border: '1px solid #059669', borderRadius: '8px',
            width: '560px', maxWidth: '95vw', padding: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)',
            color: '#F8FAFC'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#10B981', display: 'flex', alignItems: 'center', gap: '8px' }}>
                📊 Dynamic Live Cost-Per-Mile (CPM) Calibration
              </h3>
              <button
                onClick={() => setCpmCalibrationModal(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94A3B8' }}>Target Load Bidding Floor:</span>
                <span style={{ fontWeight: 800, color: '#F8FAFC' }}>{cpmCalibrationModal.targetLoad?.load_id} ({cpmCalibrationModal.targetLoad?.loaded_miles} mi)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                <span style={{ color: '#94A3B8' }}>Broker's Posted RPM:</span>
                <span style={{ fontWeight: 800, color: (cpmCalibrationModal.targetLoad?.rpm >= cpmCalibrationModal.recommended_minimum_rpm) ? '#10B981' : '#EF4444' }}>
                  ${cpmCalibrationModal.targetLoad?.rpm}/mi
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '16px' }}>
              <div style={{ backgroundColor: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1E293B', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#94A3B8', textTransform: 'uppercase' }}>True Break-Even Floor</div>
                <div style={{ fontSize: '22px', fontWeight: 900, color: '#F59E0B', marginTop: '4px' }}>
                  ${cpmCalibrationModal.true_break_even_cpm_floor}/mi
                </div>
                <div style={{ fontSize: '10px', color: '#64748B', marginTop: '2px' }}>Fixed + Variable Operating Cash Floor</div>
              </div>
              <div style={{ backgroundColor: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #059669', textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: '#10B981', textTransform: 'uppercase' }}>Target Bidding RPM ({cpmCalibrationModal.target_margin_pct}% Margin)</div>
                <div style={{ fontSize: '22px', fontWeight: 900, color: '#10B981', marginTop: '4px' }}>
                  ${cpmCalibrationModal.recommended_minimum_rpm}/mi
                </div>
                <div style={{ fontSize: '10px', color: '#64748B', marginTop: '2px' }}>Profitable Quote Threshold</div>
              </div>
            </div>

            <div style={{ backgroundColor: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #334155', fontSize: '12px', marginBottom: '16px' }}>
              <div style={{ fontWeight: 800, color: '#E2E8F0', marginBottom: '8px' }}>Operating Expense Breakdown ($/mi):</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px', color: '#94A3B8' }}>
                <div>• Diesel Fuel: <strong style={{ color: '#F1F5F9' }}>${cpmCalibrationModal.fuel_cpm}/mi</strong></div>
                <div>• Driver Base Pay: <strong style={{ color: '#F1F5F9' }}>${cpmCalibrationModal.driver_cpm}/mi</strong></div>
                <div>• Maintenance & Tires: <strong style={{ color: '#F1F5F9' }}>${cpmCalibrationModal.maintenance_wear_cpm}/mi</strong></div>
                <div>• Overhaul Sinking Fund: <strong style={{ color: '#F1F5F9' }}>${cpmCalibrationModal.depreciation_reserve_cpm}/mi</strong></div>
                <div>• Monthly Fixed Overhead: <strong style={{ color: '#F1F5F9' }}>${cpmCalibrationModal.fixed_cpm_total}/mi</strong></div>
                <div>• Total Fixed / Mo: <strong style={{ color: '#F1F5F9' }}>${cpmCalibrationModal.total_fixed_monthly_usd}</strong></div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setCpmCalibrationModal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
              >
                Close Calculator
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APEX MODAL 5: AUTOMATED ACCESSORIAL CLAIMS BUILDER */}
      {accessorialClaimModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10001
        }}>
          <div style={{
            backgroundColor: '#0F172A', border: '1px solid #DC2626', borderRadius: '8px',
            width: '580px', maxWidth: '95vw', padding: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)',
            color: '#F8FAFC'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#EF4444', display: 'flex', alignItems: 'center', gap: '8px' }}>
                ⚖️ 1-Click Accessorial Claims & Dispute Builder
              </h3>
              <button
                onClick={() => setAccessorialClaimModal(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
              <div><strong>Target Load:</strong> {accessorialClaimModal.load_id} ({accessorialClaimModal.origin_city_state} ➡️ {accessorialClaimModal.dest_city_state})</div>
              <div><strong>Broker:</strong> {accessorialClaimModal.broker_name} {accessorialClaimModal.broker_mc && `(${accessorialClaimModal.broker_mc})`}</div>
            </div>

            {!claimResult ? (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                  <div>
                    <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Claim Type</label>
                    <select
                      value={claimParams.claim_type}
                      onChange={e => setClaimParams({ ...claimParams, claim_type: e.target.value })}
                      style={{ width: '100%', padding: '8px', backgroundColor: '#020617', color: '#FFF', border: '1px solid #334155', borderRadius: '4px' }}
                    >
                      <option value="DETENTION">Detention Pay (Dock Delay &gt; 2 hrs)</option>
                      <option value="TONU">TONU (Truck Ordered Not Used)</option>
                      <option value="LAYOVER">Layover (Overnight Facility Hold)</option>
                      <option value="LUMPER">Lumper Fee Reimbursement</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', color: '#94A3B8', display: 'block', marginBottom: '4px' }}>Units Claimed (Hours or Events)</label>
                    <input
                      type="number"
                      step="0.5"
                      value={claimParams.units}
                      onChange={e => setClaimParams({ ...claimParams, units: parseFloat(e.target.value) || 1.0 })}
                      style={{ width: '100%', padding: '8px', backgroundColor: '#020617', color: '#FFF', border: '1px solid #334155', borderRadius: '4px' }}
                    />
                  </div>
                </div>

                <div style={{ backgroundColor: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1E293B', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: '#94A3B8', fontSize: '12px' }}>Rate Tariff:</span>
                    <span style={{ fontWeight: 800, color: '#F1F5F9' }}>${claimParams.claim_type === 'TONU' ? '250.00 Flat' : (claimParams.claim_type === 'LAYOVER' ? '350.00 / day' : '$75.00 / hr')}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                    <span style={{ color: '#94A3B8', fontSize: '13px' }}>Calculated Total Claim:</span>
                    <span style={{ fontSize: '18px', fontWeight: 900, color: '#EF4444' }}>
                      ${(claimParams.units * (claimParams.claim_type === 'TONU' ? 250 : (claimParams.claim_type === 'LAYOVER' ? 350 : 75))).toFixed(2)}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <button
                    onClick={() => setAccessorialClaimModal(null)}
                    style={{ padding: '8px 16px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      const rate = claimParams.claim_type === 'TONU' ? 250 : (claimParams.claim_type === 'LAYOVER' ? 350 : 75);
                      request(`${baseUrl}/api/v1/fe-express/accessorial-claim`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          claim_type: claimParams.claim_type,
                          load_id: accessorialClaimModal.load_id,
                          broker_name: accessorialClaimModal.broker_name,
                          broker_mc: accessorialClaimModal.broker_mc || '${DEVIN_DISPATCH_PROFILE.mc}',
                          broker_email: accessorialClaimModal.broker_email || 'claims@freightbroker.com',
                          units_claimed: claimParams.units,
                          unit_rate: rate,
                          facility_address: accessorialClaimModal.dest_city_state || 'Delivery Facility'
                        })
                      })
                        .then(r => r.json())
                        .then(d => {
                          if (d.success) setClaimResult(d.accessorial_claim);
                        })
                        .catch(err => alert(`Error: ${err.message}`));
                    }}
                    style={{ padding: '8px 16px', backgroundColor: '#DC2626', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
                  >
                    Generate & Stage Dispute Packet
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ backgroundColor: '#064E3B', border: '1px solid #059669', padding: '12px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px', color: '#A7F3D0' }}>
                  ✅ Dispute Claim <strong style={{ color: '#FFF' }}>{claimResult.claim_id}</strong> staged for ${Number(claimResult.total_claimed_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}!
                </div>
                <div style={{ maxHeight: '180px', overflowY: 'auto', backgroundColor: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #334155', fontSize: '11px', fontFamily: 'monospace', color: '#CBD5E1', whiteSpace: 'pre-wrap', marginBottom: '16px' }}>
                  {claimResult.formal_dispute_body}
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <button
                    onClick={() => setAccessorialClaimModal(null)}
                    style={{ padding: '8px 16px', backgroundColor: '#10B981', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* APEX MODAL 6: DYNAMIC FUEL ROUTE OPTIMIZER & ARBITRAGE */}
      {fuelOptimizerModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10001
        }}>
          <div style={{
            backgroundColor: '#0F172A', border: '1px solid #D97706', borderRadius: '8px',
            width: '540px', maxWidth: '95vw', padding: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)',
            color: '#F8FAFC'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#F59E0B', display: 'flex', alignItems: 'center', gap: '8px' }}>
                ⛽ Dynamic Fuel Route Optimizer &amp; Spot Arbitrage
              </h3>
              <button
                onClick={() => setFuelOptimizerModal(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ backgroundColor: '#1E293B', padding: '14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
              <div><strong>Trip Corridor:</strong> {fuelOptimizerModal.trip_corridor} ({fuelOptimizerModal.total_miles} mi)</div>
              <div style={{ color: '#94A3B8', marginTop: '4px' }}>
                Fuel Demand: <strong style={{ color: '#F8FAFC' }}>{fuelOptimizerModal.gallons_needed_total} gallons</strong> (Current Tank: {fuelOptimizerModal.current_tank_gallons} gal)
              </div>
            </div>

            <div style={{ backgroundColor: '#020617', border: '1px solid #059669', padding: '14px', borderRadius: '6px', marginBottom: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '14px', fontWeight: 800, color: '#38BDF8' }}>
                  {fuelOptimizerModal.optimal_fuel_stop?.station_name}
                </span>
                <span style={{ fontSize: '11px', backgroundColor: '#064E3B', color: '#A7F3D0', padding: '2px 8px', borderRadius: '4px', fontWeight: 800 }}>
                  Save ${fuelOptimizerModal.optimal_fuel_stop?.per_gal_discount}/gal
                </span>
              </div>
              <div style={{ color: '#94A3B8', fontSize: '12px', marginTop: '4px' }}>
                📍 {fuelOptimizerModal.optimal_fuel_stop?.location}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginTop: '12px', textAlign: 'center' }}>
                <div style={{ backgroundColor: '#0F172A', padding: '8px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '10px', color: '#94A3B8' }}>Retail Price</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: '#EF4444', textDecoration: 'line-through' }}>
                    ${fuelOptimizerModal.optimal_fuel_stop?.retail_price}
                  </div>
                </div>
                <div style={{ backgroundColor: '#0F172A', padding: '8px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '10px', color: '#94A3B8' }}>Carrier Discount</div>
                  <div style={{ fontSize: '15px', fontWeight: 900, color: '#10B981' }}>
                    ${fuelOptimizerModal.optimal_fuel_stop?.carrier_discount_price}
                  </div>
                </div>
                <div style={{ backgroundColor: '#0F172A', padding: '8px', borderRadius: '4px' }}>
                  <div style={{ fontSize: '10px', color: '#94A3B8' }}>Net Arbitrage Savings</div>
                  <div style={{ fontSize: '16px', fontWeight: 900, color: '#F59E0B' }}>
                    +${fuelOptimizerModal.optimal_fuel_stop?.arbitrage_savings_vs_retail}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setFuelOptimizerModal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
              >
                Close Optimizer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* APEX MODAL 7: MULTI-PLATFORM CAPACITY PUBLISHING ENGINE */}
      {capacityBroadcastModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10001
        }}>
          <div style={{
            backgroundColor: '#0F172A', border: '1px solid #0284C7', borderRadius: '8px',
            width: '540px', maxWidth: '95vw', padding: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)',
            color: '#F8FAFC'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#38BDF8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                Capacity posting draft
              </h3>
              <button
                onClick={() => setCapacityBroadcastModal(null)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '18px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {!broadcastStatus ? (
              <div>
                <div style={{ backgroundColor: '#1E293B', padding: '14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
                  <div><strong>Unit:</strong> UNIT-26FT-01 (26' Box Truck - Dock High / No Liftgate)</div>
                  <div style={{ color: '#94A3B8', marginTop: '4px' }}>
                    Origin: <strong style={{ color: '#E2E8F0' }}>{capacityBroadcastModal.location}</strong> ➡️ Destination: <strong style={{ color: '#E2E8F0' }}>{capacityBroadcastModal.destination}</strong>
                  </div>
                </div>

                <div style={{ backgroundColor: '#020617', border: '1px solid #334155', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '12px' }}>
                  <div style={{ fontWeight: 800, color: '#F1F5F9', marginBottom: '6px' }}>Intended boards — connections not configured:</div>
                  <div style={{ color: '#94A3B8', lineHeight: '1.6' }}>
                    DAT One (Direct Carrier Posting)<br />
                    Truckstop.com Pro (Expedite Filter)<br />
                    Sylectus Alliance Network<br />
                    C.H. Robinson Navisphere Carrier Portal<br />
                    TQL Direct Carrier Bidding Matrix
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <button
                    onClick={() => setCapacityBroadcastModal(null)}
                    style={{ padding: '8px 16px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        const r = await request(`${baseUrl}/api/v1/fe-express/capacity-broadcast`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            unit_id: 'UNIT-26FT-01',
                            location: capacityBroadcastModal.location,
                            destination_zone: capacityBroadcastModal.destination,
                            equipment_type: "26' Box Truck (Dock High - No Liftgate)",
                            available_time: 'Immediately'
                          })
                        });
                        const d = await r.json();
                        if (d.success) setBroadcastStatus(d.broadcast_result);
                      } catch (err) {
                        alert(`Error: ${err.message}`);
                      }
                    }}
                    style={{ padding: '8px 16px', backgroundColor: '#0284C7', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
                  >
                    Save local capacity draft
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ backgroundColor: '#064E3B', border: '1px solid #059669', padding: '14px', borderRadius: '6px', marginBottom: '14px', color: '#A7F3D0', fontSize: '13px' }}>
                  Capacity draft <strong style={{ color: '#FFF' }}>{broadcastStatus.broadcast_id}</strong> prepared locally.<br />
                  <span style={{ fontSize: '11px', color: '#D1FAE5' }}>Providers not connected. No load boards received this draft; posting and removal must be handled separately.</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => setCapacityBroadcastModal(null)}
                    style={{ padding: '8px 16px', backgroundColor: '#10B981', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* NEXT-GEN 1: DECENTRALIZED MESH-HAUL MODAL */}
      {meshModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '20px' }}>
          <div style={{ backgroundColor: '#0B0F19', border: '1px solid #6366F1', borderRadius: '12px', padding: '24px', maxWidth: '640px', width: '100%', color: '#F8FAFC' }}>
            <h3 style={{ margin: '0 0 12px', color: '#A5B4FC', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              ⛓️ Decentralized Mesh-Haul Network (P2P Capacity Trading)
            </h3>
            <p style={{ fontSize: '12px', color: '#94A3B8', marginBottom: '16px' }}>
              Eliminate the 15%–25% broker margin. Peer-to-peer capacity exchange matches fractional linear feet along shared lanes with automated cryptographic smart contracts.
            </p>

            {meshMatchResult ? (
              <div style={{ backgroundColor: '#1E1B4B', border: '1px solid #4338CA', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#C7D2FE', marginBottom: '8px' }}>
                  Smart Contract Match: {meshMatchResult.match_id}
                </div>
                <div style={{ fontSize: '12px', color: '#E0E7FF', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div><strong>Lane:</strong> {meshMatchResult.lane}</div>
                  <div><strong>Linear Space Freed:</strong> {meshMatchResult.available_linear_ft} ft</div>
                  <div><strong>Payload Allocable:</strong> {meshMatchResult.allocated_payload_lbs} lbs</div>
                  <div><strong>Pro-Rata Payout:</strong> <span style={{ color: '#34D399', fontWeight: 800 }}>${meshMatchResult.pro_rata_payout_usd}</span></div>
                  <div><strong>Status:</strong> <span style={{ color: '#10B981' }}>{meshMatchResult.contract_status}</span></div>
                  <div><strong>Broker Commission Saved:</strong> <span style={{ color: '#FBBF24', fontWeight: 800 }}>+${meshMatchResult.broker_commission_saved_usd}</span></div>
                </div>
                <div style={{ marginTop: '12px', padding: '8px', backgroundColor: '#0F172A', borderRadius: '4px', fontSize: '11px', fontFamily: 'monospace', color: '#94A3B8', wordBreak: 'break-all' }}>
                  Hash: {meshMatchResult.cryptographic_hash}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px', color: '#A5B4FC' }}>
                ⏳ Scanning active lane vectors and computing fractional linear foot arbitrage...
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setMeshModal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#6366F1', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
              >
                Close Mesh Portal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* NEXT-GEN 2: BIOMETRIC FATIGUE & HOS PREDICTIVE CATALYST MODAL */}
      {fatigueModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '20px' }}>
          <div style={{ backgroundColor: '#0B0F19', border: '1px solid #DC2626', borderRadius: '12px', padding: '24px', maxWidth: '640px', width: '100%', color: '#F8FAFC' }}>
            <h3 style={{ margin: '0 0 12px', color: '#FCA5A5', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              👁️ Biometric Fatigue &amp; HOS Predictive Catalyst
            </h3>
            <p style={{ fontSize: '12px', color: '#94A3B8', marginBottom: '16px' }}>
              Predicts driver exhaustion 2 hours before legal HOS violation using ocular micro-saccade tracking, head tilt velocity, and heart-rate variability.
            </p>

            {fatigueResult ? (
              <div style={{ backgroundColor: '#450A0A', border: '1px solid #B91C1C', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ fontSize: '14px', fontWeight: 800, color: '#FECACA' }}>Driver: {fatigueResult.driver_id} ({fatigueResult.unit_id})</span>
                  <span style={{ padding: '4px 10px', borderRadius: '4px', backgroundColor: fatigueResult.risk_level === 'CRITICAL' ? '#991B1B' : '#D97706', color: '#FFF', fontWeight: 800, fontSize: '12px' }}>
                    {fatigueResult.risk_level} RISK ({fatigueResult.fatigue_risk_index}/100)
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: '#FEE2E2', marginBottom: '10px' }}>
                  <strong>Predictive Action:</strong> {fatigueResult.predictive_action}
                </div>
                <div style={{ fontSize: '12px', color: '#FECACA', marginBottom: '6px' }}>
                  🛑 <strong>Designated Safe Haven Stop:</strong> {fatigueResult.safe_haven_parking_stop}
                </div>
                <div style={{ fontSize: '12px', color: '#FECACA', marginBottom: '12px' }}>
                  ⏱️ <strong>Proactive Receiver Reschedule:</strong> {fatigueResult.rescheduled_delivery_window}
                </div>
                <div style={{ fontSize: '11px', color: '#A7F3D0', backgroundColor: '#064E3B', padding: '8px', borderRadius: '4px' }}>
                  ✅ Dispatcher Webhook: Broker auto-notified with proactive delivery window adjustment to prevent dock detention penalties.
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px', color: '#FCA5A5' }}>
                ⏳ Ingesting front-camera ocular telemetry &amp; calculating micro-sleep probability...
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setFatigueModal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#DC2626', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
              >
                Acknowledge Alert
              </button>
            </div>
          </div>
        </div>
      )}

      {/* NEXT-GEN 3: SCOPE 3 CARBON CREDIT SPOT LEDGER MODAL */}
      {scope3Modal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '20px' }}>
          <div style={{ backgroundColor: '#0B0F19', border: '1px solid #059669', borderRadius: '12px', padding: '24px', maxWidth: '640px', width: '100%', color: '#F8FAFC' }}>
            <h3 style={{ margin: '0 0 12px', color: '#6EE7B7', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              🌱 Scope 3 Emissions &amp; Carbon Credit Spot Ledger
            </h3>
            <p style={{ fontSize: '12px', color: '#94A3B8', marginBottom: '16px' }}>
              Audit-proof carbon savings compliance engine. Generates ISO 14064-1 &amp; GLEC certified packets enabling carriers to win high-premium enterprise freight.
            </p>

            {scope3Result ? (
              <div style={{ backgroundColor: '#064E3B', border: '1px solid #10B981', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#D1FAE5', marginBottom: '10px' }}>
                  Trip Ledger: {scope3Result.dispatch_id} ({scope3Result.lane} • {scope3Result.miles} mi)
                </div>
                <div style={{ fontSize: '12px', color: '#ECFDF5', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div><strong>Standard Burn:</strong> {scope3Result.baseline_co2_kg} kg CO2</div>
                  <div><strong>Actual Green Burn:</strong> {scope3Result.actual_co2_kg} kg CO2</div>
                  <div><strong>Net CO2 Saved:</strong> <span style={{ color: '#34D399', fontWeight: 800 }}>{scope3Result.co2_saved_metric_tons} Metric Tons</span></div>
                  <div><strong>Enterprise Rebate Credit:</strong> <span style={{ color: '#FBBF24', fontWeight: 800 }}>+${scope3Result.green_rebate_credit_usd}</span></div>
                </div>
                <div style={{ marginTop: '12px', padding: '8px', backgroundColor: '#042F2E', borderRadius: '4px', fontSize: '11px', color: '#A7F3D0' }}>
                  <strong>Compliance Standard:</strong> {scope3Result.audit_certification}<br />
                  <span style={{ fontSize: '10px', color: '#6EE7B7' }}>Digital Signature: {scope3Result.cryptographic_signature}</span>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px', color: '#6EE7B7' }}>
                ⏳ Processing throttle burn vector, route topography &amp; GLEC emissions metrics...
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setScope3Modal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#059669', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
              >
                Export Compliance Packet
              </button>
            </div>
          </div>
        </div>
      )}

      {/* NEXT-GEN 4: BLACK SWAN MACRO DISRUPTION SWARM RADAR MODAL */}
      {blackSwanModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '20px' }}>
          <div style={{ backgroundColor: '#0B0F19', border: '1px solid #9333EA', borderRadius: '12px', padding: '24px', maxWidth: '640px', width: '100%', color: '#F8FAFC' }}>
            <h3 style={{ margin: '0 0 12px', color: '#D8B4FE', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              🌪️ &quot;Black Swan&quot; Macro Disruption Swarm Radar
            </h3>
            <p style={{ fontSize: '12px', color: '#94A3B8', marginBottom: '16px' }}>
              Anticipates systemic port strikes, customs outages, and arterial road collapses hours before news feeds by mining velocity sinks across all 43 fleet units.
            </p>

            {blackSwanResult ? (
              <div style={{ backgroundColor: '#3B0764', border: '1px solid #A855F7', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '14px', fontWeight: 800, color: '#F3E8FF' }}>{blackSwanResult.corridor}</span>
                  <span style={{ padding: '2px 8px', borderRadius: '4px', backgroundColor: '#7E22CE', color: '#FFF', fontWeight: 800, fontSize: '11px' }}>
                    {blackSwanResult.severity}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#E9D5FF', marginBottom: '6px' }}>
                  <strong>Velocity Drop:</strong> <span style={{ color: '#F87171', fontWeight: 800 }}>{blackSwanResult.telemetry_velocity_drop}</span>
                </div>
                <div style={{ fontSize: '13px', color: '#F5D0FE', marginBottom: '10px' }}>
                  ⚡ <strong>Preemptive Fleet Reroute:</strong> {blackSwanResult.preemptive_reroute}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', backgroundColor: '#1E1B4B', padding: '8px', borderRadius: '4px', fontSize: '11px', color: '#DDD6FE' }}>
                  <span>Detention Avoided: <strong style={{ color: '#34D399' }}>{blackSwanResult.detention_hours_avoided} hrs</strong></span>
                  <span>Fleet Savings: <strong style={{ color: '#FBBF24' }}>${blackSwanResult.dollar_value_saved_usd}</strong></span>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px', color: '#D8B4FE' }}>
                ⏳ Mining multi-truck velocity vectors and crawling regional DOT feeds...
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setBlackSwanModal(null)}
                style={{ padding: '8px 16px', backgroundColor: '#9333EA', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
              >
                Deploy Preemptive Reroute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* NEXT-GEN 5: AR NATIVE HEAD-UP DISPLAY (HUD) WINDSHIELD PROJECTION MODAL */}
      {arHudModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#000000', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '30px' }}>
          <div style={{ maxWidth: '720px', width: '100%', textAlign: 'center', transform: 'scaleY(-1)' }}>
            <div style={{ fontSize: '28px', fontWeight: 900, color: '#00FF66', letterSpacing: '4px', marginBottom: '20px' }}>
              HUD SPEED: {arHudData ? `${arHudData.current_speed_mph} MPH` : '62.0 MPH'}
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: '#38BDF8', letterSpacing: '2px', marginBottom: '16px' }}>
              BRIDGE CLEARANCE: {arHudData ? arHudData.upcoming_bridge_clearance : '13.8 FT'} [CLEAR]
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#FACC15', letterSpacing: '2px', marginBottom: '20px' }}>
              SAFE BRAKE DIST: {arHudData ? arHudData.safe_braking_distance_ft : '248 FT'}
            </div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#CBD5E1', letterSpacing: '1px' }}>
              NEXT SAFE HAVEN: {arHudData ? `${arHudData.nearest_safe_parking} (${arHudData.safe_haven_spots_open} spots)` : 'Pilot Travel Center #218 (11 spots)'}
            </div>
          </div>

          <div style={{ position: 'absolute', bottom: '30px', display: 'flex', gap: '16px', alignItems: 'center' }}>
            <span style={{ color: '#64748B', fontSize: '12px' }}>
              Place phone face-up on dashboard. Mirrored display reflects right-side up on windshield.
            </span>
            <button
              onClick={() => setArHudModal(null)}
              style={{ padding: '8px 20px', backgroundColor: '#334155', color: '#FFF', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 800 }}
            >
              Exit HUD Mode
            </button>
          </div>
        </div>
      )}
    </div>
  );

}


/** @param {{BACKEND_URL?:string,request?:typeof fetch}} props */
export default function FEExpressDispatcher(props) {
  return <PortalWorkspace baseUrl={props.BACKEND_URL || 'http://127.0.0.1:8080'} request={props.request || fetch}><DispatcherContent {...props} /></PortalWorkspace>;
}
