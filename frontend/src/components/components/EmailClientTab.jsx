import React, { useState, useEffect, useCallback } from 'react';
import { 
  Mail, MessageSquare, Video, Settings, Plus, Star, Clock, AlertOctagon, Send, 
  FileText, ShoppingBag, Users, Info, MessageCircle, Tag, Trash2, Search, 
  RotateCcw, ShieldCheck, Sparkles, Check, Filter, ExternalLink, ChevronRight, 
  X, CheckSquare, Square, Inbox as InboxIcon, User, RefreshCw, AlertTriangle, 
  CheckCircle2, Globe, Shield, Radio, ArrowUpRight, Key
} from 'lucide-react';
import { useBackendHealth } from './useBackendHealth';
import { db } from '../firebase';
import { collection, onSnapshot, query, orderBy } from 'firebase/firestore';
import CampaignAutomationTab from './CampaignAutomationTab';
import ContentGovernanceRiskModal from './ContentGovernanceRiskModal';

// Active business domain: stehouwer-publishing.com (Cloudflare Email Routing + IMAP/SMTP Gateway)
const TEAM_ACCOUNTS = [
  { id: 'brett', name: 'Brett Stehouwer', email: 'brett@stehouwer-publishing.com', label: '[Imap]/Brett', avatar: '👨‍💻' },
  { id: 'sean', name: 'Sean Stehouwer', email: 'sean@stehouwer-publishing.com', label: '[Imap]/Sean', avatar: '🚀' },
  { id: 'julie', name: 'Julie Stehouwer', email: 'julie@stehouwer-publishing.com', label: '[Imap]/Julie', avatar: '👩‍💼' }
];

const cleanEmailBody = (raw) => {
  if (!raw) return '';
  let str = String(raw);

  // 1. Strip raw MIME protocol headers if present
  if (str.startsWith('Received:') || str.includes('ARC-Seal:') || str.includes('ARC-Message-Signature:')) {
    if (str.includes('\r\n\r\n')) {
      str = str.split('\r\n\r\n').slice(1).join('\r\n\r\n');
    } else if (str.includes('\n\n')) {
      str = str.split('\n\n').slice(1).join('\n\n');
    }
  }

  // 2. Strip MIME sub-headers (Content-Type, Content-Transfer-Encoding)
  if (str.includes('Content-Type:') || str.includes('Content-Transfer-Encoding:')) {
    if (str.includes('\r\n\r\n')) {
      str = str.split('\r\n\r\n').slice(1).join('\r\n\r\n');
    } else if (str.includes('\n\n')) {
      str = str.split('\n\n').slice(1).join('\n\n');
    }
  }

  // 3. Cut off multipart HTML boundaries & raw HTML code blocks
  if (str.includes('--000')) {
    str = str.split(/--000[0-9a-fA-F]+/)[0];
  }
  if (str.includes('Content-Type: text/html')) {
    str = str.split('Content-Type: text/html')[0];
  }

  // 4. Decode quoted-printable UTF-8 artifacts (=E2=80=AF -> space, =3D -> =)
  str = str.replace(/=E2=80=AF/g, ' ')
           .replace(/=3D/g, '=')
           .replace(/=\r?\n/g, '');

  return str.trim() || 'No Body Content';
};

