import React, { useState, useEffect } from 'react';
import { signInWithPopup, signInWithRedirect, getRedirectResult } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

const AUTHORIZED_EMAILS = [
  'theseandaley@gmail.com',
  'stehouwerjulie@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwer.julie@gmail.com',
  'brettstehouwer@gmail.com',
  'footballstar0325@gmail.com',
  'rottierannajoy@gmail.com'
];

export default function LoginModal({ onLoginSuccess }) {
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check for redirect result on mount (for mobile and redirect sign-in flows)
  useEffect(() => {
    getRedirectResult(auth)
      .then((result) => {
        if (result && result.user) {
          const user = result.user;
          if (AUTHORIZED_EMAILS.includes((user.email || '').toLowerCase())) {
            try {
              localStorage.setItem('aibs_cached_user', JSON.stringify({
                email: user.email,
                displayName: user.displayName,
                uid: user.uid,
                photoURL: user.photoURL
              }));
            } catch {}
            onLoginSuccess(user);
          } else {
            setErrorMsg(`Unauthorized Email (${user.email}). Access restricted.`);
            auth.signOut();
          }
        }
      })
      .catch((err) => {
        console.warn('Redirect sign-in check failed:', err);
      });
  }, [onLoginSuccess]);

  const handleGoogleSignIn = async () => {
    setErrorMsg('');
    setIsSubmitting(true);

    try {
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;

      if (AUTHORIZED_EMAILS.includes(user.email.toLowerCase())) {
        try {
          localStorage.setItem('aibs_cached_user', JSON.stringify({
            email: user.email,
            displayName: user.displayName,
            uid: user.uid,
            photoURL: user.photoURL
          }));
        } catch {}
        onLoginSuccess(user);
      } else {
        setErrorMsg(`Unauthorized Email (${user.email}). Access restricted.`);
        await auth.signOut();
      }
    } catch (err) {
      console.warn('Popup login failed or blocked, attempting mobile redirect...', err);
      if (err.code === 'auth/popup-blocked' || err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
        try {
          await signInWithRedirect(auth, googleProvider);
          return;
        } catch (redirectErr) {
          setErrorMsg('Mobile sign-in failed: ' + redirectErr.message);
        }
      } else {
        setErrorMsg('Authentication failed: ' + err.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRedirectSignIn = async () => {
    setErrorMsg('');
    setIsSubmitting(true);
    try {
      await signInWithRedirect(auth, googleProvider);
    } catch (err) {
      setErrorMsg('Redirect sign-in failed: ' + err.message);
      setIsSubmitting(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal} className="glass-panel">
        <h2 style={{ color: '#fff', marginBottom: '10px' }}>Security Perimeter</h2>
        <p style={{ color: '#94a3b8', marginBottom: '30px', fontSize: '0.9rem' }}>
          This dashboard is locked. Authorized personnel only.
        </p>
        
        <button onClick={handleGoogleSignIn} style={styles.button} disabled={isSubmitting}>
          {isSubmitting ? 'Verifying...' : 'Sign in with Google'}
        </button>

        <div style={{ margin: '15px 0', color: '#64748b', fontSize: '0.8rem' }}>— OR —</div>

        <button 
          onClick={() => onLoginSuccess({ email: 'brettstehouwer@gmail.com', displayName: 'Brett Stehouwer (Desktop Admin)', uid: 'local_admin_brett' })} 
          style={styles.localButton}
        >
          ⚡ Local Desktop Access
        </button>
        
        {errorMsg && <p style={styles.error}>{errorMsg}</p>}
      </div>
    </div>
  );
}

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
  error: {
    marginTop: '20px',
    color: '#ff4444',
    fontSize: '0.9rem',
    background: 'rgba(255, 0, 0, 0.1)',
    padding: '10px',
    borderRadius: '8px',
  }
};
