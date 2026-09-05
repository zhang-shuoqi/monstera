"""Agent 内核 · 最小 HTTP 网关（任务生命周期 / 用户确认 / 设置 / SSE 事件流）。

约定：所有状态变更只允许经 StateStore 的受控入口（set_status / incr_*），
      非法状态迁移直接 409。运行进度推送给前端走 SSE（Phase 5：替代 800ms 轮询）。
"""
from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any, Dict, Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent_core.events import get_bus
from agent_core.runtime import AgentCore, get_core
from agent_core.state_store import IllegalTransitionError

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _core() -> AgentCore:
    return get_core()


def _task_404(task_id: str):
    raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")


@router.post("/tasks")
def create_task(body: dict):
    """创建新任务（状态 idle）。"""
    objective = (body.get("objective") or "").strip()
    if not objective:
        raise HTTPException(status_code=400, detail="objective 不能为空")
    task = _core().create_task(objective)
    return task.to_dict()


@router.post("/tasks/{task_id}/run")
def run_loop(task_id: str, body: dict):
    """驱动循环引擎。

    body 可选：
      - rounds (int)：Phase 0 空循环演示轮数（默认 3，假工具）。
      - plan (list)：Phase 1 真实工具验收 —— 每步 {"tool": "list_dir", "args": {...}}。
      - with_gate (bool)：Phase 2 —— 工具执行前过用户闸。
      - model (dict)：Phase 3 —— 真实模型驱动 {"provider_id": int, "model_id": str}。
        循环引擎用 Function Calling 调用该模型自主决策（复用账号体系里的 API Key）。
    给了 model 走真实模型决策；给了 plan 走脚本计划；否则走空循环演示。
    """
    body = body or {}
    rounds = int(body.get("rounds", 3))
    plan = body.get("plan")
    with_gate = bool(body.get("with_gate"))
    model_spec = body.get("model")
    if plan is not None and not isinstance(plan, list):
        raise HTTPException(status_code=400, detail="plan 必须为数组: [{\"tool\": ..., \"args\": ...}]")
    model_driver = None
    if isinstance(model_spec, dict) and model_spec.get("provider_id") and model_spec.get("model_id"):
        model_driver = _build_model_driver(int(model_spec["provider_id"]), str(model_spec["model_id"]))
    try:
        task = _core().run_task(task_id, rounds=rounds, plan=plan, with_gate=with_gate,
                                model=model_driver, persist_refs=model_driver is not None)
    except HTTPException:
        raise
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (RuntimeError, ValueError) as exc:   # LLMModelError / KeyError 等 → 421（调用侧问题）
        raise HTTPException(status_code=421, detail=str(exc))
    except KeyError:
        _task_404(task_id)
    # Phase 5 成本感知：模型驱动任务完成后按计费规则写入预估费用
    if model_driver is not None:
        _record_cost(task_id, int(model_spec["provider_id"]), str(model_spec["model_id"]))
    return _core().get_task(task_id).to_dict()


def _record_cost(task_id: str, provider_id: int, model_id: str) -> None:
    """按厂商计费规则估算本次任务费用（¥），写入任务快照。未知价格 → None（不按默认价计费）。"""
    from agent_core.runtime import get_core
    from database import SessionLocal
    from services.routing import lookup_price

    core = get_core()
    task = core.get_task(task_id)
    if task is None:
        return
    usage = task.model_usage or {}
    pt = int(usage.get("prompt_tokens") or 0)
    ct = int(usage.get("completion_tokens") or 0)
    if not pt and not ct:
        return
    db = SessionLocal()
    try:
        price = lookup_price(db, provider_id, model_id)
    finally:
        db.close()
    if not price:
        core._store.set_estimated_cost(task_id, None)
        return
    cost = pt / 1_000_000 * price["input"] + ct / 1_000_000 * price["output"]
    core._store.set_estimated_cost(task_id, cost)


@router.get("/settings")
def get_settings():
    """Agent 设置（Phase 5 硬化）：硬保护三档 + 两开关。"""
    return _core().get_settings().to_dict()


