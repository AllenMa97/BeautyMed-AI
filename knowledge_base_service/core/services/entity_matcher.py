# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-20
# Copyright (c) 2026. All rights reserved.

"""
实体匹配器:提供高效的实体匹配和检索功能
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

try:
    import ahocorasick
    AHO_CORASICK_AVAILABLE = True
except ImportError:
    AHO_CORASICK_AVAILABLE = False


class EntityMatcher:
    """实体匹配器"""
    
    def __init__(self):
        """初始化实体匹配器"""
        self.entities = {}
        self.entity_name_to_id = {}
        self.entity_id_to_name = {}
        self.entity_synonyms = defaultdict(set)
        self.entity_aliases = defaultdict(set)
        self.entity_types = {}
        
        self.automaton = None
        self.case_insensitive_automaton = None
        
        self.entity_type_index = defaultdict(set)
        self.entity_popularity = {}
    
    def add_entity(
        self,
        entity_id: str,
        entity_name: str,
        entity_type: str,
        synonyms: List[str] = None,
        aliases: List[str] = None,
        popularity: float = 1.0
    ):
        """
        添加实体
        
        Args:
            entity_id: 实体 ID
            entity_name: 实体名称
            entity_type: 实体类型
            synonyms: 同义词列表
            aliases: 别名列表
            popularity: 实体流行度(用于排序)
        """
        self.entities[entity_id] = {
            'id': entity_id,
            'name': entity_name,
            'type': entity_type,
            'synonyms': synonyms or [],
            'aliases': aliases or [],
            'popularity': popularity
        }
        
        self.entity_name_to_id[entity_name] = entity_id
        self.entity_id_to_name[entity_id] = entity_name
        self.entity_types[entity_id] = entity_type
        self.entity_popularity[entity_id] = popularity
        
        self.entity_type_index[entity_type].add(entity_id)
        
        if synonyms:
            for synonym in synonyms:
                self.entity_synonyms[synonym].add(entity_id)
                self.entity_name_to_id[synonym] = entity_id
        
        if aliases:
            for alias in aliases:
                self.entity_aliases[alias].add(entity_id)
                self.entity_name_to_id[alias] = entity_id
    
    def build_automaton(self):
        """构建 Aho-Corasick 自动机"""
        if not AHO_CORASICK_AVAILABLE:
            return
        
        self.automaton = ahocorasick.Automaton()
        
        all_names = set()
        all_names.update(self.entity_name_to_id.keys())
        
        for name in all_names:
            self.automaton.add_word(name, name)
        
        self.automaton.make_automaton()
        
        if AHO_CORASICK_AVAILABLE:
            self.case_insensitive_automaton = ahocorasick.Automaton()
            
            for name in all_names:
                lower_name = name.lower()
                self.case_insensitive_automaton.add_word(lower_name, name)
            
            self.case_insensitive_automaton.make_automaton()
    
    def match_exact(self, text: str) -> List[Tuple[str, str, float]]:
        """
        精确匹配实体
        
        Args:
            text: 输入文本
        
        Returns:
            匹配结果列表 [(entity_id, entity_name, score), ...]
        """
        results = []
        
        if text in self.entity_name_to_id:
            entity_id = self.entity_name_to_id[text]
            entity_name = self.entity_id_to_name[entity_id]
            popularity = self.entity_popularity.get(entity_id, 1.0)
            results.append((entity_id, entity_name, popularity))
        
        return results
    
    def match_fuzzy(self, text: str, threshold: float = 0.8) -> List[Tuple[str, str, float]]:
        """
        模糊匹配实体
        
        Args:
            text: 输入文本
            threshold: 相似度阈值
        
        Returns:
            匹配结果列表 [(entity_id, entity_name, score), ...]
        """
        from difflib import SequenceMatcher
        
        results = []
        text_lower = text.lower()
        
        for entity_id, entity_name in self.entity_id_to_name.items():
            entity_name_lower = entity_name.lower()
            
            similarity = SequenceMatcher(None, text_lower, entity_name_lower).ratio()
            
            if similarity >= threshold:
                popularity = self.entity_popularity.get(entity_id, 1.0)
                score = similarity * popularity
                results.append((entity_id, entity_name, score))
        
        results.sort(key=lambda x: x[2], reverse=True)
        return results
    
    def match_automaton(self, text: str, case_sensitive: bool = False) -> List[Tuple[str, str, int, int]]:
        """
        使用 Aho-Corasick 自动机匹配实体
        
        Args:
            text: 输入文本
            case_sensitive: 是否区分大小写
        
        Returns:
            匹配结果列表 [(entity_id, entity_name, start_pos, end_pos), ...]
        """
        results = []
        
        automaton = self.automaton if case_sensitive else self.case_insensitive_automaton
        
        if automaton is None:
            return results
        
        for end_pos, matched_name in automaton.iter(text):
            start_pos = end_pos - len(matched_name) + 1
            entity_id = self.entity_name_to_id.get(matched_name)
            
            if entity_id:
                entity_name = self.entity_id_to_name[entity_id]
                results.append((entity_id, entity_name, start_pos, end_pos))
        
        return results
    
    def match_by_type(self, text: str, entity_type: str) -> List[Tuple[str, str, float]]:
        """
        按实体类型匹配
        
        Args:
            text: 输入文本
            entity_type: 实体类型
        
        Returns:
            匹配结果列表 [(entity_id, entity_name, score), ...]
        """
        if entity_type not in self.entity_type_index:
            return []
        
        results = []
        entity_ids = self.entity_type_index[entity_type]
        
        for entity_id in entity_ids:
            entity_name = self.entity_id_to_name[entity_id]
            
            if text.lower() in entity_name.lower():
                popularity = self.entity_popularity.get(entity_id, 1.0)
                results.append((entity_id, entity_name, popularity))
        
        results.sort(key=lambda x: x[2], reverse=True)
        return results
    
    def match_multi(
        self,
        text: str,
        use_exact: bool = True,
        use_fuzzy: bool = True,
        use_automaton: bool = True,
        fuzzy_threshold: float = 0.8,
        max_results: int = 10
    ) -> List[Tuple[str, str, float]]:
        """
        多策略匹配实体
        
        Args:
            text: 输入文本
            use_exact: 是否使用精确匹配
            use_fuzzy: 是否使用模糊匹配
            use_automaton: 是否使用自动机匹配
            fuzzy_threshold: 模糊匹配阈值
            max_results: 最大结果数
        
        Returns:
            匹配结果列表 [(entity_id, entity_name, score), ...]
        """
        all_results = defaultdict(float)
        
        if use_exact:
            exact_results = self.match_exact(text)
            for entity_id, entity_name, score in exact_results:
                all_results[entity_id] += score * 1.0
        
        if use_fuzzy:
            fuzzy_results = self.match_fuzzy(text, fuzzy_threshold)
            for entity_id, entity_name, score in fuzzy_results:
                all_results[entity_id] += score * 0.8
        
        if use_automaton:
            automaton_results = self.match_automaton(text)
            for entity_id, entity_name, start_pos, end_pos in automaton_results:
                all_results[entity_id] += 1.0 * 0.6
        
        sorted_results = sorted(
            all_results.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        final_results = []
        seen_entities = set()
        
        for entity_id, score in sorted_results:
            if entity_id not in seen_entities:
                entity_name = self.entity_id_to_name[entity_id]
                final_results.append((entity_id, entity_name, score))
                seen_entities.add(entity_id)
            
            if len(final_results) >= max_results:
                break
        
        return final_results
    
    def get_entity_info(self, entity_id: str) -> Optional[Dict]:
        """
        获取实体信息
        
        Args:
            entity_id: 实体 ID
        
        Returns:
            实体信息字典
        """
        return self.entities.get(entity_id)
    
    def get_entities_by_type(self, entity_type: str) -> List[str]:
        """
        获取指定类型的所有实体 ID
        
        Args:
            entity_type: 实体类型
        
        Returns:
            实体 ID 列表
        """
        return list(self.entity_type_index.get(entity_type, set()))
    
    def get_entity_stats(self) -> Dict:
        """
        获取实体统计信息
        
        Returns:
            统计信息字典
        """
        type_counts = {
            entity_type: len(entity_ids)
            for entity_type, entity_ids in self.entity_type_index.items()
        }
        
        return {
            'total_entities': len(self.entities),
            'total_names': len(self.entity_name_to_id),
            'total_synonyms': sum(len(synonyms) for synonyms in self.entity_synonyms.values()),
            'total_aliases': sum(len(aliases) for aliases in self.entity_aliases.values()),
            'type_distribution': type_counts,
            'automaton_built': self.automaton is not None
        }
    
    def clear(self):
        """清空实体匹配器"""
        self.entities.clear()
        self.entity_name_to_id.clear()
        self.entity_id_to_name.clear()
        self.entity_synonyms.clear()
        self.entity_aliases.clear()
        self.entity_types.clear()
        self.entity_type_index.clear()
        self.entity_popularity.clear()
        self.automaton = None
        self.case_insensitive_automaton = None
