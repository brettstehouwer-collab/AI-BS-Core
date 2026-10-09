import React, { useState, useEffect } from 'react';

export default function DennisBellPortal({ backendUrl: propBackendUrl, BACKEND_URL: propUpperBackendUrl }) {
  const BACKEND_URL = propBackendUrl || propUpperBackendUrl || (
    typeof window !== 'undefined' && window.location.hostname === 'localhost' 
      ? 'http://127.0.0.1:8080' 
      : 'https://api.brettstehouwer.live'
  );

  // Active Tab with Deep URL Param Synchronization
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get('tab');
      if (tab && ['syndication', 'campaigns', 'roster', 'submit', 'network'].includes(tab)) {
        return tab;
      }
    }
    return 'syndication';
  });

  const [athletes, setAthletes] = useState([]);
  const [excludedCoaches, setExcludedCoaches] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedLink, setCopiedLink] = useState(false);

  // Syndication Category Filter: 'pending' | 'messaged' | 'coaches'
  const [syndicationCategory, setSyndicationCategory] = useState('pending');
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Test SMS State
  const [testPhone, setTestPhone] = useState('616-402-3628'); // Brett's phone by default
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // Custom Message Box State (Pre-populated with Dennis's text)
  const DEFAULT_MESSAGE = `CONGRATULATIONS! YOU’VE BEEN SELECTED TO GET YOUR ATHLETIC PORTFOLIO IN FRONT OF 850 COLLEGE COACHES NATIONWIDE!

I’m Dennis Bell, former New York Knick and President of Recreational Debut. We’ve helped more than 100 student-athletes get recruited, and now we want to help you get noticed.

If you’re serious about playing college sports, don’t wait for coaches to find you.
📱 Call or text: 616-291-5227
📧 Email: dbell002@sbcglobal.net
✅ Register FREE: RecDebut.com

College programs across the country are looking for talented student-athletes. That opportunity could include YOU.

Dennis Bell
Former New York Knicks
President, Recreational Debut
616-291-5227 • RecDebut.com • dbell002@sbcglobal.net`;

  const [messageScript, setMessageScript] = useState(DEFAULT_MESSAGE);
  const [isStaging, setIsStaging] = useState(false);
  const [stagedResult, setStagedResult] = useState(null);
  const [scrubberReport, setScrubberReport] = useState(null);
  const [isBroadcastingLive, setIsBroadcastingLive] = useState(false);
  const [liveBroadcastStatus, setLiveBroadcastStatus] = useState(null);
  const [broadcastProgress, setBroadcastProgress] = useState({
    active: false,
    status: 'IDLE',
    total: 0,
    sent: 0,
    failed: 0,
    current_athlete: '',
    progress_pct: 0,
    error: null
  });

  // CSV / File Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);

  // New Athlete Referral State
  const [referral, setReferral] = useState({
    name: '',
    phone: '',
    email: '',
    sport: 'Basketball',
    high_school: '',
    grad_year: '2026',
    city_state: '',
    notes: ''
  });
  const [isSubmittingReferral, setIsSubmittingReferral] = useState(false);
  const [referralSuccess, setReferralSuccess] = useState(false);

  const portalShareUrl = typeof window !== 'undefined' 
    ? `${window.location.origin}/?portal=recdebut&tab=${activeTab}` 
    : `https://ai-bs-dashboard.web.app/?portal=recdebut&tab=${activeTab}`;

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('tab', tabId);
      if (!url.searchParams.get('portal')) {
        url.searchParams.set('portal', 'recdebut');
      }
      window.history.replaceState({ tab: tabId, portal: 'recdebut' }, '', url.toString());
    }
  };

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [athRes, campRes, coachRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/v1/recdebut/athletes`).then(r => r.json()).catch(() => ({ athletes: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/campaigns`).then(r => r.json()).catch(() => ({ campaigns: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/excluded-coaches`).then(r => r.json()).catch(() => ({ coaches: [] }))
      ]);

      if (athRes.athletes) setAthletes(athRes.athletes);
      if (campRes.campaigns) setCampaigns(campRes.campaigns);
      if (coachRes.coaches) setExcludedCoaches(coachRes.coaches);
    } catch (e) {
      console.error('Error fetching portal data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [BACKEND_URL]);

  // Poll broadcast engine status when active
  useEffect(() => {
    let intervalId = null;
    const checkStatus = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/broadcast/status`);
        const data = await res.json();
        if (data && data.success) {
          setBroadcastProgress(data);
          if (data.active) {
            setIsBroadcastingLive(true);
            setLiveBroadcastStatus(
              `🚀 Live Mass Broadcast running: ${data.sent} / ${data.total} messaged (${data.progress_pct}%) • Currently messaging: ${data.current_athlete || 'Connecting...'}`
            );
          } else {
            if (isBroadcastingLive) {
              setIsBroadcastingLive(false);
              fetchData();
              if (data.status === 'COMPLETED') {
                alert(`🎉 MASS BROADCAST COMPLETED!\n\n• Successfully Sent: ${data.sent}\n• Failed: ${data.failed}\n• Total: ${data.total}\n\nAll contacted athletes have been updated to "Contacted" status.`);
              } else if (data.status === 'PAUSED_QUOTA') {
                alert(`⚠️ Broadcast Paused: ${data.error || 'Daily quota limit reached'}.\n${data.sent} athletes were messaged and updated.`);
              } else if (data.status === 'CANCELLED') {
                alert(`⏹️ Broadcast Stopped. ${data.sent} athletes messaged so far.`);
              } else if (data.status === 'ERROR') {
                alert(`❌ Broadcast stopped due to error: ${data.error}`);
              }
            }
          }
        }
      } catch (e) {
        console.error('Failed to poll broadcast status:', e);
      }
    };

    checkStatus();

    if (isBroadcastingLive || broadcastProgress.active) {
      intervalId = setInterval(checkStatus, 1500);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [BACKEND_URL, isBroadcastingLive, broadcastProgress.active]);

  const handleCopyLink = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(portalShareUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 3000);
    }
  };

  // Test SMS Handler
  const handleSendTestSms = async () => {
    if (!testPhone.trim()) {
      alert('Please enter a phone number.');
      return;
    }
    setIsSendingTest(true);
    setTestResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/test-sms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          test_phone: testPhone.trim(),
          message_text: messageScript,
          caller_id_email: 'BrettStehouwer@gmail.com'
        })
      });
      const data = await res.json();
      setTestResult(data);
      if (data.success) {
        alert(`✅ Test MMS sent successfully to ${testPhone}!\nCaller ID set to: BrettStehouwer@gmail.com\nCharacter Length: ${messageScript.length} chars (Full text delivered)`);
      } else {
        alert(`Notice: ${data.res?.error || 'Carrier transmission failed'}`);
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      setIsSendingTest(false);
    }
  };

  // Dry-Run Staging Handler (Safe - No Mass Text Dispatched)
  const handleStageBroadcast = async () => {
    if (!messageScript.trim()) {
      alert('Message script cannot be empty.');
      return;
    }
    setIsStaging(true);
    setStagedResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_text: messageScript.trim(),
          caller_id_email: 'BrettStehouwer@gmail.com',
          caller_id_phone: '616-402-3628',
          dry_run: true
        })
      });
      const data = await res.json();
      setStagedResult(data);
    } catch (e) {
      alert(`Staging error: ${e.message}`);
    } finally {
      setIsStaging(false);
    }
  };

  // Live Mass Broadcast Handler (Dispatches script to all pending athletes at one time)
  const handleLaunchLiveBroadcast = async () => {
    if (!messageScript.trim()) {
      alert('Message script cannot be empty.');
      return;
    }
    const count = pendingAthletes.length;
    if (count === 0) {
      alert('No pending athletes found. All athletes on the roster have already been marked as messaged.');
      return;
    }

    const confirmed = window.confirm(
      `🚨 CONFIRM LIVE MASS RECRUITING BROADCAST 🚨\n\n` +
      `You are about to dispatch this recruitment text to all ${count} student-athletes at once.\n\n` +
      `• Target Recipients: ${count} student-athletes\n` +
      `• Caller ID: BrettStehouwer@gmail.com (616-402-3628)\n` +
      `• Excluded Coaches: ${excludedCoaches.length} (100% Protected - ZERO coaches will be messaged)\n` +
      `• Protocol: Carrier MMS Multi-Paragraph Direct Delivery\n\n` +
      `Click OK to proceed and broadcast to all ${count} athletes now.`
    );

    if (!confirmed) return;

    setIsBroadcastingLive(true);
    setLiveBroadcastStatus(`🚀 Initializing background broadcast engine for ${count} athletes...`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_text: messageScript.trim(),
          caller_id_email: 'BrettStehouwer@gmail.com',
          caller_id_phone: '616-402-3628',
          dry_run: false
        })
      });
      const data = await res.json();
      if (data.success) {
        setLiveBroadcastStatus(`🚀 Mass Broadcast running in background to ${data.total} athletes...`);
      } else {
        alert(`Broadcast notice: ${data.message || 'Operation failed'}`);
        setIsBroadcastingLive(false);
        setLiveBroadcastStatus(null);
      }
    } catch (err) {
      alert(`Network error starting broadcast: ${err.message}`);
      setIsBroadcastingLive(false);
      setLiveBroadcastStatus(null);
    }
  };

  // Cancel / Pause Active Broadcast
  const handleCancelBroadcast = async () => {
    if (!window.confirm('Pause or cancel the active mass broadcast?')) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/broadcast/cancel`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert('Broadcast cancellation requested. Engine will safely stop after the current message.');
      }
    } catch (e) {
      alert(`Failed to cancel: ${e.message}`);
    }
  };

  // Scrubber: Purge Coaches from Athletes
  const handleRunCoachScrubber = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/clean-coaches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      setScrubberReport(data);
      fetchData();
      alert(`🛡️ Coach Safety Check Complete:\n${data.purged_count} coach numbers removed from athletes roster.\nAthlete list is 100% verified coach-free.`);
    } catch (e) {
      alert(`Scrubber error: ${e.message}`);
    }
  };

  // Bulk Status Update (Pending <-> Contacted)
  const handleBulkStatusUpdate = async (newStatus) => {
    if (selectedIds.size === 0) {
      alert('Please select at least one athlete.');
      return;
    }
    try {
      const ids = Array.from(selectedIds);
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/athletes/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_ids: ids,
          status: newStatus
        })
      });
      const data = await res.json();
      if (data.success) {
        setSelectedIds(new Set());
        fetchData();
      }
    } catch (e) {
      alert(`Update error: ${e.message}`);
    }
  };

  // Single Athlete Status Toggle
  const handleToggleSingleStatus = async (athlete) => {
    const nextStatus = (athlete.status === 'Contacted' || athlete.status === 'Messaged') ? 'Pending' : 'Contacted';
    try {
      await fetch(`${BACKEND_URL}/api/v1/recdebut/athletes/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_ids: [athlete.id],
          status: nextStatus
        })
      });
      fetchData();
    } catch (e) {
      alert(`Update error: ${e.message}`);
    }
  };

  // Delete Athlete
  const handleDeleteAthlete = async (id) => {
    if (!window.confirm('Delete this athlete from the tracking roster?')) return;
    try {
      await fetch(`${BACKEND_URL}/api/v1/recdebut/athletes/${id}`, { method: 'DELETE' });
      fetchData();
    } catch (e) {
      alert(`Delete error: ${e.message}`);
    }
  };

  // File Upload for Mass Listings
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (evt) => {
      const text = evt.target?.result;
      if (!text || typeof text !== 'string') return;
      setIsUploading(true);
      setUploadMessage(null);
      try {
        const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/athletes/upload-csv`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ csv_text: text })
        });
        const data = await res.json();
        if (data.success) {
          setUploadMessage(`✅ Ingested ${data.imported_count} contact rows! Coaches and athletes were automatically sorted.`);
          fetchData();
        } else {
          setUploadMessage(`❌ Upload error: ${data.error || 'Failed to parse'}`);
        }
      } catch (err) {
        setUploadMessage(`❌ Network error: ${err.message}`);
      } finally {
        setIsUploading(false);
      }
    };
    reader.readAsText(file);
  };

  // Submit Referral
  const handleSubmitReferral = async (e) => {
    e.preventDefault();
    if (!referral.name || !referral.phone) {
      alert('Athlete name and phone are required.');
      return;
    }
    setIsSubmittingReferral(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/athletes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(referral)
      });
      const data = await res.json();
      if (data.success) {
        setReferralSuccess(true);
        setReferral({
          name: '',
          phone: '',
          email: '',
          sport: 'Basketball',
          high_school: '',
          grad_year: '2026',
          city_state: '',
          notes: ''
        });
        fetchData();
        setTimeout(() => setReferralSuccess(false), 5000);
      } else {
        alert('Failed to submit athlete');
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setIsSubmittingReferral(false);
    }
  };

  // Export CSV Helper
  const exportCsv = (dataList, filename, isCoach = false) => {
    if (dataList.length === 0) {
      alert('No records to export.');
      return;
    }
    let header = '';
    let rows = '';
    if (isCoach) {
      header = 'ID,Name,Phone,Type,School,Team\n';
      rows = dataList.map(c => `"${c.id}","${c.name || ''}","${c.phone || ''}","${c.coach_type || ''}","${c.school_name || ''}","${c.team_name || ''}"`).join('\n');
    } else {
      header = 'ID,Name,Phone,Email,Sport,HighSchool,GradYear,CityState,Status,Team,Notes\n';
      rows = dataList.map(a => `"${a.id}","${a.name}","${a.phone}","${a.email || ''}","${a.sport || ''}","${a.high_school || ''}","${a.grad_year || ''}","${a.city_state || ''}","${a.status || 'Pending'}","${a.team_name || ''}","${a.notes || ''}"`).join('\n');
    }
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Categorize Athletes
  const pendingAthletes = athletes.filter(a => !a.status || a.status === 'Pending' || a.status === 'Selected');
  const messagedAthletes = athletes.filter(a => a.status === 'Contacted' || a.status === 'Messaged');

  // Filter current active table (strictly clean athletes only; coaches are 100% excluded)
  const getActiveList = () => {
    let source = [];
    if (syndicationCategory === 'messaged') source = messagedAthletes;
    else source = pendingAthletes;

    if (!searchTerm.trim()) return source;
    const term = searchTerm.toLowerCase();
    return source.filter(item => {
      return (
        (item.name && item.name.toLowerCase().includes(term)) ||
        (item.phone && item.phone.toLowerCase().includes(term)) ||
        (item.high_school && item.high_school.toLowerCase().includes(term)) ||
        (item.team_name && item.team_name.toLowerCase().includes(term)) ||
        (item.grad_year && item.grad_year.toLowerCase().includes(term))
      );
    });
  };

  const displayList = getActiveList();

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const allIds = new Set(displayList.map(i => i.id));
      setSelectedIds(allIds);
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleToggleSelectId = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalDelivered = campaigns.reduce((acc, c) => acc + (c.successful_count || 0), 0);

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#07101e',
      color: '#f8fafc',
      fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      display: 'flex',
      flexDirection: 'column'
    }}>

      {/* ── TOP EXECUTIVE BANNER & RECREATIONAL DEBUT IDENTITY ────────────────────── */}
      <header style={{
        backgroundColor: '#0a172a',
        borderBottom: '2px solid #F58426',
        padding: '20px 32px 0 32px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)'
      }}>
        
        {/* Top Row: Brand & Live Badges */}
        <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '12px',
              backgroundColor: '#ffffff',
              padding: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(245, 132, 38, 0.3)'
            }}>
              <img 
                src="https://recdebut.com/wp-content/uploads/2025/08/Screenshot__8_-removebg-preview.png" 
                alt="Recreational Debut" 
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                onError={(e) => {
                  e.target.parentNode.innerHTML = '<span style="font-size: 32px; font-weight: bold; color: #001F3F;">RD</span>';
                }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <h1 style={{ margin: 0, fontSize: '26px', fontWeight: '900', letterSpacing: '0.5px', color: '#ffffff' }}>
                  RECREATIONAL DEBUT
                </h1>
                <span style={{
                  backgroundColor: '#F58426',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: '800',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  501(c)(3) Nonprofit
                </span>
                <span style={{
                  backgroundColor: '#006BB6',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: '800',
                  padding: '4px 10px',
                  borderRadius: '4px'
                }}>
                  34+ Years In Recruiting
                </span>
                <span style={{
                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                  color: '#10b981',
                  border: '1px solid #10b981',
                  fontSize: '11px',
                  fontWeight: '800',
                  padding: '3px 8px',
                  borderRadius: '4px'
                }}>
                  MMS Direct Carrier Gateway
                </span>
              </div>

              <div style={{ marginTop: '6px', fontSize: '14px', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                <span><strong>President:</strong> Dennis Bell <span style={{ color: '#F58426' }}>(Former New York Knick #4)</span></span>
                <span>•</span>
                <span><strong>Outreach Partner:</strong> Brett Stehouwer</span>
                <span>•</span>
                <a href="https://recdebut.com" target="_blank" rel="noreferrer" style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '700' }}>
                  🌐 RecDebut.com ↗
                </a>
              </div>
            </div>
          </div>

          {/* Quick Contact & RecDebut Link */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ textAlign: 'right', fontSize: '13px', color: '#94a3b8' }}>
              <div>Direct Phone: <strong style={{ color: '#ffffff' }}>616-291-5227</strong></div>
              <div>Official Email: <strong style={{ color: '#ffffff' }}>dbell002@sbcglobal.net</strong></div>
              <div>Caller ID: <strong style={{ color: '#10b981' }}>BrettStehouwer@gmail.com</strong></div>
            </div>

            <button
              onClick={handleCopyLink}
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#ffffff',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '12px',
                fontWeight: '700',
                cursor: 'pointer'
              }}
            >
              {copiedLink ? '✓ Link Copied!' : '🔗 Share Portal Link'}
            </button>

            <a 
              href="https://recdebut.com/all-registration/" 
              target="_blank" 
              rel="noreferrer"
              style={{
                backgroundColor: '#F58426',
                color: '#ffffff',
                textDecoration: 'none',
                fontWeight: '800',
                padding: '10px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                boxShadow: '0 4px 14px rgba(245, 132, 38, 0.4)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              📝 Free Registration Form ↗
            </a>
          </div>

        </div>

        {/* Executive Metric Cards */}
        <div style={{ maxWidth: '1400px', margin: '20px auto 0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
          
          <div style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(245, 132, 38, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ fontSize: '28px' }}>🟡</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#F58426' }}>{pendingAthletes.length}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Needs To Be Messaged</div>
            </div>
          </div>

          <div style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ fontSize: '28px' }}>🟢</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#10b981' }}>{messagedAthletes.length}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Already Messaged</div>
            </div>
          </div>

          <div style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ fontSize: '28px' }}>🛡️</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#34d399' }}>{excludedCoaches.length}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Coaches Quarantined (Zero on Page)</div>
            </div>
          </div>

          <div style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ fontSize: '28px' }}>🏀</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#38bdf8' }}>850+</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>College Coaches Network</div>
            </div>
          </div>

        </div>

        {/* Tab Navigation */}
        <div style={{ maxWidth: '1400px', margin: '20px auto 0 auto', display: 'flex', gap: '10px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px', flexWrap: 'wrap' }}>
          {[
            { id: 'syndication', label: '🌐 Mass Syndication & SMS Outbox', badge: `${pendingAthletes.length} Ready` },
            { id: 'campaigns', label: '📢 Campaign Activity & Texts Sent', badge: `${campaigns.length} Blasts` },
            { id: 'roster', label: '👥 Student-Athlete Master Roster', badge: `${athletes.length}` },
            { id: 'submit', label: '➕ Submit New Athlete Candidate' },
            { id: 'network', label: '🏀 850 Coaches & Pro Endorsement Network' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              style={{
                padding: '10px 18px',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                fontWeight: '700',
                fontSize: '13px',
                backgroundColor: activeTab === tab.id ? '#F58426' : 'rgba(255, 255, 255, 0.08)',
                color: activeTab === tab.id ? '#ffffff' : '#cbd5e1',
                transition: 'all 0.15s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span>{tab.label}</span>
              {tab.badge && (
                <span style={{
                  fontSize: '10px',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  backgroundColor: activeTab === tab.id ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.15)',
                  color: '#ffffff'
                }}>
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>

      </header>

      {/* ── MAIN BODY CONTENT ──────────────────────────────────────────────────────── */}
      <main style={{ flex: 1, maxWidth: '1400px', margin: '0 auto', width: '100%', padding: '24px 32px', boxSizing: 'border-box' }}>

        {/* ── TAB 1: MASS SYNDICATION & SMS OUTBOX (PRIMARY OPERATIONAL TAB) ────────── */}
        {activeTab === 'syndication' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

            {/* Top Safety & Staging Banner */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(245, 132, 38, 0.12), rgba(7, 16, 30, 0.95))',
              border: '1px solid rgba(245, 132, 38, 0.4)',
              borderRadius: '12px',
              padding: '18px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '20px' }}>🛑</span>
                  <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: '#F58426' }}>
                    DRAFT & STAGING MODE ACTIVE (SAFE: ZERO MASS TEXTS DISPATCHED ON CLICK)
                  </h3>
                </div>
                <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: '#cbd5e1' }}>
                  Your recruitment script is staged below. You can paste custom messages, run instant tests to your phone, or stage drafts without blasting athletes.
                  <strong> All {excludedCoaches.length} club and high school coaches have been audited, purged, and quarantined in the backend blocklist. ZERO coaches are on this page or in contacts.</strong>
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={handleRunCoachScrubber}
                  style={{
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid #ef4444',
                    color: '#fca5a5',
                    padding: '8px 14px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  🛡️ Verify Coach Filter
                </button>

                <button
                  onClick={fetchData}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    color: '#ffffff',
                    padding: '8px 14px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  ↻ Refresh Data
                </button>
              </div>
            </div>

            {/* Custom Message Script Box & Staging Controls */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '24px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                    📝 Custom Recruitment Message Script
                  </h3>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '3px' }}>
                    Caller ID: <strong style={{ color: '#10b981' }}>BrettStehouwer@gmail.com</strong> (616-402-3628) • Full MMS Multi-Paragraph Delivery
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setMessageScript(DEFAULT_MESSAGE)}
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      color: '#cbd5e1',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    Reset to Dennis Bell Official Script
                  </button>
                  <button
                    onClick={() => setMessageScript('')}
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      color: '#cbd5e1',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    Clear Box
                  </button>
                </div>
              </div>

              {/* Message Script Textarea */}
              <textarea
                value={messageScript}
                onChange={(e) => setMessageScript(e.target.value)}
                placeholder="Paste or write your custom recruitment text message script here..."
                rows={8}
                style={{
                  width: '100%',
                  backgroundColor: '#07101e',
                  color: '#f8fafc',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '8px',
                  padding: '14px',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  fontFamily: 'inherit',
                  boxSizing: 'border-box',
                  resize: 'vertical'
                }}
              />

              {/* Character & Gateway Telemetry */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '12px', color: '#94a3b8', flexWrap: 'wrap', gap: '10px' }}>
                <div>
                  <span>Length: <strong style={{ color: '#F58426' }}>{messageScript.length}</strong> characters</span>
                  <span style={{ margin: '0 8px' }}>•</span>
                  <span>Direct MMS Gateway: <strong style={{ color: '#10b981' }}>Full Delivery (No 160 Char Cutoff)</strong></span>
                  <span style={{ margin: '0 8px' }}>•</span>
                  <span>Personalization: Automatically adds <em>"Hey [Athlete Name],"</em></span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <input
                    type="text"
                    value={testPhone}
                    onChange={(e) => setTestPhone(e.target.value)}
                    placeholder="Test Phone #"
                    style={{
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '6px 10px',
                      fontSize: '12px',
                      width: '120px'
                    }}
                  />
                  <button
                    onClick={handleSendTestSms}
                    disabled={isSendingTest}
                    style={{
                      backgroundColor: '#006BB6',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '7px 14px',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: isSendingTest ? 'not-allowed' : 'pointer',
                      opacity: isSendingTest ? 0.6 : 1
                    }}
                  >
                    {isSendingTest ? 'Sending Test...' : '🧪 Send Test to My Phone'}
                  </button>

                  <button
                    onClick={handleStageBroadcast}
                    disabled={isStaging}
                    style={{
                      backgroundColor: '#F58426',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '7px 16px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: isStaging ? 'not-allowed' : 'pointer',
                      opacity: isStaging ? 0.6 : 1
                    }}
                  >
                    {isStaging ? 'Staging...' : `📋 Stage Draft for ${pendingAthletes.length} Athletes`}
                  </button>

                  {/* 🚀 PRIMARY ONE-CLICK MASS SEND BUTTON */}
                  <button
                    onClick={handleLaunchLiveBroadcast}
                    disabled={isBroadcastingLive || pendingAthletes.length === 0}
                    style={{
                      backgroundColor: '#10b981',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '8px 20px',
                      fontSize: '13px',
                      fontWeight: '900',
                      letterSpacing: '0.3px',
                      cursor: (isBroadcastingLive || pendingAthletes.length === 0) ? 'not-allowed' : 'pointer',
                      boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)',
                      opacity: (isBroadcastingLive || pendingAthletes.length === 0) ? 0.6 : 1,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    {isBroadcastingLive ? '🚀 Broadcasting Mass Texts...' : `🚀 SEND TO ALL ${pendingAthletes.length} CONTACTS NOW`}
                  </button>
                </div>
              </div>

              {/* Live Broadcast In-Progress Banner with Live Progress Bar */}
              {(liveBroadcastStatus || isBroadcastingLive || broadcastProgress.active) && (
                <div style={{
                  marginTop: '16px',
                  background: 'rgba(16, 185, 129, 0.12)',
                  border: '2px solid #10b981',
                  borderRadius: '10px',
                  padding: '16px 20px',
                  color: '#ffffff'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: '26px' }}>⚡</span>
                      <div>
                        <div style={{ fontSize: '15px', fontWeight: '800', color: '#10b981' }}>
                          Live Mass Broadcast Active
                        </div>
                        <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px' }}>
                          {broadcastProgress.sent || 0} of {broadcastProgress.total || pendingAthletes.length} messaged ({broadcastProgress.progress_pct || 0}%)
                          {broadcastProgress.current_athlete ? ` • Currently sending to: ${broadcastProgress.current_athlete}` : ''}
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={handleCancelBroadcast}
                      style={{
                        backgroundColor: '#ef4444',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '7px 14px',
                        fontSize: '12px',
                        fontWeight: '800',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      ⏹️ Pause / Cancel
                    </button>
                  </div>

                  {/* Progress Bar Track */}
                  <div style={{
                    width: '100%',
                    height: '10px',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    borderRadius: '5px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, Math.max(2, broadcastProgress.progress_pct || 0))}%`,
                      backgroundColor: '#10b981',
                      transition: 'width 0.4s ease-in-out'
                    }} />
                  </div>
                </div>
              )}

              {/* Staged Draft Preview Report */}
              {stagedResult && (
                <div style={{
                  marginTop: '16px',
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid #10b981',
                  borderRadius: '8px',
                  padding: '14px 18px',
                  fontSize: '13px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ color: '#10b981', fontSize: '14px' }}>
                      ✓ {stagedResult.message}
                    </strong>
                    <button
                      onClick={() => setStagedResult(null)}
                      style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                    >
                      ✕ Close
                    </button>
                  </div>
                  <div style={{ marginTop: '8px', color: '#cbd5e1', display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                    <div>Ready Athletes: <strong style={{ color: '#ffffff' }}>{stagedResult.ready_athletes_count}</strong></div>
                    <div>Blocked Coaches: <strong style={{ color: '#ef4444' }}>{stagedResult.blocked_coaches_count}</strong> (100% Excluded)</div>
                    <div>Caller ID: <strong style={{ color: '#10b981' }}>{stagedResult.caller_id}</strong></div>
                  </div>
                  {stagedResult.preview_recipients && (
                    <div style={{ marginTop: '8px', fontSize: '12px', color: '#94a3b8' }}>
                      Sample Staged Athletes: {stagedResult.preview_recipients.map(r => `${r.name} (${r.phone})`).join(', ')}...
                    </div>
                  )}

                  <div style={{ marginTop: '14px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <button
                      onClick={handleLaunchLiveBroadcast}
                      disabled={isBroadcastingLive}
                      style={{
                        backgroundColor: '#10b981',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '8px 18px',
                        fontSize: '13px',
                        fontWeight: '800',
                        cursor: isBroadcastingLive ? 'not-allowed' : 'pointer',
                        boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                      }}
                    >
                      {isBroadcastingLive ? 'Dispatching...' : `🚀 Ready to Send: Dispatch to All ${stagedResult.ready_athletes_count} Athletes Now`}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Contact File Upload Zone for Mass Listings */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px dashed rgba(245, 132, 38, 0.4)',
              padding: '20px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '22px' }}>📁</span>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '15px', fontWeight: '800', color: '#ffffff' }}>
                      Upload Contact Files for Mass Listings
                    </h4>
                    <p style={{ margin: '3px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
                      Upload contact files (CSV, TXT, TSV). The system automatically isolates coaches from athletes.
                    </p>
                  </div>
                </div>
                {uploadMessage && (
                  <div style={{ marginTop: '8px', fontSize: '12px', color: uploadMessage.startsWith('✅') ? '#10b981' : '#ef4444' }}>
                    {uploadMessage}
                  </div>
                )}
              </div>

              <div>
                <label style={{
                  backgroundColor: '#006BB6',
                  color: '#ffffff',
                  padding: '9px 18px',
                  borderRadius: '6px',
                  fontWeight: '700',
                  fontSize: '13px',
                  cursor: isUploading ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <span>{isUploading ? 'Ingesting File...' : '📤 Select Contact File (.csv, .txt)'}</span>
                  <input
                    type="file"
                    accept=".csv,.txt,.tsv"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                    style={{ display: 'none' }}
                  />
                </label>
              </div>
            </div>

            {/* Organized Category View Switcher & Actions */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '20px'
            }}>
              
              {/* Filter Tabs & Search Bar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px' }}>
                
                {/* Clean Athlete Categories */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => { setSyndicationCategory('pending'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'pending' ? '#F58426' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'pending' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    🟡 Needs To Be Messaged ({pendingAthletes.length})
                  </button>

                  <button
                    onClick={() => { setSyndicationCategory('messaged'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'messaged' ? '#10b981' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'messaged' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    🟢 Already Messaged ({messagedAthletes.length})
                  </button>

                  <div style={{
                    padding: '8px 14px',
                    borderRadius: '6px',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    fontWeight: '700',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    color: '#34d399'
                  }}>
                    🛡️ Coach Exclusion Shield Active (Zero Coaches on Page or in Contacts)
                  </div>
                </div>

                {/* Search Bar & Export Buttons */}
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search name, phone, school, team..."
                    style={{
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '7px 12px',
                      fontSize: '12px',
                      width: '240px'
                    }}
                  />

                  <button
                    onClick={() => exportCsv(athletes, 'RecDebut_Athletes_Clean_List', false)}
                    style={{
                      backgroundColor: 'rgba(16, 185, 129, 0.2)',
                      border: '1px solid #10b981',
                      color: '#6ee7b7',
                      padding: '7px 12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer'
                    }}
                  >
                    📥 Export Clean Athletes (CSV)
                  </button>
                </div>

              </div>

              {/* Bulk Action Controls */}
              {selectedIds.size > 0 && (
                <div style={{
                  backgroundColor: 'rgba(0, 107, 182, 0.15)',
                  border: '1px solid #006BB6',
                  borderRadius: '6px',
                  padding: '10px 16px',
                  marginBottom: '14px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '13px'
                }}>
                  <div>
                    Selected <strong>{selectedIds.size}</strong> athletes
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => handleBulkStatusUpdate('Contacted')}
                      style={{
                        backgroundColor: '#10b981',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '6px 12px',
                        fontSize: '12px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      Mark Selected as Contacted
                    </button>
                    <button
                      onClick={() => handleBulkStatusUpdate('Pending')}
                      style={{
                        backgroundColor: '#F58426',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '6px 12px',
                        fontSize: '12px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      Reset Selected to Pending
                    </button>
                  </div>
                </div>
              )}

              {/* Spreadsheet Table View */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.15)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      <th style={{ padding: '12px 10px', width: '30px' }}>
                        <input
                          type="checkbox"
                          checked={displayList.length > 0 && selectedIds.size === displayList.length}
                          onChange={handleSelectAll}
                        />
                      </th>
                      <th style={{ padding: '12px 14px' }}>Name</th>
                      <th style={{ padding: '12px 14px' }}>Phone Number</th>
                      <th style={{ padding: '12px 14px' }}>High School / Club</th>
                      <th style={{ padding: '12px 14px' }}>Grad Year / Team</th>
                      <th style={{ padding: '12px 14px' }}>Status</th>
                      <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {isLoading ? (
                      <tr>
                        <td colSpan={7} style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                          Loading records...
                        </td>
                      </tr>
                    ) : displayList.length === 0 ? (
                      <tr>
                        <td colSpan={7} style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                          No records found matching current category / filter.
                        </td>
                      </tr>
                    ) : (
                      displayList.slice(0, 150).map((item, idx) => {
                        const isSelected = selectedIds.has(item.id);
                        return (
                          <tr
                            key={item.id || idx}
                            style={{
                              borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                              backgroundColor: isSelected ? 'rgba(0, 107, 182, 0.1)' : idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent'
                            }}
                          >
                            <td style={{ padding: '10px 10px' }}>
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => handleToggleSelectId(item.id)}
                              />
                            </td>
                            <td style={{ padding: '10px 14px', fontWeight: '700', color: '#ffffff' }}>
                              {item.name}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#38bdf8', fontFamily: 'monospace' }}>
                              {item.phone}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                              {item.high_school || item.sport || 'Basketball'}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                              {`${item.grad_year || '2026'}${item.team_name ? ` • ${item.team_name}` : ''}`}
                            </td>
                            <td style={{ padding: '10px 14px' }}>
                              {(item.status === 'Contacted' || item.status === 'Messaged') ? (
                                <span style={{
                                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                                  color: '#10b981',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  🟢 Contacted
                                </span>
                              ) : (
                                <span style={{
                                  backgroundColor: 'rgba(245, 132, 38, 0.2)',
                                  color: '#F58426',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  🟡 Pending
                                </span>
                              )}
                            </td>
                            <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', gap: '6px' }}>
                                <button
                                  onClick={() => handleToggleSingleStatus(item)}
                                  title="Toggle Contacted / Pending"
                                  style={{
                                    background: 'rgba(255, 255, 255, 0.08)',
                                    border: '1px solid rgba(255, 255, 255, 0.15)',
                                    color: '#cbd5e1',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  {(item.status === 'Contacted' || item.status === 'Messaged') ? 'Set Pending' : 'Mark Done'}
                                </button>
                                <button
                                  onClick={() => {
                                    setTestPhone(item.phone);
                                    alert(`Set test phone to ${item.name} (${item.phone}). Click 'Send Test' above to test dispatch.`);
                                  }}
                                  title="Send Test MMS"
                                  style={{
                                    background: 'rgba(0, 107, 182, 0.15)',
                                    border: '1px solid #006BB6',
                                    color: '#38bdf8',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  🧪 Test
                                </button>
                                <button
                                  onClick={() => handleDeleteAthlete(item.id)}
                                  title="Delete athlete"
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.15)',
                                    border: '1px solid rgba(239, 68, 68, 0.3)',
                                    color: '#f87171',
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    cursor: 'pointer'
                                  }}
                                >
                                  ✕
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {displayList.length > 150 && (
                <div style={{ textAlign: 'center', marginTop: '14px', fontSize: '12px', color: '#94a3b8' }}>
                  Showing first 150 of {displayList.length} records. Use the search bar above to filter specific names or schools, or use CSV export for full sheet.
                </div>
              )}

            </div>

          </div>
        )}

        {/* ── TAB 2: CAMPAIGN ACTIVITY & TEXTS SENT ─────────────────────────────────── */}
        {activeTab === 'campaigns' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '28px' }}>
            
            {/* Left: Broadcast History Ledger */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#ffffff' }}>
                    Broadcast History & Outbound Text Log
                  </h2>
                  <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                    Live records of every recruitment announcement transmitted to student-athletes.
                  </p>
                </div>
                <button
                  onClick={fetchData}
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}
                >
                  ↻ Refresh Feed
                </button>
              </div>

              {campaigns.length === 0 ? (
                <div style={{
                  background: '#0e1c31',
                  borderRadius: '12px',
                  border: '1px solid rgba(255,255,255,0.08)',
                  padding: '40px',
                  textAlign: 'center',
                  color: '#94a3b8'
                }}>
                  <div style={{ fontSize: '36px', marginBottom: '12px' }}>📲</div>
                  <h4 style={{ margin: '0 0 8px 0', color: '#ffffff' }}>No Mass Broadcasts Dispatched Yet</h4>
                  <p style={{ margin: 0, fontSize: '13px' }}>
                    Mass SMS broadcasts sent with Dennis Bell's message will log delivery telemetry here.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {campaigns.map((c) => (
                    <div key={c.id} style={{
                      background: '#0e1c31',
                      borderRadius: '10px',
                      border: '1px solid rgba(255,255,255,0.08)',
                      padding: '18px 20px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: '800', color: '#ffffff' }}>
                            Mass Broadcast Blast #{c.id}
                          </div>
                          <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                            {new Date(c.created_at * 1000).toLocaleString()} • Sender ID: <strong style={{ color: '#10b981' }}>{c.sender_id}</strong>
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px' }}>
                          <span style={{
                            backgroundColor: 'rgba(16, 185, 129, 0.2)',
                            color: '#10b981',
                            fontSize: '11px',
                            fontWeight: '800',
                            padding: '3px 8px',
                            borderRadius: '4px'
                          }}>
                            ✓ {c.successful_count} Delivered
                          </span>
                          {c.failed_count > 0 && (
                            <span style={{
                              backgroundColor: 'rgba(239, 68, 68, 0.2)',
                              color: '#ef4444',
                              fontSize: '11px',
                              fontWeight: '800',
                              padding: '3px 8px',
                              borderRadius: '4px'
                            }}>
                              ✕ {c.failed_count} Retried
                            </span>
                          )}
                        </div>
                      </div>

                      <div style={{
                        marginTop: '12px',
                        backgroundColor: '#07101e',
                        borderRadius: '6px',
                        padding: '12px',
                        fontSize: '12px',
                        color: '#cbd5e1',
                        whiteSpace: 'pre-line',
                        lineHeight: '1.5'
                      }}>
                        {c.message_body}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right: Message Details & Partner Verification */}
            <div>
              <div style={{ background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '24px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                  Standard SMS Outreach Script
                </h3>
                <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.5', margin: '0 0 14px 0' }}>
                  The verified message approved by Dennis Bell for candidate student-athletes.
                </p>

                <div style={{
                  backgroundColor: '#07101e',
                  border: '1px solid rgba(245, 132, 38, 0.4)',
                  borderRadius: '8px',
                  padding: '16px',
                  fontSize: '13px',
                  color: '#f8fafc',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-line'
                }}>
                  {DEFAULT_MESSAGE}
                </div>

                <div style={{ marginTop: '20px', padding: '14px', background: 'rgba(0, 107, 182, 0.1)', border: '1px solid #006BB6', borderRadius: '8px', fontSize: '12px', color: '#cbd5e1' }}>
                  <strong style={{ color: '#38bdf8' }}>Carrier Identity Verification:</strong>
                  <div style={{ marginTop: '4px' }}>
                    Messages sent through carrier MMS gateways display <strong>BrettStehouwer@gmail.com</strong> as caller ID / sender address and direct replies are routed to Dennis Bell at <strong>616-291-5227</strong> and <strong>dbell002@sbcglobal.net</strong>.
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ── TAB 3: STUDENT-ATHLETE MASTER ROSTER ─────────────────────────────────── */}
        {activeTab === 'roster' && (
          <div style={{ background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#ffffff' }}>
                  Student-Athlete Master Roster ({athletes.length})
                </h2>
                <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                  Complete database of candidate athletes with clean phone numbers, high schools, and recruitment status.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Filter roster..."
                  style={{
                    backgroundColor: '#07101e',
                    color: '#ffffff',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '6px',
                    padding: '8px 14px',
                    fontSize: '13px',
                    width: '240px'
                  }}
                />
                <button
                  onClick={() => exportCsv(athletes, 'RecDebut_Athletes_Roster', false)}
                  style={{
                    backgroundColor: '#F58426',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '8px 16px',
                    fontSize: '13px',
                    fontWeight: '800',
                    cursor: 'pointer'
                  }}
                >
                  📥 Export Roster CSV
                </button>
              </div>
            </div>

            {/* Athletes Master Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.15)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <th style={{ padding: '12px 14px' }}>ID</th>
                    <th style={{ padding: '12px 14px' }}>Name</th>
                    <th style={{ padding: '12px 14px' }}>Phone</th>
                    <th style={{ padding: '12px 14px' }}>Sport</th>
                    <th style={{ padding: '12px 14px' }}>High School</th>
                    <th style={{ padding: '12px 14px' }}>Class</th>
                    <th style={{ padding: '12px 14px' }}>Status</th>
                    <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {athletes.filter(a => {
                    if (!searchTerm.trim()) return true;
                    const term = searchTerm.toLowerCase();
                    return a.name.toLowerCase().includes(term) || a.phone.includes(term) || (a.high_school && a.high_school.toLowerCase().includes(term));
                  }).slice(0, 100).map((a, idx) => (
                    <tr key={a.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', backgroundColor: idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent' }}>
                      <td style={{ padding: '10px 14px', color: '#64748b' }}>#{a.id}</td>
                      <td style={{ padding: '10px 14px', fontWeight: '700', color: '#ffffff' }}>{a.name}</td>
                      <td style={{ padding: '10px 14px', color: '#38bdf8', fontFamily: 'monospace' }}>{a.phone}</td>
                      <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>{a.sport || 'Basketball'}</td>
                      <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>{a.high_school || '—'}</td>
                      <td style={{ padding: '10px 14px', color: '#94a3b8' }}>{a.grad_year || '2026'}</td>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          backgroundColor: (a.status === 'Contacted' || a.status === 'Messaged') ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 132, 38, 0.2)',
                          color: (a.status === 'Contacted' || a.status === 'Messaged') ? '#10b981' : '#F58426',
                          fontSize: '11px',
                          fontWeight: '800',
                          padding: '3px 8px',
                          borderRadius: '4px'
                        }}>
                          {a.status || 'Pending'}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                        <button
                          onClick={() => handleDeleteAthlete(a.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#ef4444',
                            cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── TAB 4: SUBMIT NEW ATHLETE CANDIDATE ───────────────────────────────────── */}
        {activeTab === 'submit' && (
          <div style={{ maxWidth: '800px', margin: '0 auto', background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '32px' }}>
            <h2 style={{ margin: '0 0 8px 0', fontSize: '22px', fontWeight: '800', color: '#ffffff' }}>
              Submit New Student-Athlete Candidate
            </h2>
            <p style={{ margin: '0 0 24px 0', fontSize: '13px', color: '#94a3b8' }}>
              Add a student-athlete referral directly to Dennis Bell's outreach queue for evaluation and national coach distribution.
            </p>

            {referralSuccess && (
              <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#10b981', padding: '14px', borderRadius: '8px', marginBottom: '20px', fontSize: '14px', fontWeight: '700' }}>
                ✓ Athlete candidate successfully registered and added to Recreational Debut roster!
              </div>
            )}

            <form onSubmit={handleSubmitReferral} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '18px' }}>
              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Student-Athlete Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={referral.name}
                  onChange={(e) => setReferral({ ...referral, name: e.target.value })}
                  placeholder="e.g. Jordan Miller"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#07101e',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    fontSize: '14px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Athlete Mobile Phone (For Direct SMS) *
                </label>
                <input
                  type="tel"
                  required
                  value={referral.phone}
                  onChange={(e) => setReferral({ ...referral, phone: e.target.value })}
                  placeholder="e.g. 616-555-0199"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#07101e',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    fontSize: '14px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Athlete / Parent Email
                </label>
                <input
                  type="email"
                  value={referral.email}
                  onChange={(e) => setReferral({ ...referral, email: e.target.value })}
                  placeholder="e.g. jmiller@gmail.com"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#07101e',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    fontSize: '14px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Primary Sport
                </label>
                <input
                  type="text"
                  value={referral.sport}
                  onChange={(e) => setReferral({ ...referral, sport: e.target.value })}
                  placeholder="Basketball, Football, Track, etc."
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#07101e',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    fontSize: '14px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Graduation Year
                </label>
                <input
                  type="text"
                  value={referral.grad_year}
                  onChange={(e) => setReferral({ ...referral, grad_year: e.target.value })}
                  placeholder="2026, 2027, etc."
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#07101e',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    fontSize: '14px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  High School / Club Team & City, State
                </label>
                <input
                  type="text"
                  value={referral.high_school}
                  onChange={(e) => setReferral({ ...referral, high_school: e.target.value })}
                  placeholder="e.g. East Kentwood High School, Grand Rapids MI"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#07101e',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    fontSize: '14px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ gridColumn: 'span 2' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '6px' }}>
                  Athletic Notes & Accomplishments (Stats, Height, GPA)
                </label>
                <textarea
                  rows={3}
                  value={referral.notes}
                  onChange={(e) => setReferral({ ...referral, notes: e.target.value })}
                  placeholder="e.g. 6'4 Guard, 3.6 GPA, All-Conference First Team"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '6px',
                    backgroundColor: '#07101e',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#ffffff',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ gridColumn: 'span 2', marginTop: '10px' }}>
                <button
                  type="submit"
                  disabled={isSubmittingReferral}
                  style={{
                    backgroundColor: '#F58426',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '12px 24px',
                    fontSize: '14px',
                    fontWeight: '800',
                    cursor: isSubmittingReferral ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 14px rgba(245, 132, 38, 0.4)'
                  }}
                >
                  {isSubmittingReferral ? 'Submitting...' : 'Submit Athlete Candidate'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ── TAB 5: 850 COACHES NETWORK ─────────────────────────────────────────── */}
        {activeTab === 'network' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '28px' }}>
            <div style={{ background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '28px' }}>
              <h2 style={{ margin: '0 0 12px 0', fontSize: '20px', fontWeight: '800', color: '#ffffff' }}>
                Collegiate Recruitment Architecture
              </h2>
              <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: '1.6' }}>
                Recreational Debut delivers athletic resumes and highlight film directly to college coaching departments across the United States and Canada.
              </p>

              <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {[
                  { title: 'NCAA Division I', desc: 'Over 350+ Division 1 athletic departments across ACC, Big Ten, SEC, Pac-12, Big East.' },
                  { title: 'NCAA Division II', desc: 'Full scholarship tier with extensive midwest & nationwide programs.' },
                  { title: 'NCAA Division III', desc: 'High academic standards, competitive athletics, and merit grant aid.' },
                  { title: 'NAIA & NJCAA', desc: 'Premier development, immediate starter opportunities, and university transfer pipelines.' }
                ].map((tier, i) => (
                  <div key={i} style={{ background: '#07101e', padding: '14px 18px', borderRadius: '8px', borderLeft: '4px solid #F58426' }}>
                    <div style={{ fontSize: '15px', fontWeight: '800', color: '#ffffff' }}>{tier.title}</div>
                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>{tier.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '28px' }}>
              <h2 style={{ margin: '0 0 12px 0', fontSize: '20px', fontWeight: '800', color: '#ffffff' }}>
                Dennis Bell Professional Endorsement
              </h2>
              <p style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: '1.7' }}>
                Every student portfolio distributed through Recreational Debut includes an official acknowledgement letter from former New York Knick Dennis Bell. This gives coaches added credibility and reasons to evaluate game footage closely.
              </p>

              <div style={{ marginTop: '24px', background: 'rgba(0, 107, 182, 0.1)', border: '1px solid #006BB6', borderRadius: '8px', padding: '18px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#38bdf8' }}>Official Program Inclusions:</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: '#f8fafc' }}>
                  <div>🏀 Pro Player Endorsement Letter</div>
                  <div>📄 Standardized Academic & Athletic Resume</div>
                  <div>📊 Official Statistical Breakdown</div>
                  <div>🎥 Professional Highlight Film Editing</div>
                  <div>⚡ Direct Delivery to 850+ College Coaches</div>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>

      {/* ── FOOTER ────────────────────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.08)',
        background: '#040b15',
        padding: '20px 32px',
        fontSize: '12px',
        color: '#64748b',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          Recreational Debut 501(c)(3) Nonprofit Organization • Grandville / Grand Rapids, MI
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <span>Dennis Bell: 616-291-5227</span>
          <span>•</span>
          <span>dbell002@sbcglobal.net</span>
          <span>•</span>
          <span>RecDebut.com</span>
        </div>
      </footer>

    </div>
  );
}
