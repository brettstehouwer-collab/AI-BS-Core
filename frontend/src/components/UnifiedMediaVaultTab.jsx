import { useState, useEffect } from "react";
import './UnifiedMediaVaultTab.css';

const AUTHORIZED_EMAILS = [
  'brett@stehouwerproductions.com',
  'brett@stehouwerpublishing.com',
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

/** @param {{"backendUrl": string, "currentUser": import('firebase/auth').User | null}} props */
export default function UnifiedMediaVaultTab({ backendUrl, currentUser }) {
  const [categories, setCategories] = useState(/** @type {Array<{"name": string, "files": Array<{"type": string, "url": string, "filename": string, "size": number}>}>} */ ([]));
  const [activeCategory, setActiveCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [lightboxMedia, setLightboxMedia] = useState(/** @type {{"type": string, "url": string, "filename": string, "size": number} | null} */ (null));

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

  // Password prompt removed 2026-11-22: it was client-side only; backend auth is the real gate.
  const isUnlocked = true;

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

  /** @param {number} bytes */
const formatSize = ( bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  /** @param {typeof lightboxMedia} media */
const handleMediaClick = ( media) => {
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
                      onMouseEnter={
( e) => e.currentTarget.play()}
                      onMouseLeave={
( e) => {
                        e.currentTarget.pause();
                        e.currentTarget.currentTime = 0;
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
          <div className="vault-lightbox-content" onClick={
( e) => e.stopPropagation()}>
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
