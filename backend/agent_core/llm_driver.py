"""LLM 模型驱动（The Brain）· Phase 3（执行方案　Phase 3：脑）。

职责：
  - 上下文组装：每次循环把「用户原始目标 + 可用工具清单 + 已执行步骤摘要 + 上一步结果」
    组装成发给模型的 OpenAI messages。
  - Function Calling：调用 OpenAI 兼容端点（复用 services.openai_compat），解析模型返回的
    tool_calls → 转成内核统一的 ModelDecision（tool_call / final_answer）。
  - 结果回传：把工具执行结果（Observation）追加到上下文，进入下一轮。

关键约束（执行方案 Phase 3）：
  - 上下文不能无限膨胀：早期步骤详细结果压缩成摘要，只保留最近 3 步完整细节。
  - 大段文件内容不塞进上下文：存本地临时文件，上下文只放摘要和路径引用。
  - 模型返回格式错误：重试 3 次仍失败 → 抛 LLMModelError（由循环引擎标记任务 failed）。

Phase 3 与真实模型连接；Mock 模式（config.is_mock()）下走 openai_compat 的模拟 tool_calls，
便于无 Key 验收三条标准场景。
"""
from __future__ import annotations

import logging
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from agent_core.loop import ModelDecision, Observation
from agent_core.toolbox import ToolRegistry
from services.openai_compat import OpenAICompatClient

log = logging.getLogger("monstera.agent")

# 上下文压缩（移植 OpenHands Condenser + Tencent 上下載的思想）：
#   最近 N 步保留完整细节，更早的按字符预算压成逐行摘要，超预算时从最旧逐步丢弃。
RECENT_STEPS_FULL = 3
# 早期步骤摘要的字符预算（不再是固定份数，而是预算驱动：预算内尽量多保留中间步骤）
EARLY_HISTORY_CHARS_BUDGET = 6000
# 单条工具结果塞进上下文的字符上限；超出存本地临时文件，上下文只放摘要+引用
OBS_INLINE_MAX_CHARS = 800
# 修复 4：工具结果原始载荷 ≥2KB（2048 字符）→ 落盘本地文件，上下文只回传「摘要 + 引用」
INLINE_RAW_MAX_CHARS = 2048
# 历史经验（原子记忆）注入预算：总字符数封顶（Tencent recall cap）
MEMORY_INJECT_MAX_CHARS = 2000


class LLMModelError(RuntimeError):
    """模型交互失败（API 错误 / 格式非法超限）。循环引擎据此标记任务 failed。"""


