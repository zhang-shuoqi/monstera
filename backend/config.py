"""全局配置：环境变量、路径、模型价格"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
# 数据根目录：默认项目根（源码运行）；桌面打包态可用 MONSTERA_DATA_DIR 指定用户可写目录，
# 使数据库/记忆文档等用户数据脱离安装目录（Program Files 通常只读）。
PROJECT_ROOT = Path(os.getenv("MONSTERA_DATA_DIR") or BACKEND_DIR.parent)

# 读取 backend/.env（若存在）
load_dotenv(BACKEND_DIR / ".env")


def _resolve_db_path() -> str:
    """数据库路径：默认 backend/monstera.db，相对路径以项目根为基准"""
    raw = os.getenv("MONSTERA_DB_PATH", "backend/monstera.db")
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / raw
    return str(p)


DB_PATH = _resolve_db_path()

# 请求超时（秒）
HTTP_TIMEOUT = 30.0

# 单次对话最大输出 tokens（避免长回复被截断；可按需调整）
MAX_TOKENS = 8192

# ============ 记忆中枢（Memory Hub）============
# 记忆文档目录：对用户可访问、可编辑的本地目录（项目根/memory）
MEMORY_DIR = PROJECT_ROOT / "memory"
# 模型/引擎目录：本地推理二进制与 GGUF（不进 git）
MODELS_DIR = BACKEND_DIR / "models"


def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ============ Agent 内核数据（Agent Core）============
# 单用户本地任务的持久化目录：
#   任务状态 JSON：agent_data/tasks/{task_id}.json（变更即原子落盘）
#   历史任务索引：agent_data/index.json（一张表：taskId/objective/status/createdAt/completedAt）
# 无用户 ID、无权限字段、无租户字段（设计定稿 v1.0 · 八）
AGENT_DATA_DIR = PROJECT_ROOT / "backend" / "agent_data"
AGENT_TASKS_DIR = AGENT_DATA_DIR / "tasks"


def ensure_agent_data_dir():
    AGENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_TASKS_DIR.mkdir(parents=True, exist_ok=True)


# ============ 本地整理模型（可选）============
# 记忆整理想法：优先用本地模型（Qwen2.5-1.5B-Instruct 量化版 + llama.cpp），
# 未放置模型文件/运行失败时自动降级为纯规则压缩（见 services/memory/summarizer.py）。
# 默认开启：模型放好即生效；放好后设 MONSTERA_LOCAL_MODEL=0 可退回纯规则压缩。
LOCAL_MODEL = {
    "enabled": os.getenv("MONSTERA_LOCAL_MODEL", "1").strip().lower() in ("1", "true", "yes", "on"),
    # llama.cpp 里可执行文件（llama-cli / main / llama-cli.exe 均可）
    "llama_cli": (BACKEND_DIR / "models" / "llama-cli").with_suffix(".exe"),
    # 量化 GGUF 模型路径
    "gguf": BACKEND_DIR / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "gen_tokens": 200,   # 本地模型压缩输出上限：要点≈几条短句，200 足够；设小缩短生成窗口（生成是速度瓶颈）
    "timeout_s": 60,     # 本地模型推理超时
    # 推理占用 CPU 线程数。注意：_INFER_LOCK 全局串行锁已保证同一时刻最多跑一个 llama-cli 进程，
    # 因此单进程可安全用多线程提速，不再像旧版"多进程并发抢占"那样卡整机。
    # 默认 4；机器较弱可设 MONSTERA_LOCAL_MODEL_THREADS=2 降占用，强机器可调 6 更快。
    "threads": int(os.getenv("MONSTERA_LOCAL_MODEL_THREADS", "4").strip() or "4"),
}

# 状态判定阈值
SLOW_LATENCY_MS = 2000

# ============ Mock 模式 ============
# 初始值来自环境变量 MONSTERA_MOCK（1/true 开启），运行期可通过 PUT /api/mock 热切换
_MOCK = os.getenv("MONSTERA_MOCK", "0").strip().lower() in ("1", "true", "yes", "on")


def is_mock() -> bool:
    """当前是否处于 Mock 模式（所有厂商请求走假数据）"""
    return _MOCK


def set_mock(enabled: bool):
    """运行时切换 Mock 模式"""
    global _MOCK
    _MOCK = bool(enabled)
