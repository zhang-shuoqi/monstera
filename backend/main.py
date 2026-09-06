"""Monstera 后端入口：FastAPI 应用，端口 8765"""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from database import init_db, SessionLocal
from models import Provider
from routers import providers, chat, logs, conversations, system, memory, agent

# 应用日志：uvicorn 已接管访问日志，这里只配置 monstera.* 业务日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("monstera.main")

app = FastAPI(title="Monstera Backend", version="0.1.0")

# 本地 CORS：只放行 file:// 来源（桌面壳/开发模式以 file:// 加载，其 Origin 为 "null"）。
# 收紧为 ["null"] 可阻断任何三方网站跨域读取/调用本地后端（包括触发对话消耗用户 Key 费用）。
# 若确有 http:// 来源直接访问端口的需求，再按需加入对应 Origin。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["null"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers.router)
app.include_router(chat.router)
app.include_router(logs.router)
app.include_router(conversations.router)
app.include_router(system.router)
app.include_router(memory.router)
app.include_router(agent.router)


# 前端拆分（片3 3-A）后：css/js/vendor 由后端单源伺服。
# 保证 http://127.0.0.1:8765/ 一个源即可完整加载外部资源（不依赖独立静态服务器）。
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles as _StaticFiles
_PROJECT_ROOT = _Path(__file__).resolve().parent.parent


class _NoCacheStatic(_StaticFiles):
    """静态文件响应统一加 Cache-Control: no-cache（js/css/vendor）。

    消除浏览器持久缓存墙：前端改动后无需 ?rev= 也能拿到最新字节。
    HTML 已由根路由单独带 no-cache，此处覆盖 js/css/vendor。"""

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


for _sub in ("css", "js", "vendor"):
    _dir = _PROJECT_ROOT / _sub
    if _dir.is_dir():
        app.mount(f"/{_sub}", _NoCacheStatic(directory=str(_dir)), name=_sub)


# 内置厂商清单：新增厂商只需在此加一行（+ 对应计费规则），启动时自动种子化，
# 无需改代码。字段说明：
#   name / display_name / base_url（必填，OpenAI 兼容端点）/ balance_url（可选）/ docs_url
_BUILTIN_PROVIDERS = [
    {
        "name": "deepseek", "display_name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "balance_url": "https://api.deepseek.com/user/balance",
        "docs_url": "https://platform.deepseek.com",
        # 整理：充值入口在站内导航（无独立 URL 子路径），指向平台首页即可，供充值按钮使用
        "recharge_url": "https://platform.deepseek.com",
        "pricing_rules": [  # (关键词组, 输入价, 输出价) —— ¥/百万 tokens
            (["flash"], 1.0, 3.0),             # 轻量快速档
            (["pro", "reasoner"], 5.0, 15.0),  # 旗舰推理档
            (["chat"], 2.0, 6.0),              # 标准对话档
        ],
    },
    {
        "name": "kimi", "display_name": "Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "balance_url": "https://api.moonshot.cn/v1/users/me/balance",
        "docs_url": "https://platform.moonshot.cn",
        # 整理：充值/账户入口在站内控制台（充值位于账户中心），指向控制台首页；若官方改版请用户核实后修改
        "recharge_url": "https://platform.moonshot.cn/console",
        # 官方定价（platform.moonshot.cn 2026-08）：
        #   kimi-k2.6 输入6.50/输出27.00，kimi-k2.5 输入4.00/输出21.00，moonshot-v1 输入10/输出30
        # 如官方价格变动，请在库里直接改 pricing_rules，无需改代码。
        "pricing_rules": [
            (["k2.6"], 6.5, 27.0),
            (["k2.5"], 4.0, 21.0),
            (["moonshot"], 10.0, 30.0),
        ],
    },
]


def seed_builtin_providers():
    """启动时初始化内置厂商（DeepSeek + Kimi）。

    幂等：已有同名厂商只补齐 balance_url，不覆盖用户对 models / pricing_rules 的修改；
    计费规则仅当该厂商现在没有任何规则时才写入默认。
    """
    import json

    from models import PricingRule

    db = SessionLocal()
    try:
        for spec in _BUILTIN_PROVIDERS:
            provider = db.query(Provider).filter(Provider.name == spec["name"]).first()
            if not provider:
                provider = Provider(
                    name=spec["name"],
                    display_name=spec["display_name"],
                    base_url=spec["base_url"],
                    balance_url=spec.get("balance_url", ""),
                    docs_url=spec.get("docs_url", ""),
                    recharge_url=spec.get("recharge_url", ""),
                    is_builtin=True,
                )
                db.add(provider)
                db.commit()
                db.refresh(provider)
            else:
                # 幂等补齐：老库已存在但缺新增字段时补上，不覆盖用户修改
                if spec.get("balance_url") and not provider.balance_url:
                    provider.balance_url = spec["balance_url"]
                if spec.get("recharge_url") and not provider.recharge_url:
                    provider.recharge_url = spec["recharge_url"]
                if db.is_modified(provider):
                    db.commit()

            # 默认计费规则：仅当该厂商尚无任何规则时写入（不覆盖用户修改）
            if db.query(PricingRule).filter(PricingRule.provider_id == provider.id).count() == 0:
                for kws, p_in, p_out in spec.get("pricing_rules", []):
                    db.add(PricingRule(
                        provider_id=provider.id,
                        keywords=json.dumps(kws),
                        input_price=p_in,
                        output_price=p_out,
                    ))
                db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时初始化数据库与内置厂商，退出时清理（现代 FastAPI 写法，
    取代已弃用的 @app.on_event('startup')，行为完全一致）。"""
    init_db()
    seed_builtin_providers()
    log.info("Monstera 后端已就绪（Mock 模式：%s）", "开启" if config.is_mock() else "关闭")
    yield


# 挂载 lifespan（FastAPI 从 router 读取；须在注册路由后再赋值）
app.router.lifespan_context = lifespan


@app.get("/")
def root():
    """直接提供前端页面（浏览器无法打开 file:// 时使用 http://127.0.0.1:8765/）"""
    from fastapi.responses import FileResponse
    from pathlib import Path
    return FileResponse(
        Path(__file__).resolve().parent.parent / "index.html",
        headers={"Cache-Control": "no-cache"},  # 本地工具：避免浏览器缓存旧版前端
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=False)
