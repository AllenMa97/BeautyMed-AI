"""
用户记忆挖掘服务
定期分析用户历史会话，挖掘有价值的信息并生成可聊的话题
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from algorithm_services.utils.logger import get_logger
from algorithm_services.large_model.llm_factory import llm_client_singleton, LLMRequest
from algorithm_services.session.session_factory import session_manager

logger = get_logger(__name__)


DEFAULT_PROVIDER = "aliyun"
DEFAULT_MODEL = "qwen-flash"
LLM_REQUEST_MAX_TOKENS = 4096
LLM_REQUEST_TEMPERATURE = 0.5


MEMORY_MINING_PROMPT = """你是一个用户记忆分析专家。请分析用户的历史会话记录，挖掘以下信息：

1. 用户的兴趣偏好（如：美妆、时尚、护肤等）
2. 用户提到过但未深入讨论的话题
3. 用户关心的人或事（如：家人、朋友、宠物等）
4. 用户的消费习惯和购物偏好
5. 用户的生活方式（工作、旅行、爱好等）
6. 未完成的对话或待回复的问题

请从以下会话记录中提取关键信息，并生成3-5个可以继续聊的话题候选。

会话记录：
{memory_content}

请以JSON格式返回分析结果：
{{
    "key_interests": ["兴趣1", "兴趣2"],
    "unfinished_topics": ["话题1", "话题2"],
    "personal_info": {{"key": "value"}},
    "topic_candidates": [
        {{"topic": "话题描述", "reason": "为什么适合聊这个", "priority": "high/medium/low"}}
    ],
    "insights": "其他有价值的洞察"
}}
"""


class GeneratedTopic:
    """生成的话题"""
    def __init__(
        self,
        topic_id: str,
        topic: str,
        reason: str,
        priority: str,
        related_memory: str,
        created_at: datetime,
        last_shown_at: Optional[datetime] = None,
        shown_count: int = 0
    ):
        self.topic_id = topic_id
        self.topic = topic
        self.reason = reason
        self.priority = priority
        self.related_memory = related_memory
        self.created_at = created_at
        self.last_shown_at = last_shown_at
        self.shown_count = shown_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "topic": self.topic,
            "reason": self.reason,
            "priority": self.priority,
            "related_memory": self.related_memory,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_shown_at": self.last_shown_at.isoformat() if self.last_shown_at else None,
            "shown_count": self.shown_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneratedTopic":
        return cls(
            topic_id=data["topic_id"],
            topic=data["topic"],
            reason=data.get("reason", ""),
            priority=data.get("priority", "medium"),
            related_memory=data.get("related_memory", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_shown_at=datetime.fromisoformat(data["last_shown_at"]) if data.get("last_shown_at") else None,
            shown_count=data.get("shown_count", 0)
        )


class UserMemoryMiningService:
    """
    用户记忆挖掘服务
    定期分析用户历史会话，生成可聊的话题
    """

    def __init__(self):
        self.storage_path = self._get_storage_path()
        self.mining_interval = int(os.getenv("MEMORY_MINING_INTERVAL", 3600))
        self._ensure_storage_dir()

    def _get_storage_path(self) -> str:
        """获取话题存储路径"""
        base_path = os.getenv("SESSION_STORAGE_PATH", "./sessions")
        return os.path.join(base_path, "generated_topics")

    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
        except Exception as e:
            logger.warning(f"创建话题存储目录失败: {e}")

    def _get_user_topics_file(self, user_id: str) -> str:
        """获取用户话题存储文件路径"""
        return os.path.join(self.storage_path, f"topics_{user_id}.json")

    async def mine_user_memories(self, user_id: str, force: bool = False) -> Dict[str, Any]:
        """
        挖掘用户记忆并生成话题
        :param user_id: 用户ID
        :param force: 是否强制重新挖掘
        :return: 挖掘结果
        """
        try:
            logger.info(f"[UserMemoryMining] 开始挖掘用户 {user_id} 的记忆")

            topics = self._load_user_topics(user_id)
            if topics and not force:
                logger.info(f"[UserMemoryMining] 用户 {user_id} 已有 {len(topics)} 个话题，跳过挖掘")
                return {
                    "success": True,
                    "user_id": user_id,
                    "topic_count": len(topics),
                    "message": "使用已有话题"
                }

            sessions = await self._get_user_sessions(user_id)
            if not sessions:
                logger.info(f"[UserMemoryMining] 用户 {user_id} 没有历史会话")
                return {
                    "success": True,
                    "user_id": user_id,
                    "topic_count": 0,
                    "message": "无历史会话"
                }

            memory_content = self._extract_memory_content(sessions)
            if not memory_content:
                logger.info(f"[UserMemoryMining] 用户 {user_id} 的会话内容为空")
                return {
                    "success": True,
                    "user_id": user_id,
                    "topic_count": 0,
                    "message": "会话内容为空"
                }

            mining_result = await self._llm_mine(memory_content)

            if mining_result.get("topic_candidates"):
                new_topics = self._create_topics_from_result(mining_result, user_id)
                self._save_user_topics(user_id, new_topics)
                logger.info(f"[UserMemoryMining] 用户 {user_id} 生成了 {len(new_topics)} 个话题")
            else:
                logger.info(f"[UserMemoryMining] 用户 {user_id} 未能生成有效话题")

            return {
                "success": True,
                "user_id": user_id,
                "topic_count": len(topics),
                "message": "挖掘完成"
            }

        except Exception as e:
            logger.error(f"[UserMemoryMining] 挖掘用户 {user_id} 记忆失败: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def _llm_mine(self, memory_content: str) -> Dict[str, Any]:
        """使用LLM挖掘记忆"""
        try:
            prompt = MEMORY_MINING_PROMPT.format(memory_content=memory_content)

            llm_request = LLMRequest(
                system_prompt="你是一个善于分析用户兴趣和话题的AI助手。",
                user_prompt=prompt,
                temperature=LLM_REQUEST_TEMPERATURE,
                max_tokens=LLM_REQUEST_MAX_TOKENS,
                provider=DEFAULT_PROVIDER,
                model=DEFAULT_MODEL
            )

            response = await llm_client_singleton.call_llm(llm_request)

            if isinstance(response, dict):
                return response
            elif isinstance(response, str):
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    logger.warning(f"LLM返回的不是有效JSON: {response[:200]}")
                    return {}
            return {}

        except Exception as e:
            logger.error(f"LLM挖掘记忆失败: {e}")
            return {}

    def _create_topics_from_result(self, result: Dict[str, Any], user_id: str) -> List[GeneratedTopic]:
        """从LLM结果创建话题对象"""
        topics = []
        candidates = result.get("topic_candidates", [])

        for i, candidate in enumerate(candidates):
            topic = GeneratedTopic(
                topic_id=f"{user_id}_{datetime.now().timestamp()}_{i}",
                topic=candidate.get("topic", ""),
                reason=candidate.get("reason", ""),
                priority=candidate.get("priority", "medium"),
                related_memory=result.get("key_interests", []),
                created_at=datetime.now()
            )
            if topic.topic:
                topics.append(topic)

        return topics

    async def _get_user_sessions(self, user_id: str) -> List:
        """获取用户所有会话"""
        try:
            sessions = await session_manager.session_store.get_all_sessions()
            return [s for s in sessions if s.user_id == user_id]
        except Exception as e:
            logger.warning(f"获取用户会话失败: {e}")
            return []

    def _extract_memory_content(self, sessions: List) -> str:
        """从会话中提取记忆内容"""
        memory_parts = []

        for session in sessions:
            if hasattr(session, 'dialog_summary') and session.dialog_summary:
                memory_parts.append(f"会话摘要: {session.dialog_summary}")

            if hasattr(session, 'turns'):
                for turn in session.turns[-3:]:
                    if hasattr(turn, 'user_query') and turn.user_query:
                        memory_parts.append(f"用户说: {turn.user_query}")
                    if hasattr(turn, 'ai_response') and turn.ai_response:
                        memory_parts.append(f"AI回复: {turn.ai_response[:200]}")

        return "\n".join(memory_parts[-50:])

    def _load_user_topics(self, user_id: str) -> List[GeneratedTopic]:
        """加载用户话题"""
        try:
            file_path = self._get_user_topics_file(user_id)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [GeneratedTopic.from_dict(t) for t in data]
        except Exception as e:
            logger.warning(f"加载用户话题失败: {e}")
        return []

    def _save_user_topics(self, user_id: str, topics: List[GeneratedTopic]):
        """保存用户话题"""
        try:
            file_path = self._get_user_topics_file(user_id)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in topics], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户话题失败: {e}")

    async def get_topic_for_conversation(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取可用于当前对话的话题
        仅返回未在近期展示过的话题
        """
        topics = self._load_user_topics(user_id)
        if not topics:
            return None

        now = datetime.now()
        available_topics = []

        for topic in topics:
            if topic.last_shown_at:
                hours_since_shown = (now - topic.last_shown_at).total_seconds() / 3600
                if hours_since_shown < 24:
                    continue

            available_topics.append(topic)

        if not available_topics:
            return None

        available_topics.sort(key=lambda t: (
            {"high": 0, "medium": 1, "low": 2}.get(t.priority, 1),
            -t.shown_count
        ))

        selected_topic = available_topics[0]
        selected_topic.shown_count += 1
        selected_topic.last_shown_at = now
        self._save_user_topics(user_id, topics)

        return {
            "topic": selected_topic.topic,
            "reason": selected_topic.reason,
            "priority": selected_topic.priority
        }

    async def mine_all_users(self):
        """挖掘所有用户记忆（供定时任务调用）"""
        try:
            sessions = await session_manager.session_store.get_all_sessions()
            user_ids = set()
            for session in sessions:
                if session.user_id:
                    user_ids.add(session.user_id)

            logger.info(f"[UserMemoryMining] 开始挖掘 {len(user_ids)} 个用户的记忆")

            for user_id in user_ids:
                await self.mine_user_memories(user_id)
                await asyncio.sleep(0.5)

            logger.info(f"[UserMemoryMining] 完成所有用户记忆挖掘")

        except Exception as e:
            logger.error(f"[UserMemoryMining] 批量挖掘失败: {e}")


user_memory_mining_service = UserMemoryMiningService()
