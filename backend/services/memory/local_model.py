"""本地整理模型封装（llama.cpp + Qwen2.5-1.5B-Instruct 量化版）。

本地运行，不联网、不调用户 API、不产生任何费用。用于把模型回复压缩成要点；
未启用 / 二进制缺失 / 运行失败时返回 None，由调用方降级为纯规则压缩。

只需把符合 config.LOCAL_MODEL 命名（llama-cli.exe + qwen2.5-1.5b-instruct-q4_k_m.gguf）
的产物放入 backend/models/，并设 MONSTERA_LOCAL_MODEL=1 即启用；模型文件不随仓库提交。
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from pathlib import Path

import config

log = logging.getLogger("monstera.local_model")

# 全局互斥锁：串行化本地模型推理，保证任何时刻最多只有一个 llama-cli 进程在跑。
# 聊天是连续触发的，若不串行，多条消息会并发 spawn 多个实例、同时冷加载 1.1GB 模型，
# 把 CPU/内存/磁盘一起榨干（表现为整机连鼠标都卡）。串行后资源峰值被压到最低。
_INFER_LOCK = threading.Lock()

# Windows 下不弹出黑窗；非 Windows 平台不存在该常量，退回 0
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# 让 llama-cli 独占一个进程组（新进程组组长），从而「脱离父进程的控制台进程组」：
# 这样外部/沙盒看门狗向终端进程组发送 SIGINT（Ctrl+C，父进程会收到退出码 130）时，
# 子进程不会跟着被中断，冷加载不再被误杀，也就不必每次都靠重试兜底。
_NO_CONSOLE_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x0200)
# 综合 flags：不弹黑窗 + 独创新进程组（脱离父控制台信号）
_SUBPROC_FLAGS = _NO_WINDOW | _NO_CONSOLE_GROUP

_SYSTEM_PROMPT = (
    "你是记忆整理助手。请把下面【模型回复】压缩成一条条的要点：\n"
    "1) 每条单独一行，以“- ”开头；\n"
    "2) 只保留关键信息、数据、结论与行动项，删掉客套话和重复；\n"
    "3) 每条不超过 40 字，最多输出 6 条；\n"
    "4) 不要标题：禁止输出任何以 # 开头的行，也不要照抄原回复里的章节标题；\n"
    "5) 不要开场白，不要“好的/以下是/希望有帮助”等废话，不要任何解释，直接给要点。"
)


def _is_banner_open(marker: str) -> bool:
    """判断一行是否来自 llama-cli 的开场横幅/交互回显（而非模型生成的内容）。

    这些行属于启动元数据或交互脚手架，绝不写进记忆：ASCII logo、build/model/ftype/
    modalities 行、"available commands:" 及其 /exit /regen 等提示、Promise 交互行 '>' 等。
    """
    s = marker.strip().lower()
    if not s:
        return False
    if s.startswith("loading model") or s.startswith("llama.cpp"):
        return True
    if "built with" in s or " /build " in s or s.startswith("build"):
        return True
    if s.startswith(("model", "ftype", "modalities", "main_gpu", "n_params",
                     "available commands", "/exit", "/regen", "/clear", "/read", "/glob")):
        return True
    if "▄" in s or "█" in s or "▀" in s:   # llama.club ASCII 字符画
        return True
    return False


def _is_reply_line(raw: str) -> bool:
    """判断一行是否是模型真正产出的"要点/结构行"（- */数字./#/代码）。
    显式排除 '>' 开头的行——那是 llama-cli 的交互提示符回显，不是内容。"""
    s = raw.strip()
    if not s:
        return False
    if s.startswith(("- ", "* ", "#", "```")):
        return True
    return len(s) > 1 and s[0].isdigit() and s[1] in ".．、"


def _clean_generation(out: str, prompt: str) -> str | None:
    """从 llama-cli 的 stdout 里剥离启动横幅 / prompt 回显 / 尾部统计行，只留真正的生成结果。

    llama-cli 默认会把 ASCII logo、build 信息、模型信息、完整 prompt 回显、以及结尾的
    "[ Prompt: ... t/s | Generation: ... t/s ]" 统计都印到 stdout（--simple-io 也不能完全去掉）。
    这些都不是模型生成的内容，必须剥掉，否则会被当成记忆写进文档。
    两级策略：先按 prompt 边界切割（若命中则干净）；若仍有横幅/'>' 交互回显残留，
    则兜底退化为"只保留要点行"（- /*/数字./#/代码），横幅与回显天然不含这些行首。
    """
    text = (out or "").strip()
    if not text:
        return None
    idx = text.rfind(prompt)
    if idx >= 0:
        text = text[idx + len(prompt):]

    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("[") and " t/s" in s and "|" in s:   # [ Prompt: ... | Generation: ... ]
            continue
        if s in (">", "Exiting...", "Done."):
            continue
        lines.append(ln)
    result = "\n".join(lines).strip()
    if not result:
        return None

    # 兜底：仍混有横幅或开头的 '>' 回显时，退化为"只取要点行"，保证记忆干净。
    needs_rebuild = result.lstrip().startswith(">") or any(
        _is_banner_open(ln) for ln in result.splitlines()
    )
    if needs_rebuild:
        keep = [ln.rstrip() for ln in text.splitlines() if _is_reply_line(ln)]
        result = "\n".join(keep).strip()
    return result or None


def _find_llama_cli() -> Path | None:
    """定位 llama-cli 可执行文件：优先 config.LOCAL_MODEL["llama_cli"]，否则在 PATH 中查找。"""
    c = Path(config.LOCAL_MODEL["llama_cli"])
    if c.is_file():
        return c
    for name in ("llama-cli", "llama-cli.exe", "main", "main.exe"):
        hit = shutil.which(name)
        if hit:
            return Path(hit)
    return None


def summarize(reply_text: str) -> str | None:
    """对回复做本地模型压缩；任何失败返回 None（调用方降级）。

    沙盒/受限环境下，长时间运行的本地二进制子进程可能被看门狗以 SIGINT(130)
    中断（首次还可能因模型冷加载慢而超时）。模型文件首次加载后会被 OS 缓存，
    重试时加载更快、成功率更高，因此这里最多重试 3 次；全部失败才返回 None，
    由调用方降级为规则压缩。整个流程严格受 timeout 约束，线程绝不卡死。
    """
    cfg = config.LOCAL_MODEL
    if not cfg.get("enabled"):
        return None
    gguf = Path(cfg.get("gguf") or "")
    if not gguf.is_file():
        log.warning("本地整理模型未就绪（找不到 %s），降级规则压缩", gguf.name)
        return None
    cli = _find_llama_cli()
    if cli is None:
        log.warning("本地整理模型未就绪（找不到 llama-cli），降级规则压缩")
        return None

    text = (reply_text or "").strip()
    if not text:
        return None
    if len(text) > 4000:  # 超长先按规则截断，避免本地模型上下文过载
        text = text[:4000] + "\n…"
    prompt = f"{_SYSTEM_PROMPT}\n\n【模型回复】\n{text}"

    last_err = "未执行"
    # 全程持锁：串行执行，避免并发 spawn 多个模型进程造成整机资源风暴。
    with _INFER_LOCK:
        for attempt in range(1, 4):
            cleaned, code, err = _run_once(cli, gguf, prompt, cfg)
            if cleaned is not None:
                return cleaned
            # 记录失败；重试直到次数耗尽
            if code is None:
                last_err = f"启动失败：{err}"
            elif code != 0:
                last_err = f"退出码 {code}：{(err or '')[:120]}"
            else:
                last_err = "输出为空或无法提取"
            log.warning("本地整理模型第 %s 次尝试失败（%s），%s",
                        attempt, last_err, "将重试" if attempt < 3 else "降级规则压缩")

    return None


def _run_once(cli: Path, gguf: Path, prompt: str, cfg: dict):
    """执行一次 llama-cli 推理。返回 (清洗结果, 退出码, stderr尾部)。
    进程被看门狗 SIGINT 中断时退出码为 130 或非 0，属可重试情况。"""
    # 用 Popen + communicate(timeout) 硬性限时，绝不依赖 subprocess.run 内部
    # 的"超时后再无超时的第二次 communicate()"。后者一旦子进程或其继承管道的
    # 子孙进程挂住不关闭 stdout/stderr，会无限期阻塞后台整理线程（表现为：
    # 记忆文档永远不生成、无日志、聊天正常但记忆中枢空）。这里保证任何情况下
    # 都在 timeout 内返回 None 让调用方降级为规则压缩，线程永不卡死。
    try:
        proc = subprocess.Popen(
            [
                str(cli),
                "-m", str(gguf),
                "--prompt", prompt,
                "-n", str(cfg.get("gen_tokens", 256)),
                "-t", str(cfg.get("threads", 2)),  # 限制推理线程，避免后台整理时打满全机 CPU 导致界面卡顿
                # 关键：单回合后立即退出。缺省是"对话交互模式"——生成完要点后会停在 '>' 等 stdin 输入；
                # 而我们的 stdndin 是 DEVNULL，它永远等不到输入，表现就是 60s 超时反复重试（看着极慢）。
                # 加 -st 且首轮用 --prompt 预定义后，改为一趟生成即退出，模型 20+ tok/s 秒级返回。
                "-st",
                "--no-display-prompt",
                "--simple-io",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_SUBPROC_FLAGS,
        )
    except (subprocess.SubprocessError, OSError):
        return None, None, "启动异常"

    try:
        out, err = proc.communicate(timeout=cfg.get("timeout_s", 60))
    except subprocess.TimeoutExpired:
        # 进程超时：强杀直系子进程、回收资源，返回 None 走规则压缩
        try:
            proc.kill()
        except OSError:
            pass
        proc.wait()
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()
        log.warning("本地整理模型推理超时（>%ss），%s",
                    cfg.get("timeout_s", 60), "将重试")
        return None, "timeout", "推理超时"
    except subprocess.SubprocessError:
        return None, None, "运行异常"

    # 剥离 banner / prompt 回显 / 尾部统计，只保留模型真正生成的内容
    cleaned = _clean_generation(out or "", prompt)
    if proc.returncode != 0:
        return None, proc.returncode, (err or "")[:200]
    if cleaned is None or len(cleaned) < 8:
        return None, 0, ""
    return cleaned, 0, ""


def engine_name() -> str:
    """当前可用的整理引擎名：local-model 或 rules。"""
    if config.LOCAL_MODEL.get("enabled"):
        return "local-model"
    return "rules"