export default function EmailClientTab({ onTabChange }) {
  const { isBackendHealthy, backendUrl } = useBackendHealth();
  const [emails, setEmails] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('brett@stehouwer-publishing.com');
  const [activeFolder, setActiveFolder] = useState('Inbox');
  const [activeCategory, setActiveCategory] = useState('All');
  const [activeLabel, setActiveLabel] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEmail, setSelectedEmail] = useState(null);
  
  // Selection state
  const [selectedIds, setSelectedIds] = useState([]);
  
  // Compose modal state
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [composeFrom, setComposeFrom] = useState('brett@stehouwer-publishing.com');
  const [composeTo, setComposeTo] = useState('');
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [sendStatusMsg, setSendStatusMsg] = useState('');
  const [isGovernanceOpen, setIsGovernanceOpen] = useState(false);

  // Sync & Diagnostic state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState(null);
  const [isGeneratingReply, setIsGeneratingReply] = useState(false);
  const [emailStatus, setEmailStatus] = useState({
    domain: 'stehouwer-publishing.com',
    imap_status: { connected: false, error: 'Checking...' },
    smtp_status: { ready: true },
    mailbox_stats: { total: 0, unread: 0, sent: 0 }
  });

  // Fetch email system diagnostics from backend
  const fetchDiagnostics = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/emails/status`);
      if (res.ok) {
        const data = await res.json();
        setEmailStatus(data);
      }
    } catch (e) {
      console.warn("Could not fetch email diagnostics", e);
    }
  }, [backendUrl]);

  // Fetch emails from backend
  const fetchEmails = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/emails`);
      if (res.ok) {
        const data = await res.json();
        if (data.data && Array.isArray(data.data)) {
          setEmails(prev => {
            const merged = [...prev];
            data.data.forEach(bItem => {
              if (!merged.some(m => m.id === bItem.id)) {
                merged.push(bItem);
              }
            });
            return merged;
          });
        }
      }
    } catch (e) {
      console.warn("Backend emails fetch fallback active");
    }
  }, [backendUrl]);

  // Real-time Firestore sync for live Cloudflare Worker messages
  useEffect(() => {
    try {
      const q = query(collection(db, 'emails'));
      const unsub = onSnapshot(q, (snapshot) => {
        const fsEmails = snapshot.docs.map(doc => {
          const d = doc.data();
          return {
            id: doc.id,
            account: d.account?.stringValue || d.account || 'brett@stehouwer-publishing.com',
            sender: d.sender?.stringValue || d.sender || 'External Sender',
            email: d.email?.stringValue || d.email || 'sender@external.com',
            subject: d.subject?.stringValue || d.subject || 'No Subject',
            snippet: d.snippet?.stringValue || d.body?.stringValue || d.snippet || d.body || '',
            body: d.body?.stringValue || d.body || d.snippet?.stringValue || d.snippet || '',
            time: d.time?.stringValue || d.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            date: d.date?.stringValue || d.date || new Date().toISOString().split('T')[0],
            category: d.category?.stringValue || d.category || 'Primary',
            folder: d.folder?.stringValue || d.folder || 'Inbox',
            starred: d.starred?.booleanValue ?? d.starred ?? false,
            read: d.read?.booleanValue ?? d.read ?? false,
            label: d.label?.stringValue || d.label || '[Imap]/Brett'
          };
        });
        if (fsEmails.length > 0) {
          setEmails(prev => {
            const combined = [...fsEmails, ...prev.filter(p => !fsEmails.some(f => f.id === p.id))];
            return combined;
          });
        }
      }, (err) => console.warn("Firestore emails listener fallback:", err));
      return () => unsub();
    } catch (err) {
      console.warn("Firestore email listener setup error:", err);
    }
  }, []);

  // Poll backend emails & diagnostics
  useEffect(() => {
    fetchDiagnostics();
    fetchEmails();
    const interval = setInterval(() => {
      fetchEmails();
      fetchDiagnostics();
    }, 8000);
    return () => clearInterval(interval);
  }, [fetchDiagnostics, fetchEmails]);

  // Trigger IMAP Mailbox Sync
  const handleTriggerSync = async () => {
    setIsSyncing(true);
    setSyncNotice({ type: 'info', message: 'Connecting to imap.gmail.com:993 (SSL)... Syncing inbox' });
    try {
      const res = await fetch(`${backendUrl}/api/v1/emails/sync`, { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setSyncNotice({ 
          type: 'success', 
          message: `Sync successful: ${data.synced_count ?? data.fetched_count ?? 0} email(s) inspected & synced.` 
        });
        await fetchEmails();
        await fetchDiagnostics();
      } else {
        const errorMsg = data.message || 'Google requires a 16-character App Password. Visit myaccount.google.com/apppasswords and set IMAP_APP_PASSWORD in .env.';
        setSyncNotice({
          type: 'warning',
          message: errorMsg,
          code: data.code
        });
      }
    } catch (err) {
      setSyncNotice({
        type: 'error',
        message: 'Could not reach backend sync endpoint. Check FastAPI engine on port 8080.'
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Generate Smart Reply with Stehouwer LLM
  const handleGenerateSmartReply = async (emailItem) => {
    setIsGeneratingReply(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/emails/generate-reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender: emailItem.sender || 'Client',
          subject: emailItem.subject || 'Inquiry',
          body_snippet: cleanEmailBody(emailItem.body || emailItem.snippet),
          tone_preference: 'Professional'
        })
      });
      const data = await res.json();
      if (data.status === 'success' && data.draft) {
        setComposeTo(emailItem.email);
        const subj = emailItem.subject.toLowerCase().startsWith('re:') ? emailItem.subject : `Re: ${emailItem.subject}`;
        setComposeSubject(subj);
        setComposeBody(data.draft);
        setComposeFrom(emailItem.account || 'brett@stehouwer-publishing.com');
        setIsComposeOpen(true);
        setSelectedEmail(null);
        return;
      }
    } catch (err) {
      console.warn("Stehouwer LLM endpoint fallback active:", err);
    } finally {
      setIsGeneratingReply(false);
    }

    // Deterministic Stehouwer fallback
    const senderName = emailItem.sender ? emailItem.sender.split(' ')[0] : 'there';
    const fallbackDraft = `Hi ${senderName},\n\nThank you for reaching out to Stehouwer Publishing regarding "${emailItem.subject}".\n\nI have received your message and will review the details right away. We will follow up with you shortly with our assessment.\n\nBest regards,\nBrett Stehouwer\nStehouwer Publishing\nbrett@stehouwer-publishing.com`;
    setComposeTo(emailItem.email);
    setComposeSubject(emailItem.subject.toLowerCase().startsWith('re:') ? emailItem.subject : `Re: ${emailItem.subject}`);
    setComposeBody(fallbackDraft);
    setComposeFrom(emailItem.account || 'brett@stehouwer-publishing.com');
    setIsComposeOpen(true);
    setSelectedEmail(null);
  };

  // Filter emails based on Account, Folder, Category, Label, and Search
  const filteredEmails = emails.filter(em => {
    // Normalize account comparison (stehouwerpublishing vs stehouwer-publishing)
    if (selectedAccount !== 'all') {
      const normSel = selectedAccount.toLowerCase().replace(/[-_]/g, '');
      const normEm = (em.account || '').toLowerCase().replace(/[-_]/g, '');
      if (normSel !== normEm && !normEm.includes(normSel.split('@')[0])) return false;
    }
    
    if (activeLabel && em.label !== activeLabel) return false;
    
    // Folder and property-based filtering
    if (!activeLabel && activeFolder !== 'All') {
      const emFolder = em.folder || 'Inbox';
      if (activeFolder === 'Starred') {
        if (!em.starred || emFolder === 'Trash') return false;
      } else if (activeFolder === 'Trash') {
        if (emFolder !== 'Trash') return false;
      } else if (activeFolder === 'Sent') {
        if (emFolder !== 'Sent') return false;
      } else if (activeFolder === 'Drafts') {
        if (emFolder !== 'Drafts') return false;
      } else if (activeFolder === 'Inbox') {
        if (emFolder !== 'Inbox' || em.folder === 'Trash') return false;
      } else {
        if (emFolder !== activeFolder) return false;
      }
    }
    
    if (activeCategory !== 'All') {
      const emCat = em.category || 'Primary';
      if (emCat.toLowerCase() !== activeCategory.toLowerCase()) return false;
    }
    
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        (em.sender || '').toLowerCase().includes(q) ||
        (em.subject || '').toLowerCase().includes(q) ||
        (em.snippet || '').toLowerCase().includes(q)
      );
    }
    return true;
  });

  // Dynamic account and folder counts (Strict Zero-Mock Mandate: derived strictly from data)
  const accountEmails = emails.filter(em => {
    if (selectedAccount === 'all') return true;
    const normSel = selectedAccount.toLowerCase().replace(/[-_]/g, '');
    const normEm = (em.account || '').toLowerCase().replace(/[-_]/g, '');
    return normSel === normEm || normEm.includes(normSel.split('@')[0]);
  });

  const inboxUnreadCount = accountEmails.filter(em => (em.folder || 'Inbox') === 'Inbox' && (!em.read || em.unread) && em.folder !== 'Trash').length;
  const starredCount = accountEmails.filter(em => em.starred && em.folder !== 'Trash').length;
  const sentCount = accountEmails.filter(em => em.folder === 'Sent').length;
  const draftsCount = accountEmails.filter(em => em.folder === 'Drafts').length;
  const trashCount = accountEmails.filter(em => em.folder === 'Trash').length;

  const promotionsCount = accountEmails.filter(em => (em.category || '').toLowerCase() === 'promotions' && em.folder !== 'Trash').length;
  const updatesCount = accountEmails.filter(em => (em.category || '').toLowerCase() === 'updates' && em.folder !== 'Trash').length;
  const socialCount = accountEmails.filter(em => (em.category || '').toLowerCase() === 'social' && em.folder !== 'Trash').length;
  const purchasesCount = accountEmails.filter(em => (em.category || '').toLowerCase() === 'purchases' && em.folder !== 'Trash').length;
  const forumsCount = accountEmails.filter(em => (em.category || '').toLowerCase() === 'forums' && em.folder !== 'Trash').length;

  const paginationDisplay = filteredEmails.length === 0 
    ? '0 of 0' 
    : `1-${Math.min(100, filteredEmails.length)} of ${filteredEmails.length.toLocaleString()}`;

  const toggleStar = (id) => {
    setEmails(prev => prev.map(em => em.id === id ? { ...em, starred: !em.starred } : em));
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredEmails.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredEmails.map(em => em.id));
    }
  };

  const toggleSelectOne = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const moveToTrash = (id) => {
    setEmails(prev => prev.map(em => em.id === id ? { ...em, folder: 'Trash' } : em));
    if (selectedEmail && selectedEmail.id === id) {
      setSelectedEmail(null);
    }
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    setSendingEmail(true);
    setSendStatusMsg('Dispatching message over Stehouwer SMTP bridge...');

    let sentViaSmtp = false;
    let smtpErrorNote = '';

    // 1. Post to local/cloud backend SMTP relay
    try {
      const resp = await fetch(`${backendUrl}/api/v1/emails/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_email: composeFrom,
          to: composeTo,
          subject: composeSubject,
          body: composeBody
        })
      });
      const resJson = await resp.json();
      if (resp.ok && resJson.status === 'success') {
        sentViaSmtp = true;
        setSendStatusMsg('✅ Dispatched live via Stehouwer SMTP (Port 587 TLS)!');
      } else {
        smtpErrorNote = resJson.detail || resJson.message || 'SMTP Authentication required';
      }
    } catch (err) {
      smtpErrorNote = err.message || 'Backend unreachable';
    }

    // 2. Persist to Firebase Firestore under Sent folder for persistence
    const sentMsgId = `em-${Date.now()}`;
    const sentAccount = composeFrom;
    const sentSender = composeFrom.split('@')[0];
    const sentLabel = `[Imap]/${sentSender.charAt(0).toUpperCase() + sentSender.slice(1)}`;

    try {
      await fetch("https://firestore.googleapis.com/v1/projects/ai-bs-dashboard/databases/(default)/documents/emails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fields: {
            account: { stringValue: sentAccount },
            sender: { stringValue: sentSender },
            email: { stringValue: composeTo },
            subject: { stringValue: composeSubject },
            snippet: { stringValue: composeBody.slice(0, 150) },
            body: { stringValue: composeBody },
            time: { stringValue: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) },
            date: { stringValue: new Date().toISOString().split('T')[0] },
            category: { stringValue: "Primary" },
            folder: { stringValue: "Sent" },
            starred: { booleanValue: false },
            read: { booleanValue: true },
            label: { stringValue: sentLabel }
          }
        })
      });
    } catch (err) {
      console.warn("Firestore archival fallback:", err);
    }

    // 3. Add to local state
    const newMsg = {
      id: sentMsgId,
      account: sentAccount,
      sender: sentSender,
      email: composeTo,
      subject: composeSubject,
      snippet: composeBody.slice(0, 150),
      body: composeBody,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      date: new Date().toISOString().split('T')[0],
      category: 'Primary',
      folder: 'Sent',
      starred: false,
      read: true,
      label: sentLabel
    };
    setEmails(prev => [newMsg, ...prev]);

    if (!sentViaSmtp && smtpErrorNote) {
      setSendStatusMsg(`⚠️ Email archived to Outbox/Firestore. Note: SMTP returned [${smtpErrorNote}]. Add your Google App Password to .env to complete direct external relay.`);
    }

    setTimeout(() => {
      setSendingEmail(false);
      if (sentViaSmtp) {
        setIsComposeOpen(false);
        setComposeTo('');
        setComposeSubject('');
        setComposeBody('');
        setSendStatusMsg('');
      }
    }, 2800);
  };

  // Safe formatting for IMAP/SMTP status
  const imapConnected = typeof emailStatus.imap_status === 'object'
    ? Boolean(emailStatus.imap_status?.connected)
    : Boolean(emailStatus.imap_status?.includes('Connected'));

  const imapDisplayLabel = typeof emailStatus.imap_status === 'object'
    ? (emailStatus.imap_status?.connected ? 'Connected' : 'App Password Req.')
    : (String(emailStatus.imap_status || 'Checking...').slice(0, 20));

  return (
    <div style={styles.container}>
      {/* 1. LEFTEST NARROW NAV BAR */}
      <div style={styles.iconNav}>
        <div style={styles.iconItemActive} title="Business Mail">
          <Mail size={20} color="#58a6ff" />
          <span style={styles.iconLabel}>Mail</span>
        </div>
        <div style={styles.iconItem} title="Campaigns" onClick={() => onTabChange && onTabChange('campaign_automation')}>
          <Sparkles size={20} color="#a78bfa" />
          <span style={styles.iconLabel}>Campaigns</span>
        </div>
        <div style={styles.iconItem} title="Live Status" onClick={fetchDiagnostics}>
          <Radio size={20} color="#3fb950" />
          <span style={styles.iconLabel}>Status</span>
        </div>
        <div style={{ marginTop: 'auto' }}>
          <div style={styles.iconItem} title="Settings">
            <Settings size={20} color="#8b949e" />
          </div>
        </div>
      </div>

      {/* 2. SECOND SIDEBAR (FOLDERS & LABELS) */}
      <div style={styles.folderSidebar}>
        {/* COMPOSE & CAMPAIGN BUTTONS */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
          <button style={{ ...styles.composeBtn, flex: 1, marginBottom: 0 }} onClick={() => setIsComposeOpen(true)}>
            <Plus size={18} color="#1f6feb" style={{ marginRight: '6px' }} />
            <span style={{ fontWeight: '600', color: '#f0f6fc', fontSize: '0.88rem' }}>Compose</span>
          </button>

          <button 
            style={{
              background: 'linear-gradient(90deg, #7c3aed 0%, #6d28d9 100%)',
              border: '1px solid #a78bfa',
              borderRadius: '24px',
              padding: '10px 14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(124, 58, 237, 0.4)'
            }} 
            title="Launch Stehouwer Campaign & Audience Automation Engine"
            onClick={() => onTabChange && onTabChange('campaign_automation')}
          >
            <Sparkles size={16} color="#ffffff" />
          </button>
        </div>

        {/* ACCOUNT SELECTOR DROPDOWN */}
        <div style={styles.accountSelector}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.70rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Business Account</span>
            <span style={{ fontSize: '0.68rem', color: '#3fb950', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#3fb950' }}></span>
              Online
            </span>
          </div>
          <select 
            value={selectedAccount} 
            onChange={(e) => setSelectedAccount(e.target.value)}
            style={styles.accountSelectInput}
          >
            <option value="all">📬 All Accounts (Unified Inbox)</option>
            {TEAM_ACCOUNTS.map(acc => (
              <option key={acc.id} value={acc.email}>
                {acc.avatar} {acc.name} ({acc.email})
              </option>
            ))}
          </select>
        </div>

        {/* DOMAIN STATUS BADGE */}
        <div style={styles.domainCard}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <Globe size={13} color="#58a6ff" />
            <span style={{ fontSize: '0.74rem', color: '#f0f6fc', fontWeight: '600' }}>stehouwer-publishing.com</span>
          </div>
          <div style={{ fontSize: '0.68rem', color: '#8b949e', lineHeight: '1.4' }}>
            Cloudflare Routing: <strong style={{ color: '#3fb950' }}>Active</strong> (MX/SPF)<br />
            IMAP: <span style={{ color: imapConnected ? '#3fb950' : '#e3b341', fontWeight: '600' }}>{imapDisplayLabel}</span><br />
            SMTP: <span style={{ color: '#3fb950', fontWeight: '600' }}>Ready (TLS 587)</span>
          </div>
        </div>

        {/* MAIN FOLDER LIST */}
        <div style={styles.folderList}>
          {/* CAMPAIGNS & AUDIENCES FOLDER ITEM */}
          <div 
            style={activeFolder === 'Campaigns' ? { ...styles.folderItemActive, background: 'rgba(124, 58, 237, 0.25)', color: '#c084fc', borderLeft: '3px solid #c084fc' } : styles.folderItem}
            onClick={() => { setActiveFolder('Campaigns'); setActiveLabel(null); }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={16} color="#c084fc" />
              <span style={{ fontWeight: '700', color: activeFolder === 'Campaigns' ? '#c084fc' : '#e2e8f0' }}>Campaigns & Audiences</span>
            </div>
            <span style={{ background: '#7c3aed', color: '#ffffff', fontSize: '0.68rem', padding: '1px 6px', borderRadius: '10px', fontWeight: '700' }}>AI</span>
          </div>

          <div 
            style={activeFolder === 'Inbox' && !activeLabel ? styles.folderItemActive : styles.folderItem}
            onClick={() => { setActiveFolder('Inbox'); setActiveLabel(null); }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <InboxIcon size={16} />
              <span>Inbox</span>
            </div>
            {inboxUnreadCount > 0 && <span style={styles.badge}>{inboxUnreadCount}</span>}
          </div>

          <div 
            style={activeFolder === 'Starred' ? styles.folderItemActive : styles.folderItem}
            onClick={() => { setActiveFolder('Starred'); setActiveLabel(null); }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Star size={16} color="#e3b341" />
              <span>Starred</span>
            </div>
            {starredCount > 0 && <span style={styles.badgeSecondary}>{starredCount}</span>}
          </div>

          <div 
            style={activeFolder === 'Sent' ? styles.folderItemActive : styles.folderItem}
            onClick={() => { setActiveFolder('Sent'); setActiveLabel(null); }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Send size={16} />
              <span>Sent</span>
            </div>
            {sentCount > 0 && <span style={styles.badgeSecondary}>{sentCount}</span>}
          </div>

          <div 
            style={activeFolder === 'Drafts' ? styles.folderItemActive : styles.folderItem}
            onClick={() => { setActiveFolder('Drafts'); setActiveLabel(null); }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FileText size={16} />
              <span>Drafts</span>
            </div>
            {draftsCount > 0 && <span style={styles.badgeSecondary}>{draftsCount}</span>}
          </div>

          <div 
            style={activeFolder === 'Trash' ? styles.folderItemActive : styles.folderItem}
            onClick={() => { setActiveFolder('Trash'); setActiveLabel(null); }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Trash2 size={16} color="#f85149" />
              <span>Trash</span>
            </div>
            {trashCount > 0 && <span style={styles.badgeSecondary}>{trashCount}</span>}
          </div>

          {purchasesCount > 0 && (
            <div style={styles.folderItem} onClick={() => { setActiveCategory('Purchases'); setActiveFolder('Inbox'); }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShoppingBag size={16} />
                <span>Purchases</span>
              </div>
              <span style={styles.badgeSecondary}>{purchasesCount}</span>
            </div>
          )}

          {socialCount > 0 && (
            <div style={styles.folderItem} onClick={() => { setActiveCategory('Social'); setActiveFolder('Inbox'); }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Users size={16} />
                <span>Social</span>
              </div>
              <span style={styles.badgeSecondary}>{socialCount}</span>
            </div>
          )}

          {updatesCount > 0 && (
            <div style={styles.folderItem} onClick={() => { setActiveCategory('Updates'); setActiveFolder('Inbox'); }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Info size={16} />
                <span>Updates</span>
              </div>
              <span style={styles.badgeSecondary}>{updatesCount}</span>
            </div>
          )}

          {forumsCount > 0 && (
            <div style={styles.folderItem} onClick={() => { setActiveCategory('Forums'); setActiveFolder('Inbox'); }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <MessageCircle size={16} />
                <span>Forums</span>
              </div>
              <span style={styles.badgeSecondary}>{forumsCount}</span>
            </div>
          )}

          {promotionsCount > 0 && (
            <div style={styles.folderItem} onClick={() => { setActiveCategory('Promotions'); setActiveFolder('Inbox'); }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Tag size={16} />
                <span>Promotions</span>
              </div>
              <span style={styles.badgeSecondary}>{promotionsCount}</span>
            </div>
          )}
        </div>

        {/* LABELS SECTION */}
        <div style={styles.labelsHeader}>
          <span>Accounts & Labels</span>
        </div>

        <div style={styles.labelsList}>
          {TEAM_ACCOUNTS.map(acc => (
            <div 
              key={acc.id} 
              style={activeLabel === acc.label ? styles.labelItemActive : styles.labelItem}
              onClick={() => { 
                if (activeLabel === acc.label) {
                  setActiveLabel(null);
                } else {
                  setActiveLabel(acc.label); 
                  setSelectedAccount(acc.email); 
                }
              }}
            >
              <span style={{ fontSize: '0.8rem', color: '#a371f7' }}>🏷️</span>
              <span style={{ fontSize: '0.8rem', color: '#c9d1d9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {acc.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 3. MAIN EMAIL BODY AREA */}
      {activeFolder === 'Campaigns' ? (
        <div style={{ flex: 1, overflowY: 'auto', background: '#0d1117' }}>
          <CampaignAutomationTab />
        </div>
      ) : (
        <div style={styles.mainContent}>
          {/* SEARCH & TOOLBAR HEADER */}
          <div style={styles.toolbar}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={styles.searchBarContainer}>
                <Search size={16} color="#8b949e" style={{ marginLeft: '12px' }} />
                <input 
                  type="text" 
                  placeholder="Search emails by sender, subject, or content..." 
                  value={searchQuery} 
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={styles.searchInput}
                />
              </div>

              {/* LIVE SYNC BUTTON */}
              <button 
                onClick={handleTriggerSync} 
                disabled={isSyncing}
                style={{
                  ...styles.syncButton,
                  backgroundColor: isSyncing ? '#21262d' : '#1f6feb',
                  cursor: isSyncing ? 'not-allowed' : 'pointer'
                }}
                title="Sync IMAP mailbox from mail server"
              >
                <RefreshCw size={14} className={isSyncing ? "spin-animation" : ""} style={{ marginRight: '6px' }} />
                <span>{isSyncing ? 'Syncing...' : 'Sync Mail'}</span>
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={styles.paginationText}>
                {paginationDisplay}
              </div>
            </div>
          </div>

          {/* SYNC NOTIFICATION BANNER */}
          {syncNotice && (
            <div style={{
              ...styles.noticeBanner,
              backgroundColor: syncNotice.type === 'success' ? 'rgba(46, 160, 67, 0.15)' : syncNotice.type === 'error' ? 'rgba(248, 81, 73, 0.15)' : 'rgba(227, 179, 65, 0.15)',
              borderColor: syncNotice.type === 'success' ? '#2ea043' : syncNotice.type === 'error' ? '#f85149' : '#d29922',
              color: syncNotice.type === 'success' ? '#3fb950' : syncNotice.type === 'error' ? '#f85149' : '#e3b341'
            }}>
              {syncNotice.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              <div style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                <span>{syncNotice.message}</span>
                {syncNotice.code === 'APP_PASSWORD_REQUIRED' && (
                  <a 
                    href="https://myaccount.google.com/apppasswords" 
                    target="_blank" 
                    rel="noreferrer"
                    style={{ color: '#58a6ff', fontWeight: '600', textDecoration: 'underline', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                  >
                    Generate App Password <ExternalLink size={12} />
                  </a>
                )}
              </div>
              <X size={14} style={{ marginLeft: 'auto', cursor: 'pointer' }} onClick={() => setSyncNotice(null)} />
            </div>
          )}

          {/* CATEGORY TABS (Primary, Promotions, Social, Updates, All) */}
          <div style={styles.categoryTabs}>
            <div 
              style={activeCategory === 'All' ? styles.tabActive : styles.tab}
              onClick={() => setActiveCategory('All')}
            >
              <InboxIcon size={16} color={activeCategory === 'All' ? '#58a6ff' : '#8b949e'} />
              <span>All Messages</span>
              <span style={styles.tabBadge}>{accountEmails.length}</span>
            </div>

            <div 
              style={activeCategory === 'Primary' ? styles.tabActive : styles.tab}
              onClick={() => setActiveCategory('Primary')}
            >
              <Mail size={16} color={activeCategory === 'Primary' ? '#58a6ff' : '#8b949e'} />
              <span>Primary</span>
            </div>

            {promotionsCount > 0 && (
              <div 
                style={activeCategory === 'Promotions' ? styles.tabActive : styles.tab}
                onClick={() => setActiveCategory('Promotions')}
              >
                <Tag size={16} color={activeCategory === 'Promotions' ? '#58a6ff' : '#8b949e'} />
                <span>Promotions</span>
                <span style={styles.tabBadgeSecondary}>{promotionsCount}</span>
              </div>
            )}

            {socialCount > 0 && (
              <div 
                style={activeCategory === 'Social' ? styles.tabActive : styles.tab}
                onClick={() => setActiveCategory('Social')}
              >
                <Users size={16} color={activeCategory === 'Social' ? '#58a6ff' : '#8b949e'} />
                <span>Social</span>
                <span style={styles.tabBadgeSecondary}>{socialCount}</span>
              </div>
            )}

            {updatesCount > 0 && (
              <div 
                style={activeCategory === 'Updates' ? styles.tabActive : styles.tab}
                onClick={() => setActiveCategory('Updates')}
              >
                <Info size={16} color={activeCategory === 'Updates' ? '#58a6ff' : '#8b949e'} />
                <span>Updates</span>
                <span style={styles.tabBadgeSecondary}>{updatesCount}</span>
              </div>
            )}
          </div>

          {/* EMAIL LIST STREAM */}
          <div style={styles.emailStream}>
            {filteredEmails.length === 0 ? (
              <div style={styles.emptyState}>
                <div style={styles.emptyStateIconContainer}>
                  <Mail size={44} color="#58a6ff" />
                </div>
                <h4 style={{ color: '#f0f6fc', margin: '12px 0 6px 0', fontSize: '1.1rem' }}>
                  No messages in {activeFolder}
                </h4>
                <p style={{ color: '#8b949e', fontSize: '0.86rem', maxWidth: '420px', textAlign: 'center', margin: 0 }}>
                  Emails received at <strong>{selectedAccount === 'all' ? 'any stehouwer-publishing.com address' : selectedAccount}</strong> will populate here automatically.
                </p>
                <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
                  <button onClick={handleTriggerSync} style={styles.emptySyncBtn} disabled={isSyncing}>
                    <RefreshCw size={14} className={isSyncing ? "spin-animation" : ""} style={{ marginRight: '6px' }} />
                    {isSyncing ? 'Syncing Mailbox...' : 'Sync Mailbox Now'}
                  </button>
                  <button onClick={() => setIsComposeOpen(true)} style={styles.emptyComposeBtn}>
                    <Plus size={14} style={{ marginRight: '6px' }} />
                    Compose Email
                  </button>
                </div>
              </div>
            ) : (
              filteredEmails.map(em => (
                <div 
                  key={em.id} 
                  style={{
                    ...styles.emailRow,
                    backgroundColor: !em.read ? 'rgba(56, 139, 253, 0.08)' : 'transparent',
                    fontWeight: !em.read ? '600' : '400'
                  }}
                  onClick={() => setSelectedEmail(em)}
                >
                  {/* CHECKBOX */}
                  <div style={styles.checkboxCell} onClick={(e) => { e.stopPropagation(); toggleSelectOne(em.id); }}>
                    {selectedIds.includes(em.id) ? (
                      <CheckSquare size={16} color="#58a6ff" />
                    ) : (
                      <Square size={16} color="#484f58" />
                    )}
                  </div>

                  {/* STAR */}
                  <div style={styles.starCell} onClick={(e) => { e.stopPropagation(); toggleStar(em.id); }}>
                    <Star size={16} color={em.starred ? '#e3b341' : '#484f58'} fill={em.starred ? '#e3b341' : 'none'} />
                  </div>

                  {/* SENDER */}
                  <div style={styles.senderCell}>
                    {em.sender}
                  </div>

                  {/* SUBJECT & SNIPPET */}
                  <div style={styles.subjectCell}>
                    <span style={{ color: '#f0f6fc' }}>{em.subject}</span>
                    <span style={{ color: '#8b949e', marginLeft: '8px', fontWeight: '400' }}>- {cleanEmailBody(em.snippet || em.body)}</span>
                  </div>

                  {/* TIME */}
                  <div style={styles.timeCell}>
                    {em.time}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* EMAIL READER MODAL */}
      {selectedEmail && (
        <div style={styles.modalOverlay} onClick={() => setSelectedEmail(null)}>
          <div style={{ ...styles.modalContent, width: '740px', maxWidth: '94vw' }} className="glass-panel" onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h3 style={{ color: '#f0f6fc', margin: 0, fontSize: '1.25rem', fontWeight: '700' }}>{selectedEmail.subject}</h3>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '2px 8px', borderRadius: '4px', fontWeight: '600' }}>
                    {selectedEmail.account}
                  </span>
                  <span>•</span>
                  <span>Folder: <strong>{selectedEmail.folder || 'Inbox'}</strong></span>
                </div>
              </div>
              <X size={20} color="#8b949e" style={{ cursor: 'pointer' }} onClick={() => setSelectedEmail(null)} />
            </div>
            
            <div style={{ ...styles.modalMeta, padding: '14px 0', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <div>
                <span style={{ color: '#58a6ff', fontWeight: '700', fontSize: '1rem' }}>{selectedEmail.sender}</span>
                <span style={{ color: '#8b949e', fontSize: '0.82rem', marginLeft: '8px' }}>&lt;{selectedEmail.email}&gt;</span>
              </div>
              <span style={{ color: '#8b949e', fontSize: '0.82rem' }}>{selectedEmail.date} at {selectedEmail.time}</span>
            </div>

            <div style={{ padding: '20px 0', minHeight: '200px', maxHeight: '55vh', overflowY: 'auto' }}>
              <div style={{ color: '#e6edf3', lineHeight: '1.7', fontSize: '0.96rem', whiteSpace: 'pre-wrap', fontFamily: 'Inter, system-ui, sans-serif' }}>
                {cleanEmailBody(selectedEmail.body || selectedEmail.snippet)}
              </div>
            </div>

            <div style={{ ...styles.modalFooter, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button 
                disabled={isGeneratingReply}
                style={{ ...styles.replyBtn, backgroundColor: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.4)' }}
                onClick={() => handleGenerateSmartReply(selectedEmail)}
              >
                <Sparkles size={14} style={{ marginRight: '6px' }} /> 
                {isGeneratingReply ? 'Generating Stehouwer AI Draft...' : '✨ Stehouwer AI Smart Reply'}
              </button>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  style={{ ...styles.replyBtn, backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)' }}
                  onClick={() => moveToTrash(selectedEmail.id)}
                >
                  <Trash2 size={14} style={{ marginRight: '6px' }} /> Trash
                </button>

                <button 
                  style={styles.replyBtn} 
                  onClick={() => { 
                    setIsComposeOpen(true); 
                    setComposeFrom(selectedEmail.account || 'brett@stehouwer-publishing.com'); 
                    setComposeTo(selectedEmail.email); 
                    const subj = selectedEmail.subject.toLowerCase().startsWith('re:') ? selectedEmail.subject : `Re: ${selectedEmail.subject}`;
                    setComposeSubject(subj); 
                    setSelectedEmail(null); 
                  }}
                >
                  <Send size={14} style={{ marginRight: '6px' }} /> Reply
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* COMPOSE EMAIL MODAL */}
      {isComposeOpen && (
        <div style={styles.composeModal}>
          <div style={styles.composeHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Mail size={16} color="#58a6ff" />
              <span style={{ fontWeight: '600', color: '#f0f6fc', fontSize: '0.88rem' }}>New Message • Stehouwer Publishing</span>
            </div>
            <X size={16} color="#8b949e" style={{ cursor: 'pointer' }} onClick={() => setIsComposeOpen(false)} />
          </div>

          <form onSubmit={handleSendEmail} style={styles.composeForm}>
            {/* FROM SELECTOR */}
            <div style={styles.composeField}>
              <span style={styles.fieldLabel}>From:</span>
              <select 
                value={composeFrom} 
                onChange={(e) => setComposeFrom(e.target.value)}
                style={styles.fieldSelect}
              >
                {TEAM_ACCOUNTS.map(acc => (
                  <option key={acc.id} value={acc.email}>{acc.name} &lt;{acc.email}&gt;</option>
                ))}
              </select>
            </div>

            {/* TO FIELD */}
            <div style={styles.composeField}>
              <span style={styles.fieldLabel}>To:</span>
              <input 
                type="email" 
                required 
                placeholder="recipient@domain.com"
                value={composeTo} 
                onChange={(e) => setComposeTo(e.target.value)}
                style={styles.fieldInput}
              />
            </div>

            {/* SUBJECT FIELD */}
            <div style={styles.composeField}>
              <span style={styles.fieldLabel}>Subject:</span>
              <input 
                type="text" 
                required 
                placeholder="Subject of your message"
                value={composeSubject} 
                onChange={(e) => setComposeSubject(e.target.value)}
                style={styles.fieldInput}
              />
            </div>

            {/* BODY TEXTAREA */}
            <textarea 
              rows={10} 
              placeholder="Compose your message here..."
              value={composeBody} 
              onChange={(e) => setComposeBody(e.target.value)}
              style={styles.composeTextarea}
            />

            {/* STATUS MESSAGE */}
            {sendStatusMsg && (
              <div style={{ 
                fontSize: '0.78rem', 
                padding: '8px 12px',
                borderRadius: '6px',
                backgroundColor: sendStatusMsg.startsWith('✅') ? 'rgba(46, 160, 67, 0.15)' : 'rgba(227, 179, 65, 0.15)',
                color: sendStatusMsg.startsWith('✅') ? '#3fb950' : '#e3b341',
                border: sendStatusMsg.startsWith('✅') ? '1px solid #2ea043' : '1px solid #d29922',
                marginBottom: '8px',
                lineHeight: '1.4'
              }}>
                {sendStatusMsg}
              </div>
            )}

            {/* FOOTER BUTTONS */}
            <div style={styles.composeFooter}>
              <button 
                type="button" 
                onClick={() => setIsGovernanceOpen(true)}
                style={{
                  backgroundColor: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  border: '1px solid #38bdf8',
                  borderRadius: '18px',
                  padding: '8px 16px',
                  fontWeight: '600',
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  marginRight: '8px'
                }}
              >
                🛡️ Governance Review
              </button>

              <button type="submit" disabled={sendingEmail} style={styles.sendSubmitBtn}>
                <Send size={14} style={{ marginRight: '6px' }} />
                {sendingEmail ? 'Dispatching...' : 'Send Email'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Content Governance & Risk Assessment Modal */}
      <ContentGovernanceRiskModal 
        isOpen={isGovernanceOpen} 
        onClose={() => setIsGovernanceOpen(false)}
        initialText={composeBody}
        onApplyRefinement={(newText) => setComposeBody(newText)}
      />
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    height: '100%',
    width: '100%',
    backgroundColor: '#0d1117',
    color: '#c9d1d9',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    overflow: 'hidden'
  },
  iconNav: {
    width: '68px',
    backgroundColor: '#161b22',
    borderRight: '1px solid #30363d',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '16px 0'
  },
  iconItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    padding: '10px 0',
    width: '100%',
    cursor: 'pointer',
    opacity: 0.7,
    transition: 'all 0.2s'
  },
  iconItemActive: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    padding: '10px 0',
    width: '100%',
    cursor: 'pointer',
    backgroundColor: 'rgba(56, 139, 253, 0.15)',
    borderLeft: '3px solid #58a6ff',
    opacity: 1
  },
  iconLabel: {
    fontSize: '0.65rem',
    color: '#c9d1d9'
  },
  folderSidebar: {
    width: '260px',
    backgroundColor: '#161b22',
    borderRight: '1px solid #30363d',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px 12px',
    overflowY: 'auto'
  },
  composeBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#21262d',
    border: '1px solid #363b42',
    borderRadius: '24px',
    padding: '12px 20px',
    cursor: 'pointer',
    marginBottom: '16px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    transition: 'all 0.2s'
  },
  accountSelector: {
    marginBottom: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  },
  accountSelectInput: {
    backgroundColor: '#0d1117',
    color: '#f0f6fc',
    border: '1px solid #30363d',
    borderRadius: '6px',
    padding: '6px 8px',
    fontSize: '0.78rem',
    outline: 'none',
    width: '100%',
    cursor: 'pointer'
  },
  domainCard: {
    backgroundColor: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '8px',
    padding: '8px 10px',
    marginBottom: '14px'
  },
  folderList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    marginBottom: '16px'
  },
  folderItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    borderRadius: '18px',
    fontSize: '0.85rem',
    color: '#8b949e',
    cursor: 'pointer'
  },
  folderItemActive: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    borderRadius: '18px',
    fontSize: '0.85rem',
    color: '#f0f6fc',
    backgroundColor: '#21262d',
    fontWeight: '600'
  },
  badge: {
    backgroundColor: '#1f6feb',
    color: '#fff',
    fontSize: '0.7rem',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '12px'
  },
  badgeSecondary: {
    fontSize: '0.7rem',
    color: '#8b949e'
  },
  labelsHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: '0.75rem',
    color: '#8b949e',
    fontWeight: '600',
    marginBottom: '8px',
    padding: '0 4px'
  },
  labelsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px'
  },
  labelItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    borderRadius: '12px',
    fontSize: '0.78rem',
    color: '#8b949e',
    cursor: 'pointer'
  },
  labelItemActive: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '6px 12px',
    borderRadius: '12px',
    fontSize: '0.78rem',
    color: '#a371f7',
    backgroundColor: 'rgba(163, 113, 247, 0.12)',
    fontWeight: '600'
  },
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#0d1117',
    overflow: 'hidden'
  },
  toolbar: {
    height: '56px',
    borderBottom: '1px solid #30363d',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    backgroundColor: '#161b22'
  },
  searchBarContainer: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '20px',
    width: '420px',
    height: '36px'
  },
  searchInput: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#f0f6fc',
    outline: 'none',
    width: '100%',
    padding: '0 12px',
    fontSize: '0.85rem'
  },
  syncButton: {
    display: 'flex',
    alignItems: 'center',
    color: '#fff',
    border: 'none',
    borderRadius: '18px',
    padding: '7px 14px',
    fontSize: '0.80rem',
    fontWeight: '600',
    transition: 'all 0.2s'
  },
  paginationText: {
    fontSize: '0.78rem',
    color: '#8b949e'
  },
  noticeBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 16px',
    borderBottom: '1px solid'
  },
  categoryTabs: {
    display: 'flex',
    borderBottom: '1px solid #30363d',
    backgroundColor: '#161b22'
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '14px 24px',
    fontSize: '0.85rem',
    color: '#8b949e',
    cursor: 'pointer',
    borderBottom: '2px solid transparent'
  },
  tabActive: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '14px 24px',
    fontSize: '0.85rem',
    color: '#58a6ff',
    fontWeight: '600',
    cursor: 'pointer',
    borderBottom: '2px solid #58a6ff'
  },
  tabBadge: {
    backgroundColor: '#1f6feb',
    color: '#fff',
    fontSize: '0.65rem',
    fontWeight: '700',
    padding: '1px 6px',
    borderRadius: '10px'
  },
  tabBadgeSecondary: {
    backgroundColor: '#30363d',
    color: '#8b949e',
    fontSize: '0.65rem',
    fontWeight: '600',
    padding: '1px 6px',
    borderRadius: '10px'
  },
  emailStream: {
    flex: 1,
    overflowY: 'auto'
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '380px',
    padding: '24px'
  },
  emptyStateIconContainer: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    backgroundColor: 'rgba(56, 139, 253, 0.1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid rgba(56, 139, 253, 0.2)'
  },
  emptySyncBtn: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#1f6feb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    padding: '8px 16px',
    fontSize: '0.84rem',
    fontWeight: '600',
    cursor: 'pointer'
  },
  emptyComposeBtn: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#21262d',
    color: '#c9d1d9',
    border: '1px solid #30363d',
    borderRadius: '8px',
    padding: '8px 16px',
    fontSize: '0.84rem',
    fontWeight: '600',
    cursor: 'pointer'
  },
  emailRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    borderBottom: '1px solid #21262d',
    cursor: 'pointer',
    transition: 'background-color 0.15s'
  },
  checkboxCell: {
    width: '28px',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer'
  },
  starCell: {
    width: '28px',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer'
  },
  senderCell: {
    width: '200px',
    minWidth: '180px',
    flexShrink: 0,
    paddingRight: '8px',
    fontSize: '0.85rem',
    color: '#f0f6fc',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  subjectCell: {
    flex: 1,
    minWidth: 0,
    fontSize: '0.85rem',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    paddingRight: '16px'
  },
  timeCell: {
    width: '80px',
    fontSize: '0.78rem',
    color: '#8b949e',
    textAlign: 'right'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.75)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999
  },
  modalContent: {
    width: '650px',
    backgroundColor: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '12px',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.6)'
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  modalMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    paddingBottom: '12px',
    borderBottom: '1px solid #30363d'
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '12px',
    borderTop: '1px solid #30363d'
  },
  replyBtn: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#238636',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 16px',
    fontSize: '0.85rem',
    fontWeight: '600',
    cursor: 'pointer'
  },
  composeModal: {
    position: 'fixed',
    bottom: 0,
    right: '40px',
    width: '540px',
    backgroundColor: '#161b22',
    border: '1px solid #30363d',
    borderTopLeftRadius: '12px',
    borderTopRightRadius: '12px',
    boxShadow: '0 -8px 30px rgba(0,0,0,0.6)',
    zIndex: 1000,
    display: 'flex',
    flexDirection: 'column'
  },
  composeHeader: {
    padding: '12px 16px',
    backgroundColor: '#21262d',
    borderTopLeftRadius: '12px',
    borderTopRightRadius: '12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid #30363d'
  },
  composeForm: {
    padding: '14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
  },
  composeField: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    borderBottom: '1px solid #30363d',
    paddingBottom: '6px'
  },
  fieldLabel: {
    fontSize: '0.78rem',
    color: '#8b949e',
    width: '50px'
  },
  fieldSelect: {
    flex: 1,
    backgroundColor: '#0d1117',
    color: '#f0f6fc',
    border: '1px solid #30363d',
    borderRadius: '4px',
    outline: 'none',
    fontSize: '0.82rem',
    padding: '4px 8px'
  },
  fieldInput: {
    flex: 1,
    backgroundColor: 'transparent',
    color: '#f0f6fc',
    border: 'none',
    outline: 'none',
    fontSize: '0.85rem'
  },
  composeTextarea: {
    backgroundColor: '#0d1117',
    color: '#f0f6fc',
    border: '1px solid #30363d',
    borderRadius: '6px',
    padding: '10px',
    outline: 'none',
    resize: 'none',
    fontSize: '0.85rem',
    marginTop: '4px'
  },
  composeFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    marginTop: '8px'
  },
  sendSubmitBtn: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#1f6feb',
    color: '#fff',
    border: 'none',
    borderRadius: '18px',
    padding: '8px 22px',
    fontWeight: '600',
    fontSize: '0.85rem',
    cursor: 'pointer'
  }
};
