# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Updated: 2026-04-20
# Copyright (c) 2026. All rights reserved.

from typing import List, Optional
from .base_chunker import BaseChunker, Chunk, Document


class ParentChildChunker(BaseChunker):
    """父子分块器:生成多层级的 chunk 结构"""
    
    def __init__(
        self,
        parent_max_tokens: int = None,
        child_max_tokens: int = None,
        overlap_tokens: int = 30,
        similarity_threshold: float = None,
    ):
        import os
        
        # 从环境变量或参数读取配置
        self.parent_max_tokens = parent_max_tokens or int(os.getenv("CHUNK_PARENT_MAX_TOKENS", "512"))
        self.child_max_tokens = child_max_tokens or int(os.getenv("CHUNK_CHILD_MAX_TOKENS", "128"))
        self.overlap_tokens = overlap_tokens
        self.similarity_threshold = similarity_threshold or float(os.getenv("CHUNK_SIMILARITY_THRESHOLD", "0.6"))
        
        super().__init__(max_tokens=self.parent_max_tokens, overlap_tokens=self.overlap_tokens)
    
    def chunk(self, document: Document) -> List[Chunk]:
        all_chunks = []
        
        # 先生成父 chunk
        parent_chunks = self._split_by_semantic_similarity(document)
        
        for parent_chunk in parent_chunks:
            parent_chunk.metadata["chunk_type"] = "parent"
            parent_chunk.metadata["parent_max_tokens"] = self.max_tokens
            
            # 为每个父 chunk 生成子 chunk
            children = self._create_children(parent_chunk, document)
            
            # 更新父 chunk 的 children_ids
            parent_chunk.children_ids = [child.id for child in children]
            
            all_chunks.append(parent_chunk)
            all_chunks.extend(children)
        
        return all_chunks
    
    def _split_by_semantic_similarity(self, document: Document) -> List[Chunk]:
        from ..vector_store.embedding_client import EmbeddingClient
        import numpy as np
        
        sentences = self._split_into_sentences(document.content)
        if not sentences:
            return []
        
        # 生成 Embedding
        try:
            client = EmbeddingClient()
            embeddings = client.get_embeddings(sentences)
        except Exception as e:
            embeddings = None
        
        if embeddings:
            # 计算相邻句子的相似度
            similarities = []
            for i in range(len(embeddings) - 1):
                emb1 = np.array(embeddings[i])
                emb2 = np.array(embeddings[i + 1])
                sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                similarities.append(float(sim))
            
            # 在相似度低的地方切断
            parent_chunks = []
            current_sentences = []
            current_tokens = 0
            
            for i, sentence in enumerate(sentences):
                sentence_tokens = self.count_tokens(sentence)
                
                should_split = False
                
                # 条件 1: 超过 max_tokens
                if current_tokens + sentence_tokens > self.max_tokens and current_sentences:
                    should_split = True
                
                # 条件 2: 和前一句的相似度低于阈值
                if i > 0 and similarities[i - 1] < self.similarity_threshold:
                    should_split = True
                
                if should_split and current_sentences:
                    content = "".join(current_sentences)
                    parent_chunks.append(Chunk(
                        content=content,
                        token_count=self.count_tokens(content),
                        metadata={},
                    ))
                    current_sentences = [sentence]
                    current_tokens = sentence_tokens
                else:
                    current_sentences.append(sentence)
                    current_tokens += sentence_tokens
            
            if current_sentences:
                content = "".join(current_sentences)
                parent_chunks.append(Chunk(
                    content=content,
                    token_count=self.count_tokens(content),
                    metadata={},
                ))
        else:
            # 降级策略:简单按句子累积
            parent_chunks = []
            current_sentences = []
            current_tokens = 0
            
            for sentence in sentences:
                sentence_tokens = self.count_tokens(sentence)
                
                if current_tokens + sentence_tokens > self.max_tokens and current_sentences:
                    content = "".join(current_sentences)
                    parent_chunks.append(Chunk(content=content, token_count=self.count_tokens(content), metadata={}))
                    current_sentences = [sentence]
                    current_tokens = sentence_tokens
                else:
                    current_sentences.append(sentence)
                    current_tokens += sentence_tokens
            
            if current_sentences:
                content = "".join(current_sentences)
                parent_chunks.append(Chunk(content=content, token_count=self.count_tokens(content), metadata={}))
        
        return parent_chunks
    
    def _create_children(self, parent: Chunk, document: Document) -> List[Chunk]:
        children = []
        
        # 将父 chunk 拆分为子 chunk
        child_texts = self._split_into_children(parent.content)
        
        for i, child_text in enumerate(child_texts):
            child = Chunk(
                content=child_text,
                parent_id=parent.id,
                token_count=self.count_tokens(child_text),
                metadata={
                    **parent.metadata,
                    "chunk_type": "child",
                    "child_index": i,
                    "child_max_tokens": self.child_max_tokens,
                    "document_id": document.id,
                    "document_title": document.title,
                },
            )
            children.append(child)
        
        return children
    
    def _split_into_children(self, text: str) -> List[str]:
        if self.count_tokens(text) <= self.child_max_tokens:
            return [text]
        
        children = []
        sentences = self._split_into_sentences(text)
        
        current_child = []
        current_tokens = 0
        
        # 逐句累加
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.child_max_tokens and current_child:
                children.append("".join(current_child))
                current_child = [sentence]
                current_tokens = sentence_tokens
            else:
                # 继续累加
                current_child.append(sentence)
                current_tokens += sentence_tokens
        
        # 处理最后一个子 chunk
        if current_child:
            children.append("".join(current_child))
        
        return children
    
    def _split_into_sentences(self, text: str) -> List[str]:
        import re
        sentence_endings = re.compile(r"(?<=[。！?.!?])\s*|(?<=[\n])")
        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def get_parent_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        return [c for c in chunks if c.metadata.get("chunk_type") == "parent"]
    
    def get_child_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        return [c for c in chunks if c.metadata.get("chunk_type") == "child"]
    
    def get_parent_by_child(self, child: Chunk, all_chunks: List[Chunk]) -> Optional[Chunk]:
        if not child.parent_id:
            return None
        
        for chunk in all_chunks:
            if chunk.id == child.parent_id:
                return chunk
        
        return None
