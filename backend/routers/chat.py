"""对话消息路由：按 provider 路由到对应厂商（OpenAI 兼容），持久化消息与日志

- 通过 services.routing.build_client 按 providers 表里的 base_url 构造客户端，
  不针对任何具体厂商写死；新增厂商无需改代码
- conversation_id 缺省时自动新建对话（成功收尾时才创建，失败/中断不留空壳）
- 自动携带当前对话最近 20 条消息（约 10 轮）作为上下文
- 首条消息后自动把"新对话"重命名为消息前 18 字
- 用户消息与新对话仅随成功回复一并原子落库：流式中断或全部失败时
  不写入任何数据，从根源上避免孤儿消息
- 价格无法匹配的模型：cost 记 None，price_known=False，绝不按默认价计费
- 支持 SSE 流式接口 /chat/stream（前端默认使用）
"""
import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import Conversation, Message, Provider, UsageLog, UserApi
from schemas import ChatRequest, ChatResponse
from services.encryption import decrypt_api_key
from services import memory as memory_svc
from services.routing import build_client, lookup_price

router = APIRouter(prefix="/api", tags=["chat"])

log = logging.getLogger("monstera.chat")

CONTEXT_MESSAGE_LIMIT = 20  # 携带的历史消息条数上限


def _calc_cost(db: Session, provider_id: int, model_id: str,
               prompt_tokens: int, completion_tokens: int):
    """费用计算：按该厂商的计费规则（pricing_rules 表）关键词匹配；
    未知价格返回 (None, False)，绝不按默认价计费。"""
    price = lookup_price(db, provider_id, model_id)
    if price is None:
        return None, False
    cost = round(
        prompt_tokens / 1_000_000 * price["input"]
        + completion_tokens / 1_000_000 * price["output"],
        6,
    )
    return cost, True


def _auto_title(message: str) -> str:
    """首条消息自动生成标题：去换行、截前 18 字"""
    snippet = message.strip().replace("\n", " ")
    return snippet[:18] + ("…" if len(snippet) > 18 else "")


def _user_content(message: str, images: list) -> list:
    """构造用户消息 content：无图时退回纯文本字符串（保持现有行为，兼容只读文本的模型）；
    有图时用 OpenAI 多模态 content 数组（text + 多张 image_url）。"""
    if not images:
        return message
    content = [{"type": "text", "text": message}]
    for url in images:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return content


def _parse_images(raw) -> list:
    """把数据库里存的 images JSON 字符串解析成列表；为空/损坏时返回 []"""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def _restore_message(m: Message):
    """把历史消息还原成多模态格式：带图用户消息还原成 content 数组，用于续带上下文"""
    images = _parse_images(m.images)
    if m.role == "user" and images:
        return {"role": m.role, "content": _user_content(m.content, images)}
    return {"role": m.role, "content": m.content}


def _prepare(body: ChatRequest, db: Session):
    """公共前置：校验厂商/API、定位对话、组装上下文。
    本函数只读不写：新对话与用户消息都不在此落库，
    成功收尾（_finalize_success）时才一并原子写入 ——
    流式中断或全部失败时不会留下任何孤儿数据。
    返回 (provider, apis, conv, should_rename, messages)
    conv：已存在的对话对象；None 表示本请求将新建对话"""
    provider = db.get(Provider, body.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")

    apis = (
        db.query(UserApi)
        .filter(UserApi.provider_id == provider.id)
        .order_by(UserApi.is_primary.desc(), UserApi.id)
        .all()
    )
    if not apis:
        raise HTTPException(status_code=400, detail="该厂商尚未添加 API，请先在右侧粘贴 API Key")

    if body.conversation_id:
        conv = db.get(Conversation, body.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
        should_rename = conv.title == "新对话"
        history = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id.desc())
            .limit(CONTEXT_MESSAGE_LIMIT)
            .all()
        )
    else:
        conv = None          # 新对话：成功时才创建，失败/中断不留空壳
        should_rename = True
        history = []

    history.reverse()
    messages = [_restore_message(m) for m in history]
    messages.append({"role": "user", "content": _user_content(body.message, body.images)})
    return provider, apis, conv, should_rename, messages


