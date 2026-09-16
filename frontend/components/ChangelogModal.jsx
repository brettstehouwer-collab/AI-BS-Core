import React from 'react';
import './ChangelogModal.css';
import changelogData from './changelog.json';

export default function ChangelogModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="changelog-overlay">
      <div className="changelog-modal glass-panel">
        <div className="changelog-header">
          <h2>🚀 What's New in Bullshit AI</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="changelog-content">
          {changelogData.map((release, index) => (
            <div key={release.version} className="release-block">
              <div className="release-header">
                <h3>Version {release.version}</h3>
                <span className="release-date">{release.date}</span>
              </div>
              <h4 className="release-title">{release.title}</h4>
              <ul className="release-changes">
                {release.changes.map((change, i) => (
                  <li key={i}>{change}</li>
                ))}
              </ul>
              {index < changelogData.length - 1 && <div className="release-divider" />}
            </div>
          ))}
        </div>
        
        <div className="changelog-footer">
          <button className="got-it-btn" onClick={onClose}>Awesome, Got It!</button>
        </div>
      </div>
    </div>
  );
}
