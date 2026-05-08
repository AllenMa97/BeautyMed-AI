# YISIA项目详述

> 医美领域 AI 智能对话系统 - 技术架构与实现详解

---

## 一、项目概述

### 1.1 项目定位

YISIA（Lansee Chatbot）是一个面向医美行业的 AI 智能对话系统，定位为用户的"美丽闺蜜"。系统集成了 RAG（检索增强生成）、知识图谱、内容审核、多语言国际化、用户画像、自进化等高级功能，采用微服务架构设计。

### 1.2 核心特性

- **智能对话路由**：六步处理流程，支持意图识别、功能规划、自动模式选择
- **自研 RAG 系统**：向量检索 + BM25 + 实体检索 + 知识图谱增强
- **多层内容审核**：四重防护机制，覆盖 7 类违规内容
- **多 LLM 服务商容错**：Key 轮转、模型回退、供应商回退
- **知识图谱**：实体关系抽取、图谱构建、图谱增强 RAG
- **用户画像**：用户风格学习、知识图谱、记忆挖掘
- **多语言国际化**：支持 20+ 语言
- **前端交互**：SSE 流式对话、6 种主题、响应式布局

---

## 二、系统架构

### 2.1 微服务架构总览

系统由三个独立微服务组成，部署在同一台 Linux 服务器上，通过 HTTP 内部通信：

| 服务名称 | 技术栈 | 端口 | 职责 |
|---------|--------|------|------|
| algorithm_services | Python / FastAPI / Uvicorn | 6732 | 核心算法服务：对话理解、功能规划、内容审核、LLM 调用 |
| knowledge_base_service | Python / FastAPI / Uvicorn | 8002 | 知识库服务：RAG 检索、向量索引（HNSW）、知识图谱、重排序 |
| frontend_services | Node.js / Express | 3000 | 前端服务：SPA 单页应用、用户认证、流式对话界面 |

### 2.2 请求处理流程

```
用户输入
  ↓
步骤1：快速短路检测（词表匹配简单问候/确认/感谢）
  ↓
步骤2：路由决策（判断 need_plan / need_search，异步并行启动内容违规检测）
  ├─ need_plan=False → free_chat 兜底
  └─ need_plan=True → 步骤3
  ↓
步骤3：功能规划（决定调用哪些功能模块）
  ↓
步骤4：执行功能（按顺序执行规划的功能，结果存入 session）
  ↓
步骤5：自动选择 Chat 方式（有知识检索结果用 knowledge_chat，无结果用 free_chat）
  ↓
步骤6：SSE 流式输出返回结果
```

### 2.3 架构设计亮点

#### 2.3.1 多 LLM 服务商容错机制

- **Key 轮转**：每个服务商支持最多 9 个 API Key，400/403 错误时自动切换
- **模型回退**：配额不足时自动切换到备用模型
- **供应商回退**：主供应商失败时切换到备用供应商
- **启动时 Key 健康检测**：并行检测所有 Key 的可用性和支持的模型
- **阿里云 Context Cache**：cache_control 优化重复 system_prompt 的 token 消耗

#### 2.3.2 多层内容审核防护

| 层级 | 检测方式 | 说明 | 阈值 |
|------|---------|------|------|
| 第一层 | 关键词检测 | 7 类违规内容，多线程并行 | - |
| 第二层 | LLM 检测（C41） | qwen-flash 模型，语义级审核 | 0.85 |
| 第三层 | 题库匹配（C35-C39） | Embedding 相似度检测 | 0.85 |
| 第四层 | 历史违规库匹配（C42） | Embedding 相似度检测 | 0.90 |

#### 2.3.3 SSE 流式输出

- **协议**：Server-Sent Events（text/event-stream）
- **状态码**：
  - 102 - 中间过程（AI 思考中）
  - 200 - 最终结果
  - 300 - 流式片段
  - 403 - 违规内容拦截
  - 500 - 错误
- **前端实现**：chatApi.js 使用 Fetch API + ReadableStream 接收

#### 2.3.4 会话上下文管理

- **CONTEXT_COLLAPSE 归档机制**：当对话轮数超过 MAX_LOOP（默认 2）时，将早期对话归档为摘要，保留最近轮次的完整上下文

#### 2.3.5 性能监控和指标统计

- **性能监控**：@monitor_async 装饰器跟踪异步函数执行时间
- **指标管理**：metrics_manager 记录 LLM 调用成本、请求级别统计
- **监控面板**：/admin 页面提供实时监控仪表盘
- **指标 API**：小时级、日级、实时统计 API

---

## 三、技术栈详解

### 3.1 后端技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.11 / 3.13 |
| Web 框架 | FastAPI | Latest |
| ASGI 服务器 | Uvicorn | Latest |
| HTTP 客户端 | httpx（异步）+ requests（同步） | Latest |
| 数据验证 | Pydantic | Latest |
| 环境变量 | python-dotenv | Latest |
| LLM 服务商 | 阿里云 DashScope（通义千问系列） | - |
| Embedding | text-embedding-v3 | 1024 维向量 |
| 向量索引 | HNSW（自实现） | M=16, ef_construction=200, ef_search=50 |
| 部署 | Linux systemd 守护进程 | - |

