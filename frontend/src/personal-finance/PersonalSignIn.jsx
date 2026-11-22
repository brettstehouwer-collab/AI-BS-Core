import React, { useEffect, useState } from 'react';
import { getRedirectResult, signInWithPopup, signInWithRedirect } from 'firebase/auth';
import { auth, googleProvider } from '../firebase.js';

export default function PersonalSignIn() {
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  useEffect(() => {
    let current = true;
    getRedirectResult(auth).catch(e => { if (current) setError(e.message); });
    return () => { current = false; };
  }, []);
  const login = async () => {
    setBusy(true); setError('');
    try {
      if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) await signInWithRedirect(auth, googleProvider);
      else await signInWithPopup(auth, googleProvider);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  return <section><h2>Personal account sign-in</h2><button disabled={busy} onClick={login}>Continue with Google</button>{error && <p role="alert">{error}</p>}</section>;
}
