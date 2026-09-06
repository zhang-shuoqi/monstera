"""文件工具 trio：file_read / file_write / list_dir（设计定稿 v1.0 · 四、Phase 1）。

关键约束：
  - file_write 必须回传「这是覆盖还是新建」：任务开始时由调用方记录 created 集合，
    工具本身只报告本次写是 created(新建) 还是 overwritten(覆盖已有)。
  - file_read / list_dir 为只读，不修改任何文件系统状态。

说明：Phase 1 不做路径风险评估（那是 Phase 2 用户闸 RiskEvaluator 的职责），
工具只负责"能真实读写"。危险路径拦截在 Phase 2 加闸后由循环引擎调用流程负责。
"""
from __future__ import annotations

import difflib
import os
import pathlib
from typing import Any, Dict, List, Optional

from . import Tool, ToolResult


def _unified_diff(path: str, old_text: str, new_text: str) -> str:
    """生成 unified diff（编辑时刻计算）；旧/新任一非纯文本则返回 ''（二进制/非 UTF-8 不产出 diff）。

    只服务 C3 文件证据：`+` 行新增 / `-` 行删除。若内容未变化也返回空串。"""
    try:
        old_d = old_text.encode("utf-8", "strict").decode("utf-8", "strict")
        new_d = new_text.encode("utf-8", "strict").decode("utf-8", "strict")
    except UnicodeError:
        return ""
    if old_d == new_d:
        return ""
    return "".join(difflib.unified_diff(
        old_d.splitlines(keepends=True),
        new_d.splitlines(keepends=True),
        fromfile=path, tofile=path, lineterm=""))


class ListDirTool(Tool):
    name = "list_dir"
    description = "列出目录内容（文件名/是否目录/大小）。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要列出的目录路径（绝对路径）"},
            "max_entries": {"type": "integer", "description": "最多返回条目数，默认 200"},
        },
        "required": ["path"],
    }
    permissions = ["read"]

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        path = str(args.get("path") or "").strip()
        max_entries = int(args.get("max_entries") or 200)
        if not path:
            return ToolResult(success=False, error="list_dir 需要 path 参数")
        p = pathlib.Path(path)
        if not p.exists():
            return ToolResult(success=False, error=f"目录不存在: {path}")
        if not p.is_dir():
            return ToolResult(success=False, error=f"不是目录: {path}")
        try:
            entries: List[Dict[str, Any]] = []
            for entry in p.iterdir():
                try:
                    is_dir = entry.is_dir()
                except OSError:
                    is_dir = False
                entries.append({
                    "name": entry.name,
                    "is_dir": is_dir,
                    "size": entry.stat().st_size if not is_dir else None,
                })
                if len(entries) >= max_entries:
                    break
            entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
            return ToolResult(success=True, data={
                "path": str(p),
                "count": len(entries),
                "entries": entries,
            })
        except Exception as exc:
            return ToolResult(success=False, error=f"list_dir 失败: {exc}")


class FileReadTool(Tool):
    name = "file_read"
    description = "读取本地文本文件内容。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件绝对路径"},
            "max_chars": {"type": "integer", "description": "最多读取字符数，默认 20000（防止大文件塞爆上下文）"},
        },
        "required": ["path"],
    }
    permissions = ["read"]

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        path = str(args.get("path") or "").strip()
        max_chars = int(args.get("max_chars") or 20000)
        if not path:
            return ToolResult(success=False, error="file_read 需要 path 参数")
        p = pathlib.Path(path)
        if not p.exists():
            return ToolResult(success=False, error=f"文件不存在: {path}")
        if not p.is_file():
            return ToolResult(success=False, error=f"不是文件: {path}")
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_chars
            return ToolResult(success=True, data={
                "path": str(p),
                "content": content[:max_chars],
                "chars": len(content),
                "truncated": truncated,
            })
        except Exception as exc:
            return ToolResult(success=False, error=f"file_read 失败: {exc}")


