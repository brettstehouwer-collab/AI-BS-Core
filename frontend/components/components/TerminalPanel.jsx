import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

// injectRef: a React ref whose .current is set to a function (cmd) => void
// that types the command into the terminal and executes it.
export default function TerminalPanel({ backendUrl, injectRef }) {
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
        cursor: '#00ff00',
        selectionBackground: 'rgba(0,255,0,0.2)'
      },
      fontFamily: '"Cascadia Code", "Fira Code", Consolas, monospace',
      fontSize: 14,
      cursorBlink: true,
      scrollback: 5000,
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
      } catch (e) {}
    };

    const PROMPT = 'PS C:\\AI-BS> ';

    const runCommand = async (cmd) => {
      term.write('\r\n');
      commandRef.current = '';
      if (!cmd.trim()) {
        term.write(PROMPT);
        return;
      }
      term.writeln(`\x1b[1;33m» Executing: ${cmd}\x1b[0m`);
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
        if (result.stderr && result.stderr.trim()) {
          const lines = result.stderr.split('\n');
          lines.forEach(l => {
            if (l.trim()) term.writeln(`\x1b[1;31m${l.replace(/\r/g, '')}\x1b[0m`);
          });
        }
        if (result.exit_code !== 0 && result.exit_code !== undefined) {
          term.writeln(`\x1b[2;31m[exit code: ${result.exit_code}]\x1b[0m`);
        }
      } catch (e) {
        term.writeln(`\x1b[1;31mConnection error: ${e.message}\x1b[0m`);
        term.writeln(`\x1b[2;31mMake sure the AI-BS backend is running on ${backendUrl}\x1b[0m`);
      }
      term.write(PROMPT);
    };

    rafId = requestAnimationFrame(() => {
      if (isDisposed) return;
      safeFit();
      try {
        term.writeln('\x1b[1;32mStehouwer OS Virtual Terminal [Version 1.5]\x1b[0m');
        term.writeln('\x1b[2;37m(c) Stehouwer Productions. All rights reserved.\x1b[0m');
        term.writeln(`\x1b[2;36mBackend: ${backendUrl}/api/terminal/run — PowerShell ExecutionPolicy Bypass\x1b[0m`);
        term.writeln('\x1b[2;37mType any PowerShell command or use the Quick Commands dropdown above.\x1b[0m');
        term.write(`\r\n${PROMPT}`);
      } catch (e) {}
    });

    term.onData(async (data) => {
      if (isDisposed) return;
      if (data === '\r') {
        await runCommand(commandRef.current);
      } else if (data === '\x7f') { // Backspace
        if (commandRef.current.length > 0) {
          commandRef.current = commandRef.current.slice(0, -1);
          term.write('\b \b');
        }
      } else if (data === '\x03') { // Ctrl+C
        commandRef.current = '';
        term.write('^C\r\n' + PROMPT);
      } else {
        commandRef.current += data;
        term.write(data);
      }
    });

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Expose inject function to parent via ref
    if (injectRef) {
      injectRef.current = async (cmd) => {
        if (isDisposed) return;
        // Echo what we're about to run
        commandRef.current = cmd;
        term.write(cmd);
        await runCommand(cmd);
      };
    }

    const handleResize = () => { safeFit(); };
    window.addEventListener('resize', handleResize);

    return () => {
      isDisposed = true;
      if (injectRef) injectRef.current = null;
      if (rafId) cancelAnimationFrame(rafId);
      window.removeEventListener('resize', handleResize);
      try { term.dispose(); } catch (e) {}
    };
  }, [backendUrl]);

  return (
    <div style={{ flex: 1, height: '100%', width: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div style={{ background: '#0d1117', padding: '3px 8px', fontSize: '11px', color: '#444', borderBottom: '1px solid #1a1a1a', letterSpacing: '0.05em' }}>
        TERMINAL — PowerShell ExecutionPolicy Bypass · CWD: C:\AI-BS
      </div>
      <div ref={terminalRef} style={{ flex: 1, width: '100%', padding: '4px', background: '#0a0a0a' }} />
    </div>
  );
}
