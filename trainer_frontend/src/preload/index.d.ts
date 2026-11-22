import { ElectronAPI } from '@electron-toolkit/preload'

declare global {
  interface Window {
    electron: ElectronAPI
    api: {
      sendDaemonCommand: (command: any) => void
      onDaemonMessage: (callback: (data: any) => void) => void
      minimizeWindow: () => void
      maximizeWindow: () => void
      closeWindow: () => void
      isWindowMaximized: () => Promise<boolean>
      openExternal: (url: string) => void
    }
  }
}
