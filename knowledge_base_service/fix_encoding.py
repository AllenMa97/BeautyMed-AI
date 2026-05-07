import os
import re

def fix_encoding(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        replacements = {
            '评�?': '评分',
            '配�?': '配置',
            '结�?': '结果',
            '文�?': '文件',
            '错误�?': '错误',
            '验证�?': '验证',
            '加载库配�?': '加载库配置',
            '保存库配�?': '保存库配置',
            '创建默认的可信度评�?': '创建默认的可信度评分',
            '创建错误时的可信度评�?': '创建错误时的可信度评分',
            '创建默认的质量检查结�?': '创建默认的质量检查结果',
            '创建错误时的质量检查结�?': '创建错误时的质量检查结果',
            '在{layer}层发现重复内�?': '在{layer}层发现重复内容',
            '读取文件 {md_file} 时出�?': '读取文件 {md_file} 时出错',
            '在{layer}层发现相似内�?': '在{layer}层发现相似内容',
            '相似�?': '相似度',
            '可信度不足，跳过添�?': '可信度不足，跳过添加',
            '层知识到{layer}�?': '层知识到{layer}',
            '可信度评�?': '可信度评估',
            '专业�?': '专业性',
            '权威�?': '权威性',
            '逻辑�?': '逻辑性',
            '时效�?': '时效性',
            '客观�?': '客观性',
            '适用�?': '适用性',
            '条�?': '条目',
            'Dict格�?': 'Dict格式',
            '信息�?': '信息',
            '解析Markdown内容时出�?': '解析Markdown内容时出错',
            '层内容可信度不足': '层内容可信度不足',
            '跳过添加:': '跳过添加:',
            '写入知识条目文件时出�?': '写入知识条目文件时出错',
        }

        for old, new in replacements.items():
            content = content.replace(old, new)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Fixed: {file_path}')
    except Exception as e:
        print(f'Error fixing {file_path}: {e}')

files_to_fix = [
    'core/advanced_retriever.py',
    'core/database_manager.py',
    'core/free_knowledge_api.py',
    'core/knowledge_collection.py',
    'core/processors/layered_web_crawler.py',
    'core/api_knowledge_fetcher.py',
    'core/news_search_service.py',
    'core/processors/web_crawler.py',
    'core/processors/search_engine_api.py',
    'core/multi_layer_retriever.py',
    'core/unified_knowledge_collector.py',
    'core/llm_prompts/url_identification_prompt.py',
    'core/llm_prompts/get_real_urls_prompt.py',
]

for f in files_to_fix:
    fix_encoding(f)

print('Done!')
