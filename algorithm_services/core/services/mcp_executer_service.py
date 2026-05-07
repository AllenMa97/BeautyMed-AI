"""
MCP 风格的执行器
动态发现 Service，无需手动注册
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import Dict, Any, Optional
from algorithm_services.utils.logger import get_logger
from algorithm_services.core.tools.tool_registry import ToolRegistry
from algorithm_services.session.session_factory import session_manager
from algorithm_services.core.services.feature_services import (
    dialog_summary_service,
    entity_relation_extraction_service,
    free_chat_service,
    intent_clarify_service,
    intent_recognize_service,
    text_summary_service,
    recommendation_service,
    image_understanding_service,
    memory_recall_service,
    emotion_recognition_service,
    knowledge_retrieval_service,
    knowledge_chat_service,
)

logger = get_logger(__name__)


class MCPExecuterService:
    """
    MCP 风格的执行器
    通过 ToolRegistry 动态发现并执行工具
    """
    
    # Service 类名到实例的映射（需要预先导入）
    SERVICE_CLASSES = {}
    
    def __init__(self):
        self._init_service_classes()
        logger.info("MCP Executer 初始化完成")
    
    def _init_service_classes(self):
        """动态导入并注册所有 Service 类"""
        self.SERVICE_CLASSES = {
            "dialog_summary": dialog_summary_service.DialogSummaryService,
            "entity_relation_extraction": entity_relation_extraction_service.EntityRelationExtractionService,
            "free_chat": free_chat_service.FreeChatService,
            "intent_clarify": intent_clarify_service.IntentClarifyService,
            "intent_recognize": intent_recognize_service.IntentRecognizeService,
            "text_summary": text_summary_service.TextSummaryService,
            "recommendation": recommendation_service.RecommendationService,
            "image_understanding": image_understanding_service.ImageUnderstandingService,
            "memory_recall": memory_recall_service.MemoryRecallService,
            "emotion_recognition": emotion_recognition_service.EmotionRecognitionService,
            "knowledge_retrieval": knowledge_retrieval_service.KnowledgeRetrievalService,
            "knowledge_chat": knowledge_chat_service.KnowledgeChatService,
        }
        
        for name, cls in self.SERVICE_CLASSES.items():
            tool_info = ToolRegistry.get_tool(name)
            if tool_info is None:
                logger.warning(f"Service {name} 未在 ToolRegistry 中注册")
    
    def get_service_instance(self, func_name: str):
        """动态获取 Service 实例"""
        cls = self.SERVICE_CLASSES.get(func_name)
        if cls is None:
            raise ValueError(f"未找到 Service: {func_name}")
        return cls()
    
    async def execute(self, func_name: str, params: Dict[str, Any], session) -> Dict[str, Any]:
        """
        执行单个功能（动态发现）
        """
        tool_info = ToolRegistry.get_tool(func_name)
        if tool_info is None:
            raise ValueError(f"未注册的工具: {func_name}")
        
        schema_class = tool_info["schema_class"]
        
        try:
            req_obj = schema_class(**params)
        except Exception as e:
            logger.error(f"构建请求对象失败: {e}")
            raise
        
        service = self.get_service_instance(func_name)
        
        method_map = {
            "dialog_summary": "generate_dialog_summary",
            "entity_relation_extraction": "extract",
            "free_chat": "chat",
            "intent_clarify": "clarify",
            "intent_recognize": "recognize",
            "text_summary": "generate",
            "recommendation": "recommend",
            "image_understanding": "understand",
            "memory_recall": "recall",
            "emotion_recognition": "recognize",
            "knowledge_retrieval": "retrieve",
            "knowledge_chat": "chat",
        }
        
        method_name = method_map.get(func_name, "execute")
        method = getattr(service, method_name, None)
        
        if method is None:
            raise ValueError(f"Service {func_name} 没有方法: {method_name}")
        
        result = await method(req_obj)
        
        if hasattr(result, "dict"):
            return result.dict()
        elif hasattr(result, "data"):
            return {"data": result.data} if hasattr(result.data, "dict") else {"data": str(result.data)}
        else:
            return {"data": str(result)}


mcp_executer_service = MCPExecuterService()
