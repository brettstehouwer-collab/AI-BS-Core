import { useCallback, useEffect, useRef, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '/src/firebase.js';
import { chatAuthHeaders } from '/src/utils/chatAuth.js';
import { createAccountingSession } from '/src/utils/accountingSession.js';

/** @param {{uid: string, children: (request: ReturnType<typeof import("/src/utils/accountingSession.js").createAccountingSession>["request"]) => import("react").ReactNode}} props */
function AccountSession({ uid, children }) {
  const currentSession = useRef(/** @type {ReturnType<typeof createAccountingSession> | null} */ (null));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const session = createAccountingSession({ uid, currentUid: () => auth.currentUser?.uid || '',
      getHeaders: () => chatAuthHeaders({}, uid) });
    currentSession.current = session; setReady(true);
    return () => { session.dispose(); if (currentSession.current === session) currentSession.current = null; };
  }, [uid]);
  const request = useCallback((/** @type {string} */ url, /** @type {RequestInit} */ options = {}) => {
    if (!currentSession.current) return Promise.reject(new Error('Accounting session is unavailable. Sign in again.'));
    return currentSession.current.request(url, options);
  }, []);
  return ready ? children(request) : <section role="status">Loading accounting access…</section>;
}

/** @param {{children: (request: ReturnType<typeof import("/src/utils/accountingSession.js").createAccountingSession>["request"]) => import("react").ReactNode}} props */
export default function FinancialAccountBoundary({ children }) {
  const [identity, setIdentity] = useState(/** @type {{uid: string, generation: number} | null} */ (null));
  const generation = useRef(0);
  useEffect(() => onAuthStateChanged(auth, user => setIdentity(user ? { uid: user.uid, generation: ++generation.current } : (generation.current++, null))), []);
  if (!identity || auth.currentUser?.uid !== identity.uid) return <section role="status" style={{ padding: 20, color: '#cbd5e1' }}>
    Sign in with an authorized accounting account. Manual records remain unreconciled; verified totals are Unavailable.
  </section>;
  return <AccountSession key={`${identity.uid}:${identity.generation}`} uid={identity.uid}>{children}</AccountSession>;
}
