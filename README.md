# MCP-MD Agent

一个基于 MCP (Model Context Protocol) 协议的简单 LLM Agent 项目，让 llm 可以写入本地 md 文件，支持 Ollama 本地模型或硅基流动接入，是一个学习项目，比较简单

特别感谢 https://github.com/keli-wen/mcp_chatbot 该项目基本仿照此项目来写的



## 项目结构

```
src/
├── mcp_chatbot/         # 核心包
│   ├── config/          # 配置管理
│   ├── llm/             # LLM 客户端
│   ├── mcp/             # MCP 客户端
│   ├── chat/            # 聊天会话
│   └── __init__.py
└── main.py              # 主入口

mcp_servers/
└── servers_config.json  # MCP 服务器配置
```

## 快速开始

### 1. 安装依赖

```bash
pixi install
```

### 2. 配置环境
编辑 `.env` 文件：

```env
# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NAME=gemma:2b

# 硅基流动配置
SILICONFLOW_API_KEY=your_api_key_here
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL_NAME=deepseek-ai/DeepSeek-V3

# 使用哪个 LLM (ollama 或 siliconflow)
LLM_PROVIDER=ollama
```

### 3. 运行

```bash
# 运行聊天机器人
pixi run start
```


## License
MIT

