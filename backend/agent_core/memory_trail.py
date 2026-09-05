"""Agent 原子记忆（移植 TencentDB Agent-Memory 的可本地落地语义，按 Monstera 契约重写）。

移植要点（不 import 任何外部项目）：
  - Tencent 四层记忆金字塔的 L0→L1：L0=原始事件时间线（Monstera 已有 events/*.jsonl 回放），
    L1=从任务自动提炼的「原子记忆」（目标/结果/关键步骤/失败原因/创建文件），跨会话复用——
    解决"每次会话像一个全新 Agent / 重蹈覆辙"，这是 Monstera 记忆中枢（记忆文档）之外的 Agent 维度记忆。
  - 上下文注入带 token 预算封顶（Tencent 的 recall cap）：检索到的记忆只取最相关几条且限总字符数。

铁律：
  - 本模块是事件总线的普通消费者（subscribe(task_id)），与 StateProjector 平级：
    不拦截、不修改任何状态，只读事件并提炼记忆。禁止直接调用状态存储。
  - 事件消费者必须携带 task_id 过滤（events.py 强制）。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .events import (
    K_ANSWER,
    K_DATA,
    K_DETAIL,
    K_OBJECTIVE,
    K_REASON,
    K_SUCCESS,
    K_TOOL,
    AgentEvent,
    EventType,
    get_bus,
)

# 每条原子记忆写入时保留的最大步数 / 每条记忆注入上下文的最大字符数 / 单次注入总预算
MAX_TRACKED_STEPS = 40
MEMORY_LINE_MAX_CHARS = 600
RECALL_MAX_CHARS = 2500
RECALL_TOP_K = 3
MEMORY_FILE_MAX_ROWS = 300   # 记忆上限（超出裁剪最旧），防文件无限膨胀


@dataclass
class Memory:
    """一条原子记忆：一个任务的经验沉淀。"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    objective: str = ""
    outcome: str = "failed"                  # "completed" | "failed"
    answer: Optional[str] = None             # 完成时的最终答复（截断）
    fail_reason: Optional[str] = None        # 失败时的原因（截断）
    steps: List[Dict[str, Any]] = field(default_factory=list)   # [{tool, ok, hint}]
    created_files: List[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)

    def to_compact(self) -> str:
        """压缩成可注入上下文的单段文本（带预算截断）。"""
        head = self.objective[:80]
        tag = "完成" if self.outcome == "completed" else "失败"
        raw = (self.answer or "").strip() if self.outcome == "completed" else (self.fail_reason or "").strip()
        tail = raw.replace("\n", " ")[:200]
        result_txt = f"结果: {tail}" if tail else "无结论"
        body = f"[历史经验 {tag}] 目标：{head}。{result_txt}"
        if self.steps:
            step_txt = "，".join(
                f"{s.get('tool', '?')}{'✓' if s.get('ok') else '✗'}" for s in self.steps[:8]
            )
            body += f"。关键步骤：{step_txt}"
        if self.created_files:
            body += f"。产物文件：{'; '.join(p.rsplit(chr(92), 1)[-1] for p in self.created_files[:5])}"
        return body[:MEMORY_LINE_MAX_CHARS]


