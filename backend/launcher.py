"""PyInstaller 冻结入口（桌面打包专用）。

业务逻辑全部复用 main.py / config.py 及 routers/services，本文件只做两件事：
  1) 冻结态下把「可写数据」重定向到用户目录（数据库、加密密钥、记忆文档），
     避免写入安装目录（Program Files 通常只读）或 PyInstaller 解包临时目录。
  2) 用 app 对象（而非 "main:app" import 串）启动 uvicorn，规避冻结态 import 串失效。

非冻结态直接 `python launcher.py` 也等价于 `python main.py`，可用于手工验证。
"""
import os
import sys


def _user_data_dir() -> str:
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Monstera")
    return os.path.join(os.path.expanduser("~"), ".monstera")


def _redirect_writable_paths_if_frozen():
    if not getattr(sys, "frozen", False):
        return
    base = _user_data_dir()
    os.makedirs(base, exist_ok=True)

    # 1) 数据根（驱动 PROJECT_ROOT / memory 记忆文档目录）
    os.environ.setdefault("MONSTERA_DATA_DIR", base)
    # 2) 数据库文件
    os.environ.setdefault("MONSTERA_DB_PATH", os.path.join(base, "monstera.db"))
    # 3) 加密密钥：稳定持久保存在用户目录（否则每次重启密钥漂移、旧密文全部解不开）
    key_file = os.path.join(base, ".key")
    if not os.path.exists(key_file):
        from cryptography.fernet import Fernet
        with open(key_file, "wb") as f:
            f.write(Fernet.generate_key())
    with open(key_file, "rb") as f:
        os.environ.setdefault("MONSTERA_ENCRYPTION_KEY", f.read().decode().strip())
    # 4) 本地整理模型默认关闭：桌面包不随附 1GB 模型，记忆整理降级为纯规则压缩
    os.environ.setdefault("MONSTERA_LOCAL_MODEL", "0")


_redirect_writable_paths_if_frozen()

import uvicorn  # noqa: E402
from main import app  # noqa: E402


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")