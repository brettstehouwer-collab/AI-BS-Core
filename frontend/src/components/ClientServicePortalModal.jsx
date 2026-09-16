import React, { useState } from 'react';
import './ClientServicePortalModal.css';

export default function ClientServicePortalModal({
  isOpen,
  onClose,
  serviceId = 'prestige_wash_882'
}) {
  const [sliderPos, setSliderPos] = useState(50);
  const [isPaid, setIsPaid] = useState(false);
  const [isProcessingPay, setIsProcessingPay] = useState(false);
  const [tipPercent, setTipPercent] = useState(15);
  const [clientRating, setClientRating] = useState(5);

  const basePrice = 285.00;
  const ecoFee = 15.00;
  const tax = basePrice * 0.06;
  const tipAmount = (basePrice * tipPercent) / 100;
  const total = basePrice + ecoFee + tax + tipAmount;

  const handlePay = () => {
    setIsProcessingPay(true);
    setTimeout(() => {
      setIsProcessingPay(false);
      setIsPaid(true);
    }, 1200);
  };

  if (!isOpen) return null;

  return (
    <div className="service-portal-backdrop" onClick={onClose}>
      <div className="service-portal-card" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="service-portal-header">
          <div className="service-logo-group">
            <span className="wash-icon">🚿</span>
            <div>
              <h1 className="service-brand">Prestige Mobile Wash</h1>
              <p className="service-sub">Client Service Tracking & Verified Inspection Portal • #{serviceId}</p>
            </div>
          </div>
          {onClose && <button className="portal-close-btn" onClick={onClose}>✕</button>}
        </div>

        {/* Live GPS Fleet Status Pill */}
        <div className="gps-status-banner">
          <div className="gps-indicator">
            <span className="pulse-dot">🟢</span>
            <span className="gps-text">Fleet Rig #2 (Grand Rapids Commercial Unit) — <strong>Service Completed & Quality Inspected</strong></span>
          </div>
          <span className="gps-time">Logged: Today at 2:45 PM</span>
        </div>

        {/* Body Content */}
        <div className="service-portal-body">
          {/* Left: Interactive Before / After Inspector */}
          <div className="service-inspection-pane">
            <h3 className="pane-title">📸 Verified Proof-of-Service (Interactive Slider)</h3>
            <p className="pane-sub">Drag slider left/right to inspect cleaning results across surfaces.</p>

            <div className="before-after-container">
              {/* After Layer (Background) */}
              <div
                className="ba-image-layer after-layer"
                style={{
                  background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                  fontSize: '1.2rem',
                  fontWeight: 'bold'
                }}
              >
                ✨ AFTER: Restored & Sealed Surface
              </div>

              {/* Before Layer (Foreground clipped) */}
              <div
                className="ba-image-layer before-layer"
                style={{
                  clipPath: `inset(0 ${100 - sliderPos}% 0 0)`,
                  background: 'linear-gradient(135deg, #475569 0%, #1e293b 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#f87171',
                  fontSize: '1.2rem',
                  fontWeight: 'bold'
                }}
              >
                ⚠️ BEFORE: Grime, Algae & Oxidation
              </div>

              {/* Slider Divider Line */}
              <div className="slider-divider" style={{ left: `${sliderPos}%` }}>
                <div className="slider-handle">↔</div>
              </div>

              <input
                type="range"
                min="0"
                max="100"
                value={sliderPos}
                onChange={e => setSliderPos(parseInt(e.target.value))}
                className="ba-range-input"
              />
            </div>

            {/* Quality Checklist */}
            <div className="quality-checklist">
              <div className="check-item">✅ 250°F Hot Water Pressure Wash Applied</div>
              <div className="check-item">✅ Biodegradable Surface Neutralizer Rinse</div>
              <div className="check-item">✅ Zero Runoff Environmental Compliance Verified</div>
            </div>
          </div>

          {/* Right: Itemized Invoice & Instant Checkout */}
          <div className="service-checkout-pane">
            <div className="service-invoice-card">
              <h3 className="invoice-title">🧾 Itemized Service Invoice</h3>

              <div className="invoice-line">
                <span>Commercial Fleet Power Wash:</span>
                <span>${basePrice.toFixed(2)}</span>
              </div>
              <div className="invoice-line">
                <span>Eco-Friendly Neutralizer & Rinse:</span>
                <span>${ecoFee.toFixed(2)}</span>
              </div>
              <div className="invoice-line">
                <span>Michigan State Sales Tax (6%):</span>
                <span>${tax.toFixed(2)}</span>
              </div>

              {/* Tip Selection */}
              <div className="tip-selection-row">
                <span className="tip-label">Technician Tip:</span>
                <div className="tip-buttons">
                  {[10, 15, 20, 25].map(t => (
                    <button
                      key={t}
                      className={`tip-btn ${tipPercent === t ? 'active' : ''}`}
                      onClick={() => setTipPercent(t)}
                    >
                      {t}% (${((basePrice * t) / 100).toFixed(0)})
                    </button>
                  ))}
                </div>
              </div>

              <div className="invoice-divider" />

              <div className="invoice-total-line">
                <span>Total Amount:</span>
                <span className="total-val">${total.toFixed(2)}</span>
              </div>
            </div>

            {/* Rating Stars */}
            <div className="rating-card">
              <span className="rating-label">Rate Today's Service:</span>
              <div className="stars-row">
                {[1, 2, 3, 4, 5].map(star => (
                  <button
                    key={star}
                    className={`star-btn ${clientRating >= star ? 'filled' : ''}`}
                    onClick={() => setClientRating(star)}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>

            {/* Payment Button */}
            <div className="checkout-action-area">
              {isPaid ? (
                <div className="paid-success-banner">
                  <span className="success-icon">🎉</span>
                  <div>
                    <strong>Payment Confirmed!</strong>
                    <p style={{ margin: 0, fontSize: '0.8rem' }}>Receipt sent to your email. Thank you for choosing Prestige!</p>
                  </div>
                </div>
              ) : (
                <button
                  onClick={handlePay}
                  disabled={isProcessingPay}
                  className="apple-pay-checkout-btn"
                >
                  {isProcessingPay ? 'Processing Payment...' : `💳 Pay $${total.toFixed(2)} (Instant Apple Pay / Card)`}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
