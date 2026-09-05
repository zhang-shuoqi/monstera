// Monstera 桌面壳 · 主进程
//
// 职责（严格限定，不含任何前端/后端业务逻辑）：
//   1) 应用启动时自动拉起本地 FastAPI 后端（127.0.0.1:8765）
//   2) 后端就绪后加载本地主界面（index.html，file:// 协议，前端自动回退到本地 API）
//   3) 退出时结束后端进程（含 Windows 进程树），避免残留
//   4) 保证单实例运行：二次启动只聚焦已有主窗口，不拉起新后端
//   5) 预留原生能力入口：内置窗口加载外部 URL（IPC 约定，当前仅预留）
//
// index.html 与 FastAPI 后端保持原样；以后改 UI/功能仍在原文件进行，壳不需改动。
const { app, BrowserWindow, ipcMain, dialog, shell, screen, session } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = 8765;
const BACKEND_READY_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/mock`; // 轻量 JSON 就绪探针
const READY_TIMEOUT_MS = 30000; // 后端就绪最长等待时间
const READY_POLL_MS = 250;      // 就绪探测间隔

let backendProc = null;   // 后端子进程句柄
let mainWindow = null;    // 主窗口
let quitting = false;     // 是否正在主动退出

/* ==================== 路径解析 ==================== */

function projectRoot() {
  // 开发态：desktop/ 的上一级即项目根（Monstera/）
  return path.resolve(__dirname, '..');
}

function backendDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'backend')
    : path.join(projectRoot(), 'backend');
}

function indexPath() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'index.html')
    : path.join(projectRoot(), 'index.html');
}

function backendLogFile() {
  const dir = app.isPackaged ? app.getPath('logs') : backendDir();
  try { fs.mkdirSync(dir, { recursive: true }); } catch (_) { /* ignore */ }
  return path.join(dir, 'monstera-shell.log');
}

/**
 * 解析如何拉起后端。返回 { command, args[], cwd }。
 * 优先级：显式环境变量 → 打包态自包含产物（PyInstaller exe）→ 开发态 venv → 系统 python
 */
function resolveBackendLaunch() {
  const dir = backendDir();
  const mainPy = path.join(dir, 'main.py');

  // 1) 显式覆盖（调试/特殊环境）：MONSTERA_PYTHON 指定解释器，仍跑 main.py
  if (process.env.MONSTERA_PYTHON) {
    return { command: process.env.MONSTERA_PYTHON, args: [mainPy], cwd: dir };
  }

  // 2) 打包态：自包含后端（PyInstaller onedir 目录，免解压快速启动）
  if (app.isPackaged) {
    const onedir = path.join(process.resourcesPath, 'backend', 'monstera-backend');
    const exe = path.join(onedir, 'monstera-backend.exe');
    if (!fs.existsSync(exe)) {
      throw new Error('未找到打包的后端 monstera-backend.exe，安装可能不完整');
    }
    return { command: exe, args: [], cwd: onedir };
  }

  // 3) 开发态：优先后端 .venv，其次 venv，最后系统 python
  const candidates = [
    path.join(dir, '.venv', 'Scripts', 'python.exe'),
    path.join(dir, 'venv', 'Scripts', 'python.exe'),
    'python',
  ];
  for (const c of candidates) {
    if (c === 'python' || fs.existsSync(c)) {
      return { command: c, args: [mainPy], cwd: dir };
    }
  }
  throw new Error('未找到可用的 Python 解释器，无法启动后端');
}

/* ==================== 后端生命周期 ==================== */

function startBackend() {
  const { command, args, cwd } = resolveBackendLaunch();
  console.log(`[Monstera] 启动后端：${command} ${args.join(' ')} (cwd=${cwd})`);

  const logFd = fs.openSync(backendLogFile(), 'a');
  backendProc = spawn(command, args, {
    cwd,
    env: { ...process.env },
    stdio: ['ignore', logFd, logFd],
    windowsHide: true,
    detached: false,
  });

  backendProc.on('error', (err) => {
    console.error('[Monstera] 后端启动失败:', err.message);
    backendProc = null;
  });
  backendProc.on('exit', (code, signal) => {
    if (!quitting) {
      console.warn(`[Monstera] 后端意外退出 code=${code} signal=${signal}`);
    }
    backendProc = null;
  });

  return backendProc;
}

function isBackendReady() {
  return new Promise((resolve) => {
    const req = http.get(BACKEND_READY_URL, { timeout: 1500 }, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

async function waitForBackendReady() {
  const start = Date.now();
  while (Date.now() - start < READY_TIMEOUT_MS) {
    if (quitting) throw new Error('应用正在退出');
    if (backendProc === null) throw new Error('后端进程已终止，无法提供服务');
    if (await isBackendReady()) return true;
    await new Promise((r) => setTimeout(r, READY_POLL_MS));
  }
  throw new Error('后端启动超时（30 秒）');
}

/**
 * 结束后端进程。Windows 下用 taskkill /T 杀掉整个进程树，
 * 避免 uvicorn 或其它派生进程残留。
 */
function stopBackend() {
  if (!backendProc) return;
  const proc = backendProc;
  backendProc = null;
  try {
    if (process.platform === 'win32' && proc.pid) {
      spawn('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { windowsHide: true });
    } else {
      proc.kill('SIGTERM');
    }
  } catch (_) { /* ignore */ }
}

/* ==================== 窗口 ==================== */

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    show: false, // 加载完成后再显示，避免白屏
    // 无边框 + 透明：实现 Codex 式真圆角浮动窗口。四角由页面 .app 卡片裁切，
    // 页面用 body 透明 + .app 圆角承载深色表面与氛围光。
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    title: 'Monstera',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true, // 预加载脚本仅用 contextBridge/ipcRenderer，可安全开启沙箱（Electron 推荐默认）
    },
  });

  // —— 自绘标题栏配套：最大化/还原状态同步给渲染进程（用于切换按钮图标） ——
  mainWindow.on('maximize', () => {
    mainWindow.webContents.send('win:maximized-changed', true);
  });
  mainWindow.on('unmaximize', () => {
    mainWindow.webContents.send('win:maximized-changed', false);
  });

  mainWindow.on('closed', () => { mainWindow = null; });
  // 页面内 target=_blank 链接转交系统浏览器，避免在壳内打开不可控页面
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  // 主窗口只应停留在本地 file:// 页面：拦截一切远程跳转（含外部重定向/恶意链接），
  // 需要打开外部站点一律走受控内部窗口或系统浏览器，防止主界面被导航到不受控内容。
  mainWindow.webContents.on('will-navigate', (event, url) => {
    const current = mainWindow && mainWindow.webContents.getURL();
    if ((current && String(current).startsWith('file://')) && /^https?:\/\//i.test(url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  // 加载本地页面（file://），前端据此自动回退 API 到 http://127.0.0.1:8765/api
  return mainWindow.loadFile(indexPath()).then(() => {
    mainWindow.show();
    if (!app.isPackaged) {
      console.log('[Monstera] 开发模式已启动，修改前端后刷新窗口即可（Ctrl+R）。');
    }
    return mainWindow;
  });
}

async function boot() {
  try {
    // 开发态：每次启动清空渲染进程磁盘缓存。Chromium 会缓存 file:// 页面，
    // 不清缓存时修改 index.html 后打开仍是旧界面（表现为“改了没变化”）。
    if (!app.isPackaged) {
      try { await session.defaultSession.clearCache(); } catch (_) { /* ignore */ }
    }
    startBackend();       // 立即拉起后端（不等待就绪，后端与窗口并行启动）
    await createWindow(); // 本地 index.html 很快加载完成，窗口随即显示——不用等后端就绪
    // 后端是否就绪交给前端轮询；这里仅在就绪失败/超时时给出明确错误（不阻塞已显示的界面）
    waitForBackendReady().catch((err) => {
      const errMsg = err && err.message ? err.message : String(err);
      console.error('[Monstera] 后端启动失败:', errMsg);
      if (mainWindow && !mainWindow.isDestroyed()) {
        dialog.showMessageBox(mainWindow, {
          type: 'error',
          title: 'Monstera 后端启动失败',
          message: errMsg,
          detail: `日志文件位置：\n${backendLogFile()}`,
        });
      }
    });
  } catch (err) {
    console.error('[Monstera] 启动失败:', err && err.message ? err.message : err);
    dialog.showErrorBox('Monstera 启动失败', `${err && err.message ? err.message : String(err)}\n\n日志文件位置：\n${backendLogFile()}`);
    app.quit();
  }
}

/* ==================== IPC：自绘标题栏（无边框窗口控制） ==================== */

// 透明无边框窗口在 Windows 下无法原生最大化，且没有原生缩放边缘。
// 因此最大化改为"手动铺满工作区"，正常态/最大化态均需自绘标题栏与右下角缩放手柄配合。
let customMax = false;      // 是否为"自定义最大化"（铺满工作区）
let normalBounds = null;    // 进入最大化前的窗口 bounds，用于还原

function applyCustomMaximize(on) {
  if (!mainWindow) return;
  if (on && !customMax) {
    normalBounds = mainWindow.getBounds();
    const display = screen.getDisplayMatching(normalBounds);
    mainWindow.setBounds(display.workArea);
    customMax = true;
  } else if (!on && customMax) {
    if (normalBounds) mainWindow.setBounds(normalBounds);
    customMax = false;
  }
  // 派发状态，渲染进程据此切换按钮图标 / 去掉圆角外边距
  mainWindow.webContents.send('win:maximized-changed', customMax);
}

// 最小化 / 关闭：仅作用于主窗口。
ipcMain.on('win:minimize', () => { if (mainWindow) mainWindow.minimize(); });
ipcMain.on('win:close', () => { if (mainWindow) mainWindow.close(); });
ipcMain.on('win:toggle-max', () => applyCustomMaximize(!customMax));
// 初始同步：页面加载时询问当前是否最大化，用于标题栏按钮图标初始化。
ipcMain.handle('win:get-maximized', () => customMax);

// 手动缩放：Windows 下透明无边框窗口没有原生边缘缩放，由右下角手柄补足。
ipcMain.handle('win:get-size', () =>
  mainWindow ? mainWindow.getSize() : [1280, 820]
);
// 直接设置整体尺寸：{ w, h } 已含最小尺寸钳制。dragged=true 让鼠标相对刷新失真更小。
ipcMain.on('win:set-size', (_e, { w, h, dragged } = {}) => {
  if (!mainWindow) return;
  const [cw, ch] = mainWindow.getSize();
  const nextW = Math.max(960, Number.isFinite(w) ? w : cw);
  const nextH = Math.max(640, Number.isFinite(h) ? h : ch);
  mainWindow.setSize(nextW, nextH, !!dragged);
});

/* ==================== IPC：受控内部窗口（申请 / 充值等） ==================== */

// 受控内部工具窗口：在应用内打开外部 https 页面（如官方申请页 / 充值页）。
// 用普通 BrowserWindow（无 node、contextIsolation），等效一个封闭的浏览器窗口；
// 不开 webview/BrowserView，避免权限与登录兼容问题。外部 target=_blank 一律转交
// 系统浏览器，防止在工具窗口内弹出不受控页面。窗口关闭后通知主窗口，供前端刷新状态。
function createInternalWindow({ url, kind = '' }) {
  if (typeof url !== 'string' || !/^https?:\/\//i.test(url)) {
    throw new Error('仅支持 http/https 的外部 URL');
  }
  const win = new BrowserWindow({
    width: 1024,
    height: 720,
    minWidth: 620,
    minHeight: 480,
    parent: mainWindow || undefined,   // 挂在主窗口下，工具窗口行为；主窗口关闭时一并关闭
    autoHideMenuBar: true,
    title: url,
    backgroundColor: '#0A191E',
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  // 工具窗口内的新开链接/弹窗一律转交系统浏览器，不在此窗口内追加不受控页面
  win.webContents.setWindowOpenHandler(({ url: target }) => {
    if (/^https?:\/\//i.test(target)) shell.openExternal(target);
    return { action: 'deny' };
  });
  let origin = '';
  try { origin = new URL(url).origin; } catch (_) { /* ignore */ }
  let navTimer = null;
  win.on('closed', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('internal-window-closed', { url: String(url), kind });
    }
    if (navTimer) clearTimeout(navTimer);
  });
  // 加载策略：先加载过渡页（data: URL，含 preconnect 预热 + 旋转加载动画），
  // 160ms 后导航到真实 URL。过渡页会被真实页面自动替换——无需注入或移除任何遮罩，
  // 无依赖即无故障，SPA 长连接也不会卡住。
  win.loadURL(loadingPageDataUrl(origin));
  navTimer = setTimeout(() => { if (!win.isDestroyed()) win.loadURL(url); }, 160);
  return win;
}

// 过渡页：深色背景 + 旋转加载动画，内含对目标的 preconnect 预热连接。
function loadingPageDataUrl(origin) {
  const enc = String(origin || '').replace(/"/g, '&quot;');
  const html = `<!doctype html><html><head><meta charset="utf-8">
    <link rel="preconnect" href="${enc}" crossorigin>
    <style>
      html,body{margin:0;height:100%;background:#0A191E;color:#9fb6bd;
        font:400 13px/1.4 system-ui,sans-serif;
        display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
      .ring{width:34px;height:34px;border-radius:50%;
        border:3px solid rgba(232,178,62,.22);border-top-color:#E8B23E;
        animation:spin .8s linear infinite}
      @keyframes spin{to{transform:rotate(360deg)}}
    </style></head>
    <body><div class="ring"></div><div>正在加载官网…</div></body></html>`;
  return 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
}

// 通用：打开内部工具窗口。业务侧用 kind 区分用途（如 'apply' / 'recharge'）。
ipcMain.handle('open-internal-window', (_event, { url, kind } = {}) => {
  createInternalWindow({ url, kind: kind || '' });
  return true;
});

// 充值专用（受控内部窗口）：加载官方充值页
ipcMain.handle('open-recharge-window', (_event, url) => {
  createInternalWindow({ url, kind: 'recharge' });
  return true;
});

// 兼容保留：既有 openExternalUrl 行为（在壳内打开外部 URL，无主窗口挂靠）
ipcMain.handle('open-external-url', (_event, url) => {
  createInternalWindow({ url });
  return true;
});

/* ==================== 应用生命周期 ==================== */

// 单实例锁：保证用户双击多次只运行一个应用实例。
// 必须在任何后端/窗口初始化前请求——若拿不到锁，说明已有实例在运行，
// 本进程立即退出（绝不启动后端、不进入 whenReady 初始化）。
// 设置 MONSTERA_ALLOW_MULTI=1 可跳过单实例锁（默认不跳过）：便于开发/调试强开多个实例。
const allowMulti = process.env.MONSTERA_ALLOW_MULTI === '1';
const gotTheLock = allowMulti ? true : app.requestSingleInstanceLock();

function focusMainWindow() {
  if (!mainWindow) return;          // 主窗口尚未创建（仍在启动），忽略本次聚焦
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

if (!gotTheLock) {
  // 已有实例在运行：直接退出当前启动进程
  app.quit();
} else {
  // 二次启动（用户再次双击图标）：只聚焦已有主窗口，绝不拉起新的后端
  app.on('second-instance', () => {
    focusMainWindow();
  });

  app.whenReady().then(() => {
    boot();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0 && backendProc != null) {
        createWindow();
      }
    });
  });

  app.on('before-quit', () => {
    quitting = true;
    stopBackend();
  });

  app.on('window-all-closed', () => {
    // 关闭主窗口即退出整个应用（Windows 语义）；before-quit 会顺带清理后端
    app.quit();
  });
}