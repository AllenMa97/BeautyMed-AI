# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""内容检测子模块"""
from .political_moderation_prompt import get_political_moderation_prompt
from .violence_moderation_prompt import get_violence_moderation_prompt
from .pornography_moderation_prompt import get_pornography_moderation_prompt
from .gambling_moderation_prompt import get_gambling_moderation_prompt
from .drug_moderation_prompt import get_drug_moderation_prompt
from .hate_moderation_prompt import get_hate_moderation_prompt
from .fake_moderation_prompt import get_fake_moderation_prompt

__all__ = [
    'get_political_moderation_prompt',
    'get_violence_moderation_prompt',
    'get_pornography_moderation_prompt',
    'get_gambling_moderation_prompt',
    'get_drug_moderation_prompt',
    'get_hate_moderation_prompt',
    'get_fake_moderation_prompt',
]