def _finalize_success(db: Session, provider, api, conv, should_rename, body,
                      content, pt, ct, cached, latency_ms, cost, price_known):
    """成功收尾：用户消息与 assistant 回复一并落库（原子提交）、写日志、
    自动命名、更新 API 延迟，返回响应字典。
    conv 为 None 时自动创建新对话（避免流式中断产生空壳对话）。"""
    miss = max(pt - cached, 0)
    db.add(UsageLog(
        provider_id=provider.id,
        model_id=body.model_id,
        api_id=api.id,
        request_tokens=pt,
        response_tokens=ct,
        cache_hit_tokens=cached,
        cache_miss_tokens=miss,
        cost=cost,  # 未知价格为 None
        latency_ms=latency_ms,
        success=True,
        error_message=None,
    ))
    if conv is None:
        conv = Conversation(title="新对话", provider_id=provider.id)
        db.add(conv)
        db.flush()  # 获取 conv.id
    # 先 user 后 assistant：自增 id 按此顺序分配，保证上下文排序正确
    um = Message(
        conversation_id=conv.id,
        role="user",
        content=body.message,
        images=json.dumps(body.images) if body.images else None,  # 附图持久化，历史重开可还原
    )
    db.add(um)
    am = Message(
        conversation_id=conv.id,
        role="assistant",
        content=content,
        model_id=body.model_id,
        cost=cost,
        latency_ms=latency_ms,
    )
    db.add(am)
    if should_rename:
        conv.title = _auto_title(body.message)
    conv.updated_at = datetime.now()
    api.status = "verified"
    api.latency_ms = latency_ms  # 用真实调用耗时更新延迟
    db.commit()
    db.refresh(um)
    db.refresh(am)
    return {
        "content": content,
        "model_id": body.model_id,
        "cost": cost,
        "price_known": price_known,
        "latency_ms": latency_ms,
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cache_hit_tokens": cached,
        "cache_miss_tokens": miss,
        "conversation_id": conv.id,
        "user_message_id": um.id,
        "assistant_message_id": am.id,
        "title": conv.title,
    }


def _record_failure(db: Session, provider, api, body, latency_ms, error):
    log.warning("对话调用失败 provider=%s api=%s(%s) model=%s：%s",
                provider.id, api.id, api.name, body.model_id, error)
    db.add(UsageLog(
        provider_id=provider.id,
        model_id=body.model_id,
        api_id=api.id,
        request_tokens=0, response_tokens=0,
        cache_hit_tokens=0, cache_miss_tokens=0,
        cost=0.0, latency_ms=latency_ms,
        success=False, error_message=error,
    ))
    api.status = "failed"
    db.commit()


