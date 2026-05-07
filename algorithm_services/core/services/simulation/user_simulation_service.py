"""用户模拟数据服务 - 用于User Knowledge Graph冷启动"""
import asyncio
import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.api.schemas.feature_schemas.user_simulation_schema import (
    SimulatedUser,
    SimulatedUserProfile,
    SimulatedUserConversation,
    SimulatedUserStyle,
    SimulatedUserKGConnection,
    SimulatedConversationTurn,
    SimulationConfig,
    SimulationResult,
)


logger = get_logger(__name__)


class UserSimulationService:
    """
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    用户模拟数据服务
    
    用于User Knowledge Graph冷启动，生成模拟用户数据：
    - 用户画像
    - 对话历史
    - 用户风格
    - 知识图谱关联
    
    特点：
    - 使用不同提示词和LLM API
    - 批量生成节省时间和成本
    - 支持自定义配置
    """
    
    def __init__(self):
        self.default_config = SimulationConfig()
    
    def _generate_user_profile_prompt(self, index: int) -> Dict[str, str]:
        """生成用户画像的提示词"""
        system_prompt = """你是一个用户画像生成专家。根据给定的用户编号，生成合理的用户画像数据。
要求：
1. 生成的用户画像要多样化、真实
2. 包含年龄、性别、职业、兴趣爱好、性格特征
3. 以JSON格式返回，不要有其他内容"""
        
        user_prompt = f"""请为用户编号{index}生成一个用户画像，包含以下字段：
- user_id: 用户ID (格式: sim_user_编号)
- name: 用户名 (中文名)
- age_range: 年龄范围 (如: 18-25, 26-35, 36-45, 46-55, 56+)
- gender: 性别 (男/女)
- occupation: 职业
- interests: 兴趣爱好列表 (3-5个)
- personality: 性格特征字典

请生成JSON格式数据。"""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
    
    def _generate_conversation_prompt(self, profile: Dict[str, Any], turn_index: int, history: List[Dict]) -> Dict[str, str]:
        """生成对话的提示词"""
        history_text = ""
        if history:
            history_text = "\n历史对话:\n"
            for h in history[-3:]:
                history_text += f"用户: {h['user']}\nAI: {h['ai']}\n"
        
        system_prompt = """你是一个对话生成专家。根据用户画像和历史对话，生成符合用户特征的对话。
要求：
1. 生成的用户输入要符合用户画像中的特征
2. 生成的AI回复要自然、符合上下文
3. 以JSON格式返回，不要有其他内容"""
        
        user_prompt = f"""基于以下用户画像生成第{turn_index+1}轮对话：

用户画像:
- 姓名: {profile.get('name', '用户')}
- 年龄: {profile.get('age_range', '未知')}
- 职业: {profile.get('occupation', '未知')}
- 兴趣爱好: {', '.join(profile.get('interests', []))}
- 性格: {json.dumps(profile.get('personality', {}), ensure_ascii=False)}
{history_text}

请生成JSON格式数据，包含:
- user_input: 用户输入 (一句话，符合用户特征)
- ai_response: AI回复 (自然流畅)

请生成JSON格式数据。"""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
    
    def _generate_user_style_prompt(self, conversations: List[Dict[str, Any]]) -> Dict[str, str]:
        """生成用户风格的提示词"""
        conv_text = "\n".join([
            f"用户: {c['user_input']}\nAI: {c['ai_response']}"
            for c in conversations
        ])
        
        system_prompt = """你是一个用户风格分析专家。根据对话历史，分析用户的语言风格特征。
要求：
1. 分析用词偏好、句式特征、情感表达方式
2. 以JSON格式返回，不要有其他内容"""
        
        user_prompt = f"""根据以下对话历史，分析用户的语言风格特征：

{conv_text}

请生成JSON格式数据，包含:
- user_id: 用户ID
- language_style: 语言风格描述 (如: 简洁幽默、文艺小清新、网络用语多等)
- vocabulary_preferences: 用词偏好列表 (3-5个常用词)
- sentence_patterns: 句式偏好列表 (2-3种常用句式)
- emotional_expressions: 情感表达方式列表 (2-3种)
- common_topics: 常用话题列表 (3-5个)

请生成JSON格式数据。"""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
    
    def _generate_kg_connection_prompt(self, profile: Dict[str, Any], style: Dict[str, Any], conversations: List[Dict]) -> Dict[str, str]:
        """生成知识图谱关联的提示词"""
        topics = profile.get('interests', []) + style.get('common_topics', [])
        
        system_prompt = """你是一个知识图谱构建专家。根据用户画像和对话，提取用户关注的实体和关系。
要求：
1. 提取用户提到的实体（人物、地点、事件、概念等）
2. 建立实体间的关联关系
3. 以JSON格式返回，不要有其他内容"""
        
        user_prompt = f"""根据以下信息，提取用户关注的核心实体和关系：

用户画像:
- 兴趣爱好: {', '.join(profile.get('interests', []))}
- 职业: {profile.get('occupation', '未知')}

语言风格:
- 常用话题: {', '.join(style.get('common_topics', []))}

对话内容:
{chr(10).join([f"- {c['user_input']}" for c in conversations[:5]])}

请生成JSON格式数据，包含:
- user_id: 用户ID
- entities: 实体列表，每个实体包含 name, type, description
- relationships: 关系列表，每个关系包含 source, target, type

请生成JSON格式数据。"""
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
    
    async def _call_llm(self, prompt: Dict[str, str], provider: str = "aliyun", model: str = "qwen-flash", max_retries: int = 3) -> Dict[str, Any]:
        """调用LLM生成数据，支持重试机制"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                llm_request = LLMRequest(
                    system_prompt=prompt["system_prompt"],
                    user_prompt=prompt["user_prompt"],
                    temperature=0.7,
                    max_tokens=2048,
                    provider=provider,
                    model=model,
                    source="user_simulation"
                )
                
                response = await llm_client_singleton.call_llm(llm_request)
                
                if isinstance(response, dict):
                    text = response.get("text", "")
                else:
                    text = str(response)
                
                # 检查响应是否为空
                if not text or not text.strip():
                    if attempt < max_retries - 1:
                        logger.warning(f"[用户模拟] LLM返回空响应，第{attempt + 1}次重试...")
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                        continue
                    logger.warning(f"[用户模拟] LLM返回空响应，已达最大重试次数")
                    return {}
                
                # 尝试解析JSON
                text = text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                
                text = text.strip()
                
                # 再次检查清理后的文本是否为空
                if not text:
                    if attempt < max_retries - 1:
                        logger.warning(f"[用户模拟] LLM返回内容清理后为空，第{attempt + 1}次重试...")
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                        continue
                    logger.warning(f"[用户模拟] LLM返回内容清理后为空，已达最大重试次数")
                    return {}
                
                return json.loads(text)
                
            except json.JSONDecodeError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"[用户模拟] LLM返回非JSON格式: {e}, 第{attempt + 1}次重试...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
                logger.error(f"[用户模拟] LLM返回非JSON格式: {e}, 返回内容: {text[:100] if text else 'empty'}，已达最大重试次数")
                return {}
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"[用户模拟] LLM调用失败: {e}, 第{attempt + 1}次重试...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
                logger.error(f"[用户模拟] LLM调用失败: {e}，已达最大重试次数")
                return {}
        
        return {}
    
    async def generate_single_user(self, user_index: int, config: SimulationConfig) -> Optional[SimulatedUser]:
        """生成单个模拟用户"""
        try:
            logger.info(f"[用户模拟] 开始生成用户 {user_index}")
            
            # 1. 生成用户画像
            profile_prompt = self._generate_user_profile_prompt(user_index)
            profile_data = await self._call_llm(profile_prompt, config.provider, config.model)
            
            if not profile_data:
                logger.warning(f"[用户模拟] 用户 {user_index} 画像生成失败")
                return None
            
            profile_data['user_id'] = f"sim_user_{user_index}"
            profile = SimulatedUserProfile(**profile_data)
            
            # 2. 生成对话历史
            conversation_turns = []
            for turn_idx in range(config.conversation_turns):
                history = [{"user": t.user_input, "ai": t.ai_response} for t in conversation_turns]
                conv_prompt = self._generate_conversation_prompt(
                    profile_data, turn_idx, history
                )
                conv_data = await self._call_llm(conv_prompt, config.provider, config.model)
                
                if conv_data:
                    turn = SimulatedConversationTurn(
                        turn_index=turn_idx,
                        user_input=conv_data.get("user_input", ""),
                        ai_response=conv_data.get("ai_response", ""),
                        timestamp=datetime.now().isoformat()
                    )
                    conversation_turns.append(turn)
            
            conversation = SimulatedUserConversation(
                user_id=profile.user_id,
                conversation_id=str(uuid.uuid4()),
                turns=conversation_turns,
                total_turns=len(conversation_turns)
            )
            
            # 3. 生成用户风格
            style_prompt = self._generate_user_style_prompt([
                {"user_input": t.user_input, "ai_response": t.ai_response}
                for t in conversation_turns
            ])
            style_data = await self._call_llm(style_prompt, config.provider, config.model)
            
            if not style_data:
                style_data = {"user_id": profile.user_id, "language_style": "一般", "vocabulary_preferences": [], "sentence_patterns": [], "emotional_expressions": [], "common_topics": []}
            
            style_data['user_id'] = profile.user_id
            style = SimulatedUserStyle(**style_data)
            
            # 4. 生成知识图谱关联
            kg_prompt = self._generate_kg_connection_prompt(
                profile_data, style_data,
                [{"user_input": t.user_input, "ai_response": t.ai_response} for t in conversation_turns]
            )
            kg_data = await self._call_llm(kg_prompt, config.provider, config.model)
            
            if not kg_data:
                kg_data = {"user_id": profile.user_id, "entities": [], "relationships": []}
            
            kg_data['user_id'] = profile.user_id
            knowledge_graph = SimulatedUserKGConnection(**kg_data)
            
            # 5. 组装完整用户数据
            user = SimulatedUser(
                profile=profile,
                conversation=conversation,
                style=style,
                knowledge_graph=knowledge_graph
            )
            
            logger.info(f"[用户模拟] 用户 {user_index} 生成完成")
            return user
            
        except Exception as e:
            logger.error(f"[用户模拟] 生成用户 {user_index} 失败: {e}")
            return None
    
    async def generate_batch_users(self, config: SimulationConfig) -> SimulationResult:
        """批量生成模拟用户"""
        try:
            logger.info(f"[用户模拟] 开始批量生成 {config.user_count} 个用户")
            
            all_users = []
            completed = 0
            
            # 分批处理
            for batch_start in range(0, config.user_count, config.batch_size):
                batch_end = min(batch_start + config.batch_size, config.user_count)
                logger.info(f"[用户模拟] 处理批次: {batch_start}-{batch_end}")
                
                # 并行生成批次内用户
                tasks = [
                    self.generate_single_user(i, config)
                    for i in range(batch_start, batch_end)
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, SimulatedUser):
                        all_users.append(result)
                        completed += 1
                    elif isinstance(result, Exception):
                        logger.error(f"[用户模拟] 生成失败: {result}")
                
                logger.info(f"[用户模拟] 进度: {completed}/{config.user_count}")
            
            logger.info(f"[用户模拟] 完成，总计生成 {len(all_users)} 个用户")
            
            return SimulationResult(
                success=True,
                users=all_users,
                total_generated=len(all_users),
                progress=None
            )
            
        except Exception as e:
            logger.error(f"[用户模拟] 批量生成失败: {e}")
            return SimulationResult(
                success=False,
                users=[],
                total_generated=0,
                error_message=str(e)
            )
    
    async def generate_users_async(self, config: SimulationConfig) -> SimulationResult:
        """异步生成用户（后台运行）"""
        return await self.generate_batch_users(config)


# 创建全局实例
user_simulation_service = UserSimulationService()
