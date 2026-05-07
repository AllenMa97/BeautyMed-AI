# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel, validator

class SafeSchema(BaseModel):
    @validator('components', each_item=True)
    def check_xss(cls, v):
        if 'script' in v.get('props', {}):
            raise ValueError("XSS攻击特征检测")
        return v