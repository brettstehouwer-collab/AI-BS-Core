const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const http = require('http');
const fs = require('fs');
const { autoUpdater } = require('electron-updater');

const { dialog } = require('electron');

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

app.commandLine.appendSwitch('ignore-certificate-errors');
app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('ignore-gpu-blocklist');

autoUpdater.on('update-available', () => {
  console.log('[AutoUpdater] Update available.');
});
autoUpdater.on('update-downloaded', () => {
  console.log('[AutoUpdater] Update downloaded. Prompting user...');
  dialog.showMessageBox({
    type: 'info',
    title: 'Update Ready',
    message: 'A new version of AI-BS is available and has been downloaded. Would you like to restart and install the update now?',
    buttons: ['Restart and Install', 'Later']
  }).then((result) => {
    if (result.response === 0) {
      autoUpdater.quitAndInstall();
    }
  });
});

let mainWindow;
let backendProcess = null;
let ollamaProcess = null;
let comfyProcess = null;
let agentProcesses = [];

// ─── Ollama ───────────────────────────────────────────────
function startOllama() {
  const client = new net.Socket();
  client.setTimeout(1000);
  client.once('connect', () => {
    console.log('[Ollama] Already running on port 11435.');
    client.destroy();
  }).once('error', () => {
    console.log('[Ollama] Not running — starting ollama serve...');
    ollamaProcess = spawn('ollama', ['serve'], {
      detached: true,
      stdio: 'ignore',
      shell: true,
      windowsHide: true,
      env: { ...process.env, OLLAMA_IGPU_ENABLE: '1' }
    });
    ollamaProcess.on('error', (err) => {
      console.warn('[Ollama] Could not start:', err.message);
    });
  });
  client.connect(11435, '127.0.0.1');
}

// ─── ComfyUI ──────────────────────────────────────────────
function startComfyUI() {
  const fs = require('fs');
  const comfyDirCandidates = [
    'C:\\AI-BS\\ComfyUI',
    'C:\\Users\\footb\\ComfyUI'
  ];
  let comfyDir = comfyDirCandidates.find(d => fs.existsSync(path.join(d, 'main.py'))) || comfyDirCandidates[0];
  const comfyPython = path.join(comfyDir, 'venv', 'Scripts', 'python.exe');

  if (!fs.existsSync(comfyPython)) {
    console.warn('[ComfyUI] venv not found — skipping. Run start_comfyui.bat to set up.');
    return;
  }

  const client = new net.Socket();
  client.setTimeout(1000);
  client.once('connect', () => {
    console.log('[ComfyUI] Already running on port 8189.');
    client.destroy();
  }).once('error', () => {
    console.log('[ComfyUI] Starting on RTX 4090 (port 8189)...');
    comfyProcess = spawn(comfyPython, ['main.py', '--listen', '127.0.0.1', '--port', '8189', '--preview-method', 'auto'], {
      cwd: comfyDir,
      detached: true,
      stdio: 'ignore',
      windowsHide: true
    });
    comfyProcess.on('error', (err) => {
      console.warn('[ComfyUI] Could not start:', err.message);
    });
  });
  client.connect(8189, '127.0.0.1');
}

// ─── FastAPI Backend & Matrix Daemons ───────────────────────
function startBackend() {
  console.log('[Backend] Checking port 8080...');
  const client = new net.Socket();
  client.setTimeout(1000);
  client.once('connect', () => {
    console.log('[Backend] Already running on port 8080.');
    client.destroy();
  }).once('error', () => {
    console.log('[Backend] Not running — booting Matrix Daemons...');
    
    const fs = require('fs');
    
    if (app.isPackaged) {
      const backendPath = path.join(process.resourcesPath, 'aibs_backend.exe');
      console.log('[Backend] Spawning packaged backend from:', backendPath);
      backendProcess = spawn(backendPath, [], { 
        detached: false,
        windowsHide: true
      });
    } else {
      const localExePath = path.join(__dirname, 'extra_resources', 'aibs_backend.exe');
      if (fs.existsSync(localExePath)) {
        console.log('[Backend] Spawning local dev backend from:', localExePath);
        backendProcess = spawn(localExePath, [], { 
          detached: false,
          windowsHide: true
        });
      } else {
        const matrixBatPath = 'C:\\AI-BS\\backend\\Launch_Headless_Daemons.bat';
        if (fs.existsSync(matrixBatPath)) {
          console.log('[Backend] Launching Headless Daemons from:', matrixBatPath);
          backendProcess = spawn('cmd.exe', ['/c', matrixBatPath], {
            cwd: 'C:\\AI-BS\\backend',
            detached: true,
            stdio: 'ignore',
            windowsHide: true
          });
          backendProcess.unref();
        } else {
          console.warn(`[Backend] Could not find ${matrixBatPath}.`);
        }
      }
    }
  });
  client.connect(8080, '127.0.0.1');
}

// ─── Wait for backend port then load UI ───────────────────
function waitForBackend(callback, attempts = 0) {
  if (attempts > 60) {
    console.warn('[Backend] Timed out waiting for port 8080. Loading UI anyway.');
    callback();
    return;
  }
  const client = new net.Socket();
  client.setTimeout(500);
  client.once('connect', () => {
    console.log('[Backend] Port 8080 is ready.');
    client.destroy();
    callback();
  }).once('error', () => {
    client.destroy();
    setTimeout(() => waitForBackend(callback, attempts + 1), 500);
  });
  client.connect(8080, '127.0.0.1');
}

