import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import net from 'net';
import http from 'http';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let backendProc = null;
let mainWindow = null;

function spawnBackend() {
  const pythonExe = app.isPackaged 
    ? path.join(process.resourcesPath, 'pyppeteer_env', 'Scripts', 'python.exe')
    : path.join(__dirname, '..', '..', 'pyppeteer_env', 'Scripts', 'python.exe');
    
  const scriptPath = app.isPackaged 
    ? path.join(process.resourcesPath, 'backend', 'aibs_broadcast_daemon.py')
    : path.join(__dirname, '..', '..', 'backend', 'aibs_broadcast_daemon.py');

  if (!fs.existsSync(pythonExe)) {
    console.error(`[Main] Missing python env: ${pythonExe}`);
    return;
  }
  
  console.log(`[Main] Spawning broadcast daemon: ${scriptPath}`);
  backendProc = spawn(pythonExe, [scriptPath], {
    detached: false,
    stdio: 'ignore',
    windowsHide: true,
    cwd: path.dirname(scriptPath)
  });

  backendProc.on('error', (err) => console.error(`[Main] Daemon spawn error:`, err));
  backendProc.on('exit', (code, signal) => console.log(`[Main] Daemon exited — code: ${code}, signal: ${signal}`));
}

function killBackend() {
  if (backendProc && !backendProc.killed) {
    try {
      backendProc.kill('SIGTERM');
      setTimeout(() => { if (backendProc && !backendProc.killed) backendProc.kill('SIGKILL'); }, 2000);
    } catch(e) {}
  }
}

function startLocalUiServer(distPath, preferredPort = 5174) {
  return new Promise((resolve) => {
    const mimeTypes = {
      '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
      '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
      '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.woff2': 'font/woff2'
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
          res.writeHead(200, { 'Content-Type': contentType });
          res.end(content);
        }
      });
    });

    server.listen(preferredPort, '127.0.0.1', () => resolve(preferredPort))
          .on('error', () => resolve(4174));
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    title: 'AI-BS Broadcast Studio',
    icon: path.join(__dirname, '..', 'build', 'icon.ico'),
    backgroundColor: '#121212',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
  });

  mainWindow = win;

  if (app.isPackaged) win.setMenuBarVisibility(false);

  // Universal Localhost DevTools & Hot-Reload Keyboard Bindings
  win.webContents.on('before-input-event', (event, input) => {
    // F12 or Ctrl+Shift+I to toggle DevTools anytime
    if (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i')) {
      win.webContents.toggleDevTools();
      event.preventDefault();
    }
    // F5 or Ctrl+R to reload
    if (input.key === 'F5' || (input.control && input.key.toLowerCase() === 'r')) {
      win.webContents.reload();
      event.preventDefault();
    }
    // Ctrl+Shift+R to hard reload
    if (input.control && input.shift && input.key.toLowerCase() === 'r') {
      win.webContents.reloadIgnoringCache();
      event.preventDefault();
    }
  });

  if (!app.isPackaged && process.env.NODE_ENV === 'development') {
    win.loadURL('http://localhost:5174');
    win.webContents.openDevTools();
  } else {
    const distPath = path.join(__dirname, '..', 'dist');
    startLocalUiServer(distPath, 5174).then((port) => {
      if (win) win.loadURL(`http://127.0.0.1:${port}`);
    });
  }
}

// DevTools IPC Handlers
ipcMain.on('open-devtools', () => {
  if (mainWindow) mainWindow.webContents.openDevTools();
});

ipcMain.on('toggle-devtools', () => {
  if (mainWindow) mainWindow.webContents.toggleDevTools();
});

ipcMain.on('reload-window', () => {
  if (mainWindow) mainWindow.webContents.reload();
});

let autoUpdater = null;
try {
  const pkg = await import('electron-updater');
  autoUpdater = pkg?.autoUpdater || pkg?.default?.autoUpdater;
} catch (e) {}

app.whenReady().then(() => {
  spawnBackend();
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
  
  if (app.isPackaged && autoUpdater) {
    try {
      autoUpdater.checkForUpdatesAndNotify();
    } catch (e) {}
  }
});

app.on('window-all-closed', () => {
  killBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => killBackend());
