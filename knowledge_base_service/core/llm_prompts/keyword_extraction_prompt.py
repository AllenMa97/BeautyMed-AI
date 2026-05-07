# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-21
# Copyright (c) 2026. All rights reserved.

"""
关键词提取 Prompt 模板
用于从查询中提取本地关键词和全局关键词
"""


def get_keyword_extraction_prompt(query: str, domain: str = "medical_aesthetics") -> str:
    """
    获取关键词提取的 Prompt
    
    Args:
        query: 用户查询
        domain: 领域
    
    Returns:
        Prompt 字符串
    """
    
    domain_examples = {
        "medical_aesthetics": """
示例 1:
查询:"1550nm 激光能治疗什么皮肤问题"
本地关键词:["1550nm 激光", "皮肤问题"]
全局关键词:["治疗", "功效", "适应症"]

示例 2:
查询:"兰蔻小黑瓶含有哪些成分"
本地关键词:["兰蔻小黑瓶", "成分"]
全局关键词:["包含", "含有", "成分"]

示例 3:
查询:"玻尿酸和胶原蛋白哪个更适合抗初老"
本地关键词:["玻尿酸", "胶原蛋白", "抗初老"]
全局关键词:["对比", "适用", "功效"]
"""
    }
    
    examples = domain_examples.get(domain, domain_examples["medical_aesthetics"])
    
    prompt = f"""你是一个专业的查询分析专家。请从用户查询中提取两类关键词,用于知识图谱检索。

## 领域
{domain}

## 关键词类型定义

### 本地关键词(Local Keywords)
- **定义**:具体的、特定的实体名称
- **作用**:用于精确匹配知识图谱中的具体实体节点
- **示例**:产品名、成分名、品牌名、治疗项目、皮肤问题等
- **特点**:通常是名词或名词短语

### 全局关键词(Global Keywords)
- **定义**:抽象的、主题性的概念或关系
- **作用**:用于匹配知识图谱中的关系类型或主题
- **示例**:关系类型(包含、治疗、改善)、作用机制、功效类别等
- **特点**:通常是动词、关系词或抽象概念

## 示例
{examples}

## 待分析查询
```
{query}
```

## 提取要求
1. 本地关键词:提取 1-5 个最相关的实体名称
2. 全局关键词:提取 1-3 个最相关的关系或主题
3. 确保关键词简洁明了,不要过长
4. 优先提取查询中明确提到的词汇

## 输出格式
**极其重要**:请只返回纯 JSON 格式

{{
    "local_keywords": ["本地关键词 1", "本地关键词 2"],
    "global_keywords": ["全局关键词 1", "全局关键词 2"]
}}

现在请分析查询,提取关键词。"""

    return prompt
