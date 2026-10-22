import React, { useState } from 'react';

export default function NocoSpatialCampusMap() {
  const [selectedZone, setSelectedZone] = useState('zone0');
  const [activeOverlay, setActiveOverlay] = useState('all'); // 'none', 'audio', 'power', 'water', 'all'
  const [searchQuery, setSearchQuery] = useState('');
  const [mapZoom, setMapZoom] = useState(1);

  // Campus Zones Definition
  const zones = {
    zone0: {
      id: 'zone0',
      name: 'Zone 0 (The Core): "The Living Stage" Amphitheater',
      category: 'Performance',
      size: '3,000 sq ft base | 150-1,500 Capacity',
      powerDraw: '21.0 kW Peak',
      audioRating: 'STC 68 / 105 dB Max SPL',
      waterUse: '450 Gal/day (Misting & Root Wash)',
      occupancy: '150 seated / 350 lawn festival',
      status: 'Ready for Show',
      color: '#00FFFF',
      details: 'Central bio-morphic concrete sound shell with parabolic acoustic geometry. Features root-roof vine lattice (Hops/Wisteria) providing organic solar shading and eliminating slap-back flutter echo. Houses the cardioid subwoofer array and motorized smart glass acoustic baffles.'
    },
    greenhouse: {
      id: 'greenhouse',
      name: 'The Polycarbonate Living Stage Greenhouse',
      category: 'Agricultural & Performance',
      size: '4,000 sq ft | Twin-Wall Polycarbonate',
      powerDraw: '12.5 kW Continuous',
      audioRating: 'STC 45 (6° Glazing Tilt)',
      waterUse: '1,200 Gal/day (Recirculating NFT)',
      occupancy: '120 Assembly / 9,600 crop heads',
      status: 'Active Harvest & Staging',
      color: '#10B981',
      details: 'Dual-purpose agricultural greenhouse and intimate concert hall. Features 18 vertical aeroponic towers and hanging herb walls serving as living stage backdrops. LED grow spectrum seamlessly transitions into 2700K theatrical performance wash.'
    },
    zone1: {
      id: 'zone1',
      name: 'Zone 1 (Inner Ring): "The Green Rooms"',
      category: 'Artist Facilities',
      size: '1,800 sq ft (4 Prep Suites)',
      powerDraw: '4.8 kW',
      audioRating: 'STC 60 (Sound-Locked)',
      waterUse: '250 Gal/day',
      occupancy: '20 Artists & Production Crew',
      status: 'Occupied (Resident Artists)',
      color: '#38BDF8',
      details: 'High-yield vertical nursery prep suites offering farm-to-artist nourishment. Sound-isolated dressing quarters, vocal warm-up booths, and private showers fed by geothermal hot water.'
    },
    zone2: {
      id: 'zone2',
      name: 'Zone 2 (Residential Halo): Connected Tech-Earthships',
      category: 'Residential',
      size: '6 Living Quarters (1,200 sq ft each)',
      powerDraw: '16.8 kW Combined',
      audioRating: 'STC 72 (Rammed Earth Thermal Wall)',
      waterUse: '800 Gal/day (Rainwater Harvest)',
      occupancy: '18 Permanent Residents / Family',
      status: 'Nominal HVAC & Solar Buffering',
      color: '#818CF8',
      details: 'Continuous rammed-earth north walls acting as an acoustic barrier shielding neighboring properties. South-facing electrochromic smart glass looks inward toward the central courtyard fire pit and amphitheater.'
    },
    ood_pods: {
      id: 'ood_pods',
      name: '8 ÖÖD Mirror Cottages & Artist Residency Pods',
      category: 'Residency',
      size: '8 Individual Pods (280 sq ft each)',
      powerDraw: '9.6 kW Total (1.2 kW/pod)',
      audioRating: 'STC 55 (Double Glazed Mirror Facade)',
      waterUse: '320 Gal/day (Composting Toilets)',
      occupancy: '8-16 Visiting Artists / Fellows',
      status: '6/8 Units Reserved',
      color: '#C084FC',
      details: 'Mirrored glass architectural pods embedded inside the pine and fir canopy. Reflects the natural forest environment while maintaining zero external visibility into private creative workspaces. Powered by shared 2-ton geothermal heat pumps.'
    },
    zone3: {
      id: 'zone3',
      name: 'Zone 3 (Agro-Shield): Biomass & Fir Perimeter',
      category: 'Buffer & Agriculture',
      size: '14 Acres (Perimeter Ring)',
      powerDraw: '1.2 kW (Irrigation & Smart Fencing)',
      audioRating: 'Natural -18 dB Foliage Attenuation',
      waterUse: 'Drip Catchment Reservoir',
      occupancy: 'Bio-reserve & Nature Trails',
      status: 'Healthy Canopy & Carbon Sink',
      color: '#059669',
      details: 'Dense perimeter of mature Fraser Fir, Scotch Pine, Timber Bamboo, and industrial hemp. Forms a multi-layered acoustic and visual buffer isolating the enclave from surrounding Finger Lakes rural roads.'
    },
    livestock: {
      id: 'livestock',
      name: 'Livestock Sector: Valais Sheep & Vicuña Alpacas',
      category: 'Agriculture & Livestock',
      size: '2.5 Acres Pasture | 2,000 sq ft Barns',
      powerDraw: '3.5 kW (Radiant Floors & Trough Heaters)',
      audioRating: 'Acoustic Sound Buffer (-12 dB)',
      waterUse: '600 Gal/day',
      occupancy: '15 Valais Ewes, 6 Alpacas, 30 Poultry',
      status: 'Grazing in Western Pasture',
      color: '#F59E0B',
      details: 'Timber-frame barns with heated floors for lambing. Sheep and alpacas provide high-value luxury fleece ($45/lb wool, $450/kg fiber). Free-range poultry provides biological pest control (ticks/insects) across public lawn areas.'
    },
    foh_tower: {
      id: 'foh_tower',
      name: 'Front of House (FOH) Tower & Concessions',
      category: 'Production Control',
      size: '3 Stories | 2,400 sq ft footprint',
      powerDraw: '6.5 kW Peak',
      audioRating: 'Calibrated Mix Position (85 dBA)',
      waterUse: '300 Gal/day',
      occupancy: '5 Tech Crew / 35 VIP Deck',
      status: 'FOH Audio & Lighting Online',
      color: '#EAB308',
      details: 'Level 1: Farm Concessions distributing fresh harvest from The MELT. Level 2: Master Audio/Lighting/Video control room. Level 3: Crow’s Nest VIP viewing deck overlooking the amphitheater and Finger Lakes hills.'
    },
    courtyard: {
      id: 'courtyard',
      name: 'Central Courtyard & Concentric Fire Pit',
      category: 'Communal',
      size: '5,000 sq ft Plaza',
      powerDraw: '0.8 kW (Ambient Pathway LEDs)',
      audioRating: 'Natural Ambient Diffusion',
      waterUse: 'Reflecting Pool Circulation',
      occupancy: '200 Gathering / Mingling',
      status: 'Fire Ring Prepared & Lit at Dusk',
      color: '#F97316',
      details: 'Concentric natural stone fire rings surrounded by reflecting pools. Serves as the community heart where audience, artists, and farmers gather for post-show dialogue and farm dinners.'
    }
  };

  const activeZoneData = zones[selectedZone] || zones.zone0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', color: '#f8fafc' }}>
      
      {/* Top Controls Bar */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.85)',
        border: '1px solid rgba(0, 255, 255, 0.25)',
        borderRadius: '12px',
        padding: '16px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.4rem' }}>🗺️</span>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#00FFFF', fontWeight: 800 }}>
              23-Acre Master Campus & Spatial Vector Map
            </h3>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Ithaca, NY &bull; Finger Lakes Living Stage & Agro-Acoustic Enclave
            </span>
          </div>
        </div>

        {/* Overlay Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>Active Overlays:</span>
          {[
            { id: 'all', label: '🌐 All Systems' },
            { id: 'audio', label: '🔊 Audio SPL Heatmap' },
            { id: 'power', label: '⚡ Microgrid Conduits' },
            { id: 'water', label: '💧 Closed-Loop Water' }
          ].map(ov => (
            <button
              key={ov.id}
              onClick={() => setActiveOverlay(ov.id)}
              style={{
                background: activeOverlay === ov.id ? 'rgba(0, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                border: activeOverlay === ov.id ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
                color: activeOverlay === ov.id ? '#00FFFF' : '#94a3b8',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {ov.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Map Canvas + Inspector Drawer */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(450px, 1.8fr) minmax(320px, 1fr)', gap: '20px' }}>
        
        {/* Interactive SVG Campus Map */}
        <div style={{
          background: 'radial-gradient(circle at 50% 50%, #0d1527 0%, #030712 100%)',
          border: '1px solid rgba(0, 255, 255, 0.2)',
          borderRadius: '12px',
          padding: '20px',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: 'inset 0 0 50px rgba(0,0,0,0.8)'
        }}>
          {/* Map Compass & Legend */}
          <div style={{
            position: 'absolute',
            top: '25px',
            left: '25px',
            background: 'rgba(3, 7, 18, 0.85)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '0.75rem',
            color: '#94a3b8',
            pointerEvents: 'none',
            zIndex: 10
          }}>
            <div style={{ fontWeight: 800, color: '#00FFFF' }}>▲ NORTH (Lammerson Lane)</div>
            <div>Scale: 1 in = 150 ft &bull; 23 Acres</div>
          </div>

          {/* SVG Vector Drawing */}
          <svg viewBox="0 0 800 650" style={{ width: '100%', height: 'auto', display: 'block' }}>
            <defs>
              {/* Radial Gradients for Audio Coverage */}
              <radialGradient id="audioGlow" cx="50%" cy="40%" r="55%">
                <stop offset="0%" stopColor="#ef4444" stopOpacity="0.45" />
                <stop offset="35%" stopColor="#f59e0b" stopOpacity="0.30" />
                <stop offset="65%" stopColor="#10b981" stopOpacity="0.15" />
                <stop offset="100%" stopColor="#00ffff" stopOpacity="0.0" />
              </radialGradient>

              {/* Pattern for Biomass Tree Perimeter */}
              <pattern id="treePattern" width="20" height="20" patternUnits="userSpaceOnUse">
                <circle cx="10" cy="10" r="3" fill="#047857" opacity="0.35" />
                <circle cx="5" cy="5" r="2" fill="#065f46" opacity="0.25" />
              </pattern>
            </defs>

            {/* 1. Property Boundary & Topographic Grid */}
            <rect x="20" y="20" width="760" height="610" rx="16" fill="#06101e" stroke="#1e293b" strokeWidth="2" />
            
            {/* Topography Contour Lines */}
            <path d="M 30,120 Q 200,80 400,100 T 770,90" fill="none" stroke="#132338" strokeWidth="1.5" strokeDasharray="4 4" />
            <path d="M 30,220 Q 250,180 450,210 T 770,190" fill="none" stroke="#132338" strokeWidth="1.5" strokeDasharray="4 4" />
            <path d="M 30,340 Q 220,300 420,330 T 770,310" fill="none" stroke="#132338" strokeWidth="1.5" strokeDasharray="4 4" />
            <path d="M 30,460 Q 240,420 440,450 T 770,430" fill="none" stroke="#132338" strokeWidth="1.5" strokeDasharray="4 4" />

            {/* 2. Zone 3 Agro-Shield Perimeter (Fir Grove & Bamboo) */}
            <rect x="25" y="25" width="750" height="600" rx="14" fill="url(#treePattern)" stroke="#065f46" strokeWidth="1" opacity="0.6" />
            <text x="40" y="60" fill="#059669" fontSize="11" fontWeight="700">ZONE 3: AGRO-SHIELD BIOMASS & FIR GROVE (14 ACRES)</text>

            {/* 3. Audio SPL Heatmap Overlay */}
            {(activeOverlay === 'all' || activeOverlay === 'audio') && (
              <g opacity="0.85">
                <circle cx="400" cy="270" r="240" fill="url(#audioGlow)" />
                {/* Acoustic Attenuation Rings */}
                <circle cx="400" cy="270" r="80" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.6" />
                <text x="460" y="260" fill="#f87171" fontSize="9" fontWeight="600">105 dB</text>
                
                <circle cx="400" cy="270" r="150" fill="none" stroke="#f59e0b" strokeWidth="1.2" strokeDasharray="4 4" opacity="0.6" />
                <text x="525" y="260" fill="#fbbf24" fontSize="9" fontWeight="600">85 dB (FOH)</text>
                
                <circle cx="400" cy="270" r="230" fill="none" stroke="#10b981" strokeWidth="1" strokeDasharray="4 4" opacity="0.5" />
                <text x="600" y="260" fill="#34d399" fontSize="9" fontWeight="600">55 dB (Sound-Lock)</text>
              </g>
            )}

            {/* 4. Microgrid Underground Power Lines */}
            {(activeOverlay === 'all' || activeOverlay === 'power') && (
              <g stroke="#00ffff" strokeWidth="1.8" strokeDasharray="6 4" opacity="0.7">
                {/* Power lines connecting Solar to BESS to Living Stage & Pods */}
                <path d="M 620,110 L 400,270 L 400,430 L 190,440" fill="none" />
                <path d="M 400,270 L 220,240 L 160,180" fill="none" />
                <path d="M 400,270 L 580,270 L 640,380" fill="none" />
              </g>
            )}

            {/* 5. Hydrology & Closed-Loop Water Conduits */}
            {(activeOverlay === 'all' || activeOverlay === 'water') && (
              <g stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.65">
                <path d="M 640,380 L 580,270 L 400,270 L 400,340" fill="none" />
                <path d="M 400,340 L 400,430" fill="none" />
              </g>
            )}

            {/* 6. Lammerson Lane Curved Entrance & Roadway */}
            <path d="M 370,25 C 370,80 340,110 300,140 C 260,170 230,210 230,270" fill="none" stroke="#475569" strokeWidth="10" strokeLinecap="round" />
            <path d="M 370,25 C 370,80 340,110 300,140 C 260,170 230,210 230,270" fill="none" stroke="#cbd5e1" strokeWidth="1.5" strokeDasharray="5 5" />
            <text x="385" y="45" fill="#94a3b8" fontSize="10" fontWeight="600">Lammerson Lane Entry</text>

            {/* 7. Livestock Pasture & Barns (Western Sector) */}
            <g onClick={() => setSelectedZone('livestock')} style={{ cursor: 'pointer' }}>
              <rect x="70" y="140" width="150" height="220" rx="10" fill="#78350f" fillOpacity="0.25" stroke="#f59e0b" strokeWidth={selectedZone === 'livestock' ? 3 : 1.5} />
              <text x="85" y="165" fill="#f59e0b" fontSize="10" fontWeight="700">🐑 VALAIS SHEEP &amp; ALPACAS</text>
              <rect x="85" y="180" width="60" height="40" rx="4" fill="#b45309" stroke="#fbbf24" strokeWidth="1" />
              <text x="92" y="205" fill="#ffffff" fontSize="8" fontWeight="600">Timber Barn</text>
              <rect x="85" y="235" width="45" height="30" rx="4" fill="#92400e" stroke="#fbbf24" strokeWidth="1" />
              <text x="90" y="253" fill="#ffffff" fontSize="7">Alpaca Paddock</text>
            </g>

            {/* 8. 150 kW Solar PV Field (North-Eastern Corner) */}
            <g>
              <rect x="580" y="60" width="160" height="90" rx="8" fill="#1e3a8a" fillOpacity="0.4" stroke="#38bdf8" strokeWidth="1.5" />
              <text x="595" y="85" fill="#38bdf8" fontSize="10" fontWeight="700">☀️ 150 kW SOLAR ARRAY</text>
              {/* Solar cell grid lines */}
              <line x1="630" y1="95" x2="630" y2="140" stroke="#60a5fa" strokeWidth="1" strokeDasharray="2 2" />
              <line x1="680" y1="95" x2="680" y2="140" stroke="#60a5fa" strokeWidth="1" strokeDasharray="2 2" />
              <text x="605" y="125" fill="#93c5fd" fontSize="8">BESS Battery Vault</text>
            </g>

            {/* 9. Polycarbonate Living Stage Greenhouse (East Sector) */}
            <g onClick={() => setSelectedZone('greenhouse')} style={{ cursor: 'pointer' }}>
              <rect x="560" y="210" width="170" height="130" rx="8" fill="#064e3b" fillOpacity="0.45" stroke="#10b981" strokeWidth={selectedZone === 'greenhouse' ? 3 : 1.5} />
              <text x="575" y="235" fill="#10b981" fontSize="10" fontWeight="700">🌱 POLYCARBONATE GREENHOUSE</text>
              <text x="575" y="252" fill="#6ee7b7" fontSize="8">4,000 sq ft &bull; Living NFT Towers</text>
              {/* Hydroponic tray lines */}
              <rect x="575" y="265" width="140" height="60" rx="4" fill="#047857" fillOpacity="0.3" stroke="#34d399" strokeWidth="0.8" />
              <text x="590" y="300" fill="#a7f3d0" fontSize="9" fontWeight="600">Living Stage Concert Platform</text>
            </g>

            {/* 10. ÖÖD Mirror Cottages Ring (NW, East & SE) */}
            <g onClick={() => setSelectedZone('ood_pods')} style={{ cursor: 'pointer' }}>
              {[
                { x: 260, y: 90, label: 'Pod 1' },
                { x: 310, y: 70, label: 'Pod 2' },
                { x: 480, y: 75, label: 'Pod 3' },
                { x: 530, y: 100, label: 'Pod 4' },
                { x: 670, y: 390, label: 'Pod 5' },
                { x: 690, y: 440, label: 'Pod 6' },
                { x: 650, y: 500, label: 'Pod 7' },
                { x: 600, y: 530, label: 'Pod 8' }
              ].map((pod, idx) => (
                <g key={idx}>
                  <rect x={pod.x} y={pod.y} width="32" height="24" rx="4" fill="#581c87" stroke="#c084fc" strokeWidth={selectedZone === 'ood_pods' ? 2 : 1} />
                  <text x={pod.x + 4} y={pod.y + 15} fill="#e9d5ff" fontSize="7" fontWeight="700">{pod.label}</text>
                </g>
              ))}
            </g>

            {/* 11. Zone 2: Tech-Earthships (Residential Halo) */}
            <g onClick={() => setSelectedZone('zone2')} style={{ cursor: 'pointer' }}>
              <path d="M 280,360 A 150 150 0 0 0 520,360" fill="none" stroke="#818cf8" strokeWidth={selectedZone === 'zone2' ? 18 : 14} strokeLinecap="round" opacity="0.6" />
              <text x="330" y="385" fill="#c7d2fe" fontSize="9" fontWeight="700">ZONE 2: RESIDENTIAL TECH-EARTHSHIPS</text>
            </g>

            {/* 12. Zone 1: Green Rooms (Inner Ring) */}
            <g onClick={() => setSelectedZone('zone1')} style={{ cursor: 'pointer' }}>
              <circle cx="400" cy="270" r="75" fill="none" stroke="#38bdf8" strokeWidth={selectedZone === 'zone1' ? 8 : 5} opacity="0.75" />
              <text x="325" y="210" fill="#7dd3fc" fontSize="9" fontWeight="700">ZONE 1: GREEN ROOMS</text>
            </g>

            {/* 13. Zone 0 (The Core): The Living Stage Amphitheater */}
            <g onClick={() => setSelectedZone('zone0')} style={{ cursor: 'pointer' }}>
              {/* Amphitheater bowl tiers */}
              <circle cx="400" cy="270" r="50" fill="#083344" stroke="#00ffff" strokeWidth={selectedZone === 'zone0' ? 3.5 : 2} />
              <circle cx="400" cy="270" r="35" fill="#0e7490" stroke="#22d3ee" strokeWidth="1.5" />
              <circle cx="400" cy="270" r="20" fill="#0891b2" stroke="#67e8f9" strokeWidth="1.5" />
              <polygon points="390,260 410,260 415,275 385,275" fill="#f43f5e" stroke="#ffffff" strokeWidth="1" />
              <text x="365" y="272" fill="#ffffff" fontSize="8" fontWeight="800">STAGE</text>
              <text x="345" y="310" fill="#00ffff" fontSize="10" fontWeight="800">ZONE 0: LIVING STAGE</text>
            </g>

            {/* 14. Central Courtyard Fire Pit */}
            <g onClick={() => setSelectedZone('courtyard')} style={{ cursor: 'pointer' }}>
              <circle cx="400" cy="345" r="14" fill="#7c2d12" stroke="#f97316" strokeWidth={selectedZone === 'courtyard' ? 3 : 1.5} />
              <circle cx="400" cy="345" r="5" fill="#ea580c" />
              <text x="375" y="370" fill="#fdba74" fontSize="8" fontWeight="700">Fire Pit</text>
            </g>

            {/* 15. Front of House (FOH) Tower (6 o'clock Position) */}
            <g onClick={() => setSelectedZone('foh_tower')} style={{ cursor: 'pointer' }}>
              <rect x="375" y="420" width="50" height="40" rx="6" fill="#854d0e" stroke="#eab308" strokeWidth={selectedZone === 'foh_tower' ? 3 : 1.5} />
              <text x="382" y="438" fill="#ffffff" fontSize="8" fontWeight="800">FOH</text>
              <text x="380" y="450" fill="#fef08a" fontSize="7">Tower</text>
            </g>
          </svg>

          {/* Quick Zone Picker Pills below Map */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '14px' }}>
            {Object.keys(zones).map(key => (
              <button
                key={key}
                onClick={() => setSelectedZone(key)}
                style={{
                  background: selectedZone === key ? zones[key].color : 'rgba(255, 255, 255, 0.05)',
                  color: selectedZone === key ? '#000000' : '#cbd5e1',
                  border: `1px solid ${zones[key].color}`,
                  borderRadius: '20px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {zones[key].name.split(':')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Live Zone Telemetry Inspector Card */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.95)',
          border: `1.5px solid ${activeZoneData.color}`,
          borderRadius: '12px',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          boxShadow: `0 0 25px ${activeZoneData.color}25`
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <span style={{
                  background: `${activeZoneData.color}20`,
                  color: activeZoneData.color,
                  border: `1px solid ${activeZoneData.color}`,
                  padding: '3px 8px',
                  borderRadius: '12px',
                  fontSize: '0.7rem',
                  fontWeight: 800,
                  textTransform: 'uppercase'
                }}>
                  {activeZoneData.category}
                </span>
                <h3 style={{ margin: '8px 0 4px 0', fontSize: '1.25rem', color: '#ffffff', fontWeight: 800 }}>
                  {activeZoneData.name}
                </h3>
              </div>
            </div>

            <p style={{ color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.6, margin: '0 0 16px 0' }}>
              {activeZoneData.details}
            </p>

            {/* Spec Matrix Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px',
              background: 'rgba(0, 0, 0, 0.35)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '14px',
              marginBottom: '16px'
            }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>FOOTPRINT / AREA</div>
                <div style={{ fontSize: '0.85rem', color: '#ffffff', fontWeight: 700 }}>{activeZoneData.size}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>POWER DEMAND</div>
                <div style={{ fontSize: '0.85rem', color: '#00FFFF', fontWeight: 700 }}>{activeZoneData.powerDraw}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>ACOUSTIC ISOLATION</div>
                <div style={{ fontSize: '0.85rem', color: '#10B981', fontWeight: 700 }}>{activeZoneData.audioRating}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>WATER BUDGET</div>
                <div style={{ fontSize: '0.85rem', color: '#38BDF8', fontWeight: 700 }}>{activeZoneData.waterUse}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>CAPACITY / OCCUPANCY</div>
                <div style={{ fontSize: '0.85rem', color: '#F59E0B', fontWeight: 700 }}>{activeZoneData.occupancy}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>CURRENT TELEMETRY</div>
                <div style={{ fontSize: '0.85rem', color: '#A78BFA', fontWeight: 700 }}>{activeZoneData.status}</div>
              </div>
            </div>
          </div>

          {/* Quick Action Protocol Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              onClick={() => alert(`Triggering telemetry audit for ${activeZoneData.name}... Nominal status confirmed.`)}
              style={{
                background: 'linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(122, 40, 138, 0.4))',
                border: '1px solid #00FFFF',
                color: '#ffffff',
                padding: '10px',
                borderRadius: '8px',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              📡 Ping Zone IoT Sensors
            </button>
            <button
              onClick={() => alert(`Isolating audio & power telemetry for ${activeZoneData.name}`)}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#94a3b8',
                padding: '8px',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              ⚙️ Route Microgrid Feeder
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
