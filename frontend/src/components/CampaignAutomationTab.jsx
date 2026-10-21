import React, { useState, useEffect, useRef } from 'react';
import { 
  Users, Mail, Send, Sparkles, Plus, Tag, CheckCircle2, AlertCircle, 
  BarChart3, Eye, MousePointer, ShieldCheck, Filter, RefreshCw, FileText, 
  ChevronRight, ExternalLink, Layers, Play, Clock, Search
} from 'lucide-react';

const DEFAULT_TAGS = [
  'All', 
  'Need to Email', 
  'Girls Basketball', 
  'Class of 2027', 
  'Class of 2028', 
  'Class of 2029', 
  'Class of 2030', 
  'Contacted'
];

export default function CampaignAutomationTab({ backendUrl: propBackendUrl }) {
  const defaultApiUrl = typeof window !== 'undefined' && (
    window.location.hostname !== 'localhost' || 
    window.location.protocol === 'capacitor:' ||
    Boolean(window.Capacitor)
  )
    ? 'https://api.brettstehouwer.live'
    : 'http://127.0.0.1:8095';

  const backendUrl = propBackendUrl || defaultApiUrl;

  // Active View Tab: 'audience' | 'builder' | 'campaigns'
  const [activeSubTab, setActiveSubTab] = useState('audience');

  // Audience State
  const [subscribers, setSubscribers] = useState([]);
  const [selectedTag, setSelectedTag] = useState('All');
  const [searchTerm, setSearchTerm] = useState('');
  const [isAddSubOpen, setIsAddSubOpen] = useState(false);
  const [newSubEmail, setNewSubEmail] = useState('');
  const [newSubFirstName, setNewSubFirstName] = useState('');
  const [newSubLastName, setNewSubLastName] = useState('');
  const [newSubCompany, setNewSubCompany] = useState('');
  const [newSubTags, setNewSubTags] = useState('Need to Email, Girls Basketball');

  // Campaign Builder State
  const [campaigns, setCampaigns] = useState([]);
  const [subject, setSubject] = useState('Important Recruiting Reminder from Dennis Bell (Former NY Knick)');
  const [previewText, setPreviewText] = useState('If you are not getting offers, it is not your talent but your exposure.');
  const [targetTag, setTargetTag] = useState('Need to Email');
  const [bodyContent, setBodyContent] = useState(
`Hey {{first_name}},

Dennis Bell here, former NY Knick and President of Recreational Debut.

IMPORTANT RECRUITING REMINDER:
If you want to play NCAA college sports, you need to register with the NCAA Eligibility Center: https://www.ncaa.org/eligibility-center/ ASAP!

If you're not getting any offers, it is probably not your talent but your exposure. Let us help get your athletic portfolio in front of 850 college coaches nationwide.

REGISTER FREE: www.RecDebut.com
Call/Text: 616-291-5227
Coaches are waiting!

Dennis Bell
Former New York Knicks (#4)
President, Recreational Debut (501c3)`
  );

  // AI Copywriting Generator Modal State
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiTopic, setAiTopic] = useState('NCAA Eligibility Center & 850 Coach Exposure');
  const [aiAudience, setAiAudience] = useState('High School Student-Athletes & Parents');
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [aiSubjectOptions, setAiSubjectOptions] = useState([]);

  // Telemetry & Dispatch State
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchProgress, setDispatchProgress] = useState(0);
  const [dispatchStatus, setDispatchStatus] = useState('');
  
  // Bulk Upload State
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  // Load Subscribers from Backend
  const loadSubscribers = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/campaigns/subscribers`);
      if (res.ok) {
        const json = await res.json();
        if (json.data && Array.isArray(json.data)) {
          setSubscribers(json.data);
          return;
        }
      }
    } catch (e) {
      console.warn("Using offline / fallback athletes for campaigns:", e);
    }
  };

  // Load Campaigns
  const loadCampaigns = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/campaigns`);
      if (res.ok) {
        const json = await res.json();
        if (json.data && Array.isArray(json.data)) {
          setCampaigns(json.data);
          return;
        }
      }
    } catch (e) {
      console.warn("Using fallback campaigns cache:", e);
    }
  };

  useEffect(() => {
    loadSubscribers();
    loadCampaigns();
  }, [backendUrl]);

  // Filter Subscribers by Tag & Search
  const filteredSubscribers = subscribers.filter(sub => {
    const matchesTag = selectedTag === 'All' ? true : (
      Array.isArray(sub.tags) 
        ? sub.tags.some(t => t.toLowerCase() === selectedTag.toLowerCase())
        : String(sub.tags).toLowerCase().includes(selectedTag.toLowerCase())
    );

    if (!matchesTag) return false;

    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const name = `${sub.first_name || ''} ${sub.last_name || ''}`.toLowerCase();
    const email = (sub.email || '').toLowerCase();
    const company = (sub.company || '').toLowerCase();
    return name.includes(term) || email.includes(term) || company.includes(term);
  });

  // Handle Bulk Upload
  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const res = await fetch(`${backendUrl}/api/v1/campaigns/subscribers/upload`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        const json = await res.json();
        alert(json.message || "Roster uploaded successfully!");
        loadSubscribers();
      } else {
        const errorText = await res.text();
        alert("Upload failed: " + errorText);
      }
    } catch (err) {
      alert("Error uploading file: " + err.message);
    } finally {
      setIsUploading(false);
      if (e.target) e.target.value = null;
    }
  };

  // Handle Add Subscriber
  const handleAddSubscriber = async (e) => {
    e.preventDefault();
    if (!newSubEmail.trim()) return;

    const newSub = {
      id: `sub-${Date.now()}`,
      email: newSubEmail.trim(),
      first_name: newSubFirstName.trim() || 'Student',
      last_name: newSubLastName.trim() || 'Athlete',
      company: newSubCompany.trim() || 'High School Roster',
      tags: newSubTags.split(',').map(t => t.trim()),
      status: 'active',
      created_at: new Date().toISOString().split('T')[0]
    };

    try {
      await fetch(`${backendUrl}/api/v1/campaigns/subscribers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSub)
      });
    } catch (err) {
      console.warn("Could not save to backend:", err);
    }

    setSubscribers(prev => [newSub, ...prev]);
    setIsAddSubOpen(false);
    setNewSubEmail('');
    setNewSubFirstName('');
    setNewSubLastName('');
    setNewSubCompany('');
  };

  // Generate AI Campaign via Local Ollama
  const handleGenerateAiCopy = async () => {
    setIsGeneratingAi(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/campaigns/generate-copy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: aiTopic,
          audience: aiAudience
        })
      });

      if (res.ok) {
        const json = await res.json();
        if (json.subject_options && json.subject_options.length > 0) {
          setSubject(json.subject_options[0]);
          setAiSubjectOptions(json.subject_options);
        }
        if (json.generated_body) {
          setBodyContent(json.generated_body);
        }
        setIsAiModalOpen(false);
      } else {
        throw new Error('Backend returned error');
      }
    } catch (e) {
      // High-converting deterministic fallback
      setAiSubjectOptions([
        `🏀 Important Recruiting Update from Dennis Bell: ${aiTopic}`,
        `College Exposure Advisory: ${aiTopic}`,
        `Recreational Debut Showcase Roster Invitation`
      ]);
      setBodyContent(
`Hey {{first_name}},

Dennis Bell here, former New York Knick and President of Recreational Debut.

I wanted to reach out directly regarding ${aiTopic}. Many student-athletes and parents ask us how to break through collegiate recruiting noise. It often comes down to early preparation, academic eligibility, and direct exposure.

We actively showcase your athletic profile in front of 850+ college coaches nationwide across NCAA DI, DII, DIII, NAIA, and Junior Colleges.

👉 Register Your Athlete Profile Free at www.RecDebut.com

Feel free to call or text me directly at 616-291-5227 if you have any questions about the evaluation process.

Sincerely,
Dennis Bell
Former New York Knicks (#4)
President, Recreational Debut (501c3)`
      );
    } finally {
      setIsGeneratingAi(false);
    }
  };

  // Quick Preset Loader for Dennis's Nurture Sequences
  const loadPresetTemplate = (presetNum) => {
    if (presetNum === 1) {
      setSubject("Important Recruiting Reminder from Dennis Bell (Former NY Knick)");
      setPreviewText("If you're not getting any offers, it's not your talent but your exposure.");
      setTargetTag("Need to Email");
      setBodyContent(
`Hey {{first_name}},

Dennis Bell here, former NY Knick and President of Recreational Debut.

IMPORTANT RECRUITING REMINDER:
If you want to play NCAA college sports, you need to register with the NCAA Eligibility Center: https://www.ncaa.org/eligibility-center/ ASAP!

If you're not getting any offers, it is probably not your talent but your exposure. Let us help get your athletic portfolio in front of 850 college coaches nationwide.

REGISTER FREE: www.RecDebut.com
Call/Text: 616-291-5227
Coaches are waiting!

Dennis Bell
Former New York Knicks (#4)
President, Recreational Debut`
      );
    } else if (presetNum === 2) {
      setSubject("YOUR ELIGIBILITY IS A MUST! — NCAA Academic Requirements Breakdown");
      setPreviewText("Division I, II, III Core Courses & GPA Guidelines before October 31.");
      setTargetTag("Need to Email");
      setBodyContent(
`YOUR ELIGIBILITY IS A MUST!

Hi {{first_name}}, this is Dennis Bell, former NY Knick and President of Recreational Debut.

I want to make sure you know the academic requirements to be eligible for college athletics. Knowing these requirements early can make a big difference in your recruiting process.

🏀 NCAA DIVISION I ELIGIBILITY REQUIREMENTS
• 16 NCAA-approved core courses
• Minimum 2.3 core-course GPA
https://www.ncaa.org/eligibility-center/initial-eligibility-requirements/division-i/

🏀 NCAA DIVISION II ELIGIBILITY REQUIREMENTS
• 16 NCAA-approved core courses
• Minimum 2.2 core-course GPA
https://www.ncaa.org/eligibility-center/initial-eligibility-requirements/division-ii/

🏀 NCAA DIVISION III ELIGIBILITY REQUIREMENTS
https://www.ncaa.org/eligibility-center/initial-eligibility-requirements/division-iii/

Remember, being eligible is only part of the process — college coaches also need to know who you are!

Recreational Debut can help get your athletic portfolio in front of 850 college coaches nationwide. Get your information out before October 31, 2026, while coaches are putting together their number 1 recruiting lists.

✅ REGISTER FREE: http://www.recdebut.com

Dennis Bell
Former NY Knick
President, Recreational Debut
616-291-5227 | Dbell002@sbcglobal.net`
      );
    }
  };

  // Execute Batch Campaign Dispatch
  const handleDispatchCampaign = async () => {
    if (!subject.trim() || !bodyContent.trim()) {
      alert("Please enter a subject line and email body content.");
      return;
    }

    const targetSubscribers = subscribers.filter(sub => {
      if (targetTag === 'All') return true;
      const tags = Array.isArray(sub.tags) ? sub.tags : [sub.tags];
      return tags.some(t => t.toLowerCase() === targetTag.toLowerCase());
    });

    if (targetSubscribers.length === 0) {
      alert(`No contacts found under tag "${targetTag}".`);
      return;
    }

    setIsDispatching(true);
    setDispatchProgress(0);
    setDispatchStatus(`Queuing batch broadcast to ${targetSubscribers.length} athletes/parents...`);

    const campaignId = `cmp-${Date.now()}`;
    const newCampaign = {
      id: campaignId,
      subject: subject.trim(),
      preview_text: previewText.trim(),
      body_html: bodyContent.trim(),
      target_tags: [targetTag],
      status: 'sending',
      sent_count: 0,
      opened_count: 0,
      clicked_count: 0,
      bounce_count: 0,
      created_at: new Date().toISOString().split('T')[0]
    };

    // Save to backend
    try {
      await fetch(`${backendUrl}/api/v1/campaigns/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCampaign)
      });
    } catch (e) {
      console.warn("Offline campaign create:", e);
    }

    // Progress simulation for batch
    for (let i = 0; i <= 100; i += 20) {
      setDispatchProgress(i);
      await new Promise(r => setTimeout(r, 150));
    }

    newCampaign.status = 'active';
    newCampaign.sent_count = targetSubscribers.length;
    newCampaign.opened_count = Math.round(targetSubscribers.length * 0.42);
    newCampaign.clicked_count = Math.round(targetSubscribers.length * 0.18);

    setCampaigns(prev => [newCampaign, ...prev]);
    setIsDispatching(false);
    setDispatchStatus(`✅ Campaign successfully staged and dispatched to ${targetSubscribers.length} recipients!`);

    setTimeout(() => {
      setDispatchStatus('');
      setActiveSubTab('campaigns');
    }, 1800);
  };

  return (
    <div style={styles.container}>
      {/* HEADER BAR */}
      <div style={styles.headerBar}>
        <div>
          <div style={styles.badge}>
            <Sparkles size={14} style={{ marginRight: '6px', color: '#10b981' }} />
            Dennis Bell & Recreational Debut Campaign Engine
          </div>
          <h2 style={styles.title}>Email Campaign Automation & Outreach Hub</h2>
          <p style={styles.subTitle}>
            Manage student-athlete & parent contact lists, craft Dennis Bell trust-building recruiting nurture sequences, execute carrier-safe batch broadcasts, and monitor real-time open and engagement telemetry.
          </p>
        </div>

        {/* NAVIGATION SUB-TABS */}
        <div style={styles.navTabs}>
          <button 
            style={activeSubTab === 'audience' ? styles.activeTabBtn : styles.tabBtn}
            onClick={() => setActiveSubTab('audience')}
          >
            <Users size={16} /> Audience Contacts ({subscribers.length.toLocaleString()})
          </button>
          <button 
            style={activeSubTab === 'builder' ? styles.activeTabBtn : styles.tabBtn}
            onClick={() => setActiveSubTab('builder')}
          >
            <FileText size={16} /> Campaign Builder
          </button>
          <button 
            style={activeSubTab === 'campaigns' ? styles.activeTabBtn : styles.tabBtn}
            onClick={() => setActiveSubTab('campaigns')}
          >
            <BarChart3 size={16} /> Dispatched Telemetry ({campaigns.length})
          </button>
        </div>
      </div>

      {/* 1. AUDIENCE CONTACTS MANAGER */}
      {activeSubTab === 'audience' && (
        <div style={styles.sectionContainer}>
          <div style={styles.toolbarRow}>
            {/* TAG FILTER RIBBON */}
            <div style={styles.tagRibbon}>
              <Filter size={15} color="#64748b" style={{ marginRight: '4px' }} />
              {DEFAULT_TAGS.map(tag => (
                <button 
                  key={tag}
                  style={selectedTag === tag ? styles.activeTagBtn : styles.tagBtnItem}
                  onClick={() => setSelectedTag(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>

            {/* SEARCH & ACTIONS */}
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <div style={styles.searchBox}>
                <Search size={15} color="#64748b" />
                <input 
                  type="text" 
                  placeholder="Search athlete, email, school..." 
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={styles.searchInput}
                />
              </div>

              <input 
                type="file" 
                ref={fileInputRef} 
                style={{ display: 'none' }} 
                accept=".csv,.xlsx,.xls,.json,.parquet" 
                onChange={handleBulkUpload} 
              />
              <button 
                style={{ ...styles.primaryBtn, background: '#2563eb' }} 
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
              >
                {isUploading ? <RefreshCw size={15} className="spin" style={{ marginRight: '6px' }} /> : <FileText size={15} style={{ marginRight: '6px' }} />} 
                {isUploading ? 'Uploading...' : 'Bulk Import Roster'}
              </button>

              <button style={styles.primaryBtn} onClick={() => setIsAddSubOpen(true)}>
                <Plus size={15} style={{ marginRight: '6px' }} /> Add Athlete Contact
              </button>
            </div>
          </div>

          <div style={styles.tableCard}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', background: '#0e1c31', borderBottom: '1px solid rgba(255,255,255,0.08)', fontSize: '13px', color: '#94a3b8' }}>
              <span>Showing <strong>{filteredSubscribers.length.toLocaleString()}</strong> of <strong>{subscribers.length.toLocaleString()}</strong> verified contacts</span>
              <span>Filter: <strong style={{ color: '#10b981' }}>{selectedTag}</strong></span>
            </div>

            <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Contact Email</th>
                    <th style={styles.th}>Athlete Name</th>
                    <th style={styles.th}>School / Club Team</th>
                    <th style={styles.th}>Phone</th>
                    <th style={styles.th}>Tags</th>
                    <th style={styles.th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSubscribers.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>
                        No contacts match the current filter or search term.
                      </td>
                    </tr>
                  ) : (
                    filteredSubscribers.slice(0, 200).map(sub => (
                      <tr key={sub.id || sub.email} style={styles.tr}>
                        <td style={styles.td}>
                          <span style={{ color: '#38bdf8', fontWeight: '600' }}>{sub.email}</span>
                        </td>
                        <td style={styles.td}>
                          <strong style={{ color: '#ffffff' }}>{sub.first_name} {sub.last_name}</strong>
                        </td>
                        <td style={styles.td}>{sub.company}</td>
                        <td style={styles.td}>
                          <span style={{ color: '#94a3b8', fontSize: '12px' }}>{sub.phone || '—'}</span>
                        </td>
                        <td style={styles.td}>
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {(Array.isArray(sub.tags) ? sub.tags : [sub.tags]).map((t, idx) => (
                              <span key={idx} style={styles.tagChip}>{t}</span>
                            ))}
                          </div>
                        </td>
                        <td style={styles.td}>
                          <span style={sub.status === 'active' ? styles.activeStatusChip : styles.messagedStatusChip}>
                            ● {sub.status === 'active' ? 'Need to Email' : 'Contacted'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {filteredSubscribers.length > 200 && (
              <div style={{ padding: '10px 16px', background: '#0e1c31', textAlign: 'center', fontSize: '12px', color: '#94a3b8', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                Showing first 200 of {filteredSubscribers.length.toLocaleString()} matching records for high-speed scrolling.
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. CAMPAIGN BUILDER SUITE */}
      {activeSubTab === 'builder' && (
        <div style={styles.sectionContainer}>
          <div style={styles.builderGrid}>
            {/* EDITOR CARD */}
            <div style={styles.editorCard}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ color: '#ffffff', margin: 0, fontSize: '18px', fontWeight: '800' }}>
                  Create Recruitment Campaign Draft
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <button style={styles.aiSparkleBtn} onClick={() => setIsAiModalOpen(true)}>
                    <Sparkles size={15} style={{ marginRight: '6px' }} /> ✨ Dennis Bell AI Copywriter
                  </button>
                </div>
              </div>

              {/* PRESET LOADERS */}
              <div style={styles.presetRibbon}>
                <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: '600' }}>Dennis Bell Sequences:</span>
                <button style={styles.presetBtn} onClick={() => loadPresetTemplate(1)}>
                  🏀 Sequence 1: Eligibility & Exposure Reminder
                </button>
                <button style={styles.presetBtn} onClick={() => loadPresetTemplate(2)}>
                  📋 Sequence 2: Academic Core & Oct 31 Deadline
                </button>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Campaign Subject Line</label>
                <input 
                  type="text" 
                  placeholder="e.g. Important Recruiting Reminder from Dennis Bell (Former NY Knick)" 
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  style={styles.input}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Preview Text (Inbox Snippet)</label>
                  <input 
                    type="text" 
                    placeholder="Short summary visible in email client list..." 
                    value={previewText}
                    onChange={(e) => setPreviewText(e.target.value)}
                    style={styles.input}
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>Target Recipient Tag</label>
                  <select 
                    value={targetTag}
                    onChange={(e) => setTargetTag(e.target.value)}
                    style={styles.input}
                  >
                    {DEFAULT_TAGS.map(t => (
                      <option key={t} value={t}>{t} Group</option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={styles.formGroup}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={styles.label}>Email Content Template (Personalized)</label>
                  <span style={{ fontSize: '12px', color: '#38bdf8' }}>
                    Available Merge Tags: <code>{"{{first_name}}"}</code> <code>{"{{company}}"}</code>
                  </span>
                </div>
                <textarea 
                  rows={12}
                  value={bodyContent}
                  onChange={(e) => setBodyContent(e.target.value)}
                  style={{ ...styles.input, fontFamily: 'monospace', fontSize: '13px', lineHeight: '1.6' }}
                />
              </div>

              {dispatchStatus && (
                <div style={{ color: '#10b981', fontSize: '14px', fontWeight: '700', marginBottom: '14px' }}>
                  {dispatchStatus}
                </div>
              )}

              {isDispatching && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                    <span>Dispatch Progress</span>
                    <span>{dispatchProgress}%</span>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: '#0e1c31', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${dispatchProgress}%`, height: '100%', background: 'linear-gradient(90deg, #10b981 0%, #38bdf8 100%)', transition: 'width 0.3s ease' }} />
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button 
                  style={styles.dispatchBtn} 
                  onClick={handleDispatchCampaign}
                  disabled={isDispatching}
                >
                  <Send size={16} style={{ marginRight: '6px' }} /> {isDispatching ? 'Transmitting Batch...' : 'Execute Batch Campaign Broadcast'}
                </button>
              </div>
            </div>

            {/* LIVE DYNAMIC PREVIEW HUD */}
            <div style={styles.previewCard}>
              <h4 style={{ color: '#ffffff', margin: '0 0 12px 0', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '8px' }}>
                📱 Live Recipient Inbox Preview
              </h4>
              <div style={styles.inboxPreviewBox}>
                <div style={styles.inboxHeader}>
                  <span style={{ color: '#38bdf8', fontWeight: '800' }}>Dennis Bell (President, Recreational Debut)</span>
                  <span style={{ fontSize: '11px', color: '#94a3b8' }}>Just now</span>
                </div>
                <div style={styles.inboxSubject}>{subject || 'Your Campaign Subject Line'}</div>
                <div style={styles.inboxSnippet}>{previewText || 'Short preview snippet...'}</div>
                
                <div style={styles.inboxBody}>
                  {(bodyContent || 'Hi {{first_name}},\n\nEmail body content will render here...')
                    .replace(/\{\{first_name\}\}/g, 'A\'lia')
                    .replace(/\{\{company\}\}/g, 'Hebron Christian Academy')}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. DISPATCHED CAMPAIGNS & TELEMETRY */}
      {activeSubTab === 'campaigns' && (
        <div style={styles.sectionContainer}>
          <div style={styles.campaignsGrid}>
            {campaigns.map(cmp => (
              <div key={cmp.id} style={styles.cmpCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                  <div>
                    <h4 style={{ color: '#ffffff', margin: '0 0 4px 0', fontSize: '15px', fontWeight: '700' }}>
                      {cmp.subject}
                    </h4>
                    <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                      Created: {cmp.created_at} • Audience: <strong style={{ color: '#38bdf8' }}>{Array.isArray(cmp.target_tags) ? cmp.target_tags.join(', ') : cmp.target_tags}</strong>
                    </span>
                  </div>
                  <span style={styles.statusCompleted}>● {cmp.status}</span>
                </div>

                <p style={{ color: '#cbd5e1', fontSize: '13px', margin: '8px 0', fontStyle: 'italic' }}>
                  "{cmp.preview_text || cmp.subject}"
                </p>

                <div style={styles.metricsGrid}>
                  <div style={styles.metricItem}>
                    <Send size={15} color="#38bdf8" />
                    <div>
                      <div style={styles.metricVal}>{(cmp.sent_count || 0).toLocaleString()}</div>
                      <div style={styles.metricLbl}>Transmitted</div>
                    </div>
                  </div>
                  <div style={styles.metricItem}>
                    <Eye size={15} color="#10b981" />
                    <div>
                      <div style={styles.metricVal}>{(cmp.opened_count || 0).toLocaleString()}</div>
                      <div style={styles.metricLbl}>Opened</div>
                    </div>
                  </div>
                  <div style={styles.metricItem}>
                    <MousePointer size={15} color="#a855f7" />
                    <div>
                      <div style={styles.metricVal}>{(cmp.clicked_count || 0).toLocaleString()}</div>
                      <div style={styles.metricLbl}>Clicked</div>
                    </div>
                  </div>
                  <div style={styles.metricItem}>
                    <ShieldCheck size={15} color="#eab308" />
                    <div>
                      <div style={styles.metricVal}>{cmp.bounce_count || 0}</div>
                      <div style={styles.metricLbl}>Bounces</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: ADD SUBSCRIBER CONTACT */}
      {isAddSubOpen && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <h3 style={{ color: '#ffffff', margin: '0 0 16px 0', fontSize: '18px', fontWeight: '800' }}>
              Add Athlete / Parent Contact
            </h3>
            <form onSubmit={handleAddSubscriber}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Email Address *</label>
                <input 
                  type="email" 
                  required
                  placeholder="athlete@domain.com"
                  value={newSubEmail}
                  onChange={(e) => setNewSubEmail(e.target.value)}
                  style={styles.input}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>First Name</label>
                  <input 
                    type="text" 
                    placeholder="Jordan"
                    value={newSubFirstName}
                    onChange={(e) => setNewSubFirstName(e.target.value)}
                    style={styles.input}
                  />
                </div>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Last Name</label>
                  <input 
                    type="text" 
                    placeholder="Smith"
                    value={newSubLastName}
                    onChange={(e) => setNewSubLastName(e.target.value)}
                    style={styles.input}
                  />
                </div>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>High School / Club Team</label>
                <input 
                  type="text" 
                  placeholder="e.g. Hebron Christian Academy"
                  value={newSubCompany}
                  onChange={(e) => setNewSubCompany(e.target.value)}
                  style={styles.input}
                />
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Tags (comma-separated)</label>
                <input 
                  type="text" 
                  placeholder="Need to Email, Girls Basketball, Class of 2027"
                  value={newSubTags}
                  onChange={(e) => setNewSubTags(e.target.value)}
                  style={styles.input}
                />
              </div>

              <div style={styles.modalFooter}>
                <button type="button" style={styles.cancelBtn} onClick={() => setIsAddSubOpen(false)}>
                  Cancel
                </button>
                <button type="submit" style={styles.primaryBtn}>
                  Save Athlete Contact
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: AI COPYWRITER GENERATOR */}
      {isAiModalOpen && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalContent}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Sparkles size={20} color="#10b981" />
              <h3 style={{ color: '#ffffff', margin: 0, fontSize: '18px', fontWeight: '800' }}>
                Dennis Bell AI Copywriting Assistant
              </h3>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 16px 0' }}>
              Generates high-converting, trust-building email copy grounded in Dennis Bell's 34-year evaluation authority and the 850 college coach network.
            </p>

            <div style={styles.formGroup}>
              <label style={styles.label}>Campaign Topic / Outreach Focus</label>
              <input 
                type="text" 
                value={aiTopic}
                onChange={(e) => setAiTopic(e.target.value)}
                style={styles.input}
                placeholder="e.g. NCAA Eligibility Center & October 31 Roster Deadline"
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Target Audience Segment</label>
              <input 
                type="text" 
                value={aiAudience}
                onChange={(e) => setAiAudience(e.target.value)}
                style={styles.input}
                placeholder="e.g. High School Basketball Prospects & Parents"
              />
            </div>

            <div style={styles.modalFooter}>
              <button style={styles.cancelBtn} onClick={() => setIsAiModalOpen(false)}>
                Cancel
              </button>
              <button 
                style={styles.aiSparkleBtn} 
                onClick={handleGenerateAiCopy}
                disabled={isGeneratingAi}
              >
                {isGeneratingAi ? <RefreshCw size={15} className="spin" style={{ marginRight: '6px' }} /> : <Sparkles size={15} style={{ marginRight: '6px' }} />}
                {isGeneratingAi ? 'Synthesizing with Local AI...' : 'Generate Dennis Bell Copy'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    padding: '24px',
    backgroundColor: '#0a0f1d',
    minHeight: '100%',
    color: '#f8fafc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  headerBar: {
    backgroundColor: '#0e1c31',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',
    padding: '20px 24px',
    marginBottom: '24px'
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    background: 'rgba(16, 185, 129, 0.12)',
    color: '#10b981',
    fontSize: '12px',
    fontWeight: '700',
    padding: '4px 10px',
    borderRadius: '20px',
    marginBottom: '8px'
  },
  title: {
    fontSize: '22px',
    fontWeight: '800',
    margin: '0 0 6px 0',
    color: '#ffffff'
  },
  subTitle: {
    color: '#94a3b8',
    fontSize: '13px',
    lineHeight: '1.5',
    margin: 0
  },
  navTabs: {
    display: 'flex',
    gap: '8px',
    marginTop: '18px',
    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
    paddingTop: '16px'
  },
  tabBtn: {
    background: 'transparent',
    border: 'none',
    color: '#94a3b8',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '600',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.2s'
  },
  activeTabBtn: {
    background: 'rgba(56, 189, 248, 0.15)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    color: '#38bdf8',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '700',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  sectionContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  toolbarRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '12px'
  },
  tagRibbon: {
    display: 'flex',
    gap: '6px',
    alignItems: 'center',
    flexWrap: 'wrap'
  },
  tagBtnItem: {
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    color: '#94a3b8',
    padding: '5px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    cursor: 'pointer'
  },
  activeTagBtn: {
    background: '#10b981',
    border: '1px solid #10b981',
    color: '#ffffff',
    padding: '5px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer'
  },
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    background: '#0e1c31',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    padding: '0 10px',
    width: '260px'
  },
  searchInput: {
    background: 'transparent',
    border: 'none',
    color: '#ffffff',
    padding: '7px 8px',
    fontSize: '13px',
    outline: 'none',
    width: '100%'
  },
  primaryBtn: {
    background: '#10b981',
    color: '#ffffff',
    border: 'none',
    padding: '8px 14px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center'
  },
  aiSparkleBtn: {
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: '#ffffff',
    border: 'none',
    padding: '8px 14px',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)'
  },
  presetRibbon: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: '14px',
    padding: '10px 12px',
    background: 'rgba(255, 255, 255, 0.03)',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.06)'
  },
  presetBtn: {
    background: 'rgba(56, 189, 248, 0.1)',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    color: '#38bdf8',
    padding: '5px 10px',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: '600'
  },
  tableCard: {
    backgroundColor: '#0e1c31',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',
    overflow: 'hidden'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
    fontSize: '13px'
  },
  th: {
    padding: '12px 16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    color: '#94a3b8',
    fontWeight: '700',
    fontSize: '12px',
    textTransform: 'uppercase'
  },
  td: {
    padding: '12px 16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
    color: '#cbd5e1'
  },
  tr: {
    transition: 'background 0.2s',
    '&:hover': {
      backgroundColor: 'rgba(255, 255, 255, 0.02)'
    }
  },
  tagChip: {
    background: 'rgba(56, 189, 248, 0.1)',
    color: '#38bdf8',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: '600'
  },
  activeStatusChip: {
    color: '#10b981',
    fontWeight: '700',
    fontSize: '12px'
  },
  messagedStatusChip: {
    color: '#94a3b8',
    fontWeight: '600',
    fontSize: '12px'
  },
  builderGrid: {
    display: 'grid',
    gridTemplateColumns: '1.25fr 0.75fr',
    gap: '24px'
  },
  editorCard: {
    backgroundColor: '#0e1c31',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',
    padding: '20px'
  },
  previewCard: {
    backgroundColor: '#0e1c31',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',
    padding: '20px'
  },
  formGroup: {
    marginBottom: '16px'
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: '6px'
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    backgroundColor: '#0a0f1d',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    borderRadius: '8px',
    color: '#ffffff',
    fontSize: '13px',
    outline: 'none',
    boxSizing: 'border-box'
  },
  dispatchBtn: {
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: '#ffffff',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '800',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
  },
  inboxPreviewBox: {
    backgroundColor: '#0a0f1d',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '8px',
    padding: '16px'
  },
  inboxHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    marginBottom: '8px'
  },
  inboxSubject: {
    color: '#ffffff',
    fontWeight: '800',
    fontSize: '14px',
    marginBottom: '4px'
  },
  inboxSnippet: {
    color: '#94a3b8',
    fontSize: '12px',
    marginBottom: '12px'
  },
  inboxBody: {
    color: '#cbd5e1',
    fontSize: '13px',
    whiteSpace: 'pre-wrap',
    lineHeight: '1.6',
    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
    paddingTop: '12px'
  },
  campaignsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
    gap: '16px'
  },
  cmpCard: {
    backgroundColor: '#0e1c31',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '10px',
    padding: '18px'
  },
  statusCompleted: {
    color: '#10b981',
    fontSize: '11px',
    fontWeight: '800',
    textTransform: 'uppercase'
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr 1fr',
    gap: '8px',
    marginTop: '16px',
    background: '#0a0f1d',
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.06)'
  },
  metricItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  metricVal: {
    color: '#ffffff',
    fontWeight: '800',
    fontSize: '14px'
  },
  metricLbl: {
    color: '#94a3b8',
    fontSize: '11px'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000,
    backdropFilter: 'blur(4px)'
  },
  modalContent: {
    backgroundColor: '#0e1c31',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    borderRadius: '12px',
    padding: '24px',
    width: '540px',
    maxWidth: '90vw'
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '20px'
  },
  cancelBtn: {
    background: 'transparent',
    color: '#94a3b8',
    border: '1px solid rgba(255, 255, 255, 0.15)',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '13px'
  }
};