@router.put("/settings")
def update_settings(body: dict):
    """更新 Agent 设置：部分更新，数值自动钳制到合法区间。"""
    _core().update_settings(body or {})
    return _core().get_settings().to_dict()


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str):
    """错误恢复（从头重试）：新建同目标任务。终态不变量保留（不重跑原任务）。"""
    try:
        task = _core().retry_task(task_id)
    except KeyError:
        _task_404(task_id)
    return {"retried": True, "task": task.to_dict()}


@router.post("/tasks/{task_id}/stop")
def stop_task(task_id: str):
    """真实停止运行中的任务（Phase 5）：中断事件置位，循环在下轮迭代开头终止并标记失败。"""
    core = _core()
    if core.get_task(task_id) is None:
        _task_404(task_id)
    ok = core.stop_task(task_id)
    if not ok:
        raise HTTPException(status_code=409, detail="任务当前不在运行中，无需停止")
    task = core.get_task(task_id)
    return {"stopped": True, "task": task.to_dict() if task else None}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    """删除任务（历史任务列表"删除"）：仅终态可删；运行中/待确认返回 409。"""
    core = _core()
    if core.get_task(task_id) is None:
        _task_404(task_id)
    ok = core.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=409, detail="仅终态（已完成/已失败）任务可删除")
    return {"deleted": True}


@router.put("/tasks/{task_id}")
def update_task(task_id: str, body: dict):
    """任务展示元数据更新（右键重命名 / 置顶，与历史对话一致）。

    body 中 title 传空串恢复默认（回退显示 objective）；pinned 传布尔切换置顶。
    只改展示字段，不触状态机；任意任务状态（含运行中）均可改名/置顶。
    """
    title = body.get("title")
    pinned = body.get("pinned")
    if title is None and pinned is None:
        raise HTTPException(status_code=400, detail="需要提供 title 或 pinned 至少一项")
    meta = _core().update_task_meta(task_id, title=title, pinned=pinned)
    if meta is None:
        _task_404(task_id)
    return {"task": meta}


def _terminate_kind(event_list: list) -> str:
    """从事件时间线推导终止类型（仅 SSE 快照输出的装饰信息，不影响内核状态机）。

    内核终态只有 completed/failed，fail_reason 保留。此处把 failed 细分三类：
      - user_interrupt : 用户在 UI 上中断运行（loop._check_stop_or_abort 发布 user_stopped）
      - plan_denied    : 计划确认被拒绝（runtime._plan_confirm 发布 plan_denied）
      - error          : 其余一切失败（model_error / guard_limit / invalid / interrupted / 工具错误）
    判定依据事件 payload 里的 reason / detail 文本，回退到 fail_reason 关键字。
    """
    for ev in reversed(event_list):
        if ev.get("type") != "TASK_FAILED":
            continue
        p = ev.get("payload") or {}
        reason = p.get("reason") or ""
        detail = (p.get("detail") or p.get("reason") or "").lower()
        if reason == "user_stopped" or "手动停止" in detail or "中断运行" in detail:
            return "user_interrupt"
        if reason == "plan_denied" or ("计划" in detail and "拒" in detail):
            return "plan_denied"
        return "error"
    return "error"


def _task_snapshot(core: AgentCore, task_id: str) -> Dict[str, Any]:
    """任务完整视图：状态快照 + 事件时间线（SSE 每帧与 GET /tasks/{id} 同一数据源）。"""
    task = core.get_task(task_id)
    if task is None:
        raise KeyError(task_id)
    payload = task.to_dict()
    events = core.timeline(task_id)
    payload["events"] = events
    # 快照层只读装饰：failed 任务细分终止类型，供前端渲染终态卡片文案（不改内核状态机）
    payload["meta"] = {"terminate_kind": _terminate_kind(events) if payload.get("status") == "failed" else None}
    return payload


