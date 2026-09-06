/* ============================================================
   ch15 · 增量渲染数据管道（片3 3-C 第一子步）
   - 把「任务快照」灌入 Alpine store（monstera）三域：
       activeTask : 当前任务元信息
       turnIndex  : 轮次索引（序号列表 {no, toolCalls}，由事件时间线重建）
       sessions   : 会话/任务轻量镜像（当前任务置顶标 active）
   - 纯旁路：只在 agentViewRender / agentPaneRender 入口被调用，
     同步 store 供增量渲染读取；legacy 全量 innerHTML 逻辑完全不受影响。
   - 轮次数据只追加、旧轮不回改（按 STEP_STARTED 固定序列号，不回退）。
   ============================================================ */
(function () {
  'use strict';
  if (typeof Alpine === 'undefined') return;

  var S = function () { return Alpine.store('monstera'); };

  /* —— 由事件时间线重建轮次索引：每 STEP_STARTED 一轮，统计该轮内工具调用数 —— */
  function buildTurnIndex(evs) {
    var map = new Map();            // stepNo -> {no, toolCalls}
    var cur = 0;                    // 当前 STEP_STARTED 的 step 序号
    if (Array.isArray(evs)) {
      for (var i = 0; i < evs.length; i++) {
        var e = evs[i], t = e && e.type, p = (e && e.payload) || {};
        if (t === 'STEP_STARTED') {
          var n = p.step || 0;
          cur = n;
          if (n && !map.has(n)) map.set(n, { no: n, toolCalls: 0 });
        } else if (t === 'TOOL_CALL_REQUESTED') {
          if (map.has(cur)) { map.get(cur).toolCalls++; }
          else if (map.size === 0 && cur === 0) {
            // 极少量工具调用前无 STEP_STARTED：归入第 1 轮
            cur = 1;
            map.set(1, { no: 1, toolCalls: 1 });
          }
        }
      }
    }
    return Array.from(map.values()).sort(function (a, b) { return a.no - b.no; });
  }

  /* —— 把单任务快照同步进 store（增量渲染数据源）—— */
  function feed(task) {
    if (!task || typeof task !== 'object') return;
    var s = S();
    if (!s) return;
    s.activeTask = {
      id: task.task_id || null,
      title: task.objective || '',
      status: task.status || 'idle',
      loop_iterations: task.loop_iterations || 0,
      tool_call_count: task.tool_call_count || 0,
      final_answer: task.final_answer || null,
      fail_reason: task.fail_reason || null
    };
    s.turnIndex = buildTurnIndex(task.events || []);
    // 会话/任务轻量镜像：当前任务置顶标 active，其余保留
    var curId = task.task_id;
    var arr = (s.sessions || []).filter(function (x) { return x.id !== curId; });
    arr.unshift({ id: curId, title: task.objective || '', status: task.status || 'idle', active: true });
    s.sessions = arr;
  }

  window.MonsteraFeed = feed;
  window.MonsteraFeedBuildTurnIndex = buildTurnIndex; // 便于验收
})();