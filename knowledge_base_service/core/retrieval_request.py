"""
检索请求模型
定义 Algorithm Service → Knowledge Base 的数据传递格式
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    """意图类型"""
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    DEFINITION = "definition"
    HOWTO = "howto"
    PRICE = "price"
    SAFETY = "safety"
    GENERAL = "general"


@dataclass
class Entity:
    """实体"""
    text: str
    type: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0


@dataclass
class Intent:
    """意图"""
    type: IntentType
    slots: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class Constraints:
    """约束条件"""
    price_range: Optional[tuple] = None
    brands: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    efficacy: Optional[List[str]] = None
    skin_type: Optional[List[str]] = None
    ingredients_include: Optional[List[str]] = None
    ingredients_exclude: Optional[List[str]] = None


@dataclass
class UserProfile:
    """用户画像"""
    user_id: Optional[str] = None
    skin_type: Optional[str] = None
    age_range: Optional[str] = None
    preferences: List[str] = field(default_factory=list)
    history_ids: List[str] = field(default_factory=list)
    clicked_ids: List[str] = field(default_factory=list)


@dataclass
class Context:
    """对话上下文"""
    history: List[Dict[str, str]] = field(default_factory=list)
    mentioned_entities: List[Entity] = field(default_factory=list)
    mentioned_products: List[str] = field(default_factory=list)
    current_topic: Optional[str] = None


@dataclass
class RetrievalRequest:
    """
    检索请求
    
    Algorithm Service 传递给 Knowledge Base 的完整信息
    """
    query: str
    resolved_query: Optional[str] = None
    entities: List[Entity] = field(default_factory=list)
    intent: Optional[Intent] = None
    constraints: Optional[Constraints] = None
    context: Optional[Context] = None
    user_profile: Optional[UserProfile] = None
    
    top_k: int = 10
    enable_rewrite: bool = True
    enable_rerank: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "resolved_query": self.resolved_query,
            "entities": [
                {"text": e.text, "type": e.type, "confidence": e.confidence}
                for e in self.entities
            ],
            "intent": {
                "type": self.intent.type.value if self.intent else "general",
                "slots": self.intent.slots if self.intent else {},
                "confidence": self.intent.confidence if self.intent else 0.0
            } if self.intent else None,
            "constraints": {
                "price_range": self.constraints.price_range,
                "brands": self.constraints.brands,
                "categories": self.constraints.categories,
                "efficacy": self.constraints.efficacy,
                "skin_type": self.constraints.skin_type,
                "ingredients_include": self.constraints.ingredients_include,
                "ingredients_exclude": self.constraints.ingredients_exclude,
            } if self.constraints else None,
            "context": {
                "history": self.context.history,
                "mentioned_entities": [
                    {"text": e.text, "type": e.type}
                    for e in self.context.mentioned_entities
                ],
                "mentioned_products": self.context.mentioned_products,
                "current_topic": self.context.current_topic,
            } if self.context else None,
            "user_profile": {
                "user_id": self.user_profile.user_id,
                "skin_type": self.user_profile.skin_type,
                "age_range": self.user_profile.age_range,
                "preferences": self.user_profile.preferences,
                "history_ids": self.user_profile.history_ids,
                "clicked_ids": self.user_profile.clicked_ids,
            } if self.user_profile else None,
            "top_k": self.top_k,
            "enable_rewrite": self.enable_rewrite,
            "enable_rerank": self.enable_rerank,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalRequest":
        """从字典创建"""
        entities = [
            Entity(
                text=e.get("text", ""),
                type=e.get("type", ""),
                confidence=e.get("confidence", 1.0)
            )
            for e in data.get("entities", [])
        ]
        
        intent_data = data.get("intent")
        intent = None
        if intent_data:
            intent = Intent(
                type=IntentType(intent_data.get("type", "general")),
                slots=intent_data.get("slots", {}),
                confidence=intent_data.get("confidence", 1.0)
            )
        
        constraints_data = data.get("constraints")
        constraints = None
        if constraints_data:
            constraints = Constraints(
                price_range=constraints_data.get("price_range"),
                brands=constraints_data.get("brands"),
                categories=constraints_data.get("categories"),
                efficacy=constraints_data.get("efficacy"),
                skin_type=constraints_data.get("skin_type"),
                ingredients_include=constraints_data.get("ingredients_include"),
                ingredients_exclude=constraints_data.get("ingredients_exclude"),
            )
        
        context_data = data.get("context")
        context = None
        if context_data:
            context = Context(
                history=context_data.get("history", []),
                mentioned_entities=[
                    Entity(text=e.get("text", ""), type=e.get("type", ""))
                    for e in context_data.get("mentioned_entities", [])
                ],
                mentioned_products=context_data.get("mentioned_products", []),
                current_topic=context_data.get("current_topic"),
            )
        
        profile_data = data.get("user_profile")
        user_profile = None
        if profile_data:
            user_profile = UserProfile(
                user_id=profile_data.get("user_id"),
                skin_type=profile_data.get("skin_type"),
                age_range=profile_data.get("age_range"),
                preferences=profile_data.get("preferences", []),
                history_ids=profile_data.get("history_ids", []),
                clicked_ids=profile_data.get("clicked_ids", []),
            )
        
        return cls(
            query=data.get("query", ""),
            resolved_query=data.get("resolved_query"),
            entities=entities,
            intent=intent,
            constraints=constraints,
            context=context,
            user_profile=user_profile,
            top_k=data.get("top_k", 10),
            enable_rewrite=data.get("enable_rewrite", True),
            enable_rerank=data.get("enable_rerank", True),
        )
    
    @classmethod
    def simple(cls, query: str, top_k: int = 10) -> "RetrievalRequest":
        """创建简单请求"""
        return cls(query=query, top_k=top_k)