### 3.2 前端技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 语言 | JavaScript（ES6+），原生 JS，无框架 | - |
| Web 服务器 | Node.js + Express | 4.18.2 |
| 开发工具 | nodemon | 3.0.1 |
| Markdown 渲染 | marked.js | 12.0.1（CDN 引入） |
| 代码高亮 | highlight.js | 11.9.0（CDN 引入） |
| 架构 | SPA（单页应用），对象字面量模式 | - |
| 通信协议 | SSE（Server-Sent Events）流式聊天 | - |
| UI 特性 | 6 种主题、20+ 种语言、响应式布局、暗色模式 | - |

### 3.3 AI/算法技术栈

| 技术 | 说明 |
|------|------|
| RAG | 自研 RAG 系统（向量检索 + BM25 + 实体检索 + 知识图谱） |
| 知识图谱 | 自研（实体关系抽取 + 图谱构建 + 图谱增强 RAG） |
| 文档分块 | HybridChunker（语义相似度分块 + 父子分块策略） |
| 内容审核 | 多层审核（题库匹配 C35-C39 + LLM 检测 C41 + 历史违规库 C42） |
| 国际化 | BCP 47 标准，支持 20+ 语言自动检测 |
| 用户画像 | 用户风格学习、知识图谱、记忆挖掘 |

---

## 四、核心模块详解

### 4.1 algorithm_services（核心算法服务）

#### 4.1.1 目录结构

```
algorithm_services/
├── main.py                      # FastAPI 入口文件（端口 6732）
├── fastapi_service.sh           # systemd 服务管理脚本
├── admin/
│   └── dashboard.html           # 监控面板页面
├── api/
│   ├── routers/
│   │   ├── main_router.py       # 统一入口路由 /api/v1/entrance
│   │   ├── metrics_router.py    # 监控指标路由
│   │   └── feature_routers/     # 功能路由模块（14个路由文件）
│   └── schemas/
│       ├── base_schemas.py
│       └── schema_kit.py
├── core/
│   ├── managers/                # 管理器（知识存储、指标、截图、自进化）
│   ├── models/                  # 模型（embedding）
│   ├── moderation/              # 内容审核模块
│   ├── prompts/                 # Prompt 模板
│   └── services/                # 核心服务层（30+ 服务文件）
│       ├── feature_services/    # 功能服务（30+ 文件）
│       └── simulation/          # 用户模拟服务
├── config/                      # 配置文件目录（5组 .env 配置）
├── data/                        # 数据文件
├── large_model/
│   ├── llm_factory.py           # LLM 工厂
│   └── lvlm_factory.py          # 视觉语言模型工厂
├── session/
│   └── session_factory.py       # 会话工厂
└── utils/                       # 工具函数
```

#### 4.1.2 功能路由（14个）

| 路由 | 功能 |
|------|------|
| main_router | 统一入口路由 /api/v1/entrance |
| content_moderation_router | 内容审核 |
| dialog_summary_router | 对话摘要 |
| entity_relation_extraction_router | 实体关系抽取 |
| free_chat_router | 自由聊天 |
| function_planner_router | 功能规划 |
| intent_clarify_router | 意图澄清 |
| intent_recognize_router | 意图识别 |
| language_setting_router | 语言设置 |
| llm_web_search_router | LLM 联网搜索 |
| text_summary_router | 文本摘要 |
| title_generation_router | 标题生成 |
| user_knowledge_graph_router | 用户知识图谱 |
| user_style_router | 用户风格学习 |

#### 4.1.3 核心服务层

**功能服务（feature_services）**：
- correction_detection_service - 纠正检测
- dialog_summary_service - 对话摘要
- emotion_recognition_service - 情感识别
- entity_relation_extraction_service - 实体关系抽取
- free_chat_service - 自由聊天
- function_executer_service - 功能执行
- function_planner_service - 功能规划
- i18n_service - 国际化
- image_understanding_service - 图像理解
- intent_clarify_service - 意图澄清
- intent_recognize_service - 意图识别
- knowledge_chat_service - 知识问答
- knowledge_retrieval_service - 知识检索
- memory_recall_service - 记忆召回
- pre_process_service - 预处理
- recommendation_service - 推荐
- routing_decision_service - 路由决策
- rss_feed_service - RSS 订阅
- search_decision_service - 搜索决策
- text_summary_service - 文本摘要
- title_generation_service - 标题生成
- user_knowledge_graph_service - 用户知识图谱
- user_memory_mining_service - 用户记忆挖掘
- user_profile_service - 用户画像
- user_style_service - 用户风格学习

**基础服务**：
- base_service - 基础服务
- system_initializer - 系统初始化
- knowledge_base_client - 知识库客户端
- llm_web_search_service - LLM 联网搜索
- jina_reader_service - Jina 网页读取
- mcp_executer_service - MCP 工具执行
- self_evolution_service - 自进化
- fashion_portal_service - 时尚门户
- time_location_service - 时间地理位置
- trending_topics_service - 热点话题
- scheduled_update_service - 定时更新
- browser_trending_service - 浏览器热搜
- context_injection_controller - 上下文注入控制
- external_knowledge_service - 外部知识

#### 4.1.4 内容审核模块

```
core/moderation/
├── api.py                      # 审核 API
├── blocked_query_storage.py    # 拦截查询存储
├── embedding_storage.py        # 向量存储
├── keyword_detector.py         # 关键词检测
├── moderation_coordinator.py   # 审核协调器
├── parallel_keyword_detector.py # 并行关键词检测
├── question_bank_detector.py   # 题库检测
└── question_bank_manager.py    # 题库管理
```

**7 类违规内容**：
1. 政治敏感
2. 暴力
3. 色情
4. 赌博
5. 毒品
6. 仇恨
7. 虚假信息

