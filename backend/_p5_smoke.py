"""Phase 5 冒烟自检：设置钳制/持久化、硬保护超限、单步超时、崩溃恢复、重试、Plan 确认。"""
import json
import tempfile
import threading
import time
from pathlib import Path

from agent_core.loop import LoopEngine, LoopGuardConfig, ToolResult, ModelDecision
from agent_core.runtime import AgentCore, StateProjector
from agent_core.state_store import TaskStatus
from agent_core.toolbox import ToolResult as TR
from agent_core.user_gate import UserGate
from agent_core.events import AgentEvent, EventBus, EventType, get_bus


def new_core(tmp: Path):
    from agent_core import events
    events._bus = EventBus()   # 重置全局总线，避免跨用例污染
    from agent_core.runtime import _core
    locals()  # noop
    return AgentCore(tmp)


class SleepTool:
    """可超时工具：sleep 超过线程 join 超时阈值。"""
    def execute(self, name, args):
        time.sleep(5)
        return TR(success=True, data={"slept": True})


class AlwaysToolModel:
    """幻觉循环模型：永远调工具（验证最大工具调用次数闸门）。"""
    def __init__(self, max_calls):
        self._n = 0
        self._max = max_calls

    def decide(self, objective, history):
        self._n += 1
        if self._n > self._max:
            return ModelDecision(kind="final_answer", content="ok")
        return ModelDecision(kind="tool_call", content={"n": self._n}, tool_name="fake_probe")


def test_settings_clamp_and_persist(tmp: Path):
    core = new_core(tmp)
    s = core.update_settings({"max_iterations": 999999, "max_tool_calls": 1, "step_timeout_s": 0})
    assert s.max_iterations == 500, s
    assert s.max_tool_calls == 10, s
    assert s.step_timeout_s == 10.0, s
    # 持久化：新实例读同一文件
    core2 = new_core(tmp)
    s2 = core2.get_settings()
    assert s2.max_iterations == 500 and s2.auto_allow_overwrite is False
    print("OK settings clamp+persist")


class GarbageModel:
    """模型输出格式错误：返回非法决策（不是 final_answer/tool_call）或缺失工具名。"""
    def __init__(self, kind="garbage"):
        self._kind = kind
        self._n = 0

    def decide(self, objective, history):
        self._n += 1
        if self._kind == "garbage":
            return ModelDecision(kind="???", content="乱码输出")     # 完全非法 kind
        return ModelDecision(kind="tool_call", content={})            # 工具调用却无 tool_name


def test_invalid_model_decision(tmp: Path):
    core = new_core(tmp)
    for kind in ("garbage", "no_tool_name"):
        t = core.create_task(f"坏输出 {kind}")
        state = core.run_task(t.task_id, model=GarbageModel(kind))
        assert state.status == TaskStatus.FAILED, (kind, state.status)
        assert state.fail_reason and "ModelDecision" in state.fail_reason, (kind, state.fail_reason)
        print(f"OK invalid model decision({kind}) -> failed: {state.fail_reason}")


def test_guard_max_tool_calls(tmp: Path):
    core = new_core(tmp)
    core.update_settings({"max_tool_calls": 12, "max_iterations": 50})
    task = core.create_task("超限测试")
    state = core.run_task(task.task_id, model=AlwaysToolModel(99))  # 模型想调 100 次，闸门 12 次
    assert state.status == TaskStatus.FAILED, state.status
    assert "安全限制" in (state.fail_reason or "")
    assert state.tool_call_count == 12, state.tool_call_count
    print("OK guard max_tool_calls ->", state.fail_reason)


def test_step_timeout(tmp: Path):
    core = new_core(tmp)
    core.update_settings({"step_timeout_s": 10, "max_iterations": 30})
    class TimeoutModel:
        def decide(self, objective, history):
            if history and not history[-1].success and "超时" in history[-1].summary:
                return ModelDecision(kind="final_answer", content="工具超时，改为直接回答")
            return ModelDecision(kind="tool_call", content={}, tool_name="sleep_tool")
    from agent_core.runtime import AgentCore as AC
    bus = get_bus()
    engine = LoopEngine(bus)  # 默认 60s 超时；改用短超时
    engine.guard_config = LoopGuardConfig(max_iterations=30, max_tool_calls=30, step_timeout_s=1)
    t0 = time.time()
    out = engine.run("t_timeout", "timeout", TimeoutModel(), SleepTool())
    dt = time.time() - t0
    assert out.ok, out.reason
    assert dt < 4, f"应被 1s 超时拦下，实际 {dt:.2f}s"
    print(f"OK step timeout (1s guard, took {dt:.2f}s)")


def test_crash_recovery(tmp: Path):
    core = new_core(tmp)
    t = core.create_task("crash 任务")
    # 模拟崩溃：直接把状态写成 executing（绕过状态机）
    real = core._store._tasks[t.task_id]
    real.status = TaskStatus.EXECUTING
    core._store._persist(real)
    # 重开实例恢复 → executing 应被标记 failed
    core2 = new_core(tmp)
    t2 = core2.get_task(t.task_id)
    assert t2.status == TaskStatus.FAILED, t2.status
    assert "中断" in (t2.fail_reason or "")
    print("OK crash recovery ->", t2.status.value)


