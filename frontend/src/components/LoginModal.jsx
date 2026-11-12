import DevinPhoneLogin from './DevinPhoneLogin.jsx';
import { useState, useEffect, useRef } from 'react';
import { signInWithPopup, signInWithRedirect, getRedirectResult } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import { ADMIN_EMAILS, ADMIN_UIDS } from './accessControl.js';

const isAdmin = (/** @type {import("firebase/auth").User|null} */ user) => {
  const email = (user?.email || '').toLowerCase().trim();
  return Boolean(user && user.emailVerified && (
    ADMIN_EMAILS.includes(email) || ADMIN_UIDS.includes(user.uid)
  ));
};

const isLocalDesktop = () => typeof window !== 'undefined' && (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
);

const REDIRECT_INTENT_KEY = 'aibs_google_redirect_intent_v1';

/** @param {{onLoginSuccess: (user: any) => void, backendUrl: string}} props */
export default function LoginModal({ onLoginSuccess }) {
  const [errorMsg, setErrorMsg] = useState('');
  const [pendingMode, setPendingMode] = useState('');
  const isSubmitting = pendingMode !== '';
  const mounted = useRef(false);
  const attempt = useRef(0);
  const loginSuccess = useRef(onLoginSuccess);
  loginSuccess.current = onLoginSuccess;
  /** @param {number} id */
  const isCurrent = (id) => mounted.current && attempt.current === id;

  /** @param {import('firebase/auth').User} user @param {number} id */
  const acceptUser = async (user, id) => {
    if (!isCurrent(id)) return;
    if (!isAdmin(user)) {
      setErrorMsg('This verified account is not on the AI-BS administrator list.');
      await auth.signOut();
      return;
    }
    try {
      localStorage.setItem('aibs_cached_user', JSON.stringify({
        email: user.email, displayName: user.displayName,
        uid: user.uid, photoURL: user.photoURL
      }));
    } catch {}
    loginSuccess.current(user);
  };

  useEffect(() => {
    let cancelled = false;
    mounted.current = true;
    // StrictMode cleans up its first effect before this microtask. Only the
    // surviving effect may consume the one-shot intent or start navigation.
    Promise.resolve().then(async () => {
      if (cancelled) return;
      const id = attempt.current;
      try {
        if (sessionStorage.getItem(REDIRECT_INTENT_KEY) === 'google') {
          sessionStorage.removeItem(REDIRECT_INTENT_KEY);
          setPendingMode('redirect');
          await signInWithRedirect(auth, googleProvider);
          if (!cancelled && isCurrent(id)) {
            setErrorMsg('Google sign-in did not open. Continue in this tab to retry.');
          }
        } else {
          const result = await getRedirectResult(auth);
          if (!cancelled && isCurrent(id) && result?.user) await acceptUser(result.user, id);
        }
      } catch (err) {
        if (!cancelled && isCurrent(id)) setErrorMsg('Google sign-in failed: ' + errorMessage(err));
      } finally {
        if (!cancelled && isCurrent(id)) setPendingMode('');
      }
    });
    return () => {
      cancelled = true;
      mounted.current = false;
      attempt.current += 1;
    };
  }, []);

  const handleGoogleSignIn = async () => {
    const id = ++attempt.current;
    setErrorMsg('');
    setPendingMode('popup');

    try {
      const result = await signInWithPopup(auth, googleProvider);
      await acceptUser(result.user, id);
    } catch (err) {
      if (isCurrent(id)) setErrorMsg('Authentication failed: ' + errorMessage(err));
    } finally {
      if (isCurrent(id)) setPendingMode('');
    }
  };

  /** @param {boolean} continueInTab */
  const reloadSignIn = (continueInTab) => {
    try {
      if (continueInTab) sessionStorage.setItem(REDIRECT_INTENT_KEY, 'google');
      else sessionStorage.removeItem(REDIRECT_INTENT_KEY);
    } catch (err) {
      setErrorMsg('Sign-in recovery needs browser session storage: ' + errorMessage(err));
      return;
    }
    // Unload the pending popup context before starting a redirect. Ignoring
    // its component callback alone would not stop Firebase's auth listeners.
    attempt.current += 1;
    setErrorMsg('');
    setPendingMode('reload');
    try {
      window.location.reload();
    } catch (err) {
      setErrorMsg('Could not restart sign-in. Use Restart sign-in to retry: ' + errorMessage(err));
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal} className="glass-panel" aria-busy={isSubmitting}>
        <h2 style={{ color: '#fff', marginBottom: '10px' }}>Security Perimeter</h2>
        <p style={{ color: '#94a3b8', marginBottom: '30px', fontSize: '0.9rem' }}>
          This dashboard is locked. Authorized personnel only.
        </p>
        
        <button type="button" onClick={handleGoogleSignIn} style={styles.button} disabled={isSubmitting}>
          {isSubmitting ? 'Verifying...' : 'Sign in with Google'}
        </button>

        <button type="button" onClick={() => reloadSignIn(true)} style={styles.recoveryButton}>
          Continue sign-in in this tab
        </button>
        {isSubmitting && <>
          <p role="status" style={styles.status}>
            {pendingMode === 'popup' ? 'If no Google window appeared, continue sign-in in this tab.' : 'Opening Google sign-in in this tab…'}
          </p>
          <button type="button" onClick={() => reloadSignIn(false)} style={styles.recoveryButton}>
            Restart sign-in
          </button>
        </>}

        <fieldset disabled={isSubmitting} style={styles.alternatives}>
        <DevinPhoneLogin onLoginSuccess={onLoginSuccess} />


        <div style={{ margin: '15px 0', color: '#64748b', fontSize: '0.8rem' }}>— OR —</div>

        {isLocalDesktop() && <button 
          onClick={() => {
            const localUser = { email: 'brett@stehouwerproductions.com', displayName: 'Brett Stehouwer (Desktop Admin)', uid: 'local_admin_brett' };
            try {
              localStorage.setItem('aibs_cached_user', JSON.stringify(localUser));
            } catch {}
            onLoginSuccess(localUser);
          }} 
          style={styles.localButton}
        >
          ⚡ Local Desktop Access
        </button>}
        </fieldset>
        
        {errorMsg && <p role="alert" style={styles.error}>{errorMsg}</p>}
      </div>
    </div>
  );
}

