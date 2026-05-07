# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
import asyncio
from datetime import datetime

from typing import Dict, Any, Optional

from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.core.prompts.features.correction_detection_prompt import get_correction_detection_prompt

logger = get_logger(__name__)


# 可配置当前Service的默认服务商/模型（也可从配置文件读取）

DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"  # 快速
LLM_REQUEST_MAX_TOKENS = int(4096) # 32768是Qwen flash模型的输入+输出的总token上限


# DEFAULT_PROVIDER = "lansee"
# DEFAULT_MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"
# LLM_REQUEST_MAX_TOKENS = int(512)


LLM_REQUEST_TEMPERATURE = 0.1  # 较低温度，确保判断准确性


class CorrectionDetectionService:
    """
    纠错检测服务
    用于检测用户是否在纠正AI之前提供的信息
    """
    
    def __init__(self):
        self.DEFAULT_PROVIDER = DEFAULT_PROVIDER
        self.DEFAULT_MODEL = DEFAULT_MODEL
        self.LLM_REQUEST_MAX_TOKENS = LLM_REQUEST_MAX_TOKENS
        self.LLM_REQUEST_TEMPERATURE = LLM_REQUEST_TEMPERATURE
    
    async def detect_correction(self, 
                              user_input: str, 
                              previous_ai_response: Optional[str] = None) -> Dict[str, Any]:
        """
        检测用户输入是否为纠正信息
        """
        try:
            # 构建提示词
            tmp = get_correction_detection_prompt(previous_ai_response, user_input)
            # 构建LLM请求
            llm_request = LLMRequest(
                system_prompt=tmp["system_prompt"],
                user_prompt=tmp["user_prompt"],
                temperature=self.LLM_REQUEST_TEMPERATURE,
                max_tokens=self.LLM_REQUEST_MAX_TOKENS,
                provider=self.DEFAULT_PROVIDER,
                model=self.DEFAULT_MODEL,
            )
            
            # 调用LLM进行纠错检测
            response = await llm_client_singleton.call_llm(llm_request)
            
            # 解析返回结果
            try:
                # 如果response已经是字典，直接使用
                if isinstance(response, dict):
                    result = response
                else:
                    result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # 如果不是JSON格式，使用规则基础的检测方法
                logger.warning("LLM返回的纠错检测结果不是有效的JSON格式，使用规则基础检测")
                return self._rule_based_correction_detection(user_input, previous_ai_response)
            except TypeError:
                # 如果response类型不正确，使用规则基础的检测方法
                logger.warning("LLM返回的纠错检测结果类型不正确，使用规则基础检测")
                return self._rule_based_correction_detection(user_input, previous_ai_response)
                
        except Exception as e:
            logger.error(f"LLM纠错检测失败: {e}，使用规则基础检测")
            return self._rule_based_correction_detection(user_input, previous_ai_response)
    
    def _rule_based_correction_detection(self, 
                                       user_input: str, 
                                       previous_ai_response: Optional[str] = None) -> Dict[str, Any]:
        """
        规则基础的纠错检测（备用方案）
        """
        user_input_lower = user_input.lower()
        
        # 纠错关键词
        correction_keywords = [
            "不是", "不对", "错了", "纠正", "其实", "实际上", 
            "正确的是", "应该是", "准确的是", "真实的是",
            "你错了", "你搞错了", "你讲错了", "你回答错了"
        ]
        
        # 检测是否包含纠错关键词
        is_correction = any(keyword in user_input_lower for keyword in correction_keywords)

        return {
            "is_correction": is_correction,
            "correction_content": user_input if is_correction else "",
            "original_mistake": previous_ai_response or "",
            "confidence": 0.7 if is_correction else 0.1
        }


# 创建全局实例
correction_detection_service = CorrectionDetectionService()