"""用户风格学习服务 - 异步增量更新"""
import asyncio
import json
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.api.schemas.feature_schemas.user_style_schema import (
    UserStyleFeature,
    UserStyleUpdateRequest,
    UserStyleResponse,
    UserStyleAnalysisRequest,
    UserStyleAnalysisResponse,
    StylePromptConfig,
    StylePromptResponse,
)


logger = get_logger(__name__)

USER_STYLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "knowledge")
USER_STYLE_FILE = os.path.join(USER_STYLE_DATA_DIR, "user_styles.json")


class UserStyleLearningService:
    """
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    用户风格学习服务
    
    功能：
    - 分析用户语言风格特征
    - 异步增量更新用户风格
    - 生成风格适配的提示词
    
    与用户画像服务的关系：
    - 用户画像服务：关注用户兴趣、偏好、习惯
    - 用户风格学习服务：关注用户语言特征、表达方式
    - 两者独立存储，但在Free Chat中会合并使用
    
    特点：
    - 异步增量更新，不阻塞主流程
    - 支持增量学习
    - 可配置的学习策略
    """
    
    def __init__(self):
        self.default_provider = "aliyun"
        self.default_model = "qwen-vl-plus"
        self._style_cache: Dict[str, UserStyleFeature] = {}
        self._update_queue: Dict[str, asyncio.Queue] = {}
        self._is_running = False
        self._ensure_data_dir()
        self._load_persisted_styles()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(USER_STYLE_DATA_DIR, exist_ok=True)
    
    def _load_persisted_styles(self):
        """从文件加载持久化的用户风格"""
        if os.path.exists(USER_STYLE_FILE):
            try:
                with open(USER_STYLE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    styles_data = data.get("user_styles", {})
                    for user_id, style_dict in styles_data.items():
                        self._style_cache[user_id] = UserStyleFeature(**style_dict)
                    logger.info(f"从持久化文件加载用户风格: {len(self._style_cache)} 个用户")
            except Exception as e:
                logger.warning(f"加载用户风格持久化数据失败: {e}")
    
    def _save_persisted_styles(self):
        """保存用户风格到文件"""
        try:
            styles_data = {}
            for user_id, style in self._style_cache.items():
                styles_data[user_id] = {
                    "language_style": style.language_style,
                    "vocabulary_preferences": style.vocabulary_preferences,
                    "sentence_patterns": style.sentence_patterns,
                    "emotional_expressions": style.emotional_expressions,
                    "common_topics": style.common_topics,
                    "interaction_style": style.interaction_style
                }
            data = {
                "knowledge_type": "user_styles",
                "updated_at": datetime.now().isoformat(),
                "user_styles": styles_data
            }
            with open(USER_STYLE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"用户风格已持久化: {len(self._style_cache)} 个用户")
        except Exception as e:
            logger.warning(f"保存用户风格持久化数据失败: {e}")
    
    async def _ensure_update_queue(self, user_id: str) -> asyncio.Queue:
        """确保用户的更新队列存在"""
        if user_id not in self._update_queue:
            self._update_queue[user_id] = asyncio.Queue()
        return self._update_queue[user_id]
    
    def _get_cache_key(self, user_id: str) -> str:
        """获取缓存键"""
        return f"user_style_{user_id}"
    
    async def get_user_style(self, user_id: str) -> Optional[UserStyleFeature]:
        """获取用户风格特征"""
        cache_key = self._get_cache_key(user_id)
        if cache_key in self._style_cache:
            logger.debug(f"[用户风格] 从缓存获取用户风格: {user_id}")
            return self._style_cache[cache_key]
        
        logger.debug(f"[用户风格] 缓存中无用户风格: {user_id}")
        return None
    
    async def set_user_style(self, user_id: str, style: UserStyleFeature):
        """设置用户风格特征"""
        cache_key = self._get_cache_key(user_id)
        self._style_cache[cache_key] = style
        self._save_persisted_styles()
        logger.info(f"[用户风格] 更新用户风格缓存: {user_id}")
    
    async def update_style_async(self, request: UserStyleUpdateRequest):
        """
        异步更新用户风格
        
        这是一个非阻塞方法，将更新任务放入队列
        实际更新在后台异步执行
        """
        queue = await self._ensure_update_queue(request.user_id)
        await queue.put(request)
        
        logger.info(f"[用户风格] 添加更新任务到队列: {request.user_id}")
        
        # 启动后台处理（如果尚未启动）
        if not self._is_running:
            asyncio.create_task(self._process_update_queue())
    
    async def _process_update_queue(self):
        """后台处理更新队列"""
        self._is_running = True
        logger.info("[用户风格] 启动后台更新处理")
        
        while self._is_running:
            try:
                # 处理所有非空队列
                for user_id, queue in list(self._update_queue.items()):
                    if queue.empty():
                        continue
                    
                    # 收集一批更新（最多5个）
                    updates = []
                    for _ in range(5):
                        if queue.empty():
                            break
                        try:
                            update = queue.get_nowait()
                            updates.append(update)
                        except asyncio.QueueEmpty:
                            break
                    
                    if updates:
                        await self._batch_update_style(updates)
                
                # 短暂休眠，避免CPU占用过高
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"[用户风格] 后台处理异常: {e}")
                await asyncio.sleep(1)
    
    async def _batch_update_style(self, updates: List[UserStyleUpdateRequest]):
        """批量更新用户风格"""
        try:
            logger.info(f"[用户风格] 批量更新用户风格: {len(updates)} 个用户")
            
            # 按用户分组
            user_updates: Dict[str, List[UserStyleUpdateRequest]] = {}
            for update in updates:
                if update.user_id not in user_updates:
                    user_updates[update.user_id] = []
                user_updates[update.user_id].append(update)
            
            # 并行更新每个用户
            tasks = [
                self._incremental_update(user_id, user_updates[user_id])
                for user_id in user_updates
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"[用户风格] 批量更新失败: {e}")
    
    async def _incremental_update(self, user_id: str, updates: List[UserStyleUpdateRequest]):
        """增量更新单个用户风格"""
        try:
            # 获取现有风格
            existing_style = await self.get_user_style(user_id)
            
            if existing_style is None:
                # 如果没有现有风格，从新对话中学习
                existing_style = await self._learn_style_from_scratch(updates)
            else:
                # 增量学习
                existing_style = await self._learn_style_incremental(existing_style, updates)
            
            # 保存更新后的风格
            await self.set_user_style(user_id, existing_style)
            
            logger.info(f"[用户风格] 用户风格更新完成: {user_id}")
            
        except Exception as e:
            logger.error(f"[用户风格] 用户风格更新失败: {user_id}, {e}")
    
    async def _learn_style_from_scratch(self, updates: List[UserStyleUpdateRequest]) -> UserStyleFeature:
        """从头学习用户风格"""
        conversations = [
            {"user_input": u.user_input, "ai_response": u.ai_response}
            for u in updates
        ]
        
        return await self.analyze_style_from_conversations(conversations)
    
    async def _learn_style_incremental(self, existing_style: UserStyleFeature, 
                                      updates: List[UserStyleUpdateRequest]) -> UserStyleFeature:
        """增量学习用户风格"""
        # 将新对话融入现有风格
        new_vocab = []
        new_patterns = []
        new_emotions = []
        
        for update in updates:
            # 简单提取新词汇（实际应该用NLP）
            new_vocab.extend(update.user_input.split()[:3])
            if "！" in update.user_input or "哇" in update.user_input:
                new_emotions.append("感叹")
            if "？" in update.user_input or "吗" in update.user_input:
                new_patterns.append("疑问")
        
        # 合并特征
        merged_vocab = list(set(existing_style.vocabulary_preferences + new_vocab))[:20]
        merged_patterns = list(set(existing_style.sentence_patterns + new_patterns))[:10]
        merged_emotions = list(set(existing_style.emotional_expressions + new_emotions))[:10]
        
        return UserStyleFeature(
            language_style=existing_style.language_style,
            vocabulary_preferences=merged_vocab,
            sentence_patterns=merged_patterns,
            emotional_expressions=merged_emotions,
            common_topics=existing_style.common_topics,
            interaction_style=existing_style.interaction_style
        )
    
    async def analyze_style_from_conversations(self, conversations: List[Dict[str, str]]) -> UserStyleFeature:
        """从对话历史分析用户风格"""
        try:
            conv_text = "\n".join([
                f"用户: {c.get('user_input', '')}\nAI: {c.get('ai_response', '')}"
                for c in conversations
            ])
            
            system_prompt = """你是一个用户风格分析专家。根据对话历史，分析用户的语言风格特征。
要求：
1. 分析用词偏好、句式特征、情感表达方式
2. 以JSON格式返回，不要有其他内容"""
            
            user_prompt = f"""根据以下对话历史，分析用户的语言风格特征：

{conv_text}

请生成JSON格式数据，包含:
- language_style: 语言风格描述 (如: 简洁幽默、文艺小清新、网络用语多等)
- vocabulary_preferences: 用词偏好列表 (3-8个常用词)
- sentence_patterns: 句式偏好列表 (2-4种常用句式)
- emotional_expressions: 情感表达方式列表 (2-4种)
- common_topics: 常用话题列表 (3-5个)
- interaction_style: 互动风格描述

请生成JSON格式数据。"""
            
            llm_request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1024,
                provider=self.default_provider,
                model=self.default_model,
                source="user_style"
            )
            
            response = await llm_client_singleton.call_llm(llm_request)
            
            if isinstance(response, dict):
                text = response.get("text", "").strip()
            else:
                text = str(response)
            
            # 解析JSON
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            return UserStyleFeature(
                language_style=data.get("language_style", "一般"),
                vocabulary_preferences=data.get("vocabulary_preferences", []),
                sentence_patterns=data.get("sentence_patterns", []),
                emotional_expressions=data.get("emotional_expressions", []),
                common_topics=data.get("common_topics", []),
                interaction_style=data.get("interaction_style", "")
            )
            
        except Exception as e:
            logger.error(f"[用户风格] 风格分析失败: {e}")
            return UserStyleFeature(
                language_style="一般",
                vocabulary_preferences=[],
                sentence_patterns=[],
                emotional_expressions=[],
                common_topics=[],
                interaction_style=""
            )
    
    async def generate_style_prompt(self, config: StylePromptConfig) -> StylePromptResponse:
        """
        生成风格适配的提示词
        
        合并用户画像上下文和用户风格指导
        """
        user_style = await self.get_user_style(config.user_id)
        
        if user_style is None:
            logger.debug(f"[用户风格] 无用户风格数据: {config.user_id}")
            return StylePromptResponse(
                user_id=config.user_id,
                personalized_prompt=config.base_prompt,
                style_applied=False,
                components={}
            )
        
        # 构建风格指导
        style_guide = ""
        if user_style.language_style:
            style_guide += f"\n【语言风格】{user_style.language_style}"
        
        if user_style.vocabulary_preferences:
            style_guide += f"\n【用词偏好】可以使用: {', '.join(user_style.vocabulary_preferences[:5])}"
        
        if user_style.sentence_patterns:
            style_guide += f"\n【句式偏好】{', '.join(user_style.sentence_patterns[:3])}"
        
        if user_style.emotional_expressions:
            style_guide += f"\n【情感表达】{', '.join(user_style.emotional_expressions[:3])}"
        
        # 合并用户画像上下文
        profile_context = config.user_profile_context or ""
        
        # 构建完整提示词
        components = {}
        if profile_context:
            components["profile"] = f"【用户画像背景】{profile_context}"
        if style_guide:
            components["style"] = f"【回复风格指导】{style_guide.strip()}"
        
        personalized_prompt = config.base_prompt
        if components.get("profile"):
            personalized_prompt = components["profile"] + "\n\n" + personalized_prompt
        if components.get("style"):
            personalized_prompt += "\n\n" + components["style"]
        
        return StylePromptResponse(
            user_id=config.user_id,
            personalized_prompt=personalized_prompt,
            style_applied=True,
            components=components
        )
    
    async def analyze_user_style(self, request: UserStyleAnalysisRequest) -> UserStyleAnalysisResponse:
        """分析用户风格（一次性分析）"""
        start_time = time.time()
        
        try:
            logger.info(f"[用户风格] 分析用户风格: {request.user_id}")
            
            style = await self.analyze_style_from_conversations(request.conversation_history)
            
            processing_time = time.time() - start_time
            
            return UserStyleAnalysisResponse(
                user_id=request.user_id,
                analysis=style,
                confidence=0.8,
                sample_vocabulary=style.vocabulary_preferences[:5],
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"[用户风格] 分析失败: {e}")
            return UserStyleAnalysisResponse(
                user_id=request.user_id,
                analysis=UserStyleFeature(
                    language_style="一般",
                    vocabulary_preferences=[],
                    sentence_patterns=[],
                    emotional_expressions=[],
                    common_topics=[],
                    interaction_style=""
                ),
                confidence=0.0,
                processing_time=time.time() - start_time
            )


# 创建全局实例
user_style_learning_service = UserStyleLearningService()
