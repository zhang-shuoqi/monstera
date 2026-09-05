"""循环引擎（The Loop）· Phase 0 空循环（设计定稿 v1.0 · 三）。

Phase 0 只做最小循环体：
    模型说调工具 → 系统【假装】执行 → 返回【假】结果 → 模型再决策 → … → 模型直接回答 → 完成
要求：能转 N 圈（≥3）不崩。

关键约束（铁律）：
  - 循环引擎不感知工具语义、不感知状态存储——只认 ModelDriver / ToolExecutor 两个标准协议，
    通过事件总线对外发布进展（INTENT_RECEIVED…TASK_COMPLETED / TASK_FAILED）。
  - 机械硬保护（与模型无关）：单任务最大迭代轮次 / 最大工具调用次数 / 单步最大执行时间。
    Phase 0 假工具瞬时完成，单步超时暂只保留配置参数（真实超时 kill 随 Phase 1 真工具落地）。
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Set

from .events import (
    EventBus,
    intent_received_event,
    objective_defined_event,
    step_started_event,
    tool_call_requested_event,
    tool_result_received_event,
    observation_ready_event,
    task_completed_event,
    task_failed_event,
)
from .toolbox import ToolResult

log = logging.getLogger("monstera.agent")


# ---------- 标准协议（循环引擎只认这两个） ----------

@dataclass
class Observation:
    """一次工具调用结果的观察摘要：直接交给模型决策。"""
    step: int
    tool_name: str
    success: bool
    summary: str                  # 给模型看的摘要文本
    raw: Any = field(default=None, repr=False)   # 原始结果（大载荷走 _ref，Phase 1 起用）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "toolName": self.tool_name,
            "success": self.success,
            "summary": self.summary,
        }


@dataclass
class ModelDecision:
    """模型一次决策的输出：要么『直接回答』，要么『调用某工具』。"""
    kind: str                     # "final_answer" | "tool_call"
    content: Any = None           # final_answer: 回答文本；tool_call: 参数对象
    tool_name: Optional[str] = None


class ModelDriver(Protocol):
    """模型驱动协议：输入上下文，输出决策。Phase 0 用假模型实现。"""

    def decide(self, objective: str, history: List[Observation]) -> ModelDecision: ...


class ToolExecutor(Protocol):
    """工具执行协议：按名字+参数执行，返回 ToolResult（Phase 1 用真实注册表实现）。"""

    def execute(self, name: str, args: Any) -> ToolResult: ...


# ---------- 机械硬保护配置 ----------

@dataclass
class LoopGuardConfig:
    """可配置机械硬保护（设计定稿 v1.0 · 三）。Phase 5 设置面板可调，这里落默认值。"""
    max_iterations: int = 50       # 达到强制终止（用户可配 10~500）
    max_tool_calls: int = 30       # 达到强制终止（用户可配 10~300）
    step_timeout_s: float = 60.0   # 单步最大执行时间（用户可配 10~600；真实 kill 随真工具落地）


# ---------- Phase 0 假模型 / 假工具 ----------

class ScriptedFakeModel:
    """Phase 0/2 假模型：按脚本决策。

    两种模式（都只决定"调哪个工具"，真正执行走 ToolExecutor）：
      1) rounds 模式（默认）——连续调 fake_probe 工具 rounds 次后给最终答复，
         用于验证空循环能转 N 圈不崩。
      2) plan 模式——按给定计划逐步调用【真实】工具（Phase 1 验收用）。
         Phase 2 起每个计划步可选 fallback：上一步被用户拒绝时，模型自动换方案
         走 fallback（验证"用户拒绝后模型能换方案"）。真实模型（Function Calling）接 Phase 3。
    """

    def __init__(
        self,
        rounds: int = 3,
        plan: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self._rounds = rounds
        self._plan = list(plan or [])   # 每项: {"tool","args","fallback":{"tool","args"}?}
        self._idx = 0
        self._used_fallback = set()     # 已用过的 fallback 索引（防止拒绝-重试死循环）

    def decide(self, objective: str, history: List[Observation]) -> ModelDecision:
        if self._plan:
            # 上一步被用户拒绝 → 换方案（优先走当前计划步声明的 fallback，只换一次）
            if history and not history[-1].success and "用户拒绝" in history[-1].summary:
                denied_idx = self._idx - 1
                denied_step = self._plan[denied_idx] if 0 <= denied_idx < len(self._plan) else None
                if (isinstance(denied_step, dict) and denied_step.get("fallback")
                        and denied_idx not in self._used_fallback):
                    self._used_fallback.add(denied_idx)
                    fb = denied_step["fallback"]
                    return ModelDecision(kind="tool_call", tool_name=fb["tool"], content=fb.get("args", {}))
            if self._idx < len(self._plan):
                step = self._plan[self._idx]
                self._idx += 1
                return ModelDecision(kind="tool_call", tool_name=step["tool"], content=step.get("args", {}))
            return ModelDecision(
                kind="final_answer",
                content=f"按计划处理完毕，目标『{objective}』已处理。",
            )
        if len(history) >= self._rounds:
            return ModelDecision(
                kind="final_answer",
                content=f"空循环演示完成：转了 {self._rounds} 圈，目标『{objective}』已处理。",
            )
        return ModelDecision(kind="tool_call", content={"n": len(history) + 1}, tool_name="fake_probe")


class FakeToolbox:
    """Phase 0 假工具：不接触真实文件系统，立即返回假结果。"""

    def execute(self, name: str, args: Any) -> ToolResult:
        return ToolResult(success=True, data={"args": args if args is not None else {}, "fake": True})


# ---------- 循环引擎 ----------

@dataclass
class LoopOutcome:
    ok: bool                      # True: TASK_COMPLETED；False: 硬保护/异常终止（TASK_FAILED）
    reason: str
    iterations: int
    tool_calls: int


class LoopEngine:
    """模型-工具-观察循环。只做三件事：
        1) 把目标与观察历史交给 ModelDriver；
        2) 把工具调用交给 ToolExecutor（或先过用户闸）；
        3) 通过事件总线发布每一步进展。
    状态迁移（idle→executing→completed/failed/waiting_human）不由循环引擎直接改存储，
    由订阅总线的 StateProjector（runtime 层）负责——UI/存储全程走事件管道。

    用户闸（Phase 2，可选）：gate 非空时，每次工具调用前调用 gate.guard()。
      - 风险 ALLOW/NOTIFY：直接执行；
      - 风险 CONFIRM：guard 内部阻塞等待用户允许/拒绝；
      - 用户拒绝：不执行工具，把拒绝信息包装成 Observation 回传模型（拒绝后重决策）。
    拒绝后循环不终止、不卡死，模型基于拒绝观察重新决策。
    """

    def __init__(self, bus: EventBus, guard: Optional[LoopGuardConfig] = None) -> None:
        self._bus = bus
        self._guard = guard or LoopGuardConfig()
        self._iterations = 0
        self._tool_calls = 0

    @property
    def guard_config(self) -> LoopGuardConfig:
        return self._guard

    @guard_config.setter
    def guard_config(self, g: LoopGuardConfig) -> None:
        if g is not None:
            self._guard = g

    def run(self, task_id: str, objective: str, model: ModelDriver, executor: ToolExecutor,
            gate: Optional[Any] = None, created_files_fn: Optional[Callable[[], Optional[Set[str]]]] = None,
            stop_event: Optional[threading.Event] = None) -> LoopOutcome:
        """模型-工具-观察循环编排骨架：各阶段见下方私有方法，顺序与事件点与修复前完全一致。"""
        self._iterations = 0; self._tool_calls = 0; history: List[Observation] = []
        self._bus.publish(intent_received_event(task_id, objective))
        self._bus.publish(objective_defined_event(task_id, objective))
        while True:
            out = self._check_stop_or_abort(task_id, stop_event) or self._guard_iterations(task_id)
            if out is not None:
                return out
            self._iterations += 1
            log.info("task=%s step=%d", task_id, self._iterations)
            self._bus.publish(step_started_event(task_id, self._iterations))
            decision, out = self._model_decide(task_id, objective, history, model)
            if out is not None:
                return out
            if decision.kind == "final_answer":
                return self._handle_final_answer(task_id, decision)
            out = self._handle_tool_call(task_id, decision)
            if out is not None:
                return out
            gate_result = self._user_gate(task_id, decision, gate, created_files_fn)
            if gate_result.get("denied"):
                denied = Observation(step=self._iterations, tool_name=decision.tool_name,
                                     success=False, summary=gate_result["reason"])
                history.append(denied); self._emit_observation(task_id, denied); continue
            success, data, error = self._execute_tool(task_id, decision, executor)
            obs = self._build_observation(decision, success, data, error)
            history.append(obs); self._emit_observation(task_id, obs)

    # ---------- 阶段（私有）：顺序与逻辑与原单函数完全一致 ----------

    def _check_stop_or_abort(self, task_id: str, stop_event: Optional[threading.Event]) -> Optional[LoopOutcome]:
        """① 用户手动停止：中断视为失败，收敛到终态。"""
        if stop_event is not None and stop_event.is_set():
            self._bus.publish(task_failed_event(
                task_id, "user_stopped", "任务已被用户手动停止（用户在 UI 上中断运行）"))
            return LoopOutcome(ok=False, reason="user_stopped",
                               iterations=self._iterations, tool_calls=self._tool_calls)
        return None

    def _guard_iterations(self, task_id: str) -> Optional[LoopOutcome]:
        """② 机械硬保护 1：迭代轮次上限。"""
        if self._iterations >= self._guard.max_iterations:
            return self._fail(
                task_id, "任务因超出安全限制停止（当前：迭代轮次 %d ≥ %d）" % (self._iterations, self._guard.max_iterations)
            )
        return None

    def _model_decide(self, task_id: str, objective: str, history: List[Observation],
                      model: ModelDriver) -> tuple[Optional[ModelDecision], Optional[LoopOutcome]]:
        """④ 模型决策；交互失败 → 任务失败（不把异常抛穿循环）。"""
        try:
            return model.decide(objective, list(history)), None
        except Exception as exc:
            log.error("task=%s 模型决策失败: %s", task_id, exc)
            reason = f"模型决策失败：{exc}"
            self._bus.publish(task_failed_event(task_id, "model_error", reason))
            return None, LoopOutcome(ok=False, reason="model_error",
                                     iterations=self._iterations, tool_calls=self._tool_calls)

    def _handle_final_answer(self, task_id: str, decision: ModelDecision) -> LoopOutcome:
        """⑤ 直接回答 → 任务完成。"""
        self._bus.publish(task_completed_event(
            task_id, decision.content, self._iterations, self._tool_calls))
        return LoopOutcome(ok=True, reason="completed",
                           iterations=self._iterations, tool_calls=self._tool_calls)

    def _handle_tool_call(self, task_id: str, decision: ModelDecision) -> Optional[LoopOutcome]:
        """⑥⑦⑧ 工具调用：非法决策防护 + 机械硬保护 2：工具调用次数上限。"""
        if decision.kind != "tool_call" or not decision.tool_name:
            self._bus.publish(task_failed_event(task_id, "invalid_model_decision", str(decision)))
            return LoopOutcome(ok=False, reason="invalid_model_decision",
                               iterations=self._iterations, tool_calls=self._tool_calls)
        if self._tool_calls >= self._guard.max_tool_calls:
            return self._fail(
                task_id, "任务因超出安全限制停止（当前：工具调用 %d ≥ %d）" % (self._tool_calls, self._guard.max_tool_calls)
            )
        self._tool_calls += 1
        return None

    def _user_gate(self, task_id: str, decision: ModelDecision, gate: Optional[Any],
                   created_files_fn: Optional[Callable[[], Optional[Set[str]]]]) -> Dict[str, Any]:
        """⑨ 用户闸（Phase 2）：执行前评估风险；CONFIRM 阻塞等用户，拒绝则 denied=True。"""
        if gate is None:
            return {"denied": False, "reason": "", "level": "allow"}
        created = created_files_fn() if created_files_fn else None
        return gate.guard(task_id, decision.tool_name, decision.content, created)

    def _execute_tool(self, task_id: str, decision: ModelDecision, executor: ToolExecutor) -> tuple[bool, Any, Any]:
        """⑩⑪⑫⑬ 发布调用事件 → 线程执行（单步超时）→ 发布结果事件。"""
        self._bus.publish(tool_call_requested_event(
            task_id, decision.tool_name, decision.content, self._tool_calls))
        try:
            ret: Dict[str, Any] = {}
            worker = threading.Thread(
                target=self._run_tool_guarded,
                args=(executor, decision.tool_name, decision.content, ret),
                daemon=True,
            )
            worker.start()
            worker.join(timeout=self._guard.step_timeout_s)
            if worker.is_alive():
                # 单步超时：线程仍在跑（本地工具无法强杀），观察记录为超时失败
                success, data, error = False, None, f"工具执行超时（>{self._guard.step_timeout_s}s），已终止该步骤"
            else:
                success = bool(ret.get("success"))
                data = ret.get("data")
                error = ret.get("error")
        except Exception as exc:  # 工具抛错 → 观察为失败，仍回传模型再决策
            success, data, error = False, None, str(exc)
        self._bus.publish(tool_result_received_event(task_id, decision.tool_name, success, error, data))
        return success, data, error

    def _build_observation(self, decision: ModelDecision, success: bool, data: Any, error: Any) -> Observation:
        """⑭ 整理为观察，回传模型（大载荷原样保留在 raw，摘要截断）。"""
        summary = f"[{decision.tool_name}] 已返回" + (f"：{data}" if data is not None else "") + (f"（错误：{error}）" if error else "")
        if len(str(summary)) >= 500:
            summary = f"[{decision.tool_name}] 已返回（结果过长，已截断）"
        return Observation(
            step=self._iterations,
            tool_name=decision.tool_name,
            success=success,
            summary=summary,
            raw=data,
        )

    def _emit_observation(self, task_id: str, obs: Observation) -> None:
        self._bus.publish(observation_ready_event(task_id, obs.to_dict()))

    # ---------- 内部 ----------

    @staticmethod
    def _run_tool_guarded(executor, name: str, args: Any, out: Dict[str, Any]) -> None:
        """在线程中执行工具并回填结果（供单步超时 join 使用）。"""
        try:
            result = executor.execute(name, args)
            if isinstance(result, ToolResult):
                out["success"] = result.success
                out["data"] = result.data
                out["error"] = result.error
            else:
                out["success"] = True
                out["data"] = result
                out["error"] = None
        except Exception as exc:
            out["success"] = False
            out["data"] = None
            out["error"] = str(exc)

    def _fail(self, task_id: str, reason: str) -> LoopOutcome:
        self._bus.publish(task_failed_event(task_id, "guard_limit", reason))
        return LoopOutcome(ok=False, reason="guard_limit", iterations=self._iterations, tool_calls=self._tool_calls)