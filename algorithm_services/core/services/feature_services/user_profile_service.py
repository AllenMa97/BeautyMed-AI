# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import json
from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.core.prompts.features.user_profile_prompt import get_user_profile_prompt


logger = get_logger(__name__)



# 可配置当前Service的默认服务商/模型（也可从配置文件读取）
DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 快速
LLM_REQUEST_MAX_TOKENS = int(4096) # 32768是Qwen flash模型的输入+输出的总token上限
LLM_REQUEST_TEMPERATURE = float(0.3) # 翻译场景优先准确性，降低随机性


class UserProfileService:
    """
    用户画像服务
    用于分析和维护用户画像信息
    """
    
    def __init__(self):
        self.DEFAULT_PROVIDER = DEFAULT_PROVIDER
        self.DEFAULT_MODEL = DEFAULT_MODEL
        self.LLM_REQUEST_MAX_TOKENS = LLM_REQUEST_MAX_TOKENS
        self.LLM_REQUEST_TEMPERATURE = LLM_REQUEST_TEMPERATURE
    
    async def update_user_profile(self, 
                                current_profile: Dict[str, Any], 
                                user_input: str, 
                                ai_response: str) -> Dict[str, Any]:
        """
        根据最新对话更新用户画像
        """
        try:
            tmp = get_user_profile_prompt(
                current_profile=str(current_profile),
                user_input=user_input,
                ai_response=ai_response
            )
            # 构建LLM请求
            llm_request = LLMRequest(
                system_prompt=tmp["system_prompt"],
                user_prompt=tmp["user_prompt"],
                temperature=self.LLM_REQUEST_TEMPERATURE,
                max_tokens=self.LLM_REQUEST_MAX_TOKENS,
                provider=self.DEFAULT_PROVIDER,
                model=self.DEFAULT_MODEL,
                enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
            )
            
            # 调用LLM获取更新后的用户画像
            response = await llm_client_singleton.call_llm(llm_request)
            
            # 解析返回结果
            try:
                # 如果response已经是字典，直接使用
                if isinstance(response, dict):
                    updated_profile = response
                else:
                    # 尝试解析JSON格式的返回
                    updated_profile = json.loads(response)
                
                # 确保包含最后更新时间
                updated_profile["last_updated"] = datetime.now().isoformat()
                return updated_profile
            except json.JSONDecodeError:
                # 如果不是JSON格式，返回当前画像
                logger.warning("LLM返回的用户画像不是有效的JSON格式")
                current_profile["last_updated"] = datetime.now().isoformat()
                return current_profile
            except TypeError:
                # 如果response类型不正确，返回当前画像
                logger.warning("LLM返回的用户画像类型不正确")
                current_profile["last_updated"] = datetime.now().isoformat()
                return current_profile
                
        except Exception as e:
            logger.error(f"更新用户画像失败: {e}")
            # 发生错误时返回当前画像
            current_profile["last_updated"] = datetime.now().isoformat()
            return current_profile
    
    async def get_personalized_context(self, profile: Dict[str, Any]) -> str:
        """
        根据用户画像生成个性化上下文信息
        """
        if not profile:
            return "用户画像信息暂缺"
        
        personalized_info = []
        
        if profile.get("personal_preferences"):
            personalized_info.append(f"用户偏好: {profile['personal_preferences']}")
        
        if profile.get("beauty_habits"):
            personalized_info.append(f"美妆习惯: {profile['beauty_habits']}")
        
        if profile.get("fashion_style"):
            personalized_info.append(f"时尚风格: {profile['fashion_style']}")
        
        if profile.get("lifestyle"):
            personalized_info.append(f"生活方式: {profile['lifestyle']}")
        
        if profile.get("topic_tendency"):
            personalized_info.append(f"话题倾向: {profile['topic_tendency']}")
        
        if profile.get("interaction_style"):
            personalized_info.append(f"互动风格: {profile['interaction_style']}")
        
        if profile.get("social_preferences"):
            personalized_info.append(f"社交偏好: {profile['social_preferences']}")
        
        if profile.get("consumption_habits"):
            personalized_info.append(f"消费习惯: {profile['consumption_habits']}")
        
        if profile.get("entertainment_preferences"):
            personalized_info.append(f"娱乐偏好: {profile['entertainment_preferences']}")
        
        return "；".join(personalized_info) if personalized_info else "用户画像信息暂缺"


# 创建全局实例
user_profile_service = UserProfileService()