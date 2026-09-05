"""调用日志与账单路由"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from database import get_db
from models import Provider, UsageLog

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
def list_logs(
    provider_id: Optional[int] = None,
    date: Optional[str] = None,  # 格式 YYYY-MM-DD（精确的一天；与 days 互斥，优先 date）
    days: Optional[int] = None,  # 近 N 天（含今天）
    status: Optional[str] = None,  # 过滤：success / failed
    limit: int = 200,   # 分页：每页条数（上限 500）
    offset: int = 0,    # 分页：偏移
    db: Session = Depends(get_db),
):
    """查询调用日志：支持按厂商 / 精确日期 / 近 N 天 / 状态过滤，以及 offset+limit 分页。"""
    q = db.query(UsageLog)
    if provider_id is not None:
        q = q.filter(UsageLog.provider_id == provider_id)
    if date:
        try:
            start = datetime.strptime(date, "%Y-%m-%d")
            end = start.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="date 参数格式应为 YYYY-MM-DD")
        q = q.filter(UsageLog.created_at >= start, UsageLog.created_at <= end)
    elif days:
        days = max(1, int(days))
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
        q = q.filter(UsageLog.created_at >= start)
    if status == "success":
        q = q.filter(UsageLog.success == True)  # noqa: E712
    elif status == "failed":
        q = q.filter(UsageLog.success == False)  # noqa: E712
    elif status:
        raise HTTPException(status_code=400, detail="status 仅支持 success / failed")

    limit = min(max(1, int(limit)), 500)
    offset = max(0, int(offset))
    total = q.count()
    logs = q.order_by(UsageLog.id.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [
            {
                "id": l.id,
                "provider_id": l.provider_id,
                "model_id": l.model_id,
                "api_id": l.api_id,
                "request_tokens": l.request_tokens,
                "response_tokens": l.response_tokens,
                "cache_hit_tokens": l.cache_hit_tokens,
                "cache_miss_tokens": l.cache_miss_tokens,
                "cost": l.cost,
                "latency_ms": l.latency_ms,
                "success": bool(l.success),
                "error_message": l.error_message,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
    }


@router.get("/billing")
def billing(days: int = 1, provider_id: Optional[int] = None, db: Session = Depends(get_db)):
    """总账单/用量页。provider_id 非空时仅统计该厂商（单厂商用量明细）。

    days：统计范围（天）。1=今日；7/30 为“近 N 天”（含今天）。
    口径沿用来路清晰的主流平台拆分：
      - 输入 input   = cache_miss_tokens（真实需计费的新输入）
      - 缓存 cached  = cache_hit_tokens（命中缓存，输入的一部分）
      - 输出 output  = response_tokens
    返回每日 trend 序列（含补零整天），便于前端画趋势图。
    全部在 SQL 层聚合（GROUP BY），日志量大也不把明细拉进内存。
    """
    days = max(1, int(days))
    now = datetime.now()
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    t0 = today0 - timedelta(days=days - 1)  # days=1 时回到今天 0 点
    _ok = case((UsageLog.success == True, 1), else_=0)  # noqa: E712
    filters = [UsageLog.created_at >= t0]  # 上界用 now（含今天当前时刻）
    if provider_id is not None:
        filters.append(UsageLog.provider_id == provider_id)

    total_row = (
        db.query(
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.cost), 0.0),
            func.coalesce(func.sum(_ok), 0),
            func.coalesce(func.sum(UsageLog.cache_miss_tokens), 0),
            func.coalesce(func.sum(UsageLog.cache_hit_tokens), 0),
            func.coalesce(func.sum(UsageLog.response_tokens), 0),
        )
        .filter(*filters)
        .one()
    )
    total_calls = int(total_row[0])
    total_cost = round(float(total_row[1] or 0), 6)
    success_count = int(total_row[2])
    success_rate = round(success_count / total_calls, 4) if total_calls else 0.0
    total_tokens = {
        "input": int(total_row[3] or 0),
        "cached": int(total_row[4] or 0),
        "output": int(total_row[5] or 0),
    }

    def _tokens(miss, hit, resp):
        return {"input": int(miss or 0), "cached": int(hit or 0), "output": int(resp or 0)}

    provider_rows = (
        db.query(
            UsageLog.provider_id,
            Provider.display_name,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.cost), 0.0),
            func.coalesce(func.sum(_ok), 0),
            func.coalesce(func.sum(UsageLog.cache_miss_tokens), 0),
            func.coalesce(func.sum(UsageLog.cache_hit_tokens), 0),
            func.coalesce(func.sum(UsageLog.response_tokens), 0),
        )
        .outerjoin(Provider, Provider.id == UsageLog.provider_id)
        .filter(*filters)
        .group_by(UsageLog.provider_id, Provider.display_name)
        .order_by(func.count(UsageLog.id).desc())
        .all()
    )
    by_provider = []
    for pid, pname, calls, cost, ok, miss, hit, resp in provider_rows:
        calls = int(calls)
        by_provider.append({
            "provider_id": pid,
            "display_name": pname or str(pid),
            "calls": calls,
            "cost": round(float(cost or 0), 6),
            "success_rate": round(int(ok) / calls, 4) if calls else 0.0,
            "tokens": _tokens(miss, hit, resp),
        })

    model_rows = (
        db.query(
            UsageLog.provider_id,
            Provider.display_name,
            UsageLog.model_id,
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.cost), 0.0),
            func.coalesce(func.sum(_ok), 0),
            func.coalesce(func.sum(UsageLog.cache_miss_tokens), 0),
            func.coalesce(func.sum(UsageLog.cache_hit_tokens), 0),
            func.coalesce(func.sum(UsageLog.response_tokens), 0),
        )
        .outerjoin(Provider, Provider.id == UsageLog.provider_id)
        .filter(*filters)
        .group_by(UsageLog.provider_id, UsageLog.model_id)
        .order_by(func.count(UsageLog.id).desc())
        .all()
    )
    by_model = []
    for pid, pname, mid, calls, cost, ok, miss, hit, resp in model_rows:
        calls = int(calls)
        by_model.append({
            "provider_id": pid,
            "model_id": mid,
            "display_name": pname or str(pid),
            "calls": calls,
            "cost": round(float(cost or 0), 6),
            "success_rate": round(int(ok) / calls, 4) if calls else 0.0,
            "tokens": _tokens(miss, hit, resp),
        })

    # 每日趋势：GROUP BY 按自然日；缺失的天补零，保证曲线连续
    trend_rows = (
        db.query(
            func.date(UsageLog.created_at).label("day"),
            func.count(UsageLog.id),
            func.coalesce(func.sum(UsageLog.cost), 0.0),
        )
        .filter(*filters)
        .group_by("day")
        .order_by("day")
        .all()
    )
    sums = {r[0]: (int(r[1]), round(float(r[2] or 0), 6)) for r in trend_rows}
    trend = []
    d = t0
    while d <= now:
        ds = d.strftime("%Y-%m-%d")
        calls, cost = sums.get(ds, (0, 0.0))
        trend.append({"date": ds, "calls": calls, "cost": cost})
        d += timedelta(days=1)

    return {
        "days": days,
        "date_from": t0.strftime("%Y-%m-%d"),
        "date_to": now.strftime("%Y-%m-%d"),
        "total_calls": total_calls,
        "total_cost": total_cost,
        "success_rate": success_rate,
        "total_tokens": total_tokens,
        "by_provider": by_provider,
        "by_model": by_model,
        "trend": trend,
    }
