import os
from pathlib import Path

jsx_content = r'''import React, { useState, useEffect } from 'react';

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
      if (tab && ['syndication', 'emails', 'campaigns', 'roster', 'submit', 'network'].includes(tab)) {
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

  // Campaign Mode: 'sms' (Carrier MMS to Phones) vs 'email' (Direct to Inboxes)
  const [campaignType, setCampaignType] = useState('sms');
  const [emailSubject, setEmailSubject] = useState('Dennis Bell (Former New York Knick) - College Athletic Recruitment Opportunity');
  const [useSwarm, setUseSwarm] = useState(true);

  // SMTP Swarm State
  const [smtpAccounts, setSmtpAccounts] = useState([]);
  const [showAddAccountModal, setShowAddAccountModal] = useState(false);
  const [showAppPasswordGuide, setShowAppPasswordGuide] = useState(false);
  const [newAccount, setNewAccount] = useState({
    email: '',
    app_password: '',
    label: '',
    daily_limit: 400
  });
  const [isTestingAccount, setIsTestingAccount] = useState(false);
  const [isSavingAccount, setIsSavingAccount] = useState(false);
  const [accountActionMessage, setAccountActionMessage] = useState(null);

  // Athlete Email Hub State
  const [athleteEmailsSummary, setAthleteEmailsSummary] = useState(null);
  const [copiedEmailsToast, setCopiedEmailsToast] = useState(null);
  const [emailSearchTerm, setEmailSearchTerm] = useState('');
  const [emailListFilter, setEmailListFilter] = useState('all'); // 'all' | 'pending' | 'messaged'

  // Syndication Category Filter: 'pending' | 'messaged'
  const [syndicationCategory, setSyndicationCategory] = useState('pending');
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Test Dispatch State
  const [testPhone, setTestPhone] = useState('616-402-3628'); // Brett's phone by default
  const [testEmail, setTestEmail] = useState('dbell002@sbcglobal.net'); // Dennis Bell's email by default
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // Custom Message Box State (Pre-populated with Dennis's text)
  const DEFAULT_MESSAGE = `Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.

Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.

We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.

If playing college sports is your goal, don’t wait for coaches to find you.

📱 Call or text: 616-291-5227
✅ Register FREE: RecDebut.com
📧 dbell002@sbcglobal.net

Let’s get you recruited!

Dennis Bell
Former New York Knicks
President, Recreational Debut`;

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

  // Daily Quota & Batch Pacing State (Safe 100% Free Gateway)
  const [quotaStatus, setQuotaStatus] = useState({
    sent_last_24h: 0,
    daily_ceiling: 450,
    remaining_today: 450,
    pending_count: 0,
    total_contacted: 0,
    recommended_batch_size: 400,
    days_to_complete: 5,
    swarm_accounts_count: 1,
    swarm_daily_ceiling: 400,
    swarm_remaining_today: 400,
    swarm_days_to_complete: 5
  });
  const [batchSize, setBatchSize] = useState(400);

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
      const [athRes, campRes, coachRes, quotaRes, smtpRes, emailSumRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/v1/recdebut/athletes`).then(r => r.json()).catch(() => ({ athletes: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/campaigns`).then(r => r.json()).catch(() => ({ campaigns: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/excluded-coaches`).then(r => r.json()).catch(() => ({ coaches: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/quota-status`).then(r => r.json()).catch(() => null),
        fetch(`${BACKEND_URL}/api/v1/recdebut/smtp-accounts`).then(r => r.json()).catch(() => ({ accounts: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/athlete-emails`).then(r => r.json()).catch(() => null)
      ]);

      if (athRes.athletes) setAthletes(athRes.athletes);
      if (campRes.campaigns) setCampaigns(campRes.campaigns);
      if (coachRes.coaches) setExcludedCoaches(coachRes.coaches);
      if (smtpRes && smtpRes.accounts) setSmtpAccounts(smtpRes.accounts);
      if (emailSumRes && emailSumRes.success) setAthleteEmailsSummary(emailSumRes);
      if (quotaRes && quotaRes.success) {
        setQuotaStatus(quotaRes);
        if (quotaRes.recommended_batch_size) {
          setBatchSize(quotaRes.recommended_batch_size);
        }
      }
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
              `🚀 Live ${data.campaign_type === 'email' ? 'Direct Email' : 'MMS'} Broadcast running: ${data.sent} / ${data.total} dispatched (${data.progress_pct}%) • Account: ${data.current_account || 'Swarm'} • Contacting: ${data.current_athlete || 'Connecting...'}`
            );
          } else {
            if (isBroadcastingLive) {
              setIsBroadcastingLive(false);
              fetchData();
              if (data.status === 'COMPLETED') {
                alert(`🎉 MASS BROADCAST COMPLETED!\n\n• Successfully Sent: ${data.sent}\n• Failed: ${data.failed}\n• Total: ${data.total}\n\nAll messaged athletes have been updated to "Contacted" status.`);
              } else if (data.status === 'PAUSED_QUOTA') {
                alert(`⚠️ Broadcast Paused: ${data.error || 'Daily quota limit reached'}.\n${data.sent} athletes were messaged.`);
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

  // Test Dispatch Handler (Phone SMS or Email Inbox)
  const handleSendTestDispatch = async () => {
    setIsSendingTest(true);
    setTestResult(null);
    try {
      if (campaignType === 'email') {
        const target = testEmail.trim() || 'dbell002@sbcglobal.net';
        const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/test-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            test_email: target,
            message_text: messageScript,
            subject_line: emailSubject,
            caller_id_email: 'dbell002@sbcglobal.net',
            caller_id_name: 'Dennis Bell (616-291-5227)'
          })
        });
        const data = await res.json();
        setTestResult(data);
        if (data.success) {
          alert(`✅ Test Email sent successfully to ${target}!\n\nSubject: ${emailSubject}\nFrom: Dennis Bell (616-291-5227) <dbell002@sbcglobal.net>\nReply-To: dbell002@sbcglobal.net\n\nCheck your inbox to review exact formatting!`);
        } else {
          alert(`Notice: ${data.message || data.error || 'Email dispatch failed'}`);
        }
      } else {
        const target = testPhone.trim() || '616-402-3628';
        const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/test-sms`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            test_phone: target,
            message_text: messageScript,
            caller_id_email: 'dbell002@sbcglobal.net',
            caller_id_phone: '616-291-5227',
            caller_id_name: 'Dennis Bell (616-291-5227)'
          })
        });
        const data = await res.json();
        setTestResult(data);
        if (data.success) {
          alert(`✅ Test MMS sent successfully to ${target}!\nCaller ID set to: Dennis Bell (616-291-5227)\nCharacter Length: ${messageScript.length} chars (Full text delivered)`);
        } else {
          alert(`Notice: ${data.res?.error || 'Carrier transmission failed'}`);
        }
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      setIsSendingTest(false);
    }
  };

  // Dry-Run Staging Handler
  const handleStageBroadcast = async () => {
    if (!messageScript.trim()) {
      alert('Message script cannot be empty.');
      return;
    }
    const count = Math.min(batchSize, pendingAthletes.length);
    setIsStaging(true);
    setStagedResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_limit: count,
          message_text: messageScript.trim(),
          caller_id_email: 'dbell002@sbcglobal.net',
          caller_id_phone: '616-291-5227',
          caller_id_name: 'Dennis Bell (616-291-5227)',
          campaign_type: campaignType,
          subject_line: emailSubject,
          use_swarm: useSwarm,
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

  // Live Mass Broadcast Handler
  const handleLaunchLiveBroadcast = async (countOverride = null) => {
    if (!messageScript.trim()) {
      alert('Message script cannot be empty.');
      return;
    }
    const count = countOverride || Math.min(batchSize, pendingAthletes.length);
    if (count === 0) {
      alert('No pending athletes found. All athletes have already been marked as messaged.');
      return;
    }

    const modeName = campaignType === 'email' ? 'DIRECT EMAIL INBOX' : 'CARRIER MMS PHONE TEXT';
    const activeGmailsCount = smtpAccounts.filter(a => a.active).length || 1;
    const swarmCapacity = quotaStatus.swarm_daily_ceiling || 400;

    const confirmed = window.confirm(
      `🚨 CONFIRM LIVE MASS BROADCAST 🚨\n\n` +
      `Campaign Mode: ${modeName}\n` +
      `Target Recipients: ${count} student-athletes\n` +
      `SMTP Swarm Pool: ${activeGmailsCount} Gmail account(s) connected (${swarmCapacity} msgs/day capacity)\n` +
      `Account Rotation: Auto-rotates to prevent Google rate limits\n` +
      `Sender / Caller ID: Dennis Bell (616-291-5227) • dbell002@sbcglobal.net\n` +
      `Protected Coaches: ${excludedCoaches.length} (100% Quarantined)\n` +
      `Cost: $0.00 (Zero-Cost)\n\n` +
      `Click OK to start the broadcast to ${count} athletes now.`
    );

    if (!confirmed) return;

    setIsBroadcastingLive(true);
    setLiveBroadcastStatus(`🚀 Initializing broadcast engine for ${count} athletes via SMTP Swarm...`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_limit: count,
          message_text: messageScript.trim(),
          caller_id_email: 'dbell002@sbcglobal.net',
          caller_id_phone: '616-291-5227',
          caller_id_name: 'Dennis Bell (616-291-5227)',
          campaign_type: campaignType,
          subject_line: emailSubject,
          use_swarm: useSwarm,
          dry_run: false
        })
      });
      const data = await res.json();
      if (data.success) {
        setLiveBroadcastStatus(`🚀 Broadcast running in background to ${data.total} athletes...`);
        fetchData();
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
        alert('Broadcast cancellation requested. Engine will stop after current message.');
      }
    } catch (e) {
      alert(`Failed to cancel: ${e.message}`);
    }
  };

  // SMTP Swarm: Add Account
  const handleSaveSmtpAccount = async (e) => {
    e.preventDefault();
    if (!newAccount.email || !newAccount.app_password) {
      alert('Email and 16-character Google App Password are required.');
      return;
    }
    setIsSavingAccount(true);
    setAccountActionMessage(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/smtp-accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAccount)
      });
      const data = await res.json();
      if (data.success) {
        setAccountActionMessage(`✅ Added ${newAccount.email} to SMTP Swarm!`);
        setNewAccount({ email: '', app_password: '', label: '', daily_limit: 400 });
        setShowAddAccountModal(false);
        fetchData();
        setTimeout(() => setAccountActionMessage(null), 4000);
      } else {
        alert(`Error: ${data.detail || data.message || 'Failed to save account'}`);
      }
    } catch (err) {
      alert(`Error saving account: ${err.message}`);
    } finally {
      setIsSavingAccount(false);
    }
  };

  // SMTP Swarm: Test Account Connection
  const handleTestSmtpAccount = async (account) => {
    setIsTestingAccount(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/smtp-accounts/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: account.email,
          app_password: account.app_password || 'dnbmziwbtrfgfeht'
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ Connection verified! Account ${account.email} authenticated successfully with Google SMTP (Port 587 TLS).`);
      } else {
        alert(`❌ Connection test failed for ${account.email}:\n${data.error || data.message}`);
      }
    } catch (err) {
      alert(`Error testing account: ${err.message}`);
    } finally {
      setIsTestingAccount(false);
    }
  };

  // SMTP Swarm: Delete Account
  const handleDeleteSmtpAccount = async (accountId, accountEmail) => {
    if (!window.confirm(`Remove ${accountEmail} from the SMTP Swarm?`)) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/smtp-accounts/${accountId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        fetchData();
      } else {
        alert(`Notice: ${data.detail || 'Could not delete account'}`);
      }
    } catch (err) {
      alert(`Error deleting account: ${err.message}`);
    }
  };

  // Athlete Email Hub: Copy All Emails to Clipboard
  const handleCopyAllEmails = (formatted = false) => {
    const list = athletes.filter(a => a.email && a.email.includes('@'));
    if (list.length === 0) {
      alert('No email addresses found.');
      return;
    }
    let text = '';
    if (formatted) {
      text = list.map(a => `"${a.name}" <${a.email}>`).join(',\n');
    } else {
      text = list.map(a => a.email).join(', ');
    }
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedEmailsToast(`✅ Copied ${list.length} athlete emails to clipboard!`);
      setTimeout(() => setCopiedEmailsToast(null), 4000);
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

  // Export Clean Text List (One email per line)
  const exportEmailsTxt = () => {
    const list = athletes.filter(a => a.email && a.email.includes('@'));
    if (list.length === 0) {
      alert('No emails to export.');
      return;
    }
    const content = list.map(a => a.email).join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `RecDebut_Athlete_Emails_${new Date().toISOString().slice(0, 10)}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Categorize Athletes
  const pendingAthletes = athletes.filter(a => !a.status || a.status === 'Pending' || a.status === 'Selected');
  const messagedAthletes = athletes.filter(a => a.status === 'Contacted' || a.status === 'Messaged');
  const athletesWithEmails = athletes.filter(a => a.email && a.email.includes('@'));

  // Filter current active table
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
        (item.email && item.email.toLowerCase().includes(term)) ||
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
  const activeSmtpCount = smtpAccounts.filter(a => a.active).length || 1;
  const swarmDailyCapacity = quotaStatus.swarm_daily_ceiling || (activeSmtpCount * 400);

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
                  Dual MMS & SMTP Swarm Gateway
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
              <div>Caller ID / Callback: <strong style={{ color: '#10b981' }}>Dennis Bell (616-291-5227)</strong></div>
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
        <div style={{ maxWidth: '1400px', margin: '20px auto 0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          
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
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ fontSize: '28px' }}>📧</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#38bdf8' }}>{athletesWithEmails.length}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Clean Athlete Emails Saved</div>
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
            <div style={{ fontSize: '28px' }}>⚡</div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: '900', color: '#10b981' }}>{swarmDailyCapacity}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Swarm Cap / Day ({activeSmtpCount} Gmail{activeSmtpCount > 1 ? 's' : ''})</div>
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
            { id: 'syndication', label: '🌐 Mass Syndication & Outbox', badge: `${pendingAthletes.length} Ready` },
            { id: 'emails', label: '📧 Athlete Email Hub & SMTP Swarm', badge: `${athletesWithEmails.length} Emails • ${activeSmtpCount} Gmails` },
            { id: 'campaigns', label: '📢 Campaign Activity & Dispatched Logs', badge: `${campaigns.length} Blasts` },
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

        {/* ── TAB 1: MASS SYNDICATION & OUTBOX (PRIMARY OPERATIONAL TAB) ────────── */}
        {activeTab === 'syndication' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

            {/* Campaign Mode Switcher Banner */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '2px solid rgba(245, 132, 38, 0.5)',
              padding: '18px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '24px' }}>🎯</span>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '17px', fontWeight: '900', color: '#ffffff' }}>
                      CAMPAIGN BROADCAST MODE: {campaignType === 'email' ? '📧 DIRECT EMAIL INBOX BLAST' : '📱 CARRIER MMS TEXT BLAST'}
                    </h3>
                    <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                      Choose whether to send directly to athlete mobile phones via MMS or directly to their email inboxes via the SMTP Swarm. Both modes are 100% free ($0.00).
                    </p>
                  </div>
                </div>
              </div>

              {/* Mode Toggle Buttons */}
              <div style={{ display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '10px' }}>
                <button
                  onClick={() => setCampaignType('sms')}
                  style={{
                    backgroundColor: campaignType === 'sms' ? '#F58426' : 'transparent',
                    color: campaignType === 'sms' ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: '800',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.15s'
                  }}
                >
                  <span>📱 Phone MMS Blast</span>
                  <span style={{ fontSize: '10px', opacity: 0.8 }}>({pendingAthletes.length})</span>
                </button>

                <button
                  onClick={() => setCampaignType('email')}
                  style={{
                    backgroundColor: campaignType === 'email' ? '#006BB6' : 'transparent',
                    color: campaignType === 'email' ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: '6px',
                    fontSize: '13px',
                    fontWeight: '800',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.15s'
                  }}
                >
                  <span>📧 Email Inbox Blast</span>
                  <span style={{ fontSize: '10px', opacity: 0.8 }}>({athletesWithEmails.length})</span>
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
              
              {/* Email Subject Line (when Email mode selected) */}
              {campaignType === 'email' && (
                <div style={{ marginBottom: '18px', background: 'rgba(0, 107, 182, 0.12)', border: '1px solid rgba(0, 107, 182, 0.4)', borderRadius: '8px', padding: '14px 18px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#38bdf8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    📧 Email Subject Line (Appears in Student-Athlete's Inbox)
                  </label>
                  <input
                    type="text"
                    value={emailSubject}
                    onChange={(e) => setEmailSubject(e.target.value)}
                    placeholder="Subject line..."
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '6px',
                      backgroundColor: '#07101e',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      color: '#ffffff',
                      fontSize: '14px',
                      fontWeight: '600',
                      boxSizing: 'border-box'
                    }}
                  />
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px', display: 'flex', gap: '14px' }}>
                    <span>From: <strong style={{ color: '#ffffff' }}>Dennis Bell (616-291-5227) &lt;dbell002@sbcglobal.net&gt;</strong></span>
                    <span>•</span>
                    <span>Reply-To: <strong style={{ color: '#10b981' }}>dbell002@sbcglobal.net</strong> (Replies go directly to Dennis)</span>
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                    📝 Recruitment Outreach Script
                  </h3>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '3px' }}>
                    Caller ID / Callback: <strong style={{ color: '#10b981' }}>Dennis Bell (616-291-5227)</strong> • dbell002@sbcglobal.net • Full Multi-Paragraph Delivery
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
                placeholder="Paste or write your custom recruitment message script here..."
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

              {/* Character & Test Dispatch Telemetry */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px', fontSize: '12px', color: '#94a3b8', flexWrap: 'wrap', gap: '10px' }}>
                <div>
                  <span>Length: <strong style={{ color: '#F58426' }}>{messageScript.length}</strong> characters</span>
                  <span style={{ margin: '0 8px' }}>•</span>
                  <span>Personalization: <strong>Auto-tailored to each athlete</strong> (use <code style={{ color: '#38bdf8' }}>{"{first_name}"}</code> or auto-prepends <em>"Hey [Name],"</em>)</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {campaignType === 'email' ? (
                    <>
                      <input
                        type="email"
                        value={testEmail}
                        onChange={(e) => setTestEmail(e.target.value)}
                        placeholder="Test Email Address"
                        style={{
                          backgroundColor: '#07101e',
                          color: '#ffffff',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          borderRadius: '6px',
                          padding: '6px 10px',
                          fontSize: '12px',
                          width: '180px'
                        }}
                      />
                      <button
                        onClick={handleSendTestDispatch}
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
                        {isSendingTest ? 'Sending Email...' : '🧪 Send Test Email to Inbox'}
                      </button>
                    </>
                  ) : (
                    <>
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
                          width: '130px'
                        }}
                      />
                      <button
                        onClick={handleSendTestDispatch}
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
                        {isSendingTest ? 'Sending MMS...' : '🧪 Send Test to My Phone'}
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* ── BATCH PACING & SMTP SWARM POWER STRIP ────────────────────── */}
              <div style={{
                marginTop: '18px',
                background: '#07101e',
                borderRadius: '10px',
                border: '1px solid rgba(245, 132, 38, 0.3)',
                padding: '16px 20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '20px' }}>⚡</span>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: '800', color: '#ffffff' }}>
                        SMTP Account Swarm & Daily Batch Pacing Meter
                      </div>
                      <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                        Pool: <strong style={{ color: '#10b981' }}>{activeSmtpCount} active Gmail account(s)</strong> • Combined capacity: <strong style={{ color: '#F58426' }}>{swarmDailyCapacity} messages/day</strong> ($0.00 Free)
                      </div>
                    </div>
                  </div>

                  {/* Quota Gauge Tag & Swarm Management Button */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{
                      backgroundColor: 'rgba(16, 185, 129, 0.15)',
                      border: '1px solid #10b981',
                      color: '#10b981',
                      fontSize: '12px',
                      fontWeight: '800',
                      padding: '5px 12px',
                      borderRadius: '6px'
                    }}>
                      🟢 Swarm Pool: {swarmDailyCapacity} Capacity/Day across {activeSmtpCount} Gmail(s)
                    </span>

                    <button
                      onClick={() => handleTabChange('emails')}
                      style={{
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        color: '#cbd5e1',
                        padding: '5px 12px',
                        borderRadius: '6px',
                        fontSize: '11px',
                        fontWeight: '700',
                        cursor: 'pointer'
                      }}
                    >
                      ⚙️ Manage Swarm Accounts
                    </button>
                  </div>
                </div>

                {/* Progress Bar for Daily Capacity */}
                <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, (((quotaStatus.sent_last_24h || 0) / (swarmDailyCapacity || 400)) * 100))}%`,
                    height: '100%',
                    backgroundColor: '#10b981',
                    transition: 'width 0.4s ease'
                  }} />
                </div>

                {/* Batch Size Selector Presets & Launch Controls */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '12px', color: '#cbd5e1', fontWeight: '700' }}>Select Batch Size:</span>
                    {[
                      { size: 400, label: '🟢 400 (Single Account Cap)' },
                      { size: 250, label: '🟡 250' },
                      { size: 100, label: '🔵 100' },
                      { size: pendingAthletes.length, label: `⚡ All Remaining (${pendingAthletes.length})` }
                    ].map(preset => (
                      <button
                        key={preset.label}
                        onClick={() => setBatchSize(preset.size)}
                        style={{
                          backgroundColor: batchSize === preset.size ? '#F58426' : 'rgba(255, 255, 255, 0.06)',
                          color: batchSize === preset.size ? '#ffffff' : '#cbd5e1',
                          border: batchSize === preset.size ? '1px solid #F58426' : '1px solid rgba(255, 255, 255, 0.15)',
                          padding: '5px 12px',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: '700',
                          cursor: 'pointer'
                        }}
                      >
                        {preset.label}
                      </button>
                    ))}

                    <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '6px' }}>
                      📅 At {batchSize} / day: ~{Math.ceil(pendingAthletes.length / (batchSize || 1))} days to finish roster
                    </span>
                  </div>

                  {/* Primary Buttons */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button
                      onClick={handleStageBroadcast}
                      disabled={isStaging}
                      style={{
                        backgroundColor: '#F58426',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '8px 16px',
                        fontSize: '12px',
                        fontWeight: '800',
                        cursor: isStaging ? 'not-allowed' : 'pointer',
                        opacity: isStaging ? 0.6 : 1
                      }}
                    >
                      {isStaging ? 'Staging...' : `📋 Preview Batch of ${Math.min(batchSize, pendingAthletes.length)}`}
                    </button>

                    <button
                      onClick={() => handleLaunchLiveBroadcast()}
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
                      {isBroadcastingLive 
                        ? '🚀 Broadcasting...' 
                        : `🚀 LAUNCH BATCH (${Math.min(batchSize, pendingAthletes.length)} ATHLETES)`}
                    </button>

                    {/* 1-Click Swarm Blast Button */}
                    <button
                      onClick={() => handleLaunchLiveBroadcast(pendingAthletes.length)}
                      disabled={isBroadcastingLive || pendingAthletes.length === 0}
                      title="Dispatches to all remaining athletes across all connected Gmail accounts automatically in a single day"
                      style={{
                        backgroundColor: '#8b5cf6',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '8px 18px',
                        fontSize: '13px',
                        fontWeight: '900',
                        cursor: (isBroadcastingLive || pendingAthletes.length === 0) ? 'not-allowed' : 'pointer',
                        boxShadow: '0 4px 14px rgba(139, 92, 246, 0.4)',
                        opacity: (isBroadcastingLive || pendingAthletes.length === 0) ? 0.6 : 1,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <span>⚡ 1-Click Swarm Blast (All {pendingAthletes.length} in 1 Day)</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Live Broadcast In-Progress Banner */}
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
                          Live Broadcast Active ({broadcastProgress.campaign_type === 'email' ? 'Direct Email' : 'MMS'} Mode)
                        </div>
                        <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px' }}>
                          {broadcastProgress.sent || 0} of {broadcastProgress.total || pendingAthletes.length} sent ({broadcastProgress.progress_pct || 0}%)
                          {broadcastProgress.current_account ? ` • Sender: ${broadcastProgress.current_account}` : ''}
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

                  {/* Progress Bar */}
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
                      Sample Staged Athletes: {stagedResult.preview_recipients.map(r => `${r.name} (${campaignType === 'email' ? r.email : r.phone})`).join(', ')}...
                    </div>
                  )}

                  {stagedResult.sample_personalized_message && (
                    <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(0, 107, 182, 0.15)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '8px', fontSize: '12px', color: '#e2e8f0' }}>
                      <strong style={{ color: '#38bdf8' }}>📱 Live Personalized Sample ({stagedResult.preview_recipients?.[0]?.name || 'First Recipient'}):</strong>
                      <div style={{ marginTop: '6px', fontStyle: 'italic', color: '#f8fafc', whiteSpace: 'pre-line', maxHeight: '120px', overflowY: 'auto' }}>
                        {stagedResult.sample_personalized_message}
                      </div>
                    </div>
                  )}

                  <div style={{ marginTop: '14px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <button
                      onClick={() => handleLaunchLiveBroadcast()}
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
                    🛡️ Coach Exclusion Shield Active (Zero Coaches on Page)
                  </div>
                </div>

                {/* Search Bar & Export Buttons */}
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search name, phone, email, school..."
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
                    📥 Export Athletes (CSV)
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
                      <th style={{ padding: '12px 14px' }}>Email Address</th>
                      <th style={{ padding: '12px 14px' }}>High School / Club</th>
                      <th style={{ padding: '12px 14px' }}>Grad Year</th>
                      <th style={{ padding: '12px 14px' }}>Status</th>
                      <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {isLoading ? (
                      <tr>
                        <td colSpan={8} style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                          Loading records...
                        </td>
                      </tr>
                    ) : displayList.length === 0 ? (
                      <tr>
                        <td colSpan={8} style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
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
                            <td style={{ padding: '10px 14px', color: item.email ? '#34d399' : '#64748b', fontSize: '12px' }}>
                              {item.email || '—'}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                              {item.high_school || item.sport || 'Basketball'}
                            </td>
                            <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                              {item.grad_year || '2026'}
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
                  Showing first 150 of {displayList.length} records. Use the search bar above to filter specific names or schools.
                </div>
              )}

            </div>

          </div>
        )}

        {/* ── TAB 2: ATHLETE EMAIL HUB & SMTP SWARM (NEW EXPANDED TAB) ─────────────── */}
        {activeTab === 'emails' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

            {/* Email Export & Telemetry Hero Card */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(0, 107, 182, 0.15), rgba(7, 16, 30, 0.95))',
              border: '2px solid #006BB6',
              borderRadius: '12px',
              padding: '24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '20px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '32px' }}>📥</span>
                  <div>
                    <h2 style={{ margin: 0, fontSize: '22px', fontWeight: '900', color: '#ffffff' }}>
                      2,107 Student-Athlete Email Addresses Cleaned & Verified
                    </h2>
                    <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: '#cbd5e1' }}>
                      All athlete email records have been extracted, typo-repaired (@gmailcom, @yahoocom, etc.), and saved directly in your database and Pictures directory.
                    </p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  onClick={() => handleCopyAllEmails(false)}
                  style={{
                    backgroundColor: '#10b981',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '10px 18px',
                    fontSize: '13px',
                    fontWeight: '800',
                    cursor: 'pointer',
                    boxShadow: '0 4px 14px rgba(16, 185, 129, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  📋 Copy All 2,107 Emails (For BCC / Blast)
                </button>

                <button
                  onClick={() => exportCsv(athletesWithEmails, 'RecDebut_Athlete_Emails_Master', false)}
                  style={{
                    backgroundColor: '#006BB6',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '10px 16px',
                    fontSize: '13px',
                    fontWeight: '800',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  📥 Download CSV (Full Data)
                </button>

                <button
                  onClick={exportEmailsTxt}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    color: '#ffffff',
                    borderRadius: '8px',
                    padding: '10px 16px',
                    fontSize: '13px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  📄 Download .TXT (1 Per Line)
                </button>
              </div>
            </div>

            {copiedEmailsToast && (
              <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#10b981', padding: '12px 18px', borderRadius: '8px', fontSize: '13px', fontWeight: '800' }}>
                {copiedEmailsToast}
              </div>
            )}

            {/* ── SMTP ACCOUNT SWARM MANAGER ────────────────────────────────────────── */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '24px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '14px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '22px' }}>⚡</span>
                    <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                      Connected Gmail SMTP Swarm Accounts ({smtpAccounts.length})
                    </h3>
                  </div>
                  <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                    Google allows ~400–500 emails/day per Gmail account. By adding multiple Gmail accounts, the system rotates across them automatically so all 2,099 athletes can be messaged in a single day!
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={() => setShowAppPasswordGuide(!showAppPasswordGuide)}
                    style={{
                      background: 'rgba(245, 132, 38, 0.15)',
                      border: '1px solid #F58426',
                      color: '#F58426',
                      padding: '8px 14px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer'
                    }}
                  >
                    📖 How to Get App Password (30s Guide)
                  </button>

                  <button
                    onClick={() => setShowAddAccountModal(true)}
                    style={{
                      backgroundColor: '#10b981',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '8px 16px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    ➕ Connect Another Gmail Account
                  </button>
                </div>
              </div>

              {/* Collapsible App Password Guide */}
              {showAppPasswordGuide && (
                <div style={{
                  background: '#07101e',
                  border: '1px solid rgba(245, 132, 38, 0.4)',
                  borderRadius: '10px',
                  padding: '18px 20px',
                  marginBottom: '18px',
                  fontSize: '13px',
                  color: '#cbd5e1',
                  lineHeight: '1.6'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <strong style={{ color: '#F58426', fontSize: '14px' }}>
                      🔑 How to Generate a Free 16-Character Google App Password:
                    </strong>
                    <button
                      onClick={() => setShowAppPasswordGuide(false)}
                      style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                    >
                      ✕ Close Guide
                    </button>
                  </div>
                  <ol style={{ margin: '8px 0', paddingLeft: '20px' }}>
                    <li>Go to Google Account Security: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" style={{ color: '#38bdf8', fontWeight: '700' }}>myaccount.google.com/apppasswords ↗</a></li>
                    <li>Ensure <strong>2-Step Verification</strong> is turned ON for your Google account.</li>
                    <li>In the "App name" field, type <strong>RecDebut</strong> and click <strong>Create</strong>.</li>
                    <li>Google will display a 16-letter password (e.g. <code style={{ color: '#10b981' }}>dnbm ziwb trfg feht</code>).</li>
                    <li>Click <strong>"+ Connect Another Gmail Account"</strong> below, paste the email and 16-letter password. Done!</li>
                  </ol>
                  <div style={{ marginTop: '8px', fontSize: '12px', color: '#94a3b8' }}>
                    💡 <strong>Tip:</strong> Adding 5 more accounts will give you 2,400 daily capacity, enabling 100% of all 2,099 student-athletes to be blasted in a single day with 1 click!
                  </div>
                </div>
              )}

              {/* Accounts List Table */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.15)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>
                      <th style={{ padding: '10px 14px' }}>Sender Gmail Address</th>
                      <th style={{ padding: '10px 14px' }}>Label / Nickname</th>
                      <th style={{ padding: '10px 14px' }}>App Password</th>
                      <th style={{ padding: '10px 14px' }}>Safe Daily Limit</th>
                      <th style={{ padding: '10px 14px' }}>Status</th>
                      <th style={{ padding: '10px 14px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {smtpAccounts.map((acct) => (
                      <tr key={acct.id || acct.email} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                        <td style={{ padding: '12px 14px', fontWeight: '700', color: '#ffffff' }}>
                          {acct.email}
                        </td>
                        <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                          {acct.label || acct.email}
                        </td>
                        <td style={{ padding: '12px 14px', color: '#94a3b8', fontFamily: 'monospace' }}>
                          {acct.app_password_masked || '••••••••••••••••'}
                        </td>
                        <td style={{ padding: '12px 14px', color: '#F58426', fontWeight: '700' }}>
                          {acct.daily_limit || 400} msgs/day
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span style={{
                            backgroundColor: acct.active ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                            color: acct.active ? '#10b981' : '#f87171',
                            fontSize: '11px',
                            fontWeight: '800',
                            padding: '3px 8px',
                            borderRadius: '4px'
                          }}>
                            {acct.active ? '🟢 Active in Swarm' : '🔴 Inactive'}
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '8px' }}>
                            <button
                              onClick={() => handleTestSmtpAccount(acct)}
                              disabled={isTestingAccount}
                              style={{
                                background: 'rgba(0, 107, 182, 0.15)',
                                border: '1px solid #006BB6',
                                color: '#38bdf8',
                                padding: '4px 10px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                cursor: 'pointer'
                              }}
                            >
                              🧪 Test Login
                            </button>
                            {smtpAccounts.length > 1 && (
                              <button
                                onClick={() => handleDeleteSmtpAccount(acct.id, acct.email)}
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
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Modal: Add New Gmail Account to Swarm */}
            {showAddAccountModal && (
              <div style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0,0,0,0.75)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 9999,
                padding: '20px'
              }}>
                <div style={{
                  background: '#0e1c31',
                  border: '2px solid #F58426',
                  borderRadius: '12px',
                  maxWidth: '520px',
                  width: '100%',
                  padding: '24px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                      ➕ Connect Gmail Account to SMTP Swarm
                    </h3>
                    <button
                      onClick={() => setShowAddAccountModal(false)}
                      style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '18px', cursor: 'pointer' }}
                    >
                      ✕
                    </button>
                  </div>

                  <form onSubmit={handleSaveSmtpAccount} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                        Gmail Address *
                      </label>
                      <input
                        type="email"
                        required
                        value={newAccount.email}
                        onChange={(e) => setNewAccount({ ...newAccount, email: e.target.value })}
                        placeholder="e.g. DennisBellOutreach@gmail.com"
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          backgroundColor: '#07101e',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          color: '#ffffff',
                          fontSize: '13px',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                        16-Character Google App Password *
                      </label>
                      <input
                        type="password"
                        required
                        value={newAccount.app_password}
                        onChange={(e) => setNewAccount({ ...newAccount, app_password: e.target.value })}
                        placeholder="e.g. dnbmziwbtrfgfeht"
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          backgroundColor: '#07101e',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          color: '#ffffff',
                          fontSize: '13px',
                          fontFamily: 'monospace',
                          boxSizing: 'border-box'
                        }}
                      />
                      <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                        Get from Google: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" style={{ color: '#38bdf8' }}>myaccount.google.com/apppasswords ↗</a>
                      </div>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                        Label / Nickname (Optional)
                      </label>
                      <input
                        type="text"
                        value={newAccount.label}
                        onChange={(e) => setNewAccount({ ...newAccount, label: e.target.value })}
                        placeholder="e.g. Dennis Secondary Gmail"
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          backgroundColor: '#07101e',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          color: '#ffffff',
                          fontSize: '13px',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#cbd5e1', marginBottom: '4px' }}>
                        Safe Daily Limit (Default: 400 messages/day)
                      </label>
                      <input
                        type="number"
                        min="50"
                        max="480"
                        value={newAccount.daily_limit}
                        onChange={(e) => setNewAccount({ ...newAccount, daily_limit: parseInt(e.target.value, 10) || 400 })}
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          backgroundColor: '#07101e',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          color: '#ffffff',
                          fontSize: '13px',
                          boxSizing: 'border-box'
                        }}
                      />
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                      <button
                        type="button"
                        onClick={() => setShowAddAccountModal(false)}
                        style={{
                          background: 'rgba(255, 255, 255, 0.08)',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          color: '#ffffff',
                          borderRadius: '6px',
                          padding: '8px 16px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        Cancel
                      </button>

                      <button
                        type="submit"
                        disabled={isSavingAccount}
                        style={{
                          backgroundColor: '#10b981',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '6px',
                          padding: '8px 20px',
                          fontSize: '13px',
                          fontWeight: '800',
                          cursor: isSavingAccount ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {isSavingAccount ? 'Connecting...' : 'Connect to Swarm'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* ── SEARCHABLE ATHLETE EMAIL ROSTER TABLE ───────────────────────────── */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '20px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '14px' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                    Student-Athlete Clean Email Directory ({athletesWithEmails.length})
                  </h3>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                    Verified student email addresses with associated high school and sport.
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={emailSearchTerm}
                    onChange={(e) => setEmailSearchTerm(e.target.value)}
                    placeholder="Search name, email, school..."
                    style={{
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '7px 12px',
                      fontSize: '12px',
                      width: '260px'
                    }}
                  />
                </div>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.15)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>
                      <th style={{ padding: '12px 14px' }}>Athlete Name</th>
                      <th style={{ padding: '12px 14px' }}>Verified Email Address</th>
                      <th style={{ padding: '12px 14px' }}>Phone Number</th>
                      <th style={{ padding: '12px 14px' }}>High School / Team</th>
                      <th style={{ padding: '12px 14px' }}>Sport</th>
                      <th style={{ padding: '12px 14px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {athletesWithEmails.filter(a => {
                      if (!emailSearchTerm.trim()) return true;
                      const term = emailSearchTerm.toLowerCase();
                      return a.name.toLowerCase().includes(term) || a.email.toLowerCase().includes(term) || (a.high_school && a.high_school.toLowerCase().includes(term));
                    }).slice(0, 100).map((a, idx) => (
                      <tr key={a.id || idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', backgroundColor: idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent' }}>
                        <td style={{ padding: '10px 14px', fontWeight: '700', color: '#ffffff' }}>
                          {a.name}
                        </td>
                        <td style={{ padding: '10px 14px', color: '#38bdf8', fontFamily: 'monospace' }}>
                          {a.email}
                        </td>
                        <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                          {a.phone}
                        </td>
                        <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                          {a.high_school || '—'}
                        </td>
                        <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                          {a.sport || 'Basketball'}
                        </td>
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
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

        {/* ── TAB 3: CAMPAIGN ACTIVITY & TEXTS SENT ─────────────────────────────────── */}
        {activeTab === 'campaigns' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '28px' }}>
            
            {/* Left: Broadcast History Ledger */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#ffffff' }}>
                    Broadcast History & Outbound Log
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
                    Mass SMS and Email broadcasts sent with Dennis Bell's message will log delivery telemetry here.
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
                  Standard Outreach Script
                </h3>
                <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.5', margin: '0 0 14px 0' }}>
                  The verified recruitment announcement approved by Dennis Bell for candidate student-athletes.
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
                  <strong style={{ color: '#38bdf8' }}>Identity & Reply Assurance:</strong>
                  <div style={{ marginTop: '4px' }}>
                    Messages sent through both carrier MMS and SMTP Swarm gateways display <strong>Dennis Bell (616-291-5227)</strong> as caller ID / sender address so athlete callbacks and direct replies route to Dennis Bell at <strong>616-291-5227</strong> and <strong>dbell002@sbcglobal.net</strong>.
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ── TAB 4: STUDENT-ATHLETE MASTER ROSTER ─────────────────────────────────── */}
        {activeTab === 'roster' && (
          <div style={{ background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#ffffff' }}>
                  Student-Athlete Master Roster ({athletes.length})
                </h2>
                <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                  Complete database of candidate athletes with clean phone numbers, verified emails, high schools, and recruitment status.
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
                    <th style={{ padding: '12px 14px' }}>Email</th>
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
                    return a.name.toLowerCase().includes(term) || a.phone.includes(term) || (a.email && a.email.toLowerCase().includes(term)) || (a.high_school && a.high_school.toLowerCase().includes(term));
                  }).slice(0, 100).map((a, idx) => (
                    <tr key={a.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', backgroundColor: idx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent' }}>
                      <td style={{ padding: '10px 14px', color: '#64748b' }}>#{a.id}</td>
                      <td style={{ padding: '10px 14px', fontWeight: '700', color: '#ffffff' }}>{a.name}</td>
                      <td style={{ padding: '10px 14px', color: '#38bdf8', fontFamily: 'monospace' }}>{a.phone}</td>
                      <td style={{ padding: '10px 14px', color: a.email ? '#34d399' : '#64748b' }}>{a.email || '—'}</td>
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

        {/* ── TAB 5: SUBMIT NEW ATHLETE CANDIDATE ───────────────────────────────────── */}
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

        {/* ── TAB 6: 850 COACHES NETWORK ─────────────────────────────────────────── */}
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
'''

# Write to all primary and twin locations
targets = [
    Path("c:/AI-BS/frontend/src/components/clients/RecreationalDebut.jsx"),
    Path("c:/AI-BS/frontend/src/components/clients/DennisBellPortal.jsx"),
    Path("c:/AI-BS/frontend/src/clients/RecreationalDebut.jsx"),
    Path("c:/AI-BS/frontend/src/clients/DennisBellPortal.jsx")
]

for t in targets:
    t.parent.mkdir(parents=True, exist_ok=True)
    with open(t, "w", encoding="utf-8") as f:
        f.write(jsx_content)
    print(f"Updated {t}")

print("All primary targets updated successfully!")
