"""内容检测协调器 - 联合判断模块"""
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from core.prompts.features.moderation import (
    get_political_moderation_prompt,
    get_violence_moderation_prompt,
    get_pornography_moderation_prompt,
    get_gambling_moderation_prompt,
    get_drug_moderation_prompt,
    get_hate_moderation_prompt,
    get_fake_moderation_prompt,
)
from core.moderation.keyword_detector import get_keyword_detector
from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest


logger = get_logger(__name__)


@dataclass
class ModerationResult:
    """检测结果数据类"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    category: str
    method: str
    is_violation: bool
    confidence: float
    details: Optional[Dict] = None


@dataclass
class OverallModerationResult:
    """总体检测结果"""
    is_violation: bool
    results: List[ModerationResult] = field(default_factory=list)
    violation_categories: List[str] = field(default_factory=list)
    confidence: float = 0.0
    processing_time: float = 0.0


class ModerationCoordinator:
    """内容检测协调器"""
    
    def __init__(self):
        self.keyword_detector = get_keyword_detector()
        
        self.llm_detectors = {
            'political': get_political_moderation_prompt,
            'violence': get_violence_moderation_prompt,
            'pornography': get_pornography_moderation_prompt,
            'gambling': get_gambling_moderation_prompt,
            'drug': get_drug_moderation_prompt,
            'hate': get_hate_moderation_prompt,
            'fake': get_fake_moderation_prompt,
        }
    
    def detect_by_keyword(self, text: str) -> List[ModerationResult]:
        """基于关键词检测"""
        logger.info(f"[模块化内容检测-关键词检测] 开始检测文本: {text[:50]}...")
        results = []
        keyword_result = self.keyword_detector.detect_with_details(text)
        
        for category, detail in keyword_result.items():
            if category == 'overall':
                continue
                
            if detail['detected']:
                logger.warning(f"[模块化内容检测-关键词检测] 检测到{category}违规内容，关键词: {detail['keywords']}")
                results.append(ModerationResult(
                    category=category,
                    method='keyword',
                    is_violation=True,
                    confidence=0.95,
                    details={'keywords': detail['keywords']}
                ))
        
        if results:
            logger.warning(f"[模块化内容检测-关键词检测] 发现{len(results)}个违规类别: {[r.category for r in results]}")
        else:
            logger.info(f"[模块化内容检测-关键词检测] 文本通过检测: {text[:50]}...")
        
        return results
    
    async def detect_by_llm(self, text: str, categories: Optional[List[str]] = None) -> List[ModerationResult]:
        """基于LLM检测"""
        if categories is None:
            categories = list(self.llm_detectors.keys())
        
        logger.info(f"[模块化内容检测-LLM检测] 开始检测文本: {text[:50]}..., 检测类别: {categories}")
        
        results = []
        
        for category in categories:
            prompt_func = self.llm_detectors[category]
            prompt = prompt_func(text)
            
            logger.info(f"[模块化内容检测-LLM检测] 调用LLM检测{category}类别")
            is_violation = await self._call_llm(prompt)
            
            if is_violation:
                logger.warning(f"[模块化内容检测-LLM检测] 检测到{category}违规内容")
                results.append(ModerationResult(
                    category=category,
                    method='llm',
                    is_violation=True,
                    confidence=0.85,
                    details={'prompt': prompt['system_prompt'][:100]}
                ))
        
        if results:
            logger.warning(f"[模块化内容检测-LLM检测] 发现{len(results)}个违规类别: {[r.category for r in results]}")
        else:
            logger.info(f"[模块化内容检测-LLM检测] 文本通过检测: {text[:50]}...")
        
        return results
    
    async def _call_llm(self, prompt: Dict[str, str]) -> bool:
        """调用LLM进行检测"""
        try:
            logger.info(f"[模块化内容检测-LLM调用] 开始调用LLM进行内容检测")
            
            llm_request = LLMRequest(
                system_prompt=prompt["system_prompt"],
                user_prompt=prompt["user_prompt"],
                temperature=0.1,
                max_tokens=10,
                provider="aliyun",
                model="qwen-flash",
                enable_context_cache=True
            )
            
            result = await llm_client_singleton.call_llm(llm_request)
            
            if isinstance(result, dict):
                response_text = result.get("text", "").strip()
                # 解析 LLM 返回结果：1=正常，0=违规
                if response_text == "1":
                    logger.info(f"[模块化内容检测-LLM调用] LLM判定为正常内容")
                    return False
                elif response_text == "0":
                    logger.warning(f"[模块化内容检测-LLM调用] LLM判定为违规内容")
                    return True
            
            logger.info(f"[模块化内容检测-LLM调用] LLM返回非预期结果，视为正常内容")
            return False
            
        except Exception as e:
            logger.warning(f"[模块化内容检测-LLM调用] LLM调用失败: {e}")
            # 如果LLM调用失败，为了安全起见，返回False（不违规），让其他检测层处理
            return False
    
    async def detect_parallel(
        self,
        text: str,
        use_keyword: bool = True,
        use_llm: bool = True,
        categories: Optional[List[str]] = None
    ) -> OverallModerationResult:
        """并行检测"""
        logger.info(f"[模块化内容检测-并行检测] 开始并行检测文本: {text[:50]}..., 使用关键词: {use_keyword}, 使用LLM: {use_llm}")
        
        start_time = time.time()
        
        if use_keyword:
            logger.info(f"[模块化内容检测-并行检测] 执行关键词检测")
            keyword_results = self.detect_by_keyword(text)
        else:
            logger.info(f"[模块化内容检测-并行检测] 跳过关键词检测")
            keyword_results = []
        
        if use_llm:
            logger.info(f"[模块化内容检测-并行检测] 执行LLM检测")
            llm_results = await self.detect_by_llm(text, categories)
        else:
            logger.info(f"[模块化内容检测-并行检测] 跳过LLM检测")
            llm_results = []
        
        all_results = keyword_results + llm_results
        
        violation_categories = list(set([r.category for r in all_results if r.is_violation]))
        is_violation = len(violation_categories) > 0
        
        if all_results:
            confidence = sum([r.confidence for r in all_results]) / len(all_results)
        else:
            confidence = 0.0
        
        processing_time = time.time() - start_time
        
        if is_violation:
            logger.warning(f"[模块化内容检测-并行检测] 检测到违规内容，类别: {violation_categories}, 处理时间: {processing_time:.2f}s")
        else:
            logger.info(f"[模块化内容检测-并行检测] 文本通过检测，处理时间: {processing_time:.2f}s")
        
        return OverallModerationResult(
            is_violation=is_violation,
            results=all_results,
            violation_categories=violation_categories,
            confidence=confidence,
            processing_time=processing_time
        )
    
    def detect_fast(self, text: str) -> OverallModerationResult:
        """快速检测"""
        logger.info(f"[模块化内容检测-快速检测] 开始快速检测文本: {text[:50]}...")
        
        start_time = time.time()
        
        keyword_results = self.detect_by_keyword(text)
        
        violation_categories = list(set([r.category for r in keyword_results if r.is_violation]))
        is_violation = len(violation_categories) > 0
        
        if keyword_results:
            confidence = sum([r.confidence for r in keyword_results]) / len(keyword_results)
        else:
            confidence = 0.0
        
        processing_time = time.time() - start_time
        
        if is_violation:
            logger.warning(f"[模块化内容检测-快速检测] 检测到违规内容，类别: {violation_categories}, 处理时间: {processing_time:.2f}s")
        else:
            logger.info(f"[模块化内容检测-快速检测] 文本通过检测，处理时间: {processing_time:.2f}s")
        
        return OverallModerationResult(
            is_violation=is_violation,
            results=keyword_results,
            violation_categories=violation_categories,
            confidence=confidence,
            processing_time=processing_time
        )
    
    def detect_accurate(self, text: str) -> OverallModerationResult:
        """精确检测"""
        logger.info(f"[模块化内容检测-精确检测] 开始精确检测文本: {text[:50]}...")
        
        start_time = time.time()
        
        loop = asyncio.get_event_loop()
        llm_results = loop.run_until_complete(self.detect_by_llm(text))
        
        violation_categories = list(set([r.category for r in llm_results if r.is_violation]))
        is_violation = len(violation_categories) > 0
        
        if llm_results:
            confidence = sum([r.confidence for r in llm_results]) / len(llm_results)
        else:
            confidence = 0.0
        
        processing_time = time.time() - start_time
        
        if is_violation:
            logger.warning(f"[模块化内容检测-精确检测] 检测到违规内容，类别: {violation_categories}, 处理时间: {processing_time:.2f}s")
        else:
            logger.info(f"[模块化内容检测-精确检测] 文本通过检测，处理时间: {processing_time:.2f}s")
        
        return OverallModerationResult(
            is_violation=is_violation,
            results=llm_results,
            violation_categories=violation_categories,
            confidence=confidence,
            processing_time=processing_time
        )


_coordinator = None


def get_moderation_coordinator() -> ModerationCoordinator:
    """获取检测协调器单例"""
    global _coordinator
    if _coordinator is None:
        _coordinator = ModerationCoordinator()
    return _coordinator
