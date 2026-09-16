import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';

export default function AutomatedClientSchedulerTab({ backendUrl }) {
  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;

  // Client Profiles State
  const [clients, setClients] = useState([]);
  const [selectedClientName, setSelectedClientName] = useState('Stehouwer Publishing');
  const [activeClientProfile, setActiveClientProfile] = useState({
    name: 'Stehouwer Publishing',
    industry: 'Book Publishing & Literary Media',
    website: 'https://stehouwer-publishing.com',
    target_audience: 'Authors, Readers & Book Buyers',
    brand_voice: 'Professional, Inspiring, Authoritative',
    preferred_channels: 'Twitter, LinkedIn, Facebook, Email Newsletter',
    contact_email: 'contact@stehouwer-publishing.com'
  });

  // Client Email Ingestion State
  const [emailSubject, setEmailSubject] = useState('Weekly Book Launch & Publishing Push');
  const [emailSender, setEmailSender] = useState('julie@stehouwer-publishing.com');
  const [emailBody, setEmailBody] = useState('Hi Brett, for this week we need 3 posts promoting our new fall book releases and author manuscript submission drive.');
  const [isIngestingEmail, setIsIngestingEmail] = useState(false);

  // Weekly Schedule State
  const [weeklySchedule, setWeeklySchedule] = useState([]);
  const [isGeneratingSchedule, setIsGeneratingSchedule] = useState(false);

  // Stehouwer Publishing Promo Templates
  const [selectedPromoTemplate, setSelectedPromoTemplate] = useState('book_release');

  // Load clients on mount
  const fetchClients = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/scheduler/clients`);
      if (res.ok) {
        const data = await res.json();
        if (data.clients && data.clients.length > 0) {
          setClients(data.clients);
          const found = data.clients.find(c => c.name === selectedClientName);
          if (found) setActiveClientProfile(found);
        }
      }
    } catch (e) {
      console.warn('Failed to fetch clients:', e);
    }
  };

  const fetchWeeklyQueue = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/scheduler/queue?client_name=${encodeURIComponent(selectedClientName)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.posts) setWeeklySchedule(data.posts);
      }
    } catch (e) {
      console.warn('Failed to fetch queue:', e);
    }
  };

  useEffect(() => {
    fetchClients();
    fetchWeeklyQueue();
  }, [selectedClientName]);

  const handleSelectClient = (name) => {
    setSelectedClientName(name);
    const found = clients.find(c => c.name === name);
    if (found) {
      setActiveClientProfile(found);
      setEmailSender(found.contact_email || 'client@example.com');
    }
  };

  const handleSaveClientProfile = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/scheduler/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeClientProfile)
      });
      const data = await res.json();
      if (data.status === 'success') {
        alert(`Client Profile '${activeClientProfile.name}' saved successfully!`);
        fetchClients();
      }
    } catch (e) {
      alert('Error saving client profile: ' + e.message);
    }
  };

  const handleIngestEmailAndGenerate = async () => {
    setIsIngestingEmail(true);
    try {
      // 1. Ingest Email Request
      await fetch(`${apiHost}/v1/scheduler/ingest-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: selectedClientName,
          sender_email: emailSender,
          subject: emailSubject,
          raw_request_text: emailBody
        })
      });

      // 2. Generate Weekly 7-Day Content Schedule
      setIsGeneratingSchedule(true);
      const resSched = await fetch(`${apiHost}/v1/scheduler/generate-weekly-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: selectedClientName,
          custom_instructions: `${emailSubject}: ${emailBody}`
        })
      });

      const dataSched = await resSched.json();
      if (dataSched.schedule) {
        setWeeklySchedule(dataSched.schedule);
        alert(`Weekly schedule generated for ${selectedClientName} (${dataSched.schedule_count} daily posts queued)!`);
      }
    } catch (e) {
      alert('Email Ingestion & Schedule Generation Error: ' + e.message);
    } finally {
      setIsIngestingEmail(false);
      setIsGeneratingSchedule(false);
    }
  };

  const handleTriggerPromoTemplate = async (templateType) => {
    let promoSubject = "";
    let promoBody = "";

    if (templateType === 'book_release') {
      promoSubject = "Stehouwer Publishing - New Fall Book Release Spotlight";
      promoBody = "Promote new fall book releases, author interviews, and distribution network for Stehouwer Publishing.";
    } else if (templateType === 'author_submission') {
      promoSubject = "Stehouwer Publishing - Manuscript Submissions Open";
      promoBody = "Call for author manuscript submissions. Free publishing evaluation and global distribution.";
    } else {
      promoSubject = "AI-BS Sovereign Cloud - RTX 4090 GPU Compute Service";
      promoBody = "Promote 44.1kHz RVQ Neural Audio, SDXL visual generation, and commercial developer API passkeys.";
    }

    setEmailSubject(promoSubject);
    setEmailBody(promoBody);
    handleSelectClient(templateType === 'aibs_gpu' ? 'AI-BS Sovereign Cloud' : 'Stehouwer Publishing');
  };

  return (
    <div style={{ padding: '24px', color: '#e6edf3', height: '100%', overflowY: 'auto', background: '#090d16', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Brand Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: '800', margin: 0, color: '#38bdf8' }}>
            📅 Automated Client Content Scheduler & Stehouwer Publishing Suite
          </h1>
          <p style={{ fontSize: '13px', color: '#8b949e', margin: '4px 0 0 0' }}>
            Weekly Social Media Automation, Client Email Request Ingestion & Stehouwer Publishing Advertising Campaigns
          </p>
        </div>

        <button
          onClick={fetchWeeklyQueue}
          style={{ padding: '8px 16px', background: '#1f6feb', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '13px', cursor: 'pointer' }}
        >
          ⚡ Refresh Queue
        </button>
      </div>

      {/* SECTION 1: CLIENT SELECTOR & PROFILE EDITOR */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 4px 0', color: '#f0f6fc' }}>👥 Client Profile Selection</h2>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
              Select an existing client to auto-populate brand voice, channels, and audience profile.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <select
              value={selectedClientName}
              onChange={(e) => handleSelectClient(e.target.value)}
              style={{ padding: '8px 16px', background: '#0d1117', border: '1px solid #38bdf8', borderRadius: '6px', color: '#38bdf8', fontWeight: '700', fontSize: '13px' }}
            >
              {clients.length === 0 ? (
                <option value="Stehouwer Publishing">Stehouwer Publishing</option>
              ) : (
                clients.map(c => (
                  <option key={c.id || c.name} value={c.name}>{c.name}</option>
                ))
              )}
            </select>

            <button
              onClick={() => {
                const newName = prompt('Enter New Client Business Name:');
                if (newName) {
                  const newProfile = {
                    name: newName,
                    industry: 'General Commercial',
                    website: 'https://example.com',
                    target_audience: 'Local Customers & Clients',
                    brand_voice: 'Professional, Engaging',
                    preferred_channels: 'Twitter, LinkedIn, Facebook, Instagram',
                    contact_email: `contact@${newName.toLowerCase().replace(/[^a-z]/g, '')}.com`
                  };
                  setActiveClientProfile(newProfile);
                  setSelectedClientName(newName);
                }
              }}
              style={{ padding: '8px 14px', background: '#238636', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '12px', cursor: 'pointer' }}
            >
              ➕ Add New Client
            </button>
          </div>
        </div>

        {/* Client Business Profile Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Business Name:</label>
            <input
              type="text"
              value={activeClientProfile.name}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, name: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Industry:</label>
            <input
              type="text"
              value={activeClientProfile.industry}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, industry: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Website URL:</label>
            <input
              type="text"
              value={activeClientProfile.website}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, website: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#38bdf8', fontSize: '12px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Brand Voice / Tone:</label>
            <input
              type="text"
              value={activeClientProfile.brand_voice}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, brand_voice: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
            <button
              onClick={handleSaveClientProfile}
              style={{ padding: '6px 16px', background: '#1f6feb', color: '#ffffff', border: 'none', borderRadius: '4px', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
            >
              💾 Save Client Profile Changes
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 2: CLIENT EMAIL INGESTION & STEHOUWER PROMO SUITE */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        
        {/* Email Ingestion Box */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 6px 0', color: '#38bdf8' }}>📩 Ingest Client Email & Request Notes</h2>
          <p style={{ fontSize: '12px', color: '#8b949e', margin: '0 0 14px 0' }}>
            Paste incoming client email instructions to automatically build and queue their weekly posts.
          </p>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Sender Email:</label>
            <input
              type="text"
              value={emailSender}
              onChange={(e) => setEmailSender(e.target.value)}
              style={{ width: '100%', padding: '8px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Email Subject:</label>
            <input
              type="text"
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
              style={{ width: '100%', padding: '8px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Client Request Text / Notes:</label>
            <textarea
              rows={4}
              value={emailBody}
              onChange={(e) => setEmailBody(e.target.value)}
              style={{ width: '100%', padding: '8px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '12px', fontFamily: 'sans-serif' }}
            />
          </div>

          <button
            onClick={handleIngestEmailAndGenerate}
            disabled={isIngestingEmail || isGeneratingSchedule}
            style={{ width: '100%', padding: '12px', background: 'linear-gradient(90deg, #1f6feb, #38bdf8)', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer' }}
          >
            {isIngestingEmail || isGeneratingSchedule ? '🤖 Synthesizing 7-Day Schedule...' : '⚡ Ingest & Auto-Generate 7-Day Posts'}
          </button>
        </div>

        {/* Stehouwer Publishing Promotional Campaign Suite */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 6px 0', color: '#a78bfa' }}>📢 Stehouwer Publishing Promotional Suite</h2>
          <p style={{ fontSize: '12px', color: '#8b949e', margin: '0 0 14px 0' }}>
            1-Click automated campaign generators for book releases, manuscript calls, and AI-BS Cloud.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              onClick={() => handleTriggerPromoTemplate('book_release')}
              style={{ padding: '12px', background: '#0d1117', border: '1px solid #8957e5', borderRadius: '8px', color: '#e6edf3', textAlign: 'left', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#a78bfa' }}>📚 Fall Book Release & Author Spotlight</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Auto-generates weekly spotlights for new book catalog releases.</div>
            </button>

            <button
              onClick={() => handleTriggerPromoTemplate('author_submission')}
              style={{ padding: '12px', background: '#0d1117', border: '1px solid #38bdf8', borderRadius: '8px', color: '#e6edf3', textAlign: 'left', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8' }}>✍️ Author Manuscript Submissions Drive</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Call for indie authors looking for formatting and global publishing.</div>
            </button>

            <button
              onClick={() => handleTriggerPromoTemplate('aibs_gpu')}
              style={{ padding: '12px', background: '#0d1117', border: '1px solid #238636', borderRadius: '8px', color: '#e6edf3', textAlign: 'left', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#4ade80' }}>⚡ AI-BS Sovereign GPU Cloud Promotion</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Promote RTX 4090 neural audio, SDXL, and developer passkey APIs.</div>
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 3: WEEKLY 7-DAY SCHEDULE QUEUE DISPLAY */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 4px 0', color: '#f0f6fc' }}>
              📆 Weekly Content Queue for {selectedClientName} ({weeklySchedule.length} Posts)
            </h2>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
              Automated 7-day schedule with platform-specific formatting and optimized posting timestamps.
            </p>
          </div>
        </div>

        {weeklySchedule.length === 0 ? (
          <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '30px', textAlign: 'center', color: '#8b949e', fontSize: '13px' }}>
            No scheduled posts for {selectedClientName}. Click "Ingest & Auto-Generate 7-Day Posts" above to build this week's queue!
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {weeklySchedule.map((post, idx) => (
              <div key={post.id || idx} style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '800', color: '#38bdf8' }}>{post.scheduled_day} ({post.scheduled_time})</span>
                    <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '700', background: '#1f6feb', color: '#ffffff' }}>
                      {post.platform}
                    </span>
                  </div>

                  <div style={{ fontSize: '13px', fontWeight: '700', color: '#f0f6fc', marginBottom: '8px' }}>
                    {post.post_topic}
                  </div>

                  <div style={{ fontSize: '12px', color: '#8b949e', background: '#161b22', padding: '10px', borderRadius: '6px', border: '1px solid #21262d', whiteSpace: 'pre-wrap', lineHeight: '1.4', marginBottom: '12px' }}>
                    {post.post_copy}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #21262d', paddingTop: '10px' }}>
                  <span style={{ fontSize: '11px', color: '#238636', fontWeight: '700' }}>✓ {post.status}</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(post.post_copy);
                      alert('Post copy copied to clipboard!');
                    }}
                    style={{ background: 'none', border: '1px solid #30363d', borderRadius: '4px', color: '#38bdf8', padding: '4px 10px', fontSize: '11px', cursor: 'pointer' }}
                  >
                    📋 Copy Text
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
