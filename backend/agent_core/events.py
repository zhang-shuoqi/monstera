"""事件契约与事件总线（设计定稿 v1.0 · 七）。

只做两件事：
  1) 定义 AgentEvent 契约：task_id / type / payload / timestamp
  2) 进程内内存发布订阅，所有消费者必须携带 task_id 过滤

铁律（强制）：
  - 事件消费者必须携带 taskId 过滤逻辑，禁止无条件消费全部总线事件。
  - UI 层与 Agent 内核之间禁止直接函数调用，必须通过事件总线传递事件。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EventType(str, Enum):
    """事件类型枚举（与设计定稿 v1.0 · 七 的 EventType 一一对应）。"""

    INTENT_RECEIVED = "INTENT_RECEIVED"
    OBJECTIVE_DEFINED = "OBJECTIVE_DEFINED"
    PLAN_CREATED = "PLAN_CREATED"
    STEP_STARTED = "STEP_STARTED"
    TOOL_CALL_REQUESTED = "TOOL_CALL_REQUESTED"
    TOOL_RESULT_RECEIVED = "TOOL_RESULT_RECEIVED"
    OBSERVATION_READY = "OBSERVATION_READY"
    HUMAN_INTERVENTION_REQUIRED = "HUMAN_INTERVENTION_REQUIRED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"


# ---------- 事件 payload 字段常量（消费方统一读取，禁止手写字符串 key） ----------
K_OBJECTIVE = "objective"
K_TOOL = "tool"
K_ARGS = "args"
K_TOOL_CALLS = "toolCalls"
K_SUCCESS = "success"
K_ERROR = "error"
K_DATA = "data"
K_OBSERVATION = "observation"
K_STEP = "step"
K_ANSWER = "answer"
K_ITERATIONS = "iterations"
K_REASON = "reason"
K_DETAIL = "detail"
K_LEVEL = "level"


# ---------- 高频事件 payload 类型约束（TypedDict；改名/漏字段在单文件内暴露） ----------
from typing import Any, Dict, TypedDict  # noqa: E402


class StepStartedPayload(TypedDict):
    step: int


class ToolCallRequestedPayload(TypedDict):
    tool: str
    args: Any
    toolCalls: int


class ToolResultReceivedPayload(TypedDict):
    tool: str
    success: bool
    error: Any
    data: Any


class ObservationReadyPayload(TypedDict):
    observation: Dict[str, Any]


class TaskCompletedPayload(TypedDict):
    answer: Any
    iterations: int
    toolCalls: int


class TaskFailedPayload(TypedDict):
    reason: str
    detail: Any


class HumanInterventionPayload(TypedDict):
    tool: Any
    args: Any
    reason: Any
    level: Any


class ObjectivePayload(TypedDict):
    objective: str


# ---------- 事件构造工厂（循环引擎/用户闸等发出方统一经工厂，杜绝散种 payload） ----------


def _event(task_id: str, etype: EventType, payload: Any) -> AgentEvent:
    return AgentEvent(task_id=task_id, type=etype, payload=payload)


def intent_received_event(task_id: str, objective: str) -> AgentEvent:
    return _event(task_id, EventType.INTENT_RECEIVED, {K_OBJECTIVE: objective})


def objective_defined_event(task_id: str, objective: str) -> AgentEvent:
    return _event(task_id, EventType.OBJECTIVE_DEFINED, {K_OBJECTIVE: objective})


def step_started_event(task_id: str, step: int) -> AgentEvent:
    return _event(task_id, EventType.STEP_STARTED, StepStartedPayload(step=step))


def tool_call_requested_event(task_id: str, tool: str, args: Any, tool_calls: int) -> AgentEvent:
    return _event(task_id, EventType.TOOL_CALL_REQUESTED,
                  ToolCallRequestedPayload(tool=tool, args=args, toolCalls=tool_calls))


def tool_result_received_event(task_id: str, tool: str, success: bool,
                               error: Any, data: Any) -> AgentEvent:
    return _event(task_id, EventType.TOOL_RESULT_RECEIVED,
                  ToolResultReceivedPayload(tool=tool, success=success, error=error, data=data))


def observation_ready_event(task_id: str, observation: Dict[str, Any]) -> AgentEvent:
    return _event(task_id, EventType.OBSERVATION_READY,
                  ObservationReadyPayload(observation=observation))


def task_completed_event(task_id: str, answer: Any, iterations: int, tool_calls: int) -> AgentEvent:
    return _event(task_id, EventType.TASK_COMPLETED,
                  TaskCompletedPayload(answer=answer, iterations=iterations, toolCalls=tool_calls))


def task_failed_event(task_id: str, reason: str, detail: Any = None) -> AgentEvent:
    return _event(task_id, EventType.TASK_FAILED,
                  TaskFailedPayload(reason=reason, detail=detail))


def human_intervention_required_event(task_id: str, tool: Any, args: Any,
                                      reason: Any, level: Any) -> AgentEvent:
    return _event(task_id, EventType.HUMAN_INTERVENTION_REQUIRED,
                  HumanInterventionPayload(tool=tool, args=args, reason=reason, level=level))


@dataclass
class AgentEvent:
    """事件契约。大载荷走外部引用（{ "_ref": 路径 }），Phase 1 工具结果落地时启用。"""

    task_id: str
    type: EventType
    payload: Any = None                    # 事件载荷；大载荷放 {_ref: path}
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "taskId": self.task_id,
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


EventHandler = Callable[[AgentEvent], None]


class EventBus:
    """进程内内存发布订阅，按 task_id 过滤。

    - subscribe(task_id, handler)：强制携带 task_id，禁止无条件消费全总线。
    - 每个 task 保留有界事件历史，供迟到的消费者/回放使用（Phase 4 时间线回放依赖）。
    """

    def __init__(self, history_limit: int = 200) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: Dict[str, List[AgentEvent]] = {}
        self._history_limit = history_limit

    def subscribe(self, task_id: str, handler: EventHandler) -> Callable[[], None]:
        """订阅指定任务的事件。返回取消订阅函数。

        Raises:
            ValueError: task_id 为空 —— 禁止无条件消费全部总线事件。
        """
        if not task_id:
            raise ValueError("事件消费者必须携带 task_id（禁止无条件消费全部总线事件）")
        with self._lock:
            self._subscribers.setdefault(task_id, []).append(handler)
        return lambda: self.unsubscribe(task_id, handler)

    def unsubscribe(self, task_id: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._subscribers.get(task_id)
            if handlers and handler in handlers:
                handlers.remove(handler)
                if not handlers:
                    self._subscribers.pop(task_id, None)

    def publish(self, event: AgentEvent) -> None:
        """发布事件：写入该任务历史并按 task_id 分发给订阅者。"""
        with self._lock:
            history = self._history.setdefault(event.task_id, [])
            history.append(event)
            if len(history) > self._history_limit:
                del history[: len(history) - self._history_limit]
            handlers = list(self._subscribers.get(event.task_id, []))
        for handler in handlers:
            handler(event)

    def history(self, task_id: str) -> List[AgentEvent]:
        """按任务取历史事件（快照，供回放/迟到订阅）。"""
        with self._lock:
            return list(self._history.get(task_id, []))


# 全局单例：整个 Agent 内核共用同一条总线
_bus: Optional[EventBus] = None


def get_bus() -> EventBus:
    """进程内唯一事件总线（延迟初始化）。"""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus