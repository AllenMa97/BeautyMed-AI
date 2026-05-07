"""
情感识别服务
识别用户输入中的情感状态，返回情感类别、强度和建议的回复语气
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.api.schemas.feature_schemas.emotion_recognition_schemas import (
    EmotionRecognitionRequest, EmotionRecognitionResponse, EmotionRecognitionResponseData
)
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 快速
LLM_REQUEST_TEMPERATURE = 0.3

EMOTION_SYSTEM_PROMPT = """你是一个情感分析专家。你的任务是从用户输入中识别情感状态。

情感类别包括：
- joy: 开心、愉悦、喜悦
- sadness: 难过、伤心、沮丧
- anger: 愤怒、生气、不满
- fear: 害怕、恐惧、焦虑
- surprise: 惊讶、意外
- disgust: 厌恶、反感
- neutral: 中性
- excitement: 兴奋、激动
- fatigue: 疲惫、累
- worry: 担心、忧虑

请分析用户输入，返回JSON格式：
{
  "primary_emotion": "主要情感类别",
  "emotion_intensity": 0.0-1.0的情感强度,
  "emotion_details": {
    "emotions": ["检测到的所有情感列表"],
    "reason": "判断理由"
  },
  "suggested_response_tone": "建议的回复语气如温暖/安慰/活泼/倾听等"
}
"""


class EmotionRecognitionService:
    """情感识别服务"""

    async def recognize(self, request: EmotionRecognitionRequest) -> EmotionRecognitionResponse:
        logger.info(f"情感识别服务收到请求")

        try:
            llm_request = LLMRequest(
                system_prompt=EMOTION_SYSTEM_PROMPT,
                user_prompt=f"请分析以下用户输入的情感：\n{request.user_input}\n\n上下文：{request.context}",
                temperature=LLM_REQUEST_TEMPERATURE,
                max_tokens=1024,
                response_format={"type": "json_object"},
                provider=DEFAULT_PROVIDER,
                model=DEFAULT_MODEL
            )

            result = await llm_client_singleton.call_llm(llm_request)

            if result:
                response_data = EmotionRecognitionResponseData(
                    primary_emotion=result.get("primary_emotion", "neutral"),
                    emotion_intensity=float(result.get("emotion_intensity", 0.5)),
                    emotion_details=result.get("emotion_details", {}),
                    suggested_response_tone=result.get("suggested_response_tone", "normal")
                )
            else:
                response_data = self._rule_based_recognition(request.user_input)

            return EmotionRecognitionResponse(data=response_data)

        except Exception as e:
            logger.warning(f"LLM情感识别失败，使用规则兜底: {e}")
            response_data = self._rule_based_recognition(request.user_input)
            return EmotionRecognitionResponse(data=response_data)

    def _rule_based_recognition(self, user_input: str) -> EmotionRecognitionResponseData:
        """基于规则的情感识别（兜底方案）"""
        text = user_input.lower()
        
        emotion_keywords = {
            "joy": ["开心", "高兴", "快乐", "棒", "太好了", "哈哈", "真好"],
            "sadness": ["难过", "伤心", "哭", "悲伤", "郁闷", "不爽", "烦"],
            "anger": ["生气", "愤怒", "讨厌", "滚", "气死了", "可恶"],
            "fear": ["害怕", "担心", "焦虑", "紧张", "怕", "不安"],
            "excitement": ["兴奋", "激动", "太棒了", "wow", "厉害"],
            "fatigue": ["累", "疲惫", "困", "好累", "好困", "没精力"],
            "worry": ["担心", "忧虑", "发愁", "怎么办", "愁"]
        }

        primary_emotion = "neutral"
        max_count = 0

        for emotion, keywords in emotion_keywords.items():
            count = sum(1 for kw in keywords if kw in text)
            if count > max_count:
                max_count = count
                primary_emotion = emotion

        intensity = min(max_count * 0.3, 1.0) if max_count > 0 else 0.3

        tone_map = {
            "joy": "活泼",
            "sadness": "温暖",
            "anger": "安抚",
            "fear": "安慰",
            "excitement": "共鸣",
            "fatigue": "关心",
            "worry": "关切"
        }

        return EmotionRecognitionResponseData(
            primary_emotion=primary_emotion,
            emotion_intensity=intensity,
            emotion_details={"emotions": [primary_emotion], "method": "rule_based"},
            suggested_response_tone=tone_map.get(primary_emotion, "normal")
        )


emotion_recognition_service = EmotionRecognitionService()
