/* ============================================================
   ch10 · Alpine store：Monstera 状态中枢（片3 3-B）
   - 三域：会话列表 / 当前任务元信息 / 轮次索引。
   - 轮次数据只追加、旧轮不回改（增量渲染的内存镜像基础）。
   - 放在 body 尾、vendor/alpine 之后；Alpine 未加载时静默降级。
   ============================================================ */
(function () {
  'use strict';

  // 渲染开关（3-D）：默认 legacy 保底；增量实现注册后按需切到 incremental。任一出问题关开关回滚。
  window.MONSTERA_CH = window.MONSTERA_CH || {};
  if (window.MONSTERA_CH.render !== 'incremental') window.MONSTERA_CH.render = 'legacy';

  if (typeof Alpine === 'undefined') {
    return; // 极端环境/早期 file:// 无 Alpine：静默，不影响 legacy 骨架
  }

  Alpine.store('monstera', {
    // 会话列表：对话 + 历史任务 轻量镜像（name / type / active）
    sessions: [],

    // 当前任务元信息（Agent）：id / title / status / 终态摘要
    activeTask: null,

    // 轮次索引：序号列表 [{no, toolCalls, cost}]——轮次数据追加即弃，旧轮不回改
    turnIndex: [],
  });
})();