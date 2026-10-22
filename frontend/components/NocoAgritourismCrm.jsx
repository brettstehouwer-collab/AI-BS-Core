import React, { useState } from 'react';

export default function NocoAgritourismCrm() {
  const [selectedEventId, setSelectedEventId] = useState('event1');
  const [selectedPodId, setSelectedPodId] = useState('pod1');
  const [bookingModalOpen, setBookingModalOpen] = useState(false);
  const [applicantName, setApplicantName] = useState('');
  const [applicantMedium, setApplicantMedium] = useState('Music Production');

  // Flagship Events Data
  const [events, setEvents] = useState([
    {
      id: 'event1',
      title: 'Sunset Acoustic Greenhouse Sessions',
      date: 'Saturday, November 7, 2026',
      time: '6:00 PM – 9:30 PM EDT',
      venue: 'Polycarbonate Living Stage',
      capacity: 150,
      ticketsSold: 132,
      priceGa: 45,
      priceVip: 95,
      vipSold: 25,
      gaSold: 107,
      description: 'Intimate acoustic sets by resident artists amidst vertical NFT lettuce towers. Warm 2700K theatrical lighting blended with botanical greenhouse aromas. Concessions provided by The MELT.'
    },
    {
      id: 'event2',
      title: 'Farm-to-Table Equinox Dinner (by The MELT)',
      date: 'Friday, November 13, 2026',
      time: '5:30 PM – 10:00 PM EDT',
      venue: 'Central Courtyard & Reflecting Pool',
      capacity: 60,
      ticketsSold: 54,
      priceGa: 125,
      priceVip: 175,
      vipSold: 20,
      gaSold: 34,
      description: '5-course culinary celebration curated entirely from on-site greenhouse harvest, local Finger Lakes root crops, and organic artisan cheeses. Live classical guitar by the concentric stone fire pit.'
    },
    {
      id: 'event3',
      title: 'Bio-Acoustic Sound Bath & Microgrid Retreat',
      date: 'Sunday, November 22, 2026',
      time: '10:00 AM – 2:00 PM EDT',
      venue: 'Zone 0 Amphitheater & Green Rooms',
      capacity: 40,
      ticketsSold: 38,
      priceGa: 65,
      priceVip: 110,
      vipSold: 12,
      gaSold: 26,
      description: 'Deep frequency meditation utilizing parabolic sound shells, 432Hz crystal bowls, and live plant bio-voltage synthesizers. Includes guided tour of the 500 kWh BESS microgrid and fir grove trails.'
    }
  ]);

  // 8 ÖÖD Pod Artist Residency Grid
  const [pods, setPods] = useState([
    { id: 'pod1', name: 'ÖÖD Pod 1 (Northwest Fir)', status: 'Occupied', artist: 'Elena Rostova', medium: 'Acoustic Cello & Sound Sculptor', dates: 'Oct 15 – Nov 15', fellowship: 'NYSCA Grant' },
    { id: 'pod2', name: 'ÖÖD Pod 2 (Pine Ridge)', status: 'Occupied', artist: 'Marcus Vance', medium: 'Screenwriting & Audio DSP', dates: 'Oct 20 – Dec 1', fellowship: 'Sovereign AI Grant' },
    { id: 'pod3', name: 'ÖÖD Pod 3 (Lakeside East)', status: 'Reserved', artist: 'Dr. Aris Thorne', medium: 'Botanical Frequency Synthesizer', dates: 'Nov 1 – Nov 30', fellowship: 'MIT Media Lab' },
    { id: 'pod4', name: 'ÖÖD Pod 4 (Wild Orchard)', status: 'Available', artist: 'Open Call', medium: 'Visual Arts / Playwriting', dates: 'Winter Cohort 2026', fellowship: 'Open Fellowship' },
    { id: 'pod5', name: 'ÖÖD Pod 5 (Sound Sanctuary)', status: 'Occupied', artist: 'Sean & Kief Stehouwer', medium: 'Acoustic Architecture & FOH Lead', dates: 'Permanent Co-Founder', fellowship: 'Founder Suite' },
    { id: 'pod6', name: 'ÖÖD Pod 6 (Valley Vista)', status: 'Reserved', artist: 'Chloe Moreau', medium: 'Fiber Arts & Valais Wool Weaving', dates: 'Nov 15 – Dec 15', fellowship: 'Finger Lakes Agritourism' },
    { id: 'pod7', name: 'ÖÖD Pod 7 (Stone Meadow)', status: 'Available', artist: 'Open Call', medium: 'Music Producer / Vocalist', dates: 'Winter Cohort 2026', fellowship: 'Open Fellowship' },
    { id: 'pod8', name: 'ÖÖD Pod 8 (High Fir Overlook)', status: 'Reserved', artist: 'Julian Chen', medium: 'Lighting Design & Laser Projection', dates: 'Dec 1 – Jan 15', fellowship: 'Creative Enclave Fund' }
  ]);

  // NY State Agricultural & Creative Grants Pipeline
  const grants = [
    { name: 'NYS Ag & Markets Specialty Crop Infrastructure Grant', amount: 125000, status: 'Approved & Disbursed', matchRequired: 25000, color: '#10b981' },
    { name: 'NYSCA Decentralization Creative Production Grant', amount: 75000, status: 'Under Review (Awarding Nov 2026)', matchRequired: 15000, color: '#38bdf8' },
    { name: 'Finger Lakes Regional Agritourism Growth Fund', amount: 50000, status: 'Awarded (Phase 1 Complete)', matchRequired: 10000, color: '#f59e0b' }
  ];

  const totalGrantFunds = grants.reduce((acc, g) => acc + g.amount, 0);

  const activeEvent = events.find(e => e.id === selectedEventId) || events[0];
  const activePod = pods.find(p => p.id === selectedPodId) || pods[0];

  const grossEventRevenue = (activeEvent.gaSold * activeEvent.priceGa) + (activeEvent.vipSold * activeEvent.priceVip);
  const percentSold = Math.round((activeEvent.ticketsSold / activeEvent.capacity) * 100);

  const handleSimulateTicketSale = () => {
    if (activeEvent.ticketsSold < activeEvent.capacity) {
      const updated = events.map(e => {
        if (e.id === activeEvent.id) {
          return {
            ...e,
            ticketsSold: e.ticketsSold + 1,
            gaSold: e.gaSold + 1
          };
        }
        return e;
      });
      setEvents(updated);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', color: '#f8fafc' }}>
      
      {/* 1. Header Banner */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.9)',
        border: '1px solid rgba(245, 158, 11, 0.35)',
        borderRadius: '12px',
        padding: '16px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.4rem' }}>🎟️</span>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#F59E0B', fontWeight: 800 }}>
              Agritourism, Event Box Office &amp; Artist Residency CRM
            </h3>
            <span style={{
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid #f59e0b',
              color: '#f59e0b',
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 800
            }}>
              501(c)(3) &amp; AGRITOURISM HUB
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
            Box Office Operations &bull; 8 ÖÖD Mirror Pod Residency Ledger &bull; NY State Grant War Chest
          </p>
        </div>

        {/* Total Grants Summary Badge */}
        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>TOTAL GRANT CAPITAL SECURED</div>
          <div style={{ fontSize: '1.15rem', color: '#10b981', fontWeight: 800 }}>${totalGrantFunds.toLocaleString()} USD</div>
        </div>
      </div>

      {/* 2. Top Grid: Event Box Office & Ticketing Tier Matrix */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1.3fr) minmax(320px, 1fr)', gap: '20px' }}>
        
        {/* Events Schedule & Active Ticket Drawer */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
              📅 Live Agritourism &amp; Concert Box Office
            </h4>
            <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>Real-Time Ticket Engine</span>
          </div>

          {/* Event Picker Tabs */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', overflowX: 'auto' }}>
            {events.map(ev => (
              <button
                key={ev.id}
                onClick={() => setSelectedEventId(ev.id)}
                style={{
                  background: selectedEventId === ev.id ? 'rgba(245, 158, 11, 0.2)' : 'rgba(0, 0, 0, 0.4)',
                  border: `1px solid ${selectedEventId === ev.id ? '#f59e0b' : 'rgba(255, 255, 255, 0.1)'}`,
                  color: selectedEventId === ev.id ? '#f59e0b' : '#94a3b8',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                {ev.title.split('(')[0]}
              </button>
            ))}
          </div>

          {/* Selected Event Details Card */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', marginBottom: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div>
                <h5 style={{ margin: 0, fontSize: '1.1rem', color: '#ffffff', fontWeight: 800 }}>{activeEvent.title}</h5>
                <div style={{ fontSize: '0.8rem', color: '#38bdf8', marginTop: '2px' }}>
                  {activeEvent.date} &bull; {activeEvent.time} &bull; <strong>{activeEvent.venue}</strong>
                </div>
              </div>
              <span style={{
                background: percentSold >= 90 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                color: percentSold >= 90 ? '#f87171' : '#34d399',
                border: `1px solid ${percentSold >= 90 ? '#ef4444' : '#10b981'}`,
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 800
              }}>
                {percentSold}% SOLD OUT
              </span>
            </div>

            <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5, margin: '0 0 14px 0' }}>
              {activeEvent.description}
            </p>

            {/* Sell-Through Progress Bar */}
            <div style={{ marginBottom: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Capacity: {activeEvent.ticketsSold} / {activeEvent.capacity} Attendees</span>
                <strong style={{ color: '#f59e0b' }}>Gross Projected: ${grossEventRevenue.toLocaleString()} USD</strong>
              </div>
              <div style={{ height: '8px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${percentSold}%`, height: '100%', background: 'linear-gradient(90deg, #10b981 0%, #f59e0b 80%, #ef4444 100%)' }} />
              </div>
            </div>

            {/* Ticket Tier Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ background: 'rgba(255,255,255,0.04)', padding: '10px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>GENERAL ADMISSION</div>
                <div style={{ fontSize: '1rem', color: '#ffffff', fontWeight: 800 }}>${activeEvent.priceGa} <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>({activeEvent.gaSold} Sold)</span></div>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.04)', padding: '10px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>VIP FARM HARVEST PASS</div>
                <div style={{ fontSize: '1rem', color: '#f59e0b', fontWeight: 800 }}>${activeEvent.priceVip} <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>({activeEvent.vipSold} Sold)</span></div>
              </div>
            </div>
          </div>

          {/* Quick Simulation Action */}
          <button
            onClick={handleSimulateTicketSale}
            disabled={activeEvent.ticketsSold >= activeEvent.capacity}
            style={{
              width: '100%',
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(16, 185, 129, 0.4))',
              border: '1px solid #f59e0b',
              color: '#ffffff',
              padding: '10px',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            🎟️ + Simulate Guest Ticket Purchase (Box Office POS)
          </button>
        </div>

        {/* 8 ÖÖD Pod Residency Grid */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between'
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
                🏡 8 ÖÖD Mirror Pod Residency Ledger
              </h4>
              <span style={{ fontSize: '0.75rem', color: '#c084fc', fontWeight: 600 }}>6 / 8 Units Reserved</span>
            </div>

            {/* Pod Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', marginBottom: '14px' }}>
              {pods.map(pod => (
                <div
                  key={pod.id}
                  onClick={() => setSelectedPodId(pod.id)}
                  style={{
                    background: selectedPodId === pod.id ? 'rgba(192, 132, 252, 0.25)' : 'rgba(0,0,0,0.3)',
                    border: `1px solid ${selectedPodId === pod.id ? '#c084fc' : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: '8px',
                    padding: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#ffffff' }}>{pod.name.split('(')[0]}</span>
                    <span style={{
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      color: pod.status === 'Occupied' ? '#38bdf8' : pod.status === 'Reserved' ? '#f59e0b' : '#10b981'
                    }}>
                      {pod.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {pod.artist}
                  </div>
                </div>
              ))}
            </div>

            {/* Selected Pod Inspector */}
            <div style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#c084fc', fontWeight: 700 }}>RESIDENCY PROFILE: {activePod.name}</div>
              <div style={{ fontSize: '1rem', color: '#ffffff', fontWeight: 800, margin: '4px 0' }}>{activePod.artist}</div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Medium: <strong>{activePod.medium}</strong></div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px' }}>
                Residency Window: <strong>{activePod.dates}</strong> &bull; Sponsor: <span style={{ color: '#10b981' }}>{activePod.fellowship}</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
            <button
              onClick={() => alert(`Opening Artist Residency Application Portal for ${activePod.name}`)}
              style={{
                flex: 1,
                background: 'rgba(192, 132, 252, 0.2)',
                border: '1px solid #c084fc',
                color: '#ffffff',
                padding: '8px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              ✍️ Book / Assign Residency
            </button>
          </div>
        </div>
      </div>

      {/* 3. New York State Grants & Capital Pipeline */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.85)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '12px',
        padding: '20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
              🏛️ New York State Agricultural &amp; Arts Grants War Chest
            </h4>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              501(c)(3) Non-Profit &bull; Finger Lakes Regional Development &bull; Matching Capital Program
            </span>
          </div>
          <span style={{ fontSize: '0.85rem', color: '#10b981', fontWeight: 800 }}>$250,000 Total Allocation</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
          {grants.map((g, idx) => (
            <div key={idx} style={{ background: 'rgba(0,0,0,0.35)', border: `1px solid ${g.color}40`, borderRadius: '8px', padding: '14px' }}>
              <div style={{ fontSize: '0.75rem', color: '#cbd5e1', fontWeight: 700, marginBottom: '4px' }}>{g.name}</div>
              <div style={{ fontSize: '1.3rem', color: g.color, fontWeight: 900, marginBottom: '4px' }}>
                ${g.amount.toLocaleString()} <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>USD</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: g.color, fontWeight: 600 }}>● {g.status}</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '4px' }}>Local Match: ${g.matchRequired.toLocaleString()}</div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