@router.post("/chat", response_model=ChatResponse, deprecated=True)
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    """【已弃用】非流式对话，仅为兼容保留；新代码请使用 POST /chat/stream"""
    log.warning("POST /chat 已弃用，请改用 /chat/stream（provider=%s conv=%s）",
                body.provider_id, body.conversation_id)
    provider, apis, conv, should_rename, messages = _prepare(body, db)
    client = build_client(provider)

    errors = []
    for api in apis:  # 主 API 优先，失败自动尝试备用
        key = decrypt_api_key(api.api_key_encrypted)
        if not key:
            errors.append(f"{api.name}: 密钥无法解密（加密密钥已变更），请重新粘贴该 API Key")
            continue

        t0 = time.perf_counter()
        result = client.chat_completion(key, body.model_id, messages)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        if result.get("success"):
            pt = int(result.get("prompt_tokens", 0))
            ct = int(result.get("completion_tokens", 0))
            cached = int(result.get("cached_tokens", 0))
            cost, price_known = _calc_cost(db, provider.id, body.model_id, pt, ct)
            resp = _finalize_success(
                db, provider, api, conv, should_rename, body,
                result.get("content", ""), pt, ct, cached, latency_ms, cost, price_known,
            )
            return ChatResponse(**resp)

        _record_failure(db, provider, api, body, latency_ms, result.get("error", "调用失败"))
        errors.append(f"{api.name}: {result.get('error', '调用失败')}")

    # 全部失败：未落库任何消息/对话（前端会恢复输入框文本），直接抛错
    raise HTTPException(status_code=502, detail="；".join(errors) or "所有 API 均调用失败")


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def chat_stream(body: ChatRequest, db: Session = Depends(get_db)):
    """流式对话（SSE）：
    data: {"type":"delta","content":...}   增量文本（多条）
    data: {"type":"meta", ...}             收尾元数据（对话 id/标题/费用/耗时/价格已知性）
    data: {"type":"error","error":...}     失败（之后流结束）
    data: [DONE]

    用户消息与新对话都在成功收尾（_finalize_success）时一并原子落库；
    客户端中途断开或全部失败时不写入任何数据，从根源上避免孤儿消息/空对话。
    """
    provider, apis, conv, should_rename, messages = _prepare(body, db)

    def gen():
        s = SessionLocal()  # 独立会话：流式响应生命周期长于请求级依赖
        try:
            prov = s.get(Provider, provider.id)
            conv_ = s.get(Conversation, conv.id) if conv else None
            apis_ = (
                s.query(UserApi)
                .filter(UserApi.provider_id == prov.id)
                .order_by(UserApi.is_primary.desc(), UserApi.id)
                .all()
            )
            client = build_client(prov)
            errors = []
            for api in apis_:
                key = decrypt_api_key(api.api_key_encrypted)
                if not key:
                    errors.append(f"{api.name}: 密钥无法解密（加密密钥已变更），请重新粘贴该 API Key")
                    continue

                t0 = time.perf_counter()
                parts = []
                usage = None
                stream_error = None
                for evt in client.chat_completion_stream(key, body.model_id, messages):
                    if evt["type"] == "delta":
                        parts.append(evt["content"])
                        yield _sse({"type": "delta", "content": evt["content"]})
                    elif evt["type"] == "usage":
                        usage = evt
                    elif evt["type"] == "error":
                        stream_error = evt["error"]
                        break
                latency_ms = int((time.perf_counter() - t0) * 1000)

                if stream_error is None and usage is not None:
                    pt = usage.get("prompt_tokens", 0)
                    ct = usage.get("completion_tokens", 0)
                    cached = usage.get("cached_tokens", 0)
                    cost, price_known = _calc_cost(s, prov.id, body.model_id, pt, ct)
                    meta = _finalize_success(
                        s, prov, api, conv_, should_rename, body,
                        "".join(parts), pt, ct, cached, latency_ms, cost, price_known,
                    )
                    # 记忆中枢：后台线程本地整理（不阻塞、不联网、不调用户 API）。
                    # model_name 如实记录"实际回答的那个模型"。
                    memory_svc.trigger_async(
                        meta["conversation_id"],
                        f"{prov.display_name} · {body.model_id}",
                        body.message,
                        "".join(parts),
                    )
                    yield _sse({"type": "meta", **meta})
                    yield "data: [DONE]\n\n"
                    return

                err = stream_error or "未返回用量信息，无法计费（已中止）"
                _record_failure(s, prov, api, body, latency_ms, err)
                errors.append(f"{api.name}: {err}")

            # 全部失败：未落库任何消息/对话，直接报错（前端会恢复输入框文本）
            yield _sse({"type": "error", "error": "；".join(errors) or "所有 API 均调用失败"})
            yield "data: [DONE]\n\n"
        finally:
            s.close()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
