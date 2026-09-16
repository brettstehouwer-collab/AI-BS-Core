import React, { useState } from 'react';

export default function CompetitorRadar({ backendUrl }) {
  const [isScanning, setIsScanning] = useState(false);
  const [reviews, setReviews] = useState([]);

  const handleScan = () => {
    setIsScanning(true);
    // Simulate scraping 1-star reviews from Safelite regional hubs
    setTimeout(() => {
      setReviews([
        { id: 1, location: "Safelite - Patterson Ave SE (Kent County)", rating: 1, text: "They completely botched the ADAS calibration. My lane assist hasn't worked since they left, and they told me it wasn't their problem. AVOID.", date: "2 days ago", zip: "49512", action: "Targeted LSA Ad" },
        { id: 2, location: "Safelite - 28th St SW (Wyoming)", rating: 2, text: "Mobile tech was 4 hours late. When he got here, he had the wrong windshield for my Honda. Had to wait another week with a shattered window.", date: "5 days ago", zip: "49509", action: "Mobile Rapid Response Mailer" },
        { id: 3, location: "Auto Glass Now - Plainfield Ave", rating: 1, text: "Scratched the paint on my hood while installing. Denied it. The cheap glass they used has a massive distortion wave in the passenger side.", date: "1 week ago", zip: "49525", action: "OEM Quality Educational Ad" }
      ]);
      setIsScanning(false);
    }, 2000);
  };

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #30363d', paddingBottom: '15px' }}>
        <div>
          <h2 style={{ color: '#ff7b72', margin: '0 0 5px 0' }}>"Burned Customer" Competitor Radar</h2>
          <p style={{ margin: 0, color: '#8b949e' }}>Geographically filtering recent 1-star & 2-star reviews from massive corporate chains in West Michigan.</p>
        </div>
        <button 
          onClick={handleScan}
          disabled={isScanning}
          style={{
            background: isScanning ? '#1f6feb' : '#d29922',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '6px',
            fontWeight: 'bold',
            cursor: isScanning ? 'wait' : 'pointer'
          }}
        >
          {isScanning ? 'Scraping Google Maps...' : 'Deploy Radar Scan'}
        </button>
      </div>

      <div style={{ marginTop: '20px' }}>
        {reviews.length === 0 && !isScanning ? (
          <div style={{ textAlign: 'center', padding: '50px', color: '#8b949e', background: '#161b22', borderRadius: '8px', border: '1px dashed #30363d' }}>
            Click "Deploy Radar Scan" to locate disgruntled customers at regional competitor hubs.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {reviews.map(review => (
              <div key={review.id} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '15px', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span style={{ fontWeight: 'bold', color: '#58a6ff' }}>{review.location}</span>
                  <span style={{ color: '#8b949e', fontSize: '12px' }}>{review.date} • Zip: {review.zip}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '10px' }}>
                  <span style={{ color: '#ff7b72', fontWeight: 'bold' }}>Rating: {review.rating}/5</span>
                  <span style={{ color: '#ff7b72' }}>★☆☆☆☆</span>
                </div>
                <p style={{ margin: '0 0 15px 0', fontStyle: 'italic', color: '#c9d1d9' }}>"{review.text}"</p>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button style={{ background: '#1f6feb', color: 'white', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
                    Generate {review.action}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
