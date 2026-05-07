"""
知识问答服务
基于检索到的知识和产品信息生成专业回答
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
from dotenv import load_dotenv
from algorithm_services.api.schemas.feature_schemas.knowledge_chat_schemas import (
    KnowledgeChatRequest,
    KnowledgeChatResponse,
    KnowledgeChatData,
)
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.core.prompts.features.knowledge_chat_prompt import KnowledgeChatPrompt
from algorithm_services.utils.logger import get_logger
from algorithm_services.utils.performance_monitor import monitor_async
from typing import AsyncGenerator
import json

logger = get_logger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../config/KNOWLEDGE.env"))

DEFAULT_PROVIDER = os.getenv("LLM_DEFAULT_PROVIDER", "aliyun")
DEFAULT_MODEL = os.getenv("ALIYUN_DEFAULT_MODEL", "qwen-plus")

LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 8192


class KnowledgeChatService:
    """知识问答服务"""
    description = "知识问答，基于检索到的知识生成专业回答"
    
    @monitor_async(name="knowledge_chat_chat", log_threshold=2.0)
    async def chat(self, request: KnowledgeChatRequest) -> KnowledgeChatResponse:
        """
        知识问答服务
        
        从 request.data 中读取 knowledge_retrieval 的结果
        构建 Prompt 调用 LLM 生成回答
        """
        try:
            retrieval_data = request.data or {}
            
            if "data" in retrieval_data:
                retrieval_data = retrieval_data.get("data", {})
            
            products = retrieval_data.get("products", [])
            entries = retrieval_data.get("entries", [])
            chunks = retrieval_data.get("chunks", [])
            
            has_knowledge = bool(products or entries)

            # 即使没有检索到知识，也调用大模型生成一般性回答
            if not has_knowledge:
                user_prompt = f"用户问题：{request.user_input}\n\n虽然暂时没有检索到相关的专业知识，但请基于你自己的知识，用温暖亲切的语气为用户提供有用的建议。如果问题涉及医美领域，请给出专业的通用建议。"
                
                minor_mode = getattr(request, 'minor_mode', False)
                llm_request = LLMRequest(
                    system_prompt=KnowledgeChatPrompt.get_system_prompt(minor_mode=minor_mode),
                    user_prompt=user_prompt,
                    temperature=LLM_TEMPERATURE,
                    max_tokens=LLM_MAX_TOKENS,
                    provider=DEFAULT_PROVIDER,
                    model=DEFAULT_MODEL,
                )
                
                result = await llm_client_singleton.call_llm(llm_request)
                
                answer = result.get("answer", "") if isinstance(result, dict) else str(result)
                
                return KnowledgeChatResponse(
                    code=200,
                    msg="基于通用知识的回答",
                    data=KnowledgeChatData(
                        answer=answer,
                        sources=[],
                        confidence=0.5,
                        has_knowledge=False,
                    )
                )
            
            user_prompt = KnowledgeChatPrompt.build_user_prompt(
                user_input=request.user_input,
                products=products,
                entries=entries,
                context=request.context,
                personalize=getattr(request, 'personalize', True),
            )
            
            minor_mode = getattr(request, 'minor_mode', False)
            llm_request = LLMRequest(
                system_prompt=KnowledgeChatPrompt.get_system_prompt(minor_mode=minor_mode),
                user_prompt=user_prompt,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                provider=DEFAULT_PROVIDER,
                model=DEFAULT_MODEL,
            )
            
            result = await llm_client_singleton.call_llm(llm_request)
            
            answer = result.get("answer", "") if isinstance(result, dict) else str(result)
            
            sources = []
            for product in products[:3]:
                source = f"产品：{product.get('name', '')} ({product.get('brand', '')})"
                if source not in sources:
                    sources.append(source)
            
            for entry in entries[:3]:
                source = f"知识：{entry.get('title', '')}"
                if source not in sources:
                    sources.append(source)
            
            for chunk in chunks[:3]:
                source = chunk.get("metadata", {}).get("source", "")
                if source and source not in sources:
                    sources.append(source)
            
            return KnowledgeChatResponse(
                code=200,
                msg="知识问答成功",
                data=KnowledgeChatData(
                    answer=answer,
                    sources=sources,
                    confidence=0.8 if has_knowledge else 0.0,
                    has_knowledge=has_knowledge,
                )
            )
            
        except Exception as e:
            logger.error(f"知识问答失败: {str(e)}", exc_info=True)
            return KnowledgeChatResponse(
                code=500,
                msg=f"知识问答失败: {str(e)}",
                data=KnowledgeChatData(
                    answer="",
                    sources=[],
                    confidence=0.0,
                    has_knowledge=False,
                )
            )
    
    @monitor_async(name="knowledge_chat_stream", log_threshold=2.0)
    async def stream_chat(self, request: KnowledgeChatRequest) -> AsyncGenerator[str, None]:
        """
        流式知识问答服务
        直接返回原始 chunk，由 function_planner_service 统一包装
        """
        try:
            retrieval_data = request.data or {}
            
            if "data" in retrieval_data:
                retrieval_data = retrieval_data.get("data", {})
            
            products = retrieval_data.get("products", [])
            entries = retrieval_data.get("entries", [])
            # chunks = retrieval_data.get("chunks", [])
            
            has_knowledge = bool(products or entries)

            # 即使没有检索到知识，也调用大模型生成一般性回答
            if not has_knowledge:
                user_prompt = f"用户问题：{request.user_input}\n\n虽然暂时没有检索到相关的专业知识，但请基于你自己的知识，用温暖亲切的语气为用户提供有用的建议。如果问题涉及医美领域，请给出专业的通用建议。"
                
                minor_mode = getattr(request, 'minor_mode', False)
                llm_request = LLMRequest(
                    system_prompt=KnowledgeChatPrompt.get_system_prompt(minor_mode=minor_mode),
                    user_prompt=user_prompt,
                    temperature=LLM_TEMPERATURE,
                    max_tokens=LLM_MAX_TOKENS,
                    provider=DEFAULT_PROVIDER,
                    model=DEFAULT_MODEL,
                    stream=True,
                )
                
                async for chunk in llm_client_singleton.call_llm_stream(llm_request):
                    yield chunk
                
                yield json.dumps({
                    "sources": [],
                    "has_knowledge": False
                }, ensure_ascii=False)
                return
            
            user_prompt = KnowledgeChatPrompt.build_user_prompt(
                user_input=request.user_input,
                products=products,
                entries=entries,
                context=request.context,
                personalize=getattr(request, 'personalize', True),
            )
            
            minor_mode = getattr(request, 'minor_mode', False)
            llm_request = LLMRequest(
                system_prompt=KnowledgeChatPrompt.get_system_prompt(minor_mode=minor_mode),
                user_prompt=user_prompt,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                provider=DEFAULT_PROVIDER,
                model=DEFAULT_MODEL,
                stream=True,
            )
            
            async for chunk in llm_client_singleton.call_llm_stream(llm_request):
                yield chunk
            
            sources = []
            for product in products:
                source = f"产品：{product.get('name', '')} ({product.get('brand', '')})"
                if source not in sources:
                    sources.append(source)
            
            for entry in entries:
                source = f"知识：{entry.get('title', '')}"
                if source not in sources:
                    sources.append(source)
            
            yield json.dumps({
                "sources": sources,
                "has_knowledge": True
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"流式知识问答失败: {str(e)}", exc_info=True)
            yield json.dumps({"error": str(e)}, ensure_ascii=False)


knowledge_chat_service = KnowledgeChatService()
