"""
联网搜索决策服务
异步分析用户输入是否需要联网搜索
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from pydantic import BaseModel, Field
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

SEARCH_SYSTEM_PROMPT = """
你是一个联网搜索决策助手。
判断用户输入是否需要联网搜索才能回答。

返回JSON格式：
{"need_search": true/false, "reason": "判断理由"}
"""

DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-vl-plus"  # 视觉模型，qwen3-vl-flash不存在

NO_SEARCH_PATTERNS = [
    "你好", "早上好", "晚安", "嗨", "hi", "hello", "在吗", "在么",
    "谢谢", "感谢", "OK", "好的", "收到", "明白", "知道",
    "几点", "时间", "日期", "今天", "明天", "昨天", "后天",
    "天气", "温度", "晴", "雨", "雪", "风",
    "唱歌", "讲故事", "讲个笑话", "笑话",
    "计算", "1+1", "2*3", "加减乘除"
]

NEED_SEARCH_PATTERNS = [
    "最新", "现在", "今天热搜", "当前热搜",
    "股价", "股票", "期货",
    "新闻", "发生了什么", "怎么回事",
    "谁", "什么是", "怎么做", "如何"
]


class SearchDecisionService:
    """联网搜索决策服务"""

    async def analyze(self, user_input: str) -> dict:
        """
        异步分析用户输入是否需要联网搜索
        """
        user_input_lower = user_input.lower().strip()
        
        # 快速规则匹配 - 明显不需要联网的情况
        for pattern in NO_SEARCH_PATTERNS:
            if pattern in user_input_lower:
                return {
                    "need_search": False,
                    "reason": f"快速匹配：包含常用词'{pattern}'，无需联网",
                    "method": "fast_rule"
                }
        
        # 快速规则匹配 - 明显需要联网的情况
        for pattern in NEED_SEARCH_PATTERNS:
            if pattern in user_input_lower:
                return {
                    "need_search": True,
                    "reason": f"快速匹配：包含关键词'{pattern}'，需要联网获取最新信息",
                    "method": "fast_rule"
                }
        
        # 短输入默认不联网（减少延迟）
        if len(user_input) <= 5:
            return {
                "need_search": False,
                "reason": "快速匹配：输入过短，默认不搜索",
                "method": "fast_rule"
            }
        
        # 调用 LLM 进行分析
        return await self._llm_analyze(user_input)

    async def _llm_analyze(self, user_input: str) -> dict:
        """LLM 分析（异步，使用更快的模型和超时）"""
        try:
            llm_request = LLMRequest(
                system_prompt=SEARCH_SYSTEM_PROMPT,
                user_prompt=f"判断以下用户输入是否需要联网搜索：\n{user_input}",
                temperature=0.1,
                max_tokens=128,
                provider=DEFAULT_PROVIDER,
                model=DEFAULT_MODEL
            )
            
            result = await llm_client_singleton.call_llm(llm_request)
            
            if result and isinstance(result, dict):
                return {
                    "need_search": result.get("need_search", False),
                    "reason": result.get("reason", ""),
                    "method": "llm"
                }
        except Exception as e:
            logger.warning(f"LLM 联网决策分析失败: {e}")
        
        return {
            "need_search": False,
            "reason": "LLM分析失败，默认不搜索",
            "method": "fallback"
        }


search_decision_service = SearchDecisionService()
