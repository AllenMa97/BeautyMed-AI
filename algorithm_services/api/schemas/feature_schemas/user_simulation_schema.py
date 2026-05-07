"""用户模拟数据相关的数据模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SimulatedUserProfile(BaseModel):
    """模拟用户画像"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., description="用户名")
    age_range: str = Field(..., description="年龄范围")
    gender: str = Field(..., description="性别")
    occupation: str = Field(..., description="职业")
    interests: List[str] = Field(default_factory=list, description="兴趣爱好")
    personality: Dict[str, Any] = Field(default_factory=dict, description="性格特征")


class SimulatedConversationTurn(BaseModel):
    """模拟对话轮次"""
    turn_index: int = Field(..., description="轮次索引")
    user_input: str = Field(..., description="用户输入")
    ai_response: str = Field(..., description="AI回复")
    timestamp: Optional[str] = Field(None, description="时间戳")


class SimulatedUserConversation(BaseModel):
    """模拟用户对话历史"""
    user_id: str = Field(..., description="用户ID")
    conversation_id: str = Field(..., description="对话ID")
    turns: List[SimulatedConversationTurn] = Field(default_factory=list, description="对话轮次")
    total_turns: int = Field(0, description="总轮次")


class SimulatedUserStyle(BaseModel):
    """模拟用户风格"""
    user_id: str = Field(..., description="用户ID")
    language_style: str = Field(..., description="语言风格")
    vocabulary_preferences: List[str] = Field(default_factory=list, description="用词偏好")
    sentence_patterns: List[str] = Field(default_factory=list, description="句式偏好")
    emotional_expressions: List[str] = Field(default_factory=list, description="情感表达方式")
    common_topics: List[str] = Field(default_factory=list, description="常用话题")


class SimulatedUserKGConnection(BaseModel):
    """模拟用户-知识图谱关联"""
    user_id: str = Field(..., description="用户ID")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="关注的实体")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="关系")


class SimulatedUser(BaseModel):
    """完整模拟用户数据"""
    profile: SimulatedUserProfile = Field(..., description="用户画像")
    conversation: SimulatedUserConversation = Field(..., description="对话历史")
    style: SimulatedUserStyle = Field(..., description="用户风格")
    knowledge_graph: SimulatedUserKGConnection = Field(..., description="知识图谱关联")


class SimulationConfig(BaseModel):
    """模拟配置"""
    user_count: int = Field(200, description="生成用户数量")
    conversation_turns: int = Field(10, description="每个用户的对话轮次")
    provider: str = Field("aliyun", description="LLM服务商")
    model: str = Field("qwen-flash", description="LLM模型")
    batch_size: int = Field(10, description="批处理大小")


class SimulationProgress(BaseModel):
    """模拟进度"""
    total_users: int = Field(..., description="总用户数")
    completed_users: int = Field(..., description="已完成用户数")
    progress_percentage: float = Field(..., description="进度百分比")
    status: str = Field(..., description="状态: running/completed/failed")


class SimulationResult(BaseModel):
    """模拟结果"""
    success: bool = Field(..., description="是否成功")
    users: List[SimulatedUser] = Field(default_factory=list, description="生成的模拟用户")
    total_generated: int = Field(0, description="总生成数量")
    progress: Optional[SimulationProgress] = Field(None, description="进度信息")
    error_message: Optional[str] = Field(None, description="错误信息")
