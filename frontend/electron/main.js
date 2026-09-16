/**
 * electron/main.js  —  AI-BS Matrix Electron shell
 *
 * Responsibilities:
 *  1. Spawn brain_backend.exe (the frozen FastAPI server) as a detached
 *     child process before the window opens.
 *  2. Wait for the backend to be ready (port probe loop).
 *  3. Load the compiled React SPA from dist/index.html (or the Vite dev
 *     server in development mode).
 *  4. Kill the backend process cleanly when all windows close.
 */

import { app, BrowserWindow, dialog, shell, session, desktopCapturer, ipcMain } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import https from 'https';
import os from 'os';
import crypto from 'crypto';

// Disable default Electron development security noise in DevTools console
process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true';


import { spawn }          from 'child_process';
import net                from 'net';
import http               from 'http';
import fs                 from 'fs';

function startLocalUiServer(distPath, preferredPort = 5173) {
  return new Promise((resolve) => {
    const mimeTypes = {
      '.html': 'text/html',
      '.js': 'text/javascript',
      '.css': 'text/css',
      '.json': 'application/json',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.svg': 'image/svg+xml',
      '.ico': 'image/x-icon',
      '.woff2': 'font/woff2'
    };

    const server = http.createServer((req, res) => {
      let reqPath = req.url.split('?')[0];
      if (reqPath === '/') reqPath = '/index.html';
      let filePath = path.join(distPath, reqPath);

      if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        filePath = path.join(distPath, 'index.html');
      }

      const ext = path.extname(filePath).toLowerCase();
      const contentType = mimeTypes[ext] || 'application/octet-stream';

      fs.readFile(filePath, (err, content) => {
        if (err) {
          res.writeHead(500);
          res.end('Server Error');
        } else {
          res.writeHead(200, { 
            'Content-Type': contentType,
            'Cross-Origin-Opener-Policy': 'same-origin-allow-popups'
          });
          res.end(content);
        }
      });
    });

    server.listen(preferredPort, '127.0.0.1', () => {
      console.log(`[UI Server] Serving dist from http://127.0.0.1:${preferredPort}`);
      resolve(preferredPort);
    }).on('error', () => {
      server.listen(4173, '127.0.0.1', () => {
        console.log(`[UI Server] Serving dist from http://127.0.0.1:4173`);
        resolve(4173);
      });
    });
  });
}

// ---------------------------------------------------------------------------
// Stable High-Performance Audio & Window Configuration
// ---------------------------------------------------------------------------
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const BACKEND_PORT   = 8000;
const BACKEND_HOST   = '127.0.0.1';
const BACKEND_BASE_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const PROBE_INTERVAL = 500;   // ms between readiness polls
const PROBE_TIMEOUT  = 30000; // ms before giving up on backend start

// ---------------------------------------------------------------------------
// Resolve brain_backend.exe path
//
//  Packaged (app.isPackaged = true):
//    electron-builder places extraResources inside  <installDir>/resources/
//    path = resources/brain_backend/brain_backend.exe
//
//  Development (npm run electron):
//    Use the dev Python server; skip spawning the exe.
// ---------------------------------------------------------------------------
function resolveBackendPaths() {
  if (app.isPackaged) {
    return {
      python: path.join(process.resourcesPath, 'brain_backend', 'brain_backend.exe'),
      go: path.join(process.resourcesPath, 'go-core', 'aibs_engine.exe')
    };
  }
  return null; // dev mode — backend started manually
}

// ---------------------------------------------------------------------------
// Port availability probe
// ---------------------------------------------------------------------------
function probePort(host, port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(400);
    socket
      .on('connect',  () => { socket.destroy(); resolve(true);  })
      .on('error',    () => { socket.destroy(); resolve(false); })
      .on('timeout',  () => { socket.destroy(); resolve(false); })
      .connect(port, host);
  });
}

async function waitForBackend(host, port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const ready = await probePort(host, port);
    if (ready) return true;
    await new Promise(r => setTimeout(r, PROBE_INTERVAL));
  }
  return false;
}

// ---------------------------------------------------------------------------
// Backend process handles
// ---------------------------------------------------------------------------
let backendProcesses = [];

