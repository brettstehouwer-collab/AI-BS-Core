import { useEffect, useRef } from 'react';
import { getApiBase } from '../config/api';
import { getFriendlyUserName, getFriendlyUserRole, getFriendlyUserAvatar } from '../components/collaborationService';

export function useUserSessionTelemetry({ currentUser, activeTab = 'dashboard' }) {
  const apiHost = getApiBase() || '';
  const sessionStartTimeRef = useRef(null);
  const sessionIdRef = useRef(null);

  // Initialize Session ID and Open Timestamp
  useEffect(() => {
    let sid = sessionStorage.getItem('aibs_session_id');
    let start = sessionStorage.getItem('aibs_session_start');
    if (!sid) {
      sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
      start = Date.now().toString();
      sessionStorage.setItem('aibs_session_id', sid);
      sessionStorage.setItem('aibs_session_start', start);
    }
    sessionIdRef.current = sid;
    sessionStartTimeRef.current = parseInt(start, 10) || Date.now();
  }, []);

  // Send Heartbeat & Close Handler
  useEffect(() => {
    const sendHeartbeat = async () => {
      const sid = sessionIdRef.current || sessionStorage.getItem('aibs_session_id');
      if (!sid) return;

      const startTime = sessionStartTimeRef.current || parseInt(sessionStorage.getItem('aibs_session_start'), 10) || Date.now();
      const dwellSec = Math.max(0, (Date.now() - startTime) / 1000.0);

      const email = (currentUser?.email || localStorage.getItem('aibs_user_email') || 'brettstehouwer@gmail.com').toLowerCase().trim();
      const name = currentUser?.displayName || getFriendlyUserName(email);
      const role = getFriendlyUserRole(email);
      const avatar = getFriendlyUserAvatar(email);

      const platform = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
        ? 'Mobile Device'
        : (navigator.userAgent.includes('Windows') ? 'Desktop Windows 11' : 'Desktop Browser');

      const payload = {
        session_id: sid,
        user_email: email,
        user_name: name,
        user_avatar: avatar,
        user_role: role,
        current_tab: activeTab || 'dashboard',
        activity_label: `Active in ${(activeTab || 'Dashboard').replace(/_/g, ' ').toUpperCase()}`,
        client_platform: platform,
        dwell_seconds: dwellSec
      };

      try {
        await fetch(`${apiHost}/api/telemetry/user-sessions/heartbeat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } catch (err) {
        // Silently ignore if offline
      }
    };

    // Initial heartbeat on tab change
    sendHeartbeat();

    // Periodic heartbeat every 15s
    const interval = setInterval(sendHeartbeat, 15000);

    // Unload / Close Handler
    const handleUnload = () => {
      const sid = sessionIdRef.current || sessionStorage.getItem('aibs_session_id');
      if (!sid) return;

      const startTime = sessionStartTimeRef.current || parseInt(sessionStorage.getItem('aibs_session_start'), 10) || Date.now();
      const dwellSec = Math.max(0, (Date.now() - startTime) / 1000.0);

      const payload = JSON.stringify({
        session_id: sid,
        exit_tab: activeTab || 'dashboard',
        duration_seconds: dwellSec
      });

      const closeUrl = `${apiHost}/api/telemetry/user-sessions/close`;
      if (navigator.sendBeacon) {
        navigator.sendBeacon(closeUrl, new Blob([payload], { type: 'application/json' }));
      } else {
        fetch(closeUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          keepalive: true
        }).catch(() => {});
      }
    };

    window.addEventListener('beforeunload', handleUnload);
    window.addEventListener('pagehide', handleUnload);

    return () => {
      clearInterval(interval);
      window.removeEventListener('beforeunload', handleUnload);
      window.removeEventListener('pagehide', handleUnload);
    };
  }, [apiHost, currentUser, activeTab]);
}
