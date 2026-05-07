# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template

ENTITY_RELATION_EXTRACTION_RULES = """
1. 实体分类：
   - 产品名称：医美/护肤产品名称；
   - 医美项目名称：医美服务项目；
   - 症状名称：用户描述的肌肤/身体不适症状（如"敏感肌"/"痘痘肌"/"红血丝"/"干燥脱皮"）；
   - 症状诉求：用户对症状的改善诉求（如"淡化痘印"/"补水保湿"/"修复屏障"）。

2. 关系分类（仅抽取实体间确实存在语义关联的关系，无关联则不抽取）：
   - 产品_适用_症状：某产品适用于改善某症状（如"伊芙泉修复精华适用于敏感肌"）；
   - 产品_具有_功效：某产品具有某功效（如"伊芙泉修复精华具有修复屏障的功效"）；
   - 症状_关联_症状：两个症状之间存在关联（如"痘痘肌伴随红血丝"）；
   - 用户_有_症状：用户自述存在某症状（如"我最近皮肤很干"→用户_有_症状→干燥脱皮）；
   - 用户_诉求_功效：用户表达了某改善诉求（如"想淡化痘印"→用户_诉求_功效→淡化痘印）。

3. 识别逻辑：
   - 合规约束：识别医疗相关症状时，禁止诊断性描述，仅提取症状名称；
   - 关系方向：subject为关系发出方，object为关系接收方，方向必须符合语义（如"用户_有_症状"中subject是用户，object是症状）；
   - 空值处理：若用户未提及某类实体或关系，对应字段为空数组；
   - 置信度规则：每个实体和关系的置信度保留2位小数，0-1区间。

4. 输出格式（严格JSON，无多余内容）：
   {
     "entities": [
        {
            "entity_name": "实体名称",
            "entity_type": "实体类型（匹配预设分类）",
            "confidence": 0.95
        }
     ],
     "relations": [
        {
            "subject": "头实体名称",
            "subject_type": "头实体类型",
            "predicate": "关系类型（匹配预设分类）",
            "object": "尾实体名称",
            "object_type": "尾实体类型",
            "confidence": 0.90
        }
     ],
     "entity_count": 实体数量,
     "relation_count": 关系数量
   }
"""


ENTITY_RELATION_EXTRACTION_USER_TEMPLATE = """
请识别以下用户对话中的实体，并抽取实体间的关系：
用户对话：{user_input}
对话上下文：{context}
请严格按照指定JSON格式返回，仅返回JSON，无其他内容。
"""

def get_entity_relation_extraction_prompt(user_input: str, context) -> dict:
    system_prompt = ENTITY_RELATION_EXTRACTION_RULES

    user_prompt = fill_prompt_template(
        ENTITY_RELATION_EXTRACTION_USER_TEMPLATE,
        user_input=user_input,
        context=context,
    )
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