// ─── Main Window ─────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    backgroundColor: '#0f1115',
    title: "Brett's Local AI Agent",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
      webviewTag: true
    }
  });

  const { shell, session, desktopCapturer } = require('electron');

  if (session.defaultSession.setDisplayMediaRequestHandler) {
    session.defaultSession.setDisplayMediaRequestHandler((request, callback) => {
      desktopCapturer.getSources({ types: ['window', 'screen'] }).then((sources) => {
        const windowSources = sources.filter(s => s.id && s.id.startsWith('window:'));
        const codWindow = windowSources.find(s => s.name.toLowerCase().includes('call of duty') || s.name.toLowerCase().includes('cod'));
        const otherWindow = windowSources.find(s => !s.name.includes('AI-BS') && !s.name.includes('Electron') && !s.name.includes('Visual Studio'));
        const chosenSource = codWindow || otherWindow || sources[0];
        console.log('[Electron] Selected Capture Source:', chosenSource ? chosenSource.name : 'None');
        callback({ video: chosenSource });
      }).catch((err) => {
        console.error('[Electron] Display media error:', err);
      });
    });
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
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

  const template = [
    {
      label: 'File',
      submenu: [
        { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { role: 'close' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About AI-BS',
          click: async () => {
            const { dialog } = require('electron');
            dialog.showMessageBox({
              type: 'info',
              title: 'About AI-BS',
              message: 'Brett Local AI Agent\nVersion 1.0.0\nPowered by Electron & React.'
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Browser Console] ${message}`);
  });

  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

  if (isDev) {
    // In dev, poll for Vite dev server and backend
    mainWindow.loadURL('http://localhost:5173');
  } else {
    // Wait for backend to be ready, then start local UI server on http://127.0.0.1:5173
    const distPath = path.join(__dirname, 'dist');
    waitForBackend(async () => {
      const port = await startLocalUiServer(distPath, 5173);
      if (mainWindow) {
        mainWindow.loadURL(`http://127.0.0.1:${port}`);
      }
    });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function checkForLocalUpdates() {
  const fs = require('fs');
  const updatesDir = 'G:\\Stehouwer_Server\\Updates';
  const latestYmlPath = path.join(updatesDir, 'latest.yml');
  
  if (!fs.existsSync(latestYmlPath)) return;
  
  try {
    const content = fs.readFileSync(latestYmlPath, 'utf8');
    const exeMatch = content.match(/path:\s*(.+)/);
    
    if (exeMatch) {
      const exeName = exeMatch[1].trim();
      const exePath = path.join(updatesDir, exeName);
      
      if (!fs.existsSync(exePath)) return;
      
      const newExeTime = fs.statSync(exePath).mtimeMs;
      
      // Track the last installed version's timestamp in AppData
      const trackerPath = path.join(app.getPath('userData'), 'last_installer_time.txt');
      let lastExeTime = 0;
      
      if (fs.existsSync(trackerPath)) {
        lastExeTime = parseFloat(fs.readFileSync(trackerPath, 'utf8'));
      } else {
        // First-time launch after install: record current installer timestamp and proceed silently
        fs.writeFileSync(trackerPath, newExeTime.toString(), 'utf8');
        return;
      }
      
      // If the installer file has been modified/rebuilt since we last updated
      if (newExeTime > lastExeTime) {
        dialog.showMessageBox({
          type: 'info',
          title: 'Update Detected',
          message: `A freshly rebuilt version of AI-BS was detected in your Updates folder!\n\nWould you like to close the app and install the new executable now?`,
          buttons: ['Yes, Install Update', 'No, Remind Me Later']
        }).then((result) => {
          if (result.response === 0) {
            // Save the timestamp so we don't prompt again after installation finishes
            fs.writeFileSync(trackerPath, newExeTime.toString(), 'utf8');
            
            console.log('[AutoUpdater] Spawning local installer:', exePath);
            const { spawn } = require('child_process');
            const installer = spawn(exePath, [], {
              detached: true,
              stdio: 'ignore'
            });
            installer.unref();
            app.quit();
          }
        });
      }
    }
  } catch (err) {
    console.error('[AutoUpdater] Error checking for local updates:', err);
  }
}

// ─── App Lifecycle ────────────────────────────────────────
app.whenReady().then(() => {
  const { session } = require('electron');
  
  // Automatically grant all permissions to localhost and local files without prompting
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const url = webContents.getURL();
    if (url.startsWith('http://localhost:5173') || url.startsWith('file://')) {
      callback(true);
    } else {
      // For the Ghost Browser (which visits external sites), we can allow or prompt
      // For now, allow basic permissions for the ghost browser as well to prevent popups
      callback(true);
    }
  });
  
  session.defaultSession.setPermissionCheckHandler((webContents, permission, requestingOrigin, details) => {
    if (requestingOrigin.startsWith('http://localhost:5173') || requestingOrigin.startsWith('file://')) {
      return true;
    }
    return true; // Allow for Ghost Browser external sites too
  });

  checkForLocalUpdates();
  
  startOllama();
  startComfyUI();
  startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  if (backendProcess) backendProcess.kill();
  if (ollamaProcess) ollamaProcess.kill();
  if (comfyProcess) comfyProcess.kill();
  agentProcesses.forEach(p => {
      try { p.kill() } catch (e) {}
  });
});