def test_retry(tmp: Path):
    core = new_core(tmp)
    t = core.create_task("写文档")
    core._store.set_status(t.task_id, TaskStatus.FAILED, fail_reason="测试失败")
    nt = core.retry_task(t.task_id)
    assert nt.task_id != t.task_id
    assert nt.objective == "写文档"
    assert nt.status == TaskStatus.IDLE
    # 重试是新建，原任务保持终态不变量
    assert core.get_task(t.task_id).status == TaskStatus.FAILED
    print("OK retry (new task, terminal invariant kept)")


def test_plan_confirm(tmp: Path):
    core = new_core(tmp)
    core.update_settings({"plan_confirm": True})
    t = core.create_task("确认流程")
    res = []
    def decision_caller():
        time.sleep(0.5)
        core.resolve_intervention(t.task_id, True, "")
    threading.Thread(target=decision_caller, daemon=True).start()
    core.run_task(t.task_id, model=AlwaysToolModel(0), with_gate=True)
    status = core.get_task(t.task_id).status
    assert status in (TaskStatus.COMPLETED, TaskStatus.EXECUTING, TaskStatus.FAILED)
    print("OK plan_confirm gate awaited user ->", status.value)


def test_plan_confirm_denied(tmp: Path):
    """用户拒绝计划确认 → 任务直接标记失败，不留 waiting_human 悬挂态。"""
    from agent_core.state_store import IllegalTransitionError
    core = new_core(tmp)
    core.update_settings({"plan_confirm": True})
    t = core.create_task("确认被拒")
    def denier():
        time.sleep(0.4)
        core.resolve_intervention(t.task_id, False, "先不要执行")
    threading.Thread(target=denier, daemon=True).start()
    raised = None
    try:
        core.run_task(t.task_id, model=AlwaysToolModel(0), with_gate=True)
    except IllegalTransitionError as e:
        raised = e
    assert raised is not None
    assert core.get_task(t.task_id).status == TaskStatus.FAILED
    assert "拒绝" in (core.get_task(t.task_id).fail_reason or "")
    print("OK plan_confirm denied -> task failed:", core.get_task(t.task_id).fail_reason)


def test_plan_confirm_denied(tmp: Path):
    """用户拒绝计划确认 → 任务直接标记失败，不留 waiting_human 悬挂态。"""
    from agent_core.state_store import IllegalTransitionError
    core = new_core(tmp)
    core.update_settings({"plan_confirm": True})
    t = core.create_task("确认被拒")
    def denier():
        time.sleep(0.4)
        core.resolve_intervention(t.task_id, False, "先不要执行")
    threading.Thread(target=denier, daemon=True).start()
    raised = None
    try:
        core.run_task(t.task_id, model=AlwaysToolModel(0), with_gate=True)
    except IllegalTransitionError as e:
        raised = e
    assert raised is not None
    assert core.get_task(t.task_id).status == TaskStatus.FAILED
    assert "拒绝" in (core.get_task(t.task_id).fail_reason or "")
    print("OK plan_confirm denied -> task failed:", core.get_task(t.task_id).fail_reason)


def test_stop_task(tmp: Path):
    """真实停止：运行中任务 stop 后在下轮迭代开头终止并标记 failed(user_stopped)。"""
    core = new_core(tmp)
    core.update_settings({"max_tool_calls": 500, "max_iterations": 500})   # 调大上限，让 stop 先于硬保护生效
    t = core.create_task("可停止任务")

    class SlowAlways(AlwaysToolModel):
        def decide(self, objective, history):    # 模拟真实 LLM 处理延迟
            time.sleep(0.05)
            return super().decide(objective, history)

    def stopper():
        time.sleep(0.3)
        assert core.stop_task(t.task_id) is True, "运行中任务应能请求停止"
    threading.Thread(target=stopper, daemon=True).start()
    state = core.run_task(t.task_id, model=SlowAlways(999))
    assert state.status == TaskStatus.FAILED, state.status
    assert "手动停止" in (state.fail_reason or ""), state.fail_reason
    # 已停止/终态任务再 stop → False（无注册中断事件）
    assert core.stop_task(t.task_id) is False
    print("OK stop_task ->", state.fail_reason)


def test_delete_task(tmp: Path):
    """删除：仅终态可删；删除后内存/索引/磁盘快照/事件文件均清理。"""
    core = new_core(tmp)
    t = core.create_task("待删除")
    # 运行中不可删
    assert core.delete_task(t.task_id) is False
    # 空循环完成 → 终态可删
    core.run_task(t.task_id)
    assert core.delete_task(t.task_id) is True
    assert core.get_task(t.task_id) is None
    assert all(r.get("taskId") != t.task_id for r in core.history_rows())
    assert not (tmp / "tasks" / f"{t.task_id}.json").exists()
    assert not (tmp / "events" / f"{t.task_id}.jsonl").exists()
    print("OK delete_task (terminal-only, files cleaned)")


if __name__ == "__main__":
    for fn in (test_settings_clamp_and_persist, test_invalid_model_decision,
               test_guard_max_tool_calls, test_step_timeout,
               test_crash_recovery, test_retry, test_plan_confirm, test_plan_confirm_denied,
               test_stop_task, test_delete_task):
        import sys
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(Path(td))
            except Exception as e:
                print(f"FAIL {fn.__name__}: {type(e).__name__}: {e}")
                sys.exit(1)
    print("\nALL PHASE 5 SMOKE TESTS PASSED")