"""
分割大 embeddings 文件为多个小文件
用于解决 GitHub 100MB 文件大小限制问题
"""
import json
import os
import sys
from typing import Dict, Any


def split_embedding_file(
    input_path: str,
    output_dir: str,
    max_size_mb: float = 50.0
) -> list:
    """
    分割大 embeddings 文件
    
    Args:
        input_path: 输入文件路径
        output_dir: 输出目录
        max_size_mb: 每个分割文件的最大大小（MB）
    
    Returns:
        分割后的文件列表
    """
    print(f"正在读取文件: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_items = len(data)
    print(f"文件包含 {total_items} 个 embeddings")
    
    # 估算每个 item 的大小
    sample_item = json.dumps(list(data.items())[0], ensure_ascii=False)
    avg_item_size = len(sample_item.encode('utf-8'))
    max_items_per_file = int((max_size_mb * 1024 * 1024) / avg_item_size)
    
    print(f"平均每个 item 大小: {avg_item_size} 字节")
    print(f"每个文件最多包含: {max_items_per_file} 个 items")
    
    # 分割数据
    items = list(data.items())
    file_index = 1
    split_files = []
    
    os.makedirs(output_dir, exist_ok=True)
    
    for i in range(0, len(items), max_items_per_file):
        chunk = dict(items[i:i + max_items_per_file])
        
        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_part{file_index}.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False)
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"创建文件: {output_path} ({len(chunk)} items, {file_size:.2f} MB)")
        
        split_files.append(output_path)
        file_index += 1
    
    print(f"\n分割完成！共创建 {len(split_files)} 个文件")
    return split_files


def main():
    """主函数"""
    # 配置
    embeddings_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'embeddings')
    
    # 需要分割的大文件
    large_files = [
        'question_bank_C35.json',  # 103 MB
        'question_bank_C39.json',  # 84 MB
    ]
    
    for filename in large_files:
        input_path = os.path.join(embeddings_dir, filename)
        
        if not os.path.exists(input_path):
            print(f"文件不存在: {input_path}")
            continue
        
        print(f"\n{'='*60}")
        print(f"处理文件: {filename}")
        print(f"{'='*60}")
        
        split_files = split_embedding_file(input_path, embeddings_dir)
        
        # 备份原文件
        backup_path = input_path + '.backup'
        if not os.path.exists(backup_path):
            os.rename(input_path, backup_path)
            print(f"原文件已备份为: {backup_path}")
        
        print()


if __name__ == '__main__':
    main()
