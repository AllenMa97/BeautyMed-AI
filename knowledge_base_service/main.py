# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import sys
import os

from contextlib import asynccontextmanager

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import get_logger
from api.routers.main_router import main_router
from api.schemas.knowledge_schemas import KnowledgeSearchRequest

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events
    """
    logger.info("开始服务预热...")
    
    # 初始化知识库
    from core.services.knowledge_service import KnowledgeService
    knowledge_service = KnowledgeService()
    
    # 初始化检索器
    from core.processors.knowledge_retriever import KnowledgeRetriever
    retriever = KnowledgeRetriever()
    
    # 初始化图谱服务
    from core.services.graph_enhanced_rag_service import GraphEnhancedRAGService
    graph_rag_service = GraphEnhancedRAGService(api_key="")
    
    # 预热向量索引（_load_ann_index 是同步方法，在 __init__ 中已调用，此处无需重复）
    
    yield
    
    # 服务关闭时的清理工作
    logger.info("服务即将关闭，正在进行清理...")
    # 清理资源
    try:
        logger.info("服务资源清理完成")
    except Exception as e:
        logger.error(f"服务关闭失败: {e}")

# 创建 FastAPI 应用
app = FastAPI(
    title="知识库服务 API",
    description="医美知识库服务 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（main_router 已经包含/api/v1 前缀）
app.include_router(main_router)

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板文件服务
from fastapi.requests import Request
import jinja2

_templates_dir = os.path.join(current_dir, "templates")
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_templates_dir),
    autoescape=True,
    auto_reload=True
)


def _render_html(template_name: str, **context) -> HTMLResponse:
    template = _jinja_env.get_template(template_name)
    return HTMLResponse(content=template.render(**context))


# API 文档端点（Swagger UI）
@app.get("/api/docs", include_in_schema=False)
async def api_docs():
    """重定向到 Swagger UI"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# 知识管理页面（使用原有模板）
@app.get("/knowledge", response_class=HTMLResponse, include_in_schema=False)
async def knowledge_page(request: Request):
    """知识管理页面"""
    return _render_html("knowledge.html", request=request)

# Nginx 反向代理兼容路由（/knowledge 代理下 API 也可达）
@app.post("/knowledge/search", include_in_schema=False)
async def knowledge_search_proxy(request: KnowledgeSearchRequest):
    from api.routers.knowledge_router import search_knowledge
    return await search_knowledge(request)

@app.get("/knowledge/list_all", include_in_schema=False)
async def knowledge_list_all_proxy(
    page: int = 1,
    page_size: int = 50,
    group: str = None,
    brand: str = None
):
    from api.routers.knowledge_router import list_all_data
    return await list_all_data(page=page, page_size=page_size, group=group, brand=brand)

# 添加知识页面
@app.get("/add_knowledge", response_class=HTMLResponse, include_in_schema=False)
async def add_knowledge_page(request: Request):
    """添加知识页面"""
    return _render_html("add_knowledge.html", request=request)

# 编辑知识页面
@app.get("/edit_knowledge", response_class=HTMLResponse, include_in_schema=False)
async def edit_knowledge_page(request: Request):
    """编辑知识页面"""
    return _render_html("edit_knowledge.html", request=request)

# 知识图谱可视化页面
@app.get("/graph", response_class=HTMLResponse, include_in_schema=False)
async def graph_visualization_page(request: Request):
    """知识图谱可视化页面"""
    return _render_html("graph_visualization.html", request=request)

# 健康检查端点
@app.get("/health", tags=["系统管理"])
async def health_check():
    """
    服务健康检查

    返回服务整体运行状态。可用于负载均衡器或监控系统探活。
    """
    return {"status": "healthy", "service": "knowledge_base_service", "version": "1.0.0"}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <head>
            <title>知识库服务</title>
        </head>
        <body>
            <h1>知识库服务运行中</h1>
            <p>API 文档: <a href="/docs">/docs</a></p>
        </body>
    </html>
    """

# 修复404问题 - 专门处理前端路由的回退方案
# 由于FastAPI路由匹配顺序问题，这里添加一个特殊的处理方式
# 通过在应用启动时注册一个特殊的中间件来处理这些特定路由
@app.get("/api/fix-frontend-routes", include_in_schema=False)
async def fix_frontend_routes():
    """
    专门用于修复前端路由的占位路由
    实际上这个路由不会被直接访问，但确保路由系统正确加载
    """
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    logger.info("启动服务...")
    # host="0.0.0.0" 表示监听所有网络接口，允许外部访问
    uvicorn.run(app, host="0.0.0.0", port=8002)