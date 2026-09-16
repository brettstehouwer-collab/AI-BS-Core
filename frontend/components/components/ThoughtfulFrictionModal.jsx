import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';

const ADMIN_EMAILS = [
  'theseandaley@gmail.com',
  'brettstehouwer@gmail.com',
  'footballstar0325@gmail.com',
  'footballsyat0325@gmail.com',
  'stehouwer@gmail.com',
  'rottierannajoy@gmail.com',
  'keith@evolution6media.com'
];

export default function ThoughtfulFrictionModal({ currentUser }) {
  const [frictionPayload, setFrictionPayload] = useState(null);
  const [socket, setSocket] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if current user is an Admin
  const isAdmin = currentUser && currentUser.email && ADMIN_EMAILS.includes(currentUser.email.toLowerCase());

  useEffect(() => {
    // Setup WebSocket connection (DISABLED FOR NOW to prevent 502/context canceled errors in Cloudflared logs)
    // Convert http(s):// to ws(s)://
    // let wsUrl = getApiBase().replace(/^http/, 'ws') + '/api/ws';
    // const ws = new WebSocket(wsUrl);

    // ws.onopen = () => console.log('[Friction Socket] Connected');
    
    // ws.onmessage = (event) => {
    //   try {
    //     const data = JSON.parse(event.data);
    //     if (data.type === 'FRICTION_REQUIRED') {
    //       setFrictionPayload(data);
    //     }
    //   } catch (err) {
    //     console.error('Failed to parse WebSocket message', err);
    //   }
    // };

    // ws.onclose = () => console.log('[Friction Socket] Disconnected');
    // setSocket(ws);

    // return () => {
    //   ws.close();
    // };
  }, []);

  const [password, setPassword] = useState('');
  
  const handleResolve = async (approved) => {
    if (!frictionPayload) return;
    
    // Admin password check for destructive actions
    if (approved && (frictionPayload.action === 'MEMORY_WIPE' || frictionPayload.action === 'CACHE_CLEAR')) {
      if (!isAdmin && password !== 'admin69420') {
        alert('Invalid Admin Password');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      await fetch(`${getApiBase()}/api/friction/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          friction_id: frictionPayload.friction_id,
          approved
        })
      });
      // Clear payload to close modal
      setFrictionPayload(null);
      setPassword('');
    } catch (err) {
      console.error('Failed to resolve friction', err);
      alert('Error communicating with backend. Check console.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!frictionPayload) return null;

  const requiresPassword = frictionPayload.action === 'MEMORY_WIPE' || frictionPayload.action === 'CACHE_CLEAR';

  return (
    <div className="friction-modal-overlay">
      <div className="friction-modal">
        <div className="friction-modal-header">
          <h3>THOUGHTFUL FRICTION: SYSTEM PAUSED</h3>
          <span className="pulse-indicator"></span>
        </div>
        <div className="friction-modal-body">
          <p>
            The orchestrator has requested execution for high-stakes action:{' '}
            <strong>{frictionPayload.action}</strong>
          </p>
          <div className="diagnostic-trace">
            <h4>Diagnostic Trace:</h4>
            <pre>{frictionPayload.diagnostic_trace}</pre>
          </div>
          <p className="warning-text">Review parameters before proceeding. Do you authorize this execution?</p>
          
          {requiresPassword && !isAdmin && (
            <div style={{ marginTop: '15px', background: '#222', padding: '10px', borderRadius: '4px', borderLeft: '3px solid #ff4444' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#ffaaaa' }}>
                Admin Authorization Required for Destructive Action:
              </label>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter Admin Password"
                style={{ width: '100%', padding: '8px', background: '#111', color: 'white', border: '1px solid #444', borderRadius: '4px' }}
              />
            </div>
          )}
          {requiresPassword && isAdmin && (
            <div style={{ marginTop: '15px', background: 'rgba(74, 222, 128, 0.1)', padding: '10px', borderRadius: '4px', borderLeft: '3px solid #4ade80' }}>
              <span style={{ fontSize: '0.85rem', color: '#4ade80', fontWeight: 'bold' }}>✓ Admin Bypass Active</span>
              <p style={{ margin: '5px 0 0 0', fontSize: '0.8rem', color: '#aaa' }}>Your identity verifies you as an Admin. You may authorize this destructive action without a password.</p>
            </div>
          )}
        </div>
        <div className="friction-modal-footer">
          <button 
            className="btn-abort" 
            onClick={() => handleResolve(false)}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Sending...' : 'Abort'}
          </button>
          <button 
            className="btn-approve" 
            onClick={() => handleResolve(true)}
            disabled={isSubmitting || (requiresPassword && !isAdmin && !password)}
          >
            {isSubmitting ? 'Sending...' : 'Approve Execution'}
          </button>
        </div>
      </div>
    </div>
  );
}
