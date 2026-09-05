"""本地工具箱（Local Toolbox）· 设计定稿 v1.0 · 四。

Agent 工具箱 V1 冻结集合（修正后）：
    file_read / file_write / list_dir —— 文件工具 trio
记忆工具已从 Agent 工具箱移除（记忆中枢保持独立，Agent 不通过工具读写记忆）。
其他工具一律不进 V1（浏览器、shell、代码沙盒全部后置）。

统一工具契约（与设计定稿 TypeScript 接口一一对应）：
    Tool   : name / description / parameters(JSONSchema) / permissions / execute -> ToolResult
    ToolResult : success + data（失败时 error）
循环引擎只认这个契约，不感知工具语义；它通过 ToolRegistry 按名字查表执行。
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """统一工具返回。success=False 时 error 说明失败原因。"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class Tool(abc.ABC):
    """工具基类。execute 抛异常视为执行失败（由注册表兜底转 ToolResult.success=False）。"""

    name: str = ""
    description: str = ""                # 给模型看的用途说明
    parameters: Dict[str, Any] = field(default_factory=dict)   # JSONSchema
    permissions: List[str] = field(default_factory=list)       # read/write/execute/network

    @abc.abstractmethod
    def execute(self, args: Dict[str, Any]) -> ToolResult: ...

    def info(self) -> Dict[str, Any]:
        """工具元信息（供模型/界面查看注册表）。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "permissions": list(self.permissions),
        }


class ToolRegistry:
    """「名字 → 工具逻辑」注册表：循环引擎只通过名字查表调用，不感知工具语义。"""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> "ToolRegistry":
        if not tool.name:
            raise ValueError("工具必须提供 name")
        self._tools[tool.name] = tool
        return self

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> List[str]:
        return list(self._tools)

    def info_all(self) -> List[Dict[str, Any]]:
        return [t.info() for t in self._tools.values()]

    def execute(self, name: str, args: Any) -> ToolResult:
        """按名字查表执行。未知工具 / 工具异常 → success=False（不抛穿循环）。"""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"未知工具: {name}")
        try:
            return tool.execute(dict(args) if isinstance(args, dict) else {})
        except Exception as exc:  # 工具实现异常统一兜底，循环引擎观察后仍可再决策
            return ToolResult(success=False, error=f"工具 {name} 执行异常: {exc}")


def build_default_toolbox() -> ToolRegistry:
    """构建 Agent 工具箱 V1（file trio + file_edit 精确编辑），供 AgentCore 使用。"""
    from .fs_tools import FileEditTool, FileReadTool, FileWriteTool, ListDirTool

    reg = ToolRegistry()
    reg.register(FileReadTool())
    reg.register(FileWriteTool())
    reg.register(FileEditTool())
    reg.register(ListDirTool())
    return reg


__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "build_default_toolbox",
]