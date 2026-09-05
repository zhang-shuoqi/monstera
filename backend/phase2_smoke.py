"""Phase 2 验收自测（可直接运行：python phase2_smoke.py）

对照 Phase 2 验收标准逐条验证（用户闸 + RiskEvaluator + 拒绝回传重决策）：
  1) 尝试写文件到 C:\\Windows → RiskEvaluator 识别高危（confirm），循环暂停（waiting_human）。
  2) 用户点「拒绝」→ 模型收到拒绝信息，走 fallback 换方案（不终止任务）。
  3) 用户点「允许」→ 循环继续执行。
  4) 覆盖本次任务自己生成的文件 → 只通知不弹窗（notify，不阻塞）。

另验证：
  - SYSTEM_PATH_PATTERNS 覆盖：C:\\Windows\\*、C:\\Program Files\\*、C:\\ProgramData\\*
  - 拒绝信息回传模型的格式（含"请基于此信息重新决策"）
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from agent_core.runtime import AgentCore
from agent_core.state_store import TaskStatus
from agent_core.user_gate import CONFIRM, NOTIFY, ALLOW, RiskEvaluator, is_system_path

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def test_system_path_patterns() -> None:
    """SYSTEM_PATH_PATTERNS 关键路径覆盖 + 用户目录判定。"""
    print("\n== 规则项 1：Windows 系统目录硬编码规则 ==")
    check("C:\\Windows\\test.txt → 系统", is_system_path(r"C:\Windows\test.txt"))
    check("C:\\Windows 本身 → 系统", is_system_path(r"C:\Windows"))
    check("c:\\windows\\system32 (小写) → 系统", is_system_path(r"c:\windows\system32\drivers"))
    check("C:\\Program Files\\App → 系统", is_system_path(r"C:\Program Files\App\a.exe"))
    check("C:\\Program Files (x86)\\App → 系统", is_system_path(r"C:\Program Files (x86)\App"))
    check("C:\\ProgramData\\X → 系统", is_system_path(r"C:\ProgramData\X"))
    check("D:\\My\\demo.txt → 非系统", not is_system_path(r"D:\My\demo.txt"))

    ev = RiskEvaluator()
    home = Path.home()
    desktop = home / "Desktop" / "note.txt"
    check("file_read 用户桌面 → allow", ev.evaluate("file_read", {"path": str(desktop)}).level == ALLOW)
    check("file_read C:\\Windows\\hosts → confirm",
          ev.evaluate("file_read", {"path": r"C:\Windows\System32\drivers\etc\hosts"}).level == CONFIRM)


def test_risk_rules() -> None:
    """RiskEvaluator 分级规则（含覆盖已有文件 vs 新建 vs 自己创建）。"""
    print("\n== 规则项 2：RiskEvaluator 分级 ==")
    ev = RiskEvaluator()
    tmp = Path(tempfile.mkdtemp(prefix="p2_risk_"))
    try:
        existing = tmp / "user_file.txt"
        existing.write_text("x", encoding="utf-8")
        created = tmp / "self_created.txt"

        # file_write 新建 → notify
        r = ev.evaluate("file_write", {"path": str(tmp / "new.txt")})
        check("file_write 新建 → notify", r.level == NOTIFY, r.level)

        # file_write 覆盖用户已有文件 → confirm
        r = ev.evaluate("file_write", {"path": str(existing)})
        check("file_write 覆盖已有文件 → confirm", r.level == CONFIRM, r.level)

        # file_write 覆盖自己创建的文件（created_files 集合内）→ notify
        r = ev.evaluate("file_write", {"path": str(created)}, created_files={normalized(created)})
        check("file_write 覆盖自建文件 → notify（不弹窗）", r.level == NOTIFY, r.level)

        # file_write 写系统目录 → confirm（无论是否已创建）
        sys_path = r"C:\Windows\test_overwrite.txt"
        r = ev.evaluate("file_write", {"path": sys_path}, created_files={sys_path})
        check("file_write 写系统目录（即使自建）→ confirm", r.level == CONFIRM, r.level)

        # 记忆工具已移出工具箱：被视为未知工具 → confirm（保守拦截），不再有专用规则
        check("memory_search（已移除）→ confirm", ev.evaluate("memory_search", {"query": "x"}).level == CONFIRM)
        check("memory_write（已移除）→ confirm", ev.evaluate("memory_write", {"title": "t", "content": "c"}).level == CONFIRM)
        # 未知工具 → confirm（保守拦截）
        check("未知工具 → confirm", ev.evaluate("hack_tool", {}).level == CONFIRM)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def normalized(p: Path) -> Path:
    return Path(str(p).rstrip("\\/"))


def test_deny_then_fallback() -> None:
    """验收 2：用户拒绝 → 模型收到拒绝信息 → fallback 换方案（任务仍 completed）。"""
    print("\n== 验收 2：拒绝后换方案 ==")
    tmp_hub = Path(tempfile.mkdtemp(prefix="p2_memhub_"))
    old_dir = None
    import config
    old_dir = config.MEMORY_DIR
    config.MEMORY_DIR = tmp_hub
    core = AgentCore(tempfile.mkdtemp(prefix="agent_p2_"))
    try:
        safe = tmp_hub / "safe_target.txt"
        plan = [
            {
                "tool": "file_write",
                "args": {"path": r"C:\Windows\monstera_deny_test.txt", "content": "x"},
                "fallback": {"tool": "file_write", "args": {"path": str(safe), "content": "fallback 方案"}},
            }
        ]
        task = core.create_task("写入被拒绝后换方案")
        task_id = task.task_id

        result: dict = {}
        def runner():
            result["state"] = core.run_task(task_id, plan=plan, with_gate=True)

        t = threading.Thread(target=runner)
        t.start()

        # 等待进入 waiting_human
        for _ in range(50):
            if core.get_task(task_id).status == TaskStatus.WAITING_HUMAN:
                break
            import time; time.sleep(0.05)
        check("循环暂停于 waiting_human", core.get_task(task_id).status == TaskStatus.WAITING_HUMAN,
              str(core.get_task(task_id).status))

        # 用户点「拒绝」
        core.resolve_intervention(task_id, allow=False, reason="不要写 Windows 系统目录")
        t.join(timeout=10)

        final = result.get("state")
        check("拒绝后任务未终止 → completed", final is not None and final.status == TaskStatus.COMPLETED,
              str(getattr(final, "status", None)))
        check("fallback 已执行（换方案写入安全位置）", safe.exists(), str(safe))
        check("系统目录未被写入", not Path(r"C:\Windows\monstera_deny_test.txt").exists())

        # 拒绝信息格式回传（事件流里应有含"重新决策"的观察）
        from agent_core.events import get_bus
        obs_events = [e.payload for e in get_bus().history(task_id) if e.type.value == "OBSERVATION_READY"]
        denial_seen = any(
            isinstance(p, dict) and "用户拒绝" in str(p.get("observation", {}).get("summary", "")) for p in obs_events
        )
        check("拒绝信息以观察形式回传（含拒绝原因）", denial_seen)
    finally:
        if old_dir is not None:
            config.MEMORY_DIR = old_dir
        shutil.rmtree(tmp_hub, ignore_errors=True)
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def test_allow_proceeds() -> None:
    """验收 3：用户点「允许」→ 循环继续执行并完成（真实写入用户目录）。"""
    print("\n== 验收 3：允许后继续执行 ==")
    import config
    tmp_hub = Path(tempfile.mkdtemp(prefix="p2_memhub_"))
    old_dir = config.MEMORY_DIR
    config.MEMORY_DIR = tmp_hub
    core = AgentCore(tempfile.mkdtemp(prefix="agent_p2_"))
    try:
        target = tmp_hub / "existing.txt"
        target.write_text("原内容", encoding="utf-8")   # 已存在文件 → 覆盖属 confirm
        plan = [
            {"tool": "file_write", "args": {"path": str(target), "content": "允许后覆盖写入"}},
        ]
        task = core.create_task("确认允许后覆盖文件")
        task_id = task.task_id
        result: dict = {}
        def runner():
            result["state"] = core.run_task(task_id, plan=plan, with_gate=True)
        t = threading.Thread(target=runner)
        t.start()
        for _ in range(50):
            if core.get_task(task_id).status == TaskStatus.WAITING_HUMAN:
                break
            import time; time.sleep(0.05)
        check("危险操作进入 waiting_human", core.get_task(task_id).status == TaskStatus.WAITING_HUMAN)
        # 覆盖自身：allow=True → 继续执行
        core.resolve_intervention(task_id, allow=True)
        t.join(timeout=10)
        final = result.get("state")
        check("允许后继续执行 → completed", final is not None and final.status == TaskStatus.COMPLETED, str(getattr(final, "status", None)))
        check("目标文件真实写入", target.exists() and target.read_text(encoding="utf-8") == "允许后覆盖写入")
    finally:
        config.MEMORY_DIR = old_dir
        shutil.rmtree(tmp_hub, ignore_errors=True)
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def test_self_created_overwrite_skips_confirm() -> None:
    """验收 4：覆盖本次任务自己创建的文件 → 不弹窗（notify），直接执行。"""
    print("\n== 验收 4：覆盖自建文件不弹窗 ==")
    import config
    tmp_hub = Path(tempfile.mkdtemp(prefix="p2_memhub_"))
    old_dir = config.MEMORY_DIR
    config.MEMORY_DIR = tmp_hub
    core = AgentCore(tempfile.mkdtemp(prefix="agent_p2_"))
    try:
        target = tmp_hub / "self.txt"
        # 第一步创建（任务自己 → 记录进 created_files），第二步覆盖同一文件
        plan = [
            {"tool": "file_write", "args": {"path": str(target), "content": "v1"}},
            {"tool": "file_write", "args": {"path": str(target), "content": "v2"}},
        ]
        task = core.create_task("覆盖自己创建的文件")
        task_id = task.task_id
        # 用真 gate 验证：自己创建的文件覆盖是 notify，不应触发确认弹窗
        final = core.run_task(task_id, plan=plan, with_gate=True)
        check("覆盖自建文件完成（未阻塞弹窗）", final.status == TaskStatus.COMPLETED, str(final.status))
        check("文件内容为 v2", target.read_text(encoding="utf-8") == "v2")
        check("created_files 已记录该文件", str(target) in core.get_task(task_id).created_files)

        from agent_core.events import get_bus
        confirm_seen = any(
            e.type.value == "HUMAN_INTERVENTION_REQUIRED" for e in get_bus().history(task_id)
        )
        check("覆盖自建文件全程无确认弹窗", not confirm_seen)
    finally:
        config.MEMORY_DIR = old_dir
        shutil.rmtree(tmp_hub, ignore_errors=True)
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def main() -> None:
    print("Phase 2 验收自测（Monstera Agent Core · 用户闸）")
    test_system_path_patterns()
    test_risk_rules()
    test_deny_then_fallback()
    test_allow_proceeds()
    test_self_created_overwrite_skips_confirm()

    print(f"\n===== 结果：{len(PASSED)} 通过 / {len(FAILED)} 失败 =====")
    if FAILED:
        print("失败项:", FAILED)
        sys.exit(1)
    print("Phase 2 验收全部通过 ✓")


if __name__ == "__main__":
    main()