#### 4.1.5 Prompt 模板

```
core/prompts/features/
├── moderation/                 # 审核 Prompt
│   ├── drug_moderation_prompt.py      # 毒品审核
│   ├── fake_moderation_prompt.py      # 虚假信息审核
│   ├── gambling_moderation_prompt.py  # 赌博审核
│   ├── hate_moderation_prompt.py      # 仇恨审核
│   ├── political_moderation_prompt.py # 政治审核
│   ├── pornography_moderation_prompt.py # 色情审核
│   └── violence_moderation_prompt.py  # 暴力审核
├── content_moderation_prompt.py       # 内容审核
├── correction_detection_prompt.py     # 纠正检测
├── dialog_summary_prompt.py           # 对话摘要
├── entity_relation_extraction_prompt.py # 实体关系抽取
├── feature_stage_prompt.py            # 功能阶段
├── free_chat_prompt.py                # 自由聊天
├── function_planner_prompt.py         # 功能规划
├── i18n_prompt.py                     # 国际化
├── intent_clarify_prompt.py           # 意图澄清
├── intent_recognize_prompt.py         # 意图识别
├── knowledge_chat_prompt.py           # 知识问答
├── mcp_planner_prompt.py              # MCP 规划
├── routing_decision_prompt.py         # 路由决策
├── self_evolution_prompt.py           # 自进化
├── text_summary_prompt.py             # 文本摘要
├── title_generation_prompt.py         # 标题生成
└── user_profile_prompt.py             # 用户画像
```

### 4.2 knowledge_base_service（知识库服务）

#### 4.2.1 目录结构

```
knowledge_base_service/
├── main.py                      # FastAPI 入口文件（端口 8002）
├── build_knowledge_graph.py     # 知识图谱构建脚本
├── chunk_documents.py           # 文档分块脚本
├── api/
│   ├── routers/
│   │   ├── graph_rag_router.py
│   │   ├── graph_visualization_router.py
│   │   ├── knowledge_router.py
│   │   ├── main_router.py
│   │   └── rag_router.py
│   └── schemas/
│       ├── knowledge_schemas.py
│       └── rag_schemas.py
├── core/
│   ├── augmentation/            # 上下文增强（去重、token预算）
│   ├── cache/                   # 查询缓存
│   ├── chunking/                # 文档分块系统（HybridChunker）
│   ├── llm_prompts/             # RAG Prompt（15+ 模板）
│   ├── processors/              # 处理器（OCR、爬虫、搜索引擎、代理）
│   ├── rerank/                  # 重排序（混合重排、LLM重排）
│   ├── retrieval/               # 检索（BM25、实体检索）
│   ├── services/                # 知识服务（embedding、实体匹配）
│   ├── vector_store/            # 向量存储（HNSW ANN 索引）
│   ├── llm_client.py
│   ├── content_analyzer.py
│   ├── knowledge_collection.py
│   ├── layered_knowledge_manager.py
│   └── news_search_service.py
├── config/
│   ├── env / env.example        # 环境变量配置
│   ├── settings.py              # 配置加载器
│   └── database_config.json     # 数据库配置
├── data/
│   ├── chunk_embeddings/        # 向量索引数据（JSON 格式）
│   ├── chunks/                  # 分块数据（250个产品 x 2 chunks = 500 文件）
│   ├── INDEX_README.md
│   └── brand_group_mapping.json
└── scripts/                     # 脚本工具
```

#### 4.2.2 文档分块系统（HybridChunker）

**分块策略演进**：

1. **固定长度分块** ❌
   - 简单按字符数切分
   - 问题：从句子中间切断，不考虑语义边界

2. **句子边界分块** ✅
   - 在句号、感叹号、问号、换行符处切断
   - 问题：无法识别话题转换点

3. **语义相似度分块** ✅✅
   - 计算相邻句子的 Embedding 相似度
   - 在相似度低的地方切断（阈值 < 0.6）
   - 优势：自动识别话题转换点，检索精度提升 20-30%

4. **父子分块** ✅✅✅（最佳实践）
   - 父 chunk：语义完整的段落（~512 tokens），提供上下文
   - 子 chunk：细粒度的片段（~128 tokens），用于检索
   - 检索策略：用子 chunk 检索（精度高），找到后返回父 chunk（信息完整）

**HybridChunker 参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| parent_max_tokens | 512 | 父 chunk 最大 token 数 |
| child_max_tokens | 128 | 子 chunk 最大 token 数 |
| similarity_threshold | 0.6 | 语义相似度阈值 |
| min_tokens | 50 | 最小 token 数 |
| enable_parent_child | True | 是否启用父子分块 |

#### 4.2.3 向量存储（HNSW）

**自实现 HNSW 索引**：

| 参数 | 值 | 说明 |
|------|-----|------|
| M | 16 | 每个节点的最大连接数 |
| ef_construction | 200 | 构建时的搜索宽度 |
| ef_search | 50 | 检索时的搜索宽度 |
| 维度 | 1024 | text-embedding-v3 向量维度 |
| 批量大小 | 10 | 阿里云 API 限制 |

#### 4.2.4 检索与重排序

**检索模块**：
- bm25_retriever.py - BM25 检索
- entity_retriever.py - 实体检索
- multi_path_retriever.py - 多路径检索
- constraint_retriever.py - 约束检索