class LLMModelDriver:
    """包装 OpenAICompatClient：把内核循环的 (objective, history) 转成模型调用。"""

    def __init__(
        self,
        client: OpenAICompatClient,
        api_key: str,
        model: str,
        toolbox: Optional[ToolRegistry] = None,
        temp_dir: Optional[Path] = None,
        recent_steps_full: int = RECENT_STEPS_FULL,
        early_history_chars_budget: int = EARLY_HISTORY_CHARS_BUDGET,
        obs_inline_max_chars: int = OBS_INLINE_MAX_CHARS,
        max_retries: int = 3,
        memory_recall: Optional[Any] = None,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model
        self._toolbox = toolbox
        self._temp_dir = Path(temp_dir) if temp_dir else None
        self._recent_steps_full = recent_steps_full
        self._early_history_chars_budget = early_history_chars_budget
        self._obs_inline_max_chars = obs_inline_max_chars
        self._max_retries = max_retries
        self._memory_recall = memory_recall      # callable(objective) -> List[str]（原子记忆注入）
        self._used_refs: List[str] = []
        self._prompt_tokens = 0
        self._completion_tokens = 0

    # ---------- 供循环引擎使用 ----------

    def decide(self, objective: str, history: List[Observation]) -> ModelDecision:
        """组装上下文 → Function Calling → 解析为 ModelDecision。"""
        context = self._build_messages(objective, history)
        resp = self._call_with_retry(context)
        return self._parse_response(resp, objective)

    def usage(self) -> Dict[str, int]:
        return {"prompt_tokens": self._prompt_tokens, "completion_tokens": self._completion_tokens}

    # ---------- 内部：上下文组装 ----------

    def _build_messages(self, objective: str, history: List[Observation]) -> List[dict]:
        messages: List[dict] = []
        # system：目标 + 相关历史经验（原子记忆，检索注入带预算封顶）+ 可用工具清单
        tools = self._toolbox.info_all() if self._toolbox else []
        tools_json = json.dumps(tools, ensure_ascii=False, indent=2)
        memory_block = self._memory_block(objective)
        system = (
            f"你是 Monstera 单用户本地 Agent。用户委托你完成一个目标。\n"
            f"【用户目标】{objective}\n"
            + (memory_block + "\n" if memory_block else "")
            + f"【可用工具】\n{tools_json}\n"
            "工作方式：需要操作本地文件时调用工具；工具结果会以 role=tool 消息返回你；"
            "收集到足够信息后直接给出最终答复（不要再调用工具）。"
            "如果上一步工具被拒绝或失败，说明原因并尝试换方案、跳过或结束。"
        )
        messages.append({"role": "system", "content": system})

        # 历史（预算驱动压缩，移植 Condenser 语义）：最近 N 步完整；更早的按字符预算逐行摘要
        recent = history[-self._recent_steps_full:]
        early = history[: len(history) - self._recent_steps_full] if len(history) > self._recent_steps_full else []
        if early:
            early_txt = self._compress_early(early)
            messages.append({"role": "user", "content": "【早期步骤摘要】" + early_txt + "（详情已压缩，如需要可再次调用工具获取细节）"})
        for obs in recent:
            if obs.success:
                body, ref = self._ref_or_inline(obs)
                if ref:
                    self._used_refs.append(ref)
                messages.append({"role": "user", "content": f"【第{obs.step}步工具结果 {obs.tool_name}】{body}"})
            else:
                messages.append({"role": "user", "content": f"【第{obs.step}步 {obs.tool_name} 失败】{obs.summary}"})
        return messages

    def _compress_early(self, early: List[Observation]) -> str:
        """把早期步骤压成紧凑行（预算驱动：按字符预算保留最近的早期步骤，更旧的丢弃）。"""
        lines: List[str] = []
        total = 0
        # 从最新往最旧累计（保留接近当前步骤的中间过程，丢掉最久远的）
        for o in reversed(early):
            detail = o.summary.replace("\n", " ")
            line = f"第{o.step}步 {o.tool_name}: {'成功' if o.success else '失败'} {detail[:120]}"
            if total + len(line) > self._early_history_chars_budget:
                break
            lines.append(line)
            total += len(line)
            if len(lines) >= 40:
                break
        lines.reverse()
        dropped = len(early) - len(lines)
        head = "（已省略 %d 个更早步骤）" % dropped if dropped > 0 else ""
        return head + "；".join(lines) if lines else head + "无"

    def _memory_block(self, objective: str) -> str:
        """原子记忆注入：按目标检索历史经验，总字符数预算封顶；无可召回时不注入。"""
        if self._memory_recall is None:
            return ""
        try:
            rows = self._memory_recall(objective) or []
        except Exception:
            return ""    # 记忆检索失败不阻塞主流程
        if not rows:
            return ""
        block: List[str] = []
        total = 0
        for r in rows:
            text = str(r)
            if total + len(text) > MEMORY_INJECT_MAX_CHARS:
                break
            block.append(text)
            total += len(text)
        if not block:
            return ""
        return "【历史经验（跨任务，仅参考勿盲从）】\n" + "\n".join(block)

    def _ref_or_inline(self, obs: Observation) -> tuple[str, Optional[str]]:
        """上下文预算：结果内联 / 落盘引用（修复 4 定稿校验）。

        - 原始载荷（raw）< 2KB：直接内联摘要（summary 本身 ≤ 800 字符截断）。
        - 原始载荷 ≥ 2KB：写本地临时文件，上下文只回传「摘要 + 路径引用」，
          模型需要细节时可再次调用工具读取，避免大结果撑爆上下文。
        - raw 缺失（如用户拒绝观察）：内联 summary。
        """
        text = str(obs.summary or "")
        raw = obs.raw
        if raw is None or raw == "":
            return text[: self._obs_inline_max_chars], None
        try:
            raw_text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
            if not isinstance(raw_text, str):
                raw_text = str(raw_text)
        except (TypeError, ValueError):
            raw_text = str(raw)
        if len(raw_text) < INLINE_RAW_MAX_CHARS:
            return text[: self._obs_inline_max_chars] or raw_text[: self._obs_inline_max_chars], None
        if self._temp_dir is None:
            return text[: self._obs_inline_max_chars] + "…（已截断）", None
        try:
            self._temp_dir.mkdir(parents=True, exist_ok=True)
            name = f"step{obs.step}_{obs.tool_name}.txt".replace("/", "_").replace("\\", "_")
            path = self._temp_dir / name
            path.write_text(raw_text, encoding="utf-8")
            return f"结果较大，已存本地文件：{path}（摘要在上一段）", str(path)
        except OSError as exc:
            log.warning("引用文件写入失败：%s", exc)
            return text[: self._obs_inline_max_chars] + "…（已截断）", None

    # ---------- 内部：调用与解析 ----------

    def _call_with_retry(self, messages: List[dict]) -> dict:
        tools_payload = [self._tool_schema(t) for t in (self._toolbox.info_all() if self._toolbox else [])]
        last_err = ""
        for attempt in range(1, self._max_retries + 1):
            t0 = time.perf_counter()
            resp = self._client.chat_completion(
                self._api_key, self._model, messages,
                tools=tools_payload or None,
            )
            latency = int((time.perf_counter() - t0) * 1000)
            if not resp.get("success"):
                last_err = resp.get("error", "调用失败")
                # 网络/Key 错误：重试 3 次后放弃（Phase 5 硬化里再做更细的区分）
                log.warning("模型调用失败 attempt=%d：%s", attempt, last_err)
                continue
            self._prompt_tokens += int(resp.get("prompt_tokens", 0))
            self._completion_tokens += int(resp.get("completion_tokens", 0))
            del latency
            return resp
        raise LLMModelError(f"模型调用连续失败 {self._max_retries} 次：{last_err}")

    @staticmethod
    def _tool_schema(tool: Dict[str, Any]) -> dict:
        """把注册表工具元信息转成 OpenAI tools 数组的元素。"""
        return {
            "type": "function",
            "function": {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
            },
        }

    def _parse_response(self, resp: dict, objective: str) -> ModelDecision:
        """解析模型返回：有 tool_calls → tool_call 决策；否则视为最终答复。"""
        tool_calls = resp.get("tool_calls") or []
        content = resp.get("content") or ""

        if not tool_calls:
            answer = (content or "").strip()
            if not answer:
                raise LLMModelError("模型返回既无工具调用也无内容")
            return ModelDecision(kind="final_answer", content=answer[:20000])

        # 只处理第一个 tool_call；arguments 是 JSON 字符串
        tc = tool_calls[0]
        fn = (tc.get("function") or {}) or {}
        name = fn.get("name") or ""
        try:
            args = json.loads(fn.get("arguments") or "{}")
            if not isinstance(args, dict):
                args = {}
        except (TypeError, ValueError):
            args = {}
        if not name:
            raise LLMModelError("模型返回的 tool_call 缺少函数名")
        return ModelDecision(kind="tool_call", tool_name=name, content=args)