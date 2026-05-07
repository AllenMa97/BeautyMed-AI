# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
import os
import asyncio
import datetime
from typing import Dict, Any, AsyncGenerator, Optional
from algorithm_services.core.tools.tool_registry import ToolRegistry
from pydantic import BaseModel

from algorithm_services.core.services.feature_services import (
    dialog_summary_service,
    entity_relation_extraction_service,
    free_chat_service,
    intent_clarify_service,
    intent_recognize_service,
    text_summary_service,
)
from algorithm_services.core.services.feature_services import recommendation_service
from algorithm_services.core.services.feature_services import image_understanding_service
from algorithm_services.core.services.feature_services import memory_recall_service
from algorithm_services.core.services.feature_services import emotion_recognition_service
from algorithm_services.core.services.feature_services import knowledge_retrieval_service
from algorithm_services.core.services.feature_services import knowledge_chat_service

from algorithm_services.api.schemas.feature_schemas import (
    dialog_summary_schema,
    entity_relation_extraction_schemas,
    free_chat_schemas,
    intent_clarify_schemas,
    intent_recognize_schemas,
    text_summary_schemas,
    recommendation_schemas,
    image_understanding_schemas,
    memory_recall_schemas,
    emotion_recognition_schemas,
    knowledge_retrieval_schemas,
    knowledge_chat_schemas,
)

from algorithm_services.session.session_factory import session_manager

from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


AIPOSIT_GAGALIN_DELICK_CONSTANT = float(os.getenv("AIPOSIT_GAGALIN_DELICK_CONSTANT", 1))


