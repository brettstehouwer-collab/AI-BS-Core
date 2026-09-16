/**
 * frontend/electron/preload.cjs
 * Exposes secure, context-isolated updater and bridge APIs to the React renderer.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('aibsUpdater', {
  checkForUpdates: () => ipcRenderer.invoke('aibs:updater:check'),
  downloadUpdate: (downloadUrl) => ipcRenderer.invoke('aibs:updater:download', downloadUrl),
  applyUpdate: () => ipcRenderer.invoke('aibs:updater:apply'),
  getVersion: () => ipcRenderer.invoke('aibs:updater:get-version'),
  onProgress: (callback) => {
    const listener = (_event, progress) => callback(progress);
    ipcRenderer.on('aibs:updater:progress', listener);
    return () => ipcRenderer.removeListener('aibs:updater:progress', listener);
  },
  onStatus: (callback) => {
    const listener = (_event, status) => callback(status);
    ipcRenderer.on('aibs:updater:status', listener);
    return () => ipcRenderer.removeListener('aibs:updater:status', listener);
  }
});

contextBridge.exposeInMainWorld('aibsAutomation', {
  listJobs: () => ipcRenderer.invoke('aibs:automation:list-jobs'),
  runJob: (payload) => ipcRenderer.invoke('aibs:automation:run-job', payload),
  getJob: (jobId) => ipcRenderer.invoke('aibs:automation:get-job', jobId),
  cancelJob: (jobId) => ipcRenderer.invoke('aibs:automation:cancel-job', jobId),
});
