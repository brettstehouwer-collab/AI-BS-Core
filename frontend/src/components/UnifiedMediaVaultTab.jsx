import React, { useState, useEffect } from 'react';
import './UnifiedMediaVaultTab.css';

export default function UnifiedMediaVaultTab({ backendUrl }) {
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [lightboxMedia, setLightboxMedia] = useState(null);

  useEffect(() => {
    fetchMedia();
  }, []);

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

  return (
    <div className="media-vault-container">
      <div className="media-vault-header">
        <h1><span>🎨</span> Media & Asset Vault</h1>
        <p>Unified gallery for all AI-BS generated images, videos, 3D renders, and assets.</p>
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
