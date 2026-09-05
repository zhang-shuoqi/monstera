// Monstera 桌面壳 · 预加载脚本
// 通过 contextBridge 向渲染进程暴露极小的、经过收敛的原生能力入口。
// 业务页面（index.html）仅在桌面壳下使用这些能力；浏览器打开时回退到 window.open。
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('monstera', {
  // 兼容保留：在壳内打开外部 URL
  openExternalUrl: (url) => ipcRenderer.invoke('open-external-url', url),

  // 受控内部窗口：在 Monstera 内打开官方申请页/充值页（kind 区分用途）
  openInternalWindow: (url, kind = '') =>
    ipcRenderer.invoke('open-internal-window', { url, kind }),

  // 充值专用：受控内部窗口加载官方充值页
  openRechargeWindow: (url) => ipcRenderer.invoke('open-recharge-window', url),

  // 订阅内部窗口关闭事件（数据：{ url, kind }）；返回取消订阅函数
  onInternalWindowClosed: (cb) => {
    const handler = (_e, data) => { try { cb(data); } catch (_) {} };
    ipcRenderer.on('internal-window-closed', handler);
    return () => ipcRenderer.removeListener('internal-window-closed', handler);
  },

  // 自绘标题栏（无边框窗口）控制
  windowControls: {
    minimize: () => ipcRenderer.send('win:minimize'),
    toggleMaximize: () => ipcRenderer.send('win:toggle-max'),
    close: () => ipcRenderer.send('win:close'),
    isMaximized: () => ipcRenderer.invoke('win:get-maximized'),
    onMaximizedChange: (cb) => {
      const handler = (_e, val) => { try { cb(val); } catch (_) {} };
      ipcRenderer.on('win:maximized-changed', handler);
      return () => ipcRenderer.removeListener('win:maximized-changed', handler);
    },
    getSize: () => ipcRenderer.invoke('win:get-size'),
    setSize: (w, h, dragged) => ipcRenderer.send('win:set-size', { w, h, dragged }),
  },

  // 预留：查询桌面壳能力是否可用
  isDesktop: true,
});