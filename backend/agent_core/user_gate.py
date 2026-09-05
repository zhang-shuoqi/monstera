"""用户闸（User Gate）· Phase 2（设计定稿 v1.0 · 五）。

组成：
  1) RiskEvaluator —— 独立的参数级风险评估模块：输入「工具名 + 参数 + 任务上下文」，
     输出「直接放行 / 通知用户 / 弹窗确认」。判断逻辑硬编码，不写配置文件；
     V1 只实现 Windows 路径规则（macOS/Linux 预留接口后置）。
  2) UserGate —— 确认流：风险 CONFIRM 时循环暂停（状态 waiting_human），
     等用户点「允许 / 拒绝」；拒绝不终止任务，把拒绝信息作为观察回传模型重新决策。

规则表（V1 Windows 版，与设计定稿 v1.0 · 五一致；记忆工具已移出 Agent 工具箱，无相关规则）：
  - file_read 用户目录(桌面/文档/下载)         → allow  直接执行
  - file_read 系统目录                        → confirm 弹窗确认
  - file_write / file_edit 写系统目录          → confirm 弹窗确认
  - file_write / file_edit 修改任务自己创建文件  → notify 直接执行+面板通知
  - file_write 覆盖用户已有文件 / 新建文件      → confirm（已有）/ notify（新建）
  - file_edit 编辑用户已有文件                 → confirm（修改用户文件属高风险）
  - list_dir 用户目录                        → allow
  - list_dir 系统根目录                       → notify 面板通知
  - 未知工具                                 → confirm（保守：不在 V1 冻结集一律拦截确认）
"""
from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .events import AgentEvent, EventBus, EventType, get_bus, human_intervention_required_event

# ---------- 风险分级 ----------

ALLOW = "allow"        # 直接执行
NOTIFY = "notify"      # 直接执行，右侧面板/事件流需通知用户
CONFIRM = "confirm"    # 弹窗确认（循环暂停，状态 waiting_human）


@dataclass
class RiskDecision:
    level: str          # ALLOW / NOTIFY / CONFIRM
    reason: str         # 给用户看的原因说明


# ---------- Windows 系统目录硬编码规则（V1 只实现 Windows） ----------

# 设计定稿 v1.0 · 五 关键实现要求 1：维护 SYSTEM_PATH_PATTERNS 数组（Windows 版），单元测试覆盖。
# 大小写不敏感；统一用反斜杠比较。
_SYSTEM_PATH_PATTERNS: List[re.Pattern] = [
    re.compile(r"^[a-z]:\\windows(\\|$)", re.IGNORECASE),
    re.compile(r"^[a-z]:\\program files( \(x86\))?(\\|$)", re.IGNORECASE),
    re.compile(r"^[a-z]:\\programdata(\\|$)", re.IGNORECASE),
    re.compile(r"^[a-z]:\\\$recycle\.bin(\\|$)", re.IGNORECASE),
    re.compile(r"^[a-z]:\\system volume information(\\|$)", re.IGNORECASE),
]


def normalize_path(path: Any) -> str:
    """统一为反斜杠、小写的绝对路径字符串（只用于规则比对，不触碰文件系统）。"""
    p = str(path or "").strip().strip('"')
    return os.path.normcase(os.path.abspath(p))


def is_system_path(path: Any) -> bool:
    """是否属于 Windows 系统目录（硬编码模式匹配）。"""
    norm = normalize_path(path)
    for pat in _SYSTEM_PATH_PATTERNS:
        if pat.match(norm):
            return True
    return False


def _user_dir_patterns() -> Set[str]:
    """用户目录（桌面/文档/下载）的规范化前缀集合。"""
    home = Path.home()
    base = [home / "Desktop", home / "Documents", home / "Downloads"]
    out: Set[str] = set()
    for d in base:
        out.add(os.path.normcase(str(d)).rstrip("\\/"))
    return out


def is_user_path(path: Any) -> bool:
    """是否位于用户目录（桌面/文档/下载）之下。"""
    norm = normalize_path(path)
    for prefix in _user_dir_patterns():
        if norm.startswith(prefix):
            return True
    return False


