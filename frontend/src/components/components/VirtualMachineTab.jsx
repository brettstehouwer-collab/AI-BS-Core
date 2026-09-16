/**
 * PHASE 4, STAGE 3: VNC CANVAS COMPONENT
 * React component for displaying VM framebuffer in Electron UI
 * 
 * Lazy-loaded tab that streams VNC protocol over WebSocket
 * Includes keyboard/mouse input handling
 */

import React, { useEffect, useRef, useState } from 'react';

export default function VirtualMachineTab() {
  const canvasRef = useRef(null);
  const websocketRef = useRef(null);
  const [vmList, setVmList] = useState([]);
  const [selectedVm, setSelectedVm] = useState(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState('Ready');

  // Initialize WebSocket connection to VNC bridge
  useEffect(() => {
    let ws = null;
    let isDisposed = false;

    try {
      ws = new WebSocket('ws://localhost:6080');
      
      ws.onopen = () => {
        if (isDisposed) return;
        console.log('[VNC] WebSocket connected to bridge');
        setStatus('Bridge connected');
      };
      
      ws.onmessage = (event) => {
        if (isDisposed) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'vnc_connected') {
            console.log('[VNC] Connected to VM:', data.vm_id);
            setConnected(true);
            setStatus(`Connected to ${data.vm_id}`);
          } else if (data.type === 'vnc_framebuffer') {
            // Receive framebuffer data and render to canvas
            const imageData = data.framebuffer;
            renderFramebuffer(imageData);
          } else if (data.type === 'vnc_error') {
            console.warn('[VNC] Notice:', data.error);
            setStatus(`Error: ${data.error}`);
          }
        } catch (e) {}
      };
      
      ws.onerror = (error) => {
        if (isDisposed) return;
        setStatus('Connection standby / offline');
      };
      
      websocketRef.current = ws;
    } catch (err) {
      setStatus('Bridge offline');
    }
    
    return () => {
      isDisposed = true;
      if (ws) {
        ws.onerror = null;
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        } else if (ws.readyState === WebSocket.CONNECTING) {
          ws.onopen = () => { try { ws.close(); } catch (e) {} };
        }
      }
    };
  }, []);

  // Fetch list of active VMs
  useEffect(() => {
    const fetchVmList = async () => {
      try {
        const response = await fetch('https://api.brettstehouwer.live/api/phase4/vm/list');
        const data = await response.json();
        if (data.status === 'success') {
          setVmList(data.data.vms || []);
        }
      } catch (error) {
        console.error('[VNC] Failed to fetch VM list:', error);
      }
    };

    const interval = setInterval(fetchVmList, 5000); // Poll every 5 seconds
    fetchVmList(); // Initial fetch

    return () => clearInterval(interval);
  }, []);

  // Connect to selected VM
  const connectToVm = (vmId) => {
    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      setStatus('WebSocket not connected');
      return;
    }

    websocketRef.current.send(JSON.stringify({
      cmd: 'connect',
      vm_id: vmId,
      vnc_host: 'localhost',
      vnc_port: 5900 + parseInt(vmId.slice(-2), 16) % 100, // Dynamic VNC port based on VM ID
    }));

    setSelectedVm(vmId);
  };

  // Disconnect from VM
  const disconnectFromVm = () => {
    if (selectedVm && websocketRef.current) {
      websocketRef.current.send(JSON.stringify({
        cmd: 'disconnect',
        vm_id: selectedVm,
      }));
    }
    setConnected(false);
    setSelectedVm(null);
    setStatus('Disconnected');
  };

  // Handle keyboard input
  const handleKeyDown = (e) => {
    if (!connected || !websocketRef.current) return;

    websocketRef.current.send(JSON.stringify({
      cmd: 'input',
      vm_id: selectedVm,
      type: 'keyboard',
      data: {
        keyCode: e.keyCode,
        keyDown: true,
      },
    }));
  };

  const handleKeyUp = (e) => {
    if (!connected || !websocketRef.current) return;

    websocketRef.current.send(JSON.stringify({
      cmd: 'input',
      vm_id: selectedVm,
      type: 'keyboard',
      data: {
        keyCode: e.keyCode,
        keyDown: false,
      },
    }));
  };

  // Handle mouse input
  const handleMouseMove = (e) => {
    if (!connected || !websocketRef.current || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    websocketRef.current.send(JSON.stringify({
      cmd: 'input',
      vm_id: selectedVm,
      type: 'mouse',
      data: {
        x: Math.round(x),
        y: Math.round(y),
        buttons: e.buttons,
      },
    }));
  };

  const handleMouseClick = (e) => {
    if (!connected || !websocketRef.current) return;

    websocketRef.current.send(JSON.stringify({
      cmd: 'input',
      vm_id: selectedVm,
      type: 'mouse',
      data: {
        x: e.clientX,
        y: e.clientY,
        buttons: e.buttons,
        click: true,
      },
    }));
  };

  // Render framebuffer to canvas
  const renderFramebuffer = (imageData) => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // In production, would decode RFB/VNC frame format
    // For now, just draw placeholder
    if (ctx) {
      ctx.fillStyle = '#1a1a2e';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#16c784';
      ctx.font = '16px monospace';
      ctx.fillText(`VM: ${selectedVm}`, 20, 50);
      ctx.fillText('Framebuffer streaming...', 20, 80);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2>Virtual Machines</h2>
        <div style={styles.status}>Status: {status}</div>
      </div>

      <div style={styles.content}>
        {/* VM Selection Panel */}
        <div style={styles.vmList}>
          <h3>Active VMs</h3>
          {vmList.length === 0 ? (
            <p style={styles.empty}>No active VMs</p>
          ) : (
            <div>
              {vmList.map((vm) => (
                <div
                  key={vm.vm_id}
                  onClick={() => connectToVm(vm.vm_id)}
                  style={{
                    ...styles.vmItem,
                    backgroundColor: selectedVm === vm.vm_id ? '#239d60' : '#16c784',
                  }}
                >
                  <div style={styles.vmId}>{vm.vm_id}</div>
                  <div style={styles.vmInfo}>
                    {vm.memory_mb}MB / {vm.cpu_cores} CPU
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* VNC Canvas */}
        <div style={styles.canvasContainer}>
          <canvas
            ref={canvasRef}
            width={800}
            height={600}
            style={styles.canvas}
            onKeyDown={handleKeyDown}
            onKeyUp={handleKeyUp}
            onMouseMove={handleMouseMove}
            onClick={handleMouseClick}
            tabIndex={0}
          />
        </div>

        {/* Controls */}
        <div style={styles.controls}>
          {connected ? (
            <>
              <button
                onClick={disconnectFromVm}
                style={styles.buttonDanger}
              >
                Disconnect
              </button>
              <div style={styles.hint}>
                Click canvas to focus. Use keyboard/mouse to interact with VM.
              </div>
            </>
          ) : (
            <div style={styles.hint}>
              Select a VM above to connect
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#0b0717',
    color: '#d7ffd8',
    fontFamily: 'monospace',
  },
  header: {
    padding: '20px',
    borderBottom: '1px solid #39ff14',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  status: {
    fontSize: '12px',
    color: '#16c784',
  },
  content: {
    display: 'flex',
    flex: 1,
    gap: '20px',
    padding: '20px',
    overflow: 'hidden',
  },
  vmList: {
    width: '200px',
    backgroundColor: 'rgba(26, 14, 54, 0.5)',
    border: '1px solid #39ff14',
    borderRadius: '8px',
    padding: '15px',
    overflowY: 'auto',
  },
  empty: {
    color: '#999',
    fontSize: '12px',
  },
  vmItem: {
    padding: '10px',
    marginBottom: '10px',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  vmId: {
    fontWeight: 'bold',
    marginBottom: '5px',
  },
  vmInfo: {
    fontSize: '11px',
    color: '#0b0717',
  },
  canvasContainer: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(26, 14, 54, 0.5)',
    border: '1px solid #39ff14',
    borderRadius: '8px',
    overflow: 'hidden',
  },
  canvas: {
    width: '100%',
    height: '100%',
    backgroundColor: '#1a1a2e',
    outline: 'none',
  },
  controls: {
    padding: '15px',
    backgroundColor: 'rgba(26, 14, 54, 0.5)',
    border: '1px solid #39ff14',
    borderRadius: '8px',
    textAlign: 'center',
  },
  buttonDanger: {
    padding: '8px 16px',
    backgroundColor: '#ff3ca7',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontFamily: 'monospace',
  },
  hint: {
    marginTop: '10px',
    fontSize: '12px',
    color: '#999',
  },
};
