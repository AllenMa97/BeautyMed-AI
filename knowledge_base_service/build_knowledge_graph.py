# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Updated: 2026-04-21
# Copyright (c) 2026. All rights reserved.

"""
知识图谱构建脚本（支持断点续传）
从现有数据中抽取实体和关系，构建知识图谱

特性:
    - 自动从配置文件读取环境变量
    - 支持断点续传（每批处理后自动保存）
    - 批量处理
    - 自动跳过已处理的 chunks
"""

import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime

from core.services.joint_extraction_service import JointExtractionService
from core.chunking.hybrid_chunker import HybridChunker
from core.chunking.base_chunker import Document


def load_env_from_config():
    """从配置文件读取环境变量"""
    script_dir = Path(__file__).parent
    config_file = script_dir / "config" / "env"
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
        print(f"✓ 已从 config/env 加载环境变量")
    else:
        print(f"⚠ 警告：config/env 文件不存在")


async def load_all_data(data_dir: str = "data/chunks") -> List[Dict[str, Any]]:
    """加载所有 chunks"""
    data_path = Path(data_dir)
    all_chunks = []
    
    for file_path in data_path.glob("*.json"):
        if file_path.name == "chunk_index.json":
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
                all_chunks.append(chunk)
        except Exception as e:
            print(f"加载 chunk 文件 {file_path} 失败：{e}")
    
    print(f"成功加载 {len(all_chunks)} 个 chunks")
    return all_chunks


async def load_processed_chunk_ids(output_file: str) -> Set[str]:
    """
    加载已处理的 chunk IDs（用于断点续传）
    
    Args:
        output_file: 知识图谱输出文件
    
    Returns:
        已处理的 chunk ID 集合
    """
    output_path = Path(output_file)
    if not output_path.exists():
        return set()
    
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            chunk_to_entities = data.get('chunk_to_entities', {})
            processed_ids = set(chunk_to_entities.keys())
            print(f"✓ 已加载 {len(processed_ids)} 个已处理的 chunks（断点续传）")
            return processed_ids
    except Exception as e:
        print(f"加载已处理的 chunks 失败：{e}")
        return set()


async def prepare_chunks_for_extraction(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """准备用于抽取的 chunks"""
    prepared_chunks = []
    
    for chunk in chunks:
        prepared_chunk = {
            'chunk_id': chunk.get('chunk_id', ''),
            'document_id': chunk.get('document_id', ''),
            'text': chunk.get('content', ''),
            'metadata': chunk.get('metadata', {})
        }
        prepared_chunks.append(prepared_chunk)
    
    return prepared_chunks


async def build_knowledge_graph(
    api_key: str,
    chunks_dir: str = "data/chunks",
    batch_size: int = 10,
    output_file: str = "data/knowledge_graph/knowledge_graph.json",
    save_interval: int = 1  # 每处理多少批次保存一次
):
    """
    构建知识图谱（支持断点续传）
    
    Args:
        api_key: API 密钥
        chunks_dir: chunks 目录
        batch_size: 批量处理大小
        output_file: 输出文件路径
        save_interval: 每处理多少批次保存一次（用于断点续传）
    """
    print("="*60)
    print("知识图谱构建工具（支持断点续传）")
    print("="*60)
    
    start_time = datetime.now()
    
    # 1. 加载已处理的 chunk IDs（断点续传）
    processed_ids = await load_processed_chunk_ids(output_file)
    
    # 2. 加载所有 chunks
    all_chunks = await load_all_data(chunks_dir)
    
    if not all_chunks:
        print("错误：没有找到 chunks")
        print("请先运行：python chunk_documents.py")
        return
    
    # 3. 过滤出未处理的 chunks
    remaining_chunks = [c for c in all_chunks if c.get('chunk_id') not in processed_ids]
    total_remaining = len(remaining_chunks)
    
    if total_remaining == 0:
        print("✓ 所有 chunks 都已处理完成！")
        return
    
    print(f"本次需要处理 {total_remaining}/{len(all_chunks)} 个未处理的 chunks")
    
    # 4. 准备 chunks
    prepared_chunks = await prepare_chunks_for_extraction(remaining_chunks)
    
    # 5. 初始化服务
    service = JointExtractionService(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-flash"
    )
    
    # 6. 如果已有部分处理，先加载现有知识图谱
    if processed_ids:
        print("加载现有知识图谱...")
        await service.load_knowledge_graph()
        stats = await service.get_knowledge_graph_stats()
        print(f"当前知识图谱状态：{stats.total_entities} 个实体，{stats.total_relations} 个关系")
    
    # 7. 批量处理
    total_chunks = len(prepared_chunks)
    batch_count = 0
    error_count = 0
    
    for i in range(0, total_chunks, batch_size):
        batch = prepared_chunks[i:i + batch_size]
        batch_count += 1
        
        print(f"\n处理批次 {batch_count}/{(total_chunks + batch_size - 1)//batch_size}")
        print(f"Chunk 范围：{i+1}-{min(i+batch_size, total_chunks)}/{total_chunks}")
        
        try:
            results = await service.batch_joint_extract(
                chunks=batch,
                domain="medical_aesthetics",
                max_entities_per_chunk=50,  # 不限制，让 LLM 自由抽取
                max_relations_per_chunk=100
            )
            
            batch_entities = sum(len(r.entities) for r in results)
            batch_relations = sum(len(r.relations) for r in results)
            print(f"  ✓ 提取 {batch_entities} 个实体，{batch_relations} 个关系")
            
        except Exception as e:
            print(f"  ✗ 批次处理失败：{e}")
            error_count += 1
            # 继续处理下一批，不中断
        
        # 8. 定期保存（断点续传关键）
        if batch_count % save_interval == 0:
            try:
                await service.save_knowledge_graph(output_file)
                stats = await service.get_knowledge_graph_stats()
                print(f"\n  💾 已保存进度（断点续传点）:")
                print(f"     实体总数：{stats.total_entities}")
                print(f"     关系总数：{stats.total_relations}")
                print(f"     包含实体的 chunks: {stats.chunks_with_entities}")
            except Exception as e:
                print(f"  ⚠ 保存失败：{e}")
    
    # 9. 最终保存
    print("\n保存最终结果...")
    try:
        await service.save_knowledge_graph(output_file)
        stats = await service.get_knowledge_graph_stats()
        print(f"✓ 知识图谱已保存到：{output_file}")
        print(f"  实体总数：{stats.total_entities}")
        print(f"  关系总数：{stats.total_relations}")
        print(f"  包含实体的 chunks: {stats.chunks_with_entities}")
    except Exception as e:
        print(f"✗ 保存失败：{e}")
    
    # 10. 统计信息
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "="*60)
    print("构建完成！")
    print("="*60)
    print(f"总耗时：{duration}")
    print(f"成功处理批次：{batch_count}")
    print(f"失败批次：{error_count}")
    print(f"存储位置：{output_file}")
    print("\n下一步:")
    print("1. 测试图谱增强 RAG: python test_graph_rag.py")
    print("2. 启动服务：python main.py")
    print("="*60)


async def main():
    """主函数"""
    print("="*60)
    print("知识图谱构建工具")
    print("="*60)
    
    # 自动从配置文件加载环境变量
    load_env_from_config()
    
    # 获取 API Key（支持多个 Key 轮询）
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("错误：DASHSCOPE_API_KEY 未设置")
        print("请确保 config/env 文件中配置了有效的 API Key")
        return
    
    print(f"使用 API Key: {api_key[:10]}...")
    
    # 选择构建模式
    print("\n选择构建模式:")
    print("1. 全量构建（从 chunks 构建）")
    print("2. 增量构建（从新 chunks 构建）")
    print("3. 完整流程（文档 chunk 化 + embeddings + 知识图谱）")
    print("4. 重新构建（清空现有图谱，从头构建）")
    
    choice = input("请输入选择 (1/2/3/4): ").strip()
    
    if choice == "1":
        await build_knowledge_graph(
            api_key=api_key,
            chunks_dir="data/chunks",
            batch_size=10,
            save_interval=1  # 每批都保存，支持断点续传
        )
    elif choice == "2":
        print("增量构建功能暂未实现")
    elif choice == "3":
        print("完整流程功能暂未实现")
    elif choice == "4":
        # 重新构建 - 清空现有图谱
        print("\n" + "="*60)
        print("警告：重新构建将清空现有知识图谱！")
        print("="*60)
        
        confirm = input("确定要清空现有知识图谱并重新构建吗？(yes/no): ").strip().lower()
        
        if confirm == "yes":
            # 删除现有知识图谱文件
            output_file = Path("data/knowledge_graph/knowledge_graph.json")
            if output_file.exists():
                try:
                    output_file.unlink()
                    print(f"✓ 已删除现有知识图谱：{output_file}")
                except Exception as e:
                    print(f"✗ 删除失败：{e}")
                    return
            
            # 重新开始构建
            await build_knowledge_graph(
                api_key=api_key,
                chunks_dir="data/chunks",
                batch_size=10,
                save_interval=1  # 每批都保存，支持断点续传
            )
        else:
            print("已取消重新构建")
    else:
        print("无效选择")


if __name__ == "__main__":
    asyncio.run(main())
