"""厂商与 API 管理路由"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Model as ModelEntry
from models import Provider, UsageLog, UserApi
from schemas import ApiInfo, ModelInfo, ProviderInfo
from services.encryption import decrypt_api_key, encrypt_api_key
from services.openai_compat import OpenAICompatClient
from services.routing import build_client

router = APIRouter(prefix="/api", tags=["providers"])

log = logging.getLogger("monstera.providers")


def _today_start() -> datetime:
    now = datetime.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _mask_key(key: str) -> str:
    """脱敏显示：只显示前 6 位和后 4 位"""
    if not key:
        return "***"
    if len(key) <= 10:
        return key[:3] + "***"
    return f"{key[:6]}...{key[-4:]}"


def _decrypt(api) -> Optional[str]:
    """解密 API Key；失败（加密密钥变更/损坏）返回 None 而非抛错"""
    key = decrypt_api_key(api.api_key_encrypted)
    return key if key else None


# 视觉关键词：命中即判定该模型支持识图（多模态）。远程 /models 通常不标注视觉能力，
# 据此启发式推断，保证前端发图按钮与后端能力一致。
_VISION_KEYWORDS = (
    "vision", "vl", "vlx", "-4o", "4o-", "omni", "gemini", "claude",
    "llama-3.2", "llama4", "minicpm-v", "qwen-vl", "glm-4v",
)


def _model_vision(provider_key: str, model_id: str) -> bool:
    """启发式判断模型是否支持识图：优先看模型 id 是否含视觉关键词，
    Anthropic 全系 Claude 与 OpenAI 4o 系视为视觉模型。"""
    name = (model_id or "").lower()
    if any(k in name for k in _VISION_KEYWORDS):
        return True
    return False


def _sync_models(db: Session, provider_id: int, provider_key: str, remote_models: list):
    """模型全量对账：远端存在的激活/新增，远端不存在的置 is_active=False（不残留过期条目）"""
    remote_ids = set()
    for m in remote_models:
        mid = m.get("id")
        if not mid:
            continue
        remote_ids.add(mid)
        vision = bool(m.get("vision")) or _model_vision(provider_key, mid)
        entry = (
            db.query(ModelEntry)
            .filter(ModelEntry.provider_id == provider_id, ModelEntry.model_id == mid)
            .first()
        )
        if entry:
            entry.is_active = True
            entry.display_name = m.get("display_name") or entry.display_name
            entry.vision = vision
        else:
            db.add(ModelEntry(
                provider_id=provider_id,
                model_id=mid,
                display_name=m.get("display_name") or mid,
                description=m.get("description") or "",
                context_window=m.get("context_window") or 0,
                vision=vision,
                is_active=True,
            ))
    if remote_ids:
        db.query(ModelEntry).filter(
            ModelEntry.provider_id == provider_id,
            ModelEntry.is_active == True,  # noqa: E712
            ModelEntry.model_id.notin_(remote_ids),
        ).update({"is_active": False}, synchronize_session=False)


def _ordered_apis(db: Session, provider_id: int) -> List[UserApi]:
    return (
        db.query(UserApi)
        .filter(UserApi.provider_id == provider_id)
        .order_by(UserApi.is_primary.desc(), UserApi.id)
        .all()
    )


def _status_of(db: Session, provider_id: int):
    """状态判定（反映当前真实可用性）：
    - 无 API → 未连接
    - 该厂商最近一次对话调用失败 → 异常（备用 API 成功救回时，最新日志为成功 → 不再异常）
    - 主 API 最近一次有效性检测（check）失败，且晚于最近一次成功日志 → 异常
    - 最近成功调用延迟 ≥ 2000ms → 缓慢
    - 否则 → 正常
    """
    apis = _ordered_apis(db, provider_id)
    if not apis:
        return "未连接", None, apis
    primary = apis[0]
    last = (
        db.query(UsageLog)
        .filter(UsageLog.provider_id == provider_id)
        .order_by(UsageLog.id.desc())
        .first()
    )
    latency = primary.latency_ms if primary.latency_ms is not None else (
        last.latency_ms if (last and last.success) else None
    )
    # check 失败（且晚于最近日志）→ 真实不可用
    if primary.status == "failed" and primary.last_check_at is not None:
        if last is None or primary.last_check_at >= (last.created_at or datetime.min):
            return "异常", latency, apis
    if last is not None and not last.success:
        return "异常", latency, apis
    if last is not None and last.success and last.latency_ms >= 2000:
        return "缓慢", latency, apis
    return "正常", latency, apis


def _serialize_provider(db: Session, p: Provider) -> ProviderInfo:
    status, latency, apis = _status_of(db, p.id)
    t0 = _today_start()

    # 今日统计合并为一条 GROUP BY 聚合（原为 3 条独立查询）
    stat_row = (
        db.query(
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.cache_hit_tokens), 0),
            func.coalesce(func.sum(UsageLog.cache_miss_tokens), 0),
        )
        .filter(UsageLog.provider_id == p.id, UsageLog.created_at >= t0)
        .one()
    )
    today_calls, hit, miss = int(stat_row[0]), int(stat_row[1]), int(stat_row[2])

    models = (
        db.query(ModelEntry)
        .filter(ModelEntry.provider_id == p.id, ModelEntry.is_active == True)  # noqa: E712
        .order_by(ModelEntry.id)
        .all()
    )

    # 每个 API 只解密一次（原实现解密两次：masked_key 与 decrypt_failed 各一次）
    api_infos = []
    for a in apis:
        key = _decrypt(a)
        api_infos.append(ApiInfo(
            id=a.id,
            name=a.name,
            masked_key="!!DECRYPT_FAILED" if key is None else _mask_key(key),
            is_primary=bool(a.is_primary),
            status=a.status or "unknown",
            balance=a.balance,
            decrypt_failed=key is None,
            latency_ms=a.latency_ms,
        ))

    return ProviderInfo(
        id=p.id,
        name=p.name,
        display_name=p.display_name,
        docs_url=p.docs_url or "",
        recharge_url=p.recharge_url or "",
        status=status,
        latency_ms=latency,
        balance=(apis[0].balance if apis else None),
        today_calls=today_calls,
        cache_hit_tokens=hit,
        cache_miss_tokens=miss,
        models=[
            ModelInfo(
                model_id=m.model_id,
                display_name=m.display_name or m.model_id,
                description=m.description or "",
                context_window=m.context_window or 0,
                vision=bool(m.vision),
            )
            for m in models
        ],
        apis=api_infos,
    )


@router.get("/providers", response_model=dict)
def list_providers(db: Session = Depends(get_db)):
    """获取所有厂商及其模型、API 状态（内置厂商由启动时的 seed 初始化）"""
    items = db.query(Provider).order_by(Provider.id).all()
    return {"providers": [_serialize_provider(db, p).model_dump() for p in items]}


@router.post("/providers/{provider_id}/apis")
def add_api(provider_id: int, body: dict, db: Session = Depends(get_db)):
    """验证并保存 API：请求体 {"api_key": "sk-xxx", "name": "主 API"}"""
    api_key = (body.get("api_key") or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="请填写 API Key")

    provider = db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")

    # 1. 验证 Key（按 provider 的 base_url 路由到 OpenAI 兼容 /models）
    client = build_client(provider)
    result = client.validate_api_key(api_key)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error", "验证失败"))

    # 2. 获取余额（失败不影响保存；未配置 balance_url 则跳过）
    balance = client.get_balance(api_key)

    # 3. 加密存库（若为该厂商第一条 API 则设为主 API）
    existing_count = db.query(UserApi).filter(UserApi.provider_id == provider_id).count()
    name = (body.get("name") or "").strip() or ("主 API" if existing_count == 0 else "备用 API")
    api = UserApi(
        provider_id=provider_id,
        name=name,
        api_key_encrypted=encrypt_api_key(api_key),
        is_primary=(existing_count == 0),
        status="verified",
        balance=balance,
        last_check_at=datetime.now(),
    )
    db.add(api)
    db.commit()
    db.refresh(api)

    # 4. 模型全量对账（激活/新增/停用过期条目）
    _sync_models(db, provider_id, provider.name or "", result.get("models", []))
    db.commit()

    serialized = _serialize_provider(db, provider)
    return {
        "success": True,
        "api_id": api.id,
        "balance": balance,
        "models": serialized.model_dump()["models"],
    }


@router.delete("/providers/{provider_id}/apis/{api_id}")
def remove_api(provider_id: int, api_id: int, db: Session = Depends(get_db)):
    """删除指定 API：
    - 级联删除其历史调用日志（避免孤儿日志被同厂商新 API 继承统计）
    - 若删除主 API 且有备用，自动提升第一个备用为主
    - 若该厂商 API 全部删除，停用其全部模型条目
    """
    api = (
        db.query(UserApi)
        .filter(UserApi.id == api_id, UserApi.provider_id == provider_id)
        .first()
    )
    if not api:
        raise HTTPException(status_code=404, detail="API 不存在")
    was_primary = bool(api.is_primary)
    db.query(UsageLog).filter(UsageLog.api_id == api_id).delete()
    db.delete(api)
    db.commit()
    rest = _ordered_apis(db, provider_id)
    if was_primary and rest:
        rest[0].is_primary = True
    if not rest:  # API 全删 → 模型全部停用（下次粘贴新 Key 时重新对账激活）
        db.query(ModelEntry).filter(ModelEntry.provider_id == provider_id).update(
            {"is_active": False}, synchronize_session=False
        )
    db.commit()
    return {"success": True}


@router.post("/providers/{provider_id}/check")
def check_provider(provider_id: int, db: Session = Depends(get_db)):
    """主动检测（全免费接口，不产生对话费用）：
    - 对每个 API 调用 GET /models 验证 Key 是否仍被官方承认 → 更新 status/latency_ms/last_check_at
    - 主 API 同时刷新余额（GET /user/balance）
    - 多个 API 并行检测（互不阻塞，单个 Key 网络慢不拖累整体）
    - 返回更新后的厂商聚合数据
    """
    provider = db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")
    apis = _ordered_apis(db, provider_id)
    if not apis:
        raise HTTPException(status_code=400, detail="该厂商尚未添加 API")

    # 主线程完成解密（Session 非线程安全，工作线程只做纯网络请求）
    entries = [(a, _decrypt(a)) for a in apis]
    # 提前取出 provider 配置（跨线程只用作构造客户端的普通属性，避免在工作线程访问 ORM 对象）
    pc = (provider.base_url, provider.balance_url, provider.display_name or provider.name, provider.name)

    def _work(key: str, need_balance: bool):
        t0 = time.perf_counter()
        client = OpenAICompatClient(base_url=pc[0], balance_url=(pc[1] or "") or None,
                                    name=pc[2], provider_key=pc[3])
        r = client.validate_api_key(key)
        latency = int((time.perf_counter() - t0) * 1000)
        bal = None
        if need_balance and r.get("valid"):
            bal = client.get_balance(key)
        return r, latency, bal

    with ThreadPoolExecutor(max_workers=min(8, len(entries))) as pool:
        futures = [
            (api, pool.submit(_work, key, bool(api.is_primary)))
            for api, key in entries if key is not None
        ]
        outcomes = [(api, fut.result()) for api, fut in futures]

    results = []
    for api, (r, latency, bal) in outcomes:
        api.last_check_at = datetime.now()
        api.latency_ms = latency
        if r.get("valid"):
            api.status = "verified"
            if bal is not None:
                api.balance = bal
            results.append({"id": api.id, "name": api.name, "ok": True, "latency_ms": latency})
            # 顺带对账模型列表（官方下线/新增模型）
            _sync_models(db, provider_id, provider.name or "", r.get("models", []))
        else:
            api.status = "failed"
            results.append({"id": api.id, "name": api.name, "ok": False,
                            "error": r.get("error", "验证失败"), "latency_ms": latency})
            log.warning("API 检测失败 provider=%s api=%s(%s)：%s",
                        provider_id, api.id, api.name, r.get("error"))

    # 解密失败的 API（加密密钥已变更）
    for api, key in entries:
        if key is None:
            api.status = "failed"
            api.last_check_at = datetime.now()
            results.append({"id": api.id, "name": api.name, "ok": False,
                            "error": "密钥无法解密（加密密钥已变更），请移除后重新粘贴"})

    db.commit()
    serialized = _serialize_provider(db, provider)
    return {"success": True, "results": results, "provider": serialized.model_dump()}


@router.put("/providers/{provider_id}/apis/{api_id}/primary")
def set_primary(provider_id: int, api_id: int, db: Session = Depends(get_db)):
    """设置主 API，其余自动转为备用"""
    api = (
        db.query(UserApi)
        .filter(UserApi.id == api_id, UserApi.provider_id == provider_id)
        .first()
    )
    if not api:
        raise HTTPException(status_code=404, detail="API 不存在")
    db.query(UserApi).filter(UserApi.provider_id == provider_id).update({"is_primary": False})
    api.is_primary = True
    db.commit()
    return {"success": True}
