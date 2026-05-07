# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Copyright (c) 2026. All rights reserved.

"""
文档Chunk化脚本
将现有文档chunk化，为知识图谱和向量检索做准备
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from core.chunking.hybrid_chunker import HybridChunker
from core.chunking.base_chunker import Document


async def load_documents(data_dir: str = "data/processed/contents") -> List[Dict[str, Any]]:
    """
    加载所有文档
    
    Args:
        data_dir: 数据目录
    
    Returns:
        文档列表
    """
    data_path = Path(data_dir)
    documents = []
    
    for file_path in data_path.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                documents.append(data)
        except Exception as e:
            print(f"加载文件 {file_path} 失败: {e}")
    
    print(f"成功加载 {len(documents)} 个文档")
    return documents


async def chunk_document(data: Dict[str, Any], chunker: HybridChunker) -> List[Dict[str, Any]]:
    """
    将单个文档chunk化
    
    Args:
        data: 文档数据
        chunker: Chunker实例
    
    Returns:
        Chunk列表
    """
    doc_type = data.get("type", "unknown")
    doc_id = data.get("id", "")
    
    if doc_type == "product":
        text = f"""
        产品名称：{data.get('name', '')}
        品牌：{data.get('brand', '')}
        类别：{data.get('category', '')}
        功效：{data.get('efficacy', '')}
        适用肤质：{data.get('applicable_skin', '')}
        容量：{data.get('capacity', '')}
        价格：{data.get('reference_price', '')}
        描述：{data.get('description', '')}
        标签：{', '.join(data.get('tags', []))}
        """
    elif doc_type == "entry":
        text = f"""
        标题：{data.get('title', '')}
        类别：{data.get('category', '')}
        内容：{data.get('content', '')}
        标签：{', '.join(data.get('tags', []))}
        """
    else:
        text = data.get('text', data.get('content', ''))
    
    document = Document(
        id=doc_id,
        content=text,
        metadata={
            'type': doc_type,
            'source': data.get('source', 'unknown'),
            'category': data.get('category', ''),
            'title': data.get('title', data.get('name', '')),
            'tags': data.get('tags', []),
            'original_data': data
        }
    )
    
    chunks = chunker.chunk(document)
    
    chunk_list = []
    for i, chunk in enumerate(chunks):
        chunk_data = {
            'chunk_id': f"{doc_id}_chunk_{i}",
            'document_id': doc_id,
            'content': chunk.content,
            'metadata': {
                **chunk.metadata,
                'chunk_index': i,
                'parent_chunk_id': chunk.parent_id,
                'chunk_type': chunk.metadata.get('chunk_type', 'unknown')
            },
            'token_count': chunk.token_count,
            'created_at': datetime.now().isoformat()
        }
        chunk_list.append(chunk_data)
    
    return chunk_list


async def chunk_all_documents(
    documents: List[Dict[str, Any]],
    max_chunks_per_doc: int = 5
) -> Dict[str, Any]:
    """
    Chunk化所有文档
    
    Args:
        documents: 文档列表
        max_chunks_per_doc: 每个文档最大chunk数
    
    Returns:
        Chunk化结果统计
    """
    chunker = HybridChunker()
    
    all_chunks = []
    chunk_stats = {
        'total_documents': len(documents),
        'total_chunks': 0,
        'chunks_by_document': {},
        'chunks_by_type': {},
        'total_tokens': 0
    }
    
    for doc in documents:
        doc_id = doc.get('id', '')
        doc_type = doc.get('type', 'unknown')
        
        chunks = await chunk_document(doc, chunker)
        chunks = chunks[:max_chunks_per_doc]
        
        all_chunks.extend(chunks)
        
        chunk_stats['chunks_by_document'][doc_id] = len(chunks)
        chunk_stats['chunks_by_type'][doc_type] = chunk_stats['chunks_by_type'].get(doc_type, 0) + len(chunks)
        chunk_stats['total_tokens'] += sum(c['token_count'] for c in chunks)
    
    chunk_stats['total_chunks'] = len(all_chunks)
    
    return {
        'chunks': all_chunks,
        'stats': chunk_stats
    }


async def save_chunks(chunks: List[Dict[str, Any]], output_dir: str = "data/chunks"):
    """
    保存chunks到文件
    
    Args:
        chunks: Chunk列表
        output_dir: 输出目录
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    for chunk in chunks:
        chunk_file = output_path / f"{chunk['chunk_id']}.json"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
    
    print(f"已保存 {len(chunks)} 个chunks到 {output_dir}")


