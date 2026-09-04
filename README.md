# ChatWithSmallC

> 一个有长期记忆、能看屏幕、能操作桌面的本地 AI 女友（personal desktop AI companion）。
> 基于 [Open-LLM-VTuber](https://github.com/t41372/Open-LLM-VTuber) 二次开发，集成 [Letta](https://www.letta.com/) 持久化记忆与 OpenClaw 桌面控制。

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10--3.12-blue)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Agent](https://img.shields.io/badge/agent-Letta-orange)

---

## 项目背景

Open-LLM-VTuber 是一个开源的语音交互 Live2D 数字人框架，但它原生的记忆是会话级的，关掉就忘。本项目在此基础上：

1. **接入 Letta 作为长期记忆后端** —— 角色人设、过往对话、用户偏好都持久化在 Letta Agent 里，跨会话保留。
2. **新增 computer_control 模块** —— 角色不只是"说话"，还能在用户授权下执行真实的桌面操作（截图、点击、键入、文件操作），并把执行结果（截图、操作日志）回写到对话里。
3. **MCP 工具生态** —— 通过 `mcpp` 接入 Model Context Protocol 工具（搜索、计算、自定义工具），让角色具备"动手能力"。

> 这不是又一个聊天机器人 demo，是一个可以挂在桌面上、记住你是谁、偶尔帮你点两下屏幕的角色。

---

## 核心特性

| 模块 | 能力 |
|------|------|
| 🎙 **语音交互** | ASR（sherpa-onnx）→ LLM → TTS（edge-tts / Azure）全链路本地可跑，Voice Activity Detection 支持语音打断 |
| 🧠 **长期记忆** | Letta 持久化 agent，支持 persona、human、archival memory 三段记忆，断电不丢 |
| 👁 **视觉感知** | 摄像头 / 屏幕共享 / 截图，角色能"看见"你当前在做什么 |
| 🖱 **桌面控制** | 自研 `computer_control` 模块：意图解析 → 策略审批 → OpenClaw 桥接执行 → 审计日志 |
| 🧩 **MCP 工具** | 通过 `mcpp` 集成 MCP server（如 duckduckgo-mcp-server），角色可以调用外部工具 |
| 🎭 **Live2D 形象** | 表情动作映射，表情/嘴型与 TTS 同步 |
| 🪟 **桌面宠物** | 透明背景、置顶、鼠标穿透，可拖到屏幕任意角落 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (Live2D + Web)               │
│  Vue + PixiJS · 表情驱动 · 语音输入/输出 · 摄像头/截屏     │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI Server (run_server.py)               │
│  ASR → VAD → Agent Loop → TTS → 推流回前端                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌─────────────────────┐
│  Letta Agent  │  │ Stateless LLM │  │ computer_control    │
│  (长记忆)     │  │ (OpenAI/      │  │ ┌─────────────────┐ │
│  persona/     │  │  Claude/      │  │ │ intent 意图解析 │ │
│  human/       │  │  Ollama/      │  │ │ policy 策略审批 │ │
│  archival     │  │  llama.cpp)   │  │ │ openclaw 桥接   │ │
└───────────────┘  └───────────────┘  │ │ audit  审计日志 │ │
                                       │ └─────────────────┘ │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │   本机桌面 / 文件   │
                                       └─────────────────────┘
```

---

## 技术栈

**后端**
- Python 3.10–3.12 · FastAPI · uvicorn · WebSocket
- ASR：sherpa-onnx · TTS：edge-tts / pyttsx3 / Azure Speech
- LLM 适配：OpenAI 兼容 / Anthropic / Ollama / llama.cpp
- Agent：Letta Client（持久化）+ mem0（备选）
- MCP：Model Context Protocol 客户端

**桌面控制**
- 自研意图识别（`intent.py`）+ 策略审批（`policy.py`）
- OpenClaw 命令行桥接（`openclaw_cli.py`）
- 截图/审批/审计独立子模块

**工程化**
- `pyproject.toml`（PEP 621）· `uv.lock` · `pixi.lock`
- Ruff + pre-commit · pytest
- Docker 支持

---

## 目录结构

```
.
├── Open_LLM_Vtuber/          # 主项目（基于 Open-LLM-VTuber fork）
│   ├── src/open_llm_vtuber/
│   │   ├── agent/            # Agent 抽象 + Letta/Mem0 实现
│   │   ├── asr/              # 语音识别
│   │   ├── tts/              # 语音合成
│   │   ├── vad/              # 语音活动检测
│   │   ├── live/             # Live2D 表情/动作
│   │   ├── conversations/    # 会话状态机
│   │   ├── computer_control/ # 桌面控制（自研）
│   │   ├── mcpp/             # MCP 客户端
│   │   └── translate/        # 翻译/语言检测
│   ├── frontend/             # Vue + PixiJS 前端
│   ├── characters/           # 角色预设
│   ├── prompts/              # 角色 prompt 模板
│   ├── tests/                # pytest 测试
│   ├── run_server.py         # 启动入口
│   └── pyproject.toml
├── docs/                     # 设计文档
└── README.md
```

---

## 快速开始

> 需要 Python 3.10–3.12、Node 18+（前端构建）、可选 CUDA。

```bash
# 1. 克隆
git clone https://github.com/GuideSword/vtuber-letta-stack.git
cd vtuber-letta-stack/Open_LLM_Vtuber

# 2. 安装依赖（推荐 uv）
pip install -e .
# 或
uv sync

# 3. 启动 Letta 服务（可选，启用长期记忆时需要）
#    参考 https://docs.letta.com

# 4. 复制配置模板并填入 API key
cp conf.yaml.bak conf.yaml  # 若 conf.yaml 不存在

# 5. 启动服务
python run_server.py
```

打开浏览器访问 `http://localhost:12393` 即可与角色对话。

---

## 自研模块说明

### `computer_control/` —— 桌面操作闭环

不只是"调用一次 shell"，而是完整的 **意图 → 审批 → 执行 → 审计** 闭环：

- `intent.py` — 把自然语言指令解析为结构化操作
- `policy.py` — 按白名单/危险等级决定是否需要用户授权
- `openclaw_cli.py` — 通过 OpenClaw CLI 桥接真实桌面
- `approvals.py` — 用户审批/拒绝 UI 流程
- `audit.py` — 每次操作留痕（谁、什么时候、执行了什么）
- `artifacts.py` — 截图/日志归档

### `agent/agents/letta_agent.py` —— Letta 集成

- 通过 `letta-client` 接入 Letta Server
- 角色人设与历史消息走 Letta 的 persona / human / archival 三段记忆
- 工具调用结果（computer_control、web_search）回写到 archival

---

## 致谢

- [Open-LLM-VTuber](https://github.com/t41372/Open-LLM-VTuber) — 主框架
- [Letta](https://github.com/letta-ai/letta) — 长期记忆 agent
- [OpenClaw](https://github.com/openclaw) — 桌面控制桥接
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) — 本地 ASR / VAD

---

## License

[MIT](./LICENSE)
