import React, { useState, useEffect } from 'react';
import { 
  Wine, ShieldCheck, AlertTriangle, CheckCircle, RefreshCw, 
  Search, Download, PlusCircle, Send, MapPin, Sparkles, 
  Award, FileText, Layers, Clock, DollarSign, Filter, Trash2, 
  Check, ArrowRight, Bell, Zap, Volume2, ShieldAlert
} from 'lucide-react';
import './NotoBarInventoryHub.css';
import SYSTEM_VERSION from './version';

export default function NotoBarInventoryHub({ backendUrl }) {
  const baseUrl = backendUrl || import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8080' : '');

  // 🧭 Active Operational Module (8 Core Modules)
  const [activeModule, setActiveModule] = useState('stock_matrix');

  // 📱 Kiosk Mode & High-Contrast Touch Toggle
  const [isKioskMode, setIsKioskMode] = useState(false);

  // 🏛️ Location Selector: 'GR' (Grand Rapids) vs 'GH' (Grand Haven)
  const [activeLocation, setActiveLocation] = useState('GR');

  // ─── 1. Multi-Bar Stock & Location Matrix State ───
  const [selectedZoneFilter, setSelectedZoneFilter] = useState('ALL');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [inventoryStats, setInventoryStats] = useState({ total: 38, low: 4, critical: 2, full: 32 });

  // Initial rich fallback items
  const [inventoryItems, setInventoryItems] = useState([
    { id: 'INV-GR-101', location: 'GR', name: "Tito's Handmade Vodka (750ml)", category: 'Spirits (Vodka)', parLevel: 12, upstairs: '0', downstairs: '1', banquetA: '3', banquetB: '2', patio: '0', cellarBin: 'Vault N/A', storeroom: '8 (Rack 2, Shelf B)', distributor: "Southern Glazer's", status: 'LOW' },
    { id: 'INV-GR-102', location: 'GR', name: 'Grey Goose Vodka (1L)', category: 'Spirits (Vodka)', parLevel: 8, upstairs: '2', downstairs: '2', banquetA: '1', banquetB: '1', patio: '1', cellarBin: 'Vault N/A', storeroom: '5 (Rack 2, Shelf A)', distributor: "Southern Glazer's", status: 'FULL' },
    { id: 'INV-GR-104', location: 'GR', name: 'Casamigos Blanco Tequila (750ml)', category: 'Spirits (Tequila)', parLevel: 10, upstairs: '1', downstairs: '2', banquetA: '2', banquetB: '1', patio: '1', cellarBin: 'Vault N/A', storeroom: '6 (Rack 1, Shelf A)', distributor: 'RNDC', status: 'LOW' },
    { id: 'INV-GR-106', location: 'GR', name: 'Don Julio 1942 Añejo Tequila', category: 'Spirits (Tequila)', parLevel: 4, upstairs: '1', downstairs: '1', banquetA: '0', banquetB: '0', patio: '0', cellarBin: 'Vault Reserve', storeroom: '3 (Rack 1, Shelf C)', distributor: 'RNDC', status: 'FULL' },
    { id: 'INV-GR-108', location: 'GR', name: 'Woodford Reserve Bourbon (750ml)', category: 'Spirits (Whiskey)', parLevel: 8, upstairs: '2', downstairs: '2', banquetA: '1', banquetB: '1', patio: '1', cellarBin: 'N/A', storeroom: '5 (Rack 3, Shelf A)', distributor: "Southern Glazer's", status: 'FULL' },
    { id: 'INV-GR-109', location: 'GR', name: 'Buffalo Trace Kentucky Bourbon (750ml)', category: 'Spirits (Whiskey)', parLevel: 6, upstairs: '1', downstairs: '0', banquetA: '1', banquetB: '0', patio: '0', cellarBin: 'N/A', storeroom: '2 (Rack 3, Shelf B)', distributor: 'Great Lakes Wine & Spirits', status: 'CRITICAL' },
    { id: 'INV-GR-115', location: 'GR', name: '2016 Tenuta San Guido Sassicaia', category: 'Fine Wine (Tuscany)', parLevel: 6, upstairs: '0', downstairs: '0', banquetA: '0', banquetB: '0', patio: '0', cellarBin: 'Aisle 3 • Rack D • Bin 14', storeroom: '18 (Cellar Vault)', distributor: 'Great Lakes Wine & Spirits', status: 'FULL' },
    { id: 'INV-GR-116', location: 'GR', name: '2015 Biondi-Santi Brunello di Montalcino', category: 'Fine Wine (Tuscany)', parLevel: 4, upstairs: '0', downstairs: '0', banquetA: '0', banquetB: '0', patio: '0', cellarBin: 'Aisle 1 • Rack B • Bin 08', storeroom: '12 (Cellar Vault)', distributor: 'Great Lakes Wine & Spirits', status: 'FULL' },
    { id: 'INV-GR-122', location: 'GR', name: 'Peroni Nastro Azzurro Draft Keg (1/2 Bbl)', category: 'Draft Beer', parLevel: 4, upstairs: '85% (Tap 1)', downstairs: '90% (Tap 2)', banquetA: '0% (OUT)', banquetB: '50% (Tap 1)', patio: '70% (Tap 1)', cellarBin: 'N/A', storeroom: '2 Backup Kegs', distributor: 'Imperial Beverage', status: 'LOW' },
    { id: 'INV-GR-123', location: 'GR', name: "Bell's Two Hearted Ale (1/2 Bbl Keg)", category: 'Draft Beer', parLevel: 4, upstairs: '60% (Tap 2)', downstairs: '75% (Tap 1)', banquetA: '40% (Tap 2)', banquetB: '0% (OUT)', patio: '80% (Tap 2)', cellarBin: 'N/A', storeroom: '3 Backup Kegs', distributor: 'Alliance Beverage', status: 'FULL' }
  ]);

  // Modal State for adding custom item
  const [showAddItemModal, setShowAddItemModal] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [newItemCategory, setNewItemCategory] = useState('Spirits (Vodka)');
  const [newItemPar, setNewItemPar] = useState(6);
  const [newItemStoreroom, setNewItemStoreroom] = useState('Storeroom Bay A');

  // ─── 2. Smart Barback Dispatch Queue State ───
  const [dispatchQueue, setDispatchQueue] = useState([
    { id: 'DISP-801', targetBar: 'Upstairs Main Bar (Well 1)', item: "2x Tito's Handmade Vodka", sourceLoc: 'Central Storeroom — Rack 2, Shelf B', time: '6:42 PM', requestedBy: 'Bartender Alex', status: 'PENDING' },
    { id: 'DISP-802', targetBar: 'Banquet Bar A (Grand Ballroom)', item: '1x Backup Peroni Draft Keg', sourceLoc: 'Basement Beer Cooler — Station 4', time: '6:38 PM', requestedBy: 'Banquet Lead Sam', status: 'EN_ROUTE' },
    { id: 'DISP-803', targetBar: 'Downstairs Lounge', item: '2x Casamigos Blanco Tequila', sourceLoc: 'Central Storeroom — Rack 1, Shelf A', time: '6:30 PM', requestedBy: 'Bartender Mia', status: 'DELIVERED' }
  ]);
  const [newDispatchBar, setNewDispatchBar] = useState('Upstairs Main Bar');
  const [newDispatchItem, setNewDispatchItem] = useState("Tito's Vodka");
  const [newDispatchQty, setNewDispatchQty] = useState(2);

  // ─── 3. Bar SOS Emergency Calls State ───
  const [sosCalls, setSosCalls] = useState([
    { id: 'SOS-01', bar: 'Upstairs Main Bar', type: '🧊 Need Ice Bin Refill', urgency: 'HIGH', time: '6:45 PM' },
    { id: 'SOS-02', bar: 'Downstairs Lounge', type: '🍸 Need Clean Rocks / Coupe Glasses', urgency: 'NORMAL', time: '6:41 PM' }
  ]);

  // ─── 4. Live 86'd Interceptor State ───
  const [eightySixBoard, setEightySixBoard] = useState([
    { id: '86-901', item: 'Chilean Sea Bass (Fresh Catch)', station: 'Kitchen Expo Line', reason: '38 portions sold out; delivery 8 AM tomorrow', altSuggestion: 'Grilled Mediterranean Halibut', time: '6:14 PM' },
    { id: '86-902', item: 'Casamigos Añejo Tequila', station: 'Upstairs & Downstairs Bars', reason: 'Depleted during high-volume rush', altSuggestion: 'Don Julio 1942 or Patron Reposado', time: '6:30 PM' }
  ]);
  const [new86Item, setNew86Item] = useState('');
  const [new86Station, setNew86Station] = useState('Main Bar / POS');
  const [new86Reason, setNew86Reason] = useState('');
  const [new86Alt, setNew86Alt] = useState('');

  // ─── 5. Banquet Pre-Event Par Prep Manifest State ───
  const [banquetEvents, setBanquetEvents] = useState([
    {
      id: 'BEO-8841',
      eventName: 'Stehouwer Wedding Gala',
      guests: 220,
      room: 'Grand Ballroom (Bar A & B)',
      package: 'Premium Open Bar & Cellar Reserve',
      pullManifest: [
        { item: "Tito's Vodka (750ml)", qty: 14, status: 'PULLED' },
        { item: 'Casamigos Blanco', qty: 8, status: 'PULLED' },
        { item: 'Sassicaia 2016 Red', qty: 12, status: 'PENDING' },
        { item: 'Peroni Draft Kegs', qty: 2, status: 'PULLED' },
        { item: 'Prosecco Champagne Cases', qty: 4, status: 'PULLED' }
      ]
    }
  ]);

  // ─── 6. Pour Cost & MLCC Shrink Variance State ───
  const [shrinkLogs, setShrinkLogs] = useState([
    { id: 'VAR-01', date: 'Tonight • Aug 19', bottle: 'Grey Goose Vodka', posCount: '33 Drinks ($495)', actualUsed: '2.1 Bottles (~35.7 Drinks)', variance: '-2.7 Drinks (-$40.50)', reason: 'Minor Over-Pouring during 7:30 PM surge', status: 'FLAGGED' },
    { id: 'VAR-02', date: 'Tonight • Aug 19', bottle: '2018 Gaja Barbaresco', posCount: '4 Bottles ($1,240)', actualUsed: '4.0 Bottles', variance: '0.0 (Perfect Match)', reason: 'Decanted in Vault for Table 14', status: 'CLEARED' }
  ]);
  const [breakageItem, setBreakageItem] = useState('');
  const [breakageReason, setBreakageReason] = useState('');

  // ─── 7. Michigan MLCC Distributor Purchase Order State ───
  const [distributorOrders, setDistributorOrders] = useState([
    { distributor: 'RNDC (Republic National Distributing)', items: ["Casamigos Blanco (5 Cases)", "Don Julio 1942 (1 Case)"], estCost: 2840.00 },
    { distributor: 'Southern Glazer\'s Wine & Spirits', items: ["Tito's Vodka (8 Cases)", "Woodford Reserve (3 Cases)"], estCost: 3120.00 },
    { distributor: 'Great Lakes Wine & Spirits', items: ["Sassicaia 2016 (2 Cases)", "Biondi-Santi 2015 (1 Case)"], estCost: 4680.00 },
    { distributor: 'Imperial Beverage', items: ["Peroni Draft Kegs (6 Kegs)"], estCost: 980.00 }
  ]);

  // ─── SQLite Synchronization Engine ───
  const fetchLiveInventory = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${baseUrl}/api/notos/inventory?location=${activeLocation}`);
      if (res.ok) {
        const data = await res.json();
        if (data.items && data.items.length > 0) {
          setInventoryItems(data.items.map(item => ({
            id: item.id,
            location: item.location,
            name: item.name,
            category: item.category,
            parLevel: item.par_level,
            upstairs: item.upstairs,
            downstairs: item.downstairs,
            banquetA: item.banquet_a,
            banquetB: item.banquet_b,
            patio: item.patio,
            cellarBin: item.cellar_bin,
            storeroom: item.storeroom,
            distributor: item.distributor,
            status: item.status
          })));
          if (data.stats) {
            setInventoryStats(data.stats);
          }
        }
      }
    } catch (err) {
      console.warn('[NotoInventory] Using local state fallback:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAuxiliaryData = async () => {
    try {
      const [dispRes, sosRes, eightySixRes] = await Promise.all([
        fetch(`${baseUrl}/api/notos/dispatch?location=${activeLocation}`),
        fetch(`${baseUrl}/api/notos/sos?location=${activeLocation}`),
        fetch(`${baseUrl}/api/notos/86?location=${activeLocation}`)
      ]);
      if (dispRes.ok) {
        const d = await dispRes.json();
        if (d.queue && d.queue.length > 0) {
          setDispatchQueue(d.queue.map(q => ({
            id: q.id,
            targetBar: q.target_bar,
            item: q.item,
            sourceLoc: q.source_loc,
            time: q.time,
            requestedBy: q.requested_by,
            status: q.status
          })));
        }
      }
      if (sosRes.ok) {
        const s = await sosRes.json();
        if (s.calls && s.calls.length > 0) {
          setSosCalls(s.calls.map(c => ({
            id: c.id,
            bar: c.bar,
            type: c.type,
            urgency: c.urgency,
            time: c.time
          })));
        }
      }
      if (eightySixRes.ok) {
        const e = await eightySixRes.json();
        if (e.items && e.items.length > 0) {
          setEightySixBoard(e.items.map(b => ({
            id: b.id,
            item: b.item,
            station: b.station,
            reason: b.reason,
            altSuggestion: b.alt_suggestion,
            time: b.time
          })));
        }
      }
    } catch (e) {
      console.warn('[NotoAux] Using local fallback state:', e);
    }
  };

  useEffect(() => {
    fetchLiveInventory();
    fetchAuxiliaryData();
  }, [activeLocation, baseUrl]);

  // Handlers
  const handleLogGrab = async (itemId, zone) => {
    let updatedVal = '0';
    setInventoryItems(prev => prev.map(item => {
      if (item.id === itemId) {
        const currentQty = parseInt(item[zone]) || 0;
        const nextQty = Math.max(0, currentQty - 1);
        updatedVal = String(nextQty);
        return {
          ...item,
          [zone]: updatedVal
        };
      }
      return item;
    }));

    // Sync to SQLite in background
    try {
      const fieldMap = {
        upstairs: 'upstairs',
        downstairs: 'downstairs',
        banquetA: 'banquet_a',
        banquetB: 'banquet_b',
        patio: 'patio',
        storeroom: 'storeroom'
      };
      await fetch(`${baseUrl}/api/notos/inventory/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: itemId,
          field: fieldMap[zone] || zone,
          value: updatedVal
        })
      });
    } catch (e) {
      console.warn('[NotoUpdate] Failed to persist grab:', e);
    }
  };

  const handleCreateDispatch = async () => {
    if (!newDispatchItem.trim()) return;
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const tempId = `DISP-${Date.now()}`;
    const newEntry = {
      id: tempId,
      targetBar: newDispatchBar,
      item: `${newDispatchQty}x ${newDispatchItem}`,
      sourceLoc: 'Central Storeroom — Rack 2, Shelf B',
      time: nowTime,
      requestedBy: 'Bartender / Kiosk',
      status: 'PENDING'
    };
    setDispatchQueue(prev => [newEntry, ...prev]);
    setNewDispatchItem('');

    try {
      await fetch(`${baseUrl}/api/notos/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_bar: newDispatchBar,
          item: `${newDispatchQty}x ${newDispatchItem}`,
          source_loc: 'Central Storeroom — Rack 2, Shelf B',
          requested_by: 'Bartender / Kiosk',
          location: activeLocation
        })
      });
    } catch (e) {
      console.warn('[NotoDispatch] Offline dispatch cached:', e);
    }
  };

  const handleProgressDispatch = async (id, newStatus) => {
    setDispatchQueue(prev => prev.map(item => item.id === id ? { ...item, status: newStatus } : item));
    try {
      await fetch(`${baseUrl}/api/notos/dispatch/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, status: newStatus })
      });
    } catch (e) {
      console.warn('[NotoDispatch] Offline status updated:', e);
    }
  };

  const handleTriggerSOS = async (type) => {
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const tempId = `SOS-${Date.now()}`;
    const newSOS = {
      id: tempId,
      bar: 'Upstairs Main Bar',
      type: type,
      urgency: 'HIGH',
      time: nowTime
    };
    setSosCalls(prev => [newSOS, ...prev]);

    try {
      await fetch(`${baseUrl}/api/notos/sos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bar: 'Upstairs Main Bar',
          type,
          urgency: 'HIGH',
          location: activeLocation
        })
      });
    } catch (e) {
      console.warn('[NotoSOS] Offline SOS cached:', e);
    }
  };

  const handleClearSOS = async (id) => {
    setSosCalls(prev => prev.filter(s => s.id !== id));
    try {
      await fetch(`${baseUrl}/api/notos/sos/${id}`, { method: 'DELETE' });
    } catch (e) {
      console.warn('[NotoSOS] Offline clear cached:', e);
    }
  };

  const handleAdd86 = async () => {
    if (!new86Item.trim()) return;
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const tempId = `86-${Date.now()}`;
    const newEntry = {
      id: tempId,
      item: new86Item.trim(),
      station: new86Station,
      reason: new86Reason.trim() || 'Sold out during active service rush',
      altSuggestion: new86Alt.trim() || 'Consult Sommelier / Shift Lead',
      time: nowTime
    };
    setEightySixBoard(prev => [newEntry, ...prev]);
    const itemToSubmit = new86Item.trim();
    const reasonToSubmit = new86Reason.trim();
    const altToSubmit = new86Alt.trim();

    setNew86Item('');
    setNew86Reason('');
    setNew86Alt('');

    try {
      await fetch(`${baseUrl}/api/notos/86`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item: itemToSubmit,
          station: new86Station,
          reason: reasonToSubmit || 'Sold out during active service rush',
          alt_suggestion: altToSubmit,
          location: activeLocation
        })
      });
    } catch (e) {
      console.warn('[Noto86] Offline 86 cached:', e);
    }
  };

  const handleResolve86 = async (id) => {
    setEightySixBoard(prev => prev.filter(item => item.id !== id));
    try {
      await fetch(`${baseUrl}/api/notos/86/${id}`, { method: 'DELETE' });
    } catch (e) {
      console.warn('[Noto86] Offline resolve cached:', e);
    }
  };

  const handleAddNewItem = async () => {
    if (!newItemName.trim()) return;
    const newItem = {
      id: `INV-${activeLocation}-${Date.now().toString().slice(-4)}`,
      location: activeLocation,
      name: newItemName.trim(),
      category: newItemCategory,
      parLevel: parseInt(newItemPar) || 6,
      upstairs: '1',
      downstairs: '1',
      banquetA: '0',
      banquetB: '0',
      patio: '0',
      cellarBin: 'N/A',
      storeroom: newItemStoreroom,
      distributor: "Southern Glazer's",
      status: 'FULL'
    };
    setInventoryItems(prev => [newItem, ...prev]);
    setShowAddItemModal(false);
    setNewItemName('');

    try {
      await fetch(`${baseUrl}/api/notos/inventory/item`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          location: activeLocation,
          name: newItem.name,
          category: newItem.category,
          par_level: newItem.parLevel,
          upstairs: '1',
          downstairs: '1',
          banquet_a: '0',
          banquet_b: '0',
          patio: '0',
          cellar_bin: 'N/A',
          storeroom: newItem.storeroom,
          distributor: newItem.distributor,
          status: 'FULL'
        })
      });
    } catch (e) {
      console.warn('[NotoAdd] Offline item cached:', e);
    }
  };

  const filteredInventory = inventoryItems.filter(item => {
    const matchesSearch = 
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.cellarBin && item.cellarBin.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesCategory = selectedCategory === 'ALL' || item.category.toLowerCase().includes(selectedCategory.toLowerCase());
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="noto-bar-container">
      {/* ── Top Header Bar ── */}
      <header className="noto-bar-header">
        <div className="noto-bar-brand">
          <div className="noto-bar-logo-icon">🍸</div>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.3rem', fontFamily: '"Playfair Display", Georgia, serif', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '10px' }}>
              Notō Hospitality OS <span style={{ color: '#ffffff', fontSize: '0.8rem', fontWeight: '600', padding: '2px 8px', borderRadius: '6px', background: 'rgba(159, 18, 57, 0.5)', border: '1px solid rgba(159, 18, 57, 0.8)' }}>{SYSTEM_VERSION}</span>
            </h1>
            <p style={{ margin: 0, fontSize: '0.75rem', color: '#fda4af' }}>
              Live Multi-Bar Inventory, SQLite State & MLCC Distributor Engine
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Refresh Action */}
          <button
            onClick={() => { fetchLiveInventory(); fetchAuxiliaryData(); }}
            title="Sync with SQLite Vault"
            style={{
              backgroundColor: 'rgba(217, 119, 6, 0.15)',
              color: '#f59e0b',
              border: '1px solid rgba(217, 119, 6, 0.4)',
              padding: '8px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              fontWeight: '700'
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            {isLoading ? 'Syncing...' : 'Sync Vault'}
          </button>

          {/* Bar Kiosk Mode Switcher */}
          <button
            onClick={() => setIsKioskMode(!isKioskMode)}
            style={{
              backgroundColor: isKioskMode ? '#e11d48' : 'rgba(217, 119, 6, 0.2)',
              color: '#ffffff',
              border: isKioskMode ? '1px solid #e11d48' : '1px solid #d97706',
              padding: '8px 16px',
              borderRadius: '8px',
              fontWeight: '800',
              fontSize: '0.82rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Zap size={14} color={isKioskMode ? '#ffffff' : '#f59e0b'} />
            {isKioskMode ? '⚡ Kiosk Mode ACTIVE' : '📱 Desktop View'}
          </button>

          {/* Location Toggle */}
          <div style={{ display: 'flex', backgroundColor: '#120205', padding: '4px', borderRadius: '10px', border: '1px solid rgba(159, 18, 57, 0.6)' }}>
            <button
              onClick={() => setActiveLocation('GR')}
              style={{ padding: '6px 14px', borderRadius: '6px', border: 'none', backgroundColor: activeLocation === 'GR' ? '#881337' : 'transparent', color: activeLocation === 'GR' ? '#fff' : '#fda4af', fontWeight: '700', fontSize: '0.8rem', cursor: 'pointer' }}
            >
              🏛️ Grand Rapids ({activeLocation === 'GR' ? inventoryItems.length : 30})
            </button>
            <button
              onClick={() => setActiveLocation('GH')}
              style={{ padding: '6px 14px', borderRadius: '6px', border: 'none', backgroundColor: activeLocation === 'GH' ? '#0284c7' : 'transparent', color: activeLocation === 'GH' ? '#fff' : '#93c5fd', fontWeight: '700', fontSize: '0.8rem', cursor: 'pointer' }}
            >
              🌅 Grand Haven
            </button>
          </div>
        </div>
      </header>

      {/* ── Subsystem Navigation Ribbon ── */}
      <nav className="noto-bar-nav-ribbon">
        {[
          { id: 'stock_matrix', label: `🍸 Multi-Bar Stock (${filteredInventory.length})`, icon: Layers },
          { id: 'dispatch_queue', label: `⚡ Dispatch Queue (${dispatchQueue.length})`, icon: Zap },
          { id: 'bar_sos', label: `🚨 Bar SOS (${sosCalls.length})`, icon: Bell },
          { id: 'banquet_par', label: '💒 Banquet Par Prep', icon: Award },
          { id: 'cellar_gps', label: '🍷 Wine Cellar Bin GPS', icon: MapPin },
          { id: 'board_86', label: `🔴 Live 86'd Board (${eightySixBoard.length})`, icon: ShieldAlert },
          { id: 'pour_shrink', label: '📉 Pour Cost & Shrink', icon: DollarSign },
          { id: 'distributor_po', label: '📦 MLCC Distributor POs', icon: Download }
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeModule === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveModule(tab.id)}
              className={`noto-bar-nav-btn ${isActive ? 'active' : ''}`}
            >
              <Icon size={14} color={isActive ? '#f59e0b' : '#fda4af'} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* ── Main Viewport ── */}
      <main className="noto-bar-main">

        {/* ══════════ 1. MULTI-BAR LIVE STOCK MATRIX ══════════ */}
        {activeModule === 'stock_matrix' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* KPI Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div style={{ background: 'linear-gradient(135deg, rgba(20,4,8,0.9), rgba(136,19,55,0.25))', border: '1px solid rgba(159,18,57,0.5)', borderRadius: '14px', padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: '#fda4af', fontWeight: '700', textTransform: 'uppercase' }}>Total Active SKUs</span>
                <div style={{ fontSize: '1.8rem', fontWeight: '900', color: '#ffffff', marginTop: '4px' }}>{inventoryItems.length}</div>
                <span style={{ fontSize: '0.72rem', color: '#34d399' }}>● SQLite Persistent Vault</span>
              </div>
              <div style={{ background: 'linear-gradient(135deg, rgba(20,4,8,0.9), rgba(217,119,6,0.25))', border: '1px solid rgba(217,119,6,0.5)', borderRadius: '14px', padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: '#fde68a', fontWeight: '700', textTransform: 'uppercase' }}>Low Par Warnings</span>
                <div style={{ fontSize: '1.8rem', fontWeight: '900', color: '#f59e0b', marginTop: '4px' }}>{inventoryStats.low}</div>
                <span style={{ fontSize: '0.72rem', color: '#f59e0b' }}>⚠️ Restock Scheduled</span>
              </div>
              <div style={{ background: 'linear-gradient(135deg, rgba(20,4,8,0.9), rgba(225,29,72,0.25))', border: '1px solid rgba(225,29,72,0.5)', borderRadius: '14px', padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: '#fecdd3', fontWeight: '700', textTransform: 'uppercase' }}>Depleted / Critical</span>
                <div style={{ fontSize: '1.8rem', fontWeight: '900', color: '#f43f5e', marginTop: '4px' }}>{inventoryStats.critical}</div>
                <span style={{ fontSize: '0.72rem', color: '#fb7185' }}>🚨 Immediate Pull Required</span>
              </div>
              <div style={{ background: 'linear-gradient(135deg, rgba(20,4,8,0.9), rgba(16,185,129,0.25))', border: '1px solid rgba(16,185,129,0.5)', borderRadius: '14px', padding: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: '#a7f3d0', fontWeight: '700', textTransform: 'uppercase' }}>Full Par Stocked</span>
                <div style={{ fontSize: '1.8rem', fontWeight: '900', color: '#34d399', marginTop: '4px' }}>{inventoryStats.full}</div>
                <span style={{ fontSize: '0.72rem', color: '#34d399' }}>✓ 100% Service Ready</span>
              </div>
            </div>

            {/* Filter & Search Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                  Live Multi-Bar Stock Matrix ({activeLocation === 'GR' ? 'Grand Rapids — 6600 28th St' : 'Grand Haven Waterfront'})
                </h2>
                <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                  Synchronized across Upstairs Main, Downstairs Lounge, Banquet A/B, Patio, and Walk-In Vault.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <button
                  onClick={() => setShowAddItemModal(true)}
                  style={{
                    backgroundColor: '#881337',
                    color: '#ffffff',
                    border: '1px solid #be123c',
                    padding: '8px 14px',
                    borderRadius: '10px',
                    fontWeight: '700',
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <PlusCircle size={15} /> Add Custom SKU
                </button>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'rgba(20, 4, 8, 0.9)', padding: '8px 14px', borderRadius: '10px', border: '1px solid rgba(159, 18, 57, 0.5)' }}>
                  <Search size={16} color="#fda4af" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search Vodka, Bourbon, Bin..."
                    style={{ background: 'transparent', border: 'none', color: '#fef3c7', fontSize: '0.85rem', outline: 'none', width: '200px' }}
                  />
                </div>
              </div>
            </div>

            {/* Category Ribbon */}
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
              {['ALL', 'Vodka', 'Tequila', 'Whiskey', 'Scotch', 'Fine Wine', 'Draft Beer', 'Liqueurs', 'Provisions'].map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  style={{
                    backgroundColor: selectedCategory === cat ? 'rgba(217, 119, 6, 0.25)' : 'rgba(20, 4, 8, 0.6)',
                    color: selectedCategory === cat ? '#f59e0b' : '#fda4af',
                    border: selectedCategory === cat ? '1px solid #f59e0b' : '1px solid rgba(159, 18, 57, 0.3)',
                    padding: '4px 12px',
                    borderRadius: '8px',
                    fontSize: '0.78rem',
                    fontWeight: selectedCategory === cat ? '800' : '600',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {cat === 'ALL' ? '🍾 All Categories' : cat}
                </button>
              ))}
            </div>

            {/* Matrix Table */}
            <div style={{ backgroundColor: 'rgba(20, 4, 8, 0.95)', border: '1px solid rgba(159, 18, 57, 0.4)', borderRadius: '16px', overflow: 'hidden', minHeight: '480px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ backgroundColor: 'rgba(136, 19, 55, 0.3)', borderBottom: '1px solid rgba(159, 18, 57, 0.5)', color: '#f59e0b', fontSize: '0.78rem', textTransform: 'uppercase' }}>
                    <th style={{ padding: '14px 18px' }}>Liquor / Vintage</th>
                    <th style={{ padding: '14px 12px' }}>Upstairs Main</th>
                    <th style={{ padding: '14px 12px' }}>Downstairs Lounge</th>
                    <th style={{ padding: '14px 12px' }}>Banquet Bar A</th>
                    <th style={{ padding: '14px 12px' }}>Banquet Bar B</th>
                    <th style={{ padding: '14px 12px' }}>Patio Deck</th>
                    <th style={{ padding: '14px 12px' }}>Storeroom Reserve</th>
                    <th style={{ padding: '14px 18px', textAlign: 'center' }}>Quick Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInventory.map(item => (
                    <tr key={item.id} style={{ borderBottom: '1px solid rgba(159, 18, 57, 0.2)', backgroundColor: item.status === 'CRITICAL' ? 'rgba(225, 29, 72, 0.08)' : item.status === 'LOW' ? 'rgba(245, 158, 11, 0.05)' : 'transparent' }}>
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '0.72rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.06)', color: '#fda4af' }}>{item.id}</span>
                          <strong style={{ color: '#ffffff', fontSize: '0.92rem' }}>{item.name}</strong>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#fda4af', display: 'block', marginTop: '2px' }}>
                          {item.category} • Par: {item.parLevel} • {item.distributor}
                        </span>
                      </td>
                      <td style={{ padding: '14px 12px' }}>
                        <span className={`stock-pill ${item.upstairs === '0' || item.upstairs === 0 ? 'out' : parseInt(item.upstairs) <= 1 ? 'low' : 'full'}`}>
                          {item.upstairs} {(item.upstairs === '0' || item.upstairs === 0) ? '(OUT)' : ''}
                        </span>
                      </td>
                      <td style={{ padding: '14px 12px' }}>
                        <span className={`stock-pill ${item.downstairs === '0' || item.downstairs === 0 ? 'out' : parseInt(item.downstairs) <= 1 ? 'low' : 'full'}`}>
                          {item.downstairs}
                        </span>
                      </td>
                      <td style={{ padding: '14px 12px' }}>
                        <span className={`stock-pill ${item.banquetA === '0' || item.banquetA === 0 ? 'out' : parseInt(item.banquetA) <= 1 ? 'low' : 'full'}`}>
                          {item.banquetA}
                        </span>
                      </td>
                      <td style={{ padding: '14px 12px' }}>
                        <span className={`stock-pill ${item.banquetB === '0' || item.banquetB === 0 ? 'out' : parseInt(item.banquetB) <= 1 ? 'low' : 'full'}`}>
                          {item.banquetB}
                        </span>
                      </td>
                      <td style={{ padding: '14px 12px' }}>
                        <span className={`stock-pill ${item.patio === '0' || item.patio === 0 ? 'out' : 'full'}`}>
                          {item.patio}
                        </span>
                      </td>
                      <td style={{ padding: '14px 12px', color: '#34d399', fontWeight: '700' }}>
                        📍 {item.storeroom}
                      </td>
                      <td style={{ padding: '14px 18px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                          <button
                            onClick={() => handleLogGrab(item.id, 'upstairs')}
                            className="kiosk-touch-btn"
                            title="Log bottle grab for Upstairs Well"
                            style={{ backgroundColor: 'rgba(217, 119, 6, 0.2)', color: '#f59e0b', border: '1px solid #d97706', padding: '6px 10px', minHeight: '32px', fontSize: '0.75rem' }}
                          >
                            -1 Well
                          </button>
                          <button
                            onClick={() => {
                              setNewDispatchBar('Upstairs Main Bar');
                              setNewDispatchItem(item.name);
                              setActiveModule('dispatch_queue');
                            }}
                            title="Dispatch barback to restock this SKU"
                            style={{ backgroundColor: 'rgba(14, 165, 233, 0.2)', color: '#38bdf8', border: '1px solid #0284c7', padding: '6px 10px', minHeight: '32px', fontSize: '0.75rem', borderRadius: '8px', cursor: 'pointer' }}
                          >
                            ⚡ Restock
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ══════════ ADD NEW SKU MODAL ══════════ */}
        {showAddItemModal && (
          <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, backdropFilter: 'blur(4px)' }}>
            <div style={{ width: '480px', backgroundColor: '#190408', border: '1px solid #f59e0b', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, color: '#f59e0b', fontSize: '1.2rem', fontFamily: 'serif' }}>➕ Add New Stock SKU to SQLite Vault</h3>
                <button onClick={() => setShowAddItemModal(false)} style={{ background: 'transparent', border: 'none', color: '#fda4af', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: '#fda4af', display: 'block', marginBottom: '4px' }}>Item Name / Bottle Description</label>
                <input
                  type="text"
                  value={newItemName}
                  onChange={e => setNewItemName(e.target.value)}
                  placeholder="e.g. Clase Azul Reposado (750ml)"
                  style={{ width: '100%', backgroundColor: '#120205', border: '1px solid rgba(159,18,57,0.6)', padding: '10px', borderRadius: '8px', color: '#fff', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.78rem', color: '#fda4af', display: 'block', marginBottom: '4px' }}>Category</label>
                  <select
                    value={newItemCategory}
                    onChange={e => setNewItemCategory(e.target.value)}
                    style={{ width: '100%', backgroundColor: '#120205', border: '1px solid rgba(159,18,57,0.6)', padding: '10px', borderRadius: '8px', color: '#fff', fontSize: '0.85rem' }}
                  >
                    <option>Spirits (Vodka)</option>
                    <option>Spirits (Tequila)</option>
                    <option>Spirits (Whiskey)</option>
                    <option>Scotch Single Malt</option>
                    <option>Fine Wine (Tuscany)</option>
                    <option>Fine Wine (Piedmont)</option>
                    <option>Draft Beer</option>
                    <option>Liqueurs & Cordials</option>
                    <option>Mixers & Provisions</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.78rem', color: '#fda4af', display: 'block', marginBottom: '4px' }}>Par Level</label>
                  <input
                    type="number"
                    value={newItemPar}
                    onChange={e => setNewItemPar(e.target.value)}
                    style={{ width: '100%', backgroundColor: '#120205', border: '1px solid rgba(159,18,57,0.6)', padding: '10px', borderRadius: '8px', color: '#fff', fontSize: '0.85rem' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: '#fda4af', display: 'block', marginBottom: '4px' }}>Storeroom Location / Bin</label>
                <input
                  type="text"
                  value={newItemStoreroom}
                  onChange={e => setNewItemStoreroom(e.target.value)}
                  placeholder="e.g. Rack 1, Shelf B (Cage)"
                  style={{ width: '100%', backgroundColor: '#120205', border: '1px solid rgba(159,18,57,0.6)', padding: '10px', borderRadius: '8px', color: '#fff', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button
                  onClick={() => setShowAddItemModal(false)}
                  style={{ padding: '8px 16px', background: 'transparent', border: '1px solid rgba(159,18,57,0.5)', color: '#fda4af', borderRadius: '8px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddNewItem}
                  style={{ padding: '8px 18px', background: '#d97706', border: 'none', color: '#000', fontWeight: '800', borderRadius: '8px', cursor: 'pointer' }}
                >
                  Save to Database
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ══════════ 2. BARBACK DISPATCH QUEUE ══════════ */}
        {activeModule === 'dispatch_queue' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                  ⚡ Smart Barback Dispatch Queue
                </h2>
                <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                  1-Tap restocking tickets with calculated nearest storeroom coordinates.
                </p>
              </div>

              {/* Quick Create Dispatch */}
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', backgroundColor: 'rgba(20, 4, 8, 0.9)', padding: '10px 16px', borderRadius: '12px', border: '1px solid rgba(159, 18, 57, 0.5)' }}>
                <select
                  value={newDispatchBar}
                  onChange={e => setNewDispatchBar(e.target.value)}
                  style={{ backgroundColor: '#120205', border: '1px solid rgba(159, 18, 57, 0.6)', color: '#fef3c7', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', outline: 'none' }}
                >
                  <option>Upstairs Main Bar</option>
                  <option>Downstairs Lounge</option>
                  <option>Banquet Bar A</option>
                  <option>Banquet Bar B</option>
                  <option>Patio Bar</option>
                </select>

                <input
                  type="text"
                  value={newDispatchItem}
                  onChange={e => setNewDispatchItem(e.target.value)}
                  placeholder="Item needed (e.g. Tito's Vodka)..."
                  style={{ backgroundColor: '#120205', border: '1px solid rgba(159, 18, 57, 0.6)', color: '#fef3c7', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', outline: 'none' }}
                />

                <button
                  onClick={handleCreateDispatch}
                  style={{ backgroundColor: '#d97706', color: '#000', border: 'none', padding: '6px 14px', borderRadius: '6px', fontWeight: '800', fontSize: '0.8rem', cursor: 'pointer' }}
                >
                  🚨 Dispatch Ticket
                </button>
              </div>
            </div>

            {/* Queue List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {dispatchQueue.map(item => (
                <div key={item.id} style={{ backgroundColor: 'rgba(20, 4, 8, 0.95)', border: '1px solid rgba(159, 18, 57, 0.5)', borderLeft: `6px solid ${item.status === 'PENDING' ? '#e11d48' : item.status === 'EN_ROUTE' ? '#f59e0b' : '#10b981'}`, borderRadius: '14px', padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: '800', backgroundColor: 'rgba(217, 119, 6, 0.2)', color: '#f59e0b', padding: '2px 8px', borderRadius: '6px' }}>
                        {item.id} • {item.time}
                      </span>
                      <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#ffffff' }}>{item.targetBar}</h3>
                    </div>
                    <p style={{ margin: '0 0 4px 0', fontSize: '1.05rem', fontWeight: '700', color: '#f59e0b' }}>
                      📦 Needed: {item.item}
                    </p>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: '#34d399' }}>
                      📍 <strong>Pickup Coordinates:</strong> {item.sourceLoc}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    {item.status === 'PENDING' && (
                      <button
                        onClick={() => handleProgressDispatch(item.id, 'EN_ROUTE')}
                        className="kiosk-touch-btn"
                        style={{ backgroundColor: '#d97706', color: '#000000', border: 'none' }}
                      >
                        🚚 Claim & En Route
                      </button>
                    )}
                    {item.status === 'EN_ROUTE' && (
                      <button
                        onClick={() => handleProgressDispatch(item.id, 'DELIVERED')}
                        className="kiosk-touch-btn"
                        style={{ backgroundColor: '#10b981', color: '#ffffff', border: 'none' }}
                      >
                        ✓ Mark Stocked & Delivered
                      </button>
                    )}
                    {item.status === 'DELIVERED' && (
                      <span style={{ color: '#34d399', fontWeight: '800', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle size={18} /> Stocked
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════ 3. BAR SOS RAPID RUNNER SYSTEM ══════════ */}
        {activeModule === 'bar_sos' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                🚨 "Bar SOS" Silent Rapid Runner Callouts
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                1-Tap mobile alerts for Ice, Glass Racks, Garnishes, and CO2 Keg Blowouts.
              </p>
            </div>

            {/* Quick Trigger Bar */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <button onClick={() => handleTriggerSOS('🧊 Need Ice Bin Refill')} className="kiosk-touch-btn" style={{ backgroundColor: 'rgba(2, 132, 199, 0.25)', color: '#38bdf8', border: '1px solid #0284c7' }}>
                🧊 Need Ice Refill
              </button>
              <button onClick={() => handleTriggerSOS('🍸 Need Clean Rocks / Martini Glasses')} className="kiosk-touch-btn" style={{ backgroundColor: 'rgba(168, 85, 247, 0.25)', color: '#c084fc', border: '1px solid #a855f7' }}>
                🍸 Need Glass Racks
              </button>
              <button onClick={() => handleTriggerSOS('🍋 Need Sliced Lemons & Limes')} className="kiosk-touch-btn" style={{ backgroundColor: 'rgba(234, 179, 8, 0.25)', color: '#fde047', border: '1px solid #eab308' }}>
                🍋 Need Garnishes
              </button>
              <button onClick={() => handleTriggerSOS('🍺 Keg Blowout / CO2 Tank Swap')} className="kiosk-touch-btn" style={{ backgroundColor: 'rgba(225, 29, 72, 0.25)', color: '#fb7185', border: '1px solid #e11d48' }}>
                🍺 Keg / CO2 Blowout
              </button>
            </div>

            {/* Active SOS Alerts */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <h3 style={{ margin: '10px 0 0 0', fontSize: '1.1rem', color: '#ffffff' }}>Active SOS Runner Tickets</h3>
              {sosCalls.map(sos => (
                <div key={sos.id} style={{ backgroundColor: 'rgba(225, 29, 72, 0.15)', border: '1px solid rgba(225, 29, 72, 0.6)', borderRadius: '12px', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ backgroundColor: '#e11d48', color: '#ffffff', fontSize: '0.72rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>
                        URGENT {sos.urgency}
                      </span>
                      <h4 style={{ margin: 0, fontSize: '1.15rem', color: '#ffffff' }}>{sos.bar}</h4>
                      <span style={{ fontSize: '0.78rem', color: '#fda4af' }}>({sos.time})</span>
                    </div>
                    <p style={{ margin: '4px 0 0 0', fontSize: '1.05rem', fontWeight: '800', color: '#fef3c7' }}>
                      {sos.type}
                    </p>
                  </div>

                  <button
                    onClick={() => handleClearSOS(sos.id)}
                    style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid #10b981', padding: '8px 16px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: '800', cursor: 'pointer' }}
                  >
                    ✓ Handled / Clear SOS
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════ 4. BANQUET PRE-EVENT PAR PREP ══════════ */}
        {activeModule === 'banquet_par' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                💒 Banquet Pre-Event "Par Prep" & Auto-Pull Manifest
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                Automatically computes required pre-event staging from active BEO banquet contracts.
              </p>
            </div>

            {banquetEvents.map(event => (
              <div key={event.id} style={{ backgroundColor: 'rgba(20, 4, 8, 0.95)', border: '1px solid rgba(159, 18, 57, 0.4)', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span style={{ backgroundColor: 'rgba(217, 119, 6, 0.2)', color: '#f59e0b', padding: '2px 8px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '800' }}>
                      {event.id} • {event.room}
                    </span>
                    <h3 style={{ margin: '6px 0 2px 0', fontSize: '1.3rem', color: '#ffffff', fontFamily: 'serif' }}>{event.eventName}</h3>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: '#fda4af' }}>👥 {event.guests} Guaranteed Guests • Bar Tier: <strong>{event.package}</strong></p>
                  </div>

                  <button className="kiosk-touch-btn" style={{ backgroundColor: '#d97706', color: '#000000', border: 'none', fontSize: '0.82rem' }}>
                    📥 Print Pre-Event Pull Sheet
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                  {event.pullManifest.map((m, idx) => (
                    <div key={idx} style={{ backgroundColor: 'rgba(0,0,0,0.4)', border: '1px solid rgba(159, 18, 57, 0.3)', padding: '12px 16px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <strong style={{ color: '#ffffff', display: 'block', fontSize: '0.9rem' }}>{m.item}</strong>
                        <span style={{ fontSize: '0.78rem', color: '#f59e0b' }}>Pre-Stage: {m.qty} Units</span>
                      </div>
                      <span className={`stock-pill ${m.status === 'PULLED' ? 'full' : 'low'}`}>
                        {m.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ══════════ 5. WINE CELLAR BIN GPS ══════════ */}
        {activeModule === 'cellar_gps' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                🍷 Visual Wine Cellar & Bottle GPS (Bin Finder)
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                Instant physical vault coordinates for servers to locate rare vintages in under 20 seconds.
              </p>
            </div>

            <div className="cellar-map-grid">
              {[
                { bin: 'Bin A-14-3', title: 'Vault North • Top Shelf', wine: '2016 Sassicaia (18 bot)' },
                { bin: 'Bin B-08-1', title: 'Vault North • Mid Shelf', wine: '2015 Biondi-Santi (12 bot)' },
                { bin: 'Bin P-04-2', title: 'Aisle 2 • Piedmont', wine: '2018 Gaja Barbaresco (24 bot)' },
                { bin: 'Bin V-01-4', title: 'Vault South • Reserve', wine: '2017 Quintarelli Amarone (8 bot)' }
              ].map((box, bIdx) => (
                <div key={bIdx} className="cellar-bin-box active-match">
                  <span style={{ fontSize: '0.72rem', color: '#f59e0b', fontWeight: '800' }}>📍 {box.bin}</span>
                  <strong style={{ color: '#ffffff', fontSize: '0.95rem' }}>{box.title}</strong>
                  <span style={{ fontSize: '0.8rem', color: '#fda4af' }}>{box.wine}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════ 6. LIVE 86'D BOARD ══════════ */}
        {activeModule === 'board_86' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                🔴 Live 86'd Board & POS Interceptor
              </h2>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                Broadcasts depleted food & beverage items to prevent awkward table re-orders.
              </p>
            </div>

            <div style={{ backgroundColor: 'rgba(25, 4, 8, 0.9)', padding: '18px 24px', borderRadius: '14px', border: '1px solid rgba(225, 29, 72, 0.5)', display: 'flex', gap: '12px', alignItems: 'center' }}>
              <input
                type="text"
                value={new86Item}
                onChange={e => setNew86Item(e.target.value)}
                placeholder="Item to 86 (e.g. Casamigos Añejo)..."
                style={{ backgroundColor: '#120205', border: '1px solid rgba(159, 18, 57, 0.6)', borderRadius: '8px', padding: '10px 14px', color: '#fef3c7', fontSize: '0.88rem', outline: 'none', flex: 1 }}
              />
              <input
                type="text"
                value={new86Alt}
                onChange={e => setNew86Alt(e.target.value)}
                placeholder="Alternative Suggestion..."
                style={{ backgroundColor: '#120205', border: '1px solid rgba(159, 18, 57, 0.6)', borderRadius: '8px', padding: '10px 14px', color: '#fef3c7', fontSize: '0.88rem', outline: 'none', flex: 1 }}
              />
              <button onClick={handleAdd86} style={{ backgroundColor: '#e11d48', color: '#ffffff', border: 'none', padding: '10px 20px', borderRadius: '8px', fontWeight: '800', cursor: 'pointer' }}>
                🚨 Broadcast 86
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {eightySixBoard.map(item => (
                <div key={item.id} style={{ backgroundColor: 'rgba(225, 29, 72, 0.12)', border: '1px solid rgba(225, 29, 72, 0.5)', borderRadius: '12px', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ backgroundColor: '#e11d48', color: '#ffffff', fontSize: '0.72rem', fontWeight: '800', padding: '2px 8px', borderRadius: '6px' }}>86'D ACTIVE</span>
                      <h4 style={{ margin: 0, fontSize: '1.15rem', color: '#ffffff' }}>{item.item}</h4>
                    </div>
                    <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#fecdd3' }}>
                      {item.reason} • 💡 <strong>Suggest:</strong> {item.altSuggestion}
                    </p>
                  </div>
                  <button onClick={() => handleResolve86(item.id)} style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid #10b981', padding: '6px 14px', borderRadius: '8px', fontSize: '0.78rem', fontWeight: '700', cursor: 'pointer' }}>
                    ✓ Restock / Clear
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════ 7. MLCC DISTRIBUTOR POS ══════════ */}
        {activeModule === 'distributor_po' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ margin: '0 0 4px 0', fontSize: '1.5rem', fontFamily: '"Playfair Display", serif', color: '#f59e0b' }}>
                  📦 Michigan MLCC & Distributor 1-Click Purchase Orders
                </h2>
                <p style={{ margin: 0, fontSize: '0.82rem', color: '#fda4af' }}>
                  Automatically compiles weekly orders for RNDC, Southern Glazer's, Great Lakes, and Imperial Beverage.
                </p>
              </div>
              <button className="kiosk-touch-btn" style={{ backgroundColor: '#34d399', color: '#000000', border: 'none' }}>
                📥 Download All Orders (.docx / .csv)
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
              {distributorOrders.map((po, idx) => (
                <div key={idx} style={{ backgroundColor: 'rgba(20, 4, 8, 0.95)', border: '1px solid rgba(159, 18, 57, 0.4)', borderRadius: '14px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h4 style={{ margin: 0, fontSize: '1.1rem', color: '#ffffff', fontFamily: 'serif' }}>{po.distributor}</h4>
                    <span style={{ fontSize: '1.1rem', fontWeight: '800', color: '#f59e0b' }}>${po.estCost.toFixed(2)}</span>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#fda4af' }}>
                    {po.items.map((it, i) => (
                      <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>• {it}</div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
