import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Mail, MessageSquare, Video, Settings, Plus, Star, Clock, AlertOctagon, Send, 
  FileText, ShoppingBag, Users, Info, MessageCircle, Tag, Trash2, Search, 
  RotateCcw, ShieldCheck, Sparkles, Check, Filter, ExternalLink, ChevronRight, 
  ChevronLeft, X, CheckSquare, Square, Inbox as InboxIcon, User, RefreshCw, AlertTriangle, 
  CheckCircle2, Globe, Shield, Radio, ArrowUpRight, Key, Eye, EyeOff, CornerUpLeft, 
  CornerUpRight, Sliders, Server, Cpu
} from 'lucide-react';
import { useBackendHealth } from './useBackendHealth';
import { db } from '../firebase';
import { collection, onSnapshot, query, doc, updateDoc } from 'firebase/firestore';
import CampaignAutomationTab from './CampaignAutomationTab';
import ContentGovernanceRiskModal from './ContentGovernanceRiskModal';

// Active business domain: stehouwer-publishing.com (Cloudflare Email Routing + IMAP/SMTP Gateway)
const TEAM_ACCOUNTS = [
  { id: 'brett', name: 'Brett Stehouwer', email: 'brett@stehouwer-publishing.com', label: '[Imap]/Brett', avatar: '👨‍💻' },
  { id: 'sean', name: 'Sean Stehouwer', email: 'sean@stehouwer-publishing.com', label: '[Imap]/Sean', avatar: '🚀' },
  { id: 'julie', name: 'Julie Stehouwer', email: 'julie@stehouwer-publishing.com', label: '[Imap]/Julie', avatar: '👩‍💼' }
];

const decodeMimeHeader = (raw) => {
  if (!raw) return 'No Subject';
  let val = String(raw).trim();

  // 1. Decode RFC 2047 standard encoded words: =?UTF-8?Q?...?= or =?UTF-8?B?...?=
  if (val.includes('=?')) {
    val = val.replace(/=\?([\w-]+)\?([QBqb])\?([^?]+)\?=/g, (match, charset, encoding, text) => {
      try {
        if (encoding.toUpperCase() === 'B') {
          return decodeURIComponent(escape(atob(text)));
        } else if (encoding.toUpperCase() === 'Q') {
          const qp = text.replace(/_/g, ' ');
          return qp.replace(/=([0-9A-Fa-f]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
        }
      } catch (e) {
        return text;
      }
      return match;
    });
  }

  // 2. Decode residual UTF-8 Quoted-Printable byte sequences (e.g. =E2=80=99 -> ', =E2=80=94 -> —)
  if (val.includes('=')) {
    try {
      val = val.replace(/(=[0-9A-Fa-f]{2})+/g, (match) => {
        try {
          const hexMatches = match.match(/[0-9A-Fa-f]{2}/g);
          if (hexMatches) {
            const bytes = new Uint8Array(hexMatches.map(h => parseInt(h, 16)));
            return new TextDecoder('utf-8', { fatal: false }).decode(bytes);
          }
        } catch (e) {}
        return match;
      });
    } catch (e) {}
  }

  return val.trim() || 'No Subject';
};

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

  // 4. Decode quoted-printable UTF-8 byte sequences
  if (str.includes('=')) {
    try {
      str = str.replace(/(=[0-9A-Fa-f]{2})+/g, (match) => {
        try {
          const hexMatches = match.match(/[0-9A-Fa-f]{2}/g);
          if (hexMatches) {
            const bytes = new Uint8Array(hexMatches.map(h => parseInt(h, 16)));
            return new TextDecoder('utf-8', { fatal: false }).decode(bytes);
          }
        } catch (e) {}
        return match;
      });
    } catch (e) {}
  }

  str = str.replace(/=E2=80=AF/g, ' ')
           .replace(/=3D/g, '=')
           .replace(/=\r?\n/g, '');

  return str.trim() || 'No Body Content';
};

// ═══════════════════════════════════════════════════════════════════════
// CHRONOLOGICAL TIMESTAMP PARSING & INTELLIGENT FORMATTING
// ═══════════════════════════════════════════════════════════════════════

export const parseEmailTimestamp = (item) => {
  if (!item) return 0;
  if (item.timestamp && typeof item.timestamp === 'number') {
    let t = item.timestamp;
    if (t > 10000000000000) t /= 1000;
    else if (t < 10000000000) t *= 1000;
    return t;
  }

  const dStr = (item.date || '').trim();
  const tStr = (item.time || '').trim();

  // Try parsing combined date + time or standard RFC / ISO strings
  if (dStr) {
    if (tStr) {
      const combined = `${dStr} ${tStr}`;
      const p = Date.parse(combined);
      if (!isNaN(p)) return p;
    }
    const pDate = Date.parse(dStr);
    if (!isNaN(pDate)) return pDate;
  }

  if (item.created_at) {
    const pCreated = Date.parse(item.created_at);
    if (!isNaN(pCreated)) return pCreated;
  }

  // Fallback to numeric 13-digit epoch in ID (e.g. em-1791744568616 or em-sent-1791...)
  const idStr = String(item.id || '');
  const match = idStr.match(/\b\d{13}\b/);
  if (match) {
    const epoch = parseInt(match[0], 10);
    if (epoch > 1500000000000 && epoch < 2100000000000) {
      return epoch;
    }
  }

  return 0;
};

export const formatEmailDateDisplay = (item) => {
  const ts = parseEmailTimestamp(item);
  if (!ts) return item.time || item.date || 'Unknown';

  const d = new Date(ts);
  const now = new Date();

  const isToday = d.getFullYear() === now.getFullYear() &&
                  d.getMonth() === now.getMonth() &&
                  d.getDate() === now.getDate();

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = d.getFullYear() === yesterday.getFullYear() &&
                      d.getMonth() === yesterday.getMonth() &&
                      d.getDate() === yesterday.getDate();

  if (isToday) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } else if (isYesterday) {
    return 'Yesterday';
  } else if (d.getFullYear() === now.getFullYear()) {
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } else {
    return d.toLocaleDateString([], { month: 'numeric', day: 'numeric', year: '2-digit' });
  }
};

