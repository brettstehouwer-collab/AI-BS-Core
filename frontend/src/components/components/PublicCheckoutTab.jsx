import React, { useState } from 'react';

const PASS_TIERS = [
  { id: 'pass_1day', name: '1-Day Pass', duration: '24 Hours', price: '$4.99', amount: 4.99, badge: 'Popular', reqs: '250 req/day', rpm: '20 RPM', desc: 'Ideal for quick 1-day AI generation projects and quick API testing.' },
  { id: 'pass_3day', name: '3-Day Pass', duration: '72 Hours (3 Days)', price: '$11.99', amount: 11.99, badge: 'Best Value', reqs: '250 req/day', rpm: '25 RPM', desc: 'Perfect weekend pass for artists and short project sprints.' },
  { id: 'pass_5day', name: '5-Day Pass', duration: '120 Hours (5 Days)', price: '$17.99', amount: 17.99, badge: null, reqs: '250 req/day', rpm: '30 RPM', desc: 'Work-week pass for intense creative asset production.' },
  { id: 'pass_7day', name: '7-Day Pass', duration: '168 Hours (1 Week)', price: '$22.99', amount: 22.99, badge: 'Weekly Pass', reqs: '300 req/day', rpm: '35 RPM', desc: 'Full week of unthrottled SDXL image, video, and chat compute.' },
  { id: 'pass_12day', name: '12-Day Pass', duration: '288 Hours (12 Days)', price: '$34.99', amount: 34.99, badge: null, reqs: '350 req/day', rpm: '40 RPM', desc: 'Extended developer pass for batch rendering datasets.' },
  { id: 'pass_15day', name: '15-Day Pass', duration: '360 Hours (Half-Month)', price: '$39.99', amount: 39.99, badge: 'Half Month', reqs: '400 req/day', rpm: '45 RPM', desc: 'Half-month pass for active creators and small studios.' },
  { id: 'pass_30day', name: '30-Day Pass', duration: '720 Hours (Full Month)', price: '$69.99', amount: 69.99, badge: 'Pro Month', reqs: '500 req/day', rpm: '60 RPM', desc: 'Full 30-day non-recurring pass for ongoing batch production.' },
];

export default function PublicCheckoutTab({ onLaunchPlayground }) {
  const [selectedPass, setSelectedPass] = useState(PASS_TIERS[0]);
  const [checkoutError, setCheckoutError] = useState('');
  // Keep purchases unavailable until server-side order approval, capture,
  // amount validation and fulfillment are implemented and verified.
  const checkoutAvailable = false;
  const unavailableMessage = 'Purchases are temporarily unavailable. No payment has been started.';
  const handlePayPalV6Checkout = () => {
    setCheckoutError(unavailableMessage);
    return false;
  };
  const handleStripeCheckout = () => {
    setCheckoutError(unavailableMessage);
    return false;
  };

  return (
    <div style={{ padding: '24px', background: '#090d16', color: '#e6edf3', minHeight: '100vh', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: '800', background: 'linear-gradient(90deg, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: '0 0 8px 0' }}>
          Stehouwer AI Compute Passes
        </h1>
        <p style={{ color: '#8b949e', fontSize: '15px', maxWidth: '600px', margin: '0 auto' }}>
          100% Non-Recurring Flexibility Passes — Zero monthly subscriptions, zero hidden fees. 
        </p>
      </div>

      {/* Grid of 7 Flexibility Pass Tiers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', maxWidth: '1200px', margin: '0 auto 40px auto' }}>
        {PASS_TIERS.map(tier => {
          const isSelected = selectedPass.id === tier.id;
          return (
            <div 
              key={tier.id}
              onClick={() => setSelectedPass(tier)}
              style={{
                background: isSelected ? '#161b22' : '#0d1117',
                border: isSelected ? '2px solid #38bdf8' : '1px solid #30363d',
                borderRadius: '12px',
                padding: '20px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                position: 'relative',
                boxShadow: isSelected ? '0 0 20px rgba(56, 189, 248, 0.2)' : 'none'
              }}
            >
              {tier.badge && (
                <span style={{ position: 'absolute', top: '12px', right: '12px', background: 'linear-gradient(90deg, #38bdf8, #818cf8)', color: '#000', fontSize: '10px', fontWeight: '800', padding: '2px 8px', borderRadius: '12px', textTransform: 'uppercase' }}>
                  {tier.badge}
                </span>
              )}
              <h3 style={{ fontSize: '18px', fontWeight: '700', color: '#f0f6fc', margin: '0 0 4px 0' }}>{tier.name}</h3>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#38bdf8', marginBottom: '8px' }}>{tier.price}</div>
              <div style={{ fontSize: '12px', color: '#8b949e', marginBottom: '16px' }}>Duration: <strong>{tier.duration}</strong></div>
              
              <ul style={{ listStyle: 'none', padding: '0', margin: '0 0 16px 0', fontSize: '13px', color: '#c9d1d9', lineHeight: '1.6' }}>
                <li>⚡ {tier.reqs}</li>
                <li>⏱️ {tier.rpm} rate ceiling</li>
                <li>🎨 SDXL Image + Video + Chat</li>
                <li>🔒 Non-recurring (auto-expires)</li>
              </ul>
              
              <p style={{ fontSize: '12px', color: '#8b949e', margin: '0', fontStyle: 'italic' }}>{tier.desc}</p>
            </div>
          );
        })}
      </div>

      {checkoutError && <p role="alert" style={{ textAlign: 'center', color: '#fbbf24' }}>{checkoutError}</p>}

      {/* Checkout Action Box */}
      <div style={{ maxWidth: '600px', margin: '0 auto', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', textAlign: 'center' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700', margin: '0 0 8px 0' }}>Selected: {selectedPass.name} ({selectedPass.price})</h2>
        <p style={{ color: '#8b949e', fontSize: '13px', marginBottom: '20px' }}>
          Purchases are temporarily unavailable while payment confirmation is being verified.
        </p>

        <button
          onClick={handlePayPalV6Checkout}
          disabled={!checkoutAvailable}
          style={{
            width: '100%',
            padding: '14px',
            marginBottom: '12px',
            background: 'linear-gradient(90deg, #0070ba, #003087)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '10px',
            fontSize: '16px',
            fontWeight: '700',
            cursor: checkoutAvailable ? 'pointer' : 'not-allowed',
            boxShadow: '0 4px 14px rgba(0, 112, 186, 0.4)',
            transition: 'transform 0.1s ease'
          }}
        >
          PayPal checkout unavailable
        </button>

        <button
          onClick={handleStripeCheckout}
          disabled={!checkoutAvailable}
          style={{
            width: '100%',
            padding: '14px',
            background: 'linear-gradient(90deg, #635bff, #4238e4)',
            color: '#ffffff',
            border: 'none',
            borderRadius: '10px',
            fontSize: '16px',
            fontWeight: '700',
            cursor: checkoutAvailable ? 'pointer' : 'not-allowed',
            boxShadow: '0 4px 14px rgba(99, 91, 255, 0.4)',
            transition: 'transform 0.1s ease'
          }}
        >
          Stripe checkout unavailable
        </button>
      </div>

      {onLaunchPlayground && (
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <button onClick={onLaunchPlayground} style={{ padding: '10px 18px', background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '8px', cursor: 'pointer' }}>
            Explore Public Playground
          </button>
        </div>
      )}

    </div>
  );
}
