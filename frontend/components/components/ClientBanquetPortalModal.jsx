import React, { useState, useRef } from 'react';
import './ClientBanquetPortalModal.css';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export default function ClientBanquetPortalModal({
  isOpen,
  onClose,
  eventId = 'notos_gala_2026'
}) {
  const [guestCount, setGuestCount] = useState(150);
  const [selectedRoom, setSelectedRoom] = useState('Grand Ballroom & Tuscan Terrace');
  const [selectedMenu, setSelectedMenu] = useState('executive');
  const [selectedBar, setSelectedBar] = useState('premium');
  const [specialDietary, setSpecialDietary] = useState('');
  const [clientName, setClientName] = useState('Mr. & Mrs. Anderson');
  const [clientEmail, setClientEmail] = useState('client@example.com');
  const [isSigned, setIsSigned] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);

  // Menu Options
  const menuOptions = {
    classic: { name: 'Classic Tuscan Italian Feast', price: 55.00, desc: 'House lasagna, chicken marsala, seasonal risotto, garlic foccacia, caesar salad.' },
    executive: { name: 'Executive Plated Filet Mignon & Sea Bass', price: 85.00, desc: 'Center-cut 8oz filet mignon, pan-seared Chilean sea bass, asparagus, truffle mash.' },
    reserve: { name: 'Cellar Master Reserve Gala (6-Course)', price: 120.00, desc: 'Antipasti misto, lobster ravioli, dry-aged ribeye, artisan cheeses, tiramisu.' }
  };

  // Bar Options
  const barOptions = {
    none: { name: 'Non-Alcoholic Artisanal Beverages Only', price: 10.00 },
    beer_wine: { name: 'Noto\'s Selected Italian Beers & House Wines', price: 22.00 },
    premium: { name: 'Full Premium Open Bar & Signature Cocktails', price: 38.00 },
    cellar_reserve: { name: 'Cellar Master Vintage Wine Pairings & Sommelier Service', price: 55.00 }
  };

  // Financial Calculations
  const foodTotal = guestCount * menuOptions[selectedMenu].price;
  const barTotal = guestCount * barOptions[selectedBar].price;
  const subtotal = foodTotal + barTotal;
  const serviceCharge = subtotal * 0.20;
  const tax = subtotal * 0.06;
  const total = subtotal + serviceCharge + tax;
  const deposit = 3000.00;
  const balanceDue = total - deposit;

  // Signature Pad Handlers
  const startDrawing = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1e293b';
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
  };

  const stopDrawing = () => {
    if (isDrawing) {
      setIsDrawing(false);
      setIsSigned(true);
    }
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      setIsSigned(false);
    }
  };

  // Download BEO
  const handleDownloadBEO = async () => {
    setIsExporting(true);
    try {
      const res = await fetch(`${API_BASE}/api/documents/banquet/generate_beo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_name: 'Client Reserved Banquet Celebration',
          client_name: clientName,
          contact_email: clientEmail,
          event_date: 'Saturday, October 24, 2026',
          event_time: '5:30 PM - 11:30 PM',
          room_name: selectedRoom,
          guest_count: guestCount,
          menu_package: menuOptions[selectedMenu].name,
          bar_service: barOptions[selectedBar].name,
          special_requests: specialDietary || 'Standard service requested.',
          subtotal: subtotal,
          service_charge: serviceCharge,
          tax: tax,
          total: total,
          deposit_paid: deposit,
          balance_due: balanceDue
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BEO_${clientName.replace(/\s+/g, '_')}.docx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('Could not download BEO document.');
      }
    } catch (e) {
      alert(`Export error: ${e.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="client-portal-backdrop" onClick={onClose}>
      <div className="client-portal-card" onClick={e => e.stopPropagation()}>
        {/* Portal Header */}
        <div className="portal-header">
          <div className="portal-header-left">
            <span className="venue-logo">🍷</span>
            <div>
              <h1 className="venue-title">Noto's Restaurant & Banquet Center</h1>
              <p className="portal-sub">Client Interactive Event Planner & Digital BEO Gateway</p>
            </div>
          </div>
          {onClose && <button className="portal-close-btn" onClick={onClose}>✕</button>}
        </div>

        {/* Portal Body */}
        <div className="portal-body">
          {/* Left Column: Event Configuration */}
          <div className="portal-config-pane">
            <div className="portal-section">
              <h3 className="section-title">1. Assigned Venue Space</h3>
              <div className="room-selector-grid">
                {['Grand Ballroom & Tuscan Terrace', 'Cellar Master Private Wine Vault', 'Waterfront Glass Pavilion (Grand Haven)'].map(r => (
                  <button
                    key={r}
                    className={`room-btn ${selectedRoom === r ? 'active' : ''}`}
                    onClick={() => setSelectedRoom(r)}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div className="portal-section">
              <div className="section-header-flex">
                <h3 className="section-title">2. Guaranteed Guest Count</h3>
                <span className="guest-pill">{guestCount} Guests</span>
              </div>
              <input
                type="range"
                min="40"
                max="350"
                step="5"
                value={guestCount}
                onChange={e => setGuestCount(parseInt(e.target.value))}
                className="guest-slider"
              />
            </div>

            <div className="portal-section">
              <h3 className="section-title">3. Culinary Menu Selection</h3>
              <div className="menu-cards-list">
                {Object.entries(menuOptions).map(([key, opt]) => (
                  <div
                    key={key}
                    className={`menu-card ${selectedMenu === key ? 'active' : ''}`}
                    onClick={() => setSelectedMenu(key)}
                  >
                    <div className="menu-card-top">
                      <span className="menu-name">{opt.name}</span>
                      <span className="menu-price">${opt.price.toFixed(2)} / guest</span>
                    </div>
                    <p className="menu-desc">{opt.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="portal-section">
              <h3 className="section-title">4. Beverage & Bar Program</h3>
              <div className="bar-cards-list">
                {Object.entries(barOptions).map(([key, opt]) => (
                  <div
                    key={key}
                    className={`bar-card ${selectedBar === key ? 'active' : ''}`}
                    onClick={() => setSelectedBar(key)}
                  >
                    <span className="bar-name">{opt.name}</span>
                    <span className="bar-price">+${opt.price.toFixed(2)} / guest</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="portal-section">
              <h3 className="section-title">5. Dietary & Special Requests</h3>
              <input
                type="text"
                value={specialDietary}
                onChange={e => setSpecialDietary(e.target.value)}
                placeholder="e.g. 4 gluten-free entrees, champagne arrival toast, kosher options..."
                className="portal-input"
              />
            </div>
          </div>

          {/* Right Column: Pricing Breakdown & Signature */}
          <div className="portal-summary-pane">
            <div className="pricing-summary-card">
              <h3 className="summary-title">📊 Itemized Estimate Summary</h3>

              <div className="summary-line">
                <span>Food Program ({guestCount} × ${menuOptions[selectedMenu].price}):</span>
                <span>${foodTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="summary-line">
                <span>Bar Service ({guestCount} × ${barOptions[selectedBar].price}):</span>
                <span>${barTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="summary-line highlight">
                <span>Subtotal:</span>
                <span>${subtotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="summary-line">
                <span>Service Charge & Gratuity (20%):</span>
                <span>${serviceCharge.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="summary-line">
                <span>State Tax (6%):</span>
                <span>${tax.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>

              <div className="summary-divider" />

              <div className="summary-total-line">
                <span>Total Contract:</span>
                <span className="total-amount">${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="summary-line deposit">
                <span>Deposit Confirmed:</span>
                <span>-${deposit.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="summary-line balance">
                <span>Remaining Balance Due:</span>
                <span>${balanceDue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>

            {/* Signature Block */}
            <div className="signature-card">
              <h4 className="sig-title">✍️ Client Digital Authorization</h4>
              <p className="sig-sub">Sign inside the box to lock in your banquet reservation date.</p>

              <div className="signature-canvas-wrapper">
                <canvas
                  ref={canvasRef}
                  width={340}
                  height={110}
                  className="sig-canvas"
                  onMouseDown={startDrawing}
                  onMouseMove={draw}
                  onMouseUp={stopDrawing}
                  onMouseLeave={stopDrawing}
                />
              </div>

              <div className="sig-actions">
                <button onClick={clearSignature} className="sig-clear-btn">Clear</button>
                <span className="sig-status">{isSigned ? '🟢 Signature Recorded' : 'Draw signature above'}</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="portal-final-actions">
              <button
                onClick={handleDownloadBEO}
                disabled={isExporting}
                className="download-beo-btn"
              >
                {isExporting ? '⏳ Generating BEO...' : '📥 Download Official Word BEO (.docx)'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