**重排序模块**：
- base_reranker.py - 基础重排器
- cross_encoder_reranker.py - 交叉编码器重排
- hybrid_reranker.py - 混合重排
- llm_reranker.py - LLM 重排

#### 4.2.5 RAG Prompt 模板（15+）

```
core/llm_prompts/
├── content_similarity_prompt.py       # 内容相似度
├── content_verification_prompt.py     # 内容验证
├── credibility_evaluation_prompt.py   # 可信度评估
├── extract_document_information_prompt.py # 文档信息提取
├── extract_html_content_prompt.py     # HTML 内容提取
├── extract_information_prompt.py      # 信息提取
├── generate_search_queries_prompt.py  # 搜索查询生成
├── get_real_urls_prompt.py            # 真实 URL 获取
├── joint_extraction_prompt.py         # 联合抽取
├── keyword_extraction_prompt.py       # 关键词提取
├── knowledge_classification_prompt.py # 知识分类
├── next_search_action_prompt.py       # 下一步搜索动作
├── page_analysis_prompt.py            # 页面分析
├── rag_prompt.py                      # RAG 主 Prompt
└── search_evaluation_prompt.py        # 搜索评估
└── url_identification_prompt.py       # URL 识别
```

### 4.3 frontend_services（前端服务）

#### 4.3.1 目录结构

```
frontend_services/
├── index.html                   # SPA 单页应用入口（2600+ 行）
├── server.js                    # Express 静态文件服务器（端口 3000）
├── package.json                 # Node.js 依赖
├── package-lock.json
├── README.md
├── start_frontend_services.bat  # Windows 启动脚本
├── start_frontend_services.sh   # Linux systemd 管理脚本
└── assets/
    ├── css/
    │   ├── base.css             # 基础重置样式
    │   ├── theme.css            # 主题 CSS 变量
    │   ├── chat.css             # 聊天页面布局样式
    │   └── login.css            # 登录/注册页面样式
    ├── images/
    │   └── carousel/            # 轮播图资源（5张 PNG）
    └── js/
        ├── api/
        │   ├── authApi.js       # 认证 API
        │   └── chatApi.js       # 聊天 API（SSE 流式消息、文件上传）
        ├── config/
        │   └── appConfig.js     # 全局配置
        ├── core/
        │   ├── authManager.js   # 认证管理器
        │   └── stateManager.js  # 简易状态管理器
        ├── utils/
        │   ├── chatUtils.js     # 聊天上下文生成工具
        │   ├── dateFormat.js    # 时间格式化工具
        │   ├── debounce.js      # 防抖 + 防重复执行工具
        │   ├── domUtils.js      # DOM 操作工具类
        │   └── idUtils.js       # ID 生成/管理工具
        └── views/
            ├── chatView.js      # 聊天主视图逻辑（核心文件，约1934行）
            └── loginView.js     # 登录/注册视图逻辑
```

#### 4.3.2 前端功能特性

**登录视图（loginView.js）**：
- 手机号登录：输入手机号 + 短信验证码，支持中国大陆手机号格式校验
- 图形验证码：Canvas 绘制的数学运算验证码（加减乘）
- 验证码倒计时：60 秒倒计时
- 用户注册：姓名 + 身份证号 + 手机号 + 验证码
- Token 检查：自动检查 JWT Token 有效性和过期时间
- 开发者模式：Ctrl+Shift+D 快捷键唤出 Dev Panel

**聊天视图（chatView.js，核心文件约 1934 行）**：
- 流式对话：SSE 实现 AI 回复的流式展示
- Markdown 渲染：完整的 Markdown 语法渲染
- 代码高亮：highlight.js 对代码块进行语法高亮
- 图片上传：最多 5 张图片（jpg/png/gif/webp，单张限制 5MB）
- 图片预览：全屏预览，支持复制/保存/引用
- 产品轮播图：5 张产品图片自动轮播
- 多主题切换：6 种主题风格
- 多语言支持：17 种语言
- 未成年人模式：传递 minor_mode=true 参数
- 个性化推荐：可开关
- 免责声明弹窗：首次进入显示
- 消息操作：AI 消息支持复制/重新生成；用户消息支持复制/重新发送
- 示例问题：预设示例问题按钮，支持"换一批"
- ID 管理：User ID 和 Session ID 的显示/编辑/重置
- API 配置：动态修改后端 API 地址和端口
- 停止生成：发送中可随时中断
- 响应式布局：完整的移动端适配

**6 种主题**：
1. 明亮主题（.light-theme）：主色调 #409eff（蓝色）
2. 柔和主题（.soft-theme）：主色调 #ff9a9e（粉色）
3. 现代主题（.modern-theme）：主色调 #8e44ad（紫色）
4. 深色主题（.dark-mode）：主色调 #66b1ff（亮蓝）
5. 极简主题（.minimal-theme）：主色调 #6b7280（灰色）
6. 活力主题（.vibrant-theme）：主色调 #f59e0b（橙色）

#### 4.3.3 状态管理（stateManager.js）

**状态结构**：
```javascript
{
  isSending: false,       // 是否正在发送消息
  messageList: [],        // 消息列表
  isDarkMode: false,      // 暗色模式
  lastSendTime: 0,        // 上次发送时间
  userId: "",             // 用户ID
  sessionId: "",          // 会话ID
  minorMode: false,       // 未成年人模式
  isLoggedIn: false,      // 登录状态
  userInfo: null,         // 用户信息
  personalize: true       // 个性化推荐
}
```

