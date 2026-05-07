"""
上下文注入控制器
负责智能管理各种上下文信息的注入逻辑
避免强行把所有信息都放进去，根据场景智能决定
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger(__name__)

class ContextType(Enum):
    TIME_LOCATION = "time_location"
    TRENDING_TOPICS = "trending_topics"
    USER_PROFILE = "user_profile"
    INTERMEDIATE_RESULTS = "intermediate_results"
    ERROR_RECORDS = "error_records"


@dataclass
class InjectionRule:
    context_type: ContextType
    keywords: List[str]
    priority: int = 1
    required: bool = False
    max_items: int = 5


@dataclass
class InjectionResult:
    injected_types: Set[ContextType] = field(default_factory=set)
    skipped_types: Set[ContextType] = field(default_factory=set)
    injection_details: Dict[str, Any] = field(default_factory=dict)


class ContextInjectionController:
    """
    上下文注入控制器
    根据用户输入和场景智能决定注入哪些上下文信息
    """
    
    def __init__(self):
        self._injection_rules = self._init_injection_rules()
        self._time_keywords = {
            '时间', '几点', '今天', '明天', '昨天', '现在', '日期', '星期',
            '早上', '中午', '下午', '晚上', '凌晨', '什么时候',
            'when', 'time', 'today', 'tomorrow', 'now', 'date'
        }
        self._location_keywords = {
            '位置', '在哪', '哪里', '地点', '地址', '城市', '省份',
            '这里', '那里', '附近', '本地', '地区',
            'where', 'location', 'place', 'city', 'area'
        }
        self._trending_keywords = {
            '热搜', '热点', '新闻', '热门', '流行', '趋势', '最新',
            '微博', '百度', '头条', '话题', '八卦', '娱乐',
            'hot', 'trending', 'news', 'popular', 'latest'
        }
        self._fashion_beauty_keywords = {
            '时尚', '美妆', '护肤', '穿搭', '化妆', '口红', '面膜',
            '衣服', '鞋子', '包包', '首饰', '发型', '造型',
            'vogue', 'elle', 'gq', 'beauty', 'makeup', 'style'
        }
        self._user_profile_keywords = {
            '我', '我的', '我喜欢', '我想要', '推荐给我', '适合我',
            '记住', '偏好', '习惯', '历史',
            'my', 'me', 'i like', 'recommend', 'prefer'
        }
    
    def _init_injection_rules(self) -> List[InjectionRule]:
        return [
            InjectionRule(
                context_type=ContextType.TIME_LOCATION,
                keywords=['时间', '位置', '天气', '今天', '现在'],
                priority=3,
                required=False,
                max_items=1
            ),
            InjectionRule(
                context_type=ContextType.TRENDING_TOPICS,
                keywords=['热搜', '热点', '新闻', '流行', '时尚'],
                priority=2,
                required=False,
                max_items=10
            ),
            InjectionRule(
                context_type=ContextType.USER_PROFILE,
                keywords=['我', '推荐', '适合', '喜欢'],
                priority=2,
                required=False,
                max_items=5
            ),
        ]
    
    def analyze_injection_needs(
        self,
        user_input: str,
        feature_stage: str = None,
        context: str = None
    ) -> InjectionResult:
        """
        分析用户输入，决定需要注入哪些上下文
        """
        result = InjectionResult()
        user_input_lower = user_input.lower()
        
        time_needed = self._check_time_injection_needed(user_input_lower, feature_stage)
        if time_needed:
            result.injected_types.add(ContextType.TIME_LOCATION)
            result.injection_details['time_location'] = {'reason': time_needed}
        else:
            result.skipped_types.add(ContextType.TIME_LOCATION)
        
        trending_needed = self._check_trending_injection_needed(user_input_lower, feature_stage)
        if trending_needed:
            result.injected_types.add(ContextType.TRENDING_TOPICS)
            result.injection_details['trending_topics'] = {'reason': trending_needed}
        else:
            result.skipped_types.add(ContextType.TRENDING_TOPICS)
        
        profile_needed = self._check_profile_injection_needed(user_input_lower, feature_stage)
        if profile_needed:
            result.injected_types.add(ContextType.USER_PROFILE)
            result.injection_details['user_profile'] = {'reason': profile_needed}
        else:
            result.skipped_types.add(ContextType.USER_PROFILE)
        
        return result
    
    def _check_time_injection_needed(self, user_input: str, feature_stage: str = None) -> Optional[str]:
        """
        检查是否需要注入时间位置信息
        """
        if any(kw in user_input for kw in self._time_keywords):
            return 'time_keyword_matched'
        
        if any(kw in user_input for kw in self._location_keywords):
            return 'location_keyword_matched'
        
        if feature_stage and 'schedule' in feature_stage.lower():
            return 'schedule_stage'
        
        return None
    
    def _check_trending_injection_needed(self, user_input: str, feature_stage: str = None) -> Optional[str]:
        """
        检查是否需要注入热搜信息
        """
        if any(kw in user_input for kw in self._trending_keywords):
            return 'trending_keyword_matched'
        
        if any(kw in user_input for kw in self._fashion_beauty_keywords):
            return 'fashion_beauty_keyword_matched'
        
        if feature_stage and 'beauty' in feature_stage.lower():
            return 'beauty_stage'
        
        return None
    
    def _check_profile_injection_needed(self, user_input: str, feature_stage: str = None) -> Optional[str]:
        """
        检查是否需要注入用户画像
        """
        if any(kw in user_input for kw in self._user_profile_keywords):
            return 'profile_keyword_matched'
        
        if feature_stage and 'personal' in feature_stage.lower():
            return 'personal_stage'
        
        return None
    
    def build_injection_context(
        self,
        injection_result: InjectionResult,
        time_location_info: Dict = None,
        trending_topics_info: Dict = None,
        user_profile: Dict = None,
        intermediate_results: Dict = None,
        max_trending_items: int = 5
    ) -> Dict[str, Any]:
        """
        根据注入分析结果构建上下文字典
        """
        context = {}
        
        if ContextType.TIME_LOCATION in injection_result.injected_types:
            if time_location_info:
                context['time_location'] = self._format_time_location(time_location_info)
        
        if ContextType.TRENDING_TOPICS in injection_result.injected_types:
            if trending_topics_info:
                context['trending_topics'] = self._format_trending_topics(
                    trending_topics_info, max_trending_items
                )
        
        if ContextType.USER_PROFILE in injection_result.injected_types:
            if user_profile:
                context['user_profile'] = self._format_user_profile(user_profile)
        
        if intermediate_results:
            context['intermediate_results'] = intermediate_results
        
        return context
    
    def _format_time_location(self, info: Dict) -> str:
        """
        格式化时间位置信息
        """
        time_info = info.get('time_info', {})
        location_info = info.get('location_info', {})
        
        parts = []
        if time_info.get('formatted_time'):
            parts.append(f"当前时间: {time_info['formatted_time']}")
        if time_info.get('weekday'):
            parts.append(f"{time_info['weekday']}")
        if location_info.get('location_desc'):
            parts.append(f"位置: {location_info['location_desc']}")
        
        return '，'.join(parts) if parts else ''
    
    def _format_trending_topics(self, info: Dict, max_items: int = 5) -> str:
        """
        格式化热搜信息
        """
        parts = []
        
        fashion_trends = info.get('fashion_beauty_trends', [])
        if fashion_trends:
            for i, trend in enumerate(fashion_trends[:max_items]):
                title = trend.get('title', '')
                if title:
                    parts.append(f"{i+1}. {title}")
        
        if not parts:
            weibo_hot = info.get('weibo_hot', [])
            for i, item in enumerate(weibo_hot[:max_items]):
                title = item.get('title', '')
                if title:
                    parts.append(f"{i+1}. {title}")
        
        return '\n'.join(parts) if parts else ''
    
    def _format_user_profile(self, profile: Dict) -> str:
        """
        格式化用户画像
        """
        parts = []
        
        if profile.get('preferences'):
            prefs = profile['preferences']
            if isinstance(prefs, list):
                parts.append(f"偏好: {', '.join(prefs[:5])}")
            elif isinstance(prefs, dict):
                parts.append(f"偏好: {prefs}")
        
        if profile.get('interests'):
            interests = profile['interests']
            if isinstance(interests, list):
                parts.append(f"兴趣: {', '.join(interests[:5])}")
        
        return '；'.join(parts) if parts else ''
    
    def should_inject_for_prompt(
        self,
        user_input: str,
        prompt_type: str,
        feature_stage: str = None
    ) -> Dict[str, bool]:
        """
        为特定类型的prompt决定注入策略
        """
        result = {
            'inject_time': False,
            'inject_trending': False,
            'inject_profile': False,
            'inject_intermediate': True
        }
        
        injection_analysis = self.analyze_injection_needs(user_input, feature_stage)
        
        if prompt_type == 'free_chat':
            result['inject_time'] = ContextType.TIME_LOCATION in injection_analysis.injected_types
            result['inject_trending'] = ContextType.TRENDING_TOPICS in injection_analysis.injected_types
            result['inject_profile'] = True
        
        elif prompt_type == 'planner':
            result['inject_time'] = True
            result['inject_trending'] = True
            result['inject_profile'] = True
        
        elif prompt_type == 'knowledge':
            result['inject_time'] = False
            result['inject_trending'] = False
            result['inject_profile'] = ContextType.USER_PROFILE in injection_analysis.injected_types
        
        return result


context_injection_controller = ContextInjectionController()
