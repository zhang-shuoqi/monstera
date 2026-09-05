"""记忆中枢 V1：把对话整理成用户本地、可编辑的文档。

核心规则：
- 只"存"不"读"，不把记忆喂回给模型（读留给后续版本）；
- 整理在本地异步完成，不阻塞聊天；
- 绝不调用户 API、绝不联网、绝不产生费用；
- 新建对话=新建文档；延续上一对话=记进同一份文档；切换模型也记同一份，但按实际模型名记录。

文档格式：Markdown，按"用户说 / 模型回"追加，存于 config.MEMORY_DIR（项目根/memory）。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

import config
from database import SessionLocal
from models import Conversation, ConversationMemory, MemoryDoc

from . import local_model, rules

log = logging.getLogger("monstera.memory")

# 文档文件命名：memory/conv_<conversation_id>.md（相对项目根存储）
_DOC_REL_PREFIX = "memory/conv_"


def _rel_path(conv_id: int) -> str:
    return f"{_DOC_REL_PREFIX}{conv_id}.md"


def _abs_path(rel: str) -> Path:
    return config.PROJECT_ROOT / rel


# ----------------------------- 后台追加 -----------------------------

def _entry_section(timestamp: str, user: str, assistant: str, model_name: str) -> str:
    parts = [f"## {timestamp} · {model_name}"]
    if user:
        parts += ["### 用户说", user]
    parts += ["### 模型回", assistant]
    return "\n\n".join(parts) + "\n"


def _doc_for_conversation(db: Session, conv_id: int) -> MemoryDoc | None:
    """返回某个对话要"写入"的记忆文档。
    优先查 ConversationMemory 映射（继承记忆=指向旧文档；自己建的新文档也会建映射）；
    兼容旧库：无映射时回退到按归属对话（MemoryDoc.conversation_id）查找，并顺手补建映射。"""
    link = db.query(ConversationMemory).filter(ConversationMemory.conversation_id == conv_id).first()
    if link is not None:
        doc = db.get(MemoryDoc, link.memory_doc_id)
        if doc is not None:
            return doc
    doc = db.query(MemoryDoc).filter(MemoryDoc.conversation_id == conv_id).first()
    if doc is not None:
        db.add(ConversationMemory(conversation_id=conv_id, memory_doc_id=doc.id))
        db.commit()
        return doc
    return None


def _ensure_doc(db: Session, conv: Conversation) -> MemoryDoc:
    """取该对话要写入的记忆文档；没有则新建（归属本对话）并建立写入映射。返回后文件初始头由调用方负责写入。"""
    existing = _doc_for_conversation(db, conv.id)
    if existing is not None:
        return existing
    rel = _rel_path(conv.id)
    doc = MemoryDoc(
        conversation_id=conv.id,
        path=rel,
        title=conv.title or "新对话",
        status="pending",
        engine="",
    )
    db.add(doc)
    db.flush()
    db.add(ConversationMemory(conversation_id=conv.id, memory_doc_id=doc.id))
    return doc


def _write_initial_if_empty(doc: MemoryDoc, conv: Conversation) -> None:
    """文档不存在时写入文件头（含使用说明，用户可自由编辑增删）。"""
    path = _abs_path(doc.path)
    if path.exists():
        return
    header = (
        f"# {conv.title or '我的记忆'}\n\n"
        "> 这是 Monstera 记忆中枢为你维护的本地记忆文档（用户主权资产，不归任何模型）。\n"
        "> 可自由编辑，随时补充你的想法、设计、图片或备注。\n\n"
        "---\n\n"
    )
    config.ensure_memory_dir()
    path.write_text(header, encoding="utf-8")


def append_entry(conversation_id: int, model_name: str, user_text: str, assistant_text: str) -> None:
    """整理一轮对话并追加进记忆文档。供后台线程调用（自带 DB session，线程安全）。"""
    try:
        _append_entry(conversation_id, model_name, user_text, assistant_text)
    except Exception:
        log.exception("记忆整理失败（conversation=%s）", conversation_id)


def _append_entry(conversation_id: int, model_name: str, user_text: str, assistant_text: str) -> None:
    db = SessionLocal()
    try:
        conv = db.get(Conversation, conversation_id)
        if conv is None:
            return
        # 先确保文档存在（pending），再跑本地整理：即使推理很慢/失败，
        # 文档也立即可见，不会因为推理挂住而永远不生成记忆文档。
        doc = _doc_for_conversation(db, conversation_id)
        new_doc = doc is None
        if new_doc:
            doc = _ensure_doc(db, conv)
        _write_initial_if_empty(doc, conv)
        doc.status = "pending"
        doc.error = None
        db.commit()  # 尽早落库，让前端能马上看到这份记忆

        user = rules.filter_user(user_text)
        # 优先本地模型，失败/超时降级规则；summarize 保证有界返回、绝不卡死线程
        assistant = local_model.summarize(assistant_text)
        if assistant is not None:
            engine = "local-model"
            # 模型可能带开场白/结尾客套/超长：再过一道规则清洗，统一成干净要点格式
            assistant = rules._compress_reply(assistant)
        else:
            entry = rules.build_entry(user_text, assistant_text)
            engine = "rules"
            user = entry["user"]
            assistant = entry["assistant"]
        if not user and not assistant:
            # 整轮都被判为无信息量，仅更新状态不写文件
            return _mark(db, conversation_id, "done", engine, None)

        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        section = _entry_section(stamp, user, assistant, model_name)
        path = _abs_path(doc.path)
        # 与上文之间保证有空行分隔：后台异步追加可能落在"用户刚手动编辑过的内容"之后，
        # 若文件结尾没有空行，新章节的 "## 标题" 会与末尾文本粘在同一行，破坏 Markdown 结构。
        cur = path.read_text(encoding="utf-8") if path.exists() else ""
        if cur and not cur.endswith("\n\n"):
            section = ("\n" if not cur.endswith("\n") else "") + "\n" + section
        with path.open("a", encoding="utf-8") as f:
            f.write(section)

        doc.status = "done"
        doc.engine = engine
        doc.error = None
        doc.updated_at = datetime.now()
        db.commit()
        log.info("记忆已整理（%s/%s）：conversation=%s engine=%s 字节=%s",
                 doc.path, model_name, conversation_id, engine, len(section))
    except Exception:
        db.rollback()
        try:
            _mark(db, conversation_id, "failed", None, None)
        except Exception:
            pass
        log.exception("记忆整理异常（conversation=%s）", conversation_id)
        try:
            db.close()
        except Exception:
            pass
        return
    finally:
        db.close()


def _mark(db: Session, conversation_id: int, status: str, engine: str | None, error: str | None) -> None:
    doc = _doc_for_conversation(db, conversation_id)
    if doc is not None:
        doc.status = status
        if engine:
            doc.engine = engine
        if error is not None:
            doc.error = error
        doc.updated_at = datetime.now()
        db.commit()


def trigger_async(conversation_id: int, model_name: str, user_text: str, assistant_text: str) -> None:
    """在后台线程异步整理，绝不阻塞聊天响应。"""
    threading.Thread(
        target=append_entry,
        args=(conversation_id, model_name, user_text, assistant_text),
        daemon=True,
        name=f"memory-{conversation_id}",
    ).start()


# ----------------------------- 查看 / 编辑 -----------------------------

def doc_id_for_conversation(conversation_id: int) -> int | None:
    """返回该对话当前映射的记忆文档 id。
    继承记忆 → 返回旧文档 id；不继承且未写过消息 → None（首条消息后才自动新建文档）。"""
    db = SessionLocal()
    try:
        doc = _doc_for_conversation(db, conversation_id)
        return doc.id if doc else None
    finally:
        db.close()


def list_docs() -> list[dict]:
    db = SessionLocal()
    try:
        rows = (
            db.query(MemoryDoc)
            .join(Conversation, Conversation.id == MemoryDoc.conversation_id)
            .order_by(Conversation.pinned.desc(), MemoryDoc.updated_at.desc())
            .all()
        )
        # 反查每个文档被哪些对话写入（继承记忆会让多个对话写进同一份文档）
        link_rows = (
            db.query(ConversationMemory, Conversation.id, Conversation.title)
            .join(Conversation, Conversation.id == ConversationMemory.conversation_id)
            .all()
        )
        links: dict[int, list[dict]] = {}
        for lm, cid, ctitle in link_rows:
            links.setdefault(lm.memory_doc_id, []).append({"conversation_id": cid, "title": ctitle})

        out = []
        for d in rows:
            abs_path = _abs_path(d.path)
            out.append({
                "id": d.id,
                "conversation_id": d.conversation_id,
                "title": d.title,
                "status": d.status,
                "engine": d.engine,
                "error": d.error,
                "size_bytes": abs_path.stat().st_size if abs_path.exists() else 0,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
                # 会写入本文档的对话：除归属对话外，继承它的对话也在此列
                "writing_conversations": links.get(d.id, []),
            })
        return out
    finally:
        db.close()


def get_doc(doc_id: int) -> dict | None:
    db = SessionLocal()
    try:
        d = db.get(MemoryDoc, doc_id)
        if d is None:
            return None
        path = _abs_path(d.path)
        return {
            "id": d.id,
            "conversation_id": d.conversation_id,
            "title": d.title,
            "status": d.status,
            "engine": d.engine,
            "error": d.error,
            "path": str(path),
            "content": path.read_text(encoding="utf-8") if path.exists() else "",
        }
    finally:
        db.close()


def update_doc(doc_id: int, content: str, title: str | None = None) -> bool:
    """用户手动编辑保存记忆文档。"""
    db = SessionLocal()
    try:
        d = db.get(MemoryDoc, doc_id)
        if d is None:
            return False
        path = _abs_path(d.path)
        config.ensure_memory_dir()
        path.write_text(content or "", encoding="utf-8")
        if title:
            d.title = title
        d.updated_at = datetime.now()
        d.status = "done"  # 用户保存视为已整理
        db.commit()
        return True
    finally:
        db.close()


def open_doc(doc_id: int) -> bool:
    """在系统默认编辑器/查看器中打开记忆文档（Windows 用 os.startfile）。"""
    db = SessionLocal()
    try:
        d = db.get(MemoryDoc, doc_id)
        if d is None:
            return False
        path = _abs_path(d.path)
    finally:
        db.close()
    if not path.exists():
        path.write_text("", encoding="utf-8")
    import os
    if hasattr(os, "startfile"):
        os.startfile(str(path))  # Windows
    else:
        import subprocess
        subprocess.Popen(["open", str(path)])  # macOS
    return True


def delete_doc(doc_id: int) -> bool:
    """删除记忆文档：同步移除本地 .md 文件，再删库并清掉所有对话对它的继承映射。
    文件删除先于库操作：文件删除失败则整体不提交，保持一致性。"""
    db = SessionLocal()
    try:
        d = db.get(MemoryDoc, doc_id)
        if d is None:
            return False
        path = _abs_path(d.path)
        if path.exists():  # 失败会抛 OSError → 阻止库删除，fail-closed
            path.unlink()
        db.query(ConversationMemory).filter(ConversationMemory.memory_doc_id == doc_id).delete()
        db.delete(d)
        db.commit()
        log.info("记忆文档已删除并同步移除本地文件：%s", d.path)
        return True
    finally:
        db.close()


def status() -> dict:
    """本地模型整理引擎的当前就绪状态（只读，供前端展示；不影响调用侧自动降级）。"""
    cfg = config.LOCAL_MODEL
    gguf = Path(cfg.get("gguf") or "")
    gguf_found = gguf.is_file()
    cli = local_model._find_llama_cli()
    cli_found = cli is not None
    enabled = bool(cfg.get("enabled"))
    ready = enabled and gguf_found and cli_found
    return {
        "local_model": {
            "enabled": enabled,
            "ready": ready,
            # enabled 但文件缺失时实际上会用规则压缩，这里给前端一个明确档位
            "effective_engine": "local-model" if ready else "rules",
            "gguf_found": gguf_found,
            "cli_found": cli_found,
            "gguf_path": str(gguf),
            "model_name": gguf.name if gguf_found else None,
        }
    }