# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import random
from datetime import datetime

from algorithm_services.utils.logger import get_logger

from algorithm_services.session.session_factory import session_manager

from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest

from algorithm_services.api.schemas.feature_schemas.free_chat_schemas import FreeChatRequest, FreeChatResponse
from algorithm_services.api.schemas.feature_schemas.user_style_schema import StylePromptConfig

from algorithm_services.core.prompts.features.free_chat_prompt import get_yisia_free_chat_prompt
from algorithm_services.core.prompts.features.feature_stage_prompt import apply_feature_stage_to_prompt

from algorithm_services.core.managers.self_evolution_manager import self_evolution_manager

from algorithm_services.utils.time_location import time_location_util
from algorithm_services.utils.trending_topics import trending_topics_util
from algorithm_services.core.services.feature_services.user_profile_service import user_profile_service
from algorithm_services.core.services.feature_services.correction_detection_service import correction_detection_service
from algorithm_services.core.services.context_injection_controller import context_injection_controller
from algorithm_services.core.services.feature_services.user_style_service import user_style_learning_service
from algorithm_services.core.services.feature_services.user_memory_mining_service import user_memory_mining_service



logger = get_logger(__name__)

DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 使用配置文件中的默认模型
LLM_REQUEST_MAX_TOKENS = int(4096)  # 8192

def get_random_temperature():
    return random.uniform(0.5, 0.9)


