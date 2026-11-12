import { useEffect, useRef, useState } from 'react';
import { RecaptchaVerifier, signInWithPhoneNumber } from 'firebase/auth';
import { auth } from '/firebase.js';

// This method belongs to the existing, operator-approved FE Express account.
const DEVIN_PHONE = '+16163157483';
const DEVIN_EMAIL = 'devin.feexpress@gmail.com';

/** @param {{onLoginSuccess: (user: import('firebase/auth').User) => void}} props */
export default function DevinPhoneLogin({ onLoginSuccess }) {
  /** @type {import('react').MutableRefObject<HTMLDivElement | null>} */
  const container = useRef(null);
  /** @type {import('react').MutableRefObject<RecaptchaVerifier | null>} */
  const verifier = useRef(null);
  /** @type {import('react').MutableRefObject<import('firebase/auth').ConfirmationResult | null>} */
  const confirmation = useRef(null);
  const mounted = useRef(true);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      confirmation.current = null;
      verifier.current?.clear();
      verifier.current = null;
    };
  }, []);
  const send = async () => {
    if (busy || confirmation.current) return;
    setBusy(true); setError('');
    try {
      if (!container.current) throw new Error('Verification control unavailable');
      verifier.current?.clear();
      verifier.current = new RecaptchaVerifier(auth, container.current, { size: 'normal' });
      const result = await signInWithPhoneNumber(auth, DEVIN_PHONE, verifier.current);
      if (mounted.current) { confirmation.current = result; setSent(true); }
    } catch (err) {
      verifier.current?.clear(); verifier.current = null;
      if (mounted.current) setError(errorCode(err) === 'auth/too-many-requests'
        ? 'Too many requests. Wait before trying again, or use Google sign-in.'
        : 'The verification text could not be sent. Use Google sign-in or try again later.');
    } finally { if (mounted.current) setBusy(false); }
  };
  /** @param {import('react').FormEvent} event */
  const verify = async (event) => {
    event.preventDefault();
    if (busy || !confirmation.current || !/^\d{6}$/.test(code)) return;
    setBusy(true); setError('');
    try {
      const result = await confirmation.current.confirm(code);
      const user = result.user;
      if (!user.emailVerified || (user.email || '').trim().toLowerCase() !== DEVIN_EMAIL || user.phoneNumber !== DEVIN_PHONE) {
        await auth.signOut();
        confirmation.current = null;
        if (mounted.current) { setSent(false); setCode(''); setError('This phone is not connected to the approved FE Express account. Use Google sign-in.'); }
        return;
      }
      confirmation.current = null;
      if (mounted.current) onLoginSuccess(user);
    } catch (err) {
      if (mounted.current) {
        setError(errorCode(err) === 'auth/code-expired'
          ? 'The code expired. Request a new text.' : 'The code was not accepted. Check it and try again.');
        if (errorCode(err) === 'auth/code-expired') { confirmation.current = null; setSent(false); setCode(''); }
      }
    } finally { if (mounted.current) setBusy(false); }
  };
  return <section aria-label="Devin phone login" style={{ marginTop: 20, color: '#cbd5e1' }}>
    <p>Devin: sign in by text to the number ending in 7483.</p>
    <p style={{ fontSize: '0.75rem' }}>Requesting a code sends an SMS. Message rates may apply. Google processes the number for spam and abuse prevention.</p>
    <div ref={container} />
    {!sent ? <button type="button" disabled={busy} onClick={send}>{busy ? 'Requesting code…' : 'Text Devin a login code'}</button>
      : <form onSubmit={verify}>
        <label>Verification code <input aria-label="Verification code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e => setCode(e.target.value.replace(/\D/g, ''))} disabled={busy} /></label>
        <button type="submit" disabled={busy || !/^\d{6}$/.test(code)}>{busy ? 'Verifying…' : 'Verify and sign in'}</button>
      </form>}
    {error && <p role="alert" style={{ color: '#fca5a5' }}>{error}</p>}
  </section>;
}

/** @param {unknown} error */
function errorCode(error) {
  return error && typeof error === 'object' && 'code' in error ? error.code : '';
}
