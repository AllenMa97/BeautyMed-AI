"""基于词表的内容检测模块"""
import re
from typing import Dict, List, Set, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


class KeywordDetector:
    """基于关键词的内容检测器"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

    
    def __init__(self):
        self.keyword_sets = self._load_keyword_sets()
    
    def _load_keyword_sets(self) -> Dict[str, Set[str]]:
        """加载各类违规关键词集合"""
        return {
            'political': self._load_political_keywords(),
            'violence': self._load_violence_keywords(),
            'pornography': self._load_pornography_keywords(),
            'gambling': self._load_gambling_keywords(),
            'drug': self._load_drug_keywords(),
            'hate': self._load_hate_keywords(),
            'fake': self._load_fake_keywords(),
        }
    
    def _load_political_keywords(self) -> Set[str]:
        """政治敏感关键词"""
        keywords = {
            # 领土相关
            '台独', '港独', '藏独', '疆独', '台湾国', '台湾独立',
            'taiwan', 'tw', '台弯', '台完', '台玩', '弯弯', '宝岛',
            '对岸', '那个岛', '海峡那边', '🇹🇼',
            
            # 领导人相关
            '包子', '维尼', '习大', 'xi jin ping', 'xjp',
            'li ke qiang', 'lkp', 'hu jin tao', 'hjt',
            '习近瓶', '李可强', '胡锦涛',
        }
        return keywords
    
    def _load_violence_keywords(self) -> Set[str]:
        """暴力血腥关键词"""
        keywords = {
            '杀人', '杀掉', '杀死', '杀戮', '谋杀', '凶杀',
            '暴力', '暴利', '血腥', '血性', '恐怖', '恐布',
            '自杀', '自砂', '自残', '自尽', '上吊',
            'sha ren', 'bao li', 'xue xing', 'zi sha',
            'kill', 'murder', 'suicide', 'terror',
        }
        return keywords
    
    def _load_pornography_keywords(self) -> Set[str]:
        """色情低俗关键词"""
        keywords = {
            '色情', '色晴', '黄色', '黄se', '低俗', '低素',
            '擦边', '性暗示', '性骚扰', '卖淫', '嫖娼',
            'se qing', 'huang se', 'di su', 'ca bian',
            'sex', 'porn', 'adult', '约炮', '特殊服务',
        }
        return keywords
    
    def _load_gambling_keywords(self) -> Set[str]:
        """赌博诈骗关键词"""
        keywords = {
            '赌博', '堵博', '博彩', '网赌', '赌场', '赌球',
            '诈骗', '炸骗', '集资', '传销', '传消',
            'du bo', 'zha pian', 'chuan xiao', 'scam',
            'casino', 'poker', 'betting', '盘口', '跑分',
        }
        return keywords
    
    def _load_drug_keywords(self) -> Set[str]:
        """毒品违法犯罪关键词"""
        keywords = {
            '毒品', '独品', '吸毒', '贩毒', '大麻', '海洛因',
            '冰毒', '摇头丸', 'K粉', '毒品交易',
            'du pin', 'fan mai du pin', 'drug', 'heroin',
            '假证件', '假护照', '假身份证', '黑客', '黑课',
            'weapon', 'fake id', 'hack',
        }
        return keywords
    
    def _load_hate_keywords(self) -> Set[str]:
        """仇恨言论关键词"""
        keywords = {
            '种族歧视', '地域歧视', '性别歧视', '地域黑',
            '地图炮', '性别对立', '种族仇恨',
            'zhong zu', 'di yu', 'xing bie',
            'racism', 'discrimination', 'sexism',
        }
        return keywords
    
    def _load_fake_keywords(self) -> Set[str]:
        """虚假信息关键词"""
        keywords = {
            '谣言', '摇言', '造谣', '假新闻', '假消息',
            '伪科学', '微科学', '虚假信息', '恶意造谣',
            'yao yan', 'wei ke xue', 'fake news',
            'conspiracy', 'hoax', '爆料', '内幕',
        }
        return keywords
    
    def detect(self, text: str) -> Dict[str, bool]:
        """
        检测文本是否包含违规关键词
        
        返回格式：
        {
            'political': bool,
            'violence': bool,
            'pornography': bool,
            'gambling': bool,
            'drug': bool,
            'hate': bool,
            'fake': bool,
            'overall': bool  # 是否有任何违规
        }
        """
        results = {}
        overall_violation = False
        
        text_lower = text.lower()
        
        for category, keywords in self.keyword_sets.items():
            detected = False
            
            # 直接匹配
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    detected = True
                    break
            
            results[category] = detected
            if detected:
                overall_violation = True
        
        results['overall'] = overall_violation
        return results
    
    def detect_with_details(self, text: str) -> Dict[str, any]:
        """
        检测文本并返回详细信息（多线程并行检测7类）

        返回格式：
        {
            'political': {'detected': bool, 'keywords': List[str]},
            'violence': {'detected': bool, 'keywords': List[str]},
            ...
            'overall': bool
        }
        """
        CHUNK_SIZE = 50

        def check_category_chunk(args):
            category, chunk = args
            text_lower = text.lower()
            detected_keywords = []
            for keyword in chunk:
                if keyword.lower() in text_lower:
                    detected_keywords.append(keyword)
            return category, detected_keywords

        def check_category_full(category: str, keywords: Set[str]):
            keywords_list = list(keywords)
            if len(keywords_list) <= CHUNK_SIZE:
                detected_keywords = []
                text_lower = text.lower()
                for keyword in keywords_list:
                    if keyword.lower() in text_lower:
                        detected_keywords.append(keyword)
                return category, detected_keywords

            chunks = [keywords_list[i:i + CHUNK_SIZE] for i in range(0, len(keywords_list), CHUNK_SIZE)]
            chunk_args = [(category, chunk) for chunk in chunks]

            with ThreadPoolExecutor(max_workers=len(chunks)) as chunk_executor:
                futures = {chunk_executor.submit(check_category_chunk, arg): arg for arg in chunk_args}
                all_detected = []
                for future in as_completed(futures):
                    _, detected = future.result()
                    all_detected.extend(detected)
                    if all_detected:
                        return category, all_detected
                return category, all_detected

        results = {}
        overall_violation = False

        category_items = [(cat, kws) for cat, kws in self.keyword_sets.items()]
        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                executor.submit(check_category_full, category, keywords): category
                for category, keywords in category_items
            }

            for future in as_completed(futures):
                category, detected_keywords = future.result()
                detected = len(detected_keywords) > 0
                results[category] = {
                    'detected': detected,
                    'keywords': detected_keywords
                }
                if detected:
                    overall_violation = True

        results['overall'] = overall_violation
        return results


# 全局单例
_keyword_detector = None


def get_keyword_detector() -> KeywordDetector:
    """获取关键词检测器单例"""
    global _keyword_detector
    if _keyword_detector is None:
        _keyword_detector = KeywordDetector()
    return _keyword_detector
