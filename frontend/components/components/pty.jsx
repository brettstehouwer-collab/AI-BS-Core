const pty = require('node-pty');
const os = require('os');
const { app, BrowserWindow, ipcMain } = require('electron');

const shell = 'powershell.exe';
const ptyProcess = pty.spawn(shell, ['-NoLogo', '-ExecutionPolicy', 'Bypass'], {
  name: 'xterm-color',
  cols: 80,
  rows: 30,
  cwd: 'C:\\AI-BS',
  env: process.env,
  useConpty: true
});

ipcMain.on('terminal.write', (event, data) => {
  ptyProcess.write(data);
});

ptyProcess.onData((data) => {
  mainWindow.webContents.send('terminal.incoming', data);
});