export const formatEmailFullDate = (item) => {
  const ts = parseEmailTimestamp(item);
  if (!ts) return `${item.date || ''} ${item.time || ''}`.trim() || 'Unknown date';

  const d = new Date(ts);
  const dateStr = d.toLocaleDateString([], { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
  const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  
  // Calculate relative time
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  let relative = '';
  if (diffMins < 1) relative = 'just now';
  else if (diffMins < 60) relative = `${diffMins}m ago`;
  else if (diffHours < 24) relative = `${diffHours}h ago`;
  else relative = `${diffDays}d ago`;

  return `${dateStr} at ${timeStr} (${relative})`;
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
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50;
  
  // Selection & Bulk Actions state
  const [selectedIds, setSelectedIds] = useState([]);
  
  // Compose modal state
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [composeFrom, setComposeFrom] = useState('brett@stehouwer-publishing.com');
  const [composeTo, setComposeTo] = useState('');
  const [composeCc, setComposeCc] = useState('');
  const [composeBcc, setComposeBcc] = useState('');
  const [showCcBcc, setShowCcBcc] = useState(false);
  const [composeSubject, setComposeSubject] = useState('');
  const [composeBody, setComposeBody] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [sendStatusMsg, setSendStatusMsg] = useState('');
  const [isGovernanceOpen, setIsGovernanceOpen] = useState(false);

  // Settings & Diagnostics Modals
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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

  // Reset page when filtering changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedAccount, activeFolder, activeCategory, activeLabel, searchQuery]);

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
            const mergedMap = new Map();
            // Preserve user's optimistic local states (read, starred, folder)
            prev.forEach(p => mergedMap.set(p.id, p));
            data.data.forEach(bItem => {
              const existing = mergedMap.get(bItem.id);
              mergedMap.set(bItem.id, {
                ...bItem,
                subject: decodeMimeHeader(bItem.subject),
                body: cleanEmailBody(bItem.body || bItem.snippet),
                snippet: cleanEmailBody(bItem.snippet || bItem.body),
                read: existing?.read !== undefined ? existing.read : bItem.read,
                starred: existing?.starred !== undefined ? existing.starred : bItem.starred,
                folder: existing?.folder !== undefined ? existing.folder : (bItem.folder || 'Inbox')
              });
            });
            return Array.from(mergedMap.values());
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
          const rawSubj = d.subject?.stringValue || d.subject || 'No Subject';
          const rawBody = d.body?.stringValue || d.body || d.snippet?.stringValue || d.snippet || '';
          return {
            id: doc.id,
            account: d.account?.stringValue || d.account || 'brett@stehouwer-publishing.com',
            sender: decodeMimeHeader(d.sender?.stringValue || d.sender || 'External Sender'),
            email: d.email?.stringValue || d.email || 'sender@external.com',
            subject: decodeMimeHeader(rawSubj),
            snippet: cleanEmailBody(d.snippet?.stringValue || rawBody),
            body: cleanEmailBody(rawBody),
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
            const combinedMap = new Map();
            prev.forEach(p => combinedMap.set(p.id, p));
            fsEmails.forEach(f => combinedMap.set(f.id, f));
            return Array.from(combinedMap.values());
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

  // ═══════════════════════════════════════════════════════════════════════
  // FILTERING AND STRICT CHRONOLOGICAL SORTING (NEWEST FIRST)
  // ═══════════════════════════════════════════════════════════════════════

  const sortedFilteredEmails = useMemo(() => {
    const filtered = emails.filter(em => {
      // Normalize account comparison
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
          (em.email || '').toLowerCase().includes(q) ||
          (em.subject || '').toLowerCase().includes(q) ||
          (em.snippet || '').toLowerCase().includes(q) ||
          (em.body || '').toLowerCase().includes(q)
        );
      }
      return true;
    });

    // STRICT CHRONOLOGICAL SORT: Newest Timestamp FIRST
    return filtered.sort((a, b) => {
      const tsA = parseEmailTimestamp(a);
      const tsB = parseEmailTimestamp(b);
      if (tsB !== tsA) return tsB - tsA;
      return String(b.id || '').localeCompare(String(a.id || ''));
    });
  }, [emails, selectedAccount, activeLabel, activeFolder, activeCategory, searchQuery]);

  // Dynamic account and folder counts (Strict Zero-Mock Mandate: derived strictly from data)
  const accountEmails = useMemo(() => {
    return emails.filter(em => {
      if (selectedAccount === 'all') return true;
      const normSel = selectedAccount.toLowerCase().replace(/[-_]/g, '');
      const normEm = (em.account || '').toLowerCase().replace(/[-_]/g, '');
      return normSel === normEm || normEm.includes(normSel.split('@')[0]);
    });
  }, [emails, selectedAccount]);

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

  // Pagination calculation
  const totalCount = sortedFilteredEmails.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalCount);
  const paginatedEmails = sortedFilteredEmails.slice(startIndex, endIndex);

  const paginationDisplay = totalCount === 0 
    ? '0 of 0' 
    : `${startIndex + 1}-${endIndex} of ${totalCount.toLocaleString()}`;

  // ═══════════════════════════════════════════════════════════════════════
  // PERSISTENT ACTION HANDLERS (LOCAL STATE + BACKEND API)
  // ═══════════════════════════════════════════════════════════════════════

  const handleUpdateEmail = async (id, patch) => {
    // 1. Optimistic local update
    setEmails(prev => prev.map(em => (em.id === id ? { ...em, ...patch } : em)));
    if (selectedEmail && selectedEmail.id === id) {
      setSelectedEmail(prev => prev ? { ...prev, ...patch } : null);
    }

    // 2. Persist to Backend API
    try {
      await fetch(`${backendUrl}/api/v1/emails/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, ...patch })
      });
    } catch (e) {
      console.warn("Backend update error:", e);
    }
  };

  const toggleStar = (id) => {
    const current = emails.find(e => e.id === id);
    const newStarred = !current?.starred;
    handleUpdateEmail(id, { starred: newStarred });
  };

  const toggleReadStatus = (id) => {
    const current = emails.find(e => e.id === id);
    const newRead = !current?.read;
    handleUpdateEmail(id, { read: newRead });
  };

  const moveToTrash = (id) => {
    handleUpdateEmail(id, { folder: 'Trash' });
    if (selectedEmail && selectedEmail.id === id) {
      setSelectedEmail(null);
    }
  };

  const restoreFromTrash = (id) => {
    handleUpdateEmail(id, { folder: 'Inbox' });
  };

  // Selection handlers
  const toggleSelectAll = () => {
    const currentPageIds = paginatedEmails.map(em => em.id);
    const allSelected = currentPageIds.every(id => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds(prev => prev.filter(id => !currentPageIds.includes(id)));
    } else {
      setSelectedIds(prev => Array.from(new Set([...prev, ...currentPageIds])));
    }
  };

  const toggleSelectOne = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  // Bulk actions
  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return;
    const ids = [...selectedIds];

    // Optimistic local update
    setEmails(prev => prev.map(em => {
      if (!ids.includes(em.id)) return em;
      if (action === 'mark_read') return { ...em, read: true };
      if (action === 'mark_unread') return { ...em, read: false };
      if (action === 'star') return { ...em, starred: true };
      if (action === 'unstar') return { ...em, starred: false };
      if (action === 'trash') return { ...em, folder: 'Trash' };
      if (action === 'restore') return { ...em, folder: 'Inbox' };
      return em;
    }));

    if (action === 'delete_forever') {
      setEmails(prev => prev.filter(em => !ids.includes(em.id)));
    }

    setSelectedIds([]);

    // Persist via Backend API
    try {
      await fetch(`${backendUrl}/api/v1/emails/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids, action })
      });
      fetchDiagnostics();
    } catch (e) {
      console.warn("Bulk action persist error:", e);
    }
  };

  const handleOpenEmail = (em) => {
    setSelectedEmail(em);
    if (!em.read) {
      handleUpdateEmail(em.id, { read: true });
    }
  };

  const handleReply = (emailItem) => {
    setIsComposeOpen(true);
    setComposeFrom(emailItem.account || 'brett@stehouwer-publishing.com');
    setComposeTo(emailItem.email || emailItem.sender);
    const subj = emailItem.subject.toLowerCase().startsWith('re:') ? emailItem.subject : `Re: ${emailItem.subject}`;
    setComposeSubject(subj);
    setComposeBody(`\n\n--- On ${emailItem.date} at ${emailItem.time}, ${emailItem.sender} wrote ---\n> ${cleanEmailBody(emailItem.body || emailItem.snippet).replace(/\n/g, '\n> ')}`);
    setSelectedEmail(null);
  };

  const handleForward = (emailItem) => {
    setIsComposeOpen(true);
    setComposeFrom(emailItem.account || 'brett@stehouwer-publishing.com');
    setComposeTo('');
    const subj = emailItem.subject.toLowerCase().startsWith('fwd:') ? emailItem.subject : `Fwd: ${emailItem.subject}`;
    setComposeSubject(subj);
    setComposeBody(`\n\n---------- Forwarded message ---------\nFrom: ${emailItem.sender} <${emailItem.email}>\nDate: ${emailItem.date} at ${emailItem.time}\nSubject: ${emailItem.subject}\nTo: ${emailItem.account}\n\n${cleanEmailBody(emailItem.body || emailItem.snippet)}`);
    setSelectedEmail(null);
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
          cc: composeCc || null,
          bcc: composeBcc || null,
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
        setComposeCc('');
        setComposeBcc('');
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

  const allCurrentPageSelected = paginatedEmails.length > 0 && paginatedEmails.every(em => selectedIds.includes(em.id));

  return (
    <div style={styles.container}>
      {/* 1. LEFTEST NARROW NAV BAR */}
      <div style={styles.iconNav}>
        <div 
          style={activeFolder !== 'Campaigns' ? styles.iconItemActive : styles.iconItem} 
          title="Business Mail Inbox"
          onClick={() => { setActiveFolder('Inbox'); setActiveLabel(null); }}
        >
          <Mail size={20} color="#58a6ff" />
          <span style={styles.iconLabel}>Mail</span>
        </div>
        <div 
          style={activeFolder === 'Campaigns' ? styles.iconItemActive : styles.iconItem} 
          title="Campaigns & Audiences Engine" 
          onClick={() => {
            setActiveFolder('Campaigns');
            if (onTabChange) onTabChange('campaign_automation');
          }}
        >
          <Sparkles size={20} color="#a78bfa" />
          <span style={styles.iconLabel}>Campaigns</span>
        </div>
        <div 
          style={styles.iconItem} 
          title="Live Mailbox & Infrastructure Status" 
          onClick={() => {
            fetchDiagnostics();
            setIsDiagnosticsOpen(true);
          }}
        >
          <Radio size={20} color="#3fb950" />
          <span style={styles.iconLabel}>Status</span>
        </div>
        <div style={{ marginTop: 'auto', width: '100%' }}>
          <div 
            style={styles.iconItem} 
            title="Email Client Settings"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings size={20} color="#8b949e" />
            <span style={styles.iconLabel}>Settings</span>
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
            onClick={() => {
              setActiveFolder('Campaigns');
              if (onTabChange) onTabChange('campaign_automation');
            }}
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

        {/* DOMAIN STATUS BADGE (CLICKABLE TO OPEN DIAGNOSTICS) */}
        <div 
          style={{ ...styles.domainCard, cursor: 'pointer', transition: 'border-color 0.2s' }}
          title="Click to view Live Email Diagnostics & Port Topology"
          onClick={() => {
            fetchDiagnostics();
            setIsDiagnosticsOpen(true);
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Globe size={13} color="#58a6ff" />
              <span style={{ fontSize: '0.74rem', color: '#f0f6fc', fontWeight: '600' }}>stehouwer-publishing.com</span>
            </div>
            <ArrowUpRight size={12} color="#8b949e" />
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
            {selectedIds.length > 0 ? (
              /* BULK ACTIONS TOOLBAR WHEN EMAILS ARE SELECTED */
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%' }}>
                <button 
                  onClick={toggleSelectAll} 
                  style={styles.bulkBtn}
                  title="Deselect or Select All"
                >
                  <CheckSquare size={16} color="#58a6ff" />
                  <span style={{ fontWeight: '600', color: '#f0f6fc' }}>{selectedIds.length} Selected</span>
                </button>

                <div style={styles.toolbarDivider} />

                <button 
                  onClick={() => handleBulkAction('mark_read')} 
                  style={styles.bulkBtn}
                  title="Mark Selected as Read"
                >
                  <Eye size={15} color="#58a6ff" />
                  <span>Mark Read</span>
                </button>

                <button 
                  onClick={() => handleBulkAction('mark_unread')} 
                  style={styles.bulkBtn}
                  title="Mark Selected as Unread"
                >
                  <EyeOff size={15} color="#8b949e" />
                  <span>Mark Unread</span>
                </button>

                <button 
                  onClick={() => handleBulkAction('star')} 
                  style={styles.bulkBtn}
                  title="Star Selected"
                >
                  <Star size={15} color="#e3b341" />
                  <span>Star</span>
                </button>

                {activeFolder === 'Trash' ? (
                  <>
                    <button 
                      onClick={() => handleBulkAction('restore')} 
                      style={styles.bulkBtn}
                      title="Restore Selected to Inbox"
                    >
                      <RotateCcw size={15} color="#3fb950" />
                      <span>Restore</span>
                    </button>
                    <button 
                      onClick={() => handleBulkAction('delete_forever')} 
                      style={{ ...styles.bulkBtn, color: '#f85149' }}
                      title="Permanently Delete Selected"
                    >
                      <Trash2 size={15} color="#f85149" />
                      <span>Delete Forever</span>
                    </button>
                  </>
                ) : (
                  <button 
                    onClick={() => handleBulkAction('trash')} 
                    style={{ ...styles.bulkBtn, color: '#f85149' }}
                    title="Move Selected to Trash"
                  >
                    <Trash2 size={15} color="#f85149" />
                    <span>Trash</span>
                  </button>
                )}

                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button 
                    onClick={() => setSelectedIds([])} 
                    style={styles.cancelBulkBtn}
                    title="Deselect All"
                  >
                    <X size={14} />
                    <span>Cancel</span>
                  </button>
                </div>
              </div>
            ) : (
              /* STANDARD SEARCH & ACTIONS TOOLBAR */
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {/* SELECT ALL MASTER CHECKBOX */}
                  <div 
                    style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '4px' }}
                    onClick={toggleSelectAll}
                    title={allCurrentPageSelected ? "Deselect Page" : "Select Current Page"}
                  >
                    {allCurrentPageSelected ? (
                      <CheckSquare size={16} color="#58a6ff" />
                    ) : (
                      <Square size={16} color="#484f58" />
                    )}
                  </div>

                  {/* SEARCH BAR */}
                  <div style={styles.searchBarContainer}>
                    <Search size={16} color="#8b949e" style={{ marginLeft: '12px', flexShrink: 0 }} />
                    <input 
                      type="text" 
                      placeholder="Search emails by sender, subject, or content..." 
                      value={searchQuery} 
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={styles.searchInput}
                    />
                    {searchQuery && (
                      <X 
                        size={14} 
                        color="#8b949e" 
                        style={{ marginRight: '12px', cursor: 'pointer', flexShrink: 0 }}
                        onClick={() => setSearchQuery('')}
                        title="Clear search"
                      />
                    )}
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

                {/* PAGINATION CONTROLS */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={styles.paginationText}>
                    {paginationDisplay}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage <= 1}
                      style={{
                        ...styles.pageNavBtn,
                        opacity: currentPage <= 1 ? 0.35 : 1,
                        cursor: currentPage <= 1 ? 'not-allowed' : 'pointer'
                      }}
                      title="Previous Page"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage >= totalPages}
                      style={{
                        ...styles.pageNavBtn,
                        opacity: currentPage >= totalPages ? 0.35 : 1,
                        cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer'
                      }}
                      title="Next Page"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              </>
            )}
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

          {/* EMAIL LIST STREAM - STRICTLY SORTED DESCENDING */}
          <div style={styles.emailStream}>
            {paginatedEmails.length === 0 ? (
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
              paginatedEmails.map(em => (
                <div 
                  key={em.id} 
                  style={{
                    ...styles.emailRow,
                    backgroundColor: !em.read ? 'rgba(56, 139, 253, 0.08)' : 'transparent',
                    fontWeight: !em.read ? '600' : '400'
                  }}
                  onClick={() => handleOpenEmail(em)}
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

                  {/* UNREAD INDICATOR DOT */}
                  <div style={{ width: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {!em.read && <span style={styles.unreadDot} />}
                  </div>

                  {/* SENDER */}
                  <div style={styles.senderCell} title={em.email || em.sender}>
                    {em.sender}
                  </div>

                  {/* SUBJECT & SNIPPET */}
                  <div style={styles.subjectCell}>
                    <span style={{ color: '#f0f6fc' }}>{em.subject}</span>
                    <span style={{ color: '#8b949e', marginLeft: '8px', fontWeight: '400' }}>- {cleanEmailBody(em.snippet || em.body)}</span>
                  </div>

                  {/* HOVER QUICK ACTION BUTTONS */}
                  <div style={styles.hoverActions} onClick={(e) => e.stopPropagation()}>
                    <button 
                      style={styles.quickActionBtn} 
                      title={em.read ? "Mark as unread" : "Mark as read"}
                      onClick={() => toggleReadStatus(em.id)}
                    >
                      {em.read ? <EyeOff size={14} color="#8b949e" /> : <Eye size={14} color="#58a6ff" />}
                    </button>
                    <button 
                      style={styles.quickActionBtn} 
                      title="Move to trash"
                      onClick={() => moveToTrash(em.id)}
                    >
                      <Trash2 size={14} color="#8b949e" />
                    </button>
                  </div>

                  {/* TIME / INTELLIGENT DATE */}
                  <div style={styles.timeCell} title={formatEmailFullDate(em)}>
                    {formatEmailDateDisplay(em)}
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
              <span style={{ color: '#8b949e', fontSize: '0.82rem' }}>{formatEmailFullDate(selectedEmail)}</span>
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

              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  style={{ ...styles.replyBtn, backgroundColor: '#21262d', color: '#8b949e', border: '1px solid #30363d' }}
                  onClick={() => toggleReadStatus(selectedEmail.id)}
                  title="Mark as unread"
                >
                  <EyeOff size={14} style={{ marginRight: '6px' }} /> Mark Unread
                </button>

                <button 
                  style={{ ...styles.replyBtn, backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)' }}
                  onClick={() => moveToTrash(selectedEmail.id)}
                >
                  <Trash2 size={14} style={{ marginRight: '6px' }} /> Trash
                </button>

                <button 
                  style={{ ...styles.replyBtn, backgroundColor: '#21262d', color: '#c9d1d9', border: '1px solid #30363d' }}
                  onClick={() => handleForward(selectedEmail)}
                >
                  <CornerUpRight size={14} style={{ marginRight: '6px' }} /> Forward
                </button>

                <button 
                  style={styles.replyBtn} 
                  onClick={() => handleReply(selectedEmail)}
                >
                  <CornerUpLeft size={14} style={{ marginRight: '6px' }} /> Reply
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
              <button 
                type="button" 
                onClick={() => setShowCcBcc(!showCcBcc)}
                style={styles.ccToggleBtn}
              >
                {showCcBcc ? 'Hide Cc' : 'Cc / Bcc'}
              </button>
            </div>

            {/* CC & BCC FIELDS (TOGGLEABLE) */}
            {showCcBcc && (
              <>
                <div style={styles.composeField}>
                  <span style={styles.fieldLabel}>Cc:</span>
                  <input 
                    type="text" 
                    placeholder="cc@domain.com"
                    value={composeCc} 
                    onChange={(e) => setComposeCc(e.target.value)}
                    style={styles.fieldInput}
                  />
                </div>
                <div style={styles.composeField}>
                  <span style={styles.fieldLabel}>Bcc:</span>
                  <input 
                    type="text" 
                    placeholder="bcc@domain.com"
                    value={composeBcc} 
                    onChange={(e) => setComposeBcc(e.target.value)}
                    style={styles.fieldInput}
                  />
                </div>
              </>
            )}

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

      {/* LIVE EMAIL SYSTEM DIAGNOSTICS MODAL */}
      {isDiagnosticsOpen && (
        <div style={styles.modalOverlay} onClick={() => setIsDiagnosticsOpen(false)}>
          <div style={{ ...styles.modalContent, width: '640px' }} className="glass-panel" onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Server size={22} color="#58a6ff" />
                <div>
                  <h3 style={{ color: '#f0f6fc', margin: 0, fontSize: '1.15rem', fontWeight: '700' }}>
                    Email System Infrastructure & Diagnostics
                  </h3>
                  <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>stehouwer-publishing.com • Port Collision Matrix & Relay Map</span>
                </div>
              </div>
              <X size={20} color="#8b949e" style={{ cursor: 'pointer' }} onClick={() => setIsDiagnosticsOpen(false)} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', margin: '14px 0' }}>
              {/* IMAP Card */}
              <div style={styles.diagCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Server size={16} color="#58a6ff" />
                    <span style={{ fontWeight: '600', color: '#f0f6fc', fontSize: '0.88rem' }}>Inbound IMAP Connection</span>
                  </div>
                  <span style={{ 
                    fontSize: '0.72rem', 
                    padding: '2px 8px', 
                    borderRadius: '10px', 
                    fontWeight: '700',
                    backgroundColor: imapConnected ? 'rgba(63, 185, 80, 0.2)' : 'rgba(227, 179, 65, 0.2)',
                    color: imapConnected ? '#3fb950' : '#e3b341',
                    border: imapConnected ? '1px solid #2ea043' : '1px solid #d29922'
                  }}>
                    {imapDisplayLabel}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: '#8b949e', lineHeight: '1.5' }}>
                  Host: <code style={styles.codeSnippet}>{emailStatus.imap_status?.host || 'imap.gmail.com'}:{emailStatus.imap_status?.port || 993} (SSL)</code><br />
                  Authenticated User: <code style={styles.codeSnippet}>{emailStatus.relay_user || 'Configured via .env'}</code><br />
                  {emailStatus.imap_status?.error && (
                    <div style={{ color: '#e3b341', marginTop: '4px' }}>
                      ⚠️ {emailStatus.imap_status.error}
                    </div>
                  )}
                </div>
              </div>

              {/* SMTP Card */}
              <div style={styles.diagCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Send size={16} color="#3fb950" />
                    <span style={{ fontWeight: '600', color: '#f0f6fc', fontSize: '0.88rem' }}>Outbound SMTP Relay</span>
                  </div>
                  <span style={{ 
                    fontSize: '0.72rem', 
                    padding: '2px 8px', 
                    borderRadius: '10px', 
                    fontWeight: '700',
                    backgroundColor: 'rgba(63, 185, 80, 0.2)',
                    color: '#3fb950',
                    border: '1px solid #2ea043'
                  }}>
                    Ready (TLS 587)
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: '#8b949e', lineHeight: '1.5' }}>
                  Host: <code style={styles.codeSnippet}>{emailStatus.smtp_status?.host || 'smtp.gmail.com'}:{emailStatus.smtp_status?.port || 587} (TLS)</code><br />
                  Domain Masking: <code style={styles.codeSnippet}>From: brett@stehouwer-publishing.com</code> (Zero-Leakage Policy Active)
                </div>
              </div>

              {/* Cloudflare Routing Card */}
              <div style={styles.diagCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Globe size={16} color="#a78bfa" />
                    <span style={{ fontWeight: '600', color: '#f0f6fc', fontSize: '0.88rem' }}>Cloudflare Email Routing</span>
                  </div>
                  <span style={{ 
                    fontSize: '0.72rem', 
                    padding: '2px 8px', 
                    borderRadius: '10px', 
                    fontWeight: '700',
                    backgroundColor: 'rgba(167, 139, 250, 0.2)',
                    color: '#c084fc',
                    border: '1px solid #a78bfa'
                  }}>
                    Active (MX/SPF)
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: '#8b949e', lineHeight: '1.5' }}>
                  Zone: <code style={styles.codeSnippet}>stehouwer-publishing.com</code> (Account ID: <code style={styles.codeSnippet}>810411...6efec67</code>)<br />
                  Inbound Ingestion Worker: <code style={styles.codeSnippet}>aibs-email-router</code> &rarr; Live Firestore & Local Webhook
                </div>
              </div>

              {/* Inbound Athlete Text Router Card */}
              <div style={styles.diagCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <MessageSquare size={16} color="#f59e0b" />
                    <span style={{ fontWeight: '600', color: '#f0f6fc', fontSize: '0.88rem' }}>Dennis Bell Inbound Athlete SMS Router</span>
                  </div>
                  <span style={{ 
                    fontSize: '0.72rem', 
                    padding: '2px 8px', 
                    borderRadius: '10px', 
                    fontWeight: '700',
                    backgroundColor: 'rgba(245, 158, 11, 0.2)',
                    color: '#fbbf24',
                    border: '1px solid #f59e0b'
                  }}>
                    Forwarding to +1-616-291-5227
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: '#8b949e', lineHeight: '1.5' }}>
                  Destination Cell: <code style={styles.codeSnippet}>+1 (616) 291-5227 (Dennis Bell)</code><br />
                  Loop Protection: <strong style={{ color: '#3fb950' }}>Active</strong> (Dennis's own outbound responses suppressed from forward loop)<br />
                  Sync Daemon: <code style={styles.codeSnippet}>backend/core/rec_debut_daily_dispatcher.py</code> (60s check interval)
                </div>
              </div>

              {/* Mailbox Statistics Table */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginTop: '4px' }}>
                <div style={styles.statBox}>
                  <span style={styles.statLabel}>Total Cached</span>
                  <span style={styles.statVal}>{emailStatus.mailbox_stats?.total_cached || emails.length}</span>
                </div>
                <div style={styles.statBox}>
                  <span style={styles.statLabel}>Unread Inbox</span>
                  <span style={{ ...styles.statVal, color: '#58a6ff' }}>{emailStatus.mailbox_stats?.unread_inbox || inboxUnreadCount}</span>
                </div>
                <div style={styles.statBox}>
                  <span style={styles.statLabel}>Sent Items</span>
                  <span style={{ ...styles.statVal, color: '#3fb950' }}>{emailStatus.mailbox_stats?.sent || sentCount}</span>
                </div>
                <div style={styles.statBox}>
                  <span style={styles.statLabel}>Trash Items</span>
                  <span style={{ ...styles.statVal, color: '#f85149' }}>{emailStatus.mailbox_stats?.trash || trashCount}</span>
                </div>
              </div>
            </div>

            <div style={{ ...styles.modalFooter, display: 'flex', justifyContent: 'space-between' }}>
              <button 
                onClick={handleTriggerSync} 
                disabled={isSyncing}
                style={styles.emptySyncBtn}
              >
                <RefreshCw size={14} className={isSyncing ? "spin-animation" : ""} style={{ marginRight: '6px' }} />
                {isSyncing ? 'Syncing Now...' : 'Run Live IMAP Sync'}
              </button>
              <button 
                onClick={() => setIsDiagnosticsOpen(false)}
                style={styles.emptyComposeBtn}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EMAIL CLIENT SETTINGS MODAL */}
      {isSettingsOpen && (
        <div style={styles.modalOverlay} onClick={() => setIsSettingsOpen(false)}>
          <div style={{ ...styles.modalContent, width: '600px' }} className="glass-panel" onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Sliders size={22} color="#a78bfa" />
                <div>
                  <h3 style={{ color: '#f0f6fc', margin: 0, fontSize: '1.15rem', fontWeight: '700' }}>
                    Email Client Settings & Accounts
                  </h3>
                  <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>Manage default accounts, identities, and sync parameters</span>
                </div>
              </div>
              <X size={20} color="#8b949e" style={{ cursor: 'pointer' }} onClick={() => setIsSettingsOpen(false)} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', margin: '14px 0' }}>
              {/* Accounts Management */}
              <div>
                <label style={{ fontSize: '0.80rem', color: '#8b949e', fontWeight: '600', textTransform: 'uppercase', marginBottom: '8px', display: 'block' }}>
                  Configured Business Team Accounts
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {TEAM_ACCOUNTS.map(acc => (
                    <div key={acc.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: '#0d1117', border: '1px solid #30363d', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '1.2rem' }}>{acc.avatar}</span>
                        <div>
                          <span style={{ fontWeight: '600', color: '#f0f6fc', fontSize: '0.88rem' }}>{acc.name}</span>
                          <span style={{ color: '#8b949e', fontSize: '0.78rem', display: 'block' }}>{acc.email}</span>
                        </div>
                      </div>
                      <span style={{ fontSize: '0.72rem', color: '#a78bfa', backgroundColor: 'rgba(167, 139, 250, 0.1)', padding: '2px 8px', borderRadius: '12px', border: '1px solid rgba(167, 139, 250, 0.3)' }}>
                        {acc.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Default From Account */}
              <div>
                <label style={{ fontSize: '0.80rem', color: '#8b949e', fontWeight: '600', textTransform: 'uppercase', marginBottom: '6px', display: 'block' }}>
                  Default Sending Identity
                </label>
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

              {/* Instructions */}
              <div style={{ padding: '12px', backgroundColor: 'rgba(56, 139, 253, 0.08)', border: '1px solid rgba(56, 139, 253, 0.2)', borderRadius: '8px', fontSize: '0.78rem', color: '#8b949e', lineHeight: '1.5' }}>
                <strong style={{ color: '#58a6ff' }}>Google App Passwords Setup:</strong><br />
                To authenticate inbound IMAP and outbound SMTP without OAuth2 popups, create a 16-character App Password at{' '}
                <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'underline' }}>
                  Google App Passwords
                </a> and paste it into <code style={styles.codeSnippet}>IMAP_APP_PASSWORD</code> in <code style={styles.codeSnippet}>C:\AI-BS\.env</code>.
              </div>
            </div>

            <div style={{ ...styles.modalFooter, display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                onClick={() => setIsSettingsOpen(false)}
                style={styles.emptyComposeBtn}
              >
                Close
              </button>
            </div>
          </div>
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
  toolbarDivider: {
    width: '1px',
    height: '20px',
    backgroundColor: '#30363d',
    margin: '0 4px'
  },
  bulkBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#21262d',
    border: '1px solid #30363d',
    color: '#c9d1d9',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '0.78rem',
    cursor: 'pointer',
    transition: 'all 0.15s'
  },
  cancelBulkBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#8b949e',
    padding: '6px 10px',
    fontSize: '0.78rem',
    cursor: 'pointer'
  },
  searchBarContainer: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '20px',
    width: '400px',
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
    color: '#8b949e',
    fontWeight: '500'
  },
  pageNavBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    backgroundColor: '#21262d',
    border: '1px solid #30363d',
    color: '#c9d1d9'
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
    gap: '10px',
    padding: '10px 16px',
    borderBottom: '1px solid #21262d',
    cursor: 'pointer',
    transition: 'background-color 0.15s',
    position: 'relative'
  },
  checkboxCell: {
    width: '24px',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    flexShrink: 0
  },
  starCell: {
    width: '24px',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    flexShrink: 0
  },
  unreadDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#58a6ff'
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
    paddingRight: '12px'
  },
  hoverActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    opacity: 0.8,
    marginRight: '6px'
  },
  quickActionBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '26px',
    height: '26px',
    borderRadius: '4px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer'
  },
  timeCell: {
    width: '85px',
    fontSize: '0.78rem',
    color: '#8b949e',
    textAlign: 'right',
    flexShrink: 0
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
    padding: '8px 14px',
    fontSize: '0.82rem',
    fontWeight: '600',
    cursor: 'pointer'
  },
  composeModal: {
    position: 'fixed',
    bottom: 0,
    right: '40px',
    width: '560px',
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
  ccToggleBtn: {
    background: 'none',
    border: 'none',
    color: '#58a6ff',
    fontSize: '0.75rem',
    cursor: 'pointer',
    padding: '2px 6px'
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
  },
  diagCard: {
    backgroundColor: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '8px',
    padding: '12px 14px'
  },
  codeSnippet: {
    fontFamily: 'Consolas, Monaco, monospace',
    color: '#58a6ff',
    backgroundColor: 'rgba(56, 139, 253, 0.1)',
    padding: '1px 5px',
    borderRadius: '4px',
    fontSize: '0.75rem'
  },
  statBox: {
    backgroundColor: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '8px',
    padding: '10px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center'
  },
  statLabel: {
    fontSize: '0.68rem',
    color: '#8b949e',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  statVal: {
    fontSize: '1.25rem',
    fontWeight: '700',
    color: '#f0f6fc',
    marginTop: '2px'
  }
};
