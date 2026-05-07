# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import get_base_system_prompt, fill_prompt_template
import json

YISIA_FREECHAT_RULES = """：
你需提供更个性化、情境化和与时俱进的回应。

交流原则：
- 优先关注用户的情绪和需求，但别反复啰嗦
- 用自然、亲切的语气交流，像朋友一样，可以适当使用"亲爱的"、"宝贝"等亲切称呼
- 主动关心用户的生活状态，展现真诚的关怀
- 保持轻松愉快的氛围，让用户感到舒适
- 可以适度展现个性和幽默感，但要符合情境
- 结合当前时间和地点信息，提供更贴切的回应
- 适时提及当前热门话题，让对话更有趣味性和时效性
- 参考之前函数执行的中间结果，提供连贯的对话体验

关于推荐话题：
- 如果用户输入比较简单（如只有问候），可以考虑用自然的方式引入推荐话题
- 引入话题时要自然，不要生硬，可以先回应用户当前的问题，再巧妙地过渡到话题
- 如果用户正在讨论某个话题，不要强行切换
- 推荐话题只是候选，不是必须使用

输出格式（JSON）：
{
  "chat_response": "字符串 | 闺蜜式自然回复",
  "emotional_tone": "字符串 | 回复的情感基调（温暖/活泼/安慰/鼓励等）"
}
"""

FREECHAT_USER_TEMPLATE = """
用户输入：{user_input}
上下文：{context}
所需语言(bcp47)：{lang}
当前热门话题和趋势：{trending_topics_info}
当前时间和地理位置信息：{time_location_info}
之前函数执行的中间结果：{intermediate_results_info}
用户纠正信息：{error_records_info}
个性化信息：{personalized_context_info}
推荐话题（仅在用户输入简单时参考）：{suggested_topic_info}
其他参考信息：{data}
"""

def get_yisia_free_chat_prompt(user_input: str,
                               context: str = "",
                               lang: str = "zh-CN",
                               data = "",
                               time_location_info: dict = None,
                               trending_topics_info: dict = None,
                               intermediate_results: dict = None,
                               error_records: list = None,
                               personalized_context: str = "",
                               suggested_topic: dict = None,
                               minor_mode: bool = False) -> dict:
    
    # 准备推荐话题信息
    if suggested_topic is None:
        suggested_topic = {}
    if time_location_info is None:
        time_location_info = {
            "time_info": {},
            "location_info": {},
            "combined_context": "无当前时间和位置信息"
        }
    
    # 准备热搜信息
    if trending_topics_info is None:
        trending_topics_info = {
            "fashion_beauty_trends": [],
            "weibo_hot": [],
            "baidu_hot": [],
            "xiaohongshu_hot": [],
            "combined_context": "无当前热搜信息"
        }
    
    # 准备中间结果信息
    if intermediate_results is None:
        intermediate_results = {}
    
    # 准备错误记录信息
    if error_records is None:
        error_records = []
    
    # 将时间地理位置信息格式化为字符串
    time_location_str = time_location_info.get('combined_context', '无法获取当前时间和位置信息')
    
    # 将热搜信息格式化为字符串
    # 优先使用时尚美妆相关热搜
    fashion_trends = trending_topics_info.get('fashion_beauty_trends', [])
    if fashion_trends and isinstance(fashion_trends, list):
        # 提取与Vogue、时尚芭莎、ELLE、GQ相关的话题
        fashion_magazine_trends = []
        for trend in fashion_trends:
            if not isinstance(trend, dict):
                continue
            title = trend.get('title', '').lower()
            if any(magazine in title for magazine in ['vogue', '时尚芭莎', 'elle', '世界时装之苑', '智族gq', 'gq']):
                fashion_magazine_trends.append(trend)
        
        if fashion_magazine_trends:
            # 优先使用与时尚杂志相关的话题
            trending_topics_str = "时尚杂志热点："
            for trend in fashion_magazine_trends[:5]:  # 只取前5个
                trending_topics_str += f"{trend.get('title', '')}；"
        else:
            # 使用所有时尚美妆相关话题
            trending_topics_str = "时尚美妆热点："
            for trend in fashion_trends[:5]:  # 只取前5个
                trending_topics_str += f"{trend.get('title', '')}；"
    else:
        # 如果没有时尚美妆相关热搜，使用默认的热搜信息
        trending_topics_str = trending_topics_info.get('combined_context', '无法获取当前热搜信息')
    
    # 将中间结果信息格式化为字符串
    try:
        intermediate_results_str = json.dumps(intermediate_results, ensure_ascii=False)
    except Exception as e:
        intermediate_results_str = str(intermediate_results)
    
    # 将错误记录信息格式化为字符串
    if error_records:
        error_records_str = "用户纠正信息："
        for record in error_records[-5:]:  # 只取最近的5条
            error_records_str += f"{record.get('correction', '')}；"
    else:
        error_records_str = "无用户纠正信息"
    
    # 个性化上下文信息
    personalized_context_str = personalized_context if personalized_context else "无个性化信息"

    # 推荐话题信息
    if suggested_topic and suggested_topic.get("topic"):
        suggested_topic_str = f"话题：{suggested_topic['topic']}，原因：{suggested_topic.get('reason', '根据您的兴趣推荐')}"
    else:
        suggested_topic_str = "无推荐话题"

    system_prompt = get_base_system_prompt(YISIA_FREECHAT_RULES, minor_mode=minor_mode)
    user_prompt = fill_prompt_template(FREECHAT_USER_TEMPLATE,
                                       user_input=user_input,
                                       context=context,
                                       lang=lang,
                                       time_location_info=time_location_str,
                                       trending_topics_info=trending_topics_str,
                                       intermediate_results_info=intermediate_results_str,
                                       error_records_info=error_records_str,
                                       personalized_context_info=personalized_context_str,
                                       suggested_topic_info=suggested_topic_str,
                                       data=data,
                                       )
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}




