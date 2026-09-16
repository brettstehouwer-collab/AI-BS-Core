import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';
import { db } from '../firebase';
import { collection, onSnapshot, getDocs } from 'firebase/firestore';
import { ADMIN_EMAILS } from './accessControl';

// Base Known Core Founders & Executives for styling defaults
const BASE_KNOWN_MEMBERS = [
  {
    email: 'brettstehouwer@gmail.com',
    name: 'Brett Stehouwer',
    role: 'Founder & CTO',
    avatar: '👑',
    color: '#38bdf8'
  },
  {
    uid: 'sEq0Yw9wRhZBYOsvgR0J5RjKjMJ3',
    email: 'footballstar0325@gmail.com',
    name: 'Brett Stehouwer (Mobile)',
    role: 'Lead Administrator',
    avatar: '⚡',
    color: '#38bdf8'
  },
  {
    uid: 'Kv1rQ1ftcybun9PSHDIX90o3KGl2',
    email: 'footballsyat0325@gmail.com',
    name: 'Brett Stehouwer (Mobile Alt)',
    role: 'Lead Administrator',
    avatar: '⚡',
    color: '#38bdf8'
  },
  {
    email: 'stehouwer@gmail.com',
    name: 'Stehouwer Executive',
    role: 'Executive Partner',
    avatar: '🛡️',
    color: '#38bdf8'
  },
  {
    uid: 'RaAUbpN4OPMwv2wKgU6qxwSBciB2',
    email: 'stehouwerjulie@gmail.com',
    name: 'Julie Stehouwer (Mom)',
    role: 'Executive Partner',
    avatar: '🌸',
    color: '#ec4899'
  },
  {
    uid: 'P6aAPT5n0QdiinJsmPEMI5DVsqj1',
    email: 'theseandaley@gmail.com',
    name: 'Sean Daley',
    role: 'Production & Creative Partner',
    avatar: '🎬',
    color: '#a855f7'
  },
  {
    uid: 'YlAH2rLCEcZ71b9WrVCM3rS4MvD3',
    email: 'rottierannajoy@gmail.com',
    name: 'Anna Joy Rottier',
    role: 'Executive Partner & Strategy',
    avatar: '✨',
    color: '#10b981'
  },
  {
    uid: 'Kv1rQ1ftcybun9PSHDIX90o3KGl2',
    email: 'keith@evolution6media.com',
    name: 'Keith (Evolution 6 Media)',
    role: 'Media & Production Partner',
    avatar: '🎥',
    color: '#f59e0b'
  }
];

/**
 * Bulletproof User Avatar Component:
 * - Gracefully handles Google profile photo URLs (renders rounded <img> with fallback)
 * - Gracefully handles emojis (👑, ⚡, 🌸, 🎬, ✨, etc.)
 * - Gracefully handles missing/invalid avatars by displaying user initials or standard fallback
 * - Never overflows, bursts parent flex container, or overlaps surrounding UI
 */
function UserAvatar({ avatar, name = '', size = 42, showBadge = false, isOnline = false, borderColor = 'rgba(56, 189, 248, 0.3)' }) {
  const [imgError, setImgError] = useState(false);

  const isUrl = typeof avatar === 'string' && (
    avatar.startsWith('http://') ||
    avatar.startsWith('https://') ||
    avatar.startsWith('/') ||
    avatar.startsWith('data:')
  );

  // Compute initials as fallback
  const getInitials = (n) => {
    if (!n) return '👤';
    const parts = n.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const isEmoji = !isUrl && typeof avatar === 'string' && avatar.length > 0 && avatar.length <= 4;

  return (
    <div style={{
      position: 'relative',
      width: `${size}px`,
      height: `${size}px`,
      flexShrink: 0,
      display: 'inline-block'
    }}>
      {isUrl && !imgError ? (
        <img
          src={avatar}
          alt={name || 'User'}
          onError={() => setImgError(true)}
          style={{
            width: `${size}px`,
            height: `${size}px`,
            borderRadius: '50%',
            objectFit: 'cover',
            border: `2px solid ${borderColor}`,
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
            display: 'block'
          }}
        />
      ) : (
        <div style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.98))',
          border: `2px solid ${borderColor}`,
          color: '#f8fafc',
          fontSize: isEmoji ? `${Math.round(size * 0.52)}px` : `${Math.round(size * 0.38)}px`,
          fontWeight: '800',
          letterSpacing: '-0.02em',
          userSelect: 'none',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
        }}>
          {isEmoji ? avatar : getInitials(name)}
        </div>
      )}

      {showBadge && (
        <span
          title={isOnline ? 'Online Now' : 'Offline'}
          style={{
            position: 'absolute',
            bottom: '0px',
            right: '0px',
            width: `${Math.max(10, Math.round(size * 0.28))}px`,
            height: `${Math.max(10, Math.round(size * 0.28))}px`,
            borderRadius: '50%',
            background: isOnline ? '#22c55e' : '#64748b',
            border: '2px solid #0f172a',
            boxShadow: isOnline ? '0 0 8px #22c55e' : 'none'
          }}
        />
      )}
    </div>
  );
}

