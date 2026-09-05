"""Agent 设置（Phase 5 硬化）：持久化到 agent_data/settings.json。

字段（对应执行方案 Phase 5 设置面板）：
  - 硬保护三档数字：迭代轮次 / 工具调用次数 / 单步超时
  - plan_confirm：生成/执行前是否等用户点「开始」（默认关，直接执行）
  - auto_allow_overwrite：覆盖文件是否自动放行不弹窗（高级选项，默认关 → 仍弹窗）
规则：读时全量校验并钳制到合法区间；写时同样钳制。单用户本地，直接硬编码默认值。
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

# 合法区间（执行方案 Phase 5 · 可配置机械硬保护）
MAX_ITERATIONS_RANGE = (10, 500)
MAX_TOOL_CALLS_RANGE = (10, 300)
STEP_TIMEOUT_RANGE = (10, 600)


@dataclass
class AgentSettings:
    max_iterations: int = 50          # 单任务最大迭代轮次
    max_tool_calls: int = 30          # 单任务最大工具调用次数
    step_timeout_s: float = 60.0      # 单步最大执行时间
    plan_confirm: bool = False        # 是否开启 Plan 确认（执行前等用户点「开始」）
    auto_allow_overwrite: bool = False  # 高级选项：覆盖已有文件时不弹窗（默认关，仍确认）

    def clamp(self) -> "AgentSettings":
        lo, hi = MAX_ITERATIONS_RANGE
        self.max_iterations = max(lo, min(hi, int(self.max_iterations)))
        lo, hi = MAX_TOOL_CALLS_RANGE
        self.max_tool_calls = max(lo, min(hi, int(self.max_tool_calls)))
        lo, hi = STEP_TIMEOUT_RANGE
        self.step_timeout_s = float(max(lo, min(hi, float(self.step_timeout_s))))
        self.plan_confirm = bool(self.plan_confirm)
        self.auto_allow_overwrite = bool(self.auto_allow_overwrite)
        return self

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AgentSettings":
        s = cls()
        if not isinstance(data, dict):
            return s
        for key in s.to_dict():
            if key in data:
                try:
                    setattr(s, key, data[key])
                except (TypeError, ValueError):
                    pass
        return s.clamp()


class SettingsStore:
    """设置持久化：原子写 settings.json，失败静默降级为默认值。"""

    def __init__(self, data_dir: Path) -> None:
        self._lock = threading.RLock()
        self._path = Path(data_dir) / "settings.json"
        self._settings = self._load()

    def _load(self) -> AgentSettings:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text(encoding="utf-8"))
                return AgentSettings.from_dict(data)
        except (OSError, ValueError):
            pass
        return AgentSettings()

    def get(self) -> AgentSettings:
        with self._lock:
            return AgentSettings.from_dict(self._settings.to_dict())

    def update(self, patch: Dict[str, Any]) -> AgentSettings:
        """部分更新：只覆盖传入的字段，其余保持。非法字段忽略。"""
        with self._lock:
            data = self._settings.to_dict()
            for k in ("max_iterations", "max_tool_calls", "step_timeout_s",
                      "plan_confirm", "auto_allow_overwrite"):
                if k in patch:
                    data[k] = patch[k]
            self._settings = AgentSettings.from_dict(data)
            self._save()
            return self.get()

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self._settings.to_dict(), ensure_ascii=False, indent=2),
                           encoding="utf-8")
            tmp.replace(self._path)
        except OSError:
            pass