**持久化策略（localStorage）**：
- darkMode, messageHistory, apiConfig, accessToken, userInfo
- current_user_id, current_session_id, currentTheme, currentLanguage
- minorMode, personalize, aiDisclaimerAccepted

---

## 五、配置详解

### 5.1 algorithm_services 配置（5组 .env 文件）

#### 5.1.1 LLM_API.env - LLM 服务商配置

```ini
LLM_DEFAULT_PROVIDER=aliyun
ALIYUN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
ALIYUN_API_KEY=sk-xxx
ALIYUN_DEFAULT_MODEL=qwen-plus
ALIYUN_MODELS={"qwen-flash":"qwen-flash","qwen-turbo":"qwen-turbo",...}
ALIYUN_FALLBACK_MODELS=["qwen-flash","qwen-plus","qwen-turbo"]
```

**可用模型（12个）**：
- qwen-flash, qwen-turbo, qwen-plus, qwen-long
- qwen-vl-plus, qwen-vl-max-latest
- qwen2.5-7b-instruct, qwen2.5-14b-instruct
- qwen-coder-plus-latest, qwen-coder-turbo-0919
- qwen-math-plus, qwen-math-turbo

#### 5.1.2 SESSION.env - 会话配置

```ini
THREAD_POOL_MAX_WORKERS=10
SESSION_STORAGE_PATH="./local_session_data"
MAX_LOOP=2
BACKEND_DB_API="http://backend-api/sessions/"
KNOWLEDGE_BASE_SERVICE_URL=http://101.37.209.109:8002
```

#### 5.1.3 KNOWLEDGE.env - 知识库配置

```ini
KNOWLEDGE_BASE_SERVICE_URL=http://101.37.209.109:8002
KNOWLEDGE_DEFAULT_SEARCH_MODE=hybrid
KNOWLEDGE_DEFAULT_TOP_K=10
KNOWLEDGE_DEFAULT_THRESHOLD=0.3
KNOWLEDGE_DEFAULT_SEARCH_TYPE=all
```

#### 5.1.4 MODERATION.env - 内容审核配置

```ini
QUESTION_BANK_THRESHOLD_C35=0.85
QUESTION_BANK_THRESHOLD_C36=0.85
QUESTION_BANK_THRESHOLD_C37=0.85
QUESTION_BANK_THRESHOLD_C38=0.85
QUESTION_BANK_THRESHOLD_C39=0.85
LLM_DETECTION_THRESHOLD=0.85
BLOCKED_HISTORY_THRESHOLD=0.90
```

#### 5.1.5 SCHEDULE.env - 定时任务配置

```ini
API_KEY_CHECK_INTERVAL=14400          # API Key 检测间隔（4小时）
CONTENT_UPDATE_INTERVAL=14400         # 内容更新间隔（4小时）
SIMULATION_CHECK_INTERVAL=1800        # 模拟用户生成检查间隔（30分钟）
INTENT_CACHE_TTL=3600                 # 意图缓存 TTL（1小时）
TRENDING_CACHE_TTL=1800               # 热搜缓存 TTL（30分钟）
DIALOG_SUMMARY_TIME_THRESHOLD=300     # 对话摘要时间阈值（5分钟）
USER_PROFILE_UPDATE_INTERVAL=300      # 用户画像更新间隔（5分钟）
MEMORY_MINING_INTERVAL=7200           # 用户记忆挖掘间隔（2小时）
```

### 5.2 knowledge_base_service 配置

#### 5.2.1 env - 主配置

```ini
DASHSCOPE_API_KEY=sk-xxx
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
CHUNK_SIMILARITY_THRESHOLD=0.6
CHUNK_PARENT_MAX_TOKENS=512
CHUNK_CHILD_MAX_TOKENS=128
CHUNK_MIN_TOKENS=50
CHUNK_ENABLE_PARENT_CHILD=True
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSION=1024
EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_BATCH_SIZE=10
HNSW_M=16
HNSW_EF_CONSTRUCTION=200
HNSW_EF_SEARCH=50
ENABLE_LLM_RERANKER=True
LLM_RERANKER_MODEL=qwen-plus
LLM_RERANKER_BATCH_SIZE=10
SERVICE_PORT=8002
LOG_LEVEL=INFO
DEBUG=False
```

### 5.3 前端配置（appConfig.js）

```javascript
const AppConfig = {
  API_BASE_URL: window.location.origin + "/chat",
  CHAT_API_PATH: "/api/v1/entrance",
  DEBOUNCE_TIME: 500,
  EMOTICONS: ["😊", "😂", "🤔", "👍", "👋", "😎", "🤩", "💡"],
  STORAGE_KEYS: {
    DARK_MODE: "darkMode",
    MESSAGE_HISTORY: "messageHistory",
    API_CONFIG: "apiConfig",
    ACCESS_TOKEN: "accessToken",
    USER_INFO: "userInfo"
  },
  AUTH: {
    SEND_CODE_PATH: "/api/auth/sms/send",
    LOGIN_PATH: "/api/auth/sms/login"
  }
};
```

---

## 六、数据存储说明

### 6.1 存储方式总览

项目不使用传统关系型数据库，全部使用 JSON 文件存储。

### 6.2 algorithm_services 数据存储

