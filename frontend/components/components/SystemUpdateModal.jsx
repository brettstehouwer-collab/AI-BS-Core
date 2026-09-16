import React, { useState, useEffect } from 'react';
import { 
  Download, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  X, 
  HardDrive, 
  ArrowRight, 
  ShieldCheck, 
  Package, 
  Terminal,
  ExternalLink
} from 'lucide-react';

export default function SystemUpdateModal({ isOpen, onClose, currentVersion = '5.233.0' }) {
  const [checking, setChecking] = useState(false);
  const [updateInfo, setUpdateInfo] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | checking | available | up_to_date | downloading | downloaded | applying | error
  const [progress, setProgress] = useState({ percent: 0, downloadedBytes: 0, totalBytes: 0 });
  const [errorMsg, setErrorMsg] = useState('');
  const [appVersion, setAppVersion] = useState(currentVersion);

  const isElectron = typeof window !== 'undefined' && !!window.aibsUpdater;

  useEffect(() => {
    if (isOpen) {
      if (isElectron && window.aibsUpdater.getVersion) {
        window.aibsUpdater.getVersion().then(v => {
          if (v) setAppVersion(v);
        }).catch(() => {});
      }
      handleCheckForUpdates();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isElectron) return;

    const unsubProgress = window.aibsUpdater.onProgress?.((p) => {
      setProgress(p);
      setStatus('downloading');
    });

    const unsubStatus = window.aibsUpdater.onStatus?.((s) => {
      if (s === 'downloaded') {
        setStatus('downloaded');
      }
    });

    return () => {
      if (unsubProgress) unsubProgress();
      if (unsubStatus) unsubStatus();
    };
  }, [isElectron]);

  const handleCheckForUpdates = async () => {
    setChecking(true);
    setStatus('checking');
    setErrorMsg('');

    try {
      if (isElectron) {
        const res = await window.aibsUpdater.checkForUpdates();
        setChecking(false);
        if (res && res.updateAvailable) {
          setUpdateInfo(res);
          setStatus('available');
        } else {
          setUpdateInfo(res);
          setStatus('up_to_date');
        }
      } else {
        // Web fallback: query backend updater API
        const resp = await fetch('/api/v1/updater/check').catch(() => null);
        if (resp && resp.ok) {
          const data = await resp.json();
          setChecking(false);
          if (data.update_available) {
            setUpdateInfo({
              updateAvailable: true,
              latestVersion: data.latest_version,
              releaseNotes: data.manifest?.releaseNotes || 'Maintenance and feature update.',
              downloadUrl: data.manifest?.downloadUrl || '',
              sizeBytes: data.manifest?.sizeBytes || 0,
              sha256: data.manifest?.sha256 || ''
            });
            setStatus('available');
          } else {
            setUpdateInfo(data);
            setStatus('up_to_date');
          }
        } else {
          // Direct fallback to static manifest
          const staticResp = await fetch('/updates/version.json').catch(() => null);
          if (staticResp && staticResp.ok) {
            const manifest = await staticResp.json();
            setChecking(false);
            setUpdateInfo({
              updateAvailable: manifest.version !== appVersion,
              latestVersion: manifest.version,
              releaseNotes: manifest.releaseNotes,
              downloadUrl: manifest.downloadUrl,
              sizeBytes: manifest.sizeBytes,
              sha256: manifest.sha256
            });
            setStatus(manifest.version !== appVersion ? 'available' : 'up_to_date');
          } else {
            setChecking(false);
            setStatus('up_to_date');
          }
        }
      }
    } catch (err) {
      setChecking(false);
      setStatus('error');
      setErrorMsg(err.message || 'Failed to connect to update server.');
    }
  };

  const handleStartDownload = async () => {
    if (!updateInfo?.downloadUrl && !updateInfo?.fallbackUrl) return;
    setStatus('downloading');
    setProgress({ percent: 0, downloadedBytes: 0, totalBytes: updateInfo.sizeBytes || 0 });
    setErrorMsg('');

    try {
      if (isElectron) {
        const res = await window.aibsUpdater.downloadUpdate(updateInfo.downloadUrl);
        if (res && res.success) {
          setStatus('downloaded');
        } else {
          setStatus('error');
          setErrorMsg('Download did not complete successfully.');
        }
      } else {
        // In web mode, trigger browser file download
        const url = updateInfo.downloadUrl || updateInfo.fallbackUrl;
        window.open(url, '_blank');
        setStatus('downloaded');
      }
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.message || 'Error occurred while downloading update payload.');
    }
  };

  const handleApplyUpdate = async () => {
    if (!isElectron) {
      alert('In-place binary updating is managed via the native Windows Electron application. Download the zip archive manually in web mode.');
      return;
    }
    setStatus('applying');
    try {
      await window.aibsUpdater.applyUpdate();
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.message || 'Failed to spawn updater stub.');
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes <= 0) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(5, 7, 12, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: '#0d1117',
        border: '1px solid #30363d',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '560px',
        boxShadow: '0 20px 50px rgba(0,0,0,0.8), 0 0 20px rgba(88, 166, 255, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #21262d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#161b22'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(88, 166, 255, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#58a6ff'
            }}>
              <Package size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '700', color: '#f0f6fc' }}>
                App-Level System Updater
              </h3>
              <p style={{ margin: 0, fontSize: '0.72rem', color: '#8b949e' }}>
                Delta binary & in-place application patch engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#8b949e',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              display: 'flex'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Version Comparison Bar */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto 1fr',
            alignItems: 'center',
            background: '#161b22',
            padding: '12px 16px',
            borderRadius: '8px',
            border: '1px solid #21262d'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: '#8b949e' }}>CURRENT VERSION</div>
              <div style={{ fontSize: '1rem', fontWeight: '700', color: '#f0f6fc' }}>
                v{appVersion}
              </div>
            </div>
            <ArrowRight size={18} style={{ color: '#58a6ff', opacity: 0.6 }} />
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.72rem', color: '#8b949e' }}>LATEST CLOUD BUILD</div>
              <div style={{ 
                fontSize: '1rem', 
                fontWeight: '700', 
                color: updateInfo?.latestVersion && updateInfo.latestVersion !== appVersion ? '#3fb950' : '#8b949e' 
              }}>
                v{updateInfo?.latestVersion || appVersion}
              </div>
            </div>
          </div>

          {/* Status Message / Card */}
          {status === 'checking' && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '16px',
              borderRadius: '8px',
              background: 'rgba(88, 166, 255, 0.08)',
              border: '1px solid rgba(88, 166, 255, 0.2)'
            }}>
              <RefreshCw size={20} className="animate-spin" style={{ color: '#58a6ff' }} />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f0f6fc' }}>
                  Checking update server...
                </div>
                <div style={{ fontSize: '0.75rem', color: '#8b949e' }}>
                  Connecting to ai-bs-dashboard.web.app/updates/version.json
                </div>
              </div>
            </div>
          )}

          {status === 'up_to_date' && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '16px',
              borderRadius: '8px',
              background: 'rgba(63, 185, 80, 0.08)',
              border: '1px solid rgba(63, 185, 80, 0.25)'
            }}>
              <CheckCircle2 size={22} style={{ color: '#3fb950', flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: '0.88rem', fontWeight: '600', color: '#3fb950' }}>
                  Your system is up to date
                </div>
                <div style={{ fontSize: '0.75rem', color: '#8b949e' }}>
                  You are currently running the latest sovereign release (v{appVersion}).
                </div>
              </div>
            </div>
          )}

          {(status === 'available' || status === 'downloading' || status === 'downloaded' || status === 'applying') && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              padding: '16px',
              borderRadius: '8px',
              background: 'rgba(88, 166, 255, 0.05)',
              border: '1px solid rgba(88, 166, 255, 0.25)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{
                  background: '#238636',
                  color: '#ffffff',
                  fontSize: '0.7rem',
                  fontWeight: '700',
                  padding: '2px 8px',
                  borderRadius: '12px'
                }}>
                  NEW UPDATE AVAILABLE
                </span>
                <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>
                  Payload Size: {formatBytes(updateInfo?.sizeBytes)}
                </span>
              </div>

              <div>
                <div style={{ fontSize: '0.82rem', fontWeight: '600', color: '#f0f6fc', marginBottom: '4px' }}>
                  Release Notes:
                </div>
                <div style={{
                  fontSize: '0.78rem',
                  color: '#c9d1d9',
                  background: '#161b22',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid #30363d',
                  lineHeight: '1.4'
                }}>
                  {updateInfo?.releaseNotes || 'Maintenance and bug fixes.'}
                </div>
              </div>

              {/* Download Progress Bar */}
              {(status === 'downloading' || status === 'downloaded') && (
                <div style={{ marginTop: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
                    <span style={{ color: '#8b949e' }}>
                      {status === 'downloaded' ? 'Download Complete' : 'Downloading Update Payload...'}
                    </span>
                    <span style={{ color: '#58a6ff', fontWeight: '600' }}>
                      {progress.percent}% ({formatBytes(progress.downloadedBytes)} / {formatBytes(progress.totalBytes || updateInfo?.sizeBytes)})
                    </span>
                  </div>
                  <div style={{
                    width: '100%',
                    height: '8px',
                    background: '#21262d',
                    borderRadius: '4px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${progress.percent}%`,
                      height: '100%',
                      background: status === 'downloaded' ? '#238636' : '#1f6feb',
                      transition: 'width 0.2s ease'
                    }} />
                  </div>
                </div>
              )}

              {status === 'applying' && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px',
                  background: 'rgba(210, 153, 34, 0.1)',
                  borderRadius: '6px',
                  border: '1px solid rgba(210, 153, 34, 0.3)'
                }}>
                  <RefreshCw size={16} className="animate-spin" style={{ color: '#d29922' }} />
                  <span style={{ fontSize: '0.78rem', color: '#d29922', fontWeight: '600' }}>
                    Launching aibs_updater.exe stub & restarting application...
                  </span>
                </div>
              )}
            </div>
          )}

          {status === 'error' && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '16px',
              borderRadius: '8px',
              background: 'rgba(248, 81, 73, 0.1)',
              border: '1px solid rgba(248, 81, 73, 0.3)'
            }}>
              <AlertTriangle size={20} style={{ color: '#f85149', flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f85149' }}>
                  Update Error
                </div>
                <div style={{ fontSize: '0.75rem', color: '#8b949e' }}>
                  {errorMsg}
                </div>
              </div>
            </div>
          )}

          {/* Technical Info Box */}
          <div style={{
            fontSize: '0.72rem',
            color: '#8b949e',
            borderTop: '1px solid #21262d',
            paddingTop: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={14} style={{ color: '#3fb950' }} />
              <span>Zero-Installer In-Place Patching: Atomic .old swap with rollback backup</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <HardDrive size={14} style={{ color: '#58a6ff' }} />
              <span>Engine: aibs_updater.exe (Go 1.26.5 standalone binary)</span>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div style={{
          padding: '14px 20px',
          background: '#161b22',
          borderTop: '1px solid #21262d',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '10px'
        }}>
          <button
            onClick={onClose}
            style={{
              background: '#21262d',
              border: '1px solid #30363d',
              color: '#c9d1d9',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            Close
          </button>

          {status === 'available' && (
            <button
              onClick={handleStartDownload}
              style={{
                background: '#1f6feb',
                border: '1px solid #388bfd',
                color: '#ffffff',
                padding: '8px 16px',
                borderRadius: '6px',
                fontSize: '0.82rem',
                cursor: 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 2px 6px rgba(31, 111, 235, 0.4)'
              }}
            >
              <Download size={16} />
              <span>Download & Stage Update</span>
            </button>
          )}

          {status === 'downloaded' && (
            <button
              onClick={handleApplyUpdate}
              style={{
                background: '#238636',
                border: '1px solid #2ea043',
                color: '#ffffff',
                padding: '8px 16px',
                borderRadius: '6px',
                fontSize: '0.82rem',
                cursor: 'pointer',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 2px 8px rgba(35, 134, 54, 0.5)'
              }}
            >
              <RefreshCw size={16} />
              <span>Apply Update & Restart Now</span>
            </button>
          )}

          {(status === 'up_to_date' || status === 'error' || status === 'idle') && (
            <button
              onClick={handleCheckForUpdates}
              disabled={checking}
              style={{
                background: '#238636',
                border: '1px solid #2ea043',
                color: '#ffffff',
                padding: '8px 14px',
                borderRadius: '6px',
                fontSize: '0.82rem',
                cursor: checking ? 'not-allowed' : 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                opacity: checking ? 0.7 : 1
              }}
            >
              <RefreshCw size={14} className={checking ? "animate-spin" : ""} />
              <span>Check Again</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