class FreeChatService:
    description = "自由对话，闲聊，生成自然回复"
    
    async def stream_chat(self, request: FreeChatRequest):
        """
        流式对话，边生成边 yield
        """
        session = await session_manager.get_session(request.session_id, request.user_id)
        
        injection_decision = context_injection_controller.should_inject_for_prompt(
            user_input=request.user_input,
            prompt_type='free_chat',
            feature_stage=getattr(session, 'feature_stage', None)
        )
        
        session_intermediate_results = getattr(session, 'intermediate_results', {})
        
        time_location_info = None
        if injection_decision['inject_time']:
            cached_time_location = session_intermediate_results.get('time_location')
            if cached_time_location:
                time_location_info = cached_time_location
            else:
                time_location_info = time_location_util.get_context_info()
        
        trending_topics_info = None
        if injection_decision['inject_trending']:
            cached_trending = session_intermediate_results.get('trending_topics')
            if cached_trending:
                trending_topics_info = cached_trending
            else:
                try:
                    fashion_trends_result = trending_topics_util.get_trending_topics("fashion_beauty")
                    all_trends = trending_topics_util.get_trending_topics("general")
                    fashion_beauty_list = fashion_trends_result.get('fashion_beauty_trends', [])
                    trending_topics_info = {
                        "fashion_beauty_trends": fashion_beauty_list,
                        "baidu_hot": all_trends.get("baidu_hot", []),
                        "xiaohongshu_hot": all_trends.get("xiaohongshu_hot", []),
                        "combined_context": f"时尚美妆相关热搜：{', '.join([t.get('title', '') for t in fashion_beauty_list[:5]])}" if fashion_beauty_list else all_trends.get("combined_context", "无法获取当前热搜信息"),
                        "success": all_trends.get("success", False),
                    }
                except Exception as e:
                    logger.warning(f"获取热搜失败: {e}")
                    trending_topics_info = {"combined_context": "无法获取当前热搜信息", "success": False}
        
        try:
            intermediate_results = getattr(session, 'intermediate_results', {})
            error_records = getattr(session, 'error_records', [])
            user_profile = getattr(session, 'user_profile', {}) if injection_decision['inject_profile'] else {}
        except Exception as e:
            pass
        
        personalized_context = await user_profile_service.get_personalized_context(user_profile) if user_profile else ""

        # 获取推荐话题（仅当用户输入简单时使用）
        suggested_topic = {}
        try:
            simple_patterns = ["你好", "嗨", "hi", "hello", "在吗", "在", "嗯", "好", "是的", "谢谢", "拜拜", "再见"]
            user_input_lower = request.user_input.lower().strip()
            is_simple_input = (
                len(request.user_input.strip()) < 10 or
                any(pattern in user_input_lower for pattern in simple_patterns)
            )
            if is_simple_input and request.user_id:
                suggested_topic = await user_memory_mining_service.get_topic_for_conversation(request.user_id)
                if suggested_topic:
                    logger.info(f"[FreeChat] 获取到推荐话题: {suggested_topic.get('topic', '')}")
        except Exception as e:
            logger.warning(f"[FreeChat] 获取推荐话题失败: {e}")

        minor_mode = getattr(request, 'minor_mode', False)

        prompt = get_yisia_free_chat_prompt(
            user_input=request.user_input,
            context=request.context,
            lang=request.lang,
            data=request.data,
            time_location_info=time_location_info,
            trending_topics_info=trending_topics_info,
            intermediate_results=intermediate_results,
            error_records=error_records,
            personalized_context=personalized_context,
            suggested_topic=suggested_topic,
            minor_mode=minor_mode
        )
        
        # 集成用户风格学习 - 合并用户画像和用户风格到提示词
        try:
            style_prompt_result = await user_style_learning_service.generate_style_prompt(
                StylePromptConfig(
                    user_id=request.user_id,
                    base_prompt=prompt["system_prompt"],
                    user_profile_context=personalized_context,
                    include_style_guide=True
                )
            )
            
            if style_prompt_result.style_applied:
                prompt["system_prompt"] = style_prompt_result.personalized_prompt
                logger.info(f"[FreeChat] 已集成用户风格指导: {request.user_id}")
        except Exception as e:
            logger.warning(f"[FreeChat] 集成用户风格失败: {e}")
        
        feature_stage = getattr(session, 'feature_stage', '')
        dynamic_max_tokens = LLM_REQUEST_MAX_TOKENS
        if feature_stage:
            try:
                prompt["system_prompt"], dynamic_max_tokens = apply_feature_stage_to_prompt(
                    prompt["system_prompt"], 
                    feature_stage,
                    LLM_REQUEST_MAX_TOKENS
                )
            except Exception as e:
                logger.warning(f"应用 feature_stage 到 prompt 失败: {e}")
        
        need_online_search = getattr(session, 'need_online_search', False)
        
        llm_request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            temperature=get_random_temperature(),
            max_tokens=dynamic_max_tokens,
            enable_search=need_online_search,
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL,
            stream=True,
            source="free_chat",
            enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
        )
        
        async for chunk in llm_client_singleton.call_llm_stream(llm_request):
            yield chunk
        

    async def chat(self, request: FreeChatRequest) -> FreeChatResponse:
        session = await session_manager.get_session(request.session_id, request.user_id)
        
        injection_decision = context_injection_controller.should_inject_for_prompt(
            user_input=request.user_input,
            prompt_type='free_chat',
            feature_stage=getattr(session, 'feature_stage', None)
        )
        
        # 优先从 session.intermediate_results 读取已缓存的数据，避免重复调用
        session_intermediate_results = getattr(session, 'intermediate_results', {})
        
        time_location_info = None
        if injection_decision['inject_time']:
            # 优先从 session 读取
            cached_time_location = session_intermediate_results.get('time_location')
            if cached_time_location:
                time_location_info = cached_time_location
                logger.info("从 session.intermediate_results 读取 time_location")
            else:
                # 兜底：重新获取
                time_location_info = time_location_util.get_context_info()
                logger.info("session 中无 time_location，重新获取")
        
        trending_topics_info = None
        if injection_decision['inject_trending']:
            # 优先从 session 读取
            cached_trending = session_intermediate_results.get('trending_topics')
            if cached_trending:
                trending_topics_info = cached_trending
                logger.info("从 session.intermediate_results 读取 trending_topics")
            else:
                # 兜底：重新获取
                try:
                    fashion_trends_result = trending_topics_util.get_trending_topics("fashion_beauty")
                    all_trends = trending_topics_util.get_trending_topics("general")
                    fashion_beauty_list = fashion_trends_result.get('fashion_beauty_trends', [])
                    trending_topics_info = {
                        "fashion_beauty_trends": fashion_beauty_list,
                        "baidu_hot": all_trends.get("baidu_hot", []),
                        "xiaohongshu_hot": all_trends.get("xiaohongshu_hot", []),
                        "combined_context": f"时尚美妆相关热搜：{', '.join([t.get('title', '') for t in fashion_beauty_list[:5]])}" if fashion_beauty_list else all_trends.get("combined_context", "无法获取当前热搜信息"),
                        "success": all_trends.get("success", False),
                        "last_fetch_time": datetime.now().timestamp()
                    }
                    logger.info("session 中无 trending_topics，重新获取")
                except Exception as e:
                    logger.warning(f"获取热搜信息失败: {e}")
                    trending_topics_info = None
        
        intermediate_results = {}
        error_records = []
        user_profile = {}
        try:
            intermediate_results = getattr(session, 'intermediate_results', {})
            error_records = getattr(session, 'error_records', [])
            user_profile = getattr(session, 'user_profile', {}) if injection_decision['inject_profile'] else {}
        except Exception as e:
            pass
        
        personalized_context = await user_profile_service.get_personalized_context(user_profile) if user_profile else ""

        # 获取推荐话题（仅当用户输入简单时使用）
        suggested_topic = {}
        try:
            simple_patterns = ["你好", "嗨", "hi", "hello", "在吗", "在", "嗯", "好", "是的", "谢谢", "拜拜", "再见"]
            user_input_lower = request.user_input.lower().strip()
            is_simple_input = (
                len(request.user_input.strip()) < 10 or
                any(pattern in user_input_lower for pattern in simple_patterns)
            )
            if is_simple_input and request.user_id:
                suggested_topic = await user_memory_mining_service.get_topic_for_conversation(request.user_id)
                if suggested_topic:
                    logger.info(f"[FreeChat] 获取到推荐话题: {suggested_topic.get('topic', '')}")
        except Exception as e:
            logger.warning(f"[FreeChat] 获取推荐话题失败: {e}")

        minor_mode = getattr(request, 'minor_mode', False)

        prompt = get_yisia_free_chat_prompt(
            user_input=request.user_input,
            context=request.context,
            lang=request.lang,
            data=request.data,
            time_location_info=time_location_info,
            trending_topics_info=trending_topics_info,
            intermediate_results=intermediate_results,
            error_records=error_records,
            personalized_context=personalized_context,
            suggested_topic=suggested_topic,
            minor_mode=minor_mode
        )
        
        # 集成用户风格学习 - 合并用户画像和用户风格到提示词
        try:
            style_prompt_result = await user_style_learning_service.generate_style_prompt(
                StylePromptConfig(
                    user_id=request.user_id,
                    base_prompt=prompt["system_prompt"],
                    user_profile_context=personalized_context,
                    include_style_guide=True
                )
            )
            
            if style_prompt_result.style_applied:
                prompt["system_prompt"] = style_prompt_result.personalized_prompt
                logger.info(f"[FreeChat] 已集成用户风格指导: {request.user_id}")
        except Exception as e:
            logger.warning(f"[FreeChat] 集成用户风格失败: {e}")
        
        feature_stage = getattr(session, 'feature_stage', '')
        dynamic_max_tokens = LLM_REQUEST_MAX_TOKENS
        if feature_stage:
            try:
                prompt["system_prompt"], dynamic_max_tokens = apply_feature_stage_to_prompt(
                    prompt["system_prompt"], 
                    feature_stage,
                    LLM_REQUEST_MAX_TOKENS
                )
            except Exception as e:
                logger.warning(f"应用 feature_stage 到 prompt 失败: {e}")
        
        # 使用专门的纠错检测服务检测用户是否在纠正信息
        try:
            # 获取当前轮次的AI回复作为原始信息
            current_turn = session.get_current_turn()
            previous_ai_response = current_turn.ai_response if current_turn else None
            
            # 使用LLM和规则基础的混合方法检测纠正
            correction_result = await correction_detection_service.detect_correction(
                user_input=request.user_input,
                previous_ai_response=previous_ai_response
            )
            
            # 如果检测到纠正信息，记录到错误记录中
            if correction_result["is_correction"] and correction_result["confidence"] > 0.5:
                await session_manager.add_error_record(
                    session_id=request.session_id,
                    correction=correction_result["correction_content"],
                    original_info=correction_result["original_mistake"]
                )
                
                try:
                    learning_result = await self_evolution_manager.process_correction_learning(
                        original_info=correction_result["original_mistake"],
                        correction=correction_result["correction_content"]
                    )
                    if hasattr(session, 'knowledge_updates'):
                        session.knowledge_updates.append(learning_result)
                    else:
                        session.knowledge_updates = [learning_result]
                except Exception as e:
                    logger.warning(f"自进化学习失败: {e}")
                    
        except Exception as e:
            # 记录错误但不影响主流程
            logger.warning(f"纠错检测失败: {e}")
        
        # 从 session 读取联网搜索决策
        need_online_search = getattr(session, 'need_online_search', False)
        
        llm_request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            temperature=get_random_temperature(),
            max_tokens=dynamic_max_tokens,
            enable_search=need_online_search,
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL,
            source="free_chat",
            enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
        )
        tmp = await llm_client_singleton.call_llm(llm_request) # 得到的是FreeChatResponseData
        
        result = FreeChatResponse(data=tmp)
        return result

