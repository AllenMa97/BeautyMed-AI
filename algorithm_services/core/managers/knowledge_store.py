"""
统一的知识数据模型和存储管理
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import json
import os
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)

DATA_DIR = "data/knowledge"


@dataclass
class KnowledgeMetadata:
    """知识元数据"""
    type: str  # behavior|feature|interaction|correction
    source: str  # 来源
    created_at: str  # 创建时间
    usage_count: int = 0  # 使用次数
    source_session: Optional[str] = None  # 来源会话


@dataclass
class KnowledgeItem:
    """统一的知识条目"""
    content: str  # 知识内容
    embedding: Optional[List[float]] = None  # 向量
    metadata: Optional[KnowledgeMetadata] = None  # 元数据
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "embedding": self.embedding,
            "metadata": asdict(self.metadata) if self.metadata else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'KnowledgeItem':
        metadata = data.get("metadata")
        if metadata:
            metadata = KnowledgeMetadata(**metadata)
        return cls(
            content=data.get("content", ""),
            embedding=data.get("embedding"),
            metadata=metadata
        )


class KnowledgeStore:
    """
    统一的知识存储管理
    支持分类存储：behavior|feature|interaction|correction
    """
    
    def __init__(self, knowledge_type: str):
        self.knowledge_type = knowledge_type
        self.file_path = os.path.join(DATA_DIR, f"{knowledge_type}.json")
        self.items: Dict[str, KnowledgeItem] = {}
        self._ensure_dir()
        self._load()
    
    def _ensure_dir(self):
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def _load(self):
        """加载知识"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items_data = data.get("items", {})
                    self.items = {
                        k: KnowledgeItem.from_dict(v) 
                        for k, v in items_data.items()
                    }
                logger.info(f"加载 {self.knowledge_type} 知识: {len(self.items)} 条")
            except Exception as e:
                logger.warning(f"加载 {self.knowledge_type} 知识失败: {e}")
                self.items = {}
        else:
            logger.info(f"新建设 {self.knowledge_type} 知识库")
            self.items = {}
    
    def _save(self):
        """保存知识"""
        try:
            data = {
                "knowledge_type": self.knowledge_type,
                "updated_at": datetime.now().isoformat(),
                "items": {k: v.to_dict() for k, v in self.items.items()}
            }
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"保存 {self.knowledge_type} 知识: {len(self.items)} 条")
        except Exception as e:
            logger.error(f"保存 {self.knowledge_type} 知识失败: {e}")
    
    def add(self, content: str, embedding: Optional[List[float]] = None, 
            source: str = "system", source_session: Optional[str] = None) -> str:
        """添加知识，返回 key"""
        key = hashlib.md5(content.encode()).hexdigest()[:16]
        metadata = KnowledgeMetadata(
            type=self.knowledge_type,
            source=source,
            created_at=datetime.now().isoformat(),
            source_session=source_session
        )
        self.items[key] = KnowledgeItem(
            content=content,
            embedding=embedding,
            metadata=metadata
        )
        self._save()
        return key
    
    def get(self, key: str) -> Optional[KnowledgeItem]:
        return self.items.get(key)
    
    def get_all(self) -> Dict[str, KnowledgeItem]:
        return self.items
    
    def delete(self, key: str):
        if key in self.items:
            del self.items[key]
            self._save()
    
    def update_embedding(self, key: str, embedding: List[float]):
        if key in self.items:
            self.items[key].embedding = embedding
            self._save()
    
    def increment_usage(self, key: str):
        if key in self.items and self.items[key].metadata:
            self.items[key].metadata.usage_count += 1
            self._save()
    
    def get_all_embeddings(self) -> tuple:
        """获取所有有 embedding 的知识"""
        keys = []
        embeddings = []
        contents = []
        for k, v in self.items.items():
            if v.embedding:
                keys.append(k)
                embeddings.append(v.embedding)
                contents.append(v.content)
        return keys, embeddings, contents
    
    def get_items_without_embedding(self) -> List[tuple]:
        """获取没有 embedding 的知识"""
        return [(k, v) for k, v in self.items.items() if v.embedding is None]


class KnowledgeManager:
    """
    统一的知识管理器
    管理所有类型的知识
    """
    
    def __init__(self):
        self.stores: Dict[str, KnowledgeStore] = {
            "behavior": KnowledgeStore("behavior"),
            "feature": KnowledgeStore("feature"),
            "interaction": KnowledgeStore("interaction"),
            "correction": KnowledgeStore("correction"),
        }
    
    def get_store(self, knowledge_type: str) -> KnowledgeStore:
        return self.stores.get(knowledge_type, self.stores["behavior"])
    
    def add_knowledge(self, knowledge_type: str, content: str, 
                     embedding: Optional[List[float]] = None,
                     source: str = "system",
                     source_session: Optional[str] = None) -> str:
        """添加知识"""
        return self.get_store(knowledge_type).add(content, embedding, source, source_session)
    
    def get_all_knowledge(self, knowledge_type: str = None) -> Dict[str, KnowledgeItem]:
        """获取知识"""
        if knowledge_type:
            return self.get_store(knowledge_type).get_all()
        # 返回所有类型的知识
        result = {}
        for store in self.stores.values():
            result.update(store.get_all())
        return result
    
    def get_all_embeddings(self, knowledge_type: str = None) -> tuple:
        """获取所有 embedding"""
        if knowledge_type:
            return self.get_store(knowledge_type).get_all_embeddings()
        
        all_keys = []
        all_embeddings = []
        all_contents = []
        for store in self.stores.values():
            keys, embeddings, contents = store.get_all_embeddings()
            all_keys.extend(keys)
            all_embeddings.extend(embeddings)
            all_contents.extend(contents)
        return all_keys, all_embeddings, all_contents


knowledge_manager = KnowledgeManager()
