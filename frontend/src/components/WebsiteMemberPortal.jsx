import {Suspense, useCallback, useEffect} from 'react';
import FEExpressDispatcher from '/src/components/FEExpressDispatcher.jsx';

// Reviewed self-contained readers only. Other workspaces retain their existing administrator login.
const READERS = new Set(['bible_hub', 'nutrition_subsystem']);

/** @param {{backendUrl: string, session: {token: string, expiresAt: number}, tabs: any[], activeTab: string, onTabChange: (key: string) => void, onLock: () => void}} props */
export default function WebsiteMemberPortal({backendUrl, session, tabs, activeTab, onTabChange, onLock}) {
  const base = backendUrl.replace(/\/$/, '');
  useEffect(() => {
    const timer = setTimeout(onLock, Math.max(0, session.expiresAt - Date.now()));
    return () => clearTimeout(timer);
  }, [session.expiresAt, onLock]);
  /** @type {(input: RequestInfo | URL, options?: RequestInit) => Promise<Response>} */
  const request = useCallback(async (input, options = {}) => {
    const url = new URL(input instanceof Request ? input.url : String(input), window.location.origin);
    const api = new URL(base, window.location.origin);
    if (url.origin !== api.origin || !(url.pathname.startsWith('/api/v1/fe-express/') || url.pathname === '/api/website-access/session' || url.pathname === '/api/website-access/logout')) throw new Error('This sign-in cannot authorize that action.');
    if (session.expiresAt <= Date.now()) { onLock(); throw new Error('Sign in again.'); }
    const headers = new Headers(input instanceof Request ? input.headers : undefined);
    new Headers(options.headers).forEach((value, key)=>headers.set(key,value));
    headers.set('Authorization', `Bearer ${session.token}`);
    const response = await fetch(input, {...options, headers});
    if (response.status === 401) onLock();
    return response;
  }, [base, session, onLock]);
  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const response = await request(`${base}/api/website-access/session`, {cache:'no-store',signal:AbortSignal.timeout(10000)});
        if (active && !response.ok) onLock();
      } catch { if (active) onLock(); }
    };
    check(); const timer=setInterval(check,60000);
    return () => { active=false; clearInterval(timer); };
  }, [base, request, onLock]);
  const tab = tabs.find(item=>item.key===activeTab);
  const Reader = tab?.Component;
  return <main style={{background:'#07101e',color:'#f8fafc',height:'100dvh',width:'100%',overflowY:'auto',overflowX:'hidden',boxSizing:'border-box',fontFamily:'system-ui',padding:16}}>
    <header style={{display:'flex',gap:12,justifyContent:'space-between',alignItems:'center',flexWrap:'wrap'}}>
      <h1 style={{fontSize:24}}>AI-BS · Website access</h1>
      <button onClick={async()=>{try {await request(`${base}/api/website-access/logout`,{method:'POST',signal:AbortSignal.timeout(5000)});} catch { /* The local lock still applies when offline. */ } finally {onLock();}}}>Lock website</button>
    </header>
    <p>Signed in with phone number + PIN. Administrator workspaces require your Google sign-in.</p>
    <label htmlFor="website-page">Choose a website page</label>{' '}
    <select id="website-page" value={activeTab} onChange={event=>onTabChange(event.target.value)} style={{padding:12,maxWidth:'100%',marginBottom:18}}>
      <option value="website_home">Website home</option>
      {tabs.map(item=><option key={item.key} value={item.key}>{item.label}{!READERS.has(item.key) && item.key!=='fe_express' ? ' · Administrator sign-in' : ''}</option>)}
    </select>
    <section>
      {activeTab==='website_home' ? <><h2>Welcome to AI-BS</h2><p>Choose a page above, or open your FE Express workspace.</p><button onClick={()=>onTabChange('fe_express')}>Open FE Express</button></>
       : activeTab==='fe_express' ? <FEExpressDispatcher BACKEND_URL={base} request={request}/>
       : READERS.has(activeTab) && Reader ? <Suspense fallback={<p>Loading page…</p>}><Reader backendUrl={base}/></Suspense>
       : <><h2>{tab?.label || 'Protected workspace'}</h2><p>This workspace includes protected data or actions. Sign in with an administrator account to continue.</p><button onClick={onLock}>Use administrator sign-in</button></>}
    </section>
  </main>;
}