| 数据类型 | 位置 | 格式 |
|---------|------|------|
| 会话存储 | algorithm_services/data/session_store.py | 三级缓存（内存 > pickle > 数据库接口预留） |
| 向量存储 | algorithm_services/data/vector_store.py | 本地向量存储 |
| 嵌入数据 | algorithm_services/data/embeddings/ | JSON 文件 |
| 拦截查询 | algorithm_services/data/blocked_queries/ | JSON 文件 |
| 题库数据 | algorithm_services/data/question_bank_json/ | JSON 文件（C35-C39） |
| 知识数据 | algorithm_services/data/knowledge/ | JSON 文件（behavior/feature/interaction） |

### 6.3 knowledge_base_service 数据存储

| 数据类型 | 位置 | 格式 |
|---------|------|------|
| 向量索引 | knowledge_base_service/data/chunk_embeddings/ | JSON 文件（vectors.json, id_list.json, metadata.json, contents.json） |
| 分块数据 | knowledge_base_service/data/chunks/ | JSON 文件（250 个产品 x 2 chunks = 500 个文件） |
| 品牌集团映射 | knowledge_base_service/data/brand_group_mapping.json | JSON 文件 |
| 查询缓存 | knowledge_base_service/data/query_cache/ | 缓存文件 |

---

## 七、第三方服务集成

### 7.1 LLM/AI 服务（阿里云 DashScope）

| 配置项 | 值 |
|--------|-----|
| API 地址 | https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions |
| Embedding 模型 | text-embedding-v3 |
| 向量维度 | 1024 |
| 批量大小 | 10（阿里云限制） |

**容错机制**：
- 多 API Key 轮转（支持最多 9 个 Key）
- 模型回退（配额不足时自动切换）
- 供应商回退（主供应商失败时切换）
- 启动时 Key 健康检测（并行检测）
- 阿里云 Context Cache（优化 token 消耗）

### 7.2 Jina Reader（网页内容读取）

| 配置项 | 值 |
|--------|-----|
| API 地址 | r.jina.ai |
| 功能 | 读取任意网页内容 |
| 特性 | 支持多个备用读取方案、内置 15+ 中文新闻网站配置、缓存机制（TTL 30 分钟）、关键词提取（jieba） |

### 7.3 认证后端服务

| 配置项 | 值 |
|--------|-----|
| 地址 | http://localhost:8123 |
| 功能 | 用户认证（短信验证码登录/注册） |
| 代理路径 | /api/auth/{path} → /internal-api/auth/{path} |
| 认证方式 | JWT Bearer Token |

### 7.4 MCP 工具系统

**协议**：MCP（Model Context Protocol）风格

**注册工具（12个）**：
- dialog_summary, entity_relation_extraction, free_chat
- function_planner, intent_clarify, intent_recognize
- text_summary, title_generation, content_moderation
- llm_web_search, user_style, user_knowledge_graph

---

## 八、部署与运维

### 8.1 部署环境

| 配置项 | 值 |
|--------|-----|
| 操作系统 | Linux（CentOS/Ubuntu） |
| 部署方式 | systemd 守护进程 + 手动管理 |
| Python 版本 | 3.11 / 3.13 |
| Python 虚拟环境 | /root/YISIA_Algorithm/venv |
| 项目部署路径 | /root/YISIA_Algorithm/ |
| Node.js 版本 | 推荐 v18+ |

### 8.2 algorithm_services 部署

**管理脚本**：algorithm_services/fastapi_service.sh

| 操作 | 命令 |
|------|------|
| 安装服务 | sudo ./fastapi_service.sh install |
| 启动服务 | sudo ./fastapi_service.sh start |
| 停止服务 | sudo ./fastapi_service.sh stop |
| 重启服务 | sudo ./fastapi_service.sh restart |
| 查看状态 | sudo ./fastapi_service.sh status |
| 卸载服务 | sudo ./fastapi_service.sh uninstall |
| 调试模式 | ./fastapi_service.sh debug |

**systemd 服务配置**：
- 服务文件：/etc/systemd/system/yisia-algorithm.service
- 工作目录：/root/YISIA_Algorithm/algorithm_services
- 启动命令：python -m uvicorn main:app --host 0.0.0.0 --port 6732
- 环境变量：PYTHONPATH=/root/YISIA_Algorithm
- 日志输出：logs/algorithm_service.log（标准输出）、logs/algorithm_service_err.log（错误输出）
- 重启策略：Restart=always, RestartSec=5

### 8.3 frontend_services 部署

**管理脚本**：frontend_services/start_frontend_services.sh

| 操作 | 命令 |
|------|------|
| 安装服务 | sudo ./start_frontend_services.sh install |
| 启动服务 | sudo ./start_frontend_services.sh start |
| 停止服务 | sudo ./start_frontend_services.sh stop |
| 重启服务 | sudo ./start_frontend_services.sh restart |
| 查看状态 | sudo ./start_frontend_services.sh status |
| 卸载服务 | sudo ./start_frontend_services.sh uninstall |

**Windows 开发环境**：双击 start_frontend_services.bat 或在命令行运行

**systemd 服务配置**：
- 服务文件：/etc/systemd/system/yisia-frontend.service
- 工作目录：/root/YISIA_Algorithm/frontend_services
- 启动命令：node server.js
- 环境变量：NODE_ENV=production
- 重启策略：Restart=always, RestartSec=3

### 8.4 knowledge_base_service 部署

**部署方式**：手动管理（无 systemd 服务）

**启动命令**：
```bash
cd /root/YISIA_Algorithm/knowledge_base_service
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8002
```

**建议**：生产环境应为其创建 systemd 服务，参考 algorithm_services 的脚本格式

