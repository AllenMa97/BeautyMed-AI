# YISIA - 医美领域 AI 智能对话系统

> 定位为用户的"美丽闺蜜"，集成 RAG、知识图谱、内容审核、多语言国际化等核心功能的 AI 智能对话系统

[![Python](https://img.shields.io/badge/Python-3.11%2F3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)](https://fastapi.tiangolo.com/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

## 📖 项目简介

YISIA 是一个面向医美行业的 AI 智能对话系统，采用微服务架构，由三个独立服务组成。系统集成了 RAG（检索增强生成）、知识图谱、内容审核、多语言国际化、用户画像、自进化等高级功能，提供智能问答、产品咨询、角色扮演等多样化交互场景。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端服务 (Port 3000)                     │
│              Node.js / Express / SPA / SSE                  │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────────────────────────┐
│              核心算法服务 (Port 6732)                        │
│         Python / FastAPI / Uvicorn                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ 对话理解    │  │ 功能规划    │  │ 内容审核        │    │
│  │ 意图识别    │  │ LLM 调用    │  │ 多语言国际化    │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTP
┌──────────────▼──────────────────────────────────────────────┐
│              知识库服务 (Port 8002)                          │
│         Python / FastAPI / Uvicorn                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ RAG 检索    │  │ HNSW 索引   │  │ 知识图谱        │    │
│  │ BM25        │  │ 实体检索    │  │ 重排序          │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## ✨ 核心功能

- **智能对话路由**：六步处理流程（短路检测 → 路由决策 → 功能规划 → 功能执行 → 自动 Chat 模式 → SSE 流式输出）
- **自研 RAG 系统**：向量检索 + BM25 + 实体检索 + 知识图谱增强，HybridChunker 语义分块
- **多层内容审核**：四重防护（关键词检测 → LLM 语义审核 → 题库匹配 → 历史违规库）
- **多 LLM 服务商容错**：Key 轮转、模型回退、供应商回退、启动时 Key 健康检测
- **知识图谱**：实体关系抽取、图谱构建、图谱增强 RAG
- **用户画像**：用户风格学习、知识图谱、记忆挖掘
- **多语言国际化**：支持 20+ 语言（中文简繁、英语、东南亚语言、日语、韩语等）
- **前端交互**：SSE 流式对话、6 种主题、图片上传预览、响应式布局

## 🚀 快速开始

### 环境要求

- Python 3.11 或 3.13
- Node.js 18+
- Linux（CentOS/Ubuntu）

### 1. 克隆项目

```bash
git clone <repository-url>
cd lansee_chatbot_ECS
```

### 2. 配置环境变量

```bash
# algorithm_services 配置
cp algorithm_services/config/LLM_API.env.example algorithm_services/config/LLM_API.env
cp algorithm_services/config/SESSION.env.example algorithm_services/config/SESSION.env
cp algorithm_services/config/KNOWLEDGE.env.example algorithm_services/config/KNOWLEDGE.env
cp algorithm_services/config/MODERATION.env.example algorithm_services/config/MODERATION.env
cp algorithm_services/config/SCHEDULE.env.example algorithm_services/config/SCHEDULE.env

# knowledge_base_service 配置
cp knowledge_base_service/config/env.example knowledge_base_service/config/env
```

编辑配置文件，填入实际的 API Key 和配置参数。

### 3. 安装依赖

#### Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install fastapi uvicorn httpx requests pydantic python-dotenv numpy
```

#### Node.js 依赖

```bash
cd frontend_services
npm install
```

### 4. 启动服务

#### 开发模式

```bash
# 启动知识库服务
cd knowledge_base_service
python main.py

# 启动算法服务（新终端）
cd algorithm_services
export PYTHONPATH=/root/YISIA_Algorithm
python -m uvicorn main:app --reload --host 0.0.0.0 --port 6732

# 启动前端服务（新终端）
cd frontend_services
npx nodemon server.js
```

#### 生产模式（Linux systemd）

```bash
# 安装并启动 algorithm_services
sudo ./algorithm_services/fastapi_service.sh install
sudo ./algorithm_services/fastapi_service.sh start

# 安装并启动 frontend_services
sudo ./frontend_services/start_frontend_services.sh install
sudo ./frontend_services/start_frontend_services.sh start

# 手动启动 knowledge_base_service
cd knowledge_base_service
uvicorn main:app --host 0.0.0.0 --port 8002
```

### 5. 访问应用

- 前端界面：http://localhost:3000
- 算法服务 API 文档：http://localhost:6732/api/docs
- 知识库服务 API 文档：http://localhost:8002/docs
- 监控面板：http://localhost:6732/admin

## 📁 项目结构

```
lansee_chatbot_ECS/
├── algorithm_services/          # 核心算法服务（Python/FastAPI，端口 6732）
│   ├── main.py                  # FastAPI 入口
│   ├── api/                     # API 路由和 Schema
│   │   ├── routers/             # 功能路由（14个）
│   │   └── schemas/             # 数据模型
│   ├── core/                    # 核心业务逻辑
│   │   ├── services/            # 服务层（30+ 文件）
│   │   ├── managers/            # 管理器
│   │   ├── moderation/          # 内容审核
│   │   └── prompts/             # Prompt 模板
│   ├── config/                  # 配置文件（5组 .env）
│   ├── data/                    # 数据文件
│   ├── large_model/             # LLM 工厂
│   ├── session/                 # 会话管理
│   └── utils/                   # 工具函数
├── knowledge_base_service/      # 知识库服务（Python/FastAPI，端口 8002）
│   ├── main.py                  # FastAPI 入口
│   ├── api/                     # API 路由
│   ├── core/                    # 核心逻辑
│   │   ├── chunking/            # 文档分块（HybridChunker）
│   │   ├── vector_store/        # 向量存储（HNSW）
│   │   ├── retrieval/           # 检索模块
│   │   ├── rerank/              # 重排序
│   │   └── services/            # 知识服务
│   ├── config/                  # 配置文件
│   └── data/                    # 数据文件
├── frontend_services/           # 前端服务（Node.js/Express，端口 3000）
│   ├── index.html               # SPA 入口
│   ├── server.js                # Express 服务器
│   ├── package.json             # Node.js 依赖
│   └── assets/                  # 静态资源
│       ├── css/                 # 样式文件
│       ├── js/                  # JavaScript 文件
│       └── images/              # 图片资源
└── README.md                    # 项目说明文档
```

## 🔌 核心 API

### algorithm_services

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/entrance` | POST | 聊天机器人主接口（SSE 流式） |
| `/api/v1/intent-recognize/*` | POST | 意图识别 |
| `/api/v1/function-planner/*` | POST | 功能规划 |
| `/api/v1/free-chat/*` | POST | 自由聊天 |
| `/api/v1/content-moderation/*` | POST | 内容审核 |
| `/api/v1/user-style/*` | POST | 用户风格学习 |
| `/api/v1/metrics/*` | GET | 监控指标 |
| `/health` | GET | 健康检查 |
| `/admin` | GET | 监控面板 |
| `/api/docs` | GET | Swagger API 文档 |

### knowledge_base_service

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/rag/query` | POST | RAG 统一查询 |
| `/api/v1/knowledge/search` | POST | 知识搜索 |
| `/api/v1/knowledge/list_all` | GET | 分页获取全量数据 |
| `/api/v1/graph/*` | POST | 知识图谱相关 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API 文档 |

## ⚙️ 配置说明

### algorithm_services 配置

| 配置文件 | 说明 |
|----------|------|
| `LLM_API.env` | LLM 服务商配置（API Key、模型、回退策略） |
| `SESSION.env` | 会话配置（线程池、存储路径、上下文轮数） |
| `KNOWLEDGE.env` | 知识库配置（服务地址、检索参数） |
| `MODERATION.env` | 内容审核配置（阈值设置） |
| `SCHEDULE.env` | 定时任务配置（更新间隔、缓存 TTL） |

### knowledge_base_service 配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `CHUNK_SIMILARITY_THRESHOLD` | 语义相似度阈值 | 0.6 |
| `CHUNK_PARENT_MAX_TOKENS` | 父 chunk 最大 token 数 | 512 |
| `CHUNK_CHILD_MAX_TOKENS` | 子 chunk 最大 token 数 | 128 |
| `EMBEDDING_MODEL` | Embedding 模型 | text-embedding-v3 |
| `EMBEDDING_DIMENSION` | 向量维度 | 1024 |
| `HNSW_M` | HNSW 参数 M | 16 |
| `HNSW_EF_CONSTRUCTION` | HNSW 构建参数 | 200 |
| `HNSW_EF_SEARCH` | HNSW 检索参数 | 50 |

## 🛠️ 技术栈

### 后端

- **语言**：Python 3.11 / 3.13
- **Web 框架**：FastAPI
- **ASGI 服务器**：Uvicorn
- **HTTP 客户端**：httpx（异步）+ requests（同步）
- **数据验证**：Pydantic
- **LLM 服务**：阿里云 DashScope（通义千问系列）
- **Embedding**：text-embedding-v3（1024 维）
- **向量索引**：自实现 HNSW（M=16, ef_construction=200, ef_search=50）

### 前端

- **语言**：JavaScript（ES6+），原生 JS
- **Web 服务器**：Node.js + Express 4.18.2
- **架构**：SPA（单页应用）
- **通信协议**：SSE（Server-Sent Events）
- **Markdown 渲染**：marked.js 12.0.1
- **代码高亮**：highlight.js 11.9.0

### AI/算法

- **RAG**：自研 RAG 系统（向量检索 + BM25 + 实体检索 + 知识图谱）
- **知识图谱**：自研（实体关系抽取 + 图谱构建 + 图谱增强 RAG）
- **文档分块**：HybridChunker（语义相似度分块 + 父子分块策略）
- **内容审核**：多层审核（题库匹配 + LLM 检测 + 历史违规库）

## 📊 监控与运维

### 日志管理

```bash
# 应用日志
tail -f algorithm_services/logs/YISIA.log

# 服务日志
tail -f algorithm_services/logs/algorithm_service.log
tail -f algorithm_services/logs/algorithm_service_err.log

# systemd 日志
journalctl -u yisia-algorithm -f
journalctl -u yisia-frontend -f
```

### 端口检查

```bash
lsof -i:6732  # algorithm_services
lsof -i:8002  # knowledge_base_service
lsof -i:3000  # frontend_services
```

### 服务状态

```bash
systemctl status yisia-algorithm
systemctl status yisia-frontend
```

## ⚠️ 注意事项

1. **安全风险**：
   - `aliyun.key`（阿里云 RSA 私钥）应移至安全位置
   - `.env` 文件包含实际 API Key，不应提交到版本控制
   - 建议将密钥文件加入 `.gitignore`

2. **依赖管理**：
   - Python 项目暂无 `requirements.txt`，建议补充
   - 部署时需手动安装依赖

3. **部署建议**：
   - 项目未容器化，依赖 systemd 部署
   - 建议后续考虑 Docker 化，提升部署灵活性
   - `knowledge_base_service` 缺少 systemd 服务脚本

4. **前端优化**：
   - 前端使用原生 JS，无构建工具
   - `index.html` 内联了大量 CSS，建议后续拆分
   - 当前为开发阶段缓存策略，生产环境建议启用缓存

## 📝 开发计划

- [ ] 补充 Python 依赖锁定文件（requirements.txt / pyproject.toml）
- [ ] Docker 化部署
- [ ] 为 knowledge_base_service 创建 systemd 服务脚本
- [ ] 前端构建工具集成（Webpack/Vite）
- [ ] 前端 CSS 拆分与优化
- [ ] 生产环境缓存策略配置
- [ ] 自动化测试覆盖

## 👨‍💻 开发者

- **开发者**：马赫·马智勇（大模型算法工程师）
- **创建日期**：2026-04-16
- **交接日期**：2026-05-07

## 📄 许可证

Proprietary License

---

**YISIA** - 让每一次对话都成为美丽的开始 ✨