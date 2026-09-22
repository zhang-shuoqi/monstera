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
        "docs_url": "https://platform.deepseek.com/api_keys",
        "recharge_url": "https://platform.deepseek.com",
        "pricing_rules": [
            (["flash"], 1.0, 3.0),
            (["pro", "reasoner"], 5.0, 15.0),
            (["chat"], 2.0, 6.0),
        ],
    },
    {
        "name": "kimi", "display_name": "Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "balance_url": "https://api.moonshot.cn/v1/users/me/balance",
        "docs_url": "https://platform.moonshot.cn/console/api-keys",
        "recharge_url": "https://platform.moonshot.cn/console",
        "pricing_rules": [
            (["k2.6"], 6.5, 27.0),
            (["k2.5"], 4.0, 21.0),
            (["moonshot"], 10.0, 30.0),
        ],
    },
    {
        "name": "qwen", "display_name": "通义千问",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "balance_url": "",
        "docs_url": "https://bailian.console.aliyun.com/#/api-key",
        "recharge_url": "https://bailian.console.aliyun.com",
        "pricing_rules": [
            (["max"], 4.0, 12.0),
            (["plus"], 0.5, 2.0),
            (["flash"], 0.2, 0.6),
            (["coder"], 1.0, 3.0),
        ],
    },
    {
        "name": "zhipu", "display_name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "balance_url": "",
        "docs_url": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
        "recharge_url": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
        "pricing_rules": [
            (["5.3"], 5.0, 20.0),
            (["5.2"], 4.0, 16.0),
            (["flash"], 0.5, 2.0),
            (["turbo"], 1.0, 4.0),
        ],
    },
    {
        "name": "doubao", "display_name": "豆包",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "balance_url": "",
        "docs_url": "https://console.volcengine.com/ark/api-key",
        "recharge_url": "https://console.volcengine.com/ark/overview",
        "pricing_rules": [
            (["pro", "2-1-pro"], 2.0, 6.0),
            (["turbo"], 0.8, 2.0),
            (["lite"], 0.3, 1.0),
        ],
    },
    {
        "name": "minimax", "display_name": "MiniMax",
        "base_url": "https://api.minimax.cn/v1",
        "balance_url": "",
        "docs_url": "https://platform.minimaxi.com/user-center/basic-information/interface-key",
        "recharge_url": "https://platform.minimaxi.com/user-center/payment/balance",
        "pricing_rules": [
            (["m3"], 3.0, 9.0),
            (["m2.7"], 2.0, 6.0),
            (["m2.5"], 1.5, 4.5),
            (["m2.1"], 1.0, 3.0),
        ],
    },
    {
        "name": "hunyuan", "display_name": "腾讯混元",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "balance_url": "",
        "docs_url": "https://console.cloud.tencent.com/hunyuan/start",
        "recharge_url": "https://hunyuan.cloud.tencent.com/#/app/statistics",
        "pricing_rules": [
            (["hy4"], 4.0, 12.0),
            (["hy3"], 1.0, 4.0),
            (["turbos"], 0.5, 2.0),
        ],
    },
    {
        "name": "mimo", "display_name": "MiMo",
        "base_url": "https://api.xiaomimimo.com/v1",
        "balance_url": "",
        "docs_url": "https://platform.xiaomimimo.com/#/console/api-keys",
        "recharge_url": "https://platform.xiaomimimo.com/#/console/usage",
        "pricing_rules": [
            (["pro"], 2.0, 6.0),
            (["fast"], 1.0, 3.0),
            (["32b"], 0.5, 1.5),
        ],
    },
    {
        "name": "wenxin", "display_name": "文心一言",
        "base_url": "https://qianfan.baidubce.com/v2",
        "balance_url": "",
        "docs_url": "https://console.bce.baidu.com/qianfan/ais/console/apiKey",
        "recharge_url": "https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application/v2",
        "pricing_rules": [
            (["5.1"], 5.0, 15.0),
            (["5.0"], 3.0, 9.0),
            (["turbo"], 1.0, 3.0),
        ],
    },
    {
        "name": "xinghuo", "display_name": "讯飞星火",
        "base_url": "https://maas-token-api.cn-huabei-1.xf-yun.com/v2",
        "balance_url": "",
        "docs_url": "https://maas.xfyun.cn/tokenPlan/subscription",
        "recharge_url": "https://maas.xfyun.cn/tokenPlan/subscription",
        "pricing_rules": [
            (["x2.5"], 1.6, 6.0),
            (["x2"], 2.0, 7.0),
        ],
    },
    {
        "name": "pangu", "display_name": "盘古",
        "base_url": "https://api.modelarts-maas.com/openai/v1",
        "balance_url": "",
        "docs_url": "https://console.huaweicloud.com/modelarts/#/model-studio/authmanage",
        "recharge_url": "https://console.huaweicloud.com/modelarts/#/model-studio/homepage",
        "pricing_rules": [
            (["2.0-pro"], 3.0, 9.0),
            (["2.0-flash"], 1.0, 3.0),
        ],
    },
    {
        "name": "stepfun", "display_name": "Step",
        "base_url": "https://api.stepfun.com/step_plan/v1",
        "balance_url": "",
        "docs_url": "https://platform.stepfun.com/interface-key",
        "recharge_url": "https://platform.stepfun.com/step-plan",
        "pricing_rules": [
            (["5-preview"], 5.0, 15.0),
            (["3.7"], 3.0, 9.0),
            (["3.5"], 2.0, 6.0),
        ],
    },
    {
        "name": "sensenova", "display_name": "商汤日日新",
        "base_url": "https://api.sensenova.cn/compatible-mode/v2",
        "balance_url": "",
        "docs_url": "https://console.sensecore.cn/aistudio/management/api-key",
        "recharge_url": "https://www.sensenova.cn/token-plan",
        "pricing_rules": [
            (["u1"], 4.0, 12.0),
            (["6.8"], 1.0, 3.0),
        ],
    },
]


def seed_builtin_providers():
    """启动时初始化内置厂商（13 家 OpenAI 兼容厂商）。

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