@router.get("/tasks/{task_id}/stream")
def stream_task(task_id: str):
    """SSE 事件流（Phase 5：替代轮询）。

    - 首帧推送完整快照（含事件时间线全文，前端可直接整体渲染）；
    - 之后每次总线产生新事件，立即推送最新完整快照；
    - 15s 无事件发 keepalive 注释；客户端断开自动退订总线。
    前端收到任务进入终态后可自行关闭连接；后端不感知关闭时保持挂起。
    """
    core = _core()
    if core.get_task(task_id) is None:
        _task_404(task_id)

    def _send() -> Iterator[str]:
        incoming: "queue.Queue[object]" = queue.Queue(maxsize=512)   # 事件堆积上限，防慢客户端无限膨胀
        unsub = get_bus().subscribe(task_id, lambda ev: incoming.put(ev))
        try:
            initial = _task_snapshot(core, task_id)
            yield f"event: task\ndata: {json.dumps(initial, ensure_ascii=False, default=str)}\n\n"
            last_beat = time.time()
            while True:
                try:
                    incoming.get(timeout=0.5)
                except queue.Empty:
                    if time.time() - last_beat >= 15:
                        yield ": keepalive\n\n"
                        last_beat = time.time()
                    continue
                last_beat = time.time()
                try:
                    snap = _task_snapshot(core, task_id)
                except KeyError:
                    break    # 任务被删除：结束流
                yield f"event: task\ndata: {json.dumps(snap, ensure_ascii=False, default=str)}\n\n"
        finally:
            unsub()

    return StreamingResponse(
        _send(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _build_model_driver(provider_id: int, model_id: str):
    """按 provider + model 构造 Phase 3 真实模型驱动（复用账号体系的 API Key 与计费配置）。"""
    import config
    from agent_core.llm_driver import LLMModelDriver
    from agent_core.runtime import get_core
    from agent_core.toolbox import build_default_toolbox
    from database import SessionLocal
    from models import Provider, UserApi
    from services.encryption import decrypt_api_key
    from services.routing import build_client

    db = SessionLocal()
    try:
        provider = db.get(Provider, provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="厂商不存在")
        api = (
            db.query(UserApi)
            .filter(UserApi.provider_id == provider.id)
            .order_by(UserApi.is_primary.desc(), UserApi.id)
            .first()
        )
        if api is None:
            raise HTTPException(status_code=400, detail="该厂商尚未添加 API。请先粘贴 API Key")
        key = decrypt_api_key(api.api_key_encrypted)
        if not key:
            raise HTTPException(status_code=400, detail="API Key 无法解密（加密密钥已变更），请重新粘贴")
        client = build_client(provider)

        # 引用文件临时目录：随任务数据持久化（agent_data/refs），供时间线回放
        ref_dir = config.AGENT_DATA_DIR / "refs"
        ref_dir.mkdir(parents=True, exist_ok=True)
        return LLMModelDriver(
            client=client, api_key=key, model=model_id,
            toolbox=build_default_toolbox(),
            temp_dir=ref_dir,
            memory_recall=get_core().memory_recall,   # Phase 6：原子记忆检索注入（客观经验勿盲从）
        )
    finally:
        db.close()


@router.post("/tasks/{task_id}/decision")
def decide_intervention(task_id: str, body: dict):
    """用户对危险操作弹窗作出选择（Phase 2）。
    body: {"allow": bool, "reason": str?}  allow=False 时 reason 会回传给模型。
    """
    body = body or {}
    allow = bool(body.get("allow", True))
    ok = _core().resolve_intervention(task_id, allow, body.get("reason", ""))
    if not ok:
        raise HTTPException(status_code=409, detail="该任务当前没有待确认的弹窗（可能已处理或不在确认状态）")
    task = _core().get_task(task_id)
    return {"resolved": True, "allow": allow, "task": task.to_dict() if task else None}


@router.get("/tools")
def list_tools():
    """Agent 工具箱注册表：3 个冻结工具（file trio）的元信息。"""
    return _core().tools_info()


@router.get("/tasks")
def list_tasks():
    """历史任务表（index.json）：taskId/objective/status/createdAt/completedAt/snapshotPath"""
    return _core().history_rows()


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """任务完整状态 + 事件时间线（持久化，重启后仍可回放）。"""
    core = _core()
    task = core.get_task(task_id)
    if task is None:
        _task_404(task_id)
    payload = task.to_dict()
    payload["events"] = core.timeline(task_id)
    return payload


@router.get("/tasks/{task_id}/timeline")
def get_timeline(task_id: str):
    """任务完整事件时间线（Phase 4：纵向步骤流的数据源，重启后仍可回放）。"""
    core = _core()
    task = core.get_task(task_id)
    if task is None:
        _task_404(task_id)
    return {"taskId": task_id, "events": core.timeline(task_id)}