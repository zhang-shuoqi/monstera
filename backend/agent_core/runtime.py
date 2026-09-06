"""AgentCore：把循环引擎 / 事件总线 / 状态存储接线（设计定稿 v1.0 · 二）。

职责：
  - 组装内核，对外提供最小操作面：create_task / run_task / get_task / list_tasks / restore
  - 【关键】循环引擎与状态存储之间不直接调用：核心配一个 StateProjector 订阅总线事件，
    由事件驱动状态迁移。这同时满足 Phase 0 验收"事件总线能让两个模块互相通信，不直接调用"。

Phase 0 说明：
  - run_task 只跑"空循环"（ScriptedFakeModel + FakeToolbox），验证 idle→executing→completed。
  - 真实模型驱动（Function Calling）在 Phase 3 接入；假模型/假工具届时被替换，接线方式不变。
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .events import (
    K_ANSWER,
    K_DATA,
    K_DETAIL,
    K_REASON,
    K_SUCCESS,
    K_TOOL,
    AgentEvent,
    EventBus,
    EventType,
    get_bus,
    human_intervention_required_event,
    task_failed_event,
)
from .loop import LoopEngine, LoopGuardConfig, ScriptedFakeModel, FakeToolbox
from .memory_trail import MemoryTrail
from .settings import AgentSettings, SettingsStore
from .state_store import IllegalTransitionError, StateStore, TaskState, TaskStatus
from .toolbox import ToolResult, build_default_toolbox
from .user_gate import UserGate


class StateProjector:
    """总线上唯一的『状态机维护者』。

    它订阅某个 task_id 的事件，把事件流投影成 TaskState 的状态迁移。
    循环引擎不直接写存储，状态存储也不反过来调用循环引擎——两边只通过事件总线对话。
    这保证：任何两层之间禁止直接函数调用，必须走事件总线（铁律）。
    """

    def __init__(self, store: StateStore) -> None:
        self._store = store
        self._unsub_map: Dict[str, Any] = {}   # task_id -> 取消订阅函数（供删除时单任务 detach）

    def attach(self, task_id: str) -> None:
        unsub = get_bus().subscribe(task_id, self._on_event)
        self._unsub_map[task_id] = unsub

    def detach(self, task_id: str) -> None:
        """取消某任务的投影订阅（任务被删除时调用，避免幽灵写入）。"""
        unsub = self._unsub_map.pop(task_id, None)
        if unsub is not None:
            unsub()

    def _on_event(self, event: AgentEvent) -> None:
        # 事件先落盘（Phase 4：重启后可回放时间线），再做状态投影
        self._store.append_event(event.task_id, event.to_dict())
        # 显式路由：未注册的事件类型明确跳过（不做静默歧义处理）
        handler = self._HANDLERS.get(event.type)
        if handler is not None:
            handler(self, event.task_id, event.payload or {})

    def _on_step_started(self, task_id: str, payload: Any) -> None:
        self._store.set_status(task_id, TaskStatus.EXECUTING)
        # 引擎每轮发一次 STEP_STARTED，机械计数与之保持同步
        self._store.incr_loop_iterations(task_id)

    def _on_tool_call_requested(self, task_id: str, payload: Any) -> None:
        self._store.incr_tool_call_count(task_id)

    def _on_tool_result_received(self, task_id: str, payload: Any) -> None:
        """记录本次任务自己创建过的文件（供覆盖分级判断）。"""
        if not isinstance(payload, dict):
            return
        if payload.get(K_TOOL) == "file_write" and payload.get(K_SUCCESS):
            data = payload.get(K_DATA) or {}
            path = data.get("path")
            if path and data.get("mode") == "created":
                self._store.record_created_file(task_id, str(path))

    def _on_human_intervention_required(self, task_id: str, payload: Any) -> None:
        """危险操作进入等待用户确认状态。"""
        self._store.set_status(task_id, TaskStatus.WAITING_HUMAN)

    def _on_task_completed(self, task_id: str, payload: Any) -> None:
        answer = payload.get(K_ANSWER) if isinstance(payload, dict) else None
        self._store.set_status(task_id, TaskStatus.COMPLETED, final_answer=answer)

    def _on_task_failed(self, task_id: str, payload: Any) -> None:
        reason = "unknown"
        if isinstance(payload, dict):
            reason = payload.get(K_DETAIL) or payload.get(K_REASON) or "unknown"
        # 定稿三：失败写入时刻派生并持久化终止类型（存量/未知默认 "error"），三读源据此统一
        _r = reason
        _d = str(payload.get(K_DETAIL, "") if isinstance(payload, dict) else "")
        if _r == "user_stopped" or "手动停止" in _d or "中断运行" in _d:
            kind = "user_interrupt"
        elif _r == "plan_denied" or ("计划" in _d and "拒" in _d):
            kind = "plan_denied"
        elif _r == "interrupted":
            kind = "interrupted"
        else:
            kind = "error"
        self._store.set_status(task_id, TaskStatus.FAILED, fail_reason=str(reason), terminate_kind=kind)

    # 事件类型 → 投影处理（显式 dict，替代 getattr 动态派发；未注册类型被 _on_event 跳过）
    _HANDLERS: Dict[EventType, Callable[["StateProjector", str, Any], None]] = {
        EventType.STEP_STARTED: _on_step_started,
        EventType.TOOL_CALL_REQUESTED: _on_tool_call_requested,
        EventType.TOOL_RESULT_RECEIVED: _on_tool_result_received,
        EventType.HUMAN_INTERVENTION_REQUIRED: _on_human_intervention_required,
        EventType.TASK_COMPLETED: _on_task_completed,
        EventType.TASK_FAILED: _on_task_failed,
    }

    def detach_all(self) -> None:
        for fn in self._unsub_map.values():
            fn()
        self._unsub_map.clear()


class AgentCore:
    """Monstera Agent Core 组装器。进程内单例（见 get_core()）。"""

    def __init__(
        self,
        data_dir: Path,
        guard: Optional[LoopGuardConfig] = None,
        bus: Optional[EventBus] = None,
        gate: Optional[UserGate] = None,
    ) -> None:
        self._bus = bus or get_bus()
        self._store = StateStore(Path(data_dir))
        self._settings = SettingsStore(Path(data_dir))       # Phase 5：可配置硬保护
        self._guard_cfg = guard or LoopGuardConfig()
        self._loop = LoopEngine(self._bus, self._guard_cfg)
        self._toolbox = build_default_toolbox()   # Agent 工具箱 V1：file trio
        self._projector = StateProjector(self._store)
        self._memory = MemoryTrail(Path(data_dir))   # 原子记忆（Phase 6）：总线消费者，与投影器平级
        self._gate = gate or UserGate(bus=self._bus)   # 用户闸（Phase 2）：危险操作弹窗确认
        self._stop_events: Dict[str, threading.Event] = {}   # Phase 5 真实停止：运行中任务 → 中断事件
        self.apply_settings(self._settings.get())    # 设置 → 循环/闸门
        self.restore()  # 软件打开自动恢复（含异常中断任务标记 failed）

    # ---------- Phase 5：设置（可配置机械硬保护 / 覆盖放行） ----------

    def apply_settings(self, settings: AgentSettings) -> None:
        """把设置落到循环引擎守卫与用户闸（运行前调用，无需重启）。"""
        self._guard_cfg = LoopGuardConfig(
            max_iterations=settings.max_iterations,
            max_tool_calls=settings.max_tool_calls,
            step_timeout_s=settings.step_timeout_s,
        )
        self._loop.guard_config = self._guard_cfg
        self._gate.auto_allow_overwrite = settings.auto_allow_overwrite

    def get_settings(self) -> AgentSettings:
        return self._settings.get()

    def update_settings(self, patch: Dict[str, Any]) -> AgentSettings:
        s = self._settings.update(patch)
        self.apply_settings(s)
        return s

    # ---------- 对外操作面 ----------

    def create_task(self, objective: str) -> TaskState:
        task = self._store.create_task(objective)
        self._projector.attach(task.task_id)
        self._memory.attach(task.task_id)
        return self._store.get(task.task_id)

    def run_task(self, task_id: str, rounds: int = 3, plan: Optional[List[Dict[str, Any]]] = None,
                 with_gate: bool = False, model: Optional[Any] = None,
                 persist_refs: bool = False) -> TaskState:
        """驱动循环引擎。

        - plan=None：Phase 0 空循环演示（fake_probe + FakeToolbox）。
        - plan 给定：Phase 1 真实工具验收——每步 {"tool": name, "args": {...}} 依次调用 V1 工具箱。
        - model 给定：Phase 3 真实模型驱动（LLMModelDriver）——循环引擎不感知模型实现，
          只认 ModelDriver 协议（decide → ModelDecision）。
        - with_gate=True：Phase 2 —— 工具执行前过用户闸。默认 False 保持前行为。
        - persist_refs=True：模型驱动的上下文引用文件落任务目录（agent_data/refs），供回放。
        """
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"任务不存在: {task_id}")
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            raise IllegalTransitionError(
                f"任务已处于终态（{task.status.value}），禁止重跑（状态机不变量）"
            )
        if model is not None:
            executor = self._toolbox
        elif plan:
            model = ScriptedFakeModel(plan=list(plan))
            executor = self._toolbox
        else:
            model = ScriptedFakeModel(rounds=max(1, rounds))
            executor = FakeToolbox()
        gate = self._gate if with_gate else None
        stop_ev = threading.Event()
        self._stop_events[task_id] = stop_ev   # Phase 5 真实停止：注册中断事件
        try:
            # Phase 5：Plan 确认——执行任何工具前，先等用户点「开始」（若已开启且过闸）
            if gate is not None and self._settings.get().plan_confirm:
                self._plan_confirm(task_id, task.objective)
            self._loop.run(
                task_id,
                task.objective,
                model,
                executor,
                gate=gate,
                created_files_fn=self._created_files_provider(task_id),
                stop_event=stop_ev,
            )
        finally:
            self._stop_events.pop(task_id, None)
        if persist_refs and hasattr(model, "usage"):
            self._persist_model_refs(task_id, model)
        return self._store.get(task_id)

    def stop_task(self, task_id: str) -> bool:
        """请求停止正在运行的任务（真实停止，Phase 5）。

        循环引擎每轮迭代开头检查中断事件，置位后终止并标记 failed（user_stopped）。
        任务不在运行中（无注册事件）返回 False。
        """
        stop_ev = self._stop_events.get(task_id)
        if stop_ev is None:
            return False
        stop_ev.set()
        return True

    def _plan_confirm(self, task_id: str, objective: str) -> None:
        """Plan 确认（Phase 5）：执行前等用户点「开始」/「直接执行」；拒绝则任务标记失败。"""
        self._bus.publish(human_intervention_required_event(
            task_id, "__plan__", {},
            f"计划确认：是否开始执行『{objective[:80]}』？", "plan_confirm"))
        outcome = self._gate._await(task_id)
        if not outcome.get("allow"):
            reason = outcome.get("reason", "用户未确认开始执行") or "用户未确认开始执行"
            # 拒绝即失败：发布 TASK_FAILED 事件由 StateProjector 消费后落盘（不留 waiting_human 悬挂态；
            # 状态变更唯一入口收敛到投影器，runtime 不再直接 set_status）
            self._bus.publish(task_failed_event(
                task_id, "plan_denied", f"计划确认被拒绝，任务未执行：{reason}"))
            raise IllegalTransitionError(reason)

    def _persist_model_refs(self, task_id: str, model: Any) -> None:
        """记录模型驱动的 token 用量回任务快照（成本感知前置，界面展示用）。"""
        usage = getattr(model, "usage", lambda: {})() if hasattr(model, "usage") else {}
        if usage:
            self._store.set_model_usage(task_id, {k: int(v) for k, v in usage.items()})

    def resolve_intervention(self, task_id: str, allow: bool, reason: str = "") -> bool:
        """用户对危险操作弹窗作出选择（允许/拒绝）。Phase 4 由弹窗前后端调用。"""
        return self._gate.resolve(task_id, allow, reason)

    def _created_files_provider(self, task_id: str) -> Callable[[], List[str]]:
        """返回实时读取该任务已创建文件集合的回调（循环每一步执行前取最新）。"""
        return lambda: set(self._store.get(task_id).created_files) if self._store.get(task_id) else set()

    def tools_info(self) -> List[Dict[str, Any]]:
        """V1 工具箱注册表元信息（供界面/调试查看）。"""
        return self._toolbox.info_all()

    def memory_recall(self, objective: str, top_k: int = 3, max_chars: int = 2500) -> List[str]:
        """原子记忆检索（Phase 6）：按目标相关度取 TopK 紧凑文本，供 LLMDriver 注入上下文。"""
        return self._memory.recall(objective, top_k=top_k, max_chars=max_chars)

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self._store.get(task_id)

    def list_tasks(self) -> List[TaskState]:
        return self._store.list_tasks()

    def history_rows(self) -> List[Dict[str, Any]]:
        """历史任务表（index.json），供 UI『历史任务』折叠区使用。"""
        return self._store.index_rows()

    def update_task_meta(self, task_id: str, title: Optional[str] = None,
                         pinned: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """任务展示元数据更新（右键重命名/置顶）：title/pinned 至少传一个。"""
        task = self._store.update_meta(task_id, title=title, pinned=pinned)
        if task is None:
            return None
        return task.to_meta()

    def timeline(self, task_id: str) -> List[Dict[str, Any]]:
        """任务完整事件时间线（Phase 4：优先持久化事件，回放不依赖运行期内存总线）。"""
        persisted = self._store.load_events(task_id)
        if persisted:
            return persisted
        # 兼容老版本：无持久化文件时回退到内存总线历史
        from .events import get_bus
        return [e.to_dict() for e in get_bus().history(task_id)]

    def restore(self) -> List[TaskState]:
        """启动恢复：从磁盘载入全部任务，并为每个任务重新挂上总线订阅。

        Phase 5 硬化：异常中断（软件崩溃/被杀）时遗留的 executing/waiting_human
        任务标记为 failed（"恢复或标记为失败"），避免永远停留在运行态。
        """
        self._projector.detach_all()
        tasks = self._store.restore()
        self._memory.restore()   # 读回历史原子记忆（跨进程重启仍可召回）
        for t in tasks:
            self._projector.attach(t.task_id)
            self._memory.attach(t.task_id)
            if t.status in (TaskStatus.EXECUTING, TaskStatus.WAITING_HUMAN):
                # 中断恢复：发布 TASK_FAILED 事件由 StateProjector 消费后落盘
                # （状态变更唯一入口收敛到投影器，runtime 不再直接 set_status）
                self._bus.publish(task_failed_event(
                    t.task_id, "interrupted",
                    "任务因应用中断未能完成，已标记为失败（Phase 5 硬化）"))
        return tasks

    def retry_task(self, task_id: str) -> TaskState:
        """错误恢复（从头重试）：新建一个同目标的任务，而不是污染状态机（终态不可重跑不变量保留）。

        顺带保留源任务的展示标题与置顶标记（右键重命名的名字在重试后不丢失）。
        """
        src = self.get_task(task_id)
        if src is None:
            raise KeyError(f"任务不存在: {task_id}")
        task = self.create_task(src.objective)
        self._store.update_meta(task.task_id, title=src.title, pinned=src.pinned)
        return self._store.get(task.task_id)

    def delete_task(self, task_id: str) -> bool:
        """删除任务（历史任务列表"删除"，Phase 5 交互）：仅终态可删。

        同时清理：投影订阅、内存字典、磁盘快照/事件文件、索引行。
        非终态（运行中/待确认）禁止删除 → 返回 False（由路由层转 409）。
        """
        task = self.get_task(task_id)
        if task is None:
            return False
        if task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False
        self._projector.detach(task_id)
        self._memory.detach(task_id)
        return self._store.delete_task(task_id)


_core: Optional[AgentCore] = None


def get_core() -> AgentCore:
    """进程内单例：延迟初始化，数据目录取 config.AGENT_DATA_DIR。"""
    global _core
    if _core is None:
        import config

        config.ensure_agent_data_dir()
        _core = AgentCore(config.AGENT_DATA_DIR)
    return _core