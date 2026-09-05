"""Pydantic 请求/响应模型"""
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class ApiCreate(BaseModel):
    """粘贴 API 请求体"""
    api_key: str = Field(min_length=1)
    name: Optional[str] = None


class ChatRequest(BaseModel):
    """发送对话消息请求体"""
    provider_id: int
    model_id: str
    message: str = Field(default="", max_length=6000)  # 可为空：支持"只发图片不带文字"
    images: List[str] = Field(default_factory=list)  # 图片 data URL 列表（可选，多模态）
    conversation_id: Optional[int] = None  # 为空时后端自动新建对话

    @model_validator(mode="after")
    def message_or_images_required(self):
        """至少提供文字或图片之一；文字可为空（纯图片消息），但不能两者都缺。"""
        if not self.message.strip() and not self.images:
            raise ValueError("消息不能为空：请填写文字或至少附带一张图片")
        return self


class ModelInfo(BaseModel):
    model_id: str
    display_name: str = ""
    description: str = ""
    context_window: int = 0
    vision: bool = False  # 是否支持识图（多模态），驱动前端发图按钮


class ApiInfo(BaseModel):
    id: int
    name: str
    masked_key: str
    is_primary: bool
    status: str
    balance: Optional[float] = None
    decrypt_failed: bool = False  # 密钥无法解密（加密密钥已变更），需重新粘贴
    latency_ms: Optional[int] = None


class ProviderInfo(BaseModel):
    id: int
    name: str
    display_name: str
    docs_url: str = ""
    recharge_url: str = ""
    status: str = "未连接"
    latency_ms: Optional[int] = None
    balance: Optional[float] = None
    today_calls: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    models: List[ModelInfo] = []
    apis: List[ApiInfo] = []


class ChatResponse(BaseModel):
    content: str
    model_id: str
    cost: Optional[float] = None   # 价格无法匹配时为 None（未知价格，未计费）
    price_known: bool = True       # False 表示该模型价格未知
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    cache_hit_tokens: int
    cache_miss_tokens: int
    conversation_id: int
    title: str
