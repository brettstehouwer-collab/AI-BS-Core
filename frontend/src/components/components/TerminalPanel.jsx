import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

export default function TerminalPanel({ backendUrl }) {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);
  const commandRef = useRef('');

  useEffect(() => {
    if (!terminalRef.current) return;

    let isDisposed = false;
    let rafId = null;

    const term = new Terminal({
      theme: {
        background: '#0a0a0a',
        foreground: '#00ff00',
        cursor: '#00ff00'
      },
      fontFamily: 'Courier New, monospace',
      fontSize: 14,
      cursorBlink: true
    });
    
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    
    try {
      term.open(terminalRef.current);
    } catch (e) {
      console.warn("xterm open notice:", e);
    }

    const safeFit = () => {
      if (isDisposed) return;
      try {
        if (
          terminalRef.current && 
          terminalRef.current.clientWidth > 0 && 
          terminalRef.current.clientHeight > 0 &&
          term._core && 
          term._core._renderService && 
          term._core._renderService.dimensions
        ) {
          fitAddon.fit();
        }
      } catch (e) {
        // Silently catch dimension timing errors during DOM mounting
      }
    };

    rafId = requestAnimationFrame(() => {
      if (isDisposed) return;
      safeFit();
      try {
        term.writeln('\x1b[1;32mStehouwer OS Virtual Terminal [Version 1.0]\x1b[0m');
        term.writeln('(c) Stehouwer Productions. All rights reserved.');
        term.write('\r\nPS C:\\Workspaces\\Stehouwer_Server\\Projects> ');
      } catch (e) {}
    });

    term.onData(async (data) => {
      if (isDisposed) return;
      if (data === '\r') {
        // Execute command
        term.write('\r\n');
        const cmd = commandRef.current.trim();
        commandRef.current = '';
        
        if (cmd) {
          try {
            const res = await fetch(`${backendUrl}/api/terminal/run`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ command: cmd })
            });
            const result = await res.json();
            
            if (result.stdout) {
              const lines = result.stdout.split('\n');
              lines.forEach(l => term.writeln(l.replace(/\r/g, '')));
            }
            if (result.stderr) {
              const lines = result.stderr.split('\n');
              lines.forEach(l => term.writeln(`\x1b[1;31m${l.replace(/\r/g, '')}\x1b[0m`));
            }
          } catch (e) {
            term.writeln(`\x1b[1;31mError: ${e.message}\x1b[0m`);
          }
        }
        term.write('PS C:\\Workspaces\\Stehouwer_Server\\Projects> ');
      } else if (data === '\x7f') { // Backspace
        if (commandRef.current.length > 0) {
          commandRef.current = commandRef.current.slice(0, -1);
          term.write('\b \b');
        }
      } else {
        commandRef.current += data;
        term.write(data);
      }
    });

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    const handleResize = () => {
      safeFit();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      isDisposed = true;
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener('resize', handleResize);
      try {
        term.dispose();
      } catch (e) {
        // Suppress disposal errors
      }
    };
  }, [backendUrl]);

  return (
    <div style={{ flex: 1, height: '100%', width: '100%', overflow: 'hidden', borderTop: '1px solid var(--border-glow)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ background: '#111', padding: '4px 8px', fontSize: '12px', color: '#888', borderBottom: '1px solid #333' }}>
        TERMINAL
      </div>
      <div ref={terminalRef} style={{ flex: 1, width: '100%', padding: '8px', background: '#0a0a0a' }} />
    </div>
  );
}
