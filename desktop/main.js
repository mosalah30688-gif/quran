const { app, BrowserWindow, dialog, shell } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const { startServer } = require('./server');

let win = null;
let port = 0;

function createWindow() {
  win = new BrowserWindow({
    width: 1200,
    height: 860,
    minWidth: 360,
    minHeight: 600,
    title: 'المصحف',
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  const origin = `http://127.0.0.1:${port}`;
  win.loadURL(`${origin}/index.html`);
  // الروابط الخارجية تفتح في المتصفح، والبرنامج يفضل داخل نفسه
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (e, url) => {
    if (!url.startsWith(origin + '/')) { e.preventDefault(); shell.openExternal(url); }
  });
  win.on('closed', () => { win = null; });
}

// التحديث التلقائي من GitHub Releases (يشتغل مع نسخة AppImage المبنية فقط)
function setupUpdates() {
  if (!app.isPackaged) return;
  autoUpdater.autoDownload = true;
  autoUpdater.on('update-downloaded', (info) => {
    dialog.showMessageBox(win || undefined, {
      type: 'info',
      buttons: ['أعد التشغيل الآن', 'لاحقاً'],
      defaultId: 0,
      message: `تم تنزيل النسخة ${info.version}. أعد تشغيل البرنامج لتطبيقها.`,
    }).then(({ response }) => { if (response === 0) autoUpdater.quitAndInstall(); });
  });
  autoUpdater.on('error', () => {});
  autoUpdater.checkForUpdates().catch(() => {});
}

app.whenReady().then(async () => {
  const srv = await startServer(path.join(__dirname, 'app'));
  port = srv.address().port;
  createWindow();
  setupUpdates();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on('window-all-closed', () => { app.quit(); });