class MemoryTrail:
    """按任务订阅事件 → 终态提炼原子记忆落盘 → recall 按目标检索注入。"""

    def __init__(self, data_dir: Path, max_rows: int = MEMORY_FILE_MAX_ROWS) -> None:
        self._lock = threading.RLock()
        self._data_dir = Path(data_dir)
        self._file = self._data_dir / "memory.jsonl"
        self._max_rows = max_rows
        self._unsub_map: Dict[str, Callable[[], None]] = {}
        self._buffers: Dict[str, Dict[str, Any]] = {}   # task_id -> 运行期轨迹缓冲
        self._memories: List[Memory] = []                # 全部原子记忆（新→旧）

    # ---------- 生命周期接线（与 StateProjector 平级，由 AgentCore 调用） ----------

    def attach(self, task_id: str) -> None:
        """订阅某任务事件开始跟踪（create_task 时调用）。"""
        unsub = get_bus().subscribe(task_id, self._on_event)
        with self._lock:
            self._unsub_map[task_id] = unsub
            self._buffers.setdefault(task_id, {"objective": "", "steps": [], "files": []})

    def detach(self, task_id: str) -> None:
        """取消订阅（删除任务时调用）。"""
        with self._lock:
            unsub = self._unsub_map.pop(task_id, None)
            if unsub is not None:
                unsub()
            self._buffers.pop(task_id, None)

    def detach_all(self) -> None:
        with self._lock:
            for fn in self._unsub_map.values():
                fn()
            self._unsub_map.clear()
            self._buffers.clear()

    # ---------- 检索（LLMDriver 读上下文用） ----------

    def recall(self, objective: str, top_k: int = RECALL_TOP_K,
               max_chars: int = RECALL_MAX_CHARS) -> List[str]:
        """按目标词项打分取 TopK 记忆，转紧凑文本，总字符数预算封顶。"""
        q = objective or ""
        if not q:
            return []
        scored = sorted(
            ((self._score(q, m), m) for m in self._memories),
            key=lambda pair: pair[0],
            reverse=True,
        )
        out: List[str] = []
        total = 0
        for score, mem in scored:
            if score <= 0:
                break
            text = mem.to_compact()
            if total + len(text) > max_chars:
                break
            out.append(text)
            total += len(text)
            if len(out) >= top_k:
                break
        return out

    # ---------- 事件消费 ----------

    def _on_event(self, event: AgentEvent) -> None:
        with self._lock:
            buf = self._buffers.get(event.task_id)
            if buf is None:
                return    # 未跟踪任务的事件：静默忽略（照铁律只处理自己负责的任务）
            self._track(event, buf)

    def _track(self, event: AgentEvent, buf: Dict[str, Any]) -> None:
        payload = event.payload or {}
        if event.type == EventType.OBJECTIVE_DEFINED:
            obj = payload.get(K_OBJECTIVE) if isinstance(payload, dict) else None
            if obj:
                buf["objective"] = str(obj)
        elif event.type == EventType.TOOL_RESULT_RECEIVED:
            if isinstance(payload, dict):
                tool = payload.get(K_TOOL)
                ok = bool(payload.get(K_SUCCESS))
                hint = ""
                data = payload.get(K_DATA)
                if isinstance(data, dict) and data.get("path"):
                    hint = str(data.get("path"))
                elif data and isinstance(data, (str, dict)):
                    hint = str(data)[:120].replace("\n", " ")
                if payload.get(K_TOOL) == "file_write" and ok and isinstance(data, dict) \
                        and data.get("mode") == "created" and data.get("path"):
                    buf["files"].append(str(data["path"]))
                buf["steps"].append({"tool": tool, "ok": ok, "hint": hint})
                if len(buf["steps"]) > MAX_TRACKED_STEPS:
                    buf["steps"] = buf["steps"][-MAX_TRACKED_STEPS:]
        elif event.type == EventType.TASK_COMPLETED:
            answer = payload.get(K_ANSWER) if isinstance(payload, dict) else None
            self._commit(event.task_id, "completed", answer=answer)
        elif event.type == EventType.TASK_FAILED:
            reason = ""
            if isinstance(payload, dict):
                reason = payload.get(K_DETAIL) or payload.get(K_REASON) or ""
            self._commit(event.task_id, "failed", fail_reason=str(reason))

    def _commit(self, task_id: str, outcome: str, answer: Any = None,
                fail_reason: str = "") -> None:
        """任务终态 → 提炼原子记忆 → 去重落盘。"""
        with self._lock:
            buf = self._buffers.pop(task_id, None)
            unsub = self._unsub_map.pop(task_id, None)
        if buf is None:
            return
        if unsub is not None:
            unsub()
        objective = (buf.get("objective") or "").strip()
        if not objective:
            objective = "(无明确目标)"
        mem = Memory(
            objective=objective[:200],
            outcome=outcome,
            answer=(str(answer or "")[:500]) if answer else None,
            fail_reason=(str(fail_reason or "")[:300]) if fail_reason else None,
            steps=buf.get("steps", [])[-MAX_TRACKED_STEPS:],
            created_files=list(dict.fromkeys(buf.get("files", [])))[:20],
        )
        with self._lock:
            self._memories.insert(0, mem)
            if len(self._memories) > self._max_rows:
                del self._memories[self._max_rows:]
            if self._memories[0] is mem:
                self._flush()

    def _flush(self) -> None:
        """全量重写记忆文件（行式 JSON，原子写）。"""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self._data_dir), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for m in self._memories:
                    f.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")
            os.replace(tmp, self._file)
        except OSError:
            pass    # 记忆落盘失败不阻塞内核（可降级为仅内存）

    # ---------- 恢复/索引 ----------

    def restore(self) -> int:
        """启动时从 memory.jsonl 读回历史原子记忆（进程重启后仍可召回）。"""
        rows: List[Memory] = []
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            if self._file.exists():
                for line in self._file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(Memory(**json.loads(line)))
                    except (TypeError, ValueError):
                        continue
        except OSError:
            pass
        rows.sort(key=lambda m: m.ts, reverse=True)   # 新→旧
        with self._lock:
            self._memories = rows[: self._max_rows]
        return len(rows)

    # ---------- 内部 ----------

    @staticmethod
    def _tokens(text: str) -> set:
        """轻量词项：英文单词 + 中文连续段的 2-gram（无需分词依赖）。"""
        tokens: set = set()
        for w in re.findall(r"[a-zA-Z0-9_\-]{2,}", text):
            tokens.add(w.lower())
        for seg in re.findall(r"[\u4e00-\u9fff]+", text):
            for i in range(len(seg) - 1):
                tokens.add(seg[i : i + 2])
        return tokens

    @classmethod
    def _score(cls, query: str, mem: Memory) -> int:
        q = cls._tokens(query)
        t = cls._tokens(mem.objective)
        hit = len(q & t)
        if hit == 0:
            return 0
        bonus = 0
        if query in mem.objective or mem.objective in query:
            bonus = 6
        return hit * 2 + bonus