### 8.5 依赖安装

**Python 依赖**：
```bash
pip install fastapi uvicorn httpx requests pydantic python-dotenv numpy
```

**Node.js 依赖**：
```bash
cd frontend_services
npm install
```

### 8.6 日志管理

**algorithm_services 应用日志**：
- 日志文件：algorithm_services/logs/YISIA.log
- 日志级别：控制台 INFO，文件 DEBUG
- 日志格式：2026-05-07 12:00:00 - YISIA - INFO - [session:xxx] [user:xxx] 内容
- 日志切分：每天午夜切分，保留 7 天
- 日志系统：全局单例 Logger（YISIA），通过 ContextVar 关联 session_id 和 user_id

**查看日志**：
```bash
# 应用日志
tail -f /root/YISIA_Algorithm/algorithm_services/logs/YISIA.log

# 服务日志
tail -f /root/YISIA_Algorithm/algorithm_services/logs/algorithm_service.log
tail -f /root/YISIA_Algorithm/algorithm_services/logs/algorithm_service_err.log

# systemd 日志
journalctl -u yisia-algorithm -f
journalctl -u yisia-frontend -f
```

### 8.7 常用运维命令

**端口检查**：
```bash
lsof -i:6732  # algorithm_services
lsof -i:8002  # knowledge_base_service
lsof -i:3000  # frontend_services
```

**服务状态**：
```bash
systemctl status yisia-algorithm
systemctl status yisia-frontend
```

**开发调试**：
```bash
# algorithm_services 调试模式（热重载）
cd /root/YISIA_Algorithm/algorithm_services
source /root/YISIA_Algorithm/venv/bin/activate
export PYTHONPATH=/root/YISIA_Algorithm
python -m uvicorn main:app --reload --host 0.0.0.0 --port 6732

# frontend_services 开发模式
cd /root/YISIA_Algorithm/frontend_services
npx nodemon server.js
```

**API 文档**：
- algorithm_services: http://服务器IP:6732/api/docs
- knowledge_base_service: http://服务器IP:8002/docs

---

## 九、核心 API 接口

### 9.1 algorithm_services API（端口 6732，root_path=/chat）

#### 统一入口

**POST /api/v1/entrance** - 聊天机器人主接口（SSE 流式）

请求体：
```json
{
  "session_id": "996",
  "user_id": "996",
  "lang": "zh-CN",
  "stream_flag": true,
  "user_input": "用户输入内容",
  "context": "[{\"user\":\"输入1\",\"response\":\"回答1\"}]",
  "minor_mode": false,
  "personalize": true
}
```

SSE 响应码：
- 102 - 中间过程（AI 思考中）
- 200 - 最终结果
- 300 - 流式打字
- 403 - 违规内容拦截
- 500 - 错误