async function spawnEcosystem() {
  const paths = resolveBackendPaths();
  if (!paths) {
    console.log('[Main] Dev mode — skipping ecosystem spawn.');
    return;
  }

  const services = [
    { name: 'Python Backend', path: paths.python, port: 8080, args: [] },
    { name: 'Go Gateway', path: paths.go, port: 8000, args: [] }
  ];

  for (const svc of services) {
    if (!fs.existsSync(svc.path)) {
      console.warn(`[Main] Warning: ${svc.name} not found at ${svc.path}`);
      continue;
    }

    const isAlreadyRunning = await probePort(BACKEND_HOST, svc.port);
    if (isAlreadyRunning) {
      console.log(`[Main] ${svc.name} is already active on port ${svc.port} (managed externally). Skipping spawn.`);
      continue;
    }

    console.log(`[Main] Spawning ${svc.name}: ${svc.path}`);
    const proc = spawn(svc.path, svc.args, {
      detached: false,      // keep it as a child so it dies with Electron
      stdio:    'ignore',   // do not pipe — avoids buffer deadlocks
      windowsHide: true,    // no console window visible to the end-user
      cwd: path.dirname(svc.path),
    });

    proc.on('error', (err) => {
      console.error(`[Main] ${svc.name} spawn error:`, err);
    });

    proc.on('exit', (code, signal) => {
      console.log(`[Main] ${svc.name} exited — code: ${code}, signal: ${signal}`);
    });

    backendProcesses.push(proc);
  }
}

function killEcosystem() {
  console.log(`[Main] Shutting down ${backendProcesses.length} backend processes...`);
  backendProcesses.forEach(proc => {
    try {
      if (proc && !proc.killed) {
        if (process.platform === 'win32') {
          spawn('taskkill', ['/pid', proc.pid, '/f', '/t'], { stdio: 'ignore' });
        } else {
          proc.kill('SIGTERM');
          setTimeout(() => {
            if (proc && !proc.killed) {
              proc.kill('SIGKILL');
            }
          }, 3000);
        }
      }
    } catch (e) {
      console.warn('[Main] Error killing process:', e.message);
    }
  });
  backendProcesses = [];
}

const LOCAL_TRUST_STATE_PATH = path.join(app.getPath('userData'), 'aibs-local-trust.json');

function readLocalTrustState() {
  try {
    const raw = fs.readFileSync(LOCAL_TRUST_STATE_PATH, 'utf8');
    const parsed = JSON.parse(raw);
    return {
      enabled: !!parsed.enabled,
      allowedUsers: Array.isArray(parsed.allowedUsers) ? parsed.allowedUsers.filter(Boolean).map(String) : [],
      updatedAt: parsed.updatedAt || null,
    };
  } catch (err) {
    return { enabled: false, allowedUsers: [], updatedAt: null };
  }
}

function writeLocalTrustState(nextState) {
  const state = {
    enabled: !!nextState.enabled,
    allowedUsers: Array.isArray(nextState.allowedUsers) ? nextState.allowedUsers.filter(Boolean).map(String) : [],
    updatedAt: new Date().toISOString(),
  };
  fs.writeFileSync(LOCAL_TRUST_STATE_PATH, JSON.stringify(state, null, 2));
  return state;
}

function applyLocalTrustEnvironment(state = readLocalTrustState()) {
  const enabled = !!state.enabled;
  process.env.AI_BS_LOCAL_TRUST_MODE = enabled ? '1' : '0';
  process.env.AI_BS_ALLOW_DESTRUCTIVE_ACTIONS = enabled ? '1' : '0';
  const allowedUsers = Array.isArray(state.allowedUsers) ? state.allowedUsers.filter(Boolean).join(',') : '';
  if (allowedUsers) {
    process.env.AI_BS_LOCAL_ALLOWED_USERS = allowedUsers;
  } else {
    delete process.env.AI_BS_LOCAL_ALLOWED_USERS;
  }
  return { ...state, enabled };
}

async function fetchJsonWithLocalToken(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = process.env.AI_BS_LOCAL_TOKEN;
  if (token) headers['x-local-token'] = token;
  const userEmail = headers['x-local-user-email'] || process.env.AI_BS_LOCAL_USER_EMAIL;
  if (userEmail) headers['x-local-user-email'] = userEmail;
  const response = await fetch(url, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.detail || payload.error || 'Local automation request failed';
    throw new Error(message);
  }
  return payload;
}

ipcMain.handle('aibs:local-mode:get', async () => {
  return readLocalTrustState();
});

