import React, { useState } from 'react';

export default function DriverOutreach({ backendUrl }) {
  const [selectedSchool, setSelectedSchool] = useState('');
  const [emailDraft, setEmailDraft] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const schools = [
    { id: 'century_wyoming', name: 'Century Driving School (Wyoming)', address: '1008 28th St. SW, Wyoming, MI 49509', type: 'Regional' },
    { id: 'buckle_in', name: 'Buckle In Driving Academy', address: '3901 Chicago Dr SW, Grandville, MI 49418', type: 'Local Family' },
    { id: 'macatawa_jenison', name: 'Macatawa Driving School (Jenison)', address: '7726 Graceland Drive, Jenison, MI 49428', type: 'School-Hosted' },
    { id: 'integrity', name: 'Integrity Driver Testing', address: '5710 Balsam Dr, Hudsonville, MI 49426', type: 'Testing Center' }
  ];

  const handleGeneratePitch = () => {
    setIsGenerating(true);
    // Simulate AI generation for B2B partnership pitch
    setTimeout(() => {
      const school = schools.find(s => s.id === selectedSchool);
      setEmailDraft(`Subject: Ensuring Safety for Your New Drivers at ${school.name}\n\nHi [Name],\n\nAs a local business here in West Michigan, we know that ${school.name} puts driver safety above all else.\n\nAt Action Glass, we specialize in OEM-quality windshield replacement and ADAS (Advanced Driver Assistance Systems) camera recalibration. Many parents don't realize that if a new driver cracks a windshield, replacing the glass without properly recalibrating the lane-assist cameras can be incredibly dangerous.\n\nWe'd love to partner with you to offer an exclusive "New Driver Safety Discount" for your graduating students. We handle the insurance ($0 out of pocket for them) and ensure their safety systems are 100% calibrated.\n\nCould we drop off some partnership flyers at your ${school.address} location next week?\n\nBest,\nAction Glass Team\n(616) 669-8888`);
      setIsGenerating(false);
    }, 1500);
  };

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ color: '#8957e5', margin: '0 0 15px 0', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
        New Driver Outreach Campaigner
      </h2>
      <p>Target the most accident-prone demographic (new 16-year-old drivers) by building direct partnerships with local driving schools in the Wyoming, Grandville, Jenison, and Hudsonville corridors.</p>

      <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
        {/* School Database */}
        <div style={{ flex: 1, background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '15px' }}>
          <h3 style={{ margin: '0 0 15px 0' }}>Local Driving Academies CRM</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {schools.map(school => (
              <div 
                key={school.id} 
                onClick={() => setSelectedSchool(school.id)}
                style={{ 
                  padding: '12px', 
                  background: selectedSchool === school.id ? '#1f6feb' : '#0d1117', 
                  border: '1px solid #30363d', 
                  borderRadius: '6px', 
                  cursor: 'pointer',
                  transition: '0.2s'
                }}
              >
                <div style={{ fontWeight: 'bold', color: 'white' }}>{school.name}</div>
                <div style={{ fontSize: '12px', color: '#c9d1d9', marginTop: '4px' }}>{school.address}</div>
                <div style={{ fontSize: '10px', background: '#30363d', padding: '2px 6px', borderRadius: '10px', display: 'inline-block', marginTop: '8px' }}>
                  {school.type}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Pitch Generator */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '15px', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h3 style={{ margin: 0 }}>AI Partnership Pitch</h3>
              <button 
                onClick={handleGeneratePitch}
                disabled={!selectedSchool || isGenerating}
                style={{
                  background: '#238636', color: 'white', border: 'none', padding: '6px 12px', borderRadius: '4px',
                  cursor: (!selectedSchool || isGenerating) ? 'not-allowed' : 'pointer',
                  opacity: (!selectedSchool || isGenerating) ? 0.5 : 1
                }}
              >
                {isGenerating ? 'Drafting...' : 'Generate B2B Email'}
              </button>
            </div>
            
            <textarea 
              readOnly
              value={emailDraft}
              placeholder={selectedSchool ? "Click 'Generate B2B Email' to draft a targeted pitch..." : "Select a driving school from the CRM first..."}
              style={{
                flex: 1, background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: '4px', padding: '15px', resize: 'none', fontFamily: 'sans-serif', fontSize: '14px', lineHeight: '1.5'
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