# ---------- RiskEvaluator ----------

class RiskEvaluator:
    """参数级风险评估。纯函数式：不阻塞、不落盘，只返回 RiskDecision。

    created_files：本次任务自己创建过的文件集合（存在集合内 → 覆盖自己文件只是 notify）。
    """

    def evaluate(self, tool_name: str, args: Dict[str, Any], created_files: Optional[Set[str]] = None) -> RiskDecision:
        params = args or {}
        created = {normalize_path(p) for p in (created_files or [])}
        path = params.get("path")

        # ---- 文件工具 ----
        if tool_name == "file_read":
            if path is None:
                return RiskDecision(ALLOW, "file_read 缺少 path，将由工具校验")
            return RiskDecision(CONFIRM, f"读取系统目录文件属高风险：{path}") if is_system_path(path) \
                else RiskDecision(ALLOW, "读取用户目录/普通路径文件，低风险")

        if tool_name == "file_write":
            if path is None:
                return RiskDecision(ALLOW, "file_write 缺少 path，将由工具校验")
            if is_system_path(path):
                return RiskDecision(CONFIRM, f"写入系统目录属高风险：{path}")
            norm = normalize_path(path)
            if norm in created:
                # 本次任务自己创建过的文件：覆盖只需面板通知，不弹窗（设计定稿 v1.0 · 五）
                return RiskDecision(NOTIFY, f"覆盖本次任务自己创建的文件（面板通知）：{path}")
            if os.path.exists(path):
                # 用户之前就有的文件：覆盖属高风险，弹窗确认
                return RiskDecision(CONFIRM, f"覆盖用户已有文件属高风险：{path}")
            return RiskDecision(NOTIFY, f"写入新文件（面板通知）：{path}")

        # file_edit（Phase 6 精确编辑）：写操作，风险分级与 file_write 对齐
        if tool_name == "file_edit":
            if path is None:
                return RiskDecision(ALLOW, "file_edit 缺少 path，将由工具校验")
            if is_system_path(path):
                return RiskDecision(CONFIRM, f"编辑系统目录文件属高风险：{path}")
            norm = normalize_path(path)
            if norm in created:
                # 编辑本次任务自己创建的文件：只需面板通知
                return RiskDecision(NOTIFY, f"编辑本次任务自己创建的文件（面板通知）：{path}")
            if os.path.exists(path):
                # 修改用户已有文件：属高风险，弹窗确认
                return RiskDecision(CONFIRM, f"编辑用户已有文件属高风险（将修改文件内容）：{path}")
            return RiskDecision(CONFIRM, f"编辑不存在的文件（将由工具校验）：{path}")

        if tool_name == "list_dir":
            if path is None:
                return RiskDecision(ALLOW, "list_dir 缺少 path，将由工具校验")
            return RiskDecision(NOTIFY, f"列系统根目录（面板通知）：{path}") if is_system_path(path) \
                else RiskDecision(ALLOW, "列用户目录/普通路径，低风险")

        # ---- 未知工具：保守拦截（记忆工具已移出工具箱，不再有专用规则） ----
        if tool_name == "fake_probe":
            return RiskDecision(ALLOW, "空循环演示工具")
        return RiskDecision(CONFIRM, f"未知工具（不在 V1 冻结集）：{tool_name}")


# ---------- UserGate：确认流 ----------