ipcMain.handle('aibs:local-mode:set', async (_event, nextState) => {
  const normalized = writeLocalTrustState({
    enabled: !!nextState?.enabled,
    allowedUsers: Array.isArray(nextState?.allowedUsers) ? nextState.allowedUsers : []
  });
  applyLocalTrustEnvironment(normalized);
  return normalized;
});

ipcMain.handle('aibs:automation:list-jobs', async () => {
  return fetchJsonWithLocalToken(`${BACKEND_BASE_URL}/api/v1/jobs`);
});

ipcMain.handle('aibs:automation:run-job', async (_event, payload) => {
  const body = payload || {};
  const headers = { 'Content-Type': 'application/json' };
  const userEmail = body.user_email || process.env.AI_BS_LOCAL_USER_EMAIL;
  if (userEmail) headers['x-local-user-email'] = userEmail;
  return fetchJsonWithLocalToken(`${BACKEND_BASE_URL}/api/v1/jobs`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body)
  });
});

ipcMain.handle('aibs:automation:get-job', async (_event, jobId) => {
  return fetchJsonWithLocalToken(`${BACKEND_BASE_URL}/api/v1/jobs/${jobId}`);
});

ipcMain.handle('aibs:automation:cancel-job', async (_event, jobId) => {
  return fetchJsonWithLocalToken(`${BACKEND_BASE_URL}/api/v1/jobs/${jobId}/cancel`, {
    method: 'POST'
  });
});

// ---------------------------------------------------------------------------
// Browser window
// ---------------------------------------------------------------------------
let mainWindow = null;

async function createWindow() {
  const win = new BrowserWindow({
    width:  1440,
    height: 900,
    minWidth:  1024,
    minHeight: 768,
    title: 'AI-BS Matrix',
    backgroundColor: '#0d0d0f',
    webPreferences: {
      nodeIntegration:  false,          // security: keep Node out of renderer
      contextIsolation: true,
      sandbox:          false,
      preload:          path.join(__dirname, 'preload.cjs'),
    },
  });

  mainWindow = win;

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.includes('accounts.google.com') || url.includes('firebaseapp.com')) {
      return {
        action: 'allow',
        overrideBrowserWindowOptions: {
          autoHideMenuBar: true,
          webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
          }
        }
      };
    }
    shell.openExternal(url);
    return { action: 'deny' };
  });

  win.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.error(`[Main] Failed to load ${validatedURL}: ${errorDescription} (${errorCode})`);
  });

  // Remove default menu bar in production
  if (app.isPackaged) win.setMenuBarVisibility(false);

  if (!app.isPackaged) {
    const isViteLive = await probePort('127.0.0.1', 5173);
    if (isViteLive || process.env.NODE_ENV === 'development') {
      console.log('[Main] Connected to live Vite HMR server at http://127.0.0.1:5173');
      win.loadURL('http://127.0.0.1:5173');
      win.webContents.openDevTools();
      return;
    }
  }

  // Production or Standalone: serve dist over local http server on http://127.0.0.1:5173
  const distPath = path.join(__dirname, '..', 'dist');
  startLocalUiServer(distPath, 5173).then((port) => {
    if (win) {
      win.loadURL(`http://127.0.0.1:${port}`);
    }
  });
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(async () => {
  // Allow embedded cloud dashboards, overlays, and webviews without X-Frame-Options / CSP block
  if (session && session.defaultSession) {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      const responseHeaders = { ...details.responseHeaders };
      delete responseHeaders['x-frame-options'];
      delete responseHeaders['X-Frame-Options'];
      delete responseHeaders['Content-Security-Policy'];
      callback({ cancel: false, responseHeaders });
    });

    // Fix Screen Capture (NotSupportedError) in Electron
    session.defaultSession.setDisplayMediaRequestHandler((request, callback) => {
      desktopCapturer.getSources({ types: ['screen', 'window'] }).then((sources) => {
        // Automatically grant access to the primary screen to prevent NotSupportedError
        const screenSource = sources.find(s => s.id.startsWith('screen')) || sources[0];
        if (screenSource) {
          callback({ video: screenSource, audio: 'loopback' });
        } else {
          callback();
        }
      }).catch(err => {
        console.error('[Main] Display media request failed:', err);
        callback();
      });
    });
  }

  applyLocalTrustEnvironment(readLocalTrustState());

  await spawnEcosystem();

  // In packaged mode, wait for the backend to accept connections
  if (app.isPackaged) {
    console.log(`[Main] Waiting for backend on ${BACKEND_HOST}:${BACKEND_PORT}...`);
    const ready = await waitForBackend(BACKEND_HOST, BACKEND_PORT, PROBE_TIMEOUT);
    if (!ready) {
      dialog.showErrorBox(
        'AI-BS Matrix — Startup Error',
        `The backend server failed to start within ${PROBE_TIMEOUT / 1000}s.\n\n` +
        'Please try restarting the application. If the problem persists, ' +
        'check that port 8000 is not blocked by another application.'
      );
      app.quit();
      return;
    }
    console.log('[Main] Backend is ready.');
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  killEcosystem();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  killEcosystem();
});

