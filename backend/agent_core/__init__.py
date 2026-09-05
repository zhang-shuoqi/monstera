"""Monstera Agent Core（地基内核）· Phase 0 骨架。

模块划分（与地基总图一致，设计定稿 v1.0 · 二）：
    events.py       事件契约 + 进程内事件总线（按 task_id 过滤）
    state_store.py  任务状态存储（内存 + 本地 JSON 原子持久化 + 恢复）
    loop.py         循环引擎（模型-工具-观察）+ Phase 0 假模型/假工具
    runtime.py      AgentCore 组装器：把各模块经事件总线接线
"""