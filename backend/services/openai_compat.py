"""统一 OpenAI 兼容推送客户端（面向任意厂商，数据驱动，无 per-vendor 代码）

每个客户端仅由 providers 表里的一行构造：base_url（必填）+ balance_url（可选）。
只要该厂商端点兼容 OpenAI 的 /models 与 /chat/completions（OpenAI 兼容格式），
即可接入，无需为每家改动代码。所有请求本地直连，不经过任何云端代理。

Mock 模式（config.is_mock()）下全部返回假数据，绝不发起真实网络请求，
假数据规则沿用历史 DeepSeek 测试约定（sk- 前缀、403/banned/revoked/neg 关键词）。
"""
import json
import random
import time
from typing import Iterator, List, Optional

import httpx

import config


def _auth(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def _content_text(content) -> str:
    """从消息 content 提取纯文本：兼容字符串与多模态数组（text / image_url）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict):
                if p.get("type") == "text":
                    parts.append(p.get("text", ""))
                elif p.get("type") == "image_url":
                    parts.append("📷")
        return "\n".join(x for x in parts if x)
    return str(content)


def _count_images(content) -> int:
    """统计一条消息 content 中的图片数（多模态数组）。"""
    if isinstance(content, dict):
        return 1 if content.get("type") == "image_url" else 0
    if isinstance(content, list):
        return sum(1 for p in content if isinstance(p, dict) and p.get("type") == "image_url")
    return 0


def _desktop_path() -> str:
    """用户桌面路径（Agent mock 默认操作目录，Windows 优先）。"""
    import os
    return os.path.join(os.path.expanduser("~"), "Desktop")


# ==================== Mock 假数据（测试用） ====================
# 按 provider 区分假模型，让每个厂商的下拉都能看到自己的模型（真实模式由 /models 同步）。
_MOCK_MODELS_BY_PROVIDER = {
    "deepseek": [
        {"id": "deepseek-v4-flash", "display_name": "DeepSeek-V4-Flash",
         "description": "轻量快速，适合日常对话和简单任务", "context_window": 1000000, "vision": False},
        {"id": "deepseek-v4-pro", "display_name": "DeepSeek-V4-Pro",
         "description": "能力更强，适合复杂推理和代码", "context_window": 1000000, "vision": False},
    ],
    "kimi": [
        {"id": "kimi-k2.6", "display_name": "Kimi-K2.6",
         "description": "最新旗舰，长程代码编写与 Agent 能力更强", "context_window": 262144, "vision": True},
        {"id": "kimi-k2.5", "display_name": "Kimi-K2.5",
         "description": "支持视觉与文本、思考/非思考模式", "context_window": 262144, "vision": True},
    ],
}
# 未收录厂商的回退假模型
_DEFAULT_MOCK_MODELS = [
    {"id": "model-a", "display_name": "Model-A",
     "description": "Mock 通用模型（该厂商未被 Mock 收录）", "context_window": 0, "vision": False},
]

# 模拟"粘贴时有效、之后被平台删除"的 Key（含 revoked）：首次验证通过，此后失效
_REVOKED_KEYS = set()


class OpenAICompatClient:
    """按单个厂商配置构造的 OpenAI 兼容客户端"""

    def __init__(self, base_url: str, balance_url: Optional[str] = None,
                 name: str = "", provider_key: str = ""):
        self.base_url = (base_url or "").rstrip("/")
        self.balance_url = (balance_url or "").rstrip("/") if balance_url else None
        self.name = name
        self.provider_key = (provider_key or name or "").lower()  # 用于 Mock 区分假模型

    # ---------------- Mock（进程内假数据） ----------------

    def _mock_models(self) -> list:
        """返回当前 provider 的假模型列表（未被收录则退回通用假模型）"""
        models = _MOCK_MODELS_BY_PROVIDER.get(self.provider_key) or _DEFAULT_MOCK_MODELS
        return [dict(m) for m in models]

    def _mock_validate(self, api_key: str) -> dict:
        k = api_key.strip()
        if not k.startswith("sk-") or len(k) < 8:
            return {"valid": False, "error": "API Key 无效，请检查是否复制完整（Mock 假数据）"}
        if "403" in k or "banned" in k.lower():
            return {"valid": False, "error": "请前往厂商开放平台完成实名认证（Mock 假数据）"}
        if "revoked" in k.lower():
            if k in _REVOKED_KEYS:  # 已用过一次：模拟此后被平台删除/吊销
                return {"valid": False,
                        "error": "API Key 已被平台删除或吊销（Mock 假数据），请重新创建并粘贴"}
            _REVOKED_KEYS.add(k)
            return {"valid": True, "models": self._mock_models()}
        time.sleep(random.uniform(0.1, 0.3))  # 模拟网络延迟，使 latency_ms 更真实
        return {"valid": True, "models": self._mock_models()}

    def _mock_balance(self, api_key: str) -> float:
        seed = sum(api_key.encode("utf-8"))
        if "neg" in api_key.lower() or "debt" in api_key.lower():
            return -round(1 + seed % 20 + (seed % 100) / 100, 2)  # 负余额（测试欠费警示）
        return round(5 + seed % 45 + (seed % 100) / 100, 2)

    def _mock_chat(self, api_key: str, model: str, messages: List[dict],
                   tools: Optional[List[dict]] = None) -> dict:
        if "banned" in api_key.lower() or "fail" in api_key.lower():
            return {"success": False, "error": "API Key 已被平台禁用（Mock 假数据），请更换 Key"}
        time.sleep(random.uniform(0.3, 0.9))  # 模拟网络与推理延迟
        last = _content_text(messages[-1].get("content", "")) if messages else ""
        img_n = _count_images(messages[-1].get("content", "")) if messages else 0
        history = max(len(messages) - 1, 0)

        # —— Function Calling 模拟：按目标关键词决定是否调工具 ——
        if tools:
            tool_call = self._mock_agent_tool_call(tools, last, history)
            if tool_call is not None:
                return {
                    "success": True,
                    "content": "",
                    "tool_calls": [tool_call],
                    "prompt_tokens": 150 + len(last),
                    "completion_tokens": 40,
                    "cached_tokens": 0,
                }

        content = (
            f"[Mock 模拟回复｜假数据，未调用真实 API]\n"
            f"收到你的消息：「{last[:60]}」\n"
            + (f"本次检测到 {img_n} 张图片（多模态 content 数组已正确透传）。\n" if img_n else "")
            + (f"当前对话已携带 {history} 条历史消息作为上下文，我记得之前说过什么。"
               if history else "这是本对话的第一条消息（新对话，无历史上下文）。")
            + f"\n（使用模型：{model}）"
        )
        prompt_chars = sum(len(_content_text(m.get("content", ""))) for m in messages)
        cached = int(prompt_chars * 0.3) if history else 0  # 有历史时模拟部分缓存命中
        return {
            "success": True,
            "content": content,
            "prompt_tokens": int(prompt_chars * 1.2) + 12,
            "completion_tokens": int(len(content) * 1.3) + 8,
            "cached_tokens": cached,
        }

    def _mock_agent_tool_call(self, tools: List[dict], last: str, history: int):
        """Mock 阶段模拟 Agent 模型决策：识别最后一次工具结果 / 用户目标关键词。

        - 上一条是工具结果（消息含「第N步工具结果」标记）→ 已拿到结果，直接答复（不再调工具）
        - 首轮：只取「【用户目标】…」段做意图判断（避免工具清单 JSON 里的工具名字符串干扰）
          - 目标含「创建/写入/写」 → file_write（验收场景 2）
          - 目标含「读取/读」     → file_read（验收场景 3）
          - 目标含「列出/桌面」   → list_dir（验收场景 1）
        - 否则直接答复
        返回 OpenAI tool_call 结构；不匹配时返回 None（表示直接回答）。
        """
        if tools is None:
            return None
        if "第" in last and "步工具结果" in last:
            return None  # 工具结果已就绪 → 模型直接给最终答复
        if "第" in last and "步" in last and "失败" in last:
            return None  # 上一步失败/被拒绝的观察 → 直接给最终答复（换方案交给真实模型）

        # 只取【用户目标】行（不取完整 system，以免工具名/JSON 干扰意图识别）
        marker = "【用户目标】"
        if marker not in last:
            return None   # 后续轮由观察驱动，不参与意图匹配
        target = last.split(marker, 1)[1]
        if "\n" in target:
            target = target.split("\n", 1)[0] or target
        lower = target.lower()
        if "创建" in lower or "写入" in lower or "写" in lower:
            return self._mk_tool_call(tools, "file_write", {"path": f"{_desktop_path()}\\test.txt", "content": "hello"})
        if "读取" in lower or "读" in lower or "file_read" in lower:  # noqa: SIM114
            return self._mk_tool_call(tools, "file_read", {"path": r"C:\Windows\system32\drivers\etc\hosts"})
        if "列出" in lower or "list_dir" in lower or "桌面" in lower:
            return self._mk_tool_call(tools, "list_dir", {"path": _desktop_path()})
        return None

    @staticmethod
    def _mk_tool_call(tools: List[dict], name: str, args: dict) -> dict:
        """构造 OpenAI tool_call 结构（arguments 为 JSON 字符串）。"""
        return {
            "id": f"call_{random.randint(10_000, 99_999)}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
        }

    def _mock_chat_stream(self, api_key: str, model: str, messages: List[dict]) -> Iterator[dict]:
        r = self._mock_chat(api_key.strip(), model, messages)
        if not r.get("success"):
            yield {"type": "error", "error": r.get("error", "调用失败")}
            return
        content = r["content"]
        for i in range(0, len(content), 8):  # 模拟打字机效果
            yield {"type": "delta", "content": content[i:i + 8]}
            time.sleep(0.025)
        yield {"type": "usage",
               "prompt_tokens": r["prompt_tokens"],
               "completion_tokens": r["completion_tokens"],
               "cached_tokens": r["cached_tokens"]}

    # ---------------- 对外开放接口 ----------------

    def validate_api_key(self, api_key: str) -> dict:
        """验证 API Key：GET {base_url}/models

        兼容 OpenAI 标准 {data:[...]} 与个别厂商的 {models:[...]} 两种返回。
        成功：{"valid": True, "models": [...]}
        失败：{"valid": False, "error": "中文提示"}
        """
        if config.is_mock():
            return self._mock_validate(api_key.strip())
        try:
            r = httpx.get(
                f"{self.base_url}/models", headers=_auth(api_key), timeout=config.HTTP_TIMEOUT
            )
            if r.status_code == 401:
                return {"valid": False, "error": "API Key 无效，请检查是否复制完整"}
            if r.status_code == 403:
                return {"valid": False, "error": "请前往该厂商开放平台完成实名认证"}
            if r.status_code != 200:
                return {"valid": False, "error": f"验证失败（HTTP {r.status_code}），请稍后重试"}
            data = r.json()
            models = data.get("data") or data.get("models") or []
            return {"valid": True, "models": models}
        except httpx.TimeoutException:
            return {"valid": False, "error": f"连接 {self.name or '厂商'} 超时，请检查网络后重试"}
        except Exception as e:  # noqa: BLE001
            return {"valid": False, "error": f"验证请求异常：{e}"}

    def get_balance(self, api_key: str) -> Optional[float]:
        """获取余额：GET {balance_url}；未配置 balance_url 时直接返回 None"""
        if config.is_mock():
            return self._mock_balance(api_key.strip())
        if not self.balance_url:
            return None
        try:
            r = httpx.get(self.balance_url, headers=_auth(api_key), timeout=config.HTTP_TIMEOUT)
            if r.status_code != 200:
                return None
            return self._parse_balance(r.json())
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _parse_balance(data: dict) -> Optional[float]:
        """尽可能兼容常见余额字段：DeepSeek balance_infos[].total_balance、
        Kimi data.available_balance、其它 balance/credits。纯格式兼容，无 per-vendor 分支。"""
        infos = data.get("balance_infos") or []
        total, hit = 0.0, False
        for info in infos:
            b = info.get("total_balance")
            if b is not None:
                try:
                    total += float(b)
                    hit = True
                except (TypeError, ValueError):
                    continue
        if hit:
            return round(total, 2)
        # Kimi 等：{ "code":0, "data": { "available_balance": 49.58, ... } }
        if isinstance(data.get("data"), dict):
            d = data["data"]
            for k in ("available_balance", "balance", "total_balance", "credits"):
                v = d.get(k)
                if v is not None:
                    try:
                        return round(float(v), 2)
                    except (TypeError, ValueError):
                        continue
        for k in ("available_balance", "balance", "credits", "total_credit", "available_credit"):
            if k in data and data[k] is not None:
                try:
                    return round(float(data[k]), 2)
                except (TypeError, ValueError):
                    continue
        return None

    def chat_completion(self, api_key: str, model: str, messages: List[dict],
                        max_tokens: Optional[int] = None,
                        tools: Optional[List[dict]] = None,
                        tool_choice: Optional[dict] = None) -> dict:
        """对话补全：POST {base_url}/chat/completions（OpenAI 兼容，非流式）

        支持 Function Calling：传入 tools（OpenAI tools 数组）时，模型可在回复中
        携带 tool_calls；调用方据此执行工具并把结果以 role=tool 消息回传。
        成功：{"success": True, "content", "tool_calls"?,
               "prompt_tokens", "completion_tokens", "cached_tokens"}
        失败：{"success": False, "error": "..."}
        """
        if config.is_mock():
            return self._mock_chat(api_key.strip(), model, messages, tools=tools)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens or config.MAX_TOKENS,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions", json=payload,
                headers=_auth(api_key), timeout=config.HTTP_TIMEOUT,
            )
            if r.status_code == 401:
                return {"success": False, "error": "API Key 无效"}
            if r.status_code == 403:
                return {"success": False, "error": "请前往该厂商开放平台完成实名认证"}
            if r.status_code == 402:
                return {"success": False, "error": "账户余额不足，请前往该厂商平台充值"}
            if r.status_code != 200:
                return {"success": False, "error": f"厂商返回错误（HTTP {r.status_code}）"}
            data = r.json()
            usage = data.get("usage") or {}
            details = usage.get("prompt_tokens_details") or {}
            choices = data.get("choices") or []
            if not choices:
                return {"success": False, "error": "厂商返回内容为空"}
            msg = choices[0].get("message", {}) or {}
            tool_calls = msg.get("tool_calls") or []
            return {
                "success": True,
                "content": msg.get("content", "") or "",
                "tool_calls": tool_calls or None,
                "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
                "completion_tokens": usage.get("completion_tokens", 0) or 0,
                "cached_tokens": details.get("cached_tokens", 0) or 0,
            }
        except httpx.TimeoutException:
            return {"success": False, "error": f"{self.name or '厂商'} 请求超时"}
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": f"请求异常：{e}"}

    # ---------------- 流式对话 ----------------

    def _sse_error(self, msg: str) -> dict:
        return {"type": "error", "error": msg}

    def _usage_frame(self, usage: dict) -> dict:
        details = usage.get("prompt_tokens_details") or {}
        return {
            "type": "usage",
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "cached_tokens": int(details.get("cached_tokens", 0) or 0),
        }

    def chat_completion_stream(self, api_key: str, model: str, messages: List[dict],
                               max_tokens: Optional[int] = None) -> Iterator[dict]:
        """流式对话：POST {base_url}/chat/completions（stream=true）

        生成器依次 yield：
          {"type": "delta", "content": str}                       增量文本
          {"type": "usage", "prompt_tokens"/"completion_tokens"/"cached_tokens"}  最终用量
          {"type": "error", "error": str}                         失败（终止信号）
        """
        if config.is_mock():
            yield from self._mock_chat_stream(api_key, model, messages)
            return

        base_payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or config.MAX_TOKENS,
        }
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

        def _drain(stream_resp):
            """逐行解析 SSE：yield 增量文本，返回最终 usage"""
            usage = None
            for line in stream_resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    j = json.loads(data)
                except ValueError:
                    continue
                if j.get("usage"):
                    usage = j["usage"]
                for ch in j.get("choices") or []:
                    piece = (ch.get("delta") or {}).get("content")
                    if piece:
                        yield {"type": "delta", "content": piece}
            return usage

        try:
            with httpx.Client(timeout=timeout) as client:
                url = f"{self.base_url}/chat/completions"
                # 优先带 stream_options.include_usage（末帧返回用量）；
                # 服务端不支持（400）时降级为不带
                payload = dict(base_payload, stream=True, stream_options={"include_usage": True})
                usage = None
                with client.stream("POST", url, json=payload, headers=_auth(api_key)) as resp:
                    if resp.status_code == 400:
                        resp.read()  # 读取错误体以便复用连接
                        payload = dict(base_payload, stream=True)
                        with client.stream("POST", url, json=payload, headers=_auth(api_key)) as resp2:
                            if resp2.status_code != 200:
                                yield self._sse_error(f"厂商返回错误（HTTP {resp2.status_code}）")
                                return
                            usage = yield from _drain(resp2)
                    else:
                        if resp.status_code == 401:
                            yield self._sse_error("API Key 无效"); return
                        if resp.status_code == 403:
                            yield self._sse_error("请前往该厂商开放平台完成实名认证"); return
                        if resp.status_code == 402:
                            yield self._sse_error("账户余额不足，请前往该厂商平台充值"); return
                        if resp.status_code != 200:
                            yield self._sse_error(f"厂商返回错误（HTTP {resp.status_code}）"); return
                        usage = yield from _drain(resp)

                if usage is None:
                    yield self._sse_error("接口未返回用量信息，无法计费（已中止）"); return
                yield self._usage_frame(usage)
        except httpx.TimeoutException:
            yield self._sse_error(f"{self.name or '厂商'} 请求超时")
        except Exception as e:  # noqa: BLE001
            yield self._sse_error(f"请求异常：{e}")