@dataclass
class UserGate:
    """确认流实现。

    - guard()：循环引擎调用。CONFIRM 时发布 HUMAN_INTERVENTION_REQUIRED 事件、
      阻塞等待用户选择，再返回 允许/拒绝。
    - resolve()：由外部（如危险操作弹窗的「允许/拒绝」按钮 → HTTP 端点）唤醒等待。
    - auto_allow_overwrite：Phase 5 高级选项——覆盖已有文件时不弹窗（降为 NOTIFY，仍通知）。
      系统目录写入不被此选项影响（永远 CONFIRM，绝不静默放行）。
    """
    evaluator: RiskEvaluator = field(default_factory=RiskEvaluator)
    bus: Optional[EventBus] = None
    wait_timeout_s: float = 300.0   # 用户确认最长等待；超时视为拒绝（安全默认，永不静默放行）
    auto_allow_overwrite: bool = False

    def __post_init__(self) -> None:
        self._bus = self.bus or get_bus()
        self._lock = threading.RLock()
        self._waiters: Dict[str, threading.Event] = {}
        self._results: Dict[str, Dict[str, Any]] = {}

    def guard(self, task_id: str, tool_name: str, args: Any, created_files: Optional[Set[str]] = None) -> Dict[str, Any]:
        """循环引擎在【执行工具前】调用。返回：
            {"denied": bool, "reason": str, "level": str}
        denied=True 表示用户拒绝 → 循环引擎不得执行工具，把 reason 作为观察回传模型。
        """
        decision = self.evaluator.evaluate(tool_name, args, created_files)

        # Phase 5 高级选项：覆盖已有文件降级为通知（不进弹窗确认流程；file_edit 同规则）
        if (self.auto_allow_overwrite and decision.level == CONFIRM
                and tool_name in ("file_write", "file_edit")
                and ("覆盖用户已有文件" in decision.reason or "编辑用户已有文件" in decision.reason)):
            decision = RiskDecision(NOTIFY, decision.reason + "（已开启自动放行覆盖，仅通知）")

        if decision.level == CONFIRM:
            # 发布"需要用户确认"事件（右侧面板据此显示等待状态 / 弹窗）
            self._bus.publish(human_intervention_required_event(
                task_id, tool_name, args, decision.reason, decision.level))
            outcome = self._await(task_id)
            if outcome.get("allow"):
                return {"denied": False, "reason": decision.reason, "level": decision.level}
            return {"denied": True, "reason": self._denial_message(tool_name, args, outcome.get("reason", "用户点击了'拒绝'按钮")), "level": decision.level}

        if decision.level == NOTIFY:
            # 通知不阻塞：面板经事件流的 TOOL_CALL_REQUESTED（带风险注解）感知
            return {"denied": False, "reason": decision.reason, "level": decision.level}

        return {"denied": False, "reason": decision.reason, "level": decision.level}

    def resolve(self, task_id: str, allow: bool, reason: str = "") -> bool:
        """用户作出决定：allow=True 放行，allow=False 拒绝（reason 说明原因）。"""
        with self._lock:
            self._results[task_id] = {"allow": bool(allow), "reason": (reason or "").strip()}
            waiter = self._waiters.get(task_id)
            if waiter:
                waiter.set()
            return waiter is not None

    def _await(self, task_id: str) -> Dict[str, Any]:
        """阻塞等待用户选择（带超时；超时按拒绝处理，绝不静默放行）。

        已登记过结果（resolve 先于注册 waiter 到达）时立即消费，避免丢决定。
        """
        ev = threading.Event()
        with self._lock:
            existing = self._waiters.get(task_id)
            if existing is not None:
                return {"allow": False, "reason": "该任务已有一个待确认的弹窗尚未处理"}
            self._waiters[task_id] = ev
            pre_result = self._results.get(task_id)
        if pre_result is not None:
            return self._consume(task_id)
        ev.wait(timeout=self.wait_timeout_s)   # 阻塞直到用户选择（resolve 唤醒）
        return self._consume(task_id)

    def _consume(self, task_id: str) -> Dict[str, Any]:
        with self._lock:
            self._waiters.pop(task_id, None)
            result = self._results.pop(task_id, None)
        if result is None:
            return {"allow": False, "reason": "等待用户确认超时，已自动拒绝（安全默认，不静默放行）"}
        return result

    @staticmethod
    def _denial_message(tool_name: str, args: Any, user_reason: str) -> str:
        """用户拒绝后回传给模型的统一信息（设计定稿 v1.0 · 五 · 拒绝后的循环走向）。"""
        args_txt = json.dumps(args, ensure_ascii=False) if args not in (None, "") else "{}"
        return (
            f"用户拒绝了工具调用：{tool_name}({args_txt})。"
            f"拒绝原因：{user_reason}。"
            f"请基于此信息重新决策：换方案、跳过此步骤、或终止任务。"
        )