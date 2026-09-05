# -*- coding: utf-8 -*-
"""Phase 6 移植能力单元冒烟：file_edit / user_gate / MemoryTrail / LLMDriver 压缩+记忆注入。
运行：.venv\\Scripts\\python.exe _p6_features_smoke.py
"""
import tempfile
import pathlib

# ---- 1. file_edit 工具行为 ----
from agent_core.toolbox.fs_tools import FileEditTool

d = pathlib.Path(tempfile.mkdtemp())
f = d / "a.py"
f.write_text('def hello():\n    return "hi"\n\nprint(x)\n', encoding="utf-8")
t = FileEditTool()
r = t.execute({"path": str(f), "old_string": "print(x)", "new_string": 'print("done")'})
assert r.success and r.data["replaced"] == "once", r
assert 'print("done")' in f.read_text(encoding="utf-8"), f.read_text(encoding="utf-8")
r2 = t.execute({"path": str(f), "old_string": "NOT_EXISTS", "new_string": "y"})
assert not r2.success and "未找到" in r2.error, r2
r3 = t.execute({"path": str(f), "old_string": '"', "new_string": "'"})  # 引号出现多次
assert not r3.success and "次" in r3.error, r3
print("1. file_edit OK")

# ---- 2. user_gate file_edit 规则 ----
from agent_core.user_gate import RiskEvaluator

ev = RiskEvaluator()
assert ev.evaluate("file_edit", {"path": "C:/Windows/system32/x"}).level == "confirm"
assert ev.evaluate("file_edit", {"path": str(f)}).level == "confirm"          # 已有文件
assert ev.evaluate("file_edit", {"path": str(d / "new.txt")}).level == "confirm"  # 不存在
print("2. user_gate file_edit rules OK")

# ---- 3. MemoryTrail 提炼 + 召回 + 持久化 ----
from agent_core.memory_trail import MemoryTrail
from agent_core.events import get_bus, AgentEvent, EventType

data_dir = pathlib.Path(tempfile.mkdtemp())
mt = MemoryTrail(data_dir)
tid = "task_mem_1"
mt.attach(tid)
bus = get_bus()
bus.publish(AgentEvent(task_id=tid, type=EventType.OBJECTIVE_DEFINED,
                       payload={"objective": "修复登录接口 401 问题"}))
bus.publish(AgentEvent(task_id=tid, type=EventType.TOOL_RESULT_RECEIVED,
                       payload={"tool": "file_read", "success": True,
                                "data": {"path": "src/auth.py"}}))
bus.publish(AgentEvent(task_id=tid, type=EventType.TOOL_RESULT_RECEIVED,
                       payload={"tool": "file_write", "success": True,
                                "data": {"path": "src/auth_fix.py", "mode": "created"}}))
bus.publish(AgentEvent(task_id=tid, type=EventType.TASK_COMPLETED,
                       payload={"answer": "把 token 过期判断提前到中间件"}))
recall = mt.recall("登录接口 401 修复")
assert recall and "登录接口 401" in recall[0], recall
assert mt.recall("画一只猫") == []
print("3a. memory recall OK ->", recall[0][:40])
mt2 = MemoryTrail(data_dir)
n = mt2.restore()
assert n == 1, n
assert mt2.recall("修复登录 401")[0].startswith("[历史经验")
print("3b. memory persist OK")

# ---- 4. LLMDriver：预算驱动压缩 + 记忆注入 ----
from agent_core.llm_driver import LLMModelDriver
from agent_core.loop import Observation

driver = LLMModelDriver.__new__(LLMModelDriver)
driver._recent_steps_full = 3
driver._early_history_chars_budget = 6000
driver._obs_inline_max_chars = 800
driver._memory_recall = lambda obj: ["[历史经验 test] old login fix"]
driver._used_refs = []
driver._client = None
driver._toolbox = None
driver._temp_dir = None
history = [Observation(step=i, tool_name="ls", success=True, summary="s" * 50) for i in range(1, 8)]
msgs = driver._build_messages("fix login", history)
sys_content = msgs[0]["content"]
assert "【历史经验" in sys_content and "test" in sys_content
joined = "\n".join(m["content"] for m in msgs)
assert "早期步骤摘要" in joined
assert "第4步 ls: 成功" in joined        # 预算内保留最近早期步骤
assert "第6步工具结果 ls" in joined      # 最近3步保留完整细节
print("4. llm_driver memory+compress OK")

# ---- 5. 上下文预算（修复 4）：10MB 工具结果不内联、上下文不超 8K tokens ----
import tempfile as _tf
import pathlib as _pl

ref_dir = _pl.Path(_tf.mkdtemp())
d2 = LLMModelDriver.__new__(LLMModelDriver)
for attr, val in (("_recent_steps_full", 3), ("_early_history_chars_budget", 6000),
                  ("_obs_inline_max_chars", 800), ("_memory_recall", None),
                  ("_used_refs", []), ("_client", None), ("_toolbox", None),
                  ("_temp_dir", ref_dir)):
    setattr(d2, attr, val)
big = "x" * (10 * 1024 * 1024)   # 10MB 工具结果（file_read 读大文件场景）
big_obs = Observation(step=1, tool_name="file_read", success=True, summary="[file_read] 已返回（结果过长，已截断）", raw=big)
body, ref = d2._ref_or_inline(big_obs)
assert ref is not None and "已存本地文件" in body, (body, ref)
assert _pl.Path(ref).exists()
small_obs = Observation(step=1, tool_name="file_read", success=True, summary="短结果", raw="短")
body2, ref2 = d2._ref_or_inline(small_obs)
assert ref2 is None and "短结果" in body2
# 全 messages 序列化后字符量远低于 8K tokens（按 2 字符/token 上保守估算）
msgs_big = d2._build_messages("read big file", [big_obs])
total_chars = sum(len(m["content"]) for m in msgs_big)
assert total_chars < 8000 * 2, f"上下文可能超 8K tokens: {total_chars} chars"
print(f"5. context budget OK (10MB->ref, msgs={total_chars} chars < 16K)")
print("ALL SMOKE PASS")