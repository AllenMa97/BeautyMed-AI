# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-17
# Copyright (c) 2026. All rights reserved.

"""
实体关系联合抽取 Prompt 模板
符合 NLP 领域命名习惯(Joint Extraction)
用于从文本中同时提取实体和关系,构建知识图谱
"""


def get_joint_extraction_prompt(
    text: str,
    domain: str = "medical_aesthetics",
    max_entities: int = 50,  # 默认不限制
    max_relations: int = 100,
    chunk_id: str = None
) -> str:
    """
    获取实体和关系联合抽取的 Prompt
    
    Args:
        text: 待提取的文本
        domain: 领域(如:medical_aesthetics、general 等)
        max_entities: 最大实体数量(默认不限制)
        max_relations: 最大关系数量(默认不限制)
        chunk_id: Chunk ID(用于日志)
    
    Returns:
        Prompt 字符串
    """
    
    domain_descriptions = {
        "medical_aesthetics": "医美领域,包括:产品、成分、功效、品牌、适用肤质、治疗项目等",
        "general": "通用领域,包括:人名、地名、组织、时间、事件等",
        "product": "产品领域,包括:产品名称、品牌、型号、规格、价格等",
        "academic": "学术领域,包括:论文、作者、机构、期刊、会议等",
    }
    
    domain_desc = domain_descriptions.get(domain, "通用领域")
    
    prompt = f"""你是一个专业的知识图谱构建专家,擅长从文本中提取实体和关系。

## 任务目标
从给定的文本中提取实体和关系,构建结构化的知识图谱。

## 领域信息
当前领域:{domain}
领域描述:{domain_desc}

## 实体类型定义
重点关注以下实体类型:
- **产品/服务**:具体的产品名称、服务项目、治疗手段等
- **成分/原料**:化学成分、天然成分、活性成分等
- **功效/作用**:产品或成分的具体功效、作用机制等
- **品牌/厂商**:品牌名称、生产厂商、研发机构等
- **适用对象**:适用肤质、适用人群、适用症状等
- **分类/类别**:产品类别、功效分类、治疗分类等
- **数值/参数**:价格、容量、浓度、剂量等数值信息
- **其他重要实体**:文本中其他重要的名词实体

## 关系类型定义
重点关注以下关系类型:
- **包含关系**:产品包含成分、类别包含产品等
- **功效关系**:产品/成分具有某种功效
- **适用关系**:产品适用于某种肤质/人群/症状
- **品牌关系**:产品属于某个品牌
- **分类关系**:实体属于某个分类
- **数值关系**:产品的价格、容量等数值属性
- **关联关系**:实体之间的其他语义关联
- **对比关系**:产品之间的对比关系
- **推荐关系**:产品之间的推荐搭配关系

## 待分析文本
```
{text}
```

## 提取要求
1. **实体提取**:
   - 识别文本中的所有重要实体
   - 为每个实体分配合适的类型
   - 评估提取的置信度(0.0-1.0)

2. **关系提取**:
   - 识别实体之间的语义关系
   - 确保关系的方向性(源实体→目标实体)
   - 为关系分配合适的类型
   - 评估关系的置信度(0.0-1.0)

3. **质量控制**:
   - 优先提取高置信度的实体和关系(>0.7)
   - 避免提取过于通用或无意义的实体
   - 确保关系的合理性和可解释性

## 输出格式要求
**极其重要**:请只返回纯 JSON 格式,不要包含任何其他文字、注释或 Markdown 标记！

返回格式:
{{
  "entities": [
    {{
      "entity_name": "实体名称",
      "entity_type": "实体类型",
      "confidence": 0.95
    }}
  ],
  "relations": [
    {{
      "source_entity": "源实体名称",
      "target_entity": "目标实体名称",
      "relation_type": "关系类型",
      "confidence": 0.90
    }}
  ]
}}

**必须遵守的规则**:
1. 只返回 JSON,不要有 ```json 或 ``` 标记
2. 不要有任何注释
3. 所有字符串必须用双引号 " 包裹
4. 不能有未闭合的引号或括号
5. **description 字段必须是单行文本,禁止包含换行符**
6. **description 字段长度不超过 50 个字符**
7. 如果没有任何实体或关系,返回:{{"entities": [], "relations": []}}

现在请分析上述文本,提取实体和关系。直接返回 JSON。"""

    return prompt


