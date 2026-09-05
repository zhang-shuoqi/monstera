"""规则压缩：不依赖任何本地模型，纯本地离线执行。

记忆中枢 V1 只"存"不"读"。这里负责把每一轮对话整理成可编辑的 Markdown 片段：
- 用户消息：过滤明显废话后原样保留；
- 模型回复：压缩成要点；
- 本地模型未启用/失败时，走本模块的规则压缩作为保底。
"""
from __future__ import annotations

# 视为"废话"的整句（常见口头禅/语气词），单独成句时整句丢弃
_FILLER = {
    "嗯", "嗯嗯", "啊", "哦", "好的", "好的好的", "好", "行", "收到", "哈哈", "哈哈哈",
    "呵呵", "ok", "okay", "好的吧", "可以", "没问题", "了解了", "点头", "👍", "知道了",
}
# 模型回复压缩：保留的 Markdown 行类型
_KEEP_PREFIX = ("#", "##", "###", "####", "-", "* ", "1. ", "2. ", ">", "```")

# 规则压缩输出上限（字符），超长截断并加省略
_MAX_ASSISTANT_CHARS = 1200
_MAX_USER_CHARS = 2000
# 普通正文每次最多保留的要点行数（避免整段照抄，只提炼首句）
_MAX_PROSE_LINES = 4
_MAX_PROSE_LINE_CHARS = 60  # 每条正文要点截取为"首句"左右的长度


def _is_filler_line(line: str) -> bool:
    """整句是否为明显废话。仅当一句话去掉空格后完全命中废话集合才判定。"""
    s = line.strip()
    if not s:
        return True
    return s in _FILLER or s.lower() in _FILLER


def filter_user(user_text: str) -> str:
    """用户消息：过滤明显废话后原样保留。"""
    text = (user_text or "").strip()
    if not text:
        return ""
    lines = text.splitlines()
    kept = [ln for ln in lines if not _is_filler_line(ln)]
    out = "\n".join(kept).strip()
    # 只剩一句话且是废话时返回空（表示本段被过滤，不写入记忆）
    if not out or (len(kept) == 1 and _is_filler_line(kept[0])):
        return ""
    if len(out) > _MAX_USER_CHARS:
        out = out[: _MAX_USER_CHARS].rstrip() + "\n…（过长已截断）"
    return out


def _compress_reply(text: str) -> str:
    """把模型回复提炼成要点（规则引擎）。

    规则：去空行与废话 → 标题/列表/代码块/引用等结构行完整保留 →
    普通正文只提炼首句（压成单行、截断、去重、限量），最终整体限长。
    目标是"提炼成要点的记忆"，而不是把整段对话照抄进记忆文档。
    """
    text = (text or "").strip()
    if not text:
        return "（无内容）"
    lines = text.splitlines()
    out = []       # 结构要点 + 已选正文要点（顺序输出）
    prose = []     # 普通正文候选：先暂存，用于去重与限量
    in_code = False
    for raw in lines:
        line = raw.rstrip()
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        if not s:
            continue                    # 收紧连续空行
        if s.startswith(_KEEP_PREFIX):  # 标题/列表/引用 等结构性要点，完整保留
            out.append(line)
            continue
        if _is_filler_line(s):
            continue                    # 去掉口水话与纯语气
        # 普通正文：压成单行要点（取首句），去重后暂存
        single = " ".join(s.split())
        if len(single) > _MAX_PROSE_LINE_CHARS:
            single = single[:_MAX_PROSE_LINE_CHARS].rstrip() + "…"
        if single not in prose:
            prose.append(single)
    # 普通正文限量收尾，排在结构要点之后
    out.extend(prose[:_MAX_PROSE_LINES])
    if len(prose) > _MAX_PROSE_LINES:
        out.append(f"…（正文尚有 {len(prose) - _MAX_PROSE_LINES} 处零散要点，详见原对话）")
    if not out:
        return text[:200]
    joined = "\n".join(out).strip()
    if len(joined) > _MAX_ASSISTANT_CHARS:
        joined = joined[:_MAX_ASSISTANT_CHARS].rstrip() + "\n…（回复较长，已压缩，详见原对话）"
    return joined


def build_entry(user_text: str, assistant_text: str) -> dict:
    """构造一轮对话的记忆条目（规则引擎）。

    返回 {"user": str, "assistant": str}：
    - user 为空字符串表示该轮用户消息被判定为废话、不写入；
    - assistant 一定非空（模型回复压缩后的要点）。
    """
    user = filter_user(user_text)
    assistant = _compress_reply(assistant_text)
    return {"user": user, "assistant": assistant}