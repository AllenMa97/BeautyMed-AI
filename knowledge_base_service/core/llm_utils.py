# Developer: 马赫·马智明
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
import re
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMUtils:
    """
    LLM 工具类
    提供共用LLM调用和响应解析功能
    """

    @staticmethod
    def parse_json_response(content: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        解析 LLM 返回的JSON响应

        Args:
            content: LLM 返回的内容
            default: 解析失败时返回的默认值

        Returns:
            解析后的字典
        """
        if default is None:
            default = {}

        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                if isinstance(result, dict):
                    return result
                else:
                    logger.warning(f"LLM 返回的不是字典类型: {type(result)}")
                    return default
            else:
                logger.warning(f"无法在响应中找到 JSON: {content[:200]}...")
                return default
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {str(e)}, 内容: {content[:200]}...")
            return default

    @staticmethod
    def parse_json_array_response(content: str, default: Optional[list] = None) -> list:
        """
        解析 LLM 返回的JSON数组响应

        Args:
            content: LLM 返回的内容
            default: 解析失败时返回的默认值

        Returns:
            解析后的列表
        """
        if default is None:
            default = []

        try:
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                if isinstance(result, list):
                    return result
                else:
                    logger.warning(f"LLM 返回的不是列表类型: {type(result)}")
                    return default
            else:
                logger.warning(f"无法在响应中找到 JSON 数组: {content[:200]}...")
                return default
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 数组解析失败: {str(e)}, 内容: {content[:200]}...")
            return default

    @staticmethod
    def extract_text_from_json_array(content: str, num_items: int = 5) -> list:
        """
        从文本中提取列表项(JSON解析失败时的备用方案)

        Args:
            content: LLM 返回的内容
            num_items: 最多提取的项目数

        Returns:
            提取的文本列表
        """
        items = []
        lines = content.split('\n')

        for line in lines:
            clean_line = line.strip()

            if clean_line.startswith(('"', "'")) and clean_line.endswith(('"', "'")):
                items.append(clean_line.strip('"\''))
            elif re.match(r'^\d+\.', clean_line):
                parts = clean_line.split('.', 1)
                if len(parts) > 1:
                    query = parts[1].strip().strip('"\'')
                    if query:
                        items.append(query)

            if len(items) >= num_items:
                break

        return items

    @staticmethod
    def create_default_credibility_score() -> Dict[str, Any]:
        """创建默认的可信度评分"""
        return {
            "credibility_score": 60,
            "professional_score": 60,
            "authority_score": 60,
            "logic_score": 60,
            "timeliness_score": 60,
            "objectivity_score": 60,
            "applicability_score": 60,
            "issues": ["无法解析 LLM 评估结果"],
            "suggestions": ["重新评估"]
        }

    @staticmethod
    def create_error_credibility_score(error: str) -> Dict[str, Any]:
        """创建错误时的可信度评分"""
        return {
            "credibility_score": 50,
            "professional_score": 50,
            "authority_score": 50,
            "logic_score": 50,
            "timeliness_score": 50,
            "objectivity_score": 50,
            "applicability_score": 50,
            "issues": [error],
            "suggestions": ["重新评估"]
        }

    @staticmethod
    def create_default_quality_check() -> Dict[str, Any]:
        """创建默认的质量检查结果"""
        return {
            'is_valid': False,
            'quality_score': 50,
            'issues': ['无法解析 LLM 响应'],
            'suggestions': ['重试']
        }

    @staticmethod
    def create_error_quality_check(error: str) -> Dict[str, Any]:
        """创建错误时的质量检查结果"""
        return {
            'is_valid': False,
            'quality_score': 30,
            'issues': [error],
            'suggestions': ['重试']
        }
