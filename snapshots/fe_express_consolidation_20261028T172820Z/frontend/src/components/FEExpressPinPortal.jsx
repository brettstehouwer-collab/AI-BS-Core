import {useCallback, useEffect, useRef, useState} from 'react';
import FEExpressDispatcher from '/src/components/FEExpressDispatcher.jsx';
import WebsitePhoneLogin from './WebsitePhoneLogin.jsx';

/** @typedef {{token: string, expiresAt: number, base: string}} PortalSession */
/** @param {{backendUrl: string, onExit: () => void}} props */
export default function FEExpressPinPortal({backendUrl, onExit}) {
  const [session, setSession] = useState(/** @type {PortalSession | null} */ (null));
  const currentSession = useRef(/** @type {PortalSession | null} */ (null));
  const [error, setError] = useState('');
  const base = backendUrl.replace(/\/$/, '');
  const activeSession = session?.base === base ? session : null;
  const lock = useCallback(/** @param {PortalSession | undefined} expected */ (expected) => {
    if (expected && currentSession.current !== expected) return false;
    currentSession.current = null; setSession(null); return true;
  }, []);

  useEffect(() => {
    if (!activeSession) return;
    const timer = setTimeout(() => lock(activeSession), Math.max(0, activeSession.expiresAt - Date.now()));
    return () => clearTimeout(timer);
  }, [activeSession, lock]);
  useEffect(() => { if (currentSession.current?.base !== base) lock(undefined); }, [base, lock]);

  // Retain the existing phone + PIN API. Its token grants FE access, never main login.
  const portalFetch = useCallback(/** @param {RequestInfo | URL} input @param {RequestInit} options */ async (input, options = {}) => {
    const url = new URL(input instanceof Request ? input.url : String(input), window.location.origin);
    const api = new URL(base, window.location.origin);
    const sessionEndpoint = ['/api/website-access/session', '/api/website-access/logout'].includes(url.pathname);
    if (url.origin !== api.origin || (!url.pathname.startsWith('/api/v1/fe-express/') && !sessionEndpoint)) {
      throw new Error('This session only opens FE Express.');
    }
    if (!activeSession || currentSession.current !== activeSession || activeSession.expiresAt <= Date.now()) {
      if (activeSession) lock(activeSession);
      throw new Error('Enter your phone number and PIN again.');
    }
    const headers = new Headers(options.headers);
    headers.set('Authorization', `Bearer ${activeSession.token}`);
    const response = await fetch(input, {...options, headers, redirect:'error'});
    if (response.status === 401 && lock(activeSession)) setError('Your session ended. Enter your phone number and PIN again.');
    return response;
  }, [base, activeSession, lock]);

  useEffect(() => {
    if (!activeSession) return;
    const check = () => portalFetch(`${base}/api/website-access/session`, {cache:'no-store',signal:AbortSignal.timeout(10000)}).catch(() => {});
    check();
    const timer = setInterval(check, 60000);
    return () => clearInterval(timer);
  }, [base, activeSession, portalFetch]);

  /** @param {boolean} exit */
  async function closePortal(exit) {
    const closing = currentSession.current;
    lock(undefined); setError('');
    if (exit) onExit();
    try {
      if (closing?.base === base) await fetch(`${base}/api/website-access/logout`, {
        method:'POST',headers:{Authorization:`Bearer ${closing.token}`},signal:AbortSignal.timeout(5000),redirect:'error'
      });
    } catch { /* Clear the local session even if its server is unavailable. */ }
  }

  if (activeSession) return <main style={{height:'100dvh',width:'100%',overflowY:'auto',overflowX:'hidden',boxSizing:'border-box',background:'#07101e',color:'#f8fafc'}}>
    <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,flexWrap:'wrap',padding:16}}>
      <strong>Devin · FE Express</strong>
      <div style={{display:'flex',gap:12,flexWrap:'wrap'}}>
        <button type="button" onClick={() => closePortal(true)}>Back to AI-BS / administrator sign-in</button>
        <button type="button" onClick={() => closePortal(false)}>Lock portal</button>
      </div>
    </header>
    <FEExpressDispatcher BACKEND_URL={base} request={portalFetch} />
  </main>;

  return <main style={{height:'100dvh',width:'100%',overflowY:'auto',overflowX:'hidden',boxSizing:'border-box',display:'grid',placeItems:'center',background:'#07101e',color:'#f8fafc',padding:20,fontFamily:'system-ui'}}>
    <section style={{width:'100%',maxWidth:400,display:'grid',gap:14,padding:24,background:'#101b2c',borderRadius:16,boxSizing:'border-box'}}>
      <h1 style={{margin:0,fontSize:26}}>Devin’s FE Express</h1>
      <p style={{margin:0,color:'#94a3b8'}}>Use your existing phone number and PIN for the FE Express workspace.</p>
      <WebsitePhoneLogin backendUrl={base} onLogin={nextSession => {
        const admitted = {...nextSession,base};
        currentSession.current = admitted; setError(''); setSession(admitted);
      }} />
      {error && <p role="alert" style={{margin:0,color:'#fda4af'}}>{error}</p>}
      <button type="button" onClick={() => closePortal(true)}>Back to AI-BS / administrator sign-in</button>
    </section>
  </main>;
}
