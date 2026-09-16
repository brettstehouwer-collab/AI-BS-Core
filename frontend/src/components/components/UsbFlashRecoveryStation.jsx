import React, { useState, useEffect } from 'react';

export default function UsbFlashRecoveryStation({ backendUrl }) {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDisk, setSelectedDisk] = useState(null);
  const [probeResult, setProbeResult] = useState(null);
  const [probing, setProbing] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildStatus, setRebuildStatus] = useState(null);
  const [targetFs, setTargetFs] = useState('FAT32');
  const [volumeLabel, setVolumeLabel] = useState('AI_BS_USB');
  const [confirmDestructive, setConfirmDestructive] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState('devices'); // 'devices', 'flasher_guide', 'pinout_matrix'

  const API_BASE = backendUrl || 'http://127.0.0.1:8080';

  const scanDevices = async () => {
    setLoading(true);
    setRebuildStatus(null);
    try {
      const res = await fetch(`${API_BASE}/api/usb-recovery/devices`, {
        headers: {
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        setDevices(data.devices || []);
        if (data.devices && data.devices.length > 0 && !selectedDisk) {
          setSelectedDisk(data.devices[0].disk_number);
        }
      }
    } catch (err) {
      console.warn("USB scanner error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    scanDevices();
  }, []);

  const handleProbe = async (diskNum) => {
    setProbing(true);
    setProbeResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/usb-recovery/probe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ disk_number: diskNum })
      });
      const data = await res.json();
      if (res.ok) {
        setProbeResult(data);
      } else {
        setProbeResult({ error: data.detail || 'Probe failed' });
      }
    } catch (err) {
      setProbeResult({ error: String(err) });
    } finally {
      setProbing(false);
    }
  };

  const handleRebuild = async (diskNum) => {
    if (!confirmDestructive) {
      alert("Safety Lock: You must check 'Confirm Total Wipe' before rebuilding the partition table.");
      return;
    }
    setRebuilding(true);
    setRebuildStatus(null);
    try {
      const res = await fetch(`${API_BASE}/api/usb-recovery/rebuild-partition`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({
          disk_number: diskNum,
          file_system: targetFs,
          volume_label: volumeLabel,
          confirm_destructive: true
        })
      });
      const data = await res.json();
      if (res.ok) {
        setRebuildStatus({ success: true, message: data.message || 'Partition rebuilt and formatted successfully.' });
        scanDevices();
      } else {
        setRebuildStatus({ success: false, message: data.detail || 'Rebuild failed' });
      }
    } catch (err) {
      setRebuildStatus({ success: false, message: String(err) });
    } finally {
      setRebuilding(false);
    }
  };

  const currentDev = devices.find(d => d.disk_number === selectedDisk);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', color: '#e2e8f0', width: '100%' }}>
      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.9))',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: '12px',
        padding: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.8rem' }}>💾</span>
            <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 800, color: '#38bdf8' }}>
              AI-BS USB Diagnostic & Flash Drive Recovery Engine
            </h2>
            <span style={{
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid #38bdf8',
              color: '#38bdf8',
              fontSize: '0.75rem',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '6px'
            }}>
              HARDWARE LEVEL
            </span>
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.88rem', color: '#94a3b8' }}>
            Direct Win32 SCSI pass-through probing, flash controller identification (ChipsBank, Phison, SMI, Alcor), LBA sector 0 testing, and partition re-initialization.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={scanDevices}
            disabled={loading}
            style={{
              background: 'linear-gradient(135deg, #0284c7, #2563eb)',
              color: '#ffffff',
              border: 'none',
              padding: '10px 18px',
              borderRadius: '8px',
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.88rem'
            }}
          >
            <span>{loading ? '🔄 Scanning...' : '🔄 Rescan USB Busses'}</span>
          </button>
        </div>
      </div>

      {/* Safety Notice Card */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.6)',
        border: '1px solid rgba(234, 179, 8, 0.3)',
        borderRadius: '8px',
        padding: '12px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        fontSize: '0.84rem',
        color: '#facc15'
      }}>
        <span>🛡️</span>
        <div>
          <strong>System NVMe Protection Active:</strong> Disks 0, 1, 2 (Samsung 980/990 PRO NVMe system drives <code>C:</code>, <code>D:</code>, <code>E:</code>) are permanently locked against formatting or destructive commands. Only verified <code>BusType == 'USB'</code> removable media is accepted.
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '8px' }}>
        {[
          { id: 'devices', label: `Connected USB Media (${devices.length})`, icon: '🔌' },
          { id: 'flasher_guide', label: 'Mass-Production Flasher Guide (BootROM)', icon: '🛠️' },
          { id: 'pinout_matrix', label: 'Controller Pinout & Test Point Shorting', icon: '⚡' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              background: activeSubTab === tab.id ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
              border: `1px solid ${activeSubTab === tab.id ? '#38bdf8' : 'transparent'}`,
              color: activeSubTab === tab.id ? '#ffffff' : '#94a3b8',
              borderRadius: '6px',
              padding: '8px 16px',
              fontSize: '0.85rem',
              fontWeight: activeSubTab === tab.id ? 700 : 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {activeSubTab === 'devices' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) minmax(400px, 1.4fr)', gap: '20px' }}>
          {/* Left Column: Device Cards List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h3 style={{ margin: '0 0 4px 0', fontSize: '1rem', color: '#94a3b8' }}>Detected USB Storage Endpoints</h3>
            
            {devices.length === 0 ? (
              <div style={{
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px dashed rgba(255, 255, 255, 0.15)',
                borderRadius: '8px',
                padding: '30px',
                textAlign: 'center',
                color: '#64748b'
              }}>
                No USB storage devices detected. Plug in a flash drive or card reader and click "Rescan USB Busses".
              </div>
            ) : (
              devices.map(dev => {
                const isSelected = selectedDisk === dev.disk_number;
                const isBootRom = dev.state_category === 'bootrom_recovery';
                const isCorrupt = dev.state_category === 'corrupted_partition';

                return (
                  <div
                    key={dev.disk_number}
                    onClick={() => setSelectedDisk(dev.disk_number)}
                    style={{
                      background: isSelected ? 'rgba(30, 41, 59, 0.9)' : 'rgba(15, 23, 42, 0.6)',
                      border: `1px solid ${isSelected ? '#38bdf8' : 'rgba(255, 255, 255, 0.08)'}`,
                      borderRadius: '10px',
                      padding: '16px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      boxShadow: isSelected ? '0 0 12px rgba(56, 189, 248, 0.15)' : 'none'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '1.3rem' }}>{isBootRom ? '⚠️' : '💾'}</span>
                        <div>
                          <div style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.95rem' }}>
                            {dev.friendly_name}
                          </div>
                          <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                            PhysicalDrive{dev.disk_number} {dev.drive_letter ? `(Drive ${dev.drive_letter}:)` : '(No Drive Letter)'}
                          </div>
                        </div>
                      </div>

                      <span style={{
                        background: isBootRom ? 'rgba(239, 68, 68, 0.2)' : isCorrupt ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        border: `1px solid ${isBootRom ? '#ef4444' : isCorrupt ? '#f59e0b' : '#10b981'}`,
                        color: isBootRom ? '#f87171' : isCorrupt ? '#fbbf24' : '#34d399',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        padding: '3px 8px',
                        borderRadius: '6px'
                      }}>
                        {isBootRom ? 'BOOTROM RECOVERY' : isCorrupt ? 'RAW PARTITION' : 'READY'}
                      </span>
                    </div>

                    <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', fontSize: '0.8rem' }}>
                      <div>
                        <span style={{ color: '#64748b' }}>Capacity: </span>
                        <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{dev.size_gb > 0 ? `${dev.size_gb} GB` : '0 Bytes (No Media)'}</span>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>VID:PID: </span>
                        <span style={{ color: '#38bdf8', fontWeight: 600 }}>{dev.vid_pid}</span>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Operational: </span>
                        <span style={{ color: dev.operational_status === 'No Media' ? '#f87171' : '#34d399' }}>{dev.operational_status}</span>
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Partition: </span>
                        <span style={{ color: '#e2e8f0' }}>{dev.partition_style || 'None'}</span>
                      </div>
                    </div>

                    {dev.controller_signature && (
                      <div style={{
                        marginTop: '10px',
                        background: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid rgba(239, 68, 68, 0.25)',
                        borderRadius: '6px',
                        padding: '8px 10px',
                        fontSize: '0.76rem',
                        color: '#fca5a5'
                      }}>
                        <div><strong>Identified Controller:</strong> {dev.controller_signature.controller}</div>
                        <div><strong>Mode:</strong> {dev.controller_signature.mode}</div>
                        <div><strong>Recovery Utility:</strong> {dev.controller_signature.tool}</div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Right Column: Diagnostic Probe & Operations Deck */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {currentDev ? (
              <>
                {/* Station Diagnostic Deck */}
                <div style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '10px',
                  padding: '20px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#ffffff' }}>
                      Diagnostic Station: PhysicalDrive{currentDev.disk_number} ({currentDev.friendly_name})
                    </h3>
                    <button
                      onClick={() => handleProbe(currentDev.disk_number)}
                      disabled={probing}
                      style={{
                        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                        color: '#ffffff',
                        border: 'none',
                        padding: '7px 14px',
                        borderRadius: '6px',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        cursor: probing ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {probing ? 'Probing...' : '🔬 Probe SCSI & LBA'}
                    </button>
                  </div>

                  {probeResult && (
                    <div style={{
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: '8px',
                      padding: '14px',
                      fontSize: '0.82rem',
                      marginBottom: '16px'
                    }}>
                      <div style={{ fontWeight: 700, color: '#38bdf8', marginBottom: '8px' }}>
                        Low-Level Hardware Probe Results:
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px' }}>
                        <div><span style={{ color: '#64748b' }}>Hardware Vendor:</span> <strong>{probeResult.hardware_vendor || 'N/A'}</strong></div>
                        <div><span style={{ color: '#64748b' }}>Hardware Product:</span> <strong>{probeResult.hardware_product || 'N/A'}</strong></div>
                        <div><span style={{ color: '#64748b' }}>Firmware Revision:</span> <strong>{probeResult.hardware_revision || 'N/A'}</strong></div>
                        <div><span style={{ color: '#64748b' }}>LBA Read Status:</span> <strong style={{ color: probeResult.sector_zero_readable ? '#34d399' : '#f87171' }}>{probeResult.lba_status}</strong></div>
                        <div><span style={{ color: '#64748b' }}>BootROM Trap:</span> <strong style={{ color: probeResult.is_bootrom_mode ? '#f87171' : '#34d399' }}>{probeResult.is_bootrom_mode ? 'YES (Microcode Missing)' : 'NO'}</strong></div>
                        <div><span style={{ color: '#64748b' }}>SCSI Pass-Through:</span> <strong>{probeResult.scsi_pass_through_supported ? 'SUPPORTED' : `IOCTL Trap (${probeResult.scsi_pass_through_error})`}</strong></div>
                      </div>
                      {probeResult.diagnosis_summary && (
                        <div style={{ marginTop: '8px', color: '#94a3b8', fontStyle: 'italic', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '6px' }}>
                          {probeResult.diagnosis_summary}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Recommendation Banner */}
                  <div style={{
                    background: currentDev.state_category === 'bootrom_recovery' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(56, 189, 248, 0.1)',
                    border: `1px solid ${currentDev.state_category === 'bootrom_recovery' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(56, 189, 248, 0.25)'}`,
                    borderRadius: '8px',
                    padding: '12px',
                    fontSize: '0.84rem',
                    color: currentDev.state_category === 'bootrom_recovery' ? '#fca5a5' : '#7dd3fc'
                  }}>
                    <strong>AI Recommendation:</strong> {currentDev.recommended_action}
                  </div>
                </div>

                {/* Partition Rebuilder Control Deck */}
                <div style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '10px',
                  padding: '20px'
                }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#ffffff' }}>
                    Universal Low-Level Partition Rebuilder
                  </h3>
                  <p style={{ margin: '0 0 16px 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                    Clears corrupted partition tables (RAW), re-writes Master Boot Record (MBR), creates a maximum-size primary partition, and applies high-speed volume formatting.
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '16px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '4px' }}>Target Filesystem</label>
                      <select
                        value={targetFs}
                        onChange={(e) => setTargetFs(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'rgba(30, 41, 59, 0.8)',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          borderRadius: '6px',
                          padding: '8px 10px',
                          color: '#ffffff',
                          fontSize: '0.85rem'
                        }}
                      >
                        <option value="FAT32">FAT32 (Standard USB / Max Compatibility)</option>
                        <option value="exFAT">exFAT (Drives &gt; 32GB / Large Media)</option>
                        <option value="NTFS">NTFS (Windows System / High Security)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.78rem', color: '#94a3b8', marginBottom: '4px' }}>Volume Label</label>
                      <input
                        type="text"
                        value={volumeLabel}
                        onChange={(e) => setVolumeLabel(e.target.value)}
                        style={{
                          width: '100%',
                          background: 'rgba(30, 41, 59, 0.8)',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          borderRadius: '6px',
                          padding: '8px 10px',
                          color: '#ffffff',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <input
                      type="checkbox"
                      id="confirmDestructive"
                      checked={confirmDestructive}
                      onChange={(e) => setConfirmDestructive(e.target.checked)}
                      style={{ cursor: 'pointer' }}
                    />
                    <label htmlFor="confirmDestructive" style={{ fontSize: '0.82rem', color: '#cbd5e1', cursor: 'pointer' }}>
                      I confirm total wipe of <strong>PhysicalDrive{currentDev.disk_number}</strong> ({currentDev.friendly_name})
                    </label>
                  </div>

                  {rebuildStatus && (
                    <div style={{
                      background: rebuildStatus.success ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      border: `1px solid ${rebuildStatus.success ? '#10b981' : '#ef4444'}`,
                      borderRadius: '6px',
                      padding: '10px 12px',
                      fontSize: '0.82rem',
                      color: rebuildStatus.success ? '#34d399' : '#f87171',
                      marginBottom: '14px'
                    }}>
                      {rebuildStatus.message}
                    </div>
                  )}

                  <button
                    onClick={() => handleRebuild(currentDev.disk_number)}
                    disabled={rebuilding || !confirmDestructive || currentDev.state_category === 'bootrom_recovery'}
                    style={{
                      width: '100%',
                      background: currentDev.state_category === 'bootrom_recovery'
                        ? 'rgba(100, 116, 139, 0.4)'
                        : confirmDestructive
                        ? 'linear-gradient(135deg, #e11d48, #be123c)'
                        : 'rgba(255, 255, 255, 0.1)',
                      color: '#ffffff',
                      border: 'none',
                      padding: '12px',
                      borderRadius: '8px',
                      fontWeight: 800,
                      cursor: (rebuilding || !confirmDestructive || currentDev.state_category === 'bootrom_recovery') ? 'not-allowed' : 'pointer',
                      fontSize: '0.9rem',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {currentDev.state_category === 'bootrom_recovery'
                      ? '⚠️ Partition Rebuild Locked: Flash Microcode Re-Flash Required First'
                      : rebuilding
                      ? 'Rebuilding Partition Table...'
                      : `Rebuild & Format PhysicalDrive${currentDev.disk_number} (${targetFs})`}
                  </button>
                </div>
              </>
            ) : (
              <div style={{
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px dashed rgba(255, 255, 255, 0.15)',
                borderRadius: '10px',
                padding: '40px',
                textAlign: 'center',
                color: '#64748b'
              }}>
                Select a connected USB device to view low-level hardware diagnostics and recovery options.
              </div>
            )}
          </div>
        </div>
      )}

      {activeSubTab === 'flasher_guide' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '10px',
            padding: '20px'
          }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#38bdf8' }}>
              Flash Memory Controller Mass-Production Flashing Protocol
            </h3>
            <p style={{ margin: 0, fontSize: '0.86rem', color: '#94a3b8', lineHeight: 1.6 }}>
              When a USB flash drive reports <code>0 Bytes</code>, <code>No Media</code>, and appears as <code>VID: 048D, PID: 1234</code> (ChipsBank), <code>VID: 13FE, PID: 3D00</code> (Phison), or <code>VID: 090C, PID: 1000</code> (SMI), standard OS-level partition tools (Diskpart, Disk Management, GParted) cannot communicate with the NAND flash. The controller has halted and fallen back to its internal factory ROM.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
            {/* ChipsBank Box */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.2rem' }}>🔵</span>
                <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#38bdf8' }}>ChipsBank CBM209X / CBM219X</h4>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                <p><strong>Affected Controllers:</strong> CBM2098, CBM2099, CBM2199, CBM2098E, CBM2099E</p>
                <p><strong>Factory Signature:</strong> VID 048D / PID 1234 (ChipsBnk Flash Disk 5.00)</p>
                <p><strong>Recovery Software:</strong> ChipsBank <code>CBM209X UMPTool</code> / <code>APTool</code> (v7200 / v7201)</p>
                <p><strong>Flashing Procedure:</strong>
                  <br />1. Download official CBM209X UMPTool from USBDev.ru.
                  <br />2. Run <code>UMPTool.exe</code> as Administrator.
                  <br />3. The utility detects the CBM209X controller on port #1.
                  <br />4. Select "Scan Level: Low Level Format (Erase Blocks)".
                  <br />5. Click "All Start" to write new microcode, scan flash NAND bad blocks, and initialize the filesystem.
                </p>
              </div>
            </div>

            {/* Phison Box */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.2rem' }}>🟣</span>
                <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#818cf8' }}>Phison PS2251-XX Series</h4>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                <p><strong>Affected Controllers:</strong> PS2251-03 (PS2303), PS2251-67, PS2251-70</p>
                <p><strong>Factory Signature:</strong> VID 13FE / PID 3D00 (Phison 230X BootROM)</p>
                <p><strong>Recovery Software:</strong> <code>Phison MPALL</code> or <code>UPTool</code></p>
                <p><strong>Flashing Procedure:</strong> Requires matching Burner Image (<code>BNxx.BIN</code>) and Firmware File (<code>FWxx.BIN</code>) matching the specific NAND flash part number.</p>
              </div>
            </div>

            {/* Silicon Motion Box */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.2rem' }}>🟢</span>
                <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#34d399' }}>Silicon Motion (SMI) SM32XX</h4>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                <p><strong>Affected Controllers:</strong> SM3257EN, SM3267, SM3281</p>
                <p><strong>Factory Signature:</strong> VID 090C / PID 1000 (SMI Test Mode)</p>
                <p><strong>Recovery Software:</strong> <code>SMI MPTool</code> / <code>Dyna Mass Storage Tool</code></p>
                <p><strong>Flashing Procedure:</strong> Launch SMI MPTool, press "Scan USB (F5)", load default ISP firmware profile, and execute "Start (Space)".</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeSubTab === 'pinout_matrix' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(234, 179, 8, 0.3)',
            borderRadius: '10px',
            padding: '20px'
          }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#facc15' }}>
              Hardware Test-Point Shorting Procedure (Hardware Safe Mode)
            </h3>
            <p style={{ margin: 0, fontSize: '0.86rem', color: '#cbd5e1', lineHeight: 1.6 }}>
              If a flash drive is completely dead, unlisted in Device Manager, or the controller loops trying to initialize corrupted NAND memory, you must place the controller into <strong>Hardware Safe Mode (Test Mode)</strong> before plugging it in:
            </p>

            <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.82rem' }}>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px' }}>
                <strong>Step 1: Disassemble Casing:</strong> Carefully remove the plastic housing of the USB drive to expose the PCB, the controller IC (square chip), and the NAND flash chip (rectangular 48-pin chip).
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px' }}>
                <strong>Step 2: Identify TSOP-48 Data Pins:</strong> On standard 48-pin NAND packages, locate Pin 29 and Pin 30 (or Pin 31 and 32) on the data bus (I/O 0 to I/O 7).
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px' }}>
                <strong>Step 3: Bridge Pins:</strong> Using a needle, precision tweezers, or a dental pick, short Pin 29 and Pin 30 together.
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px' }}>
                <strong>Step 4: Plug In While Shorted:</strong> Insert the USB drive into the PC while maintaining the short. The controller will fail to read the corrupted NAND and will default to factory BootROM (VID: 048D / PID: 1234).
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px' }}>
                <strong>Step 5: Release Short & Flash:</strong> Once Windows sounds the USB chime and displays the device, immediately release the short. The device is now ready to receive firmware via UMPTool.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