class FileEditTool(Tool):
    """精确块替换编辑（移植 OpenHands StrReplace 设计思想，按 Monstera 工具契约重写）。

    与 file_write 的区别：只替换文件中匹配到的 old_string 片段，不重写整个文件——
    省 token、不破坏无关内容。old_string 需精确匹配且尽量唯一，否则拒绝并要求更多上下文。
    """

    name = "file_edit"
    description = (
        "在已有文件中精确替换一段文本。old_string 必须与文件现有内容完全一致"
        "（含缩进与换行，建议包含足够上下文保证唯一）；new_string 为替换后的内容。"
        "适合小范围修改；大范围改动请用 file_write 整写。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件绝对路径"},
            "old_string": {"type": "string", "description": "要替换的旧文本（必须精确匹配；唯一，或设置 replace_all）"},
            "new_string": {"type": "string", "description": "替换后的新文本（可为空串表示删除该片段）"},
            "replace_all": {"type": "boolean", "description": "是否替换所有匹配（默认 false，仅允许唯一匹配）"},
        },
        "required": ["path", "old_string", "new_string"],
    }
    permissions = ["write"]

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        path = str(args.get("path") or "").strip()
        old_string = str(args.get("old_string") or "")
        new_string = str(args.get("new_string") or "")
        replace_all = bool(args.get("replace_all"))
        if not path:
            return ToolResult(success=False, error="file_edit 需要 path 参数")
        if not old_string:
            return ToolResult(success=False, error="file_edit 需要非空 old_string 参数")
        p = pathlib.Path(path)
        if not p.exists():
            return ToolResult(success=False, error=f"文件不存在: {path}")
        if not p.is_file():
            return ToolResult(success=False, error=f"不是文件: {path}")
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            count = content.count(old_string)
            if count == 0:
                return ToolResult(success=False, error=(
                    f"未找到要替换的文本（old_string 与文件内容不匹配）。"
                    f"文件共 {len(content)} 字符；请检查片段是否与文件完全一致（尤其换行/缩进/转义）。"
                ))
            if count > 1 and not replace_all:
                return ToolResult(success=False, error=(
                    f"old_string 在文件中出现 {count} 次，请包含更多上下文使其唯一，"
                    f"或设置 replace_all=true 全部替换。"
                ))
            new_content = content.replace(old_string, new_string)
            # 定稿二：编辑时刻统一 diff；文件非纯文本则不产出（old_strict=None）
            try:
                old_strict = p.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                old_strict = None
            p.write_text(new_content, encoding="utf-8")
            return ToolResult(success=True, data={
                "path": str(p),
                "mode": "edited",
                "replaced": "once" if count == 1 else f"all({count})",
                "summary": f"已替换 {count} 处（{old_string[:60]!r} → {new_string[:60]!r}）",
                "bytes": os.path.getsize(p),
                "diff": "" if old_strict is None else _unified_diff(str(p), old_strict, new_content),
            })
        except Exception as exc:
            return ToolResult(success=False, error=f"file_edit 失败: {exc}")


class FileWriteTool(Tool):
    name = "file_write"
    description = "写入新文件或覆盖已有文件。"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件绝对路径"},
            "content": {"type": "string", "description": "要写入的内容"},
        },
        "required": ["path", "content"],
    }
    permissions = ["write"]

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        path = str(args.get("path") or "").strip()
        content = args.get("content", "")
        if not path:
            return ToolResult(success=False, error="file_write 需要 path 参数")
        p = pathlib.Path(path)
        existed_before = p.exists()  # 关键：写前判断「覆盖还是新建」
        mode = "overwritten" if existed_before else "created"
        try:
            if p.parent and not p.parent.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
            new_text = str(content)
            # 定稿二：编辑/写入时刻计算 unified diff（overwritten 对比旧内容；created 视为全行新增）
            old_strict = "" if not existed_before else None
            if existed_before:
                try:
                    old_strict = p.read_text(encoding="utf-8", errors="strict")
                except (UnicodeDecodeError, OSError):
                    old_strict = None
            p.write_text(new_text, encoding="utf-8")
            return ToolResult(success=True, data={
                "path": str(p),
                "mode": mode,          # "created" | "overwritten"
                "created": not existed_before,
                "overwritten": existed_before,
                "bytes": os.path.getsize(p),
                "diff": "" if old_strict is None else _unified_diff(str(p), old_strict, new_text),
            })
        except Exception as exc:
            return ToolResult(success=False, error=f"file_write 失败: {exc}")