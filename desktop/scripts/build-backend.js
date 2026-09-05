// 构建自包含后端产物 monstera-backend.exe（PyInstaller）
// 输出到 desktop/build/backend/monstera-backend.exe，供 electron-builder 打包。
const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '..', '..'); // Monstera/
const BACKEND = path.join(ROOT, 'backend');
const OUT_DIR = path.join(ROOT, 'desktop', 'build', 'backend');

function findPython() {
  for (const d of ['.venv', 'venv']) {
    const p = path.join(BACKEND, d, 'Scripts', 'python.exe');
    if (fs.existsSync(p)) return p;
  }
  return process.env.MONSTERA_PYTHON || 'python';
}

function run(cmd, args, cwd) {
  const r = spawnSync(cmd, args, { cwd, stdio: 'inherit', shell: false });
  if (r.error) { console.error('[build-backend] 执行失败:', r.error.message); process.exit(1); }
  if (r.status !== 0) process.exit(r.status == null ? 1 : r.status);
}

const python = findPython();
console.log('[build-backend] 使用 Python:', python);

// 确保 PyInstaller 已安装（缺失时自动安装到该解释器环境）
const check = spawnSync(python, ['-m', 'PyInstaller', '--version'], { stdio: 'ignore' });
if (check.status !== 0) {
  console.log('[build-backend] 安装 PyInstaller ...');
  run(python, ['-m', 'pip', 'install', 'pyinstaller']);
}

fs.mkdirSync(OUT_DIR, { recursive: true });
// 清理旧的单文件产物（onedir 模式不再生成顶层 exe，避免与旧文件混在一起被 extraResources 整目录带上）
for (const stale of ['monstera-backend.exe']) {
  const p = path.join(OUT_DIR, stale);
  if (fs.existsSync(p)) fs.rmSync(p, { force: true });
}

// uvicorn 通过 importlib 动态加载 loops / protocols / lifespan，需显式声明；
// 否则冻结后运行时报 ModuleNotFoundError。
const hidden = [
  'uvicorn.logging',
  'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio',
  'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
  'uvicorn.protocols.http.h11_impl',
  'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
  'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off',
];

const args = [
  '-m', 'PyInstaller',
  '--onedir', '--noconfirm', '--clean',
  '--name', 'monstera-backend',
  '--distpath', OUT_DIR,
  '--workpath', path.join(ROOT, 'desktop', 'build', 'pyi-work'),
  '--specpath', path.join(ROOT, 'desktop', 'build'),
  '--console', // 保留控制台便于直接运行排障；Electron 侧用 windowsHide 隐藏窗口
  ...hidden.flatMap((h) => ['--hidden-import', h]),
  path.join(BACKEND, 'launcher.py'),
];

console.log('[build-backend] 构建 monstera-backend/（onedir，免解压快速启动）...');
run(python, args, BACKEND);

const exe = path.join(OUT_DIR, 'monstera-backend', 'monstera-backend.exe');
if (!fs.existsSync(exe)) {
  console.error('[build-backend] 产物未生成:', exe);
  process.exit(1);
}
// 统计整个 onedir 目录体积（会随 extraResources 整目录打包进安装包）
let total = 0;
(function sum(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) sum(p); else total += fs.statSync(p).size;
  }
})(path.join(OUT_DIR, 'monstera-backend'));
const mb = (total / 1024 / 1024).toFixed(1);
console.log(`[build-backend] 完成: ${exe} (目录 ${mb} MB)`);