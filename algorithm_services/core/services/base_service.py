# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import uuid
from typing import Any, Dict, Optional
from datetime import datetime


class BaseService:
    """特征服务基类，封装通用初始化和任务ID生成逻辑"""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """
        通用初始化方法
        :param context: 上下文信息，包含用户ID、请求ID、业务标识等
        """
        self.context = context or {}
        # 通用上下文字段初始化（可根据实际业务扩展）
        self.user_id = self.context.get("user_id")
        self.request_id = self.context.get("request_id")
        self.biz_code = self.context.get("biz_code", "default_feature")
        self.create_time = datetime.now()

    def _generate_task_id(self) -> str:
        """
        通用任务ID生成规则：业务编码 + 时间戳 + 随机UUID
        :return: 唯一任务ID
        """
        timestamp = self.create_time.strftime("%Y%m%d%H%M%S%f")[:-3]  # 毫秒级时间戳
        random_uuid = str(uuid.uuid4()).replace("-", "")[:8]  # 短UUID
        task_id = f"{self.biz_code}_{timestamp}_{random_uuid}"
        return task_id

    # 可扩展其他通用方法（如日志记录、参数校验等）
    def _log_info(self, message: str) -> None:
        """通用日志记录（示例）"""
        log_content = f"[TaskID: {self._generate_task_id()}] [User: {self.user_id}] {message}"
        print(log_content)  # 实际场景替换为日志库（如logging）