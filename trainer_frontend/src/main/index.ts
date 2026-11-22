import { app, shell, BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'
import { spawn, ChildProcess } from 'child_process'
import readline from 'readline'
import fs from 'fs'

let mainWindow: BrowserWindow | null = null
let trainerDaemon: ChildProcess | null = null

function startTrainerDaemon() {
  let executablePath = ''
  let args: string[] = []

  // Check candidates for Go native binary first
  const goCandidates = [
    join(process.resourcesPath, 'btd6_trainer_daemon.exe'),
    join(process.resourcesPath, 'resources', 'btd6_trainer_daemon.exe'),
    join(process.resourcesPath, 'app.asar.unpacked', 'resources', 'btd6_trainer_daemon.exe'),
    join(__dirname, '../../resources/btd6_trainer_daemon.exe'),
    'C:\\AI-BS\\go-core\\cmd\\btd6_trainer_daemon\\btd6_trainer_daemon.exe',
    'C:\\AI-BS\\EXE\\btd6_trainer_daemon.exe'
  ]

  for (const candidate of goCandidates) {
    if (fs.existsSync(candidate)) {
      executablePath = candidate
      args = []
      break
    }
  }

  // Fallback to Python daemon if Go binary is not present
  if (!executablePath) {
    if (app.isPackaged) {
      const pyCandidates = [
        join(process.resourcesPath, 'trainer_daemon.exe'),
        join(process.resourcesPath, 'resources', 'trainer_daemon.exe'),
        join(process.resourcesPath, 'app.asar.unpacked', 'resources', 'trainer_daemon.exe')
      ]
      for (const candidate of pyCandidates) {
        if (fs.existsSync(candidate)) {
          executablePath = candidate
          args = ['--daemon']
          break
        }
      }
    } else {
      executablePath = process.platform === 'win32' ? 'python' : 'python3'
      const scriptPath = join(__dirname, '../../../game_trainer/launch_btd6_trainer.py')
      args = ['-u', scriptPath, '--daemon']
    }
  }

  console.log('[MAIN] Spawning trainer daemon:', executablePath, args)

  trainerDaemon = spawn(executablePath, args, {
    windowsHide: true,
    stdio: ['pipe', 'pipe', 'inherit']
  })

  trainerDaemon.on('error', (err) => {
    console.error('[MAIN] Daemon spawn error:', err)
    if (mainWindow) {
      mainWindow.webContents.send('daemon-message', {
        type: 'error',
        message: `Failed to spawn trainer daemon at ${executablePath}. Error: ${err.message}`
      })
    }
  })

  if (trainerDaemon.stdout) {
    const rl = readline.createInterface({ input: trainerDaemon.stdout })
    rl.on('line', (line) => {
      try {
        const data = JSON.parse(line)
        if (mainWindow) {
          mainWindow.webContents.send('daemon-message', data)
        }
      } catch (e) {
        console.log('[DAEMON RAW]', line)
      }
    })
  }
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 780,
    minWidth: 920,
    minHeight: 640,
    show: false,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#070a12',
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // HMR for renderer base on electron-vite cli.
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.stehouwer.aibs.btd6trainer')
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  startTrainerDaemon()

  // Native Window Management IPC
  ipcMain.on('window-minimize', () => {
    mainWindow?.minimize()
  })

  ipcMain.on('window-maximize', () => {
    if (mainWindow?.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow?.maximize()
    }
  })

  ipcMain.on('window-close', () => {
    mainWindow?.close()
  })

  ipcMain.handle('is-window-maximized', () => {
    return mainWindow?.isMaximized() ?? false
  })

  ipcMain.on('open-external', (_, url: string) => {
    shell.openExternal(url)
  })

  // Handle messages from Renderer -> Go Daemon
  ipcMain.on('send-daemon-command', (_, command) => {
    if (trainerDaemon && trainerDaemon.stdin && !trainerDaemon.stdin.destroyed) {
      trainerDaemon.stdin.write(JSON.stringify(command) + '\n')
    }
  })

  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (trainerDaemon) {
    try {
      trainerDaemon.stdin?.write(JSON.stringify({ action: 'quit' }) + '\n')
    } catch (_) {}
    setTimeout(() => {
      trainerDaemon?.kill()
    }, 500)
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