/** @type {Record<string,import("react").CSSProperties>} */
const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 9999,
  },
  modal: {
    padding: '40px',
    borderRadius: '16px',
    width: '350px',
    maxWidth: 'calc(100vw - 32px)',
    maxHeight: '90vh',
    overflowY: 'auto',
    textAlign: 'center',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(15, 23, 42, 0.95)',
    boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
    backdropFilter: 'blur(16px)',
  },
  button: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    backgroundColor: '#fff',
    color: '#000',
    fontWeight: 'bold',
    cursor: 'pointer',
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    fontSize: '1rem',
    transition: 'all 0.2s',
  },
  localButton: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: '1px solid rgba(59, 130, 246, 0.4)',
    backgroundColor: '#1e293b',
    color: '#60a5fa',
    fontWeight: 'bold',
    cursor: 'pointer',
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    fontSize: '0.95rem',
    transition: 'all 0.2s',
  },
  recoveryButton: {
    marginTop: '12px', padding: '10px', width: '100%', borderRadius: '8px',
    border: '1px solid #64748b', background: 'transparent', color: '#e2e8f0', cursor: 'pointer',
  },
  status: { color: '#cbd5e1', fontSize: '0.85rem', margin: '12px 0 0' },
  alternatives: { border: 0, padding: 0, margin: 0, minWidth: 0 },
  error: {
    marginTop: '20px',
    color: '#ff4444',
    fontSize: '0.9rem',
    background: 'rgba(255, 0, 0, 0.1)',
    padding: '10px',
    borderRadius: '8px',
  }
};

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
