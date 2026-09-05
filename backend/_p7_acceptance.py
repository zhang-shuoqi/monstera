# -*- coding: utf-8 -*-
"""内核修复（体检报告 4 项）验收自动化：
  1. 状态迁移唯一入口（StateProjector）
  2. 事件契约工厂/常量（结构回归：SSE 事件序列与 payload 字段不退化）
  3. LoopEngine.run 阶段化（run() 方法 ≤30 行）
  4. 上下文压缩（10MB -> 落盘引用，见 _p6 第 5 项）
手动验证 5 项脚本化：正常任务 / 用户拒绝后继续 / restore 中断恢复 / memory 提炼 / SSE 结构。
运行：.venv\\Scripts\\python.exe _p7_acceptance.py
"""
import ast
import pathlib
import tempfile
import threading

import agent_core.runtime as rt
from agent_core.events import get_bus, step_started_event
from agent_core.loop import FakeToolbox, LoopEngine, ScriptedFakeModel
from agent_core.runtime import AgentCore
from agent_core.toolbox import build_default_toolbox

HERE = pathlib.Path(__file__).resolve().parent


# ---------- 验收 3：LoopEngine.run 方法体 ≤30 行 ----------
_src = (HERE / "agent_core" / "loop.py").read_text(encoding="utf-8")
_tree = ast.parse(_src)
_run_node = next(n for n in ast.walk(_tree)
                 if isinstance(n, ast.FunctionDef) and n.name == "run"
                 and isinstance(n.body[0], ast.Expr) and "编排骨架" in ast.get_docstring(n) or "")
_span = _run_node.end_lineno - _run_node.lineno + 1
assert _span <= 30, f"LoopEngine.run 共 {_span} 行 > 30（验收要求 ≤30）"
print(f"acceptance 3: LoopEngine.run 方法体 {_span} 行（阶段逻辑已下沉到私有方法）")

# ---------- 验收 1：set_status 唯一调用方 = StateProjector ----------
_runtime_src = (HERE / "agent_core" / "runtime.py").read_text(encoding="utf-8")
_hits = [i for i, ln in enumerate(_runtime_src.splitlines(), 1)
         if "set_status(" in ln and not ln.lstrip().startswith("#")]  # 仅真实调用，排除注释
# 找出每个调用点所属的方法名，必须全部位于 StateProjector（def _on_*）内
def _method_of(line_no):
    for j in range(line_no - 1, 0, -1):
        l = _runtime_src.splitlines()[j - 1]
        if l.lstrip().startswith("def "):
            return l.strip()
    return "?"
_calls = {_method_of(n) for n in _hits}
assert all(m.startswith("def _on_") for m in _calls), f"set_status 出现在非投影器方法: {_calls}"
print(f"acceptance 1: set_status 仅被投影器调用 {sorted(_calls)}；runtime 无直连 set_status")

# ---------- 手动验证 1/4/5：正常任务运行 + memory 提炼 + 事件序列回归 ----------
data_dir = pathlib.Path(tempfile.mkdtemp())
core = AgentCore(data_dir)
tid = core.create_task("验收任务：列举当前目录").task_id
core.run_task(tid, rounds=3)   # FakeToolbox + ScriptedFakeModel（rounds 模式）
st = core.get_task(tid)
assert st.status.value == "completed", st.status
ev = get_bus().history(tid)
types = [e.type.value for e in ev]
assert types[0] == "INTENT_RECEIVED" and types[1] == "OBJECTIVE_DEFINED"
assert "STEP_STARTED" in types and "TOOL_CALL_REQUESTED" in types \
    and "TOOL_RESULT_RECEIVED" in types and "OBSERVATION_READY" in types
assert types[-1] == "TASK_COMPLETED"
# 修复 2 回归：事件 payload 关键字段完整（对外 SSE 结构不变）
for e in ev:
    p = e.payload or {}
    if e.type.value == "TOOL_CALL_REQUESTED":
        assert {"tool", "args", "toolCalls"} <= set(p), p
    elif e.type.value == "TOOL_RESULT_RECEIVED":
        assert {"tool", "success", "error", "data"} <= set(p), p
    elif e.type.value == "OBSERVATION_READY":
        assert "observation" in p and "toolName" in p["observation"], p
    elif e.type.value == "TASK_COMPLETED":
        assert {"answer", "iterations", "toolCalls"} <= set(p), p
st = core.get_task(tid)
assert st.status.value == "completed"
n_mem = core._memory.recall("验收任务")   # 任务终态应已提炼，目标含"验收任务"
assert len(n_mem) >= 1, n_mem
print(f"acceptance 1): 正常任务 completed；事件类型序列 {len(types)} 帧结构完整；memory 提炼 {len(n_mem)} 条")

# ---------- 手动验证 2：用户拒绝工具调用后任务继续 ----------
core2 = AgentCore(pathlib.Path(tempfile.mkdtemp()))
tid2 = core2.create_task("拒绝后继续").task_id
plan = [
    # 写系统目录 → 闸 CONFIRM → 用户拒绝 → 模型走 fallback（file_read 用户文件）继续
    {"tool": "file_write", "args": {"path": r"C:\Windows\system32\probe.txt", "content": "x"},
     "fallback": {"tool": "file_read", "args": {"path": str(HERE / ".." / "backend" / "config.py")}}},
    {"tool": "list_dir", "args": {"path": str(HERE)}},
]
timeout = threading.Timer(0.08, lambda: core2.resolve_intervention(tid2, False, "测试：拒绝写系统目录"))
timeout.start()
core2.run_task(tid2, plan=plan, with_gate=True)
timeout.cancel()
assert core2.get_task(tid2).status.value == "completed", core2.get_task(tid2).status
ev2 = get_bus().history(tid2)
assert any(e.type.value == "HUMAN_INTERVENTION_REQUIRED" for e in ev2)
assert core2.get_task(tid2).status.value == "completed"   # 拒绝后继续并完成（不卡死不悬挂）
print("acceptance 2): 用户拒绝系统目录写入 → 模型换方案继续 → completed")

# ---------- 手动验证 3：restore 中断恢复（残留 executing → failed） ----------
data3 = pathlib.Path(tempfile.mkdtemp())
core3 = AgentCore(data3)
tid3 = core3.create_task("中断恢复验证").task_id
core3._bus.publish(step_started_event(tid3, 1))   # 投影器置 executing
assert core3.get_task(tid3).status.value == "executing"
core3._projector.detach_all(); core3._memory.detach_all()   # 模拟旧实例下线（断开订阅）
core3b = AgentCore(data3)                                    # 重启：restore 将 executing 置 failed
t3 = core3b.get_task(tid3)
assert t3.status.value == "failed" and "中断" in (t3.fail_reason or ""), t3.status
print(f"acceptance 3): restore 把残留 executing 标记 failed（{t3.fail_reason[:40]}…）")

print("ALL ACCEPTANCE PASS")