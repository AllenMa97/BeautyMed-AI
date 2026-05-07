"""
Function Planner Service - 核心路由与规划服务

================================================================================
                              系统架构流程图
================================================================================

用户输入 (user_input)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  步骤1: 快速短路检测 (词表匹配)                                                │
│  ────────────────────────────────────────                                   │
│  检测简单问候/确认/感谢等 → is_simple = True                                  │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  步骤2: 路由决策 (routing_decision_service)                                   │
│  ────────────────────────────────────────────                               │
│  输出: need_plan (是否需要规划), need_search (是否需要搜索)                    │
│  同时启动: 内容违规检测 (异步并行)                                             │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ├── need_plan = False ──────────────────────────────────────┐
    │                                                           │
    │                                                           ▼
    │                                              ┌─────────────────────┐
    │                                              │  free_chat (兜底)    │
    │                                              │  直接闲聊回复        │
    │                                              └─────────────────────┘
    │
    └── need_plan = True ───────────────────────────────────────┐
                                                                │
                                                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  步骤3: 功能规划 (planner)                                                    │
│  ─────────────────────────────                                               │
│  Planner 决定调用哪些功能:                                                    │
│  - knowledge_retrieval: 知识检索 (医美/产品/成分/功效)                         │
│  - intent_clarify: 意图澄清                                                  │
│  - text_summary: 文本摘要                                                    │
│  - 空调用: 不需要任何功能                                                     │
│                                                                              │
│  内部自动执行的前置步骤（无需 Planner 规划）:                                   │
│  - 意图识别 (intent_recognize): 在规划前自动执行，结果写入 session             │
│  - 对话摘要 (dialog_summary): 条件触发，上下文压缩                            │
│  - 实体关系联合抽取: 作为 knowledge_retrieval 的内部前置步骤自动执行           │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  步骤4: 执行功能 (function_executer_service)                                  │
│  ─────────────────────────────────────────                                   │
│  按顺序执行 planner 规划的功能                                                │
│  结果存入 session.intermediate_results                                       │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  步骤5: 自动选择 Chat 方式                                                    │
│  ─────────────────────────────                                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  判断: 是否有 knowledge_retrieval 结果?                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│      │                                                                       │
│      ├── 有结果 ────────────────────────────────────────────┐               │
│      │                                                      │               │
│      │                                                      ▼               │
│      │                                         ┌─────────────────────┐     │
│      │                                         │  knowledge_chat     │     │
│      │                                         │  基于知识生成回答    │     │
│      │                                         └─────────────────────┘     │
│      │                                                                       │
│      └── 无结果 ────────────────────────────────────────────┐               │
│                                                             │               │
│                                                             ▼               │
│                                                ┌─────────────────────┐      │
│                                                │  free_chat (兜底)   │      │
│                                                │  通用闲聊回复       │      │
│                                                └─────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  步骤6: 返回结果 (流式输出)                                                   │
│  ─────────────────────────────                                               │
│  SSE 流式返回 chat_response                                                  │
│  异步更新 session 历史                                                       │
└─────────────────────────────────────────────────────────────────────────────┘


================================================================================
                              职责划分
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│  服务                          │  职责                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  routing_decision_service     │  快速分流: need_plan, need_search          │
│  intent_recognize_service     │  意图识别: 规划前自动执行，结果写入 session  │
│  dialog_summary_service       │  对话摘要: 条件触发，上下文压缩              │
│  planner                      │  功能规划: 决定调用哪些功能                  │
│  function_executer_service    │  执行功能: 按顺序执行规划的功能              │
│  自动路由 (步骤5)              │  根据 knowledge_retrieval 结果选择 chat     │
└─────────────────────────────────────────────────────────────────────────────┘


================================================================================
                              关键设计原则
================================================================================

1. 知识检索 → 知识问答
   - 有 knowledge_retrieval 结果 → knowledge_chat
   - 无 knowledge_retrieval 结果 → free_chat (兜底)

2. 异步并行
   - 内容违规检测与规划流程并行执行
   - 不阻塞主流程

3. 快速路径
   - 简单问题 (need_plan=False) 直接走 free_chat
   - 跳过 planner 调用，减少延迟
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.


import json
import os
import random
import ast
import asyncio
import time
import datetime
import uuid
from typing import Dict, List, Any

from algorithm_services.api.schemas.base_schemas import BaseResponse
from algorithm_services.api.schemas.feature_schemas.free_chat_schemas import FreeChatRequest
from algorithm_services.api.schemas.feature_schemas.knowledge_chat_schemas import KnowledgeChatRequest
from algorithm_services.api.schemas.feature_schemas.function_planner_schemas import (
    FunctionPlannerRequest, FunctionPlannerResponse, FunctionPlannerResponseData
)
from algorithm_services.api.schemas.feature_schemas.dialog_summary_schema import DialogSummaryRequest
from algorithm_services.api.schemas.feature_schemas.intent_recognize_schemas import IntentRecognizeRequest

from algorithm_services.session.session_factory import TurnData, session_manager, SessionFeatureStage
from algorithm_services.core.prompts.features.function_planner_prompt import get_function_planner_prompt
from algorithm_services.utils.time_location import time_location_util
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger, set_log_context, clear_log_context
from algorithm_services.core.services.feature_services.function_executer_service import FunctionExecuterService
from algorithm_services.core.services.feature_services.i18n_service import I18N_Translate
from algorithm_services.core.services.feature_services.dialog_summary_service import DialogSummaryService
from algorithm_services.core.services.feature_services.intent_recognize_service import IntentRecognizeService
from algorithm_services.core.services.feature_services.user_profile_service import user_profile_service
from algorithm_services.core.services.feature_services.user_style_service import user_style_learning_service
from algorithm_services.api.schemas.feature_schemas.user_style_schema import UserStyleUpdateRequest
from algorithm_services.core.services.feature_services.search_decision_service import search_decision_service
from algorithm_services.core.services.feature_services.routing_decision_service import routing_decision_service
from algorithm_services.core.processors.content_moderation_service import content_moderation_service
from algorithm_services.utils.performance_monitor import monitor_async

logger = get_logger(__name__)

AIPOSIT_GAGALIN_DELICK_CONSTANT = float(os.getenv("AIPOSIT_GAGALIN_DELICK_CONSTANT", 1))
DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-plus"  # 生成计划用强模型
PLANNING_MODEL = "qwen-flash"  # 规划可以用较弱的模型，更快
LLM_REQUEST_MAX_TOKENS = int(4096) # qwen-flash极限是32768;

# DEFAULT_PROVIDER = "lansee"
# DEFAULT_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
# LLM_REQUEST_MAX_TOKENS = int(512)


LLM_REQUEST_TEMPERATURE = float(0.2)
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "zh-CN")

# 重规划阈值超参数（0-1，值越高越容易触发重规划，灵活性越高），从环境变量读取，默认0.2（低重规划概率，优先稳定性）
REPLAN_THRESHOLD = float(os.getenv("FUNCTION_PLANNER_REPLAN_THRESHOLD", 0.2))
# 最小执行步数（至少执行N步后才允许重规划，避免频繁重规划）
MIN_STEPS_BEFORE_REPLAN = int(os.getenv("MIN_STEPS_BEFORE_REPLAN", 1))
# 从环境变量读取关于执行规划的随机截取比例范围（0-1），默认最少截 20%，最多截 50%
RANDOM_HEAD_RATIO_MIN = float(os.getenv("RANDOM_HEAD_RATIO_MIN", 0.2))
RANDOM_HEAD_RATIO_MAX = float(os.getenv("RANDOM_HEAD_RATIO_MAX", 0.5))

class FunctionPlannerService:
    """规划器核心Service（支持动态调度+回环）"""

    def __init__(self):
        self.SIMPLE_PATTERNS = [
            "你好", "早上好", "晚安", "嗨", "hi", "hello", "在吗", "在不在", "在么",
            "谢谢", "OK", "好的", "收到", "明白", "知道", "感谢",
            "唱歌", "讲故事", "讲个笑话",
        ]
        
        self.INTENT_CACHE_TTL = int(os.getenv("INTENT_CACHE_TTL", 3600))
        self.DIALOG_SUMMARY_TIME_THRESHOLD = int(os.getenv("DIALOG_SUMMARY_TIME_THRESHOLD", 300))
        self.USER_PROFILE_UPDATE_INTERVAL = int(os.getenv("USER_PROFILE_UPDATE_INTERVAL", 300))
        
        self.executer = FunctionExecuterService()
        self.dialog_summary_service = DialogSummaryService()
        self.intent_recognize_service = IntentRecognizeService()
        self._intent_cache = {}  # 意图缓存: {hash(input): {intent, confidence, expire}}

    async def yield_i18n_process_of_thinking(self, code=102, msg="thinking", source_data="", target_lang="zh-CN"):
        if "zh-CN" in target_lang:
            yield BaseResponse(code=code, msg=msg, data=source_data).to_stream(is_sse=True)
        else:
            translation_result = await I18N_Translate(text=source_data, target_lang=target_lang)
            translated_data = translation_result['data']['translated_text']
            yield BaseResponse(code=code, msg=msg, data=translated_data).to_stream(is_sse=True)

    def process_of_thinking(self, code=102, msg="thinking", data=""):
        return BaseResponse(code=code, msg=msg, data=data).to_stream(is_sse=True)

    @monitor_async(name="generate_plan_result", log_threshold=2.0)
    async def generate_plan_result(self, request: FunctionPlannerRequest, session) -> Dict[str, Any]:
        """
        生成初始规划结果
        :param request: 功能规划请求对象
        :param session: 当前会话对象
        :return: 规划结果字典
        """
        step_start = time.time()
        
        # 更新 session 的 context（如果有新传入的 context）
        if request.context:
            session.context = request.context
        
        user_input_lower = request.user_input.lower().strip()
        input_hash = hash(user_input_lower)
        
        simple_decision = None
        
        # 检查是否为简单问题（使用缓存）
        cached = self._intent_cache.get(input_hash)
        if cached and cached.get("expire", 0) > time.time():
            intent = cached["intent"]
            confidence = cached["confidence"]
            simple_decision = cached.get("simple_decision")
            logger.info(f"[意图缓存命中] {request.user_input[:20]} -> {intent} (conf:{confidence})")
        else:
            # 判断是否为简单问题
            if len(request.user_input) <= 5:
                for pattern in self.SIMPLE_PATTERNS:
                    if pattern in user_input_lower:
                        simple_decision = True
                        break
            
            # 异步执行意图识别（不阻塞后续流程）
        # 但在简单模式下跳过意图识别以节省时间
        if simple_decision is not True:  # 只有当不是简单问题时才执行意图识别
            try:
                intent_start = time.time()
                intent_request = IntentRecognizeRequest(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    user_input=request.user_input,
                    context=request.context or session.context,
                    lang=request.lang
                )
                
                intent_result = await self.intent_recognize_service.recognize(intent_request)
                
                if intent_result.code == 200:
                    intent = intent_result.data.intent
                    confidence = intent_result.data.confidence
                    
                    # 高置信度 + 简单模式 = 简单问题
                    if confidence >= 0.95 and simple_decision is None:
                        for pattern in self.SIMPLE_PATTERNS:
                            if pattern in user_input_lower:
                                simple_decision = True
                                break
                    
                    # 缓存意图结果
                    self._intent_cache[input_hash] = {
                        "intent": intent,
                        "confidence": confidence,
                        "simple_decision": simple_decision,
                        "expire": time.time() + self.INTENT_CACHE_TTL
                    }
                    
                    await self.executer.update_session_from_feature(
                        "intent_recognize", 
                        {"code": 200, "msg": "success", "data": intent_result.data.dict()},
                        session
                    )
                    logger.info(f"意图识别: {intent} (置信度:{confidence}, 简单:{simple_decision}, 耗时:{time.time() - intent_start:.2f}秒)")
                else:
                    logger.warning(f"意图识别失败：{intent_result.msg}")
            except Exception as e:
                logger.error(f"意图识别执行失败：{e}", exc_info=True)
        else:
            logger.info(f"跳过意图识别，已确定为简单问题")
        
        # 存储简单问题判断结果到session，供后续使用
        session._is_simple = simple_decision
        
        # 步骤 1: 根据条件执行对话摘要功能，确保上下文连续性
        summary_start = time.time()
        await self.execute_dialog_summary_if_needed(request, session)
        logger.info(f"对话摘要耗时: {time.time() - summary_start:.2f}秒")
        
        # 异步更新用户画像（不阻塞主流程）
        asyncio.create_task(self.execute_user_profile_update_if_needed(request, session))
        
        # 步骤 2: 获取时间地理位置信息
        time_start = time.time()
        time_location_task = asyncio.create_task(self._get_time_location_info_async())
        
        time_location_info = await time_location_task
        
        if isinstance(time_location_info, Exception):
            logger.warning(f"获取时间地理位置信息失败: {time_location_info}")
            time_location_info = time_location_util.get_context_info()
        
        logger.info(f"获取时间地理位置耗时: {time.time() - time_start:.2f}秒")
        
        # 将获取到的 time_location 存入 session，供后续 free_chat 使用
        try:
            if not hasattr(session, 'intermediate_results') or not session.intermediate_results:
                session.intermediate_results = {}
            session.intermediate_results['time_location'] = time_location_info
            await session_manager.update_session(
                session.session_id,
                intermediate_results=session.intermediate_results
            )
            
            need_search = getattr(session, 'need_online_search', False)
            logger.info(f"联网搜索决策(已判断): {need_search}")
            logger.info("时间地理位置信息已存入 session.intermediate_results")
        except Exception as e:
            logger.warning(f"存入 session intermediate_results 失败: {e}")
        
        # 获取中间结果信息
        intermediate_results = getattr(session, 'intermediate_results', {})
        
        # 构建对话上下文（从 session.turns）
        dialog_context = self._build_dialog_context(session)
        
        plan_prompt = get_function_planner_prompt(
            session_id=request.session_id,
            user_input=request.user_input,
            context=request.context or session.context or dialog_context,
            executed_functions_and_results=[],
            explanation='',
            intermediate_results=intermediate_results
        )
        llm_request = LLMRequest(
            stream=False,
            system_prompt=plan_prompt["system_prompt"],
            user_prompt=plan_prompt["user_prompt"],
            temperature=LLM_REQUEST_TEMPERATURE,
            max_tokens=LLM_REQUEST_MAX_TOKENS,
            response_format={"type": "json_object"},
            provider=DEFAULT_PROVIDER,
            model=PLANNING_MODEL,
            enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
        )
        plan_start = time.time()
        plan_result = await llm_client_singleton.call_llm(llm_request)
        logger.info(f"生成计划耗时: {time.time() - plan_start:.2f}秒")
        logger.info(f"generate_plan_result 总耗时: {time.time() - step_start:.2f}秒")
        return plan_result
    
    def _build_dialog_context(self, session, max_turns: int = 5) -> str:
        """
        从 session.turns 构建对话上下文字符串
        
        Args:
            session: 会话对象
            max_turns: 最大包含的对话轮次数
        
        Returns:
            对话上下文字符串，格式如：
            "用户: 我有点色斑，想去掉
             助手: 您好，色斑问题很常见...
             用户: 嗯最近的，有啥好用的不"
        """
        context_parts = []
        
        turns = getattr(session, 'turns', [])
        if not turns:
            return ""
        
        recent_turns = turns[-max_turns:] if len(turns) > max_turns else turns
        
        for turn in recent_turns:
            user_query = getattr(turn, 'user_query', '') or ''
            assistant_response = getattr(turn, 'assistant_response', '') or ''
            
            if user_query:
                context_parts.append(f"用户: {user_query}")
            if assistant_response:
                truncated_response = assistant_response[:200] + "..." if len(assistant_response) > 200 else assistant_response
                context_parts.append(f"助手: {truncated_response}")
        
        return "\n".join(context_parts)
    
    def should_execute_dialog_summary(self, request: FunctionPlannerRequest, session) -> bool:
        """
        判断是否需要执行对话摘要功能（CONTEXT_COLLAPSE）
        基于以下条件：
        1. 用户输入长度超过阈值（>200 字符）
        2. 会话历史长度达到随机轮次（5-8 轮）
        """
        try:
            # 条件 1: 检查用户输入长度
            user_input_length = len(request.user_input) if request.user_input else 0
            USER_INPUT_LENGTH_THRESHOLD = 200  # 用户输入超过 200 字符
            
            # 条件 2: 检查会话历史长度（随机轮次：5-8）
            history_length = 0
            if hasattr(session, 'history') and session.turns:
                history_length = len(session.turns)
            
            # 随机生成归档阈值（5-8轮）
            HISTORY_LENGTH_THRESHOLD = random.randint(5, 8)
            
            # 检查上次摘要时间（避免重复摘要）
            last_summary_time = getattr(session, 'last_summary_time', 0)
            current_time = time.time()
            TIME_THRESHOLD = self.DIALOG_SUMMARY_TIME_THRESHOLD
            
            # 如果距离上次摘要时间太短，跳过
            if (current_time - last_summary_time) < TIME_THRESHOLD:
                return False
            
            # 满足任一条件即执行摘要
            if user_input_length >= USER_INPUT_LENGTH_THRESHOLD:
                logger.info(f"触发对话摘要：用户输入长度={user_input_length}")
                return True
            
            if history_length >= HISTORY_LENGTH_THRESHOLD:
                logger.info(f"触发对话摘要：会话轮次={history_length}（阈值={HISTORY_LENGTH_THRESHOLD}）")
                return True
            
            return False
        except Exception as e:
            logger.warning(f"判断是否需要执行对话摘要时出错：{e}")
            return False  # 出错时不执行，避免影响正常流程
    
    async def execute_dialog_summary_if_needed(self, request: FunctionPlannerRequest, session):
        """
        根据条件判断是否执行对话摘要功能（CONTEXT_COLLAPSE）
        生成结构化归档，删除原始turns，维护类似git log的结构
        """
        if not self.should_execute_dialog_summary(request, session):
            logger.debug("跳过对话摘要，条件不符合")
            return
        
        try:
            # 准备对话内容 - 从会话历史中获取最近的对话
            dialog_content = []
            if hasattr(session, 'turns') and session.turns:
                # 获取最近的几轮对话
                recent_history = session.turns[-5:]  # 最近5轮对话
                for item in recent_history:
                    if isinstance(item, dict):
                        user_msg = item.get('user_input', '')
                        agent_msg = item.get('agent_response', '')
                        if user_msg or agent_msg:
                            dialog_content.append(f"用户: {user_msg}")
                            dialog_content.append(f"助手: {agent_msg}")
            else:
                # 如果没有历史记录，使用当前输入
                dialog_content = [f"用户: {request.user_input}", f"助手: 正在处理您的请求..."]
            
            # 创建摘要请求
            summary_request = DialogSummaryRequest(
                dialog_content=dialog_content,
                summary_length=200,  # 限制摘要长度
                summary_type="brief"  # 简洁摘要
            )
            
            # 执行摘要功能
            summary_result = await self.dialog_summary_service.generate_dialog_summary(summary_request)
            
            # CONTEXT_COLLAPSE：生成结构化归档
            if hasattr(session, 'turns') and len(session.turns) > 3:
                # 归档前N轮（保留最近3轮）
                archive_count = len(session.turns) - 3
                archived_turns = session.turns[:archive_count]
                
                # 提取关键信息
                key_entities = set()
                key_intents = set()
                for turn in archived_turns:
                    if hasattr(turn, 'user_query_entities'):
                        for entity_type, entities in turn.user_query_entities.items():
                            if isinstance(entities, list):
                                key_entities.update(entities)
                            elif entities:
                                key_entities.add(str(entities))
                    if hasattr(turn, 'user_query_intent') and turn.user_query_intent:
                        key_intents.add(turn.user_query_intent)
                
                # 创建结构化归档
                archive_entry = {
                    'archive_id': f"archive_{int(time.time())}",
                    'turn_range': (0, archive_count),
                    'summary': summary_result.data.dialog_summary,
                    'key_entities': list(key_entities),
                    'key_intents': list(key_intents),
                    'timestamp': datetime.now().isoformat(),
                    'turn_count': archive_count
                }
                
                # 保存归档
                if not hasattr(session, 'archived_contexts'):
                    session.archived_contexts = []
                session.archived_contexts.append(archive_entry)
                
                # 删除已归档的轮次（真正节省空间）
                session.turns = session.turns[-3:]
                
                logger.info(f"[CONTEXT_COLLAPSE] 归档{archive_count}轮，保留3轮，归档ID: {archive_entry['archive_id']}")
            
            # 将摘要结果存储到会话中，供后续使用
            if hasattr(session, 'intermediate_results'):
                if not isinstance(session.intermediate_results, dict):
                    session.intermediate_results = {}
                session.intermediate_results['dialog_summary'] = summary_result.data.dialog_summary
            else:
                session.intermediate_results = {'dialog_summary': summary_result.data.dialog_summary}
            
            # 更新最后摘要时间
            session.last_summary_time = time.time()
            
            logger.info(f"执行对话摘要完成，摘要长度: {summary_result.data.summary_length}")
            
        except Exception as e:
            logger.warning(f"执行对话摘要失败: {e}，将继续执行其他功能")
    
    def should_update_user_profile(self, request: FunctionPlannerRequest, session) -> bool:
        """
        判断是否需要更新用户画像
        基于以下条件：
        1. 会话历史长度达到固定轮次（5 轮）
        2. 距离上次更新时间超过阈值（5 分钟）
        """
        try:
            history_length = 0
            if hasattr(session, 'turns') and session.turns:
                history_length = len(session.turns)
            
            HISTORY_LENGTH_THRESHOLD = 5
            
            last_update_time = getattr(session, 'last_profile_update_time', 0)
            current_time = time.time()
            TIME_THRESHOLD = self.USER_PROFILE_UPDATE_INTERVAL
            
            if (current_time - last_update_time) < TIME_THRESHOLD:
                return False
            
            if history_length >= HISTORY_LENGTH_THRESHOLD:
                return True
            
            return False
        except Exception as e:
            logger.warning(f"判断用户画像更新条件失败: {e}")
            return False
    
    def should_enable_search(self, request: FunctionPlannerRequest) -> bool:
        """
        判断是否需要联网搜索
        基于用户输入中是否包含实时信息需求
        """
        user_input = request.user_input.lower()
        
        search_keywords = [
            "今天", "昨天", "明天", "现在", "刚刚",
            "新闻", "最新", "最近", "实时",
            "天气", "温度", "多少度",
            "发生了什么", "怎么了",
            "现在几点", "当前时间",
            "今日", "此刻",
        ]
        
        for keyword in search_keywords:
            if keyword in user_input:
                return True
        
        return False
    
    async def async_update_search_decision(self, request: FunctionPlannerRequest, session):
        """
        异步更新联网搜索决策（用 LLM 更精确分析）
        """
        try:
            result = await search_decision_service.analyze(request.user_input)
            
            if result.get("need_search"):
                session.need_online_search = True
                logger.info(f"联网搜索决策(LLM): True, reason: {result.get('reason')}")
        except Exception as e:
            logger.warning(f"异步联网决策分析失败: {e}")
    
    async def _get_time_location_info_async(self):
        """异步获取时间地理位置信息"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, time_location_util.get_context_info)
        except Exception as e:
            logger.warning(f"获取时间地理位置信息失败: {e}")
            # 返回默认值
            return {
                "current_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "location": "未知位置",
                "weather": "未知天气"
            }
    
    async def execute_user_profile_update_if_needed(self, request: FunctionPlannerRequest, session):
        """
        根据条件判断是否更新用户画像
        """
        if not self.should_update_user_profile(request, session):
            logger.debug("跳过用户画像更新，条件不符合")
            return
        
        try:
            user_profile = getattr(session, 'user_profile', {}) or {}
            
            if hasattr(session, 'turns') and session.turns:
                recent_history = session.turns[-5:]
                user_input_text = ""
                ai_response_text = ""
                for item in recent_history:
                    if isinstance(item, dict):
                        user_input_text += item.get('user_input', '') + " "
                        ai_response_text += item.get('agent_response', '') + " "
                
                if user_input_text.strip():
                    update_result = await user_profile_service.update_user_profile(
                        current_profile=user_profile,
                        user_input=user_input_text.strip(),
                        ai_response=ai_response_text.strip()
                    )
                    
                    session.user_profile = update_result
                    session.last_profile_update_time = time.time()
                    
                    await session_manager.update_session(
                        request.session_id,
                        user_profile=update_result
                    )
                    
                    logger.info("用户画像更新完成")
        except Exception as e:
            logger.warning(f"更新用户画像失败: {e}")

    async def regenerate_plan_result(self, request: FunctionPlannerRequest, session) -> Dict[str, Any]:
        """
        生成新的规划（重规划专用）
        :param request: 原始请求
        :param session: 当前会话
        :return: 新的规划结果
        """
        # 根据条件执行对话摘要功能，确保上下文连续性
        await self.execute_dialog_summary_if_needed(request, session)
        
        # 异步更新用户画像（不阻塞主流程）
        asyncio.create_task(self.execute_user_profile_update_if_needed(request, session))
        
        # 获取时间地理位置信息
        time_location_task = asyncio.create_task(self._get_time_location_info_async())
        
        time_location_info = await time_location_task
        
        if isinstance(time_location_info, Exception):
            logger.warning(f"获取时间地理位置信息失败: {time_location_info}")
            time_location_info = time_location_util.get_context_info()
        
        # 获取中间结果信息
        intermediate_results = getattr(session, 'intermediate_results', {})
        
        replan_prompt = get_function_planner_prompt(
            session_id=request.session_id,
            user_input=request.user_input,
            context=request.context or session.context,
            executed_functions_and_results=request.executed_functions_and_results,
            explanation='',
            intermediate_results=intermediate_results
        )

        llm_request = LLMRequest(
            stream=False,
            system_prompt=replan_prompt["system_prompt"],
            user_prompt=replan_prompt["user_prompt"],
            temperature=LLM_REQUEST_TEMPERATURE * 1.1,
            max_tokens=LLM_REQUEST_MAX_TOKENS,
            response_format={"type": "json_object"},
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL,
            enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
        )

        new_plan_result = await llm_client_singleton.call_llm(llm_request)
        logger.info(f"重规划生成新计划：{new_plan_result}")
        return new_plan_result

    def build_context(self, request, session) -> str:
        """
        构建上下文：对话摘要 + 最近3轮对话
        """
        parts = []
        
        # 1. 对话摘要（从 session.dialog_summary）
        if session.dialog_summary:
            parts.append(f"【之前对话摘要】{session.dialog_summary}")
        
        # 2. 最近3轮对话（从 session.turns）
        if hasattr(session, 'turns') and session.turns:
            recent = session.turns[-3:]
            if recent:
                parts.append("【最近对话】")
                for turn in recent:
                    user_msg = turn.user_query
                    agent_msg = turn.ai_response
                    if user_msg:
                        parts.append(f"用户: {user_msg}")
                    if agent_msg:
                        parts.append(f"助手: {agent_msg}")
        
        return "\n".join(parts) if parts else "已理解用户的需求"
    
    async def _update_session_async(self, session, response: str, function_calls: list):
        """异步更新 session"""
        try:
            if hasattr(session, 'current_turn') and session.current_turn:
                session.current_turn.ai_response = response
                session.current_turn.plan_functions = function_calls
                logger.info(f"异步更新 session 完成，回复长度: {len(response)}")
            
            await self._trigger_user_style_update(session, response)
            
        except Exception as e:
            logger.warning(f"异步更新 session 失败: {e}")
    
    async def _trigger_user_style_update(self, session, response: str):
        """触发用户风格异步更新"""
        try:
            user_id = getattr(session, 'user_id', None)
            user_input = getattr(session.current_turn, 'user_input', '') if hasattr(session, 'current_turn') and session.current_turn else ''
            
            if user_id and user_input and response:
                update_request = UserStyleUpdateRequest(
                    user_id=user_id,
                    user_input=user_input,
                    ai_response=response
                )
                await user_style_learning_service.update_style_async(update_request)
                logger.info(f"[用户风格] 已触发异步更新: {user_id}")
                
        except Exception as e:
            logger.warning(f"[用户风格] 触发更新失败: {e}")


    def get_random_max_iterations(self) -> int:
        """
        根据随机性获取最大迭代次数
        """
        base_iterations = int(os.getenv("REACT_BASE_ITERATIONS", 2))
        max_iterations = int(os.getenv("REACT_MAX_ITERATIONS", 5))
        return random.randint(base_iterations, max_iterations)
    
    def get_steps_for_iteration(self, execution_order, function_calls, iteration, max_iterations, head_ratio) -> List[int]:
        """
        获取当前迭代需要执行的步骤索引
        使用随机截取策略
        """
        if not execution_order:
            return []
        
        if iteration == 0:
            head_count = max(1, int(len(execution_order) * head_ratio))
            return execution_order[:head_count]
        
        remaining = execution_order[len(self.get_executed_count(iteration, max_iterations, len(execution_order))):]
        if not remaining:
            return []
        
        current_ratio = head_ratio * (1 - iteration / max_iterations)
        steps_count = max(1, int(len(remaining) * current_ratio))
        return remaining[:steps_count]
    
    def get_executed_count(self, iteration, max_iterations, total_steps) -> int:
        return int(total_steps * iteration / max_iterations)
    
    def should_trigger_replan(self, iteration_results: List[Dict], iteration: int) -> bool:
        """
        判断是否应该触发重规划
        """
        if iteration < MIN_STEPS_BEFORE_REPLAN:
            return False
        
        random_value = random.random()
        return random_value < REPLAN_THRESHOLD
    
    def format_executed_info(self, executed_steps: List[str], all_results: List[Dict]) -> str:
        """
        格式化已执行信息，用于重规划提示
        """
        info_parts = []
        for step in executed_steps:
            result = next((r for r in all_results if r["function_name"] == step), None)
            if result:
                info_parts.append(f"- {step}: {'成功' if result.get('success') else '失败'}")
        return "\n".join(info_parts)

    @monitor_async(name="function_planner_stream_plan", log_threshold=5.0)
    async def stream_plan(self, request: FunctionPlannerRequest):
        """
        执行规划器逻辑（流式版本）：
        1. 加载会话状态
        2. 生成调度计划 并 执行功能
        3. 更新会话状态
        4. 逐块返回执行结果
        """
        try:
            set_log_context(session_id=request.session_id, user_id=request.user_id)
        
            ############################################################
            # 步骤0：初始化所有关键变量，避免UnboundLocalError
            execution_log = []
            final_result = ""
            function_calls = []
            execution_order = []
            explanation = ""
            current_executed_steps = []  # 记录已执行的功能
            need_replan = False  # 是否需要重规划
            replan_count = 0  # 重规划次数，避免无限重规划
            request_start_time = time.time()
            step_start_time = request_start_time
            ############################################################
            # 步骤1：加载会话信息
            logger.info("【步骤1】加载会话信息")
            session = await session_manager.get_session(request.session_id, request.user_id)

            session.intermediate_results = {}
        
            # 创建新的轮次并添加到 session
            turn_id = f"{request.session_id}_{uuid.uuid4().hex[:8]}"
            current_turn = TurnData(
                turn_id=turn_id,
                session_id=request.session_id,
                user_query=request.user_input
            )
            session.add_turn(current_turn)
        
            step_time = time.time() - step_start_time
            logger.info(f"【步骤1完成】加载会话，耗时{step_time:.2f}秒")
            step_start_time = time.time()
        
            async for tmp in self.yield_i18n_process_of_thinking(source_data="🔍 正在加载你的会话信息...\n",
                                                                 target_lang=request.lang): yield tmp
            ############################################################
            # 步骤2：并行路由决策（判断是否需要规划 + 是否需要联网）
            # 优化：一个 Prompt 同时返回两个决策
            logger.info("【步骤2】路由决策（是否需要规划 + 是否需要联网）")

            user_input_lower = request.user_input.lower().strip()

            # 快速词表匹配
            is_simple = False
            if len(request.user_input) <= 5:
                for pattern in self.SIMPLE_PATTERNS:
                    if pattern in user_input_lower:
                        is_simple = True
                        logger.info(f"[快速短路] 检测为简单问题（词表匹配），跳过规划")
                        break

            # 使用统一的路由决策服务（词表 + LLM 判断）
            routing_decision = await routing_decision_service.decide(request.user_input)
            need_plan = routing_decision.get("need_plan", not is_simple)
            need_search = routing_decision.get("need_search", False)
            session.need_online_search = need_search
            session._is_simple = not need_plan
        
            # 同时启动内容违规检测（与后续流程并行）
            session._moderation_task = asyncio.create_task(
                content_moderation_service.moderate(request.user_input)
            )
        
            logger.info(f"路由决策结果: need_plan={need_plan}, need_search={need_search}")

            # 根据决策结果决定后续流程
            if routing_decision.get("method") == "pattern_match" and not need_plan:
                # 词表匹配确定的简单问题，直接进入free_chat
                plan_result = {
                    "feature_stage": "CASUAL_CHAT_MODE",
                    "function_calls": [{"function_name": "free_chat", "function_params": {}}],
                    "execution_order": [0],
                    "explanation": "简单问题，直接回复"
                }
                logger.info(f"[路由] 词表匹配确定为简单问题，跳过规划")
            elif is_simple or not need_plan:
                # 简单问题，不需要规划，直接进入free_chat
                plan_result = {
                    "feature_stage": "CASUAL_CHAT_MODE",
                    "function_calls": [{"function_name": "free_chat", "function_params": {}}],
                    "execution_order": [0],
                    "explanation": "简单问题，直接回复"
                }
                logger.info(f"[路由] 跳过规划，直接进入 free_chat")
            else:
                # 需要规划，进入完整流程（planner 会决定是否需要 RAG）
                plan_result = await self.generate_plan_result(request=request, session=session)
        
            step_time = time.time() - step_start_time
            step_start_time = time.time()
        
            async for tmp in self.yield_i18n_process_of_thinking(source_data="📝 正在规划执行步骤...\n",
                                                                 target_lang=request.lang): yield tmp
            execution_log.append(f"生成调度计划：{plan_result}")
            ############################################################
            # 步骤3：解析调度计划
            logger.info("【步骤3】解析调度计划")
        
            feature_stage = plan_result.get("feature_stage", session.feature_stage)
            function_calls: List[Dict[str, Any]] = plan_result.get("function_calls", [])
            execution_order: List[int] = plan_result.get("execution_order", [item for item in range(len(function_calls))])
            explanation = plan_result.get("explanation", '')
        
            # 安全地获取功能名称列表，避免类型错误
            function_names = []
            for d in function_calls:
                if isinstance(d, dict) and 'function_name' in d:
                    function_names.append(d['function_name'])
                else:
                    function_names.append(str(d))  # 如果不是字典，转换为字符串
        
            step_time = time.time() - step_start_time
            logger.info(f"【步骤3完成】解析计划，耗时{step_time:.2f}秒 | 功能列表: {function_names}")
            step_start_time = time.time()
        
            async for tmp in self.yield_i18n_process_of_thinking(
                source_data=f"📋 解析到初始调度计划需要执行 {len(execution_order)} 个功能步骤\n",
                target_lang=request.lang): yield tmp
            execution_log.append(f"解析到初始调度计划需要执行 {len(execution_order)} 个功能步骤: {function_names}")
            await asyncio.sleep(0.1 * AIPOSIT_GAGALIN_DELICK_CONSTANT)
            ############################################################
            # 步骤3.5：检查内容违规拦截结果
            moderation_result = None
            if hasattr(session, '_moderation_task') and session._moderation_task:
                try:
                    moderation_result = await asyncio.wait_for(
                        session._moderation_task,
                        timeout=3.0
                    )
                    session._moderation_done = True
                except asyncio.TimeoutError:
                    logger.warning("违规检测超时，将重新检测")
                except Exception as e:
                    logger.warning(f"违规检测异常: {e}")

            if moderation_result is None:
                moderation_result = await content_moderation_service.moderate(request.user_input)

            if moderation_result.blocked:
                error_response = {
                    "code": 403,
                    "msg": "抱歉，您的输入内容未通过安全审核，无法进行回复。",
                    "data": {
                        "chat_response": "抱歉，您的输入内容未通过安全审核，无法进行回复。",
                        "reason": moderation_result.reason
                    }
                }
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                logger.warning(f"内容拦截生效: {moderation_result.reason}")
                return

            ############################################################
            # 步骤4：按顺序执行功能
            logger.info("【步骤4】执行功能")
        
            step_time = time.time() - step_start_time
            logger.info(f"【步骤4开始】执行功能，耗时{step_time:.2f}秒")
            step_start_time = time.time()
        
            async for tmp in self.yield_i18n_process_of_thinking(source_data=f"🧠 执行调度计划...\n",
                                                                 target_lang=request.lang): yield tmp
        
            # 合并分组日志
            logger.info(f"功能分组 | execution_order: {execution_order} | function_calls: {[call.get('function_name') for call in function_calls]}")
        
            await asyncio.sleep(0.1 * AIPOSIT_GAGALIN_DELICK_CONSTANT)
            tmp_session_data = None  # 用于存放前一个function执行过后的data，后续也可以进行更新，对所有的function执行后的data都记录起来
            feature_results = {}

            # 将功能调用按依赖关系分组，实现并行执行
            # 为了简化，我们假设所有功能都可以并行执行（除了 free_chat 依赖其他功能结果的情况）
            # 实际应用中可以根据功能类型和依赖关系进行更精细的分组

            # 首先，将功能分为两组：独立功能和依赖功能
            independent_funcs = []
            dependent_funcs = []

            logger.info(f"开始分组功能，execution_order: {execution_order}")
            logger.info(f"function_calls: {[call.get('function_name') for call in function_calls]}")

            for idx in execution_order:
                if idx >= len(function_calls):
                    continue
                call = function_calls[idx]
                func_name = call.get("function_name")
                func_params = call.get("function_params", {})

                # 以防规划器出现幻觉，调用不存在的功能。
                if func_name not in self.executer.feature_services:
                    execution_log.append(f"跳过不支持的功能：{func_name}")
                    async for tmp in self.yield_i18n_process_of_thinking(source_data=f"⚠️ 跳过不支持的功能：{func_name}\n",
                                                                         target_lang=request.lang): yield tmp
                    continue

                # 如果是 free_chat 功能，跳过（会在最后兜底执行）
                if func_name == "free_chat":
                    continue

                # 其他功能正常分组
                independent_funcs.append((idx, call))

            # 合并分组结果日志
            independent_names = [name for idx, name in [(x[0], x[1].get('function_name')) for x in independent_funcs]]
            dependent_names = [name for idx, name in [(x[0], x[1].get('function_name')) for x in dependent_funcs]]
            logger.info(f"分组完成 | 独立功能({len(independent_names)}): {independent_names} | 依赖功能({len(dependent_names)}): {dependent_names}")

            # 为并行执行准备独立函数
            async def execute_single_function(idx_call_tuple, current_tmp_session_data):
                idx, call = idx_call_tuple
                func_name = call.get("function_name")
                func_params = call.get("function_params", {})

                # 补充通用参数（会话ID/用户ID/上下文）
                func_params.update({
                    "session_id": request.session_id,
                    "user_id": request.user_id,
                    "lang": request.lang,
                    "context": request.context or session.context,
                    "data": current_tmp_session_data or request.data,
                    "session_data": getattr(session, 'session_data', None),
                    "personalize": request.personalize,
                })

                # 执行功能
                param_keys = list(func_params.keys())
                execution_log.append(f"执行功能：{func_name}，参数：{param_keys}")
                logger.info(f"【执行】{func_name} | 参数={param_keys}")

                # 初始化变量，收集流式执行的最终结果
                func_final_result = None  # 存储当前功能的最终结果
                stream_chunks = []  # 可选：存储所有流式片段，便于调试

                # 流式执行：遍历异步生成器
                async for chunk in self.executer.stream_execute_feature(func_name, func_params, session):
                    stream_chunks.append(chunk)  # 收集所有流式片段

                # 关键：从流式结果中解析出最终的功能执行结果
                try:
                    # 从stream_execute_feature的输出中提取最终结果
                    # 适配格式：[执行完成] 功能：xxx，结果：{...}
                    final_chunk = None
                    for chunk in reversed(stream_chunks):
                        if "[执行完成]" in chunk and "结果：" in chunk:
                            final_chunk = chunk
                            break
                    if final_chunk:
                        # 提取结果部分（去掉前缀和换行）
                        result_part = final_chunk.split("结果：")[-1].strip()
                        # 优先JSON解析（兼容LLM返回的标准JSON），再降级ast
                        try:
                            func_final_result = json.loads(result_part)
                        except json.JSONDecodeError:
                            # 兼容单引号字典格式
                            func_final_result = ast.literal_eval(result_part)
                    else:
                        # 兜底：拼接所有片段作为结果
                        func_final_result = "\n".join(stream_chunks)
                except Exception as e:
                    logger.warning(f"解析{func_name}结果失败：{e}，使用原始片段")
                    func_final_result = "\n".join(stream_chunks)

                # 记录当前功能的结果（供后续最终结果处理使用）
                # 返回结果而不直接更新，避免并发问题
                if 'data' in func_final_result:
                    return idx, func_name, func_final_result, func_final_result['data']
                else:
                    return idx, func_name, func_final_result, current_tmp_session_data

            # 并行执行独立功能
            if independent_funcs:
                async for tmp in self.yield_i18n_process_of_thinking(
                    source_data=f"🚀 并行执行 {len(independent_funcs)} 个独立功能...\n", target_lang=request.lang): yield tmp
                # 使用当前的 tmp_session_data 作为所有并行任务的输入
                independent_results = await asyncio.gather(
                    *[execute_single_function(func_tuple, tmp_session_data) for func_tuple in independent_funcs],
                    return_exceptions=True
                )

                # 处理并行执行结果并显示状态
                for result in independent_results:
                    if isinstance(result, Exception):
                        logger.error(f"并行执行功能时发生错误: {result}")
                    else:
                        if isinstance(result, tuple) and len(result) >= 3:  # 确保结果是预期的元组格式
                            idx, func_name, func_final_result = result[0], result[1], result[2]
                            # 更新 feature_results
                            feature_results[func_name] = func_final_result

                            # 显示执行完成状态
                            async for tmp in self.yield_i18n_process_of_thinking(
                                source_data=f"✅ 【步骤{idx + 1}】功能 {func_name} 执行完成\n",
                                target_lang=request.lang): yield tmp

                            # 更新会话状态
                            try:
                                await self.executer.update_session_from_feature(func_name, func_final_result, session)
                            except Exception as e:
                                logger.warning(f"功能 {func_name} 更新会话失败：{str(e)}")
                        else:
                            logger.warning(f"并行执行结果格式异常: {result}")

            # 串行执行依赖功能（如 free_chat）
            for idx, call in dependent_funcs:
                func_name = call.get("function_name")
                func_params = call.get("function_params", {})

                # 补充通用参数（会话ID/用户ID/上下文）
                func_params.update({
                    "session_id": request.session_id,
                    "user_id": request.user_id,
                    "lang": request.lang,
                    "context": request.context or session.context,
                    "data": tmp_session_data or request.data,
                    "session_data": getattr(session, 'session_data', None),
                    "personalize": request.personalize,
                })

                # 执行功能：流式调用
                param_keys = list(func_params.keys())
                execution_log.append(f"执行功能：{func_name}，参数：{param_keys}")
                logger.info(f"【执行】{func_name} | 参数={param_keys}")

                # 初始化变量，收集流式执行的最终结果
                func_final_result = None  # 存储当前功能的最终结果
                stream_chunks = []  # 可选：存储所有流式片段，便于调试

                # 流式执行：遍历异步生成器
                async for chunk in self.executer.stream_execute_feature(func_name, func_params, session):
                    async for tmp in self.yield_i18n_process_of_thinking(source_data=f"{chunk}\n",
                                                                         target_lang=request.lang): yield tmp
                    stream_chunks.append(chunk)  # 收集所有流式片段

                # 关键：从流式结果中解析出最终的功能执行结果
                try:
                    # 从stream_execute_feature的输出中提取最终结果
                    # 适配格式：[执行完成] 功能：xxx，结果：{...}
                    final_chunk = None
                    for chunk in reversed(stream_chunks):
                        if "[执行完成]" in chunk and "结果：" in chunk:
                            final_chunk = chunk
                            break
                    if final_chunk:
                        # 提取结果部分（去掉前缀和换行）
                        result_part = final_chunk.split("结果：")[-1].strip()
                        # 优先JSON解析（兼容LLM返回的标准JSON），再降级ast
                        try:
                            func_final_result = json.loads(result_part)
                        except json.JSONDecodeError:
                            # 兼容单引号字典格式
                            func_final_result = ast.literal_eval(result_part)
                    else:
                        # 兜底：拼接所有片段作为结果
                        func_final_result = "\n".join(stream_chunks)
                except Exception as e:
                    logger.warning(f"解析{func_name}结果失败：{e}，使用原始片段")
                    func_final_result = "\n".join(stream_chunks)

                # 记录当前功能的结果（供后续最终结果处理使用）
                feature_results[func_name] = func_final_result
                # 记录当前 function 执行过后的 data
                tmp_session_data = None
                if isinstance(func_final_result, dict) and 'data' in func_final_result:
                    tmp_session_data = func_final_result['data']
                # 实时更新会话状态
                try:
                    await self.executer.update_session_from_feature(func_name, func_final_result, session)
                    async for tmp in self.yield_i18n_process_of_thinking(
                        source_data=f"✅ 【步骤{idx + 1}】功能 {func_name} 执行完成并更新会话\n",
                        target_lang=request.lang): yield tmp

                except Exception as e:
                    error_msg = f"❌ 【步骤{idx + 1}】功能 {func_name} 执行完成但更新会话失败：{str(e)}\n"
                    async for tmp in self.yield_i18n_process_of_thinking(code=500, msg='error', data=error_msg,
                                                                         target_lang=request.lang): yield tmp

                await asyncio.sleep(0.1)

            ############################################################
            # 步骤5：处理最终结果（流式返回）
            logger.info("【步骤5】处理最终结果")
            step_time = time.time() - step_start_time
            logger.info(f"【步骤5开始】整理最终结果，耗时{step_time:.2f}秒")
            step_start_time = time.time()
        
            async for tmp in self.yield_i18n_process_of_thinking(source_data=f"📊 正在整理最终结果...\n",
                                                                 target_lang=request.lang): yield tmp

            await asyncio.sleep(0.1 * AIPOSIT_GAGALIN_DELICK_CONSTANT)

            # 状态匹配逻辑
            # if feature_stage.lower() == SessionFeatureStage.COMPANIONSHIP_MODE.lower():
            #     pass
            # # 建议模式
            # elif feature_stage.lower() == SessionFeatureStage.ADVICE_MODE.lower():
            #     pass
            # # 闲聊模式
            # elif feature_stage.lower() == SessionFeatureStage.CASUAL_CHAT_MODE.lower():
            #     pass
            # # 情感支持模式
            # elif feature_stage.lower() == SessionFeatureStage.EMOTIONAL_SUPPORT_MODE.lower():
            #     pass
            # # 学习模式
            # elif feature_stage.lower() == SessionFeatureStage.LEARNING_MODE.lower():
            #     pass
            # # 美学咨询模式
            # elif feature_stage.lower() == SessionFeatureStage.BEAUTY_CONSULTATION_MODE.lower():
            #     pass
            # # 兜底：未匹配到会话类型
            # else:
            #     # 可根据需求添加默认处理逻辑，比如日志记录、返回默认值等
            #     # print(1)
            #     pass

            # 根据是否有 knowledge_retrieval 结果决定 chat 方式
            has_knowledge_result = (
                hasattr(session, 'intermediate_results') and 
                'knowledge_retrieval' in session.intermediate_results and
                session.intermediate_results['knowledge_retrieval']
            )

            free_chat_full_response = ""
            knowledge_chat_full_response = ""
            chat_response = ""
        
            # 使用对话摘要作为上下文（如果有）
            tmp_context = self.build_context(request, session)

            if has_knowledge_result:
                # 有知识检索结果 → knowledge_chat
                logger.info("执行 knowledge_chat (流式)")
            
                knowledge_chat_service = self.executer.feature_services["knowledge_chat"]
                knowledge_chat_full_response = ""
            
                try:
                    async for chunk in knowledge_chat_service.stream_chat(
                        request=KnowledgeChatRequest(
                            session_id=request.session_id,
                            user_id=request.user_id,
                            user_input=request.user_input,
                            lang=request.lang,
                            context=tmp_context,
                            data=session.intermediate_results['knowledge_retrieval'],
                            minor_mode=request.minor_mode,
                            personalize=request.personalize
                        )
                    ):
                        if chunk.strip().startswith('{"sources"'):
                            continue
                        knowledge_chat_full_response += chunk
                    
                        chunk_data = {
                            "code": 300,
                            "msg": "chunk",
                            "data": {
                                "content": chunk
                            }
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                            
                except Exception as e:
                    logger.error(f"knowledge_chat 流式调用失败: {e}", exc_info=True)
                    yield f"data: {json.dumps({'code': 500, 'msg': f'流式调用失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    return

                logger.info(f"knowledge_chat 流式完成，回复长度：{len(knowledge_chat_full_response)}字符")
            
                try:
                    llm_response = json.loads(knowledge_chat_full_response)
                    chat_response = llm_response.get("chat_response") or knowledge_chat_full_response
                except (json.JSONDecodeError, TypeError):
                    chat_response = knowledge_chat_full_response
            
            else:
                # 无知识检索结果 → free_chat（兜底）
                logger.info("执行 free_chat (流式)")
            
                need_online_search = getattr(session, 'need_online_search', False)
                if need_online_search:
                    async for tmp in self.yield_i18n_process_of_thinking(
                            source_data="🌐 这个问题需要联网查询，让我先搜索一下相关信息...\n",
                            target_lang=request.lang
                    ): yield tmp

                free_chat_service = self.executer.feature_services["free_chat"]
            
                free_chat_full_response = ""
                try:
                    async for chunk in free_chat_service.stream_chat(
                        request=FreeChatRequest(
                            session_id=request.session_id,
                            user_id=request.user_id,
                            user_input=request.user_input,
                            lang=request.lang,
                            context=tmp_context,
                            minor_mode=request.minor_mode
                        )
                    ):
                        free_chat_full_response += chunk
                    
                        chunk_data = {
                            "code": 300,
                            "msg": "chunk",
                            "data": {
                                "content": chunk
                            }
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                            
                except Exception as e:
                    logger.error(f"free_chat 流式调用失败: {e}", exc_info=True)
                    yield f"data: {json.dumps({'code': 500, 'msg': f'流式调用失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    return

                logger.info(f"free_chat 流式完成，回复长度：{len(free_chat_full_response)}字符")
            
                try:
                    llm_response = json.loads(free_chat_full_response)
                    chat_response = llm_response.get("chat_response") or free_chat_full_response
                    emotional_tone = llm_response.get("emotional_tone", "")
                except (json.JSONDecodeError, TypeError):
                    chat_response = free_chat_full_response
                    emotional_tone = ""

            logger.info(f"chat_response 最终长度：{len(chat_response)}字符")
        
            if not chat_response and knowledge_chat_full_response:
                chat_response = knowledge_chat_full_response
            if not chat_response and free_chat_full_response:
                chat_response = free_chat_full_response

            # 异步更新 session（不阻塞返回）
            asyncio.create_task(self._update_session_async(session, chat_response, function_calls))

            # 流式返回最终结果（code: 200）
            final_data = {
            "code": 200,
            "type": "final",
            "data": {
                "chat_response": chat_response,
                # "emotional_tone": emotional_tone,
                "emotional_tone": "",
                "feature_stage": feature_stage,
                "function_calls": function_calls,
                "execution_order": execution_order,
                "explanation": explanation
            }
            }
            yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"

            total_time = time.time() - request_start_time
            logger.info(
            f"\n{'=' * 60}\n"
            f"请求处理完成 (session_id:{request.session_id})\n"
            f"{'=' * 60}\n"
            f"用户输入 ({len(request.user_input)}字符): {request.user_input[:200]}{'...' if len(request.user_input) > 200 else ''}\n"
            f"返回内容 ({len(chat_response)}字符): {chat_response[:300]}{'...' if len(chat_response) > 300 else ''}\n"
            f"执行的功能：{function_names}\n"
            f"总耗时：{total_time:.2f}秒\n"
            f"{'=' * 60}\n"
            )
        
        except Exception as e:
            logger.error(f"[stream_plan] 顶层异常捕获: {e}", exc_info=True)
            error_msg = str(e)
            if "内容审核" in error_msg:
                user_msg = "抱歉，您输入的内容未通过安全审核，请修改后重试。"
            else:
                user_msg = "抱歉，服务暂时出现问题，请稍后重试。"
            yield f"data: {json.dumps({'code': 500, 'msg': user_msg, 'data': {'chat_response': user_msg}}, ensure_ascii=False)}\n\n"
        finally:
            clear_log_context()