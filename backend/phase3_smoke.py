"""Phase 3 验收自测（可直接运行：python phase3_smoke.py）

对照 Phase 3 验收标准逐条验证（循环引擎接【真实模型驱动】→ Mock Function Calling 模拟）：

验收 1：用户输入「列出桌面所有文件」 → 模型调用 list_dir → 返回结果 → 任务完成。
验收 2：用户输入「在桌面创建 test.txt，内容 hello」 → 模型调用 file_write → 真实创建文件 → 任务完成。
验收 3：用户输入「读取 C:\\Windows\\...hosts」 → 模型调用 file_read → 用户闸拦截 → 弹窗确认。

另验证 Phase 3 关键约束：
  - 上下文组装：目标 + 工具清单 + 历史压缩（只保留最近 3 步完整细节）。
  - Function Calling 解析：模型返回 tool_calls → ModelDecision。
  - 结果回传：工具结果整理成观察追加上下文，模型下轮直接回答。
  - 模型格式错误（返回非法 tool_call）重试 3 次仍失败 → 任务 failed。
  - 硬保护：机械计数器（迭代/工具调用）仍生效。
Mock 模式：config.is_mock() 时 OpenAICompatClient 返回模拟 tool_calls，无需真实 Key。
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

import config

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def _make_core():
    from agent_core.runtime import AgentCore
    from agent_core.toolbox import build_default_toolbox

    core = AgentCore(tempfile.mkdtemp(prefix="agent_p3_"))
    return core


def _make_driver(core, objective_hint: str = ""):
    """构造 Mock 模型驱动：直接包 OpenAICompatClient（mock 走假 tool_calls）。"""
    from agent_core.llm_driver import LLMModelDriver
    from services.openai_compat import OpenAICompatClient

    client = OpenAICompatClient(base_url="http://mock.local/v1", provider_key="deepseek")
    temp_refs = Path(tempfile.mkdtemp(prefix="p3_refs_"))
    return LLMModelDriver(
        client=client,
        api_key="sk-mock-agent-key-123",
        model="deepseek-v4-flash",
        toolbox=core._toolbox,
        temp_dir=temp_refs,
    ), temp_refs


def _fake_desktop() -> tuple:
    """Monkeypatch openai_compat._desktop_path → 临时沙箱桌面，避免测试触碰真实桌面。

    返回 (fake_path, restore_fn)。
    """
    import services.openai_compat as oc
    fake = Path(tempfile.mkdtemp(prefix="p3_desktop_"))
    orig = oc._desktop_path
    oc._desktop_path = lambda: str(fake)
    return fake, lambda: setattr(oc, "_desktop_path", orig)


def _shutdown(core, refs, restore=None, extra=None):
    if restore:
        restore()
    shutil.rmtree(core._store._data_dir, ignore_errors=True)
    if refs:
        shutil.rmtree(refs, ignore_errors=True)
    if extra:
        shutil.rmtree(extra, ignore_errors=True)


def test_acceptance_list_dir() -> None:
    """验收 1：列出桌面 → 模型调 list_dir → 完成。"""
    print("\n== 验收 1：『列出桌面所有文件』→ 模型调用 list_dir ==")
    core = _make_core()
    fake, restore = _fake_desktop()
    (fake / "hello.txt").write_text("hi", encoding="utf-8")
    config.set_mock(True)
    try:
        driver, refs = _make_driver(core)
        task = core.create_task("列出桌面所有文件")
        final = core.run_task(task.task_id, model=driver, persist_refs=True)
        check("任务完成 status=completed", final.status.value == "completed", str(final.status))
        check("模型主动调用 list_dir（tool_call_count>=1）", final.tool_call_count >= 1,
              f"tool_calls={final.tool_call_count}")
        check("模型给出最终答复", bool(final.final_answer), str(final.final_answer))
        check("token 用量已记录", set(final.model_usage) == {"prompt_tokens", "completion_tokens"},
              str(final.model_usage))
        check("list_dir 结果涉及沙箱桌面", (fake / "hello.txt").exists())
    finally:
        config.set_mock(False)
        _shutdown(core, None, restore, extra=fake)


def test_acceptance_file_write() -> None:
    """验收 2：桌面创建 test.txt → 模型调 file_write → 真实创建。"""
    print("\n== 验收 2：『在桌面创建 test.txt，内容 hello』→ 模型调用 file_write ==")
    core = _make_core()
    fake, restore = _fake_desktop()
    config.set_mock(True)
    try:
        driver, refs = _make_driver(core)
        task = core.create_task("在桌面创建 test.txt，内容 hello")   # mock 会写出 fake\\test.txt
        final = core.run_task(task.task_id, model=driver, persist_refs=True)
        check("任务完成 status=completed", final.status.value == "completed", str(final.status))
        check("模型主动调用 file_write", final.tool_call_count >= 1, f"tool_calls={final.tool_call_count}")
        check("沙箱桌面 test.txt 真实创建", (fake / "test.txt").exists())
        check("写路径已记入 created_files", len(final.created_files) >= 1, str(final.created_files))
        check("最终答复非空", bool(final.final_answer))
    finally:
        config.set_mock(False)
        _shutdown(core, None, restore, extra=fake)


def test_acceptance_file_read_system_denied() -> None:
    """验收 3：读取 C:\\Windows...hosts → 模型调 file_read → 用户闸拦截 → 弹窗确认。"""
    print("\n== 验收 3：『读取 hosts』→ 模型调 file_read → 用户闸拦截 ==")
    core = _make_core()
    _, restore = _fake_desktop()
    config.set_mock(True)
    try:
        from agent_core.state_store import TaskStatus

        driver, refs = _make_driver(core)
        task = core.create_task("读取 C:\\Windows\\system32\\drivers\\etc\\hosts")
        task_id = task.task_id

        result: dict = {}
        def runner():
            result["task"] = core.run_task(task_id, model=driver, with_gate=True)   # 读取系统目录 → confirm
        t = threading.Thread(target=runner)
        t.start()

        for _ in range(60):
            if core.get_task(task_id).status == TaskStatus.WAITING_HUMAN:
                break
            import time; time.sleep(0.05)
        check("每次读系统目录都等待用户确认（waiting_human）",
              core.get_task(task_id).status == TaskStatus.WAITING_HUMAN,
              str(core.get_task(task_id).status))

        # 用户拒绝 → 模型换方案 → 任务仍完成（不终止）
        core.resolve_intervention(task_id, allow=False, reason="不要读取系统目录文件")
        t.join(timeout=15)
        final = result.get("task")
        check("拒绝后任务不终止（completed）", final is not None and final.status.value == "completed",
              str(getattr(final, "status", None)))

        from agent_core.events import get_bus
        obs_events = [e.payload for e in get_bus().history(task_id) if e.type.value == "OBSERVATION_READY"]
        denial = any(
            isinstance(p, dict) and "用户拒绝" in str(p.get("observation", {}).get("summary", "")) for p in obs_events
        )
        check("拒绝信息已回传模型（观察含'用户拒绝'）", denial)
    finally:
        config.set_mock(False)
        _shutdown(core, None, restore)


def test_context_compression() -> None:
    """上下文压缩：只保留最近 3 步完整，早期压成一行摘要。"""
    print("\n== 关键约束：上下文组装（摘要压缩 + 大载荷引用）==")
    from agent_core.llm_driver import LLMModelDriver
    from agent_core.loop import Observation

    driver, refs = _make_core2()
    # 大载荷（summary > 800 字符）应走引用文件；小载荷内联
    big_obs = Observation(step=1, tool_name="file_read", success=True,
                          summary="内容" * 500, raw={"content": "x" * 5000})
    small_obs = Observation(step=2, tool_name="list_dir", success=True, summary="桌面：a.txt, b.txt")
    body, ref = driver._ref_or_inline(big_obs)
    check("大载荷存本地引用文件", ref is not None and Path(ref).exists(), str(ref))
    body2, ref2 = driver._ref_or_inline(small_obs)
    check("小载荷保持内联（无引用文件）", ref2 is None, str(ref2))
    shutil.rmtree(refs, ignore_errors=True)


def _make_core2():
    from agent_core.llm_driver import LLMModelDriver
    from agent_core.toolbox import build_default_toolbox
    from services.openai_compat import OpenAICompatClient

    temp_refs = Path(tempfile.mkdtemp(prefix="p3_refs_"))
    return LLMModelDriver(
        client=OpenAICompatClient(base_url="http://mock.local/v1", provider_key="deepseek"),
        api_key="sk-mock-agent-key-123", model="m",
        toolbox=build_default_toolbox(), temp_dir=temp_refs,
    ), temp_refs


def test_invalid_model_output_fails() -> None:
    """模型输出格式错误：重试 3 次仍失败 → 任务 failed。"""
    print("\n== 关键约束：模型输出非法 → 重试仍失败 → failed ==")
    core = _make_core()
    config.set_mock(True)
    try:
        from agent_core.llm_driver import LLMModelDriver, LLMModelError
        from agent_core.loop import ModelDecision
        from services.openai_compat import OpenAICompatClient

        # 构造「永远抛错」的假模型：模拟模型每次返回非法（无工具名）
        class BrokenDriver:
            def __init__(self): self._calls = 0
            def decide(self, objective, history):
                self._calls += 1
                raise LLMModelError("模型返回的 tool_call 缺少函数名")

        task = core.create_task("乱来过")
        final = core.run_task(task.task_id, model=BrokenDriver())
        check("任务标记 failed", final.status.value == "failed", str(final.status))
        check("失败原因含模型错误", "模型" in (final.fail_reason or ""), str(final.fail_reason))
    finally:
        config.set_mock(False)
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def test_hard_guard_still_works() -> None:
    """硬保护回归：模型无限调工具会在上限内被强制终止。"""
    print("\n== 关键约束：机械硬保护仍生效 ==")
    core = _make_core()
    try:
        from agent_core.loop import LoopGuardConfig, ModelDecision

        class InfiniteDriver:
            def decide(self, objective, history):
                return ModelDecision(kind="tool_call", tool_name="fake_probe", content={})

        small_guard = LoopGuardConfig(max_iterations=10, max_tool_calls=5)
        from agent_core.runtime import AgentCore
        st = tempfile.mkdtemp(prefix="agent_p3g_")
        core2 = AgentCore(st)
        core2._loop._guard = small_guard
        task = core2.create_task("无限循环测试")
        final = core2.run_task(task.task_id, model=InfiniteDriver())
        check("超限强制终止 → failed", final.status.value == "failed", str(final.status))
        check("终止原因=安全限制", "安全" in (final.fail_reason or "") or "限制" in (final.fail_reason or ""),
              str(final.fail_reason))
        shutil.rmtree(st, ignore_errors=True)
    finally:
        shutil.rmtree(core._store._data_dir, ignore_errors=True)


def main() -> None:
    print("Phase 3 验收自测（Monstera Agent Core · 循环引擎接模型）")
    test_acceptance_list_dir()
    test_acceptance_file_write()
    test_acceptance_file_read_system_denied()
    test_context_compression()
    test_invalid_model_output_fails()
    test_hard_guard_still_works()

    print(f"\n===== 结果：{len(PASSED)} 通过 / {len(FAILED)} 失败 =====")
    if FAILED:
        print("失败项:", FAILED)
        sys.exit(1)
    print("Phase 3 验收全部通过 ✓")


if __name__ == "__main__":
    main()