"""Phase 1 验收自测（可直接运行：python phase1_smoke.py）

对照 Phase 1 验收标准逐条验证（真实工具，非假执行）：
  1) 循环引擎能真实调用 list_dir，拿到桌面文件列表。
  2) 能真实调用 file_read，读到本地文本文件内容。
  3) 能真实调用 file_read 之外的 V1 工具箱成员（修正后工具箱 = file_read/file_write/list_dir）。

另验证 Phase 1 关键约束：
  - 工具注册表：循环引擎按名字查表执行，不感知工具语义。
  - file_write 返回「覆盖还是新建」（created / overwritten）。
修正后：Agent 工具箱移除记忆工具（memory_search/memory_write 已删除），注册表只含 file trio。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from agent_core.runtime import AgentCore
from agent_core.state_store import TaskStatus

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def test_registry() -> None:
    """工具注册表：3 个冻结工具（修正后），按名字查表。"""
    print("\n== 生效项 1：Agent 工具箱注册表（修正后 file trio）==")
    core = AgentCore(tempfile.mkdtemp(prefix="agent_p1_"))
    try:
        info = core.tools_info()
        tool_names = {t["name"] for t in info}
        check("注册表含 3 个冻结工具（file trio）",
              tool_names == {"file_read", "file_write", "list_dir"},
              f"实际 {sorted(tool_names)}")
        check("注册表不再含记忆工具",
              "memory_search" not in tool_names and "memory_write" not in tool_names)
        by_name = {t["name"]: t for t in info}
        check("file_write 权限=write", by_name["file_write"]["permissions"] == ["write"])
        check("file_read 权限=read", by_name["file_read"]["permissions"] == ["read"])
        check("list_dir 权限=read", by_name["list_dir"]["permissions"] == ["read"])
        check("工具含 JSONSchema 参数", all("parameters" in t for t in info))
    finally:
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def test_file_write_overwrite_flag() -> None:
    """file_write 回传「覆盖还是新建」。"""
    print("\n== 生效项 2：file_write 覆盖/新建标记 ==")
    core = AgentCore(tempfile.mkdtemp(prefix="agent_p1_"))
    try:
        tmp = Path(tempfile.mkdtemp(prefix="p1_fs_"))
        target = tmp / "demo.txt"

        # 直接用注册表执行（Phase 1 要求工具可被真实调用）
        r1 = core._toolbox.execute("file_write", {"path": str(target), "content": "hello"})
        check("新建返回 created", bool(r1.success) and r1.data.get("mode") == "created" and r1.data.get("created"), str(r1))

        r2 = core._toolbox.execute("file_write", {"path": str(target), "content": "world"})
        check("覆盖返回 overwritten",
              bool(r2.success) and r1.data.get("mode") == "created" and r2.data.get("mode") == "overwritten", str(r2))

        # 落盘确认 + 读回来
        read = core._toolbox.execute("file_read", {"path": str(target)})
        check("file_read 读回内容", bool(read.success) and read.data.get("content") == "world", str(read))

        # list_dir 拿到条目
        listed = core._toolbox.execute("list_dir", {"path": str(tmp)})
        check("list_dir 真实列出", bool(listed.success) and listed.data.get("count", 0) >= 1, str(listed))

        # 未知工具：注册表返回 success=False（不抛穿循环）
        unknown = core._toolbox.execute("no_such_tool", {})
        check("未知工具被拒绝为失败结果", not unknown.success and "未知工具" in (unknown.error or ""), str(unknown))
        # 已移除的记忆工具：同样按「未知工具」拒绝
        mem = core._toolbox.execute("memory_search", {"query": "x"})
        check("记忆工具已移除（memory_search → 未知工具失败）", not mem.success and "未知工具" in (mem.error or ""), str(mem))
        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def test_loop_real_tools_all_criteria() -> None:
    """验收 1/2：循环引擎真实调用 list_dir / file_read（file_write 三件套）。"""
    print("\n== Phase 1 验收：循环引擎真实驱动 Agent 工具箱 ==")
    core = AgentCore(tempfile.mkdtemp(prefix="agent_p1_"))
    try:
        desktop = Path.home() / "Desktop"
        tmp = Path(tempfile.mkdtemp(prefix="p1_loop_"))   # 文件读写的安全沙箱
        readme = tmp / "readme.txt"
        readme.write_text("Monstera Phase 1 验收文件。", encoding="utf-8")
        objective = "按要求依次列目录、读文件、写文件"

        # 计划（Phase 1 假模型按计划调用真实工具；Phase 3 换真实模型自动生成计划）
        plan = [
            {"tool": "list_dir", "args": {"path": str(desktop)}},
            {"tool": "file_read", "args": {"path": str(readme)}},
            {"tool": "file_write", "args": {"path": str(tmp / "out.txt"), "content": "写入结果"}},
        ]
        task = core.create_task(objective)
        final = core.run_task(task.task_id, plan=plan)

        check("循环完成（真实工具）", final.status == TaskStatus.COMPLETED, str(final.status))
        check("机械计数：3 次工具调用", final.loop_iterations == 4 and final.tool_call_count == 3,
              f"iter={final.loop_iterations} tool={final.tool_call_count}")

        from agent_core.events import get_bus

        types = [e.type.value for e in get_bus().history(task.task_id)]
        check("事件含 TOOL_CALL_REQUESTED", "TOOL_CALL_REQUESTED" in types)
        check("事件链闭合 TASK_COMPLETED", types[-1] == "TASK_COMPLETED")

        # 观察输出里能看到真实工具结果条目（通过事件载荷检查）
        payloads = [e.payload for e in get_bus().history(task.task_id)]
        tool_results = [p for p in payloads if isinstance(p, dict)]
        list_called = any(p.get("tool") == "list_dir" for p in tool_results)
        read_called = any(p.get("tool") == "file_read" for p in tool_results)
        write_called = any(p.get("tool") == "file_write" for p in tool_results)
        check("真实调用 list_dir", list_called)
        check("真实调用 file_read", read_called)
        check("真实调用 file_write", write_called)
        check("计划内文件已真实写入", (tmp / "out.txt").read_text(encoding="utf-8") == "写入结果")

        shutil.rmtree(tmp, ignore_errors=True)
    finally:
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def main() -> None:
    print("Phase 1 验收自测（Monstera Agent Core · 真实工具箱）")
    test_registry()
    test_file_write_overwrite_flag()
    test_loop_real_tools_all_criteria()

    print(f"\n===== 结果：{len(PASSED)} 通过 / {len(FAILED)} 失败 =====")
    if FAILED:
        print("失败项:", FAILED)
        sys.exit(1)
    print("Phase 1 验收全部通过 ✓")


if __name__ == "__main__":
    main()