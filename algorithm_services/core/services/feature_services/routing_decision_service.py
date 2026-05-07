"""
路由决策服务 - 判断是否需要规划和联网搜索

核心原则：
- need_plan=false 仅限：简单问候、确认、感谢、纯闲聊
- need_plan=true：其他所有情况，特别是需要专业知识的问题
- 宁可多规划也不要漏掉需要专业知识的场景
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.


import logging
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.core.prompts.features.routing_decision_prompt import get_routing_decision_prompt
from algorithm_services.utils.logger import get_logger
from algorithm_services.utils.performance_monitor import monitor_async

logger = get_logger(__name__)

DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"

NO_PLAN_PATTERNS = [
    "你好", "早上好", "晚安", "嗨", "hi", "hello", "在吗", "在不在", "在么",
    "谢谢", "OK", "好的", "收到", "明白", "知道", "感谢",
    "几点", "时间", "日期", "今天", "明天", "昨天", "后天",
    "天气", "温度", "晴", "雨", "雪", "风",
    "唱歌", "讲故事", "讲个笑话", "笑话",
    "计算", "1+1", "2*3",
]

NEED_SEARCH_PATTERNS = [
    "最新", "现在", "今天热搜", "当前热搜", "热搜",
    "股价", "股票", "期货", "新闻", "发生了什么", "怎么回事", "刚发生了什么",
    "谁", "什么是", "怎么做", "如何", "怎样",
    "查一下", "搜索", "找一下"
]


class RoutingDecisionService:
    """路由决策服务 - 判断是否需要规划和联网搜索"""

    @monitor_async(name="routing_decision_decide", log_threshold=1.0)
    async def decide(self, user_input: str) -> dict:
        """
        判断是否需要规划和联网搜索
        1. 先快速匹配词表（毫秒级）
        2. 词表未命中则调用 LLM 判断
        """
        user_input_lower = user_input.lower().strip()

        need_plan = True
        for pattern in NO_PLAN_PATTERNS:
            if pattern in user_input_lower:
                need_plan = False
                break

        need_search = False
        for pattern in NEED_SEARCH_PATTERNS:
            if pattern in user_input_lower:
                need_search = True
                break

        if need_plan and not need_search:
            llm_result = await self._llm_decide(user_input)
            
            if llm_result.get("need_plan") is not None:
                need_plan = llm_result["need_plan"]
            if llm_result.get("need_search") is not None:
                need_search = llm_result["need_search"]
            
            logger.info(f"路由决策(LLM): need_plan={need_plan}, need_search={need_search}")
            
            return {
                "need_plan": need_plan,
                "need_search": need_search,
                "method": "llm"
            }
        
        logger.info(f"路由决策(词表匹配): need_plan={need_plan}, need_search={need_search}")
        
        return {
            "need_plan": need_plan,
            "need_search": need_search,
            "method": "pattern_match"
        }

    @monitor_async(name="routing_decision_llm_decide", log_threshold=1.0)
    async def _llm_decide(self, user_input: str) -> dict:
        """LLM 判断是否需要规划和联网搜索"""
        try:
            prompt = get_routing_decision_prompt(user_input)
            llm_request = LLMRequest(
                system_prompt=prompt["system_prompt"],
                user_prompt=prompt["user_prompt"],
                temperature=0.1,
                max_tokens=64,
                provider=DEFAULT_PROVIDER,
                model=DEFAULT_MODEL,
                enable_context_cache=True  # 启用阿里云Context Cache（Microcompact）
            )

            result = await llm_client_singleton.call_llm(llm_request)

            if result and isinstance(result, dict):
                need_plan = result.get("need_plan", True)
                need_search = result.get("need_search", False)
                return {
                    "need_plan": bool(need_plan),
                    "need_search": bool(need_search),
                }
        except Exception as e:
            logger.warning(f"路由决策 LLM 分析失败: {e}")

        return {
            "need_plan": True,
            "need_search": False,
        }


routing_decision_service = RoutingDecisionService()