// Catch unhandled renderer crashes
app.on('render-process-gone', (_event, _webContents, details) => {
  console.error('[Main] Renderer process gone:', details.reason);
});

// ---------------------------------------------------------------------------
// App-Level Downloader / In-Place Updater Subsystem
// ---------------------------------------------------------------------------
const REMOTE_MANIFEST_URL = 'https://ai-bs-dashboard.web.app/updates/version.json';
const LOCAL_FALLBACK_MANIFEST = path.join(__dirname, '..', 'public', 'updates', 'version.json');

function compareVersions(v1, v2) {
  const parse = (v) => (v || '0').replace(/^v/, '').split('.').map(n => parseInt(n, 10) || 0);
  const p1 = parse(v1);
  const p2 = parse(v2);
  for (let i = 0; i < Math.max(p1.length, p2.length); i++) {
    const n1 = p1[i] || 0;
    const n2 = p2[i] || 0;
    if (n1 > n2) return 1;
    if (n1 < n2) return -1;
  }
  return 0;
}

function fetchJson(url, timeoutMs = 6000) {
  return new Promise((resolve, reject) => {
    try {
      const u = new URL(url);
      const client = u.protocol === 'https:' ? https : http;
      const req = client.get(url, { timeout: timeoutMs }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          fetchJson(res.headers.location, timeoutMs).then(resolve).catch(reject);
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP status ${res.statusCode}`));
          return;
        }
        let body = '';
        res.setEncoding('utf8');
        res.on('data', chunk => { body += chunk; });
        res.on('end', () => {
          try {
            resolve(JSON.parse(body));
          } catch (err) {
            reject(err);
          }
        });
      });
      req.on('error', reject);
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timed out'));
      });
    } catch (e) {
      reject(e);
    }
  });
}

function resolveUpdaterStub() {
  const candidates = [
    path.join(process.resourcesPath, 'updater', 'aibs_updater.exe'),
    path.join(process.resourcesPath, 'aibs_updater.exe'),
    path.join(path.dirname(app.getPath('exe')), 'aibs_updater.exe'),
    path.join(__dirname, '..', 'desktop-build', 'win-unpacked', 'aibs_updater.exe'),
    path.join(__dirname, '..', '..', 'go-core', 'aibs_updater.exe'),
    path.join(process.cwd(), 'go-core', 'aibs_updater.exe'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

function downloadUpdateFile(urlToUse, destZip) {
  return new Promise((resolve, reject) => {
    try {
      const u = new URL(urlToUse);
      const client = u.protocol === 'https:' ? https : http;
      const fileStream = fs.createWriteStream(destZip);
      let downloadedBytes = 0;

      const req = client.get(urlToUse, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          fileStream.close();
          fs.unlink(destZip, () => {});
          return resolve(downloadUpdateFile(res.headers.location, destZip));
        }

        if (res.statusCode !== 200) {
          fileStream.close();
          fs.unlink(destZip, () => {});
          return reject(new Error(`Download failed with status ${res.statusCode}`));
        }

        const totalBytes = parseInt(res.headers['content-length'] || '0', 10);

        res.on('data', (chunk) => {
          downloadedBytes += chunk.length;
          fileStream.write(chunk);
          const percent = totalBytes > 0 ? (downloadedBytes / totalBytes) * 100 : 0;
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('aibs:updater:progress', {
              percent: Math.round(percent * 10) / 10,
              downloadedBytes,
              totalBytes
            });
          }
        });

        res.on('end', () => {
          fileStream.end(() => {
            console.log(`[Updater] Download complete: ${downloadedBytes} bytes written to ${destZip}`);
            if (mainWindow && !mainWindow.isDestroyed()) {
              mainWindow.webContents.send('aibs:updater:status', 'downloaded');
            }
            resolve({ success: true, path: destZip, sizeBytes: downloadedBytes });
          });
        });
      });

      req.on('error', (err) => {
        fileStream.close();
        fs.unlink(destZip, () => {});
        reject(err);
      });
    } catch (err) {
      reject(err);
    }
  });
}

// IPC Handlers
ipcMain.handle('aibs:updater:get-version', () => {
  return app.getVersion();
});

ipcMain.handle('aibs:updater:check', async () => {
  const currentVersion = app.getVersion();
  let manifest = null;

  try {
    manifest = await fetchJson(REMOTE_MANIFEST_URL, 5000);
  } catch (err) {
    console.warn('[Updater] Remote manifest fetch failed:', err.message);
    try {
      manifest = await fetchJson('http://127.0.0.1:8080/api/v1/updater/check', 3000);
      if (manifest && manifest.manifest) {
        manifest = manifest.manifest;
      }
    } catch (e) {
      if (fs.existsSync(LOCAL_FALLBACK_MANIFEST)) {
        try {
          manifest = JSON.parse(fs.readFileSync(LOCAL_FALLBACK_MANIFEST, 'utf8'));
        } catch (_) {}
      }
    }
  }

  if (!manifest || !manifest.version) {
    return {
      updateAvailable: false,
      currentVersion,
      latestVersion: currentVersion,
      message: 'Could not fetch update manifest.'
    };
  }

  const isUpdate = compareVersions(manifest.version, currentVersion) > 0;
  return {
    updateAvailable: isUpdate,
    currentVersion,
    latestVersion: manifest.version,
    releaseNotes: manifest.releaseNotes || 'Maintenance and feature update.',
    releaseDate: manifest.releaseDate || '',
    downloadUrl: manifest.downloadUrl || '',
    fallbackUrl: manifest.fallbackUrl || '',
    sha256: manifest.sha256 || '',
    sizeBytes: manifest.sizeBytes || 0,
    files: manifest.files || []
  };
});

ipcMain.handle('aibs:updater:download', async (_event, downloadUrl) => {
  const tempDir = path.join(os.tmpdir(), 'aibs_update');
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
  }
  const destZip = path.join(tempDir, 'aibs_update_payload.zip');
  const urlToUse = downloadUrl || 'https://ai-bs-dashboard.web.app/updates/aibs_update_payload.zip';
  console.log(`[Updater] Downloading payload from ${urlToUse} to ${destZip}`);
  return await downloadUpdateFile(urlToUse, destZip);
});

ipcMain.handle('aibs:updater:apply', async () => {
  const updaterStub = resolveUpdaterStub();
  if (!updaterStub || !fs.existsSync(updaterStub)) {
    throw new Error('aibs_updater.exe stub binary not found on system.');
  }

  const tempDir = path.join(os.tmpdir(), 'aibs_update');
  const tempUpdater = path.join(tempDir, 'aibs_updater.exe');
  const payloadZip = path.join(tempDir, 'aibs_update_payload.zip');

  if (!fs.existsSync(payloadZip)) {
    throw new Error(`Update payload not found at ${payloadZip}`);
  }

  try {
    fs.copyFileSync(updaterStub, tempUpdater);
  } catch (err) {
    console.error('[Updater] Failed to copy updater stub to temp dir:', err);
  }

  const targetDir = app.isPackaged
    ? path.dirname(app.getPath('exe'))
    : path.resolve(__dirname, '..', 'desktop-build', 'win-unpacked');

  const exeName = app.isPackaged
    ? path.basename(app.getPath('exe'))
    : 'AI-BS Sovereign Studio.exe';

  const currentPid = process.pid;

  console.log('[Updater] Launching detached updater stub:');
  console.log(`  Stub: ${tempUpdater}`);
  console.log(`  Target: ${targetDir}`);
  console.log(`  Payload: ${payloadZip}`);
  console.log(`  PID: ${currentPid}`);
  console.log(`  Exe: ${exeName}`);

  const child = spawn(tempUpdater, [
    '-target-dir', targetDir,
    '-payload-zip', payloadZip,
    '-parent-pid', String(currentPid),
    '-executable', exeName,
    '-relaunch=true',
    '-backup=true'
  ], {
    detached: true,
    stdio: 'ignore',
    windowsHide: false
  });
  child.unref();

  setTimeout(() => {
    killEcosystem();
    app.exit(0);
  }, 500);

  return { success: true };
});

