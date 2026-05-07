# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from .feature_schemas.dialog_summary_schema import DialogSummaryRequest, DialogSummaryResponse
from .feature_schemas.entity_relation_extraction_schemas import EntityRelationExtractionRequest, EntityRelationExtractionResponse
from .feature_schemas.free_chat_schemas import FreeChatRequest, FreeChatResponse
from .feature_schemas.intent_clarify_schemas import IntentClarifyRequest, IntentClarifyResponse
from .feature_schemas.intent_recognize_schemas import IntentRecognizeRequest, IntentRecognizeResponse
from .feature_schemas.text_summary_schemas import TextSummaryRequest, TextSummaryResponse
from .feature_schemas.knowledge_retrieval_schemas import KnowledgeRetrievalRequest, KnowledgeRetrievalResponse
from .feature_schemas.knowledge_chat_schemas import KnowledgeChatRequest, KnowledgeChatResponse

SCHEMA_MAPPING = {
    "dialog_summary": {"description": "对话摘要生成器", "input": DialogSummaryRequest, "output": DialogSummaryResponse},
    "entity_relation_extraction": {"description": "实体与关系联合抽取", "input": EntityRelationExtractionRequest, "output": EntityRelationExtractionResponse},
    "free_chat": {"description": "闲聊", "input": FreeChatRequest, "output": FreeChatResponse},
    "intent_clarify": {"description": "意图澄清", "input": IntentClarifyRequest, "output": IntentClarifyResponse},
    "intent_recognize": {"description": "意图识别", "input": IntentRecognizeRequest, "output": IntentRecognizeResponse},
    "text_summary": {"description": "文本摘要生成器", "input": TextSummaryRequest, "output": TextSummaryResponse},
    "knowledge_retrieval": {"description": "知识检索", "input": KnowledgeRetrievalRequest, "output": KnowledgeRetrievalResponse},
    "knowledge_chat": {"description": "知识问答", "input": KnowledgeChatRequest, "output": KnowledgeChatResponse},
}

def get_pydantic_json_schema(model) -> str:
    return model.model_json_schema()

def get_schema_by_func_name(func_name: str) -> dict:
    if func_name not in SCHEMA_MAPPING:
        raise ValueError(f"功能名{func_name}未在SCHEMA_MAPPING中注册，请检查schema_kit.py")
    model_map = SCHEMA_MAPPING[func_name]
    return {
        "description": model_map["description"],
        "input_schema": get_pydantic_json_schema(model_map["input"]),
        "output_schema": get_pydantic_json_schema(model_map["output"])
    }