#### 功能路由

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/dialog-summary/* | POST | 对话摘要 |
| /api/v1/entity-relation-extraction/* | POST | 实体关系联合抽取 |
| /api/v1/free-chat/* | POST | 闲聊 |
| /api/v1/function-planner/* | POST | 功能规划器 |
| /api/v1/intent-clarify/* | POST | 意图澄清 |
| /api/v1/intent-recognize/* | POST | 意图识别 |
| /api/v1/text-summary/* | POST | 文本摘要 |
| /api/v1/title-generation/* | POST | 标题生成 |
| /api/v1/content-moderation/* | POST | 内容审核 |
| /api/v1/llm-web-search/* | POST | LLM 联网搜索 |
| /api/v1/user-style/* | POST | 用户风格学习 |
| /api/v1/user-knowledge-graph/* | POST | 用户知识图谱 |

#### 监控指标

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/metrics/hourly | GET | 小时级统计 |
| /api/v1/metrics/realtime | GET | 实时统计 |
| /api/v1/metrics/daily/{days} | GET | N 天统计 |
| /api/v1/metrics/model-key/{days} | GET | 模型和 Key 使用统计 |

#### 系统端点

| 接口 | 方法 | 说明 |
|------|------|------|
| /health | GET | 健康检查 |
| /admin | GET | 监控仪表盘页面 |
| /api/docs | GET | Swagger API 文档 |

### 9.2 knowledge_base_service API（端口 8002）

#### 知识搜索

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/knowledge/search | POST | 知识搜索（hybrid/vector/graph/keyword） |
| /api/v1/knowledge/list_all | GET | 分页获取全量数据 |
| /api/v1/knowledge/list_products | GET | 获取全部产品 |
| /api/v1/knowledge/list_entries | GET | 获取全部知识条目 |
| /api/v1/knowledge/product/{id} | GET | 获取单个产品 |
| /api/v1/knowledge/entry/{id} | GET | 获取单个知识条目 |
| /api/v1/knowledge/add_product | POST | 添加产品 |
| /api/v1/knowledge/add_knowledge | POST | 添加知识条目 |
| /api/v1/knowledge/import | POST | 批量导入（JSON/CSV/MD） |
| /api/v1/knowledge/product/{id} | PUT | 更新产品 |
| /api/v1/knowledge/product/{id} | DELETE | 删除产品 |
| /api/v1/knowledge/entry/{id} | PUT | 更新知识条目 |
| /api/v1/knowledge/entry/{id} | DELETE | 删除知识条目 |
| /api/v1/knowledge/index_status | GET | 向量索引状态 |
| /api/v1/knowledge/cache_stats | GET | 缓存统计 |
| /api/v1/knowledge/clear_cache | POST | 清除缓存 |

#### RAG 检索

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/rag/query | POST | RAG 统一查询 |
| /api/v1/rag/documents | POST | 添加文档 |
| /api/v1/rag/stats | GET | 知识库统计 |
| /api/v1/rag/build-ann-index | POST | 构建 ANN 索引 |
| /api/v1/rag/ann-stats | GET | ANN 索引统计 |

#### 知识图谱

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/graph/* | POST | 图谱相关路由 |

#### 系统端点

| 接口 | 方法 | 说明 |
|------|------|------|
| /health | GET | 健康检查 |
| /docs | GET | Swagger API 文档 |
| /knowledge | GET | 知识管理页面 |
| /graph | GET | 知识图谱可视化页面 |

---

## 十、注意事项与待办事项

### 10.1 安全风险

- ⚠️ aliyun.key（阿里云 RSA 私钥）位于项目根目录，应移至安全位置
- ⚠️ .env 文件中包含实际 API Key，不应提交到版本控制
- ⚠️ 建议将密钥文件加入 .gitignore，使用环境变量或密钥管理服务

### 10.2 缺少依赖锁定文件

- ⚠️ Python 项目没有 requirements.txt 或 pyproject.toml 文件
- ⚠️ 部署时需手动安装依赖，建议补充 requirements.txt

### 10.3 缺少 Docker 化

- ⚠️ 项目未容器化，依赖 systemd 部署
- ⚠️ 建议后续考虑 Docker 化，提升部署灵活性

### 10.4 knowledge_base_service 缺少 systemd 服务

- ⚠️ 知识库服务无 systemd 管理脚本，需手动启动
- ⚠️ 建议参考 algorithm_services/fastapi_service.sh 创建管理脚本

### 10.5 前端无构建工具

- ⚠️ 前端使用原生 JS，无 Webpack/Vite 等构建工具
- ⚠️ index.html 内联了大量 CSS（2300+ 行），建议后续拆分

### 10.6 前端缓存策略

- ⚠️ 所有资源均设置为 no-cache，HTML 文件更是 no-store
- ⚠️ 这是开发阶段的配置，生产环境建议启用缓存

### 10.7 认证后端服务

- ℹ️ 认证后端服务（localhost:8123）不在本项目范围内
- ℹ️ 交接时需确认认证后端服务的部署位置和运维方式

---

## 十一、核心文件索引

### 11.1 入口文件

| 文件 | 说明 |
|------|------|
| algorithm_services/main.py | 算法服务入口 |
| knowledge_base_service/main.py | 知识库服务入口 |
| frontend_services/server.js | 前端服务入口 |
| frontend_services/index.html | SPA 单页应用入口 |

### 11.2 核心业务文件

| 文件 | 说明 |
|------|------|
| algorithm_services/api/routers/main_router.py | 统一入口路由 |
| algorithm_services/core/services/feature_services/ | 功能服务目录 |
| algorithm_services/large_model/llm_factory.py | LLM 工厂 |
| algorithm_services/session/session_factory.py | 会话工厂 |
| algorithm_services/core/moderation/ | 内容审核模块 |
| algorithm_services/core/managers/metrics_manager.py | 指标管理 |
| knowledge_base_service/core/services/knowledge_service.py | 知识服务 |
| knowledge_base_service/core/vector_store/ | 向量存储 |
| knowledge_base_service/core/retrieval/ | 检索模块 |
| knowledge_base_service/core/rerank/ | 重排序模块 |
| knowledge_base_service/core/chunking/ | 文档分块 |
| frontend_services/assets/js/views/chatView.js | 聊天视图（核心） |
| frontend_services/assets/js/views/loginView.js | 登录视图 |
| frontend_services/assets/js/core/stateManager.js | 状态管理 |
| frontend_services/assets/js/api/chatApi.js | 聊天 API |

### 11.3 配置文件

| 文件 | 说明 |
|------|------|
| algorithm_services/config/LLM_API.env | LLM 配置 |
| algorithm_services/config/SESSION.env | 会话配置 |
| algorithm_services/config/KNOWLEDGE.env | 知识库配置 |
| algorithm_services/config/MODERATION.env | 内容审核配置 |
| algorithm_services/config/SCHEDULE.env | 定时任务配置 |
| knowledge_base_service/config/env | 知识库服务配置 |
| frontend_services/assets/js/config/appConfig.js | 前端配置 |

### 11.4 部署脚本

| 文件 | 说明 |
|------|------|
| algorithm_services/fastapi_service.sh | 算法服务管理 |
| frontend_services/start_frontend_services.sh | 前端服务管理（Linux） |
| frontend_services/start_frontend_services.bat | 前端服务管理（Windows） |

---

## 十二、开发计划

- [ ] 补充 Python 依赖锁定文件（requirements.txt / pyproject.toml）
- [ ] Docker 化部署
- [ ] 为 knowledge_base_service 创建 systemd 服务脚本
- [ ] 前端构建工具集成（Webpack/Vite）
- [ ] 前端 CSS 拆分与优化
- [ ] 生产环境缓存策略配置
- [ ] 自动化测试覆盖

---

## 附录：项目信息

- **项目名称**：YISIA（Lansee Chatbot）
- **项目定位**：医美领域 AI 智能对话系统
- **开发者**：马赫·马智勇（大模型算法工程师）
- **创建日期**：2026-04-16
- **最后更新**：2026-05-07

---

**YISIA** - 让每一次对话都成为美丽的开始 ✨