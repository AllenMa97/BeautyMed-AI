# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import fill_prompt_template

USER_PROFILE_PROMPT = """
你是YISIA的用户画像分析助手。你的任务是根据用户的对话历史和行为，更新和完善用户画像。

当前用户画像：
{current_profile}

最新对话内容：
用户输入：{user_input}
AI回复：{ai_response}

请分析用户的新信息，并更新用户画像。用户画像应包含以下维度（如果有的话）：

1. 个人偏好：用户的兴趣爱好、偏好（如电影、音乐、书籍、运动、美食等）
2. 美妆习惯：护肤、化妆习惯和偏好（如肤质、喜欢的产品类型、护肤步骤等）
3. 时尚风格：穿衣风格、审美偏好（如喜欢的风格、颜色、品牌等）
4. 生活方式：作息、生活习惯（如作息时间、饮食习惯、运动习惯等）
5. 价值观：生活态度、价值观念（如人生观、消费观、工作观等）
6. 话题倾向：经常讨论的话题类型（如科技、娱乐、时尚、生活等）
7. 互动风格：与AI互动的方式和偏好（如喜欢的沟通方式、表达习惯等）
8. 社交偏好：社交活动偏好（如喜欢的聚会形式、社交场合等）
9. 消费习惯：购物偏好（如品牌偏好、价格敏感度、购买渠道等）
10. 娱乐偏好：休闲娱乐偏好（如喜欢的电影类型、音乐类型、游戏等）

注意：用户可能在闲聊、谈论电影角色、八卦等开放性话题中透露个人信息。请仔细分析对话内容，从中提取可能反映用户特征的信息，即使这些信息不是直接陈述的。

请返回更新后的用户画像
"""

OUTPUT_FORMAT = """
输出格式（严格JSON，无多余内容）：
{
  "personal_preferences": "...",
  "beauty_habits": "...",
  "fashion_style": "...",
  "lifestyle": "...",
  "values": "...",
  "topic_tendency": "...",
  "interaction_style": "...",
  "social_preferences": "...",
  "consumption_habits": "...",
  "entertainment_preferences": "...",
  "last_updated": "时间戳"
}
"""

def get_user_profile_prompt(current_profile, user_input, ai_response):
    user_prompt = fill_prompt_template(
        USER_PROFILE_PROMPT,
        current_profile=current_profile,
        user_input=user_input,
        ai_response=ai_response,
    ) + OUTPUT_FORMAT
    return {"system_prompt": "", "user_prompt":user_prompt}