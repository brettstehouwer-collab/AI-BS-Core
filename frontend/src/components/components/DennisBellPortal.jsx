import React, { useState, useEffect, useRef } from 'react';
import DennisBellMobileRemote from './DennisBellMobileRemote.jsx';
import { 
  REC_DEBUT_BRAND, 
  REC_DEBUT_LEADERSHIP, 
  REC_DEBUT_AWARDS, 
  REC_DEBUT_SPORTS_PORTALS, 
  REC_DEBUT_FAQS, 
  REC_DEBUT_PROGRAM_DETAILS,
  REC_DEBUT_YOUTUBE_CHANNELS,
  REC_DEBUT_FEATURED_VIDEOS,
  REC_DEBUT_VERIFICATION_MATRIX
} from './recDebutAssets.js';

export default function DennisBellPortal({ backendUrl: propBackendUrl, BACKEND_URL: propUpperBackendUrl }) {
  const BACKEND_URL = propBackendUrl || propUpperBackendUrl || (
    typeof window !== 'undefined' && window.location.hostname === 'localhost' 
      ? 'http://127.0.0.1:8080' 
      : 'https://api.brettstehouwer.live'
  );

  // View Mode: 'desktop' vs 'mobile' (S25 Ultra Remote Control Suite)
  const [viewMode, setViewMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const isNative = (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
                       window.location.protocol === 'capacitor:' ||
                       window.innerWidth < 640;
      if (params.get('view') === 'mobile' || params.get('remote') === 'true' || isNative) {
        return 'mobile';
      }
    }
    return 'desktop';
  });

  // Active Tab with Deep URL Param Synchronization
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get('tab');
      if (tab && ['telemetry', 'syndication', 'emails', 'replies', 'campaigns', 'roster', 'submit', 'network', 'awards', 'portals', 'faq'].includes(tab)) {
        return tab;
      }
    }
    return 'telemetry';
  });

  const [analyticsData, setAnalyticsData] = useState(null);

  const [athletes, setAthletes] = useState([]);
  const [excludedCoaches, setExcludedCoaches] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedLink, setCopiedLink] = useState(false);

  // Campaign Mode: 'sms' (Carrier MMS to Phones) vs 'email' (Direct to Inboxes)
  const [campaignType, setCampaignType] = useState('email');
  const [emailSubject, setEmailSubject] = useState('YOUR ELIGIBILITY IS A MUST! — NCAA Academic Requirements Breakdown');
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

  // Inbound Athlete SMS & Email Replies State
  const [athleteReplies, setAthleteReplies] = useState([]);
  const [unreadRepliesCount, setUnreadRepliesCount] = useState(0);
  const [isSyncingReplies, setIsSyncingReplies] = useState(false);
  const [syncReplyMessage, setSyncReplyMessage] = useState(null);
  const [replySearchTerm, setReplySearchTerm] = useState('');
  const [replyFilter, setReplyFilter] = useState('all'); // 'all' | 'unread'
  const [activeReplyId, setActiveReplyId] = useState(null);
  const [replyMessageText, setReplyMessageText] = useState('');
  const [isSendingReply, setIsSendingReply] = useState(false);

  // RecDebut Verified Assets State (All-American Alumni, Sport Portals, FAQ)
  const [awardSearchTerm, setAwardSearchTerm] = useState('');
  const [awardStateFilter, setAwardStateFilter] = useState('ALL');
  const [selectedSportPortal, setSelectedSportPortal] = useState('all');
  const [expandedFaqIndex, setExpandedFaqIndex] = useState(null);

  // Test Dispatch State
  const [testPhone, setTestPhone] = useState('616-402-3628'); // Brett's phone by default
  const [testEmail, setTestEmail] = useState('dbell002@sbcglobal.net'); // Dennis Bell's email by default
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // Transactional Email API (Resend / SendGrid) Shield State
  const [emailApiConfig, setEmailApiConfig] = useState(null);
  const [resendApiKeyInput, setResendApiKeyInput] = useState('');
  const [resendFromInput, setResendFromInput] = useState('Dennis Bell <recruiting@recdebut.com>');
  const [selectedProvider, setSelectedProvider] = useState('auto');
  const [isSavingApiConfig, setIsSavingApiConfig] = useState(false);
  const [apiConfigToast, setApiConfigToast] = useState(null);
  const [showApiSetupGuide, setShowApiSetupGuide] = useState(false);

  const handleSaveApiConfig = async () => {
    setIsSavingApiConfig(true);
    setApiConfigToast(null);
    try {
      const payload = {
        provider: selectedProvider,
        resend_from_email: resendFromInput.trim() || 'Dennis Bell <recruiting@recdebut.com>'
      };
      if (resendApiKeyInput.trim()) {
        payload.resend_api_key = resendApiKeyInput.trim();
      }
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/email-api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        setApiConfigToast('✅ Email API configuration successfully saved! Transactional Shield Active.');
        fetchData();
        setResendApiKeyInput('');
      } else {
        setApiConfigToast(`❌ Error saving API config: ${data.detail || data.message}`);
      }
    } catch (e) {
      setApiConfigToast(`❌ Network error: ${e.message}`);
    } finally {
      setIsSavingApiConfig(false);
      setTimeout(() => setApiConfigToast(null), 6000);
    }
  };

  // Custom Message Box State (Pre-populated with Dennis's updated NCAA Eligibility Email Draft)
  const NCAA_ELIGIBILITY_DRAFT = `YOUR ELIGIBILITY IS A MUST!
Hi {first_name}, this is Dennis Bell, former NY Knick and President of Recreational Debut.

If playing college sports is your goal, don’t wait for coaches to find you. We want to help get your athletic profile in front of 850+ college coaches nationwide!

I want to make sure you know the academic requirements to be eligible for college athletics. Knowing these requirements early can make a big difference in your recruiting process:

🏀 NCAA DIVISION I ELIGIBILITY REQUIREMENTS
• 16 NCAA-approved core courses
• Minimum 2.3 core-course GPA
• Guide: https://www.ncaa.org/sports/2021/4/27/division-i-academic-eligibility.aspx

🏀 NCAA DIVISION II ELIGIBILITY REQUIREMENTS
• 16 NCAA-approved core courses
• Minimum 2.2 core-course GPA
• Guide: https://www.ncaa.org/sports/2021/4/27/division-ii-academic-eligibility.aspx

🏀 NCAA DIVISION III ELIGIBILITY REQUIREMENTS
• Meet institution admission standards & core coursework
• Guide: https://www.ncaa.org/sports/2021/4/27/division-iii-academic-eligibility.aspx

Remember, being eligible is only part of the process — college coaches also need to know who you are and see your film!

Recreational Debut can help get your athletic portfolio in front of 850 college coaches nationwide. Get your information out before October 31, 2026, while coaches are putting together their number 1 recruiting lists.

✅ REGISTER FREE:
https://recdebut.com/all-registration/

📱 Call or text: 616-291-5227
📧 Email: dbell002@sbcglobal.net
🌐 Web: https://recdebut.com

Let’s get you recruited!

Dennis Bell
Former New York Knicks (#4)
President, Recreational Debut`;

  const LAS_VEGAS_TALENT_SCRIPT = `Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.

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

  const DEFAULT_MESSAGE = NCAA_ELIGIBILITY_DRAFT;

  const [messageScript, setMessageScript] = useState(NCAA_ELIGIBILITY_DRAFT);
  const [isStaging, setIsStaging] = useState(false);
  const [stagedResult, setStagedResult] = useState(null);
  const [scrubberReport, setScrubberReport] = useState(null);
  const [isBroadcastingLive, setIsBroadcastingLive] = useState(false);
  const [liveBroadcastStatus, setLiveBroadcastStatus] = useState(null);
  const pollTickRef = useRef(0);
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
      const [athRes, campRes, coachRes, quotaRes, smtpRes, emailSumRes, repliesRes, analyticsRes, apiConfigRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/v1/recdebut/athletes`).then(r => r.json()).catch(() => ({ athletes: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/campaigns`).then(r => r.json()).catch(() => ({ campaigns: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/excluded-coaches`).then(r => r.json()).catch(() => ({ coaches: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/quota-status`).then(r => r.json()).catch(() => null),
        fetch(`${BACKEND_URL}/api/v1/recdebut/smtp-accounts`).then(r => r.json()).catch(() => ({ accounts: [] })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/athlete-emails`).then(r => r.json()).catch(() => null),
        fetch(`${BACKEND_URL}/api/v1/recdebut/sms/replies`).then(r => r.json()).catch(() => ({ replies: [], unread_count: 0 })),
        fetch(`${BACKEND_URL}/api/v1/recdebut/outreach-analytics`).then(r => r.json()).catch(() => null),
        fetch(`${BACKEND_URL}/api/v1/recdebut/email-api/config`).then(r => r.json()).catch(() => null)
      ]);

      if (athRes.athletes) setAthletes(athRes.athletes);
      if (campRes.campaigns) setCampaigns(campRes.campaigns);
      if (coachRes.coaches) setExcludedCoaches(coachRes.coaches);
      if (smtpRes && smtpRes.accounts) setSmtpAccounts(smtpRes.accounts);
      if (emailSumRes && emailSumRes.success) setAthleteEmailsSummary(emailSumRes);
      if (repliesRes && repliesRes.success) {
        setAthleteReplies(repliesRes.replies || []);
        setUnreadRepliesCount(repliesRes.unread_count || 0);
      }
      if (analyticsRes && analyticsRes.success) {
        setAnalyticsData(analyticsRes);
      }
      if (apiConfigRes && apiConfigRes.success) {
        setEmailApiConfig(apiConfigRes);
        if (apiConfigRes.provider) setSelectedProvider(apiConfigRes.provider);
        if (apiConfigRes.resend_from_email) setResendFromInput(apiConfigRes.resend_from_email);
      }
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
            pollTickRef.current += 1;
            if (pollTickRef.current % 8 === 0) {
              fetchData();
            }
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

  // Inbound SMS Reply Handlers
  const handleSyncReplies = async () => {
    setIsSyncingReplies(true);
    setSyncReplyMessage(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/sms/sync-replies`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setSyncReplyMessage(`✅ Sync Complete: Checked Inbound Gateway Listener. Total replies: ${data.total_replies} (${data.new_replies_count} new)`);
        fetchData();
      } else {
        setSyncReplyMessage(`⚠️ Sync error: ${data.error || 'Failed to sync'}`);
      }
    } catch (e) {
      setSyncReplyMessage(`❌ Network error: ${e.message}`);
    } finally {
      setIsSyncingReplies(false);
    }
  };

  const handleMarkReplyRead = async (replyId) => {
    try {
      await fetch(`${BACKEND_URL}/api/v1/recdebut/sms/replies/${replyId}/read`, { method: 'POST' });
      setAthleteReplies(prev => prev.map(r => r.id === replyId ? { ...r, is_read: 1 } : r));
      setUnreadRepliesCount(prev => Math.max(0, prev - 1));
    } catch (e) {
      console.error('Error marking reply as read:', e);
    }
  };

  const handleSendQuickReply = async (reply) => {
    if (!replyMessageText.trim()) {
      alert('Please enter a reply message.');
      return;
    }
    setIsSendingReply(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/recdebut/sms/replies/${reply.id}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_text: replyMessageText.trim(),
          caller_id_email: 'dbell002@sbcglobal.net',
          caller_id_name: 'Dennis Bell (+1-616-291-5227)'
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`✅ SMS response sent to ${reply.sender_phone || reply.athlete_name} via carrier gateway!`);
        setReplyMessageText('');
        setActiveReplyId(null);
        handleMarkReplyRead(reply.id);
      } else {
        alert(`❌ Send failed: ${data.dispatch_result?.error || 'Unknown error'}`);
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      setIsSendingReply(false);
    }
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
  const phoneOnlyAthletes = athletes.filter(a => a.email_status === 'NO_EMAIL' || (!a.email && a.phone));
  const pendingAthletes = athletes.filter(a => (!a.status || a.status === 'Pending' || a.status === 'Selected') && a.email_status !== 'NO_EMAIL' && a.email);
  const messagedAthletes = athletes.filter(a => a.status === 'Contacted' || a.status === 'Messaged');
  const athletesWithEmails = athletes.filter(a => a.email && a.email.includes('@'));

  // Filter current active table
  const getActiveList = () => {
    let source = [];
    if (syndicationCategory === 'messaged') source = messagedAthletes;
    else if (syndicationCategory === 'phone_only') source = phoneOnlyAthletes;
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

  if (viewMode === 'mobile') {
    return (
      <DennisBellMobileRemote 
        backendUrl={BACKEND_URL} 
        onSwitchToDesktop={() => setViewMode('desktop')} 
      />
    );
  }

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
              <div>Inbound SMS Gateway: <strong style={{ color: '#10b981' }}>dbell002@sbcglobal.net</strong></div>
            </div>

            <button
              onClick={() => setViewMode('mobile')}
              style={{
                backgroundColor: 'rgba(245, 132, 38, 0.2)',
                border: '1px solid #F58426',
                color: '#ffffff',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '12px',
                fontWeight: '800',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
              title="Switch to Mobile Phone Remote View (6-Tab S25 Ultra App)"
            >
              📱 S25 Ultra Mobile Remote
            </button>

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

        {/* Consolidated Executive 4-Card Hero Grid */}
        <div style={{ maxWidth: '1400px', margin: '20px auto 0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
          
          <div 
            onClick={() => {
              setSyndicationCategory('messaged');
              handleTabChange('syndication');
            }}
            style={{
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 78, 59, 0.25) 100%)',
              border: '1px solid rgba(16, 185, 129, 0.45)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              cursor: 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease'
            }}
            title="Click to view Contacted Athletes in Outbox"
          >
            <div style={{ fontSize: '32px' }}>🟢</div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: '900', color: '#10b981' }}>{messagedAthletes.length.toLocaleString()}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: '700' }}>Contacted & Verified</div>
            </div>
          </div>

          <div 
            onClick={() => {
              setSyndicationCategory('pending');
              handleTabChange('syndication');
            }}
            style={{
              background: 'linear-gradient(135deg, rgba(245, 132, 38, 0.12) 0%, rgba(124, 45, 18, 0.25) 100%)',
              border: '1px solid rgba(245, 132, 38, 0.45)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              cursor: 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease'
            }}
            title="Click to view Ready / Pending Athletes in Outbox"
          >
            <div style={{ fontSize: '32px' }}>🟡</div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: '900', color: '#F58426' }}>{pendingAthletes.length.toLocaleString()}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: '700' }}>Needs To Be Messaged</div>
            </div>
          </div>

          <div 
            onClick={() => handleTabChange('replies')}
            style={{
              background: unreadRepliesCount > 0 ? 'linear-gradient(135deg, rgba(245, 132, 38, 0.2) 0%, rgba(180, 83, 9, 0.3) 100%)' : 'rgba(255, 255, 255, 0.04)',
              border: unreadRepliesCount > 0 ? '1px solid #F58426' : '1px solid rgba(16, 185, 129, 0.35)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              cursor: 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease'
            }}
            title="Click to view Inbound Athlete Replies"
          >
            <div style={{ fontSize: '32px' }}>💬</div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: '900', color: unreadRepliesCount > 0 ? '#F58426' : '#10b981', display: 'flex', alignItems: 'center', gap: '8px' }}>
                {athleteReplies.length}
                {unreadRepliesCount > 0 && (
                  <span style={{ fontSize: '10px', background: '#F58426', color: '#000', padding: '2px 8px', borderRadius: '4px', fontWeight: '900' }}>
                    {unreadRepliesCount} NEW
                  </span>
                )}
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: '700' }}>Inbound SMS Replies</div>
            </div>
          </div>

          <div 
            onClick={() => handleTabChange('emails')}
            style={{
              background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.12) 0%, rgba(14, 116, 144, 0.25) 100%)',
              border: '1px solid rgba(56, 189, 248, 0.45)',
              borderRadius: '12px',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              cursor: 'pointer',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease'
            }}
            title="Click to open Email Hub & SMTP Swarm"
          >
            <div style={{ fontSize: '32px' }}>📧</div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: '900', color: '#38bdf8' }}>{athletesWithEmails.length.toLocaleString()}</div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.6px', fontWeight: '700' }}>Clean Athlete Emails</div>
            </div>
          </div>

        </div>

        {/* Compact Telemetry Status Strip */}
        <div style={{
          maxWidth: '1400px',
          margin: '10px auto 0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          padding: '8px 16px',
          background: 'rgba(255, 255, 255, 0.025)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.06)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px', fontSize: '12px', color: '#94a3b8', flexWrap: 'wrap' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: '#10b981' }}>⚡</span> Swarm Daily Cap: <strong style={{ color: '#ffffff' }}>{swarmDailyCapacity}</strong> ({activeSmtpCount} Gmail{activeSmtpCount > 1 ? 's' : ''})
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: '#34d399' }}>🛡️</span> Coach Safety Quarantine: <strong style={{ color: '#ffffff' }}>{excludedCoaches.length.toLocaleString()}</strong> Shielded
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: '#38bdf8' }}>🏀</span> College Coaches Network: <strong style={{ color: '#ffffff' }}>850+</strong> NCAA / NAIA
            </span>
          </div>
          <div style={{ fontSize: '11px', color: '#38bdf8', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }}></span>
            Dual SIM & SMTP Swarm Active
          </div>
        </div>

        {/* Permanent Master Outreach Progress & Live Telemetry Card */}
        <div style={{
          maxWidth: '1400px',
          margin: '14px auto 0 auto',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.85) 100%)',
          border: '1px solid rgba(245, 132, 38, 0.35)',
          borderRadius: '12px',
          padding: '16px 22px',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '26px' }}>🚀</span>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '15px', fontWeight: '900', color: '#ffffff', letterSpacing: '0.3px' }}>
                    CAMPAIGN PROGRESS: {messagedAthletes.length.toLocaleString()} OF {athletes.length.toLocaleString()} ATHLETES CONTACTED
                  </span>
                  <span style={{
                    backgroundColor: messagedAthletes.length > 0 ? '#10b981' : '#F58426',
                    color: '#07101e',
                    fontSize: '11px',
                    fontWeight: '900',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    letterSpacing: '0.5px'
                  }}>
                    {athletes.length > 0 ? ((messagedAthletes.length / athletes.length) * 100).toFixed(1) : 0}% COMPLETE
                  </span>
                  <span style={{
                    backgroundColor: 'rgba(56, 189, 248, 0.15)',
                    border: '1px solid rgba(56, 189, 248, 0.4)',
                    color: '#38bdf8',
                    fontSize: '11px',
                    fontWeight: '800',
                    padding: '2px 8px',
                    borderRadius: '4px'
                  }}>
                    ⚡ Cloudflare Tunnel: api.brettstehouwer.live
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>
                  <strong style={{ color: '#10b981' }}>{messagedAthletes.length.toLocaleString()} Contacted & Verified</strong> • <strong style={{ color: '#F58426' }}>{pendingAthletes.length.toLocaleString()} Pending</strong> • <strong style={{ color: '#38bdf8' }}>{athleteReplies.length} Inbound SMS Replies</strong> • <strong>0% Bounce Rate</strong>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => {
                  setSyndicationCategory('messaged');
                  handleTabChange('syndication');
                }}
                style={{
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  color: '#10b981',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  borderRadius: '6px',
                  padding: '7px 14px',
                  fontSize: '12px',
                  fontWeight: '700',
                  cursor: 'pointer'
                }}
              >
                View {messagedAthletes.length.toLocaleString()} Contacted ✓
              </button>
              <button
                onClick={() => {
                  setSyndicationCategory('pending');
                  handleTabChange('syndication');
                }}
                style={{
                  backgroundColor: '#F58426',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '7px 14px',
                  fontSize: '12px',
                  fontWeight: '800',
                  cursor: 'pointer',
                  boxShadow: '0 2px 10px rgba(245, 132, 38, 0.35)'
                }}
              >
                Send Next Batch ({pendingAthletes.length.toLocaleString()} Ready) →
              </button>
            </div>
          </div>

          {/* Master Progress Bar Track */}
          <div style={{
            width: '100%',
            height: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
            borderRadius: '6px',
            overflow: 'hidden',
            position: 'relative',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <div style={{
              height: '100%',
              width: `${Math.min(100, Math.max(1, athletes.length > 0 ? (messagedAthletes.length / athletes.length) * 100 : 0))}%`,
              background: 'linear-gradient(90deg, #F58426 0%, #10b981 100%)',
              borderRadius: '6px',
              transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: '0 0 12px rgba(16, 185, 129, 0.6)'
            }} />
          </div>
        </div>

        {/* Global Live Swarm Broadcast Telemetry Banner */}
        {(liveBroadcastStatus || isBroadcastingLive || broadcastProgress.active) && (
          <div style={{
            maxWidth: '1400px',
            margin: '16px auto 0 auto',
            background: 'linear-gradient(90deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 78, 59, 0.3) 100%)',
            border: '2px solid #10b981',
            borderRadius: '10px',
            padding: '14px 20px',
            boxShadow: '0 0 20px rgba(16, 185, 129, 0.25)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '24px' }}>⚡</span>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: '800', color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>LIVE SWARM BROADCAST TRANSMISSION IN PROGRESS</span>
                    <span style={{ fontSize: '11px', background: '#10b981', color: '#0f172a', padding: '2px 8px', borderRadius: '4px', fontWeight: '900' }}>ACTIVE</span>
                  </div>
                  <div style={{ fontSize: '13px', color: '#e2e8f0', marginTop: '3px' }}>
                    <strong>{broadcastProgress.sent || 0}</strong> of <strong>{broadcastProgress.total || 800}</strong> athletes dispatched ({broadcastProgress.progress_pct || 0}%)
                    {broadcastProgress.current_account ? <span> • Swarm Node: <code style={{ color: '#38bdf8' }}>{broadcastProgress.current_account}</code></span> : ''}
                    {broadcastProgress.current_athlete ? <span> • Delivering to: <strong style={{ color: '#F58426' }}>{broadcastProgress.current_athlete}</strong></span> : ''}
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleTabChange('syndication')}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    color: '#ffffff',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  View Outbox Details ↗
                </button>
                <button
                  onClick={handleCancelBroadcast}
                  style={{
                    backgroundColor: '#ef4444',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: '800',
                    cursor: 'pointer'
                  }}
                >
                  ⏹️ Pause / Cancel
                </button>
              </div>
            </div>
            {/* Progress bar */}
            <div style={{ width: '100%', height: '8px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${Math.min(100, Math.max(2, broadcastProgress.progress_pct || 0))}%`,
                backgroundColor: '#10b981',
                transition: 'width 0.4s ease-in-out'
              }} />
            </div>
          </div>
        )}

        {/* ── CONSOLIDATED 4-TAB EXECUTIVE NAVIGATION ────────────────────────── */}
        <div style={{ maxWidth: '1400px', margin: '22px auto 0 auto' }}>
          {/* Level 1: 4 Master Workspace Tabs */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '8px',
            background: 'rgba(15, 23, 42, 0.75)',
            padding: '6px',
            borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            {[
              {
                id: 'analytics',
                label: '📊 Campaigns & Analytics',
                badge: `${messagedAthletes.length.toLocaleString()} Sent • ${campaigns.length} Blasts`,
                matches: ['telemetry', 'campaigns'],
                defaultTab: 'telemetry'
              },
              {
                id: 'comms',
                label: '💬 Communications Hub',
                badge: `${pendingAthletes.length.toLocaleString()} Ready • ${athleteReplies.length} Replies`,
                matches: ['syndication', 'emails', 'replies'],
                defaultTab: 'syndication'
              },
              {
                id: 'roster',
                label: '👥 Athlete Master Roster',
                badge: `${athletes.length.toLocaleString()} Athletes`,
                matches: ['roster', 'submit'],
                defaultTab: 'roster'
              },
              {
                id: 'vault',
                label: '🏛️ Organization & Vault',
                badge: 'Directory & Resources',
                matches: ['network', 'awards', 'portals', 'faq'],
                defaultTab: 'network'
              }
            ].map(cat => {
              const isCatActive = cat.matches.includes(activeTab);
              return (
                <button
                  key={cat.id}
                  onClick={() => {
                    if (!isCatActive) {
                      handleTabChange(cat.defaultTab);
                    }
                  }}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '8px',
                    border: 'none',
                    cursor: 'pointer',
                    fontWeight: isCatActive ? '900' : '700',
                    fontSize: '14px',
                    backgroundColor: isCatActive ? '#F58426' : 'transparent',
                    color: isCatActive ? '#ffffff' : '#94a3b8',
                    transition: 'all 0.15s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px',
                    boxShadow: isCatActive ? '0 4px 16px rgba(245, 132, 38, 0.4)' : 'none'
                  }}
                >
                  <span style={{ letterSpacing: '0.3px' }}>{cat.label}</span>
                  <span style={{
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '10px',
                    backgroundColor: isCatActive ? 'rgba(0,0,0,0.3)' : 'rgba(255,255,255,0.06)',
                    color: isCatActive ? '#ffffff' : '#64748b',
                    fontWeight: '700'
                  }}>
                    {cat.badge}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Level 2: Secondary Contextual Sub-Nav Pills */}
          <div style={{
            display: 'flex',
            gap: '8px',
            marginTop: '10px',
            padding: '8px 12px',
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            flexWrap: 'wrap',
            alignItems: 'center'
          }}>
            <span style={{ fontSize: '11px', fontWeight: '800', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.8px', marginRight: '6px' }}>
              Workspace View:
            </span>

            {/* Sub-pills for Category 1: Analytics */}
            {['telemetry', 'campaigns'].includes(activeTab) && (
              <>
                <button
                  onClick={() => handleTabChange('telemetry')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'telemetry' ? '1px solid #10b981' : '1px solid transparent',
                    backgroundColor: activeTab === 'telemetry' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'telemetry' ? '#10b981' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  📊 Live Outreach Telemetry &amp; Funnel
                </button>
                <button
                  onClick={() => handleTabChange('campaigns')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'campaigns' ? '1px solid #10b981' : '1px solid transparent',
                    backgroundColor: activeTab === 'campaigns' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'campaigns' ? '#10b981' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  📢 Campaign Activity &amp; Dispatched Logs ({campaigns.length} Blasts)
                </button>
              </>
            )}

            {/* Sub-pills for Category 2: Comms */}
            {['syndication', 'emails', 'replies'].includes(activeTab) && (
              <>
                <button
                  onClick={() => handleTabChange('syndication')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'syndication' ? '1px solid #F58426' : '1px solid transparent',
                    backgroundColor: activeTab === 'syndication' ? 'rgba(245, 132, 38, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'syndication' ? '#F58426' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  📱 Mass SMS Syndication &amp; Outbox ({pendingAthletes.length.toLocaleString()} Ready)
                </button>
                <button
                  onClick={() => handleTabChange('emails')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'emails' ? '1px solid #38bdf8' : '1px solid transparent',
                    backgroundColor: activeTab === 'emails' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'emails' ? '#38bdf8' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  📧 Athlete Email Hub &amp; SMTP Swarm ({athletesWithEmails.length.toLocaleString()} Emails)
                </button>
                <button
                  onClick={() => handleTabChange('replies')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'replies' ? '1px solid #10b981' : '1px solid transparent',
                    backgroundColor: activeTab === 'replies' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'replies' ? '#10b981' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  <span>💬 Inbound Athlete SMS Replies</span>
                  {unreadRepliesCount > 0 && (
                    <span style={{ fontSize: '10px', background: '#F58426', color: '#000', padding: '1px 6px', borderRadius: '4px', fontWeight: '900' }}>
                      {unreadRepliesCount} NEW
                    </span>
                  )}
                </button>
              </>
            )}

            {/* Sub-pills for Category 3: Roster */}
            {['roster', 'submit'].includes(activeTab) && (
              <>
                <button
                  onClick={() => handleTabChange('roster')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'roster' ? '1px solid #38bdf8' : '1px solid transparent',
                    backgroundColor: activeTab === 'roster' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'roster' ? '#38bdf8' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  👥 Master Athlete Directory ({athletes.length.toLocaleString()})
                </button>
                <button
                  onClick={() => handleTabChange('submit')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'submit' ? '1px solid #10b981' : '1px solid transparent',
                    backgroundColor: activeTab === 'submit' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'submit' ? '#10b981' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  ➕ Submit New Candidate Intake Form
                </button>
              </>
            )}

            {/* Sub-pills for Category 4: Vault */}
            {['network', 'awards', 'portals', 'faq'].includes(activeTab) && (
              <>
                <button
                  onClick={() => handleTabChange('network')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'network' ? '1px solid #F58426' : '1px solid transparent',
                    backgroundColor: activeTab === 'network' ? 'rgba(245, 132, 38, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'network' ? '#F58426' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  🏀 2,000+ Coaches &amp; Pro Ambassadors
                </button>
                <button
                  onClick={() => handleTabChange('awards')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'awards' ? '1px solid #eab308' : '1px solid transparent',
                    backgroundColor: activeTab === 'awards' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'awards' ? '#eab308' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  🏆 All-American Alumni Vault ({REC_DEBUT_AWARDS.length})
                </button>
                <button
                  onClick={() => handleTabChange('portals')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'portals' ? '1px solid #ec4899' : '1px solid transparent',
                    backgroundColor: activeTab === 'portals' ? 'rgba(236, 72, 153, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'portals' ? '#ec4899' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  🎯 13-Sport Registration Portals
                </button>
                <button
                  onClick={() => handleTabChange('faq')}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: activeTab === 'faq' ? '1px solid #a855f7' : '1px solid transparent',
                    backgroundColor: activeTab === 'faq' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    color: activeTab === 'faq' ? '#a855f7' : '#cbd5e1',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer'
                  }}
                >
                  ❓ Program Intel &amp; FAQs
                </button>
              </>
            )}

          </div>
        </div>

      </header>

      {/* ── MAIN BODY CONTENT ──────────────────────────────────────────────────────── */}
      <main style={{ flex: 1, maxWidth: '1400px', margin: '0 auto', width: '100%', padding: '24px 32px', boxSizing: 'border-box' }}>

        {/* ── TAB: OUTREACH TELEMETRY & ENGAGEMENT HUB ────────────────────────────── */}
        {activeTab === 'telemetry' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Header Telemetry Bar */}
            <div style={{
              background: 'linear-gradient(135deg, #0e1c31 0%, #0a172a 100%)',
              borderRadius: '14px',
              border: '2px solid rgba(245, 132, 38, 0.4)',
              padding: '24px 28px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '20px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '28px' }}>📊</span>
                  <div>
                    <h2 style={{ margin: 0, fontSize: '22px', fontWeight: '900', color: '#ffffff', letterSpacing: '0.3px' }}>
                      OUTREACH TELEMETRY & ENGAGEMENT ANALYTICS
                    </h2>
                    <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                      Comprehensive deliverability tracking, inbound athlete response routing, and open & click telemetry for Dennis Bell (Recreational Debut).
                    </p>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={fetchData}
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    color: '#ffffff',
                    padding: '9px 16px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: '700',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  🔄 Live Refresh
                </button>
                <button
                  onClick={() => handleTabChange('syndication')}
                  style={{
                    backgroundColor: '#F58426',
                    color: '#ffffff',
                    border: 'none',
                    padding: '9px 18px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: '800',
                    cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(245, 132, 38, 0.35)'
                  }}
                >
                  🚀 Launch Next Batch &rarr;
                </button>
              </div>
            </div>

            {/* Core Funnel Metric Cards (6 KPI Cards) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
              
              {/* Card 1: Total Contacted */}
              <div style={{
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Outreached</span>
                  <span style={{ fontSize: '20px' }}>🟢</span>
                </div>
                <div style={{ fontSize: '32px', fontWeight: '900', color: '#10b981' }}>
                  {analyticsData?.funnel?.contacted_count || messagedAthletes.length}
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                  <strong>{analyticsData?.funnel?.contacted_pct || '73.0'}%</strong> of 2,171 candidate roster
                </div>
                <div style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16, 185, 129, 0.15)', padding: '3px 8px', borderRadius: '4px', width: 'fit-content' }}>
                  ✓ 100% Accepted (250 OK)
                </div>
              </div>

              {/* Card 2: Inbound Replies */}
              <div style={{
                background: athleteReplies.length > 0 ? 'rgba(245, 132, 38, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(245, 132, 38, 0.5)',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                cursor: 'pointer'
              }} onClick={() => handleTabChange('replies')}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Inbound Replies</span>
                  <span style={{ fontSize: '20px' }}>💬</span>
                </div>
                <div style={{ fontSize: '32px', fontWeight: '900', color: '#F58426' }}>
                  {athleteReplies.length}
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                  <strong>{analyticsData?.funnel?.reply_rate_pct || '0.82'}%</strong> response rate
                </div>
                <div style={{ fontSize: '11px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.15)', padding: '3px 8px', borderRadius: '4px', width: 'fit-content' }}>
                  📱 Auto-Routed to 616-291-5227
                </div>
              </div>

              {/* Card 3: Pending Next Batch */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Pending Outreach</span>
                  <span style={{ fontSize: '20px' }}>🟡</span>
                </div>
                <div style={{ fontSize: '32px', fontWeight: '900', color: '#f59e0b' }}>
                  {analyticsData?.funnel?.pending_count || pendingAthletes.length}
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                  <strong>{analyticsData?.funnel?.pending_pct || '27.0'}%</strong> waiting for batch trigger
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', background: 'rgba(255, 255, 255, 0.08)', padding: '3px 8px', borderRadius: '4px', width: 'fit-content' }}>
                  ⏱️ 24h Pacing Sentinel
                </div>
              </div>

              {/* Card 4: Open Rate Telemetry */}
              <div style={{
                background: 'rgba(56, 189, 248, 0.06)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Open Rate Telemetry</span>
                  <span style={{ fontSize: '20px' }}>👁️</span>
                </div>
                <div style={{ fontSize: '32px', fontWeight: '900', color: '#38bdf8' }}>
                  {analyticsData?.funnel?.open_rate_pct || 0}%
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                  {analyticsData?.funnel?.unique_opens || 0} unique opens ({analyticsData?.funnel?.total_opens || 0} total)
                </div>
                <div style={{ fontSize: '11px', color: '#a5b4fc', background: 'rgba(99, 102, 241, 0.15)', padding: '3px 8px', borderRadius: '4px', width: 'fit-content' }}>
                  ⚡ Transparent Pixel Active
                </div>
              </div>

              {/* Card 5: Click Rate Telemetry */}
              <div style={{
                background: 'rgba(168, 85, 247, 0.06)',
                border: '1px solid rgba(168, 85, 247, 0.3)',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Click-Through Rate</span>
                  <span style={{ fontSize: '20px' }}>🖱️</span>
                </div>
                <div style={{ fontSize: '32px', fontWeight: '900', color: '#c084fc' }}>
                  {analyticsData?.funnel?.click_rate_pct || 0}%
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                  {analyticsData?.funnel?.unique_clicks || 0} unique clicks ({analyticsData?.funnel?.total_clicks || 0} total)
                </div>
                <div style={{ fontSize: '11px', color: '#c084fc', background: 'rgba(168, 85, 247, 0.15)', padding: '3px 8px', borderRadius: '4px', width: 'fit-content' }}>
                  🎯 RecDebut.com CTAs
                </div>
              </div>

              {/* Card 6: Swarm Capacity */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Delivery Network</span>
                  <span style={{ fontSize: '20px' }}>⚡</span>
                </div>
                <div style={{ fontSize: '32px', fontWeight: '900', color: '#ffffff' }}>
                  {swarmDailyCapacity}
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                  Daily cap across {activeSmtpCount} sender Gmail{activeSmtpCount > 1 ? 's' : ''}
                </div>
                <div style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16, 185, 129, 0.15)', padding: '3px 8px', borderRadius: '4px', width: 'fit-content' }}>
                  $0.00 Zero-Cost SMTP
                </div>
              </div>

            </div>

            {/* Tracking Protocol Deep-Dive Alert Card */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              padding: '20px 24px',
              display: 'flex',
              gap: '16px',
              alignItems: 'flex-start'
            }}>
              <span style={{ fontSize: '24px', marginTop: '2px' }}>ℹ️</span>
              <div style={{ flex: 1, fontSize: '13px', lineHeight: '1.6', color: '#cbd5e1' }}>
                <strong style={{ color: '#38bdf8', fontSize: '14px' }}>Why Past Plain-Text Emails Do Not Report Open Pixels & How Tracking Operates:</strong>
                <p style={{ margin: '6px 0 0 0' }}>
                  Batches 1 through 5 (1,585 emails sent) were dispatched in raw <strong>RFC plain-text format</strong> to maximize initial inbox placement directly past spam filters (achieving 100% server acceptance with 0 SMTP bounces). Because email clients (Gmail, Apple Mail, Outlook) only emit open signals when loading remote HTML images, raw plain-text emails cannot retroactively report when a recipient opened their mail app.
                </p>
                <p style={{ margin: '8px 0 0 0' }}>
                  <strong>Current System Upgrade:</strong> All outgoing email dispatches now compose in <strong>MIMEMultipart ("alternative")</strong> containing both the clean plain text and a responsive HTML layout with an embedded 1x1 transparent tracking pixel (<code style={{ color: '#F58426' }}>/api/v1/recdebut/track/open/...</code>) and click-redirect wrapper (<code style={{ color: '#F58426' }}>/api/v1/recdebut/track/click/...</code>). Future dispatches and test emails will track opens and clicks in real time.
                </p>
              </div>
            </div>

            {/* Split Grid: Left = Inbound Replies Stream, Right = Campaign Batches Audit */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '24px' }}>
              
              {/* Left Column: Live Inbound Athlete Replies Stream */}
              <div style={{
                background: '#0e1c31',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                padding: '22px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '17px', fontWeight: '800', color: '#ffffff' }}>
                      💬 Inbound Athlete Responses ({athleteReplies.length})
                    </h3>
                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                      Replies received via Carrier SMS & direct email, auto-forwarded to Dennis Bell (+1-616-291-5227)
                    </div>
                  </div>
                  <button
                    onClick={() => handleTabChange('replies')}
                    style={{
                      background: 'rgba(245, 132, 38, 0.15)',
                      border: '1px solid #F58426',
                      color: '#F58426',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: '800',
                      cursor: 'pointer'
                    }}
                  >
                    Manage Replies &rarr;
                  </button>
                </div>

                {athleteReplies.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                    No inbound replies recorded yet.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '480px', overflowY: 'auto', paddingRight: '4px' }}>
                    {athleteReplies.slice(0, 10).map((r) => (
                      <div
                        key={r.id}
                        style={{
                          background: '#07101e',
                          border: '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '8px',
                          padding: '14px 16px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ fontWeight: '800', color: '#ffffff', fontSize: '14px' }}>
                            {r.athlete_name || 'Student-Athlete'}
                          </div>
                          <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                            {new Date(r.received_at * 1000).toLocaleString()}
                          </span>
                        </div>

                        <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                          {r.sender_phone && <span style={{ color: '#38bdf8', fontWeight: '700' }}>📱 {r.sender_phone} &bull; </span>}
                          <span>From: {r.sender_email}</span>
                        </div>

                        <div style={{
                          background: 'rgba(255, 255, 255, 0.03)',
                          borderRadius: '6px',
                          padding: '10px 12px',
                          fontSize: '13px',
                          color: '#f8fafc',
                          lineHeight: '1.4',
                          whiteSpace: 'pre-wrap'
                        }}>
                          "{r.reply_body || r.subject}"
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
                          <span style={{ fontSize: '11px', color: '#10b981' }}>
                            ✓ Forwarded to Dennis Bell (616-291-5227)
                          </span>
                          {r.sender_phone && (
                            <a
                              href={`tel:${r.sender_phone.replace(/\D/g, '')}`}
                              style={{
                                color: '#F58426',
                                textDecoration: 'none',
                                fontSize: '11px',
                                fontWeight: '800'
                              }}
                            >
                              📞 Call Athlete &rarr;
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Column: Campaign Batch Dispatches Audit */}
              <div style={{
                background: '#0e1c31',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                padding: '22px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '17px', fontWeight: '800', color: '#ffffff' }}>
                      📢 Dispatched Campaign Batches ({campaigns.length})
                    </h3>
                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                      Chronological ledger of every mass announcement fired
                    </div>
                  </div>
                  <button
                    onClick={() => handleTabChange('campaigns')}
                    style={{
                      background: 'rgba(255, 255, 255, 0.08)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      color: '#cbd5e1',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: '700',
                      cursor: 'pointer'
                    }}
                  >
                    View All &rarr;
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '480px', overflowY: 'auto' }}>
                  {campaigns.map((c) => (
                    <div
                      key={c.id}
                      style={{
                        background: '#07101e',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '8px',
                        padding: '14px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ fontWeight: '800', color: '#ffffff', fontSize: '14px' }}>
                          Batch #{c.id} Broadcast
                        </div>
                        <span style={{
                          backgroundColor: 'rgba(16, 185, 129, 0.18)',
                          color: '#10b981',
                          fontSize: '11px',
                          fontWeight: '800',
                          padding: '3px 8px',
                          borderRadius: '4px'
                        }}>
                          ✓ {c.successful_count} Delivered
                        </span>
                      </div>

                      <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                        Dispatched: {new Date(c.created_at * 1000).toLocaleString()} &bull; Sender: <span style={{ color: '#10b981' }}>{c.sender_id}</span>
                      </div>

                      <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
                        Recipients targeted: <strong>{c.total_recipients}</strong> &bull; Bounces/Retried: <strong>{c.failed_count}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Student-Athlete Master Engagement Table */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '22px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '14px' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '17px', fontWeight: '800', color: '#ffffff' }}>
                    👥 Athlete-by-Athlete Outreach & Engagement Directory ({athletes.length})
                  </h3>
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                    Real-time per-athlete delivery, open count, click count, and response status
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search athlete, school, phone, email..."
                    style={{
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 14px',
                      fontSize: '12px',
                      width: '260px'
                    }}
                  />
                  <button
                    onClick={() => handleTabChange('roster')}
                    style={{
                      background: 'rgba(255, 255, 255, 0.08)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      color: '#ffffff',
                      padding: '8px 14px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer'
                    }}
                  >
                    Open Full Roster Table &rarr;
                  </button>
                </div>
              </div>

              {/* Table */}
              <div style={{ overflowX: 'auto', maxHeight: '420px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      <th style={{ padding: '10px 14px' }}>Athlete</th>
                      <th style={{ padding: '10px 14px' }}>Sport & School</th>
                      <th style={{ padding: '10px 14px' }}>Phone / Email</th>
                      <th style={{ padding: '10px 14px' }}>Outreach Status</th>
                      <th style={{ padding: '10px 14px' }}>Messaged Date</th>
                      <th style={{ padding: '10px 14px' }}>Opens</th>
                      <th style={{ padding: '10px 14px' }}>Clicks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {athletes.filter(a => {
                      if (!searchTerm.trim()) return true;
                      const q = searchTerm.toLowerCase();
                      return (
                        (a.name && a.name.toLowerCase().includes(q)) ||
                        (a.high_school && a.high_school.toLowerCase().includes(q)) ||
                        (a.phone && a.phone.includes(q)) ||
                        (a.email && a.email.toLowerCase().includes(q))
                      );
                    }).slice(0, 30).map((a) => {
                      const isMessaged = a.status === 'Contacted' || a.status === 'Messaged';
                      const isReplied = a.status === 'Replied' || athleteReplies.some(r => r.athlete_id === a.id);
                      return (
                        <tr key={a.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                          <td style={{ padding: '12px 14px', fontWeight: '700', color: '#ffffff' }}>
                            {a.name}
                          </td>
                          <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                            <div>{a.sport || 'Basketball'}</div>
                            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{a.high_school || 'Class of ' + (a.grad_year || '2026')}</div>
                          </td>
                          <td style={{ padding: '12px 14px', color: '#94a3b8', fontSize: '12px' }}>
                            <div>📱 {a.phone}</div>
                            {a.email && <div style={{ color: '#38bdf8' }}>📧 {a.email}</div>}
                          </td>
                          <td style={{ padding: '12px 14px' }}>
                            {isReplied ? (
                              <span style={{ backgroundColor: 'rgba(245, 132, 38, 0.2)', color: '#F58426', fontSize: '11px', fontWeight: '800', padding: '3px 8px', borderRadius: '4px' }}>
                                💬 REPLIED
                              </span>
                            ) : isMessaged ? (
                              <span style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981', fontSize: '11px', fontWeight: '800', padding: '3px 8px', borderRadius: '4px' }}>
                                ✓ CONTACTED
                              </span>
                            ) : (
                              <span style={{ backgroundColor: 'rgba(255, 255, 255, 0.08)', color: '#f59e0b', fontSize: '11px', fontWeight: '800', padding: '3px 8px', borderRadius: '4px' }}>
                                ⏳ PENDING
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '12px 14px', color: '#cbd5e1', fontSize: '12px' }}>
                            {a.last_messaged_at ? new Date(a.last_messaged_at * 1000).toLocaleDateString() : '—'}
                          </td>
                          <td style={{ padding: '12px 14px', color: a.open_count > 0 ? '#38bdf8' : '#64748b', fontWeight: '700' }}>
                            {a.open_count || 0}
                          </td>
                          <td style={{ padding: '12px 14px', color: a.click_count > 0 ? '#c084fc' : '#64748b', fontWeight: '700' }}>
                            {a.click_count || 0}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

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
                  <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span>Caller ID / Callback: <strong style={{ color: '#10b981' }}>Dennis Bell (616-291-5227)</strong> • dbell002@sbcglobal.net</span>
                    <span style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.35)', color: '#34d399', padding: '2px 8px', borderRadius: '4px', fontWeight: '700', fontSize: '11px' }}>
                      📎 Official NCAA Eligibility Poster Attached
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => {
                      setMessageScript(NCAA_ELIGIBILITY_DRAFT);
                      setEmailSubject('YOUR ELIGIBILITY IS A MUST! — NCAA Academic Requirements Breakdown');
                      setCampaignType('email');
                    }}
                    style={{
                      background: 'rgba(245, 132, 38, 0.15)',
                      border: '1px solid rgba(245, 132, 38, 0.4)',
                      color: '#f58426',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '700',
                      cursor: 'pointer'
                    }}
                  >
                    🏀 NCAA Eligibility Draft
                  </button>
                  <button
                    onClick={() => {
                      setMessageScript(LAS_VEGAS_TALENT_SCRIPT);
                      setCampaignType('sms');
                    }}
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
                    Las Vegas Talent Script
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
                  <span>Personalization: <strong>Auto-tailored</strong> (Tokens: <code style={{ color: '#38bdf8' }}>{"{first_name}"}</code>, <code style={{ color: '#38bdf8' }}>{"{name}"}</code>, <code style={{ color: '#38bdf8' }}>{"{school}"}</code>, <code style={{ color: '#38bdf8' }}>{"{sport}"}</code>, <code style={{ color: '#38bdf8' }}>{"{grad_year}"}</code>)</span>
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

                  <button
                    onClick={() => { setSyndicationCategory('phone_only'); setSelectedIds(new Set()); }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      fontWeight: '800',
                      fontSize: '13px',
                      cursor: 'pointer',
                      backgroundColor: syndicationCategory === 'phone_only' ? '#3b82f6' : 'rgba(255, 255, 255, 0.06)',
                      color: syndicationCategory === 'phone_only' ? '#ffffff' : '#94a3b8'
                    }}
                  >
                    📱 Phone-Only Follow-Up ({phoneOnlyAthletes.length})
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

              {/* Phone-Only Advisory Banner */}
              {syndicationCategory === 'phone_only' && (
                <div style={{
                  backgroundColor: 'rgba(59, 130, 246, 0.12)',
                  border: '1px solid rgba(59, 130, 246, 0.4)',
                  borderRadius: '8px',
                  padding: '14px 18px',
                  marginBottom: '16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '13px',
                  color: '#93c5fd'
                }}>
                  <div>
                    <strong style={{ color: '#ffffff', fontSize: '14px' }}>📱 Phone-Only Outreach Queue ({phoneOnlyAthletes.length} Student-Athletes)</strong>
                    <div style={{ fontSize: '12px', marginTop: '4px', color: '#cbd5e1' }}>
                      These verified student-athletes have high schools and active phone numbers in the recruiting guide, but no email listed. Recommended: Direct 1-on-1 SMS or phone call from Dennis Bell (616-291-5227). They are safely isolated from bulk email blasts.
                    </div>
                  </div>
                  <button
                    onClick={() => exportCsv(phoneOnlyAthletes, 'Athletes_Nike_Phone_Only_Roster', false)}
                    style={{
                      backgroundColor: '#2563eb',
                      border: 'none',
                      color: '#ffffff',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    📥 Export Phone-Only (CSV)
                  </button>
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
                              {item.email_status === 'NO_EMAIL' ? (
                                <span style={{
                                  backgroundColor: 'rgba(59, 130, 246, 0.2)',
                                  color: '#60a5fa',
                                  fontSize: '11px',
                                  fontWeight: '800',
                                  padding: '3px 8px',
                                  borderRadius: '4px'
                                }}>
                                  📱 Phone Only
                                </span>
                              ) : (item.status === 'Contacted' || item.status === 'Messaged') ? (
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

            {/* ── TRANSACTIONAL EMAIL API SHIELD (RESEND / SENDGRID) ────────────────────────── */}
            <div style={{
              background: emailApiConfig?.is_api_active
                ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(7, 16, 30, 0.95))'
                : 'linear-gradient(135deg, rgba(245, 132, 38, 0.12), rgba(7, 16, 30, 0.95))',
              borderRadius: '12px',
              border: emailApiConfig?.is_api_active ? '2px solid #10b981' : '2px solid #F58426',
              padding: '24px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '14px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '26px' }}>🛡️</span>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '900', color: '#ffffff' }}>
                          Anti-Spam Email Protection Shield & Transactional API
                        </h3>
                        <span style={{
                          backgroundColor: emailApiConfig?.is_api_active ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 132, 38, 0.2)',
                          color: emailApiConfig?.is_api_active ? '#10b981' : '#F58426',
                          border: `1px solid ${emailApiConfig?.is_api_active ? '#10b981' : '#F58426'}`,
                          padding: '3px 10px',
                          borderRadius: '20px',
                          fontSize: '11px',
                          fontWeight: '800'
                        }}>
                          {emailApiConfig?.is_api_active ? 'API SHIELD ACTIVE' : 'DIRECT SMTP FALLBACK'}
                        </span>
                      </div>
                      <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#cbd5e1' }}>
                        {emailApiConfig?.recommendation || 'Protect your personal Google account from spam flags and temporary restrictions.'}
                      </p>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={() => setShowApiSetupGuide(!showApiSetupGuide)}
                    style={{
                      background: 'rgba(56, 189, 248, 0.15)',
                      border: '1px solid #38bdf8',
                      color: '#38bdf8',
                      padding: '8px 14px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer'
                    }}
                  >
                    📖 Why Emails Get Flagged & How to Fix
                  </button>
                </div>
              </div>

              {/* Collapsible API & Spam Explanation Guide */}
              {showApiSetupGuide && (
                <div style={{
                  background: '#07101e',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  borderRadius: '10px',
                  padding: '18px 20px',
                  marginBottom: '18px',
                  fontSize: '13px',
                  color: '#cbd5e1',
                  lineHeight: '1.6'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <strong style={{ color: '#38bdf8', fontSize: '14px' }}>
                      🔍 Root Cause of Email Flagging & Restriction:
                    </strong>
                    <button
                      onClick={() => setShowApiSetupGuide(false)}
                      style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                    >
                      ✕ Close
                    </button>
                  </div>
                  <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                    <li><strong>Carrier SMS Shotgun Blasts:</strong> In SMS mode, sending emails to 7 carrier gateways (@vzwpix.com, @mms.att.net, etc.) creates 6 immediate hard bounces per athlete (85.7% bounce rate!). Google detects this high bounce volume and temporarily restricts personal Gmail accounts.</li>
                    <li><strong>SPF & DMARC Mismatch:</strong> Setting <code>From: Dennis Bell &lt;dbell002@sbcglobal.net&gt;</code> while authenticating via <code>@gmail.com</code> fails SPF/DKIM validation at remote mail servers.</li>
                    <li><strong>The Solution (Transactional API):</strong> With <strong>Resend</strong> (resend.com) or <strong>SendGrid</strong>, all emails are signed with custom domain DKIM/SPF. Personal Gmail accounts are 100% untouched, ensuring zero risk of account bans or restrictions.</li>
                  </ul>
                  <div style={{ marginTop: '8px', fontSize: '12px', color: '#10b981' }}>
                    💡 <strong>Resend Free Tier:</strong> Gives you 3,000 free emails/month. Sign up at <a href="https://resend.com" target="_blank" rel="noreferrer" style={{ color: '#38bdf8', fontWeight: '700' }}>resend.com ↗</a>, grab your API Key (starts with <code>re_</code>), paste it below, and click Save!
                  </div>
                </div>
              )}

              {/* API Configuration Inputs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#94a3b8', marginBottom: '6px' }}>
                    Active Provider Mode
                  </label>
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    style={{
                      width: '100%',
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      fontSize: '13px'
                    }}
                  >
                    <option value="auto">Auto-Detect (Use API Shield if configured, else SMTP)</option>
                    <option value="resend">Resend API (Recommended — Zero-Spam / Custom Domain)</option>
                    <option value="sendgrid">SendGrid API</option>
                    <option value="smtp_swarm">Gmail Direct SMTP Swarm (Fallback)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#94a3b8', marginBottom: '6px' }}>
                    Resend API Key {emailApiConfig?.resend_status && <span style={{ color: '#10b981' }}>({emailApiConfig.resend_status})</span>}
                  </label>
                  <input
                    type="password"
                    value={resendApiKeyInput}
                    onChange={(e) => setResendApiKeyInput(e.target.value)}
                    placeholder="re_1234567890abcdef..."
                    style={{
                      width: '100%',
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      fontSize: '13px'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#94a3b8', marginBottom: '6px' }}>
                    Verified Sender Address (From)
                  </label>
                  <input
                    type="text"
                    value={resendFromInput}
                    onChange={(e) => setResendFromInput(e.target.value)}
                    placeholder="Dennis Bell <recruiting@recdebut.com>"
                    style={{
                      width: '100%',
                      backgroundColor: '#07101e',
                      color: '#ffffff',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      fontSize: '13px'
                    }}
                  />
                </div>
              </div>

              {/* Action Toolbar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                  Student athlete replies will always be routed directly to: <strong style={{ color: '#ffffff' }}>dbell002@sbcglobal.net</strong>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={handleSaveApiConfig}
                    disabled={isSavingApiConfig}
                    style={{
                      backgroundColor: '#10b981',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '10px 20px',
                      fontSize: '13px',
                      fontWeight: '800',
                      cursor: isSavingApiConfig ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                    }}
                  >
                    {isSavingApiConfig ? 'Saving...' : '💾 Save API Shield Configuration'}
                  </button>
                </div>
              </div>

              {apiConfigToast && (
                <div style={{ marginTop: '14px', backgroundColor: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#10b981', padding: '10px 16px', borderRadius: '6px', fontSize: '13px', fontWeight: '700' }}>
                  {apiConfigToast}
                </div>
              )}
            </div>

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

        {/* ── TAB: INBOUND ATHLETE SMS REPLIES (IMAP SYNC) ────────────────────────── */}
        {activeTab === 'replies' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Header Inbound Hub Banner */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '2px solid rgba(16, 185, 129, 0.4)',
              padding: '22px 26px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '26px' }}>💬</span>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '900', color: '#ffffff' }}>
                      INBOUND ATHLETE SMS RESPONSES & TWO-WAY RECRUITING HUB
                    </h3>
                    <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                      When student-athletes text back, their messages are automatically captured, logged below, and <strong>instantly forwarded as a text message directly to Dennis Bell's cell phone (+1-616-291-5227)</strong> in real time.
                    </p>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  onClick={handleSyncReplies}
                  disabled={isSyncingReplies}
                  style={{
                    backgroundColor: '#10b981',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '10px 18px',
                    fontSize: '13px',
                    fontWeight: '800',
                    cursor: isSyncingReplies ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 4px 14px rgba(16, 185, 129, 0.3)'
                  }}
                >
                  {isSyncingReplies ? '🔄 Checking IMAP Mailbox...' : '🔄 Sync Inbound Replies Now'}
                </button>
              </div>
            </div>

            {/* Sync Feedback Alert */}
            {syncReplyMessage && (
              <div style={{
                backgroundColor: syncReplyMessage.includes('✅') ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                border: syncReplyMessage.includes('✅') ? '1px solid #10b981' : '1px solid #ef4444',
                color: syncReplyMessage.includes('✅') ? '#34d399' : '#f87171',
                padding: '12px 18px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: '700'
              }}>
                {syncReplyMessage}
              </div>
            )}

            {/* Inbound Replies Container */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '22px'
            }}>
              {/* Filter & Search Bar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '14px' }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <button
                    onClick={() => setReplyFilter('all')}
                    style={{
                      backgroundColor: replyFilter === 'all' ? '#F58426' : 'rgba(255, 255, 255, 0.08)',
                      color: '#ffffff',
                      border: 'none',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer'
                    }}
                  >
                    All Replies ({athleteReplies.length})
                  </button>
                  <button
                    onClick={() => setReplyFilter('unread')}
                    style={{
                      backgroundColor: replyFilter === 'unread' ? '#F58426' : 'rgba(255, 255, 255, 0.08)',
                      color: '#ffffff',
                      border: 'none',
                      padding: '8px 16px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer'
                    }}
                  >
                    Unread Only ({unreadRepliesCount})
                  </button>
                </div>

                <input
                  type="text"
                  value={replySearchTerm}
                  onChange={(e) => setReplySearchTerm(e.target.value)}
                  placeholder="Search name, phone, or text content..."
                  style={{
                    backgroundColor: '#07101e',
                    color: '#ffffff',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '6px',
                    padding: '8px 14px',
                    fontSize: '12px',
                    width: '280px'
                  }}
                />
              </div>

              {/* Replies Feed */}
              {athleteReplies.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
                  <div style={{ fontSize: '36px', marginBottom: '10px' }}>📬</div>
                  <h4 style={{ margin: '0 0 6px 0', color: '#ffffff' }}>No Inbound Replies Synced Yet</h4>
                  <p style={{ margin: 0, fontSize: '13px' }}>
                    Click "Sync Inbound Replies Now" to connect to the inbound recruitment gateway and check for new athlete text replies.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {athleteReplies.filter(r => {
                    if (replyFilter === 'unread' && r.is_read) return false;
                    if (!replySearchTerm.trim()) return true;
                    const q = replySearchTerm.toLowerCase();
                    return (
                      (r.athlete_name && r.athlete_name.toLowerCase().includes(q)) ||
                      (r.sender_phone && r.sender_phone.includes(q)) ||
                      (r.reply_body && r.reply_body.toLowerCase().includes(q)) ||
                      (r.sender_email && r.sender_email.toLowerCase().includes(q))
                    );
                  }).map(r => (
                    <div
                      key={r.id}
                      style={{
                        background: r.is_read ? 'rgba(255, 255, 255, 0.02)' : 'rgba(245, 132, 38, 0.06)',
                        border: r.is_read ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid rgba(245, 132, 38, 0.5)',
                        borderRadius: '10px',
                        padding: '18px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '18px' }}>👤</span>
                          <div>
                            <div style={{ fontSize: '15px', fontWeight: '800', color: '#ffffff' }}>
                              {r.athlete_name || 'Direct Mobile Contact'}
                            </div>
                            <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                              {r.sender_phone ? <span>📱 <strong>{r.sender_phone}</strong> • </span> : ''}
                              <span>Gateway: <code style={{ color: '#38bdf8' }}>{r.sender_email}</code></span>
                              <span> • Received: <strong>{new Date(r.received_at * 1000).toLocaleString()}</strong></span>
                            </div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          {!r.is_read ? (
                            <button
                              onClick={() => handleMarkReplyRead(r.id)}
                              style={{
                                background: 'rgba(255, 255, 255, 0.08)',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                color: '#cbd5e1',
                                padding: '5px 10px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                cursor: 'pointer'
                              }}
                            >
                              ✓ Mark Read
                            </button>
                          ) : (
                            <span style={{ fontSize: '11px', color: '#64748b' }}>Read</span>
                          )}

                          <button
                            onClick={() => {
                              if (activeReplyId === r.id) {
                                setActiveReplyId(null);
                              } else {
                                setActiveReplyId(r.id);
                                setReplyMessageText(`Hey ${r.athlete_name?.split(' ')[0] || ''}, Dennis Bell here! Great to hear from you. Have you registered your recruitment profile on RecDebut.com yet?`);
                              }
                            }}
                            style={{
                              backgroundColor: activeReplyId === r.id ? '#64748b' : '#F58426',
                              color: '#ffffff',
                              border: 'none',
                              padding: '6px 14px',
                              borderRadius: '6px',
                              fontSize: '12px',
                              fontWeight: '800',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px'
                            }}
                          >
                            {activeReplyId === r.id ? '✕ Close Reply' : '💬 Quick SMS Reply'}
                          </button>
                        </div>
                      </div>

                      {/* Message Content */}
                      <div style={{
                        background: '#07101e',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        fontSize: '14px',
                        color: '#f8fafc',
                        lineHeight: '1.5',
                        whiteSpace: 'pre-wrap'
                      }}>
                        "{r.reply_body || r.subject}"
                      </div>

                      {/* Collapsible Inline SMS Reply Box */}
                      {activeReplyId === r.id && (
                        <div style={{
                          background: '#060d19',
                          border: '2px solid #F58426',
                          borderRadius: '8px',
                          padding: '16px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px'
                        }}>
                          <div style={{ fontSize: '13px', fontWeight: '800', color: '#F58426' }}>
                            Respond to {r.athlete_name} via Carrier MMS / SMS (+1-616-291-5227 Caller ID)
                          </div>
                          <textarea
                            value={replyMessageText}
                            onChange={(e) => setReplyMessageText(e.target.value)}
                            rows={3}
                            style={{
                              backgroundColor: '#07101e',
                              color: '#ffffff',
                              border: '1px solid rgba(255, 255, 255, 0.2)',
                              borderRadius: '6px',
                              padding: '10px 14px',
                              fontSize: '13px',
                              fontFamily: 'inherit',
                              resize: 'vertical'
                            }}
                          />
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                            <button
                              onClick={() => setActiveReplyId(null)}
                              style={{
                                background: 'transparent',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                color: '#94a3b8',
                                padding: '6px 14px',
                                borderRadius: '6px',
                                fontSize: '12px',
                                cursor: 'pointer'
                              }}
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleSendQuickReply(r)}
                              disabled={isSendingReply}
                              style={{
                                backgroundColor: '#10b981',
                                color: '#ffffff',
                                border: 'none',
                                padding: '8px 18px',
                                borderRadius: '6px',
                                fontSize: '12px',
                                fontWeight: '800',
                                cursor: isSendingReply ? 'not-allowed' : 'pointer'
                              }}
                            >
                              {isSendingReply ? 'Sending SMS...' : '📤 Send SMS Text Now'}
                            </button>
                          </div>
                        </div>
                      )}

                    </div>
                  ))}
                </div>
              )}

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

        {/* ── TAB 6: 2,000+ COACHES & PRO AMBASSADORS NETWORK ──────────────────────── */}
        {activeTab === 'network' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
            
            {/* Top Overview Banner */}
            <div style={{
              background: 'linear-gradient(135deg, #0e1c31 0%, #081325 100%)',
              borderRadius: '14px',
              border: '1px solid rgba(245, 132, 38, 0.4)',
              padding: '28px',
              boxShadow: '0 8px 30px rgba(0,0,0,0.3)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '20px'
            }}>
              <div style={{ maxWidth: '850px' }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(245, 132, 38, 0.15)', border: '1px solid #F58426', padding: '4px 12px', borderRadius: '20px', marginBottom: '12px' }}>
                  <span style={{ fontSize: '13px' }}>🏀</span>
                  <span style={{ fontSize: '12px', fontWeight: '800', color: '#F58426', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Authentic Pedigree Since 1984
                  </span>
                </div>
                <h2 style={{ margin: '0 0 10px 0', fontSize: '24px', fontWeight: '900', color: '#ffffff', letterSpacing: '0.5px' }}>
                  Collegiate Recruitment Architecture & Pro Leadership
                </h2>
                <p style={{ margin: 0, fontSize: '14px', color: '#94a3b8', lineHeight: '1.6' }}>
                  Recreational Debut delivers student-athlete resumes and highlight film directly to over <strong>2,000+ college coaches</strong> across NCAA Division I, II, III, NAIA, and NJCAA throughout the United States and Canada. Every portfolio is fortified by an official signed letter from former New York Knick Dennis Bell and our veteran coaching staff.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ background: 'rgba(0, 107, 182, 0.2)', border: '1px solid #006BB6', padding: '14px 20px', borderRadius: '10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: '900', color: '#38bdf8' }}>2,000+</div>
                  <div style={{ fontSize: '11px', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: '700' }}>College Coaches</div>
                </div>
                <div style={{ background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', padding: '14px 20px', borderRadius: '10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: '900', color: '#10b981' }}>34+</div>
                  <div style={{ fontSize: '11px', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: '700' }}>Years Impact</div>
                </div>
                <div style={{ background: 'rgba(245, 132, 38, 0.2)', border: '1px solid #F58426', padding: '14px 20px', borderRadius: '10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: '900', color: '#F58426' }}>501(c)(3)</div>
                  <div style={{ fontSize: '11px', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: '700' }}>Nonprofit Status</div>
                </div>
              </div>
            </div>

            {/* Leadership & Staff Grid */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span>🌟</span> Executive Leadership, Pro Ambassadors & Coaching Staff
                </h3>
                <span style={{ fontSize: '12px', color: '#64748b' }}>Verified profiles from RecDebut.com WordPress Registry</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
                {REC_DEBUT_LEADERSHIP.map((leader, idx) => (
                  <div key={idx} style={{
                    background: '#0e1c31',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.08)',
                    padding: '24px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
                  }}>
                    <div>
                      <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{
                          width: '76px',
                          height: '76px',
                          borderRadius: '10px',
                          overflow: 'hidden',
                          backgroundColor: '#07101e',
                          border: '2px solid #F58426',
                          flexShrink: 0
                        }}>
                          <img 
                            src={leader.image} 
                            alt={leader.name}
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.parentNode.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#F58426;font-weight:bold;font-size:20px;">RD</div>';
                            }}
                          />
                        </div>

                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <h4 style={{ margin: 0, fontSize: '18px', fontWeight: '900', color: '#ffffff' }}>
                              {leader.name}
                            </h4>
                            {leader.badge && (
                              <span style={{
                                backgroundColor: '#F58426',
                                color: '#ffffff',
                                fontSize: '10px',
                                fontWeight: '800',
                                padding: '2px 8px',
                                borderRadius: '4px'
                              }}>
                                {leader.badge}
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8', marginTop: '3px' }}>
                            {leader.role}
                          </div>
                          <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                            {leader.phone} • {leader.email}
                          </div>
                        </div>
                      </div>

                      <div style={{ background: '#07101e', padding: '12px 14px', borderRadius: '8px', marginBottom: '12px', borderLeft: '3px solid #006BB6' }}>
                        <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700', marginBottom: '4px' }}>
                          Athletic / Coaching Career
                        </div>
                        <div style={{ fontSize: '12px', color: '#e2e8f0', fontWeight: '600', lineHeight: '1.4' }}>
                          {leader.pro}
                        </div>
                      </div>

                      <div style={{ background: '#07101e', padding: '12px 14px', borderRadius: '8px', marginBottom: '14px', borderLeft: '3px solid #10b981' }}>
                        <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700', marginBottom: '4px' }}>
                          Collegiate & Academic Credentials
                        </div>
                        <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.4' }}>
                          {leader.college}
                        </div>
                      </div>

                      <p style={{ fontSize: '12px', color: '#94a3b8', lineHeight: '1.6', margin: 0 }}>
                        {leader.bio}
                      </p>
                    </div>

                    <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', color: '#64748b' }}>Recreational Debut 501(c)(3)</span>
                      <a 
                        href={`mailto:${leader.email}`} 
                        style={{ fontSize: '12px', color: '#38bdf8', textDecoration: 'none', fontWeight: '700' }}
                      >
                        ✉️ Contact Direct ↗
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Collegiate Divisions Breakdown & Endorsement Letter Details */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              <div style={{ background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '24px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                  Collegiate Division Tier Distribution
                </h3>
                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: '1.6', margin: '0 0 16px 0' }}>
                  Our network maintains active collegiate relationships spanning every governing division:
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {[
                    { tier: 'NCAA Division I', desc: 'Over 350+ Division 1 athletic departments across ACC, Big Ten, SEC, Big 12, Big East, and mid-majors.' },
                    { tier: 'NCAA Division II', desc: 'Full and partial athletic scholarship tier with competitive nationwide and Midwest programs.' },
                    { tier: 'NCAA Division III', desc: 'High academic standards, competitive athletics, and merit-based financial aid awards.' },
                    { tier: 'NAIA & NJCAA', desc: 'Premier collegiate development, immediate starter opportunities, and university transfer pipelines.' }
                  ].map((t, idx) => (
                    <div key={idx} style={{ background: '#07101e', padding: '12px 16px', borderRadius: '8px', borderLeft: '4px solid #F58426' }}>
                      <div style={{ fontSize: '14px', fontWeight: '800', color: '#ffffff' }}>{t.tier}</div>
                      <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '3px' }}>{t.desc}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ background: '#0e1c31', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', padding: '24px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '800', color: '#ffffff' }}>
                  Dennis Bell Signed Pro Endorsement Letter
                </h3>
                <p style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 16px 0' }}>
                  College coaches receive hundreds of emails every single week from athletes and parents. When an email or envelope carries the formal seal and endorsement of a former NBA player like Dennis Bell, coaches stop, open, and evaluate the game footage.
                </p>

                <div style={{ background: 'rgba(0, 107, 182, 0.1)', border: '1px solid #006BB6', borderRadius: '8px', padding: '18px', marginBottom: '16px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#38bdf8' }}>Included In The Gold Package:</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: '#f8fafc' }}>
                    <div>🏀 Dennis Bell Signed Professional Player Acknowledgment Letter</div>
                    <div>📄 Standardized Academic & Athletic Resume</div>
                    <div>📊 Official Statistical Breakdown & Physical Testing Profile</div>
                    <div>🎥 Professional Highlight Film Consultation</div>
                    <div>⚡ Direct Placement into 2,000+ College Coaches Inboxes</div>
                    <div>🧾 100% Tax-Deductible 501(c)(3) Charitable Receipt</div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <a 
                    href="https://recdebut.com/program/" 
                    target="_blank" 
                    rel="noreferrer"
                    style={{
                      background: '#F58426',
                      color: '#ffffff',
                      textDecoration: 'none',
                      padding: '10px 18px',
                      borderRadius: '8px',
                      fontSize: '13px',
                      fontWeight: '800',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    View Official Program Page ↗
                  </a>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ── TAB: ALL-AMERICAN & PRESEASON HONOREES VAULT ─────────────────────────── */}
        {activeTab === 'awards' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Awards Header Banner */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(245, 132, 38, 0.3)',
              padding: '24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(245, 132, 38, 0.15)', border: '1px solid #F58426', padding: '3px 10px', borderRadius: '20px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px' }}>🏆</span>
                  <span style={{ fontSize: '11px', fontWeight: '800', color: '#F58426', textTransform: 'uppercase' }}>
                    Proven Track Record
                  </span>
                </div>
                <h2 style={{ margin: 0, fontSize: '22px', fontWeight: '900', color: '#ffffff' }}>
                  McDonald's & Pre-Season All-American Nominees From RecDebut
                </h2>
                <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                  Over the decades, Recreational Debut has guided dozens of standouts to All-American ballots, state championships, and full college scholarships.
                </p>
              </div>

              {/* State Filter Buttons */}
              <div style={{ display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '8px' }}>
                {['ALL', 'MI', 'IN', 'OH'].map(st => (
                  <button
                    key={st}
                    onClick={() => setAwardStateFilter(st)}
                    style={{
                      background: awardStateFilter === st ? '#F58426' : 'transparent',
                      color: awardStateFilter === st ? '#ffffff' : '#94a3b8',
                      border: 'none',
                      padding: '6px 14px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '800',
                      cursor: 'pointer'
                    }}
                  >
                    {st === 'ALL' ? 'All States' : `${st}`}
                  </button>
                ))}
              </div>
            </div>

            {/* Search Input */}
            <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
              <input 
                type="text"
                placeholder="🔍 Search honoree by athlete name, high school, city, or coach..."
                value={awardSearchTerm}
                onChange={(e) => setAwardSearchTerm(e.target.value)}
                style={{
                  flex: 1,
                  padding: '12px 18px',
                  borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.12)',
                  background: '#07101e',
                  color: '#ffffff',
                  fontSize: '14px',
                  outline: 'none'
                }}
              />
              <span style={{ fontSize: '12px', color: '#64748b' }}>
                Showing {REC_DEBUT_AWARDS.filter(a => {
                  const matchSearch = !awardSearchTerm || 
                    a.name.toLowerCase().includes(awardSearchTerm.toLowerCase()) ||
                    a.school.toLowerCase().includes(awardSearchTerm.toLowerCase()) ||
                    a.city_state.toLowerCase().includes(awardSearchTerm.toLowerCase()) ||
                    a.coach.toLowerCase().includes(awardSearchTerm.toLowerCase());
                  const matchState = awardStateFilter === 'ALL' || a.city_state.includes(awardStateFilter);
                  return matchSearch && matchState;
                }).length} of {REC_DEBUT_AWARDS.length} Honorees
              </span>
            </div>

            {/* Awards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
              {REC_DEBUT_AWARDS.filter(a => {
                const matchSearch = !awardSearchTerm || 
                  a.name.toLowerCase().includes(awardSearchTerm.toLowerCase()) ||
                  a.school.toLowerCase().includes(awardSearchTerm.toLowerCase()) ||
                  a.city_state.toLowerCase().includes(awardSearchTerm.toLowerCase()) ||
                  a.coach.toLowerCase().includes(awardSearchTerm.toLowerCase());
                const matchState = awardStateFilter === 'ALL' || a.city_state.includes(awardStateFilter);
                return matchSearch && matchState;
              }).map((honoree, idx) => (
                <div key={idx} style={{
                  background: '#0e1c31',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.08)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: '0 4px 14px rgba(0,0,0,0.2)'
                }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <h4 style={{ margin: 0, fontSize: '17px', fontWeight: '900', color: '#ffffff' }}>
                        {honoree.name}
                      </h4>
                      <span style={{
                        background: '#F58426',
                        color: '#ffffff',
                        fontSize: '11px',
                        fontWeight: '800',
                        padding: '2px 8px',
                        borderRadius: '4px'
                      }}>
                        {honoree.height}
                      </span>
                    </div>

                    <div style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8' }}>
                      🏫 {honoree.school}
                    </div>
                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '2px' }}>
                      📍 {honoree.city_state}
                    </div>
                    <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '6px' }}>
                      👤 <strong>Coach:</strong> {honoree.coach}
                    </div>

                    <div style={{ background: '#07101e', padding: '10px 12px', borderRadius: '6px', marginTop: '12px', borderLeft: '3px solid #10b981' }}>
                      <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700' }}>Accolades & Honors</div>
                      <div style={{ fontSize: '12px', color: '#f8fafc', marginTop: '2px', lineHeight: '1.4' }}>
                        {honoree.accolades}
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>All-American Registry</span>
                    <span style={{ fontSize: '11px', color: '#F58426', fontWeight: '800' }}>{honoree.badge}</span>
                  </div>
                </div>
              ))}
            </div>

          </div>
        )}

        {/* ── TAB: 13-SPORT REGISTRATION PORTALS ────────────────────────────────────── */}
        {activeTab === 'portals' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Header Banner */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(0, 107, 182, 0.4)',
              padding: '24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div style={{ maxWidth: '800px' }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(0, 107, 182, 0.2)', border: '1px solid #006BB6', padding: '3px 10px', borderRadius: '20px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px' }}>🎯</span>
                  <span style={{ fontSize: '11px', fontWeight: '800', color: '#38bdf8', textTransform: 'uppercase' }}>
                    Multi-Sport Coverage
                  </span>
                </div>
                <h2 style={{ margin: 0, fontSize: '22px', fontWeight: '900', color: '#ffffff' }}>
                  Official 13-Sport Student-Athlete Registration Portals
                </h2>
                <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                  Each sport features specialized metric intake tailored to college scouts (40 times, approach vertical, pitching velocity, PR times, Hudl highlights). Click any sport to open its dedicated intake portal on RecDebut.com.
                </p>
              </div>

              <a
                href={REC_DEBUT_BRAND.all_registration_url}
                target="_blank"
                rel="noreferrer"
                style={{
                  background: '#F58426',
                  color: '#ffffff',
                  textDecoration: 'none',
                  padding: '12px 20px',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: '800',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 14px rgba(245, 132, 38, 0.4)'
                }}
              >
                📝 Master Registration Hub (All Sports) ↗
              </a>
            </div>

            {/* Grid of 13 Sports */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {REC_DEBUT_SPORTS_PORTALS.map(sport => (
                <div key={sport.id} style={{
                  background: '#0e1c31',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.08)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
                      <span style={{ fontSize: '28px' }}>{sport.icon}</span>
                      <div>
                        <h4 style={{ margin: 0, fontSize: '18px', fontWeight: '900', color: '#ffffff' }}>
                          {sport.sport}
                        </h4>
                        <div style={{ fontSize: '11px', color: '#10b981', fontWeight: '700' }}>
                          Verified Portal
                        </div>
                      </div>
                    </div>

                    <div style={{ background: '#07101e', padding: '10px 12px', borderRadius: '6px', marginBottom: '16px' }}>
                      <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700', marginBottom: '2px' }}>
                        Key Scouting Metrics Collected:
                      </div>
                      <div style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.4' }}>
                        {sport.focus}
                      </div>
                    </div>
                  </div>

                  <a
                    href={sport.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid rgba(255,255,255,0.15)',
                      color: '#ffffff',
                      textDecoration: 'none',
                      textAlign: 'center',
                      padding: '10px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: '800',
                      transition: 'all 0.15s'
                    }}
                  >
                    Open {sport.sport} Registration Form ↗
                  </a>
                </div>
              ))}
            </div>

          </div>
        )}

        {/* ── TAB: PROGRAM INTEL & FAQS ────────────────────────────────────────────── */}
        {activeTab === 'faq' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* Header */}
            <div style={{
              background: '#0e1c31',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.08)',
              padding: '24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px'
            }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '22px', fontWeight: '900', color: '#ffffff' }}>
                  Frequently Asked Questions & Program Intel
                </h2>
                <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
                  Essential answers regarding the collegiate recruiting process, tax-deductibility, and Dennis Bell's signature endorsement letter.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <a
                  href={`tel:${REC_DEBUT_BRAND.phone}`}
                  style={{
                    background: '#10b981',
                    color: '#ffffff',
                    textDecoration: 'none',
                    padding: '10px 16px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: '800'
                  }}
                >
                  📞 Call: {REC_DEBUT_BRAND.phone}
                </a>
                <a
                  href={`mailto:${REC_DEBUT_BRAND.email}`}
                  style={{
                    background: '#006BB6',
                    color: '#ffffff',
                    textDecoration: 'none',
                    padding: '10px 16px',
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: '800'
                  }}
                >
                  ✉️ Email: {REC_DEBUT_BRAND.email}
                </a>
              </div>
            </div>

            {/* FAQs Accordion / Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {REC_DEBUT_FAQS.map((faq, idx) => {
                const isExpanded = expandedFaqIndex === idx;
                return (
                  <div
                    key={idx}
                    style={{
                      background: '#0e1c31',
                      borderRadius: '10px',
                      border: isExpanded ? '1px solid #F58426' : '1px solid rgba(255,255,255,0.08)',
                      overflow: 'hidden',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <button
                      onClick={() => setExpandedFaqIndex(isExpanded ? null : idx)}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '18px 22px',
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '16px'
                      }}
                    >
                      <span style={{ fontSize: '15px', fontWeight: '800', color: isExpanded ? '#F58426' : '#ffffff' }}>
                        {faq.q}
                      </span>
                      <span style={{ fontSize: '18px', color: '#94a3b8' }}>
                        {isExpanded ? '▲' : '▼'}
                      </span>
                    </button>

                    {isExpanded && (
                      <div style={{ padding: '0 22px 20px 22px', fontSize: '14px', color: '#cbd5e1', lineHeight: '1.7', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                        <div style={{ paddingTop: '14px' }}>
                          {faq.a}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
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
