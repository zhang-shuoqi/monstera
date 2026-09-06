"""任务状态存储（设计定稿 v1.0 · 八）。

职责：
  1) 定义"一个任务在内存里长什么样"（TaskState）
  2) 内存状态原子落盘到本地 JSON（snapshot 文件 + 历史索引表）
  3) 软件启动时从本地 JSON 恢复

存储布局（单用户本地，无任何用户/租户字段）：
    agent_data/
      index.json                   历史任务表（一张表，对标 SQLite 单表）
      tasks/{task_id}.json         每个任务的完整快照（含事件时间线引用）

安全不变量（State Machine，遵循 staff-engineer-mode:state-machine-correctness）：
  - 状态只允许沿 ALLOWED_TRANSITIONS 给定的方向迁移，非法迁移直接抛错——
    例如已完成任务禁止重跑、idle 禁止直接跳到 completed。
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"


# 状态机合法迁移表：old -> 允许的 new 集合
# 设计依据：空循环 idle→executing→completed；用户闸（Phase 2）引入 waiting_human；
#          Phase 5 Plan 确认在首个 STEP_STARTED 之前发生，允许 idle→waiting_human；
#          硬保护/拒绝/异常收敛到 failed。
ALLOWED_TRANSITIONS: Dict[TaskStatus, set] = {
    TaskStatus.IDLE: {TaskStatus.EXECUTING, TaskStatus.WAITING_HUMAN, TaskStatus.FAILED},
    TaskStatus.EXECUTING: {TaskStatus.WAITING_HUMAN, TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.WAITING_HUMAN: {TaskStatus.EXECUTING, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),        # 终态：不可再迁移
    TaskStatus.FAILED: set(),           # 终态：不可再迁移
}


class IllegalTransitionError(RuntimeError):
    """状态机非法迁移（should never happen）。"""


@dataclass
class TaskState:
    task_id: str
    objective: str
    status: TaskStatus = TaskStatus.IDLE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    # 循环引擎机械计数（与模型无关，硬保护实现基于它们）
    loop_iterations: int = 0
    tool_call_count: int = 0
    # 终止信息
    final_answer: Optional[str] = None
    fail_reason: Optional[str] = None
    # 覆盖判断：本次任务自己创建过的文件集合（任务开始时记录 → 运行中累积）
    created_files: List[str] = field(default_factory=list)
    # Phase 3：模型 token 用量（成本感知前置记录，界面展示用）
    model_usage: Dict[str, int] = field(default_factory=dict)
    # Phase 5：预估费用（¥），由路由层依据计费规则写入
    estimated_cost: Optional[float] = None
    # 快照路径（历史索引表引用），由 Storage 维护
    snapshot_path: Optional[str] = None
    # Phase 6 交互增强：显示标题（右键重命名，与对话一致；缺省回退 objective）与置顶标记
    title: Optional[str] = None
    pinned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    def to_meta(self) -> Dict[str, Any]:
        """历史任务表行：taskId/objective/status/createdAt/completedAt/snapshotPath"""
        return {
            "taskId": self.task_id,
            "objective": self.objective,
            "title": self.title,
            "pinned": self.pinned,
            "status": self.status.value,
            "createdAt": self.created_at,
            "completedAt": self.completed_at,
            "snapshotPath": self.snapshot_path,
        }


def _now() -> float:
    return time.time()


def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
    """原子写：先写临时文件再 rename，避免半截 JSON 损坏（崩溃安全）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class StateStore:
    """任务状态存储：内存活字典 + 磁盘快照/索引。进程内单实例使用，加锁保证主从一致。"""

    def __init__(self, data_dir: Path) -> None:
        self._lock = threading.RLock()
        self._data_dir = Path(data_dir)
        self._tasks_dir = self._data_dir / "tasks"
        self._events_dir = self._data_dir / "events"
        self._index_path = self._data_dir / "index.json"
        self._tasks: Dict[str, TaskState] = {}
        self._index: List[Dict[str, Any]] = []

    # ---------- 事件持久化（Phase 4：时间线回放不依赖内存总线） ----------

    def append_event(self, task_id: str, event: Dict[str, Any]) -> None:
        """把总线事件逐行追加到 tasks/{task_id}.events.jsonl（原子追加，崩溃安全）。

        供 StateProjector 在每个事件到达时调用。Phase 4 让历史任务在重启后仍可回放时间线。
        """
        try:
            self._events_dir.mkdir(parents=True, exist_ok=True)
            path = self._events_dir / f"{task_id}.jsonl"
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            pass    # 事件落盘失败不阻塞内核运行；时间线以内存总线为准

    def load_events(self, task_id: str) -> List[Dict[str, Any]]:
        """读取某任务持久化的事件全文（按发生顺序）。文件缺失/损坏返回空列表。"""
        try:
            path = self._events_dir / f"{task_id}.jsonl"
            if not path.exists():
                return []
            with path.open("r", encoding="utf-8") as f:
                out = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
                return out
        except OSError:
            return []

    # ---------- 生命周期 ----------

    def create_task(self, objective: str) -> TaskState:
        """新建任务（idle），立即落盘。"""
        with self._lock:
            task = TaskState(
                task_id=self._new_id(),
                objective=objective.strip() or "(无目标)",
                status=TaskStatus.IDLE,
            )
            self._tasks[task.task_id] = task
            self._persist(task)
            self._sync_index(task.task_id)
            return self.get(task.task_id)

    def get(self, task_id: str) -> Optional[TaskState]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            # 返回深拷贝快照，防止外部直接改内部状态（变更为经 set_status 等受控入口）
            return TaskState(**asdict(task))

    def list_tasks(self) -> List[TaskState]:
        with self._lock:
            return [TaskState(**asdict(t)) for t in self._tasks.values()]

    def set_status(self, task_id: str, new_status: TaskStatus, **extra) -> TaskState:
        """受控状态迁移：校验合法方向后更新并落盘。

        Raises:
            KeyError: 任务不存在
            IllegalTransitionError: 非法迁移（should never happen）
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"任务不存在: {task_id}")

            # 同状态重复迁移视为幂等（如循环中多次 STEP_STARTED，状态保持 executing）
            if new_status == task.status:
                pass
            elif new_status not in ALLOWED_TRANSITIONS.get(task.status, set()):
                raise IllegalTransitionError(
                    f"非法状态迁移: {task.status.value} -> {new_status.value}（task_id={task_id}）"
                )

            task.status = new_status
            task.updated_at = _now()
            if new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.completed_at = task.updated_at
            for key, value in extra.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            self._persist(task)
            self._sync_index(task_id)
            return self.get(task_id)

    def incr_loop_iterations(self, task_id: str, amount: int = 1) -> None:
        """循环迭代机械计数 +amount，并落盘。"""
        self._incr(task_id, "loop_iterations", amount)

    def incr_tool_call_count(self, task_id: str, amount: int = 1) -> None:
        """工具调用机械计数 +amount，并落盘。"""
        self._incr(task_id, "tool_call_count", amount)

    def _incr(self, task_id: str, field_name: str, amount: int) -> None:
        """共享计数递增实现（仅限内部两个计数字段使用）。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"任务不存在: {task_id}")
            setattr(task, field_name, getattr(task, field_name) + amount)
            task.updated_at = _now()
            self._persist(task)

    def record_created_file(self, task_id: str, path: str) -> None:
        """记入本次任务自己创建过的文件（覆盖判断用），去重并落盘。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"任务不存在: {task_id}")
            norm = str(path).rstrip("\\/") or str(path)
            if norm not in task.created_files:
                task.created_files.append(norm)
            task.updated_at = _now()
            self._persist(task)

    def set_model_usage(self, task_id: str, usage: Dict[str, int]) -> None:
        """记录本任务的模型 token 用量（Phase 3，供界面成本展示）。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"任务不存在: {task_id}")
            task.model_usage = dict(usage)
            task.updated_at = _now()
            self._persist(task)

    def set_estimated_cost(self, task_id: str, cost: Optional[float]) -> None:
        """记录本任务的预估费用（¥，Phase 5 成本感知）。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"任务不存在: {task_id}")
            task.estimated_cost = round(cost, 4) if cost is not None else None
            task.updated_at = _now()
            self._persist(task)

    def update_meta(self, task_id: str, title: Optional[str] = None, pinned: Optional[bool] = None) -> Optional[TaskState]:
        """更新任务展示元数据（右键重命名/置顶，与历史对话一致）。

        只改 title/pinned，不触状态机；None 表示该字段保持不变。
        返回 None 表示任务不存在。成功后同步索引并落盘。
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if title is not None:
                title = (title or "").strip()
                task.title = title or None    # 空串视为恢复默认（回退 objective 显示）
            if pinned is not None:
                task.pinned = bool(pinned)
            task.updated_at = _now()
            self._persist(task)
            self._sync_index(task_id)
            return self.get(task_id)

    # ---------- 持久化 ----------

    def restore(self) -> List[TaskState]:
        """软件启动时调用：从磁盘恢复全部任务（快照为准，索引由快照重建）。"""
        with self._lock:
            self._tasks.clear()
            if self._tasks_dir.exists():
                for p in sorted(self._tasks_dir.glob("*.json")):
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        task = TaskState(**data)
                        task.status = TaskStatus(task.status)
                        task.snapshot_path = str(p)
                        self._tasks[task.task_id] = task
                    except Exception:
                        # 单个损坏快照不阻塞整体恢复（跳过并继续）
                        continue
            self._rebuild_index()
            return list(self._tasks.values())

    def _persist(self, task: TaskState) -> None:
        path = self._tasks_dir / f"{task.task_id}.json"
        task.snapshot_path = str(path)
        _atomic_write(path, task.to_dict())

    def _sync_index(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            return
        row = task.to_meta()
        for i, existing in enumerate(self._index):
            if existing.get("taskId") == task_id:
                self._index[i] = row
                break
        else:
            self._index.append(row)
        # 历史表排序：置顶优先，其次按新建时间倒序（最新在前），板块/时间线展示友好
        self._index.sort(key=lambda r: (not bool(r.get("pinned")), -float(r.get("createdAt", 0))))
        _atomic_write(self._index_path, self._index)

    def _rebuild_index(self) -> None:
        rows = [t.to_meta() for t in self._tasks.values()]
        rows.sort(key=lambda r: (not bool(r.get("pinned")), -float(r.get("createdAt", 0))))
        self._index = rows
        _atomic_write(self._index_path, self._index)

    def index_rows(self) -> List[Dict[str, Any]]:
        with self._lock:
            # 定稿一：内存读穿缓存——冷启动/restore 未种子化时以磁盘 index.json 为准兜底，
            # 避免有历史任务却首查返空（磁盘为准，内存为读穿缓存；磁盘缺失则维持空表）。
            if not self._index and self._index_path.exists():
                try:
                    data = json.loads(self._index_path.read_text(encoding="utf-8"))
                    self._index = data if isinstance(data, list) else []
                except Exception:
                    self._index = []
            return [dict(r) for r in self._index]

    def delete_task(self, task_id: str) -> bool:
        """删除任务：内存字典 + 磁盘快照/事件文件 + 索引行（Phase 5 历史任务删除）。"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            del self._tasks[task_id]
            for p in (self._tasks_dir / f"{task_id}.json", self._events_dir / f"{task_id}.jsonl"):
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass    # 文件缺失/占用不阻塞删除
            self._index = [r for r in self._index if r.get("taskId") != task_id]
            _atomic_write(self._index_path, self._index)
            return True

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]