import {useEffect, useRef, useState} from 'react';

/** @param {{backendUrl: string, onLogin: (session: {token: string, expiresAt: number}) => void}} props */
export default function WebsitePhoneLogin({backendUrl, onLogin}) {
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef(/** @type {{generation: number, controller: AbortController | null}} */ ({generation:0, controller:null}));
  useEffect(() => {
    setBusy(false); setError(''); setPin('');
    return () => {
      pending.current.generation += 1;
      pending.current.controller?.abort();
      pending.current.controller = null;
    };
  }, [backendUrl]);
  /** @param {import('react').FormEvent} event */
  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    const generation = ++pending.current.generation;
    const controller = new AbortController();
    pending.current.controller = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`${backendUrl.replace(/\/$/, '')}/api/website-access/login`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({phone, pin}), cache: 'no-store', signal: controller.signal, redirect:'error'
      });
      const data = await response.json();
      if (pending.current.generation !== generation) return;
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to sign in.');
      if (data.scope !== 'website_pages' || typeof data.access_token !== 'string' || !Number.isFinite(data.expires_in) || data.expires_in <= 0) throw new Error('Invalid sign-in response.');
      setPin(''); setPhone('');
      onLogin({token: data.access_token, expiresAt: Date.now() + data.expires_in * 1000});
    } catch (err) {
      if (pending.current.generation === generation) setError(err instanceof Error && !['TimeoutError','AbortError'].includes(err.name) ? err.message : 'Connection unavailable. Try again.');
    } finally {
      clearTimeout(timeout);
      if (pending.current.generation === generation) { pending.current.controller = null; setBusy(false); }
    }
  }
  return <form onSubmit={submit} style={{display:'grid',gap:10,marginTop:24,textAlign:'left'}}>
    <h3 style={{margin:0,color:'#fff'}}>Phone number + PIN</h3>
    <p style={{margin:0,color:'#94a3b8',fontSize:13}}>No text message needed. This sign-in opens FE Express only.</p>
    <label htmlFor="website-phone" style={{color:'#fff'}}>Phone number</label>
    <input id="website-phone" type="tel" autoComplete="tel" required maxLength={32} value={phone} onChange={event=>setPhone(event.target.value)} style={{padding:12,minWidth:0}} />
    <label htmlFor="website-pin" style={{color:'#fff'}}>Four-digit PIN</label>
    <input id="website-pin" type="password" inputMode="numeric" autoComplete="off" required pattern="[0-9]{4}" maxLength={4} value={pin} onChange={event=>setPin(event.target.value.replace(/\D/g,'').slice(0,4))} style={{padding:12,minWidth:0}} />
    <button type="submit" disabled={busy || pin.length !== 4 || !phone.trim()} style={{padding:13,cursor:'pointer'}}>{busy ? 'Signing in…' : 'Sign in with phone + PIN'}</button>
    {error && <p role="alert" style={{color:'#fda4af',margin:0}}>{error}</p>}
  </form>;
}
