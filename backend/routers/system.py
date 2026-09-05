"""系统开关：Mock 模式查询与热切换"""
from fastapi import APIRouter, HTTPException

import config

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/mock")
def mock_status():
    """浏览器打开 http://127.0.0.1:8765/api/mock 即可查看当前开关状态"""
    return {"enabled": config.is_mock()}


@router.put("/mock")
def toggle_mock(body: dict):
    """热切换：PUT /api/mock  {"enabled": true|false}，无需重启后端"""
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=400, detail='请求体需为 {"enabled": true} 或 {"enabled": false}')
    config.set_mock(enabled)
    return {
        "enabled": config.is_mock(),
        "message": "Mock 模式已开启，所有请求走假数据" if enabled else "Mock 模式已关闭，恢复真实 DeepSeek 调用",
    }
