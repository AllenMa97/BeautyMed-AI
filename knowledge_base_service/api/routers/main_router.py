# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
主路由 - 统一入口
"""
from fastapi import APIRouter
from api.routers import knowledge_router, rag_router, graph_visualization_router, graph_rag_router

main_router = APIRouter(prefix="/api/v1")

main_router.include_router(knowledge_router.router)
main_router.include_router(rag_router.router)
main_router.include_router(graph_visualization_router.router)
main_router.include_router(graph_rag_router.router)