// Option Icon helper: Prevents raw URLs from showing inside <option> tags
const getOptionIcon = (avatar) => {
  if (!avatar || typeof avatar !== 'string') return '👤';
  if (avatar.startsWith('http') || avatar.length > 4) return '👤';
  return avatar;
};

export default function UserSessionTelemetryWidget({ backendUrl }) {
  const apiHost = backendUrl || getApiBase() || '';
  const [telemetry, setTelemetry] = useState({
    total_active_now: 0,
    total_sessions_recorded: 0,
    total_dwell_time_seconds: 0,
    live_users: [],
    last_seen_users: [],
    recent_sessions: [],
    user_aggregates: []
  });
  const [firestoreUsers, setFirestoreUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [selectedUserFilter, setSelectedUserFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL'); // ALL, ACTIVE, CLOSED
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [isSyncingFirebase, setIsSyncingFirebase] = useState(false);
  const [firebaseSyncStatus, setFirebaseSyncStatus] = useState(null);

  // 1. Fetch Backend SQLite Telemetry Summary
  const fetchSessionTelemetry = async () => {
    try {
      const res = await fetch(`${apiHost}/api/telemetry/user-sessions/summary`);
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
        setLastRefreshed(new Date());
      }
    } catch (err) {
      console.debug('Failed to fetch user session telemetry:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Periodic Telemetry Polling
  useEffect(() => {
    fetchSessionTelemetry();
    if (!isAutoRefresh) return;
    const interval = setInterval(fetchSessionTelemetry, 5000);
    return () => clearInterval(interval);
  }, [apiHost, isAutoRefresh]);

  // 2. Real-time Firebase Firestore Users Listener & Dynamic Sync
  const syncUsersWithBackend = async (usersList) => {
    if (!usersList || usersList.length === 0) return;
    try {
      setIsSyncingFirebase(true);
      const res = await fetch(`${apiHost}/api/telemetry/user-sessions/sync-users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ users: usersList })
      });
      if (res.ok) {
        const result = await res.json();
        setFirebaseSyncStatus(`Synced ${result.synced_users_count || usersList.length} users with SQLite`);
        fetchSessionTelemetry();
      }
    } catch (err) {
      console.debug('Firebase to SQLite sync error:', err);
    } finally {
      setIsSyncingFirebase(false);
    }
  };

  useEffect(() => {
    if (!db) return;
    try {
      const usersRef = collection(db, 'users');
      const unsubscribe = onSnapshot(usersRef, (snapshot) => {
        const extracted = [];
        snapshot.forEach((docSnap) => {
          const data = docSnap.data();
          if (data && (data.email || data.user_email)) {
            const cleanEmail = (data.email || data.user_email).toLowerCase().trim();
            const known = BASE_KNOWN_MEMBERS.find((m) => m.email.toLowerCase() === cleanEmail);
            extracted.push({
              uid: docSnap.id,
              email: cleanEmail,
              user_email: cleanEmail,
              displayName: data.displayName || data.name || data.user_name || (known ? known.name : cleanEmail.split('@')[0]),
              photoURL: data.photoURL || data.avatar || (known ? known.avatar : '👤'),
              role: data.role || (known ? known.role : (ADMIN_EMAILS.includes(cleanEmail) ? 'Master Admin' : 'Authorized Operator')),
              color: data.color || (known ? known.color : '#38bdf8'),
              isOnline: Boolean(data.isOnline),
              lastSeen: data.lastSeen
            });
          }
        });

        setFirestoreUsers(extracted);
        if (extracted.length > 0) {
          syncUsersWithBackend(extracted);
        }
      }, (error) => {
        console.debug('Firestore users subscription inactive:', error);
      });

      return () => unsubscribe();
    } catch (e) {
      console.debug('Firestore users collection unavailable:', e);
    }
  }, [apiHost]);

  // Manual Trigger to re-fetch and push all Firebase users
  const handleManualFirebaseSync = async () => {
    if (!db) return;
    try {
      setIsSyncingFirebase(true);
      const snapshot = await getDocs(collection(db, 'users'));
      const extracted = [];
      snapshot.forEach((docSnap) => {
        const data = docSnap.data();
        if (data && (data.email || data.user_email)) {
          const cleanEmail = (data.email || data.user_email).toLowerCase().trim();
          const known = BASE_KNOWN_MEMBERS.find((m) => m.email.toLowerCase() === cleanEmail);
          extracted.push({
            uid: docSnap.id,
            email: cleanEmail,
            user_email: cleanEmail,
            displayName: data.displayName || data.name || data.user_name || (known ? known.name : cleanEmail.split('@')[0]),
            photoURL: data.photoURL || data.avatar || (known ? known.avatar : '👤'),
            role: data.role || (known ? known.role : (ADMIN_EMAILS.includes(cleanEmail) ? 'Master Admin' : 'Authorized Operator')),
            color: data.color || (known ? known.color : '#38bdf8'),
            isOnline: Boolean(data.isOnline),
            lastSeen: data.lastSeen
          });
        }
      });
      setFirestoreUsers(extracted);
      await syncUsersWithBackend(extracted);
    } catch (e) {
      console.warn('Manual Firebase sync failed:', e);
    } finally {
      setIsSyncingFirebase(false);
    }
  };

  // Helper Formatters
  const formatDuration = (seconds) => {
    if (!seconds || seconds <= 0) return '0s';
    const s = Math.round(seconds);
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  const formatTimestamp = (epochMs) => {
    if (!epochMs) return '—';
    const d = new Date(epochMs);
    if (isNaN(d.getTime())) return '—';
    return (
      d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
      ' · ' +
      d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
    );
  };

  const formatRelativeTime = (secondsAgo) => {
    if (secondsAgo === null || secondsAgo === undefined) return 'Never';
    if (secondsAgo < 10) return 'Just now';
    if (secondsAgo < 60) return `${Math.round(secondsAgo)}s ago`;
    const mins = Math.floor(secondsAgo / 60);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ${mins % 60}m ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  // 3. Assemble Dynamic Operator Roster for Dropdown Filter
  const allOperatorsMap = new Map();

  // Seed base known members
  BASE_KNOWN_MEMBERS.forEach((km) => {
    allOperatorsMap.set(km.email.toLowerCase(), {
      email: km.email.toLowerCase(),
      name: km.name,
      avatar: km.avatar,
      role: km.role
    });
  });

  // Seed ADMIN_EMAILS
  ADMIN_EMAILS.forEach((email) => {
    const clean = email.toLowerCase().trim();
    if (!allOperatorsMap.has(clean)) {
      allOperatorsMap.set(clean, {
        email: clean,
        name: clean.split('@')[0].toUpperCase(),
        avatar: '👤',
        role: 'Admin Partner'
      });
    }
  });

  // Add all Firestore users
  firestoreUsers.forEach((fu) => {
    const clean = fu.email.toLowerCase();
    const existing = allOperatorsMap.get(clean) || {};
    allOperatorsMap.set(clean, {
      email: clean,
      name: fu.displayName || existing.name || clean.split('@')[0],
      avatar: fu.photoURL || existing.avatar || '👤',
      role: fu.role || existing.role || 'Authorized Member'
    });
  });

  // Add all SQLite registered / last seen users
  (telemetry.last_seen_users || []).forEach((lu) => {
    const clean = lu.user_email?.toLowerCase();
    if (!clean) return;
    const existing = allOperatorsMap.get(clean) || {};
    allOperatorsMap.set(clean, {
      email: clean,
      name: lu.user_name || existing.name || clean.split('@')[0],
      avatar: lu.user_avatar || existing.avatar || '👤',
      role: lu.user_role || existing.role || 'Authorized Member'
    });
  });

  // Add Live Users
  (telemetry.live_users || []).forEach((lu) => {
    const clean = lu.user_email?.toLowerCase();
    if (!clean) return;
    const existing = allOperatorsMap.get(clean) || {};
    allOperatorsMap.set(clean, {
      email: clean,
      name: lu.user_name || existing.name || clean.split('@')[0],
      avatar: lu.user_avatar || existing.avatar || '👤',
      role: lu.user_role || existing.role || 'Authorized Member'
    });
  });

  const allAvailableOperators = Array.from(allOperatorsMap.values()).sort((a, b) =>
    (a.name || '').localeCompare(b.name || '')
  );

  // 4. Merge Last Seen Roster (SQLite + Firestore + Base Members)
  const combinedLastSeen = [...(telemetry.last_seen_users || [])];
  const seenEmails = new Set(combinedLastSeen.map((u) => u.user_email?.toLowerCase()));

  firestoreUsers.forEach((fu) => {
    if (!seenEmails.has(fu.email.toLowerCase())) {
      combinedLastSeen.push({
        user_email: fu.email,
        user_name: fu.displayName,
        user_avatar: fu.photoURL,
        user_role: fu.role,
        color: fu.color || '#38bdf8',
        is_online: fu.isOnline ? 1 : 0,
        status: fu.isOnline ? 'ACTIVE' : 'OFFLINE',
        started_at: null,
        last_heartbeat: null,
        ended_at: null,
        duration_seconds: 0.0,
        current_tab: fu.isOnline ? 'Active' : 'Offline',
        activity_label: 'Registered in Firebase',
        seconds_ago: null
      });
      seenEmails.add(fu.email.toLowerCase());
    }
  });

  // Also include any BASE_KNOWN_MEMBERS not yet tracked
  BASE_KNOWN_MEMBERS.forEach((bm) => {
    if (!seenEmails.has(bm.email.toLowerCase())) {
      combinedLastSeen.push({
        user_email: bm.email,
        user_name: bm.name,
        user_avatar: bm.avatar,
        user_role: bm.role,
        color: bm.color || '#38bdf8',
        is_online: 0,
        status: 'OFFLINE',
        started_at: null,
        last_heartbeat: null,
        ended_at: null,
        duration_seconds: 0.0,
        current_tab: 'Offline',
        activity_label: 'Standby Core Executive',
        seconds_ago: null
      });
      seenEmails.add(bm.email.toLowerCase());
    }
  });

  // Sort last seen: Active first, then most recently seen, then alphabetical
  combinedLastSeen.sort((a, b) => {
    if (a.is_online !== b.is_online) return b.is_online - a.is_online;
    const timeA = a.last_heartbeat || a.started_at || 0;
    const timeB = b.last_heartbeat || b.started_at || 0;
    if (timeA !== timeB) return timeB - timeA;
    return (a.user_name || '').localeCompare(b.user_name || '');
  });

  // 5. Filtered Chronological Sessions
  const filteredSessions = (telemetry.recent_sessions || []).filter((sess) => {
    // Operator Filter
    if (selectedUserFilter !== 'ALL' && sess.user_email?.toLowerCase() !== selectedUserFilter.toLowerCase()) {
      return false;
    }
    // Status Filter
    if (statusFilter === 'ACTIVE' && !sess.is_online) return false;
    if (statusFilter === 'CLOSED' && sess.is_online) return false;

    // Search Query Filter
    if (searchFilter) {
      const q = searchFilter.toLowerCase().trim();
      const matchEmail = sess.user_email?.toLowerCase().includes(q);
      const matchName = sess.user_name?.toLowerCase().includes(q);
      const matchTab = sess.current_tab?.toLowerCase().includes(q);
      const matchActivity = sess.activity_label?.toLowerCase().includes(q);
      const matchPlatform = sess.client_platform?.toLowerCase().includes(q);
      return matchEmail || matchName || matchTab || matchActivity || matchPlatform;
    }
    return true;
  });

  // Export Filtered Sessions to CSV
  const exportSessionsToCsv = () => {
    if (filteredSessions.length === 0) return;
    const headers = ['Session ID', 'User Name', 'Email', 'Role', 'Status', 'Started At', 'Ended At', 'Duration (s)', 'Tab', 'Activity', 'Platform'];
    const rows = filteredSessions.map(s => [
      s.session_id || '',
      `"${(s.user_name || '').replace(/"/g, '""')}"`,
      `"${(s.user_email || '').replace(/"/g, '""')}"`,
      `"${(s.user_role || '').replace(/"/g, '""')}"`,
      s.is_online ? 'ACTIVE' : (s.status || 'CLOSED'),
      s.started_at ? new Date(s.started_at).toISOString() : '',
      s.ended_at ? new Date(s.ended_at).toISOString() : '',
      s.duration_seconds || 0,
      `"${(s.current_tab || '').replace(/"/g, '""')}"`,
      `"${(s.activity_label || '').replace(/"/g, '""')}"`,
      `"${(s.client_platform || '').replace(/"/g, '""')}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `ai_bs_telemetry_audit_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', color: '#e2e8f0', width: '100%', boxSizing: 'border-box' }}>
      
      {/* ─── Header & Telemetry Controls ─── */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.75) 100%)',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: '14px',
        padding: '18px 22px',
        backdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.37)'
      }}>
        <div style={{ flex: '1 1 400px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '24px' }}>👥</span>
            <h3 style={{ margin: 0, fontSize: '20px', fontWeight: '800', color: '#38bdf8', letterSpacing: '-0.01em' }}>
              Live User Presence, Dwell Time & Session Audit Telemetry
            </h3>
          </div>
          <p style={{ margin: '6px 0 0 0', fontSize: '12px', color: '#cbd5e1', lineHeight: '1.5' }}>
            Zero-cost SQLite & Firebase real-time telemetry matrix tracking active operators, session durations, login/logout timestamps, and active tools across the AI-BS ecosystem.
          </p>
          {firebaseSyncStatus && (
            <div style={{ marginTop: '6px', fontSize: '11px', color: '#4ade80', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span>✓</span> {firebaseSyncStatus}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <button
            onClick={handleManualFirebaseSync}
            disabled={isSyncingFirebase}
            title="Sync all Firestore users into SQLite telemetry database"
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(14, 165, 233, 0.3))',
              border: '1px solid rgba(56, 189, 248, 0.5)',
              color: '#38bdf8',
              fontSize: '12px',
              fontWeight: '700',
              cursor: isSyncingFirebase ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 8px rgba(56, 189, 248, 0.15)'
            }}
          >
            <span>☁️</span> {isSyncingFirebase ? 'Syncing Firebase...' : 'Sync Firebase Roster'}
          </button>

          <button
            onClick={() => setIsAutoRefresh(!isAutoRefresh)}
            title="Toggle periodic live heartbeat polling"
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              background: isAutoRefresh ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              border: isAutoRefresh ? '1px solid #22c55e' : '1px solid #ef4444',
              color: isAutoRefresh ? '#4ade80' : '#f87171',
              fontSize: '12px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s ease'
            }}
          >
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: isAutoRefresh ? '#22c55e' : '#ef4444',
              boxShadow: isAutoRefresh ? '0 0 8px #22c55e' : 'none'
            }} />
            {isAutoRefresh ? 'Auto-Refresh: 5s' : 'Auto-Refresh: Paused'}
          </button>

          <button
            onClick={fetchSessionTelemetry}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: '#fff',
              fontSize: '12px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s ease'
            }}
          >
            🔄 Refresh
          </button>
          
          {lastRefreshed && (
            <span style={{ fontSize: '11px', color: '#94a3b8', background: 'rgba(0,0,0,0.3)', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
              Updated {lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
        </div>
      </div>

      {/* ─── Top Telemetry KPI Cards ─── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px'
      }}>
        {/* KPI 1: Active Online */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(6, 78, 59, 0.25))',
          border: '1px solid rgba(34, 197, 94, 0.35)',
          borderTop: '3px solid #22c55e',
          borderRadius: '12px',
          padding: '18px 20px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '800' }}>
              Active Users Online
            </span>
            <span style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: '#22c55e',
              boxShadow: '0 0 10px #22c55e'
            }} />
          </div>
          <div style={{ fontSize: '32px', fontWeight: '900', color: '#4ade80', marginTop: '8px' }}>
            {telemetry.total_active_now}
          </div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
            Heartbeat ping within last 65s
          </div>
        </div>

        {/* KPI 2: Total Dwell Time */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(14, 116, 144, 0.25))',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          borderTop: '3px solid #38bdf8',
          borderRadius: '12px',
          padding: '18px 20px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '800' }}>
              Total Dwell Time Logged
            </span>
            <span style={{ fontSize: '16px' }}>⏱️</span>
          </div>
          <div style={{ fontSize: '28px', fontWeight: '900', color: '#38bdf8', marginTop: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {formatDuration(telemetry.total_dwell_time_seconds)}
          </div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
            Across all verified sessions
          </div>
        </div>

        {/* KPI 3: Total Sessions */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(88, 28, 135, 0.25))',
          border: '1px solid rgba(168, 85, 247, 0.35)',
          borderTop: '3px solid #c084fc',
          borderRadius: '12px',
          padding: '18px 20px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '800' }}>
              Total Sessions Recorded
            </span>
            <span style={{ fontSize: '16px' }}>📋</span>
          </div>
          <div style={{ fontSize: '32px', fontWeight: '900', color: '#c084fc', marginTop: '8px' }}>
            {telemetry.total_sessions_recorded}
          </div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
            Persistent SQLite audit storage
          </div>
        </div>

        {/* KPI 4: Authorized Operators */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(120, 53, 15, 0.25))',
          border: '1px solid rgba(245, 158, 11, 0.35)',
          borderTop: '3px solid #fbbf24',
          borderRadius: '12px',
          padding: '18px 20px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '800' }}>
              Total Authorized Operators
            </span>
            <span style={{ fontSize: '16px' }}>🛡️</span>
          </div>
          <div style={{ fontSize: '32px', fontWeight: '900', color: '#fbbf24', marginTop: '8px' }}>
            {allAvailableOperators.length}
          </div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '4px' }}>
            Firebase + SQLite verified roster
          </div>
        </div>
      </div>

      {/* ─── SECTION 1: LIVE ONLINE OPERATORS ─── */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.8)',
        border: '1px solid rgba(34, 197, 94, 0.25)',
        borderRadius: '14px',
        padding: '20px 24px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: '#22c55e',
              boxShadow: '0 0 10px #22c55e'
            }} />
            <h4 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: '#4ade80' }}>
              Currently Online Operators ({telemetry.live_users?.length || 0})
            </h4>
          </div>
          <span style={{ fontSize: '11px', color: '#94a3b8', background: 'rgba(34, 197, 94, 0.1)', padding: '4px 10px', borderRadius: '6px', border: '1px solid rgba(34, 197, 94, 0.3)' }}>
            Real-Time WebSocket & Heartbeat Mesh
          </span>
        </div>

        {(!telemetry.live_users || telemetry.live_users.length === 0) ? (
          <div style={{
            background: 'rgba(2, 6, 23, 0.45)',
            border: '1px dashed rgba(255, 255, 255, 0.12)',
            borderRadius: '10px',
            padding: '28px',
            textAlign: 'center',
            color: '#94a3b8',
            fontSize: '13px'
          }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>📡</div>
            <div style={{ fontWeight: '600', color: '#cbd5e1' }}>No other operators actively transmitting heartbeats right now.</div>
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
              Active browser tabs register within 5–10 seconds of interaction.
            </div>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '14px'
          }}>
            {telemetry.live_users.map((u) => (
              <div key={u.session_id} style={{
                background: 'linear-gradient(135deg, rgba(2, 6, 23, 0.8), rgba(15, 23, 42, 0.9))',
                border: '1px solid rgba(34, 197, 94, 0.45)',
                borderRadius: '12px',
                padding: '16px',
                display: 'flex',
                gap: '14px',
                alignItems: 'flex-start',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)'
              }}>
                <UserAvatar
                  avatar={u.user_avatar}
                  name={u.user_name}
                  size={46}
                  showBadge={true}
                  isOnline={true}
                  borderColor="rgba(34, 197, 94, 0.5)"
                />

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                    <div style={{
                      fontWeight: '800',
                      fontSize: '15px',
                      color: '#f8fafc',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {u.user_name}
                    </div>
                    <span style={{
                      background: 'rgba(34, 197, 94, 0.2)',
                      color: '#4ade80',
                      border: '1px solid rgba(34, 197, 94, 0.5)',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '10px',
                      fontWeight: '800',
                      letterSpacing: '0.05em'
                    }}>
                      LIVE NOW
                    </span>
                  </div>

                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ color: '#38bdf8', fontWeight: '600' }}>{u.user_role}</span> • <span>{u.user_email}</span>
                  </div>

                  <div style={{
                    marginTop: '10px',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    fontSize: '11px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#94a3b8' }}>Active Tool / Tab:</span>
                      <span style={{
                        color: '#38bdf8',
                        fontWeight: '700',
                        background: 'rgba(56, 189, 248, 0.1)',
                        padding: '2px 8px',
                        borderRadius: '6px',
                        border: '1px solid rgba(56, 189, 248, 0.2)'
                      }}>
                        {u.activity_label || u.current_tab}
                      </span>
                    </div>

                    <div style={{ marginTop: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#94a3b8' }}>Session Duration:</span>
                      <span style={{ color: '#4ade80', fontWeight: '800', fontSize: '12px' }}>
                        {formatDuration(u.live_duration_seconds)}
                      </span>
                    </div>

                    <div style={{ marginTop: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#64748b', fontSize: '10px' }}>
                      <span>Heartbeat Ping:</span>
                      <span>{u.seconds_since_heartbeat !== undefined ? `${u.seconds_since_heartbeat}s ago` : 'Active'}</span>
                    </div>
                  </div>

                  <div style={{ marginTop: '8px', fontSize: '10px', color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Opened: {formatTimestamp(u.started_at)}</span>
                    <span style={{ color: '#94a3b8' }}>{u.client_platform || 'Desktop'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ─── SECTION 2: WHO WAS ON LAST & ALL TEAM MEMBERS STATUS ─── */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.8)',
        border: '1px solid rgba(56, 189, 248, 0.2)',
        borderRadius: '14px',
        padding: '20px 24px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '18px',
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>🕒</span>
              <h4 style={{ margin: 0, fontSize: '17px', fontWeight: '800', color: '#38bdf8' }}>
                Team Member Last-Seen & Total Time Spent ({combinedLastSeen.length} Operators)
              </h4>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
              Identifies who was on last, how long they were active, what tool they used, and login/logout activity across all Firebase & SQLite operators.
            </p>
          </div>

          <span style={{
            fontSize: '11px',
            color: '#cbd5e1',
            background: 'rgba(56, 189, 248, 0.1)',
            padding: '5px 12px',
            borderRadius: '8px',
            border: '1px solid rgba(56, 189, 248, 0.25)'
          }}>
            Showing all {combinedLastSeen.length} verified operators
          </span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          gap: '16px'
        }}>
          {combinedLastSeen.map((member) => {
            const isOnline = Boolean(member.is_online);
            return (
              <div
                key={member.user_email}
                style={{
                  background: 'linear-gradient(135deg, rgba(2, 6, 23, 0.85) 0%, rgba(15, 23, 42, 0.9) 100%)',
                  border: isOnline ? '1px solid rgba(34, 197, 94, 0.5)' : '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  boxShadow: isOnline ? '0 4px 20px rgba(34, 197, 94, 0.15)' : '0 4px 12px rgba(0, 0, 0, 0.25)',
                  transition: 'transform 0.2s ease, border-color 0.2s ease',
                  overflow: 'hidden'
                }}
              >
                {/* Operator Header: Avatar + Identity + Status Pill */}
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <UserAvatar
                    avatar={member.user_avatar}
                    name={member.user_name}
                    size={44}
                    showBadge={true}
                    isOnline={isOnline}
                    borderColor={isOnline ? 'rgba(34, 197, 94, 0.6)' : 'rgba(255, 255, 255, 0.2)'}
                  />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                      <div style={{
                        fontWeight: '800',
                        fontSize: '14px',
                        color: '#fff',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        {member.user_name}
                      </div>

                      <span style={{
                        fontSize: '10px',
                        padding: '3px 9px',
                        borderRadius: '12px',
                        fontWeight: '800',
                        letterSpacing: '0.04em',
                        flexShrink: 0,
                        background: isOnline ? 'rgba(34, 197, 94, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                        color: isOnline ? '#4ade80' : '#cbd5e1',
                        border: isOnline ? '1px solid rgba(34, 197, 94, 0.5)' : '1px solid rgba(100, 116, 139, 0.3)'
                      }}>
                        {isOnline ? '● ONLINE' : formatRelativeTime(member.seconds_ago)}
                      </span>
                    </div>

                    <div style={{
                      fontSize: '11px',
                      color: member.color || '#38bdf8',
                      fontWeight: '600',
                      marginTop: '2px',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {member.user_role}
                    </div>

                    <div style={{
                      fontSize: '11px',
                      color: '#94a3b8',
                      marginTop: '1px',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {member.user_email}
                    </div>
                  </div>
                </div>

                {/* Structured Metrics Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '8px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '8px',
                  padding: '10px'
                }}>
                  <div>
                    <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '700' }}>
                      Last Active Tab
                    </div>
                    <div style={{
                      marginTop: '3px',
                      fontSize: '12px',
                      fontWeight: '700',
                      color: '#38bdf8',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {member.current_tab || 'Offline'}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '700' }}>
                      Total Time Logged
                    </div>
                    <div style={{
                      marginTop: '3px',
                      fontSize: '12px',
                      fontWeight: '800',
                      color: '#fbbf24',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {formatDuration(member.duration_seconds)}
                    </div>
                  </div>

                  <div style={{ gridColumn: 'span 2', borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '6px', marginTop: '2px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                      <span style={{ color: '#94a3b8' }}>Last Heartbeat / Activity:</span>
                      <span style={{ color: '#cbd5e1', fontWeight: '600' }}>
                        {member.last_heartbeat ? formatTimestamp(member.last_heartbeat) : (member.activity_label || 'Registered')}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginTop: '3px' }}>
                      <span style={{ color: '#94a3b8' }}>Session Start:</span>
                      <span style={{ color: '#94a3b8' }}>
                        {formatTimestamp(member.started_at)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer Sync Indicator */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '10px',
                  color: '#64748b',
                  paddingTop: '2px'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ color: '#38bdf8' }}>⚡</span> Firebase & SQLite Synced
                  </span>
                  <span>{member.status || 'READY'}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── SECTION 3: COMPLETE CHRONOLOGICAL SESSIONS AUDIT LEDGER ─── */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.8)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '14px',
        padding: '20px 24px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)'
      }}>
        {/* Ledger Header & Advanced Filter Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '14px',
          marginBottom: '18px'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>📋</span>
              <h4 style={{ margin: 0, fontSize: '17px', fontWeight: '800', color: '#f8fafc' }}>
                Session Open & Close Audit Ledger ({filteredSessions.length} Records)
              </h4>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
              Full immutable trace of session start times, exit times, total duration, and exit activities.
            </p>
          </div>

          {/* Filter Controls */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            {/* Status Filter Toggle */}
            <div style={{
              display: 'flex',
              background: '#0f172a',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              overflow: 'hidden',
              padding: '2px'
            }}>
              {['ALL', 'ACTIVE', 'CLOSED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  style={{
                    padding: '6px 12px',
                    fontSize: '11px',
                    fontWeight: '700',
                    borderRadius: '6px',
                    border: 'none',
                    background: statusFilter === st ? '#1e293b' : 'transparent',
                    color: statusFilter === st ? (st === 'ACTIVE' ? '#4ade80' : '#38bdf8') : '#94a3b8',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {st === 'ALL' ? 'All' : (st === 'ACTIVE' ? '🟢 Active' : '⚪ Closed')}
                </button>
              ))}
            </div>

            {/* Operator Dropdown */}
            <select
              value={selectedUserFilter}
              onChange={(e) => setSelectedUserFilter(e.target.value)}
              style={{
                background: '#1e293b',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#fff',
                borderRadius: '8px',
                padding: '7px 12px',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="ALL">All Operators ({allAvailableOperators.length})</option>
              {allAvailableOperators.map((op) => (
                <option key={op.email} value={op.email}>
                  {getOptionIcon(op.avatar)} {op.name} ({op.email})
                </option>
              ))}
            </select>

            {/* Search Input with Clear Button */}
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Search tab, activity, or device..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                style={{
                  background: '#1e293b',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#fff',
                  borderRadius: '8px',
                  padding: '7px 28px 7px 12px',
                  fontSize: '12px',
                  minWidth: '220px',
                  outline: 'none'
                }}
              />
              {searchFilter && (
                <button
                  onClick={() => setSearchFilter('')}
                  style={{
                    position: 'absolute',
                    right: '8px',
                    background: 'none',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    fontSize: '12px',
                    padding: 0
                  }}
                >
                  ✕
                </button>
              )}
            </div>

            {/* CSV Export Button */}
            <button
              onClick={exportSessionsToCsv}
              disabled={filteredSessions.length === 0}
              title="Export filtered records to CSV"
              style={{
                padding: '7px 12px',
                borderRadius: '8px',
                background: 'rgba(56, 189, 248, 0.12)',
                border: '1px solid rgba(56, 189, 248, 0.35)',
                color: '#38bdf8',
                fontSize: '12px',
                fontWeight: '700',
                cursor: filteredSessions.length === 0 ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>📥</span> CSV
            </button>
          </div>
        </div>

        {/* Audit Table */}
        <div style={{
          overflowX: 'auto',
          borderRadius: '10px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          background: 'rgba(2, 6, 23, 0.6)'
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(30, 41, 59, 0.9)', color: '#94a3b8', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <th style={{ padding: '12px 16px', fontWeight: '800', letterSpacing: '0.03em' }}>Operator</th>
                <th style={{ padding: '12px 16px', fontWeight: '800', letterSpacing: '0.03em' }}>Status</th>
                <th style={{ padding: '12px 16px', fontWeight: '800', letterSpacing: '0.03em' }}>Session Opened</th>
                <th style={{ padding: '12px 16px', fontWeight: '800', letterSpacing: '0.03em' }}>Session Closed</th>
                <th style={{ padding: '12px 16px', fontWeight: '800', letterSpacing: '0.03em' }}>Time Spent</th>
                <th style={{ padding: '12px 16px', fontWeight: '800', letterSpacing: '0.03em' }}>Active Tab / Activity</th>
                <th style={{ padding: '12px 16px', fontWeight: '800', letterSpacing: '0.03em' }}>Device / Platform</th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ padding: '36px', textAlign: 'center', color: '#94a3b8' }}>
                    <div style={{ fontSize: '24px', marginBottom: '8px' }}>🔍</div>
                    <div style={{ fontWeight: '600', color: '#cbd5e1' }}>No sessions match the selected filters.</div>
                    <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                      Try selecting "All Operators" or clearing your search term.
                    </div>
                  </td>
                </tr>
              ) : (
                filteredSessions.map((sess) => {
                  const isOnline = Boolean(sess.is_online);
                  return (
                    <tr
                      key={sess.session_id}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                        background: isOnline ? 'rgba(34, 197, 94, 0.05)' : 'transparent',
                        transition: 'background 0.15s ease'
                      }}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <UserAvatar
                            avatar={sess.user_avatar}
                            name={sess.user_name}
                            size={32}
                            showBadge={false}
                          />
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: '700', color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {sess.user_name}
                            </div>
                            <div style={{ fontSize: '11px', color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {sess.user_email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          fontSize: '10px',
                          fontWeight: '800',
                          padding: '3px 9px',
                          borderRadius: '10px',
                          background: isOnline ? 'rgba(34, 197, 94, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                          color: isOnline ? '#4ade80' : '#cbd5e1',
                          border: isOnline ? '1px solid rgba(34, 197, 94, 0.4)' : '1px solid rgba(100, 116, 139, 0.3)'
                        }}>
                          {isOnline ? 'ACTIVE' : (sess.status || 'CLOSED')}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#cbd5e1', whiteSpace: 'nowrap' }}>
                        {formatTimestamp(sess.started_at)}
                      </td>
                      <td style={{ padding: '12px 16px', color: isOnline ? '#4ade80' : '#94a3b8', whiteSpace: 'nowrap' }}>
                        {isOnline ? '● Ongoing Session' : formatTimestamp(sess.ended_at || sess.last_heartbeat)}
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: '800', color: isOnline ? '#38bdf8' : '#fbbf24' }}>
                        {formatDuration(sess.duration_seconds)}
                      </td>
                      <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>
                        <div style={{ fontWeight: '700', color: '#38bdf8' }}>{sess.current_tab || 'System Root'}</div>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>{sess.activity_label || 'Interaction'}</div>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#94a3b8', fontSize: '11px' }}>
                        <span style={{
                          background: 'rgba(255, 255, 255, 0.05)',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          border: '1px solid rgba(255, 255, 255, 0.08)'
                        }}>
                          {sess.client_platform || 'Windows 11'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
