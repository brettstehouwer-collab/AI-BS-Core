import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

// Custom APIs for renderer
const api = {
  sendDaemonCommand: (command: any) => ipcRenderer.send('send-daemon-command', command),
  onDaemonMessage: (callback: (data: any) => void) => {
    ipcRenderer.removeAllListeners('daemon-message')
    ipcRenderer.on('daemon-message', (_event, value) => callback(value))
  },
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  maximizeWindow: () => ipcRenderer.send('window-maximize'),
  closeWindow: () => ipcRenderer.send('window-close'),
  isWindowMaximized: () => ipcRenderer.invoke('is-window-maximized'),
  openExternal: (url: string) => ipcRenderer.send('open-external', url)
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore
  window.electron = electronAPI
  // @ts-ignore
  window.api = api
}
