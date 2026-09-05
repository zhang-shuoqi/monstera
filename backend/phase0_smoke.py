"""Phase 0 验收自测（可直接运行：python phase0_smoke.py）

对照 Phase 0 验收标准逐条验证：
  1) 能创建新任务，任务状态能序列化到硬盘，关闭再打开能恢复。
  2) 事件总线能让两个模块互相通信，不直接调用。
  3) 空循环能跑完一个假任务，状态从 idle → executing → completed。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from agent_core.events import AgentEvent, EventBus, EventType
from agent_core.loop import FakeToolbox, ScriptedFakeModel
from agent_core.runtime import AgentCore
from agent_core.state_store import IllegalTransitionError, StateStore, TaskStatus

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def test_event_bus_two_modules_no_direct_call() -> None:
    """验收 2：事件总线让两个模块互相通信，不直接调用。"""
    print("\n== 验收 2：事件总线跨模块通信 ==")
    bus = EventBus()
    received: list[AgentEvent] = []

    def collector(ev: AgentEvent) -> None:
        received.append(ev)

    # 模块 A 只订阅 task_1 的事件（强制携带 taskId）
    bus.subscribe("task_1", collector)

    # 若无 task_id 订阅，必须被拒绝
    try:
        bus.subscribe("", collector)
        check("总线拒绝无 taskId 订阅", False, "空 task_id 未被禁止")
    except ValueError:
        check("总线拒绝无 taskId 订阅", True)

    # 模块 B 发 task_1 与 task_2 的事件
    bus.publish(AgentEvent(task_id="task_1", type=EventType.STEP_STARTED, payload={"step": 1}))
    bus.publish(AgentEvent(task_id="task_2", type=EventType.STEP_STARTED, payload={"step": 1}))
    bus.publish(AgentEvent(task_id="task_1", type=EventType.TASK_COMPLETED, payload={"answer": "ok"}))

    # collector 只应收到 task_1 的 2 条
    check("模块 A 只收到 task_1 事件", len(received) == 2, f"实际 {len(received)}")
    check("事件类型/载荷/时间戳完整", all(e.timestamp > 0 and e.type in EventType for e in received))
    check("task_2 事件被过滤", all(e.task_id == "task_1" for e in received))

    # 历史回放同样按 taskId 过滤
    check("总线历史按任务过滤", len(bus.history("task_1")) == 2 and len(bus.history("task_2")) == 1)


def test_state_store_serialize_restore() -> None:
    """验收 1：任务状态序列化到硬盘，关闭再打开能恢复。"""
    print("\n== 验收 1：状态序列化 + 重启恢复 ==")
    tmp = Path(tempfile.mkdtemp(prefix="agent_p0_"))
    try:
        store = StateStore(tmp)
        task = store.create_task("演示任务")
        check("新任务状态为 idle", task.status == TaskStatus.IDLE)

        store.set_status(task.task_id, TaskStatus.EXECUTING)
        check("迁移到 executing", store.get(task.task_id).status == TaskStatus.EXECUTING)

        # 非法迁移：COMPLETED 禁止重跑回 executing
        store.set_status(task.task_id, TaskStatus.COMPLETED, final_answer="done")
        try:
            store.set_status(task.task_id, TaskStatus.EXECUTING)
            check("非法迁移被拦截", False, "COMPLETED->EXECUTING 未被拦截")
        except IllegalTransitionError:
            check("非法迁移被拦截", True)

        # 磁盘文件已存在
        snap = tmp / "tasks" / f"{task.task_id}.json"
        check("快照已落盘", snap.exists(), f"缺 {snap}")
        check("历史索引表已写", (tmp / "index.json").exists())

        # 模拟"关闭再打开"：全新 StateStore 实例从磁盘恢复
        store2 = StateStore(tmp)
        restored = store2.restore()
        r = store2.get(task.task_id)
        check("重启后任务恢复", r is not None and r.objective == "演示任务")
        check("重启后状态保持 completed", r.status == TaskStatus.COMPLETED and r.final_answer == "done")
        _ = restored
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_empty_loop_full_flow() -> None:
    """验收 3：空循环跑完假任务，idle → executing → completed。"""
    print("\n== 验收 3：空循环假任务（连核心价值观：状态机单向迁移）==")
    tmp = Path(tempfile.mkdtemp(prefix="agent_p0_"))
    try:
        core = AgentCore(tmp)
        task = core.create_task("列出桌面文件（空循环演示）")
        task_id = task.task_id
        check("创建后状态为 idle", core.get_task(task_id).status == TaskStatus.IDLE)

        # 跑 5 圈空循环（假模型 5 次工具调用后回答）
        final = core.run_task(task_id, rounds=5)
        check("空循环完成状态 completed", final.status == TaskStatus.COMPLETED, f"实际 {final.status}")
        check("机械计数：迭代=6（5 次工具调用 + 1 次最终回答）", final.loop_iterations == 6, f"实际 {final.loop_iterations}")
        check("机械计数：工具调用=5", final.tool_call_count == 5, f"实际 {final.tool_call_count}")
        check("最终答复非空", bool(final.final_answer))
        check("completed_at 已写", final.completed_at is not None)

        # 终态禁止重跑（状态机 no-op 守卫）
        try:
            core.run_task(task_id, rounds=3)
            check("终态禁止重跑", False, "completed 任务被再次运行")
        except RuntimeError:
            check("终态禁止重跑", True)

        # 关闭再打开：同一数据目录新内核恢复 completed 任务
        core2 = AgentCore(tmp)
        restored = core2.get_task(task_id)
        check("重启后 completed 任务恢复", restored.status == TaskStatus.COMPLETED)

        # 事件时间线完整闭合（设计定稿 v1.0 · 七 事件契约）
        from agent_core.events import get_bus

        types = [e.type for e in get_bus().history(task_id)]
        check("事件链完整性", len(types) >= 3, f"仅 {len(types)} 条")
        check("事件以 INTENT_RECEIVED 开场", types[0] == EventType.INTENT_RECEIVED)
        check("事件以 TASK_COMPLETED 收尾", types[-1] == EventType.TASK_COMPLETED)
        check("事件契约字段完整", all(e.task_id == task_id and e.type and e.timestamp > 0 for e in get_bus().history(task_id)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    print("Phase 0 验收自测（Monstera Agent Core）")
    test_event_bus_two_modules_no_direct_call()
    test_state_store_serialize_restore()
    test_empty_loop_full_flow()

    print(f"\n===== 结果：{len(PASSED)} 通过 / {len(FAILED)} 失败 =====")
    if FAILED:
        print("失败项:", FAILED)
        sys.exit(1)
    print("Phase 0 验收全部通过 ✓")


if __name__ == "__main__":
    main()