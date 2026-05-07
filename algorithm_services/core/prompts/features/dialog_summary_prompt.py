# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

def get_dialog_summary_prompt(dialog_content: list, summary_length: int, summary_type: str) -> str:
    """生成对话摘要的LLM提示词"""
    prompt = f"""
    你需要对以下对话内容进行摘要：
    对话内容：{dialog_content}
    要求：
    1. 摘要类型：{summary_type}（brief=简洁版，仅保留核心信息；detail=详细版，保留关键细节）
    2. 长度限制：不超过{summary_length}个字
    3. 逻辑清晰，无冗余信息
    4. 汇总多轮对话的核心需求，忽略闲聊/澄清内容
    5. 保留用户最终确认的需求，删除中间修改过程
    """
    return prompt.strip()
