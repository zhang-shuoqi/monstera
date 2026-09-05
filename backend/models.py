"""SQLAlchemy 数据模型"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from database import Base


class Provider(Base):
    """厂商（如 DeepSeek）"""
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)        # OpenAI 兼容端点，必须从库读取，禁止写死
    balance_url = Column(String, default="")          # 余额查询端点；未配置则不查余额
    docs_url = Column(String, default="")
    recharge_url = Column(String, default="")      # 官方充值/账户页；无独立充值页则留空
    is_builtin = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class PricingRule(Base):
    """厂商计费规则：关键词包含匹配 → 单价（¥/百万 tokens）。
    一个厂商可有多条规则，按添加顺序匹配；无匹配时视为未知价格，不计费。"""
    __tablename__ = "pricing_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    keywords = Column(Text, nullable=False)  # JSON 数组，如 '["flash"]'
    input_price = Column(Float, nullable=False)
    output_price = Column(Float, nullable=False)


class Model(Base):
    """具体模型（从厂商 /models 动态同步）"""
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    model_id = Column(String, nullable=False)
    display_name = Column(String, default="")
    description = Column(Text, default="")
    context_window = Column(Integer, default=0)
    vision = Column(Boolean, default=False)  # 是否支持识图（多模态），驱动前端发图按钮
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class UserApi(Base):
    """用户粘贴的 API Key（加密存储）"""
    __tablename__ = "user_apis"
    __table_args__ = {"sqlite_autoincrement": True}  # 禁止复用已删除的 id

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    name = Column(String, default="主 API")
    api_key_encrypted = Column(Text, nullable=False)
    is_primary = Column(Boolean, default=False)
    status = Column(String, default="unknown")  # verified / failed / unknown
    balance = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)      # 最近一次检测/调用的延迟
    last_check_at = Column(DateTime, nullable=True)  # 最近一次有效性检测时间
    created_at = Column(DateTime, default=datetime.now)


class UsageLog(Base):
    """调用日志"""
    __tablename__ = "usage_logs"
    __table_args__ = {"sqlite_autoincrement": True}  # 禁止复用已删除的 id

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    model_id = Column(String, nullable=False)
    api_id = Column(Integer, ForeignKey("user_apis.id"), nullable=False)
    request_tokens = Column(Integer, default=0)
    response_tokens = Column(Integer, default=0)
    cache_hit_tokens = Column(Integer, default=0)
    cache_miss_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class Conversation(Base):
    """对话"""
    __tablename__ = "conversations"
    __table_args__ = {"sqlite_autoincrement": True}  # 禁止复用已删除的 id

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, default="新对话")
    pinned = Column(Boolean, default=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    # 排序时间仅由业务代码显式更新（发消息时），重命名/置顶不改变排序
    updated_at = Column(DateTime, default=datetime.now)


class Message(Base):
    """对话消息"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    images = Column(Text, nullable=True)  # 用户附图（data URL 列表，JSON 数组），None 表示无图
    model_id = Column(String, nullable=True)
    cost = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class MemoryDoc(Base):
    """记忆中枢文档：一个对话对应一份本地 Markdown（用户记忆资产，可自由编辑）"""
    __tablename__ = "memory_docs"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    # 文档在本地磁盘的相对路径（相对项目根），如 memory/conv_12.md
    path = Column(String, nullable=False)
    title = Column(String, default="")
    # 每次整理的状态与所用引擎：pending / done / failed / degraded
    status = Column(String, default="pending")
    engine = Column(String, default="")  # 本次整理用到的引擎：local-model / rules
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)


class ConversationMemory(Base):
    """对话 → 记忆文档的写入映射（多对一：多个对话可续写进同一份记忆文档）。

    - 继承记忆：新建对话时把 conversation_id 指向某份旧文档，消息续写进该文档；
    - 不继承：无映射，首条成功后自动建立新文档并写入映射。
    """
    __tablename__ = "conversation_memory"

    conversation_id = Column(Integer, ForeignKey("conversations.id"), primary_key=True)
    memory_doc_id = Column(Integer, ForeignKey("memory_docs.id"), nullable=False)
