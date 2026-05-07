# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import httpx

from algorithm_services.api.routers.main_router import main_router
from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton
from algorithm_services.api.routers.feature_routers import (
    dialog_summary_router,
    entity_relation_extraction_router,
    free_chat_router,
    function_planner_router,
    intent_clarify_router,
    intent_recognize_router,
    text_summary_router,
    title_generation_router,
    content_moderation_router,
    llm_web_search_router,
    user_style_router,
    user_knowledge_graph_router,
)
from algorithm_services.api.routers.metrics_router import router as metrics_router
from algorithm_services.core.services.system_initializer import initialize_basic_services, shutdown_basic_services
from algorithm_services.core.managers.metrics_manager import metrics_manager

logger = get_logger(__name__)

API_DESCRIPTION = """
## YISIA 算法服务 API

### 系统架构流程图

```
用户输入 (user_input)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤1: 快速短路检测 (词表匹配)                                    │
│  检测简单问候/确认/感谢等 → is_simple = True                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤2: 路由决策 (routing_decision_service)                       │
│  输出: need_plan, need_search                                    │
│  同时启动: 内容违规检测 (异步并行)                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ├── need_plan = False ────────────────────┐
    │                                          ▼
    │                              ┌─────────────────────┐
    │                              │  free_chat (兜底)   │
    │                              └─────────────────────┘
    │
    └── need_plan = True ─────────────────────┐
                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤3: 功能规划 (planner)                                        │
│  决定调用: knowledge_retrieval / 等                              │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤4: 执行功能 (function_executer_service)                      │
│  结果存入 session.intermediate_results                           │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤5: 自动选择 Chat 方式                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  有 knowledge_retrieval 结果 → knowledge_chat            │    │
│  │  无 knowledge_retrieval 结果 → free_chat (兜底)          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  步骤6: 返回结果 (SSE 流式输出)                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 职责划分

| 服务 | 职责 |
|------|------|
| routing_decision_service | 快速分流: need_plan, need_search |
| planner | 功能规划: 决定调用哪些功能 |
| function_executer_service | 执行功能: 按顺序执行规划的功能 |
| 自动路由 (步骤5) | 根据 knowledge_retrieval 结果选择 chat |

### 关键设计原则

1. **知识检索 → 知识问答** - 有结果用 knowledge_chat，无结果用 free_chat
2. **异步并行** - 内容违规检测与规划流程并行执行
3. **快速路径** - 简单问题直接走 free_chat，跳过 planner
"""

@asynccontextmanager
async def lifespan(app):
    initialize_basic_services()
    metrics_manager.start_hourly_timer()
    logger.info("YISIA （算法侧API）启动成功")
    yield
    await llm_client_singleton.close()
    metrics_manager.stop_timer()
    shutdown_basic_services()
    logger.info("YISIA （算法侧API）已关闭")


app = FastAPI(
    title="Lansee Chatbot (Algorithm API)",
    description=API_DESCRIPTION,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    root_path="/chat"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# 注册路由（按业务模块分组，统一加版本前缀）
app.include_router(main_router)
app.include_router(dialog_summary_router.router)  # 对话摘要路由
app.include_router(entity_relation_extraction_router.router)
app.include_router(free_chat_router.router)
app.include_router(function_planner_router.router)
app.include_router(intent_clarify_router.router)
app.include_router(intent_recognize_router.router)
app.include_router(text_summary_router.router)
app.include_router(title_generation_router.router)
app.include_router(content_moderation_router.router)  # 内容检测路由
app.include_router(llm_web_search_router.router)  # LLM联网搜索路由
app.include_router(user_style_router.router)  # 用户风格学习路由
app.include_router(user_knowledge_graph_router.router)  # 用户知识图谱路由
app.include_router(metrics_router)

AUTH_BACKEND_URL = "http://localhost:8123"


@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def auth_proxy(path: str, request: Request):
    target_url = f"{AUTH_BACKEND_URL}/internal-api/auth/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers={
                k: v for k, v in request.headers.items()
                if k.lower() not in ("host", "content-length")
            }
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={
            k: v for k, v in resp.headers.items()
            if k.lower() not in ("content-encoding", "transfer-encoding", "content-length")
        }
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 监控面板页面
@app.get("/admin")
async def admin_page():
    admin_path = os.path.join(os.path.dirname(__file__), "admin", "dashboard.html")
    return FileResponse(admin_path)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=6732,
        reload=False,
        log_level="info"
    )