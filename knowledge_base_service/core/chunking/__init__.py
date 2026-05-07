# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Updated: 2026-04-20
# Copyright (c) 2026. All rights reserved.

"""
分块系统模块 (Chunking System)

导出所有分块相关的类和数据结构。
只推荐使用 HybridChunker,其他都是内部实现细节。

使用示例:
    from core.chunking import HybridChunker, Document
    
    chunker = HybridChunker()
    chunks = chunker.chunk(document)
"""

from .base_chunker import BaseChunker, Chunk, Document
from .hybrid_chunker import HybridChunker

__all__ = [
    "BaseChunker",
    "Chunk",
    "Document",
    "HybridChunker",
]
