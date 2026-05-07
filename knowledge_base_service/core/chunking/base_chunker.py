# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Updated: 2026-04-20
# Copyright (c) 2026. All rights reserved.

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


@dataclass
class Chunk:
    """分块数据结构"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    token_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "metadata": self.metadata,
            "token_count": self.token_count,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            metadata=data.get("metadata", {}),
            token_count=data.get("token_count", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class Document:
    """文档数据结构"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    title: str = ""
    source: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "title": self.title,
            "source": self.source,
            "source_type": self.source_type,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class BaseChunker(ABC):
    """分块器抽象基类"""
    
    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50):
        """
        初始化分块器
        
        Args:
            max_tokens: 单个 chunk 的最大 token 数,默认 512
            overlap_tokens: chunk 之间的重叠 token 数,默认 50
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
    
    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """
        对文档进行分块(抽象方法)
        
        Args:
            document: 待分块的文档
            
        Returns:
            Chunk 列表
        """
        pass
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数量
        
        估算方法:4 个字符 = 1 个 token
        
        Args:
            text: 输入文本
            
        Returns:
            token 数量
        """
        return len(text) // 4 + 1
    
    def split_by_tokens(self, text: str, max_tokens: int) -> List[str]:
        """
        按 token 数分割文本
        
        Args:
            text: 待分割的文本
            max_tokens: 每个 chunk 的最大 token 数
            
        Returns:
            分割后的文本列表
        """
        tokens = self.count_tokens(text)
        if tokens <= max_tokens:
            return [text]
        
        chars_per_chunk = max_tokens * 4
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chars_per_chunk
            chunk_text = text[start:end]
            
            if end < len(text):
                # 尝试在句号或换行处断开
                last_period = chunk_text.rfind("。")
                last_newline = chunk_text.rfind("\n")
                split_point = max(last_period, last_newline)
                
                if split_point > start + chars_per_chunk // 2:
                    chunk_text = text[start:start + split_point + 1]
                    end = start + split_point + 1
            
            chunks.append(chunk_text.strip())
            start = end - self.overlap_tokens * 4 if end < len(text) else end
        
        return chunks
