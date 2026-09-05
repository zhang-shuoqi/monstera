"""对话持久化路由：列表 / 新建 / 重命名 / 置顶 / 删除 / 消息记录"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Conversation, ConversationMemory, Message, MemoryDoc
from services import memory as memory_svc

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _conv_dict(c: Conversation) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "pinned": bool(c.pinned),
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("")
def list_conversations(db: Session = Depends(get_db)):
    """按 置顶优先 > 最近更新 排序"""
    convs = (
        db.query(Conversation)
        .order_by(Conversation.pinned.desc(), Conversation.updated_at.desc(), Conversation.id.desc())
        .all()
    )
    return {"conversations": [_conv_dict(c) for c in convs]}


@router.post("")
def create_conversation(body: dict, db: Session = Depends(get_db)):
    """新建对话，title 可省略（默认“新对话”，首条消息后自动命名）。

    可选 memory_doc_id：继承某份旧记忆文档 —— 这个新对话后续记入该旧文档；
    不传则新建对话，首次消息后自动建立一份空白记忆文档。
    返回 inherited_memory_doc_id：表示"新对话会写进旧文档"（非空）或"写进新文档"（null）。
    """
    payload = body or {}
    title = payload.get("title") or "新对话"
    memory_doc_id = payload.get("memory_doc_id")
    conv = Conversation(title=title)
    db.add(conv)
    db.flush()
    if memory_doc_id:
        doc = db.get(MemoryDoc, memory_doc_id)
        if not doc:
            db.rollback()
            raise HTTPException(status_code=404, detail="要继承的记忆文档不存在")
        db.add(ConversationMemory(conversation_id=conv.id, memory_doc_id=doc.id))
    db.commit()
    db.refresh(conv)
    return {**_conv_dict(conv), "inherited_memory_doc_id": memory_doc_id if memory_doc_id else None}


@router.put("/{conversation_id}")
def update_conversation(conversation_id: int, body: dict, db: Session = Depends(get_db)):
    """重命名 / 置顶 / 取消置顶。
    注意：不更新 updated_at —— 排序时间只反映"最近一次对话活动"，
    重命名/置顶不应把老对话顶到列表最前。"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    if "title" in body:
        title = str(body.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="标题不能为空")
        conv.title = title
    if "pinned" in body:
        conv.pinned = bool(body.get("pinned"))
    db.commit()
    return _conv_dict(conv)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """删除对话及其全部消息。

    先删除该对话"自动生成"的记忆文档（MemoryDoc.conversation_id == 本对话），
    并同步移除本地 .md 文件——否则删对话时外键约束失败（MemoryDoc 的
    conversation_id 仍指向该对话）。复用 memory_svc.delete_doc，避免复制删除逻辑。
    「继承他人旧文档」的对话没有自己 conversation_id 的 MemoryDoc，
    该分支不命中，只删除它到旧文档的映射（下方 ConversationMemory），不会误删旧文档。
    """
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    # 1) 该对话自动生成的记忆文档：连带删除本地文件与库记录（解除 FK）
    for doc in db.query(MemoryDoc).filter(MemoryDoc.conversation_id == conversation_id).all():
        memory_svc.delete_doc(doc.id)
    # 2) 对话自身数据
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.query(ConversationMemory).filter(ConversationMemory.conversation_id == conversation_id).delete()
    db.delete(conv)
    db.commit()
    return {"success": True}


@router.delete("/{conversation_id}/messages/{message_id}")
def delete_message(conversation_id: int, message_id: int, db: Session = Depends(get_db)):
    """删除对话内的单条消息（编辑/清理时使用）"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    m = db.get(Message, message_id)
    if not m or m.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="消息不存在")
    db.delete(m)
    db.commit()
    return {"success": True}


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    """按时间正序返回对话内全部消息"""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .all()
    )
    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "images": json.loads(m.images) if m.images else [],
                "model_id": m.model_id,
                "cost": m.cost,
                "latency_ms": m.latency_ms,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ]
    }
