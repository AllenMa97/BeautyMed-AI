"""
知识问答Prompt
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from algorithm_services.core.prompts.base_prompt import BasePrompt, get_base_system_prompt


class KnowledgeChatPrompt(BasePrompt):
    """知识问答Prompt"""

    KNOWLEDGE_CHAT_RULES = """
你现在进入了「专业顾问模式」，需要基于检索到的专业知识和产品信息，为用户提供准确、专业、有依据的回答。

回答原则：
- 必须基于提供的知识内容和产品信息回答，不要编造信息
- 专业内容要用通俗易懂的方式表达，像给闺蜜讲解一样，避免堆砌术语
- 推荐产品或服务时要自然融入对话，像朋友分享好物一样，不要像推销
- 如果涉及医疗建议，温馨提醒用户咨询专业医生

语气与风格：
- 保持YISIA闺蜜式的温暖亲切，但在此基础上展现专业度
- 可以先共情用户的困扰或需求，再给出专业建议，让用户感到被理解
- 适当使用口语化表达，比如"其实呢""说实话""我比较推荐"等，让回答更自然
- 回答要有层次感，但不要像写论文一样分段罗列，用自然的过渡连接

回答结构：
- 先共情或回应用户的关注点
- 再给出专业解答和建议
- 最后自然地推荐相关产品或服务（如果有合适的）
- 整体像一次有深度的闺蜜对话，而不是一份产品说明书

请直接输出回答内容，不需要JSON格式。
"""

    SYSTEM_PROMPT = None

    @classmethod
    def get_system_prompt(cls, minor_mode: bool = False) -> str:
        return get_base_system_prompt(cls.KNOWLEDGE_CHAT_RULES, minor_mode=minor_mode)

    @staticmethod
    def build_user_prompt(
        user_input: str,
        products: list = None,
        entries: list = None,
        context: str = "",
        personalize: bool = True
    ) -> str:
        """
        构建用户Prompt

        Args:
            user_input: 用户输入
            products: 产品列表，数据结构：
                {'id': str, 'type': 'product', 'name': str, 'brand': str,
                 'group': str, 'category': str, 'reference_price': float,
                 'description': str, 'efficacy': str, 'applicable_skin': str,
                 'capacity': str, 'tags': List[str], 'score': float}
            entries: 知识条目列表，数据结构：
                {'id': str, 'type': 'entry', 'title': str, 'topic': str,
                 'content': str, 'category': str, 'references': List[str],
                 'tags': List[str], 'source_url': str, 'score': float}
            context: 上下文

        Returns:
            构建好的用户Prompt
        """
        prompt_parts = [f"用户问题：{user_input}\n"]

        if context:
            prompt_parts.append(f"对话上下文：\n{context}\n")

        if products and len(products) > 0 and personalize:
            prompt_parts.append("\n以下是我为你找到的相关产品，可以参考一下：\n")
            for i, product in enumerate(products[:5], 1):
                if product.get('type') != 'product':
                    continue

                prompt_parts.append(f"\n【产品 {i}】\n")
                prompt_parts.append(f"名称：{product.get('name', '未知')}\n")

                brand = product.get('brand', '未知')
                prompt_parts.append(f"品牌：{brand}\n")

                if product.get('group'):
                    prompt_parts.append(f"所属集团：{product['group']}\n")

                if product.get('reference_price'):
                    prompt_parts.append(f"参考价格：{product['reference_price']}元\n")

                if product.get('capacity'):
                    prompt_parts.append(f"容量规格：{product['capacity']}\n")

                if product.get('category'):
                    prompt_parts.append(f"产品类别：{product['category']}\n")

                if product.get('efficacy'):
                    prompt_parts.append(f"功效：{product['efficacy']}\n")

                if product.get('applicable_skin'):
                    prompt_parts.append(f"适用肤质：{product['applicable_skin']}\n")

                if product.get('description'):
                    prompt_parts.append(f"产品描述：{product['description']}\n")

                if product.get('tags'):
                    tags_str = '、'.join(product['tags'])
                    prompt_parts.append(f"标签：{tags_str}\n")

                if product.get('score'):
                    prompt_parts.append(f"相关度得分：{product['score']:.4f}\n")

        if entries and len(entries) > 0:
            prompt_parts.append("\n以下是一些相关的专业知识，供你参考：\n")
            for i, entry in enumerate(entries[:5], 1):
                if entry.get('type') != 'entry':
                    continue

                prompt_parts.append(f"\n【知识 {i}】\n")

                if entry.get('title'):
                    prompt_parts.append(f"标题：{entry['title']}\n")

                if entry.get('topic'):
                    prompt_parts.append(f"主题：{entry['topic']}\n")

                if entry.get('category'):
                    prompt_parts.append(f"分类：{entry['category']}\n")

                if entry.get('content'):
                    content = entry['content']
                    if len(content) > 1500:
                        content = content[:1500] + "..."
                    prompt_parts.append(f"内容：\n{content}\n")

                if entry.get('references'):
                    refs_str = '；'.join(entry['references'])
                    prompt_parts.append(f"参考依据：{refs_str}\n")

                if entry.get('tags'):
                    tags_str = '、'.join(entry['tags'])
                    prompt_parts.append(f"标签：{tags_str}\n")

                if entry.get('source_url'):
                    prompt_parts.append(f"来源：{entry['source_url']}\n")

                if entry.get('score'):
                    prompt_parts.append(f"相关度得分：{entry['score']:.4f}\n")

        if not products and not entries:
            prompt_parts.append("\n注意：暂时没有找到相关的产品或知识信息，请基于自己的知识为用户提供建议。\n")

        prompt_parts.append("\n请结合以上信息，用自然亲切的语气回答用户的问题。")

        return "".join(prompt_parts)
