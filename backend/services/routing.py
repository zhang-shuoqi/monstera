"""最薄的路由层：按 providers 表记录构造 OpenAI 兼容客户端，并按厂商计费。

新增厂商只需要在数据库里：
  1. providers 表加一条记录：name / display_name / base_url（必填）/ balance_url（可选）/ docs_url
  2. pricing_rules 表加若干条关键词→单价规则（可选，缺省则该厂商计费视为"未知"）
chat.py 与 providers.py 就会自动按 provider_id 路由到 OpenAI 兼容端点（本地直连，
不经任何云端代理），无需改动任何业务代码。base_url 一律从库读取，禁止写死。
"""
import json
import logging
from typing import Optional

from services.openai_compat import OpenAICompatClient

log = logging.getLogger("monstera.routing")


def build_client(provider) -> OpenAICompatClient:
    """按 providers 表的一行记录构造客户端。base_url 从库读取，禁止写死。

    provider.balance_url 为空时不启用余额查询（get_balance 返回 None）。
    """
    return OpenAICompatClient(
        base_url=provider.base_url,
        balance_url=(provider.balance_url or "") or None,
        name=provider.display_name or provider.name,
        provider_key=provider.name,  # 供 Mock 区分各厂商的假模型/假数据
    )


def lookup_price(db, provider_id: int, model_id: str) -> Optional[dict]:
    """按厂商计费规则做关键词包含匹配。

    成功：{"input": 单价, "output": 单价}（¥/百万 tokens）
    无匹配/无规则：返回 None（前端显示"未知价格"，cost 记为 null，绝不按默认价计费）
    """
    from models import PricingRule

    mid = (model_id or "").lower()
    rules = (
        db.query(PricingRule)
        .filter(PricingRule.provider_id == provider_id)
        .all()
    )
    for r in rules:
        try:
            kws = json.loads(r.keywords)
        except (TypeError, ValueError):
            continue
        if kws and any(k in mid for k in kws):
            return {"input": r.input_price, "output": r.output_price}
    return None