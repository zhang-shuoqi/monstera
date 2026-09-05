"""记忆中枢 API：查看 / 编辑 / 打开本地记忆文档。"""
from fastapi import APIRouter, HTTPException

from services import memory as memory_svc

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("")
def list_memory():
    """列出全部记忆文档（含会话标题、状态、引擎、更新时间）。"""
    return {"docs": memory_svc.list_docs()}


@router.get("/status")
def memory_status():
    """本地整理模型就绪状态（前端展示用）。
    enabled 但文件未就绪时，实际会用规则压缩降级（effective_engine=rules）。"""
    return memory_svc.status()


@router.get("/{doc_id}")
def get_memory(doc_id: int):
    """读取某份记忆文档的完整内容（用于查看 / 编辑）。"""
    doc = memory_svc.get_doc(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="记忆文档不存在")
    return doc


@router.put("/{doc_id}")
def save_memory(doc_id: int, body: dict):
    """用户手动编辑保存记忆文档。body: {content, title?}"""
    content = body.get("content")
    if not isinstance(content, str):
        raise HTTPException(status_code=400, detail="content 必须为字符串")
    ok = memory_svc.update_doc(doc_id, content, body.get("title"))
    if not ok:
        raise HTTPException(status_code=404, detail="记忆文档不存在")
    return {"ok": True, "path": memory_svc.get_doc(doc_id)["path"]}


@router.post("/{doc_id}/open")
def open_memory(doc_id: int):
    """用系统默认程序在本地打开记忆文档（Windows / macOS）。"""
    ok = memory_svc.open_doc(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆文档不存在")
    return {"ok": True}


@router.delete("/{doc_id}")
def delete_memory(doc_id: int):
    """删除记忆文档：本地 .md 文件与数据库记录一并移除。
    前端必须先弹二次确认再调用本接口。
    """
    ok = memory_svc.delete_doc(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆文档不存在")
    return {"ok": True}