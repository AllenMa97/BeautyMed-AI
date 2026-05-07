# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Updated: 2026-04-20
# Copyright (c) 2026. All rights reserved.
from typing import List, Dict, Any, Optional
from .base_chunker import BaseChunker, Chunk, Document
from .parent_child_chunker import ParentChildChunker


class HybridChunker(BaseChunker):
    def __init__(
        self,
        parent_max_tokens: int = None,
        child_max_tokens: int = None,
        min_tokens: int = None,
        overlap_tokens: int = 30,
        similarity_threshold: float = None,
        enable_parent_child: bool = None,
    ):
       
        import os
        
        # 从环境变量或参数读取配置
        self.parent_max_tokens = parent_max_tokens or int(os.getenv("CHUNK_PARENT_MAX_TOKENS", "512"))
        self.child_max_tokens = child_max_tokens or int(os.getenv("CHUNK_CHILD_MAX_TOKENS", "128"))
        self.min_tokens = min_tokens or int(os.getenv("CHUNK_MIN_TOKENS", "50"))
        self.overlap_tokens = overlap_tokens
        self.similarity_threshold = similarity_threshold or float(os.getenv("CHUNK_SIMILARITY_THRESHOLD", "0.6"))
        
        enable_pc_env = os.getenv("CHUNK_ENABLE_PARENT_CHILD", "True").lower()
        if enable_parent_child is not None:
            self.enable_parent_child = enable_parent_child
        else:
            self.enable_parent_child = enable_pc_env in ("true", "1", "yes")
        
        super().__init__(max_tokens=self.parent_max_tokens, overlap_tokens=self.overlap_tokens)
        
        # 初始化父子分块器(内部已包含语义相似度识别)
        if self.enable_parent_child:
            self.parent_child_chunker = ParentChildChunker(
                parent_max_tokens=self.parent_max_tokens,
                child_max_tokens=self.child_max_tokens,
                overlap_tokens=self.overlap_tokens,
                similarity_threshold=self.similarity_threshold,
            )
    
    def chunk(self, document: Document) -> List[Chunk]:
        """
        对文档进行分块(推荐使用此方法)
        
        工作流程:
            1. 用语义相似度识别话题转换点,形成?chunk
            2. 将父 chunk 拆分为子 chunk,建立父子关?            
            3. 为每?chunk 补充元数据(权威等级、类别等?        
        Args:
            document: 待分块的文档
            
        Returns:
            Chunk 列表(包含父子关系)
        """
        if self.enable_parent_child:
            # 使用父子分块器(内部已包含语义相似度识别)
            chunks = self.parent_child_chunker.chunk(document)
        else:
            # 只生成父 chunk(不推荐)
            chunks = self.parent_child_chunker._split_by_semantic_similarity(document)
        
        # Step 2: 补充元数据
        chunks = self._enrich_metadata(chunks, document)
        
        return chunks
    
    def _enrich_metadata(self, chunks: List[Chunk], document: Document) -> List[Chunk]:
        """
        为 chunk 补充元数据
        
        补充的元数据:
            - document_id, document_title: 文档 ID 和标题
            - source, source_type: 来源和类型
            - authority_level: 权威等级(专家/学术/临床/官方/产品/通用)
            - category: 类别(产品/学术/专利/临床/新闻/医美/通用)
        
        Args:
            chunks: 原始 chunk 列表
            document: 原始文档
            
        Returns:
            元数据增强后的 chunk 列表
        """
        for chunk in chunks:
            chunk.metadata.update({
                "document_id": document.id,
                "document_title": document.title,
                "source": document.source,
                "source_type": document.source_type,
                "chunker_type": "hybrid",
                "parent_max_tokens": self.parent_max_tokens,
                "child_max_tokens": self.child_max_tokens,
                "similarity_threshold": self.similarity_threshold,
            })
            
            # 推断权威等级(如果还没有)
            if "authority_level" not in chunk.metadata:
                chunk.metadata["authority_level"] = self._infer_authority(document)
            
            # 推断类别(如果还没有)
            if "category" not in chunk.metadata:
                chunk.metadata["category"] = self._infer_category(document)
        
        return chunks
    
    def _infer_authority(self, document: Document) -> str:
        """
        推断文档的权威等级
        
        优先级:
            专利 > 学术论文 > 临床研究 > 官方指南 > 产品 > 通用
        
        Args:
            document: 文档对象
            
        Returns:
            权威等级字符串
        """
        source_type = document.source_type.lower()
        source = document.source.lower()
        
        if "patent" in source_type or "专利" in source:
            return "patent"
        elif "paper" in source_type or "论文" in source or "pubmed" in source:
            return "academic"
        elif "clinical" in source_type or "临床" in source:
            return "clinical"
        elif "official" in source_type or "官方" in source:
            return "official"
        elif "product" in source_type or "产品" in source:
            return "product"
        else:
            return "general"
    
    def _infer_category(self, document: Document) -> str:
        """
        推断文档的类别
        
        规则:
            基于标题、内容前 500 字、来源类型进行推断        
        Args:
            document: 文档对象
            
        Returns:
            类别字符串
        """
        title = document.title.lower()
        content = document.content.lower()[:500]
        source_type = document.source_type.lower()
        
        if "产品" in title or "product" in source_type:
            return "product"
        elif "论文" in title or "paper" in source_type:
            return "academic"
        elif "专利" in title or "patent" in source_type:
            return "patent"
        elif "临床" in content or "clinical" in source_type:
            return "clinical"
        elif "新闻" in title or "news" in source_type:
            return "news"
        elif "医美" in content or "美容" in content:
            return "medical_aesthetics"
        else:
            return "general"
