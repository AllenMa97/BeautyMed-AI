"""用户风格学习相关的数据模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class UserStyleFeature(BaseModel):
    """用户风格特征"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    language_style: str = Field(..., description="语言风格描述")
    vocabulary_preferences: List[str] = Field(default_factory=list, description="用词偏好")
    sentence_patterns: List[str] = Field(default_factory=list, description="句式偏好")
    emotional_expressions: List[str] = Field(default_factory=list, description="情感表达方式")
    common_topics: List[str] = Field(default_factory=list, description="常用话题")
    interaction_style: str = Field("", description="互动风格")


class UserStyleUpdateRequest(BaseModel):
    """用户风格更新请求"""
    user_id: str = Field(..., description="用户ID")
    user_input: str = Field(..., description="用户输入")
    ai_response: str = Field(..., description="AI回复")


class UserStyleResponse(BaseModel):
    """用户风格响应"""
    user_id: str = Field(..., description="用户ID")
    style: UserStyleFeature = Field(..., description="用户风格特征")
    confidence: float = Field(0.0, description="置信度")
    last_updated: str = Field(..., description="最后更新时间")


class UserStyleAnalysisRequest(BaseModel):
    """用户风格分析请求"""
    user_id: str = Field(..., description="用户ID")
    conversation_history: List[Dict[str, Any]] = Field(..., description="对话历史")


class UserStyleAnalysisResponse(BaseModel):
    """用户风格分析响应"""
    user_id: str = Field(..., description="用户ID")
    analysis: UserStyleFeature = Field(..., description="分析结果")
    confidence: float = Field(0.0, description="分析置信度")
    sample_vocabulary: List[str] = Field(default_factory=list, description="样本用词")
    processing_time: float = Field(0.0, description="处理时间")


class StylePromptConfig(BaseModel):
    """风格提示词配置"""
    user_id: str = Field(..., description="用户ID")
    base_prompt: str = Field("", description="基础提示词")
    user_profile_context: Optional[str] = Field(None, description="用户画像上下文")
    include_style_guide: bool = Field(True, description="是否包含风格指导")


class StylePromptResponse(BaseModel):
    """风格提示词响应"""
    user_id: str = Field(..., description="用户ID")
    personalized_prompt: str = Field(..., description="个性化提示词")
    style_applied: bool = Field(..., description="是否应用了风格")
    components: Dict[str, str] = Field(default_factory=dict, description="提示词组件")