async def generate_chunk_summary(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成chunk摘要
    
    Args:
        chunks: Chunk列表
    
    Returns:
        摘要信息
    """
    if not chunks:
        return {}
    
    total_tokens = sum(c['token_count'] for c in chunks)
    avg_tokens = total_tokens / len(chunks)
    
    token_distribution = {}
    for chunk in chunks:
        tokens = chunk['token_count']
        if tokens <= 100:
            token_distribution['small'] = token_distribution.get('small', 0) + 1
        elif tokens <= 300:
            token_distribution['medium'] = token_distribution.get('medium', 0) + 1
        else:
            token_distribution['large'] = token_distribution.get('large', 0) + 1
    
    type_distribution = {}
    for chunk in chunks:
        chunk_type = chunk['metadata'].get('chunk_type', 'unknown')
        type_distribution[chunk_type] = type_distribution.get(chunk_type, 0) + 1
    
    return {
        'total_chunks': len(chunks),
        'total_tokens': total_tokens,
        'avg_tokens': avg_tokens,
        'token_distribution': token_distribution,
        'type_distribution': type_distribution,
        'min_tokens': min(c['token_count'] for c in chunks),
        'max_tokens': max(c['token_count'] for c in chunks)
    }


async def main():
    """主函数"""
    print("="*60)
    print("文档Chunk化工具")
    print("="*60)
    
    documents = await load_documents("data/processed/contents")
    
    if not documents:
        print("错误: 没有找到文档")
        return
    
    print(f"\n开始chunk化 {len(documents)} 个文档...")
    
    result = await chunk_all_documents(documents, max_chunks_per_doc=5)
    
    chunks = result['chunks']
    stats = result['stats']
    
    print(f"\nChunk化完成！")
    print(f"  总文档数: {stats['total_documents']}")
    print(f"  总chunk数: {stats['total_chunks']}")
    print(f"  总token数: {stats['total_tokens']}")
    print(f"  平均token数: {stats['total_tokens'] / stats['total_chunks']:.1f}")
    
    print(f"\n按文档分布:")
    for doc_id, count in stats['chunks_by_document'].items():
        print(f"  {doc_id}: {count} chunks")
    
    print(f"\n按类型分布:")
    for doc_type, count in stats['chunks_by_type'].items():
        print(f"  {doc_type}: {count} chunks")
    
    summary = await generate_chunk_summary(chunks)
    
    print(f"\nToken分布:")
    print(f"  小型chunks (≤100 tokens): {summary['token_distribution'].get('small', 0)}")
    print(f"  中型chunks (101-300 tokens): {summary['token_distribution'].get('medium', 0)}")
    print(f"  大型chunks (>300 tokens): {summary['token_distribution'].get('large', 0)}")
    
    print(f"\nChunk类型分布:")
    for chunk_type, count in summary['type_distribution'].items():
        print(f"  {chunk_type}: {count}")
    
    print(f"\nToken统计:")
    print(f"  最小: {summary['min_tokens']} tokens")
    print(f"  最大: {summary['max_tokens']} tokens")
    print(f"  平均: {summary['avg_tokens']:.1f} tokens")
    
    save_choice = input("\n是否保存chunks到文件？(y/n): ").strip().lower()
    
    if save_choice == 'y':
        await save_chunks(chunks, "data/chunks")
        
        index_file = Path("data/chunks/chunk_index.json")
        index_data = {
            'total_chunks': len(chunks),
            'created_at': datetime.now().isoformat(),
            'summary': summary,
            'documents': stats['chunks_by_document']
        }
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Chunks已保存到 data/chunks/")
        print(f"✓ 索引已保存到 data/chunks/chunk_index.json")
    else:
        print("\nChunks未保存")
    
    print("\n" + "="*60)
    print("下一步:")
    print("1. 为chunks生成embeddings: python generate_embeddings.py")
    print("2. 构建知识图谱: python build_knowledge_graph.py")
    print("3. 测试图谱增强RAG: python test_graph_rag.py")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