def get_entity_extraction_from_query_prompt(
    query: str,
    domain: str = "medical_aesthetics"
) -> str:
    """
    从查询中提取实体的 Prompt
    
    Args:
        query: 用户查询
        domain: 领域
    
    Returns:
        Prompt 字符串
    """
    
    prompt = f"""你是一个专业的实体识别专家,擅长从用户查询中提取关键实体。

## 任务目标
从用户查询中提取关键实体,用于知识图谱检索。

## 领域信息
当前领域:{domain}

## 待分析查询
```
{query}
```

## 提取要求
1. 识别查询中的关键实体(产品、成分、功效、品牌等)
2. 为每个实体分配合适的类型
3. 评估实体的重要性(0.0-1.0)
4. 最多提取 5 个最重要的实体

## 输出格式
请严格按照以下 JSON 格式输出:
{{
  "entities": [
    {{
      "entity_name": "实体名称",
      "entity_type": "实体类型",
      "importance": 0.95,
      "original_text": "原文中的出现"
    }}
  ],
  "query_intent": "查询意图描述",
  "main_entity": "最主要的实体"
}}

现在请分析上述查询,提取关键实体。"""

    return prompt


def get_relation_validation_prompt(
    entities: list,
    relations: list,
    text: str
) -> str:
    """
    验证和优化关系的 Prompt
    
    Args:
        entities: 实体列表
        relations: 关系列表
        text: 原始文本
    
    Returns:
        Prompt 字符串
    """
    
    entities_str = "\n".join([f"- {e.get('entity_name', '')} ({e.get('entity_type', '')})" for e in entities])
    relations_str = "\n".join([
        f"- {r.get('source_entity', '')} -> {r.get('relation_type', '')} -> {r.get('target_entity', '')}"
        for r in relations
    ])
    
    prompt = f"""你是一个知识图谱质量专家,负责验证和优化实体关系。

## 已提取的实体
{entities_str}

## 已提取的关系
{relations_str}

## 原始文本
```
{text}
```

## 验证任务
1. **关系合理性检查**:
   - 每个关系是否在原文中有明确支持?
   - 关系的方向是否正确?
   - 关系类型是否合适?

2. **实体一致性检查**:
   - 关系中引用的实体是否都存在?
   - 实体类型是否一致?

3. **质量评估**:
   - 识别低质量的关系(置信度<0.6)
   - 识别冗余或重复的关系
   - 识别缺失的重要关系

## 输出格式
请严格按照以下 JSON 格式输出:
{{
  "valid_relations": [
    {{
      "source_entity": "源实体",
      "target_entity": "目标实体",
      "relation_type": "关系类型",
      "confidence": 0.90,
      "validation_status": "valid"
    }}
  ],
  "invalid_relations": [
    {{
      "original_relation": "原关系",
      "reason": "无效原因"
    }}
  ],
  "suggested_additions": [
    {{
      "source_entity": "源实体",
      "target_entity": "目标实体",
      "relation_type": "建议添加的关系类型",
      "reason": "建议原因"
    }}
  ],
  "overall_quality": 0.85
}}

现在请验证上述关系,提供优化建议。"""

    return prompt


def get_graph_summarization_prompt(
    entities: list,
    relations: list,
    domain: str = "medical_aesthetics"
) -> str:
    """
    生成知识图谱摘要的 Prompt
    
    Args:
        entities: 实体列表
        relations: 关系列表
        domain: 领域
    
    Returns:
        Prompt 字符串
    """
    
    entity_count = len(entities)
    relation_count = len(relations)
    
    entity_types = {}
    for e in entities:
        etype = e.get('entity_type', 'unknown')
        entity_types[etype] = entity_types.get(etype, 0) + 1
    
    top_entities = sorted(entities, key=lambda x: x.get('confidence', 0), reverse=True)[:5]
    
    prompt = f"""你是一个知识图谱分析专家,负责生成知识图谱的摘要报告。

## 图谱统计信息
- 实体总数:{entity_count}
- 关系总数:{relation_count}
- 领域:{domain}

## 实体类型分布
{json.dumps(entity_types, ensure_ascii=False, indent=2)}

## 核心实体(按置信度排序)
{chr(10).join([f"{i+1}. {e.get('entity_name', '')} ({e.get('entity_type', '')}) - 置信度 {e.get('confidence', 0):.2f}" for i, e in enumerate(top_entities)])}

## 摘要任务
1. 分析图谱的整体结构和特点
2. 识别主要的实体类型和关系模式
3. 评估图谱的覆盖度和完整性
4. 提供优化建议

## 输出格式
请严格按照以下 JSON 格式输出:
{{
  "graph_summary": "图谱整体描述",
  "main_patterns": ["主要模式 1", "主要模式 2"],
  "coverage_assessment": {{
    "breadth": "广度评估",
    "depth": "深度评估",
    "completeness": 0.75
  }},
  "quality_metrics": {{
    "entity_diversity": 0.85,
    "relation_density": 0.65,
    "connectivity": 0.70
  }},
  "recommendations": [
    "建议 1",
    "建议 2"
  ]
}}

现在请生成知识图谱摘要。"""

    return prompt