class FunctionExecuterService:
    """执行器Service"""
    def __init__(self):
        self.feature_services: Dict[str, Any] = {
            "dialog_summary": dialog_summary_service.DialogSummaryService(),
            "entity_relation_extraction": entity_relation_extraction_service.EntityRelationExtractionService(),
            "free_chat": free_chat_service.FreeChatService(),
            "intent_clarify": intent_clarify_service.IntentClarifyService(),
            "intent_recognize": intent_recognize_service.IntentRecognizeService(),
            "text_summary": text_summary_service.TextSummaryService(),
            "recommendation": recommendation_service.RecommendationService(),
            "image_understanding": image_understanding_service.ImageUnderstandingService(),
            "memory_recall": memory_recall_service.MemoryRecallService(),
            "emotion_recognition": emotion_recognition_service.EmotionRecognitionService(),
            "knowledge_retrieval": knowledge_retrieval_service.KnowledgeRetrievalService(),
            "knowledge_chat": knowledge_chat_service.KnowledgeChatService(),
        }
        
        self.FUNC_REQUEST_MAP = {
            "dialog_summary": dialog_summary_schema.DialogSummaryRequest,
            "entity_relation_extraction": entity_relation_extraction_schemas.EntityRelationExtractionRequest,
            "free_chat": free_chat_schemas.FreeChatRequest,
            "intent_clarify": intent_clarify_schemas.IntentClarifyRequest,
            "intent_recognize": intent_recognize_schemas.IntentRecognizeRequest,
            "text_summary": text_summary_schemas.TextSummaryRequest,
            "recommendation": recommendation_schemas.RecommendationRequest,
            "image_understanding": image_understanding_schemas.ImageUnderstandingRequest,
            "memory_recall": memory_recall_schemas.MemoryRecallRequest,
            "emotion_recognition": emotion_recognition_schemas.EmotionRecognitionRequest,
            "knowledge_retrieval": knowledge_retrieval_schemas.KnowledgeRetrievalRequest,
            "knowledge_chat": knowledge_chat_schemas.KnowledgeChatRequest,
        }
        
        self._register_mcp_tools()

    def build_request_object(self, func_name: str, params: dict) -> object:
        if func_name not in self.FUNC_REQUEST_MAP:
            raise ValueError(f"未找到功能{func_name}对应的Request类")

        request_cls = self.FUNC_REQUEST_MAP[func_name]
        return request_cls(**params)

    def _register_mcp_tools(self):
        for func_name, service in self.feature_services.items():
            description = getattr(service, "description", f"执行 {func_name}")
            schema_class = self.FUNC_REQUEST_MAP.get(func_name)
            if schema_class:
                ToolRegistry.register(func_name, description, schema_class)
        
        logger.info(f"MCP 工具注册完成，共 {len(ToolRegistry.get_all_tools())} 个工具")

    async def execute_feature(
            self,
            func_name: str,
            params: Dict[str, Any],
            session
    ) -> Dict[str, Any]:
        result: Optional[Any] = None
        try:
            service = self.feature_services[func_name]
            
            if func_name == "intent_clarify":
                recognized_intent = ""
                if getattr(session, 'recognized_first_level_intent', None):
                    recognized_intent = session.recognized_first_level_intent
                if getattr(session, 'intent', None):
                    recognized_intent = f"{recognized_intent}|{session.intent}" if recognized_intent else session.intent
                
                params["recognized_intent"] = recognized_intent
                params["recognized_entities"] = json.dumps(session.entities) if getattr(session, 'entities', None) else "[]"

            if func_name == "knowledge_chat":
                if hasattr(session, 'intermediate_results') and 'knowledge_retrieval' in session.intermediate_results:
                    params["data"] = session.intermediate_results['knowledge_retrieval']

            req_obj = self.build_request_object(func_name, params)
        except ValueError as e:
            error_msg = f"构建{func_name}的Request对象失败：{str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        try:
            func_method_map = {
                "dialog_summary": "generate_dialog_summary",
                "entity_relation_extraction": "extract",
                "free_chat": "chat",
                "intent_clarify": "clarify",
                "intent_recognize": "recognize",
                "text_summary": "generate",
                "knowledge_retrieval": "retrieve",
                "knowledge_chat": "chat",
                "product_recommendation": "recommend",
            }
            method_name = func_method_map.get(func_name, "recognize")
            method = getattr(service, method_name)
            result = await method(req_obj)
            logger.info(f"执行功能：{method_name}成功，参数：{req_obj}，结果：{result}")
            
            if hasattr(session, 'intermediate_results'):
                result_dict = result.dict() if hasattr(result, 'dict') else result
                session.intermediate_results[func_name] = result_dict
                await session_manager.update_session(session.session_id, intermediate_results=session.intermediate_results)
            
            return result_dict

        except Exception as e:
            error_msg = f"执行功能{func_name}失败：{str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def stream_execute_feature(
            self,
            func_name: str,
            params: Dict[str, Any],
            session
    ) -> AsyncGenerator[str, None]:
        result: Optional[Any] = None
        try:
            service = self.feature_services[func_name]
            
            if func_name == "knowledge_chat":
                if hasattr(session, 'intermediate_results') and 'knowledge_retrieval' in session.intermediate_results:
                    params["data"] = session.intermediate_results['knowledge_retrieval']
            
            req_obj = self.build_request_object(func_name, params)
            func_method_map = {
                "dialog_summary": "generate_dialog_summary",
                "entity_relation_extraction": "extract",
                "free_chat": "chat",
                "intent_clarify": "clarify",
                "intent_recognize": "recognize",
                "text_summary": "generate",
                "knowledge_retrieval": "retrieve",
                "knowledge_chat": "chat",
            }
            method_name = func_method_map.get(func_name, "recognize")
            method = getattr(service, method_name)
            yield f"🚀 [开始执行] 功能：{func_name}\n"
            await asyncio.sleep(0.1 * AIPOSIT_GAGALIN_DELICK_CONSTANT)

            if not hasattr(method, "__aiter__"):
                result = await method(req_obj)
                if result is None:
                    yield f"🎯 [执行完成] 功能：{func_name}，结果：无返回值\n"
                elif isinstance(result, BaseModel):
                    result_dict = result.dict()
                    yield f"🎯 [执行完成] 功能：{func_name}，结果：{result_dict}\n"
                    if hasattr(session, 'intermediate_results'):
                        session.intermediate_results[func_name] = result_dict
                        await session_manager.update_session(session.session_id, intermediate_results=session.intermediate_results)
                else:
                    yield f"🎯 [执行完成] 功能：{func_name}，结果：{str(result)}\n"
                    if hasattr(session, 'intermediate_results'):
                        session.intermediate_results[func_name] = result
                        await session_manager.update_session(session.session_id, intermediate_results=session.intermediate_results)
            else:
                async for chunk in method(req_obj, stream=True):
                    yield f"❌ [{func_name}] {chunk}\n"
                    await asyncio.sleep(0.05 * AIPOSIT_GAGALIN_DELICK_CONSTANT)
                yield f"🎯 [执行完成] 功能：{func_name}\n"

        except ValueError as e:
            error_msg = f"构建{func_name}的Request对象失败：{str(e)}"
            logger.error(error_msg)
            yield f"❌ [错误] {error_msg}\n"
        except Exception as e:
            error_msg = f"执行功能{func_name}失败：{str(e)}"
            logger.error(error_msg)
            yield f"❌ [错误] {error_msg}\n"

    async def update_session_from_feature(self, func_name: str, result: Dict[str, Any], session):
        current_turn = getattr(session, 'current_turn', None)
        
        if not isinstance(result, dict):
            logger.warning(f"功能{func_name}结果非字典类型，跳过会话更新：{type(result)}")
            return
        if result.get('code') == 500 or "error" in result.get('msg', ''):
            logger.warning(f"功能{func_name}执行失败，跳过会话更新")
            return
        
        try:
            data = result.get('data', {})
            if not data:
                logger.debug(f"功能{func_name}无数据返回，跳过会话更新")
                return
            
            if session.session_data is None:
                session.session_data = {}
            
            if func_name == "intent_recognize":
                if 'intent' in data:
                    session.session_data['intent'] = {
                        'intent': data.get('intent'),
                        'confidence': data.get('confidence', 0.0),
                        'timestamp': datetime.datetime.now().timestamp()
                    }
                    if current_turn:
                        current_turn.user_query_intent = data.get('intent')
                        current_turn.user_query_intent_confidence = data.get('confidence', 0.0)
                    logger.info(f"意图识别结果已更新到 session_data: {data.get('intent')}")
                
                if 'entities' in data and data['entities']:
                    session.session_data['entities'] = data['entities']
                    if current_turn:
                        current_turn.user_query_entities = data['entities']
                    for entity_type, entity_value in data['entities'].items():
                        if entity_value:
                            if entity_type not in session.user_profile:
                                session.user_profile[entity_type] = []
                            if entity_value not in session.user_profile[entity_type]:
                                session.user_profile[entity_type].append(entity_value)
                    logger.info(f"实体识别结果已更新到 session_data 和 user_profile: {data['entities']}")
            
            elif func_name == "entity_relation_extraction":
                if 'entities' in data and data['entities']:
                    session.session_data['entities'] = data['entities']
                    entities = data['entities']
                    if isinstance(entities, list):
                        for entity in entities:
                            if isinstance(entity, dict):
                                entity_type = entity.get('entity_type', 'unknown')
                                entity_name = entity.get('entity_name', '')
                                if entity_type and entity_name:
                                    if entity_type not in session.user_profile:
                                        session.user_profile[entity_type] = []
                                    if entity_name not in session.user_profile[entity_type]:
                                        session.user_profile[entity_type].append(entity_name)
                    elif isinstance(entities, dict):
                        for entity_type, entity_value in entities.items():
                            if entity_value:
                                if entity_type not in session.user_profile:
                                    session.user_profile[entity_type] = []
                                if isinstance(entity_value, list):
                                    for val in entity_value:
                                        if val not in session.user_profile[entity_type]:
                                            session.user_profile[entity_type].append(val)
                                elif entity_value not in session.user_profile[entity_type]:
                                    session.user_profile[entity_type].append(entity_value)
                    logger.info(f"实体识别结果已更新到 session_data 和 user_profile: {data['entities']}")

                if 'relations' in data and data['relations']:
                    session.session_data['relations'] = data['relations']
                    logger.info(f"关系抽取结果已更新到 session_data: {data['relations']}")
            
            elif func_name == "dialog_summary":
                if 'dialog_summary' in data:
                    session.dialog_summary = data['dialog_summary']
                    logger.info(f"对话摘要已更新：{data['dialog_summary'][:50]}...")
            
            else:
                session.intermediate_results[func_name] = data
                logger.info(f"功能{func_name}结果已更新到 intermediate_results")
            
            await session_manager.update_session(session.session_id, 
                                               session_data=session.session_data,
                                               user_profile=session.user_profile,
                                               dialog_summary=session.dialog_summary,
                                               intermediate_results=session.intermediate_results)
            
        except Exception as e:
            logger.error(f"更新会话状态失败：{e}", exc_info=True)
