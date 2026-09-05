# 本地模型接入说明（可选）

记忆中枢整理对话可选择性地走本地模型（完全本地、离线、不联网、不调 API、零费用）；
未放置模型或加载失败时，**自动降级回规则压缩**，对话体验不受影响。

> ✅ 本项目已为你完成安装：`llama-cli.exe`(llama.cpp b10549) 与
> `qwen2.5-1.5b-instruct-q4_k_m.gguf`(1.07 GB) 已放入 `backend/models/`，
> 配置默认开启。当前记忆中枢引擎状态带应为**绿色「本地整理模型已就绪」**。

---

## 1. 模型文件放哪

把两样东西放进目录 `backend/models/`：

```
backend/models/
├── llama-cli.exe          # llama.cpp 官方可执行程序
└── qwen2.5-1.5b-instruct-q4_k_m.gguf   # 量化后的 Qwen2.5-1.5B 模型
```

这些文件体积较大，且**不会、也不要提交进 git**（该目录已在忽略列表中）。

## 2. 推荐下载哪个量化版

推荐：**Qwen2.5-1.5B-Instruct · GGUF · Q4_K_M**

原因：
- Q4_K_M 是质量/体积/速度最均衡的量化档，1.5B 档位在普通 CPU 上也能较快运行；
- Instruct 版本经过指令微调，适合"把回复整理成要点"这类任务；
- 若你的设备配置很低，可下 `Q2_K`（更小更慢均压缩）；配置高可上 `Q5_K_M` / `Q6_K`
  （体积更大、略更准）。文件名须与配置里的路径一致，否则识别不到。

获取途径：从 llama.cpp 官方 Release 页面下载 `llama-cli` 可执行文件，
从 Qwen2.5-1.5B-Instruct 的 GGUF 仓库（HuggingFace 等）下载对应量化 .gguf。

## 3. 如何开启开关

已默认开启（`backend/config.py` 的 `LOCAL_MODEL.enabled` 默认为 `True`，也可用环境变量 `MONSTERA_LOCAL_MODEL` 覆盖）。

- 确认方式：打开记忆中枢，顶部状态带应为绿色 **「本地整理模型已就绪 · qwen2.5-1.5b-instruct-q4_k_m.gguf」**。
- 若只开启但模型文件缺失，则显示黄色提示"暂用规则压缩"，说明降级生效。
- 环境变量覆盖示例（可在启动时临时切换）：

```powershell
# 强制开启（默认即开启，一般无需设置）
$env:MONSTERA_LOCAL_MODEL = "1"
# 临时退回纯规则压缩
$env:MONSTERA_LOCAL_MODEL = "0"
python -m uvicorn main:app --host 127.0.0.1 --port 8765
```

## 4. 关闭 / 回退

- 不设置 `MONSTERA_LOCAL_MODEL`（或设为 `0`）即可回到纯规则压缩；
- 运行时随时移走模型文件，下一次整理会自动降级，无需重启。

## 硬性约束（现状即如此）

- 所有整理在本地完成：**不出内网、不经过任何服务器、不调你的 API、不产生费用**；
- 不新增云端依赖；
- 不改变现有整体架构；记忆文档仍是用户本地可编辑的 Markdown。