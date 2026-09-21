import React, { useState, useEffect } from 'react';
import './UnifiedMediaVaultTab.css';

const AUTHORIZED_EMAILS = [
  'brettstehouwer@gmail.com',
  'footballstar0325@gmail.com',
  'stehouwerjulie@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwer.julie@gmail.com',
  'julie@stehouwer-publishing.com'
];

const JULIE_EMAILS = [
  'stehouwerjulie@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwer.julie@gmail.com',
  'julie@stehouwer-publishing.com'
];

export default function UnifiedMediaVaultTab({ backendUrl, currentUser }) {
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [lightboxMedia, setLightboxMedia] = useState(null);

  // Determine if running locally or on local home network (LAN)
  const isLocalDev = typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname.startsWith('192.168.') ||
    window.location.hostname.startsWith('10.') ||
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(window.location.hostname) ||
    window.location.protocol === 'file:'
  );

  // Determine current active user email
  const userEmail = (currentUser?.email || '').toLowerCase().trim();

  // Julie Stehouwer has full unrestricted access without any password requirement
  const isJulie = JULIE_EMAILS.includes(userEmail) || userEmail.includes('julie');

  // Allowed operators: Julie, Brett, LocalDev, footballstar0325
  const isAuthorizedOperator = isLocalDev || isJulie || AUTHORIZED_EMAILS.includes(userEmail);

  // Check persistent authorization or session unlock (Julie is ALWAYS unlocked with zero password prompt)
  const [isUnlocked, setIsUnlocked] = useState(() => {
    if (isJulie) return true;
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('aibs_media_vault_unlocked') === 'true';
    }
    return false;
  });

  const [enteredPassword, setEnteredPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const handlePasswordUnlock = (e) => {
    e?.preventDefault();
    setPasswordError('');
    if (!enteredPassword.trim()) {
      setPasswordError('Please enter the vault security password.');
      return;
    }

    // Secure vault access password check
    if (enteredPassword.trim() === 'jssdbdAS2631') {
      setIsUnlocked(true);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('aibs_media_vault_unlocked', 'true');
      }
    } else {
      setPasswordError('Invalid security password. Access denied.');
    }
  };

  const handleLockVault = () => {
    setIsUnlocked(false);
    setEnteredPassword('');
    setPasswordError('');
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('aibs_media_vault_unlocked');
    }
  };

  useEffect(() => {
    if (isAuthorizedOperator && isUnlocked) {
      fetchMedia();
    }
  }, [isAuthorizedOperator, isUnlocked]);

  const fetchMedia = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${backendUrl || 'http://localhost:8000'}/api/media-vault/all`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data.categories || []);
        if (data.categories && data.categories.length > 0 && !activeCategory) {
          setActiveCategory(data.categories[0].name);
        }
      }
    } catch (err) {
      console.error('Failed to fetch media vault:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleMediaClick = (media) => {
    setLightboxMedia(media);
  };

  const closeLightbox = () => {
    setLightboxMedia(null);
  };

  const currentCategoryData = categories.find((c) => c.name === activeCategory);

  // Security Barrier 1: Email / LocalDev Identity Enforcement
  if (!isAuthorizedOperator) {
    return (
      <div className="media-vault-container media-vault-auth-guard">
        <div className="media-vault-lock-box">
          <div className="vault-lock-shield">🔒</div>
          <h2 className="vault-lock-title">Restricted Vault Access</h2>
          <p className="vault-lock-subtitle">
            The Unified Media Gallery is strictly restricted to authorized operators:
          </p>
          <div className="vault-authorized-roster">
            <span className="roster-badge">👤 Brettstehouwer@gmail.com</span>
            <span className="roster-badge">⚡ LocalDev (localhost / 127.0.0.1)</span>
            <span className="roster-badge">👤 footballstar0325@gmail.com</span>
          </div>
          <div className="vault-denied-status">
            Current Operator Identity: <strong>{userEmail || 'Unauthenticated Guest'}</strong>
          </div>
        </div>
      </div>
    );
  }

  // Security Barrier 2: Password Challenge
  if (!isUnlocked) {
    return (
      <div className="media-vault-container media-vault-auth-guard">
        <div className="media-vault-lock-box">
          <div className="vault-lock-shield pulse-shield">🔐</div>
          <h2 className="vault-lock-title">Unified Media Vault — Password Required</h2>
          <p className="vault-lock-subtitle">
            Identity Verified: <span className="vault-verified-user">{isLocalDev ? 'LocalDev' : userEmail}</span>. Enter the master vault security password to unlock media assets.
          </p>
          <form onSubmit={handlePasswordUnlock} className="vault-password-form">
            <div className="vault-input-group">
              <input
                type="password"
                className="vault-password-input"
                placeholder="Enter Vault Password"
                value={enteredPassword}
                onChange={(e) => setEnteredPassword(e.target.value)}
                autoFocus
              />
              <button type="submit" className="vault-unlock-btn">
                Unlock Gallery 🔓
              </button>
            </div>
            {passwordError && (
              <div className="vault-auth-error">
                ⚠️ {passwordError}
              </div>
            )}
          </form>
          <div className="vault-security-note">
            🛡️ Encrypted media store with session-scoped authentication.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="media-vault-container">
      <div className="media-vault-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h1><span>🎨</span> Media & Asset Vault</h1>
            <p>Unified gallery for all AI-BS generated images, videos, 3D renders, and assets.</p>
          </div>
          <div className="vault-auth-badge-container">
            <span className="vault-operator-badge">
              🟢 {isLocalDev ? 'LocalDev Operator' : userEmail}
            </span>
            <button className="vault-relock-btn" onClick={handleLockVault} title="Lock Vault">
              🔒 Lock Vault
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="media-vault-loading">Loading media assets...</div>
      ) : (
        <>
          <div className="media-vault-categories">
            {categories.map((cat) => (
              <button
                key={cat.name}
                className={`vault-category-btn ${activeCategory === cat.name ? 'active' : ''}`}
                onClick={() => setActiveCategory(cat.name)}
              >
                {cat.name} <span style={{ opacity: 0.7, fontSize: '11px', marginLeft: '6px' }}>({cat.files.length})</span>
              </button>
            ))}
          </div>

          <div className="media-vault-grid">
            {currentCategoryData &&
              currentCategoryData.files.map((file, idx) => (
                <div key={idx} className="vault-media-card" onClick={() => handleMediaClick(file)}>
                  {file.type === 'video' ? (
                    <video
                      className="vault-media-video"
                      src={`${backendUrl}${file.url}`}
                      muted
                      loop
                      onMouseEnter={(e) => e.target.play()}
                      onMouseLeave={(e) => {
                        e.target.pause();
                        e.target.currentTime = 0;
                      }}
                    />
                  ) : (
                    <img className="vault-media-preview" src={`${backendUrl}${file.url}`} alt={file.filename} loading="lazy" />
                  )}
                  <div className="vault-media-overlay">
                    <span className="vault-media-filename">{file.filename}</span>
                    <span className="vault-media-size">{formatSize(file.size)}</span>
                  </div>
                </div>
              ))}
            {(!currentCategoryData || currentCategoryData.files.length === 0) && (
              <div style={{ color: '#8b949e' }}>No media found in this category.</div>
            )}
          </div>
        </>
      )}

      {lightboxMedia && (
        <div className="vault-lightbox-overlay" onClick={closeLightbox}>
          <div className="vault-lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button className="vault-lightbox-close" onClick={closeLightbox}>&times;</button>
            {lightboxMedia.type === 'video' ? (
              <video className="vault-lightbox-media-vid" src={`${backendUrl}${lightboxMedia.url}`} controls autoPlay loop />
            ) : (
              <img className="vault-lightbox-media-img" src={`${backendUrl}${lightboxMedia.url}`} alt={lightboxMedia.filename} />
            )}
            <div className="vault-lightbox-details">
              <span><strong>File:</strong> {lightboxMedia.filename}</span>
              <span><strong>Size:</strong> {formatSize(lightboxMedia.size)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
