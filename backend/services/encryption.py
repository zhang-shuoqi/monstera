"""API Key 加密存储：Fernet 对称加密

密钥优先级：环境变量 MONSTERA_ENCRYPTION_KEY > backend/.key 文件 > 自动生成新密钥。
环境变量可以是 Fernet 格式密钥，也可以是任意口令（PBKDF2 派生为 Fernet 密钥）。
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_FILE = os.path.join(BACKEND_DIR, ".key")

# PBKDF2 参数。权衡说明：盐固定（无随机盐）意味着同一口令必得同一密钥——
# 这是刻意设计，否则每次重启口令派生出不同密钥，旧密文全部解不开。
# 本工具定位为本地单机使用，威胁模型不含离线暴力破解数据库的场景；
# 若需更强保护，请直接通过 MONSTERA_ENCRYPTION_KEY 提供 Fernet 密钥。
_PBKDF2_ITERATIONS = 600_000  # OWASP 2023 对 PBKDF2-HMAC-SHA256 的建议值
_PBKDF2_SALT = b"monstera-local-key-derive-v2"


def _derive_key(passphrase: str) -> bytes:
    """任意口令 → Fernet 密钥（PBKDF2-HMAC-SHA256）"""
    digest = hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), _PBKDF2_SALT, _PBKDF2_ITERATIONS
    )
    return base64.urlsafe_b64encode(digest)


def _load_or_create_key() -> bytes:
    env_key = os.getenv("MONSTERA_ENCRYPTION_KEY")
    if env_key:
        try:
            Fernet(env_key.encode())
            return env_key.encode()  # 本身就是合法 Fernet 密钥
        except Exception:
            return _derive_key(env_key)  # 任意口令 → PBKDF2 派生
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            key = f.read().strip()
        if key:
            return key
    # 自动生成并保存到 backend/.key
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt_api_key(plain: str) -> str:
    """加密 API Key，返回可存库的字符串"""
    return _fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted: str) -> str:
    """解密 API Key"""
    try:
        return _fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
