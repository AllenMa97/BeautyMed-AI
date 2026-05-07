# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import pickle
import os
import aiohttp
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv
from pathlib import Path
from algorithm_services.utils.logger import get_logger

# 拼接加载自定义路径的.env文件路径：项目根目录/config/SESSION.env
env_path = Path(__file__).resolve().parent.parent / "config" / "SESSION.env"

# 验证.env文件是否存在
if not env_path.exists():
    raise FileNotFoundError(f"未找到配置文件：{env_path}")

# 加载.env文件
load_dotenv(dotenv_path=env_path, encoding="utf-8")

logger = get_logger(__name__)

# ========== 环境变量配置 ==========
# SESSION本地存储路径
SESSION_STORAGE_PATH = os.getenv("SESSION_STORAGE_PATH", "./sessions")
# 线程池大小，控制异步IO并发
EXECUTOR = ThreadPoolExecutor(max_workers=int(os.getenv("THREAD_POOL_MAX_WORKERS", 3)))
# 对话最大Loop数
MAX_LOOP = int(os.getenv("MAX_LOOP", 1))
# 后端数据库API
BACKEND_DB_API = os.getenv("BACKEND_DB_API", "")

# ========== 轮次（单次交互）状态模型（简化后保留核心） ==========
class TurnData:
    """
    轮次级临时状态：仅保留单次用户Query→AI响应的全量数据，轮次结束后可选择性合并到会话全局状态
    核心设计：临时数据隔离，避免污染会话全局状态；新手可直观理解“单次交互”和“全会话”的边界
    """
    # 序列化版本（用于版本兼容）
    VERSION = "1.0"

    def __init__(self, turn_id: str, session_id: str, user_query: str):
        # 基础标识
        self.turn_id = turn_id  # 轮次唯一ID（建议：session_id + 时间戳 + 序号）
        self.session_id = session_id  # 关联的会话ID
        self.turn_create_time = datetime.now()  # 轮次创建时间

        # 用户原始输入
        self.user_query = user_query  # 本次用户Query

        # 意图结果与置信度
        self.user_query_intent: Optional[str] = None  # 本次Query识别的意图
        self.user_query_intent_confidence: float = 0.0  # 本次意图置信度
        # 实体结果
        self.user_query_entities: Dict[str, Any] = {}  # 本次Query识别的实体

        # Planner/Function执行临时数据
        self.plan_functions: list[str] = []  # 本次轮次规划的Function列表
        self.function_exec_results: Dict[str, Any] = {}  # 本次Function执行结果（key=Function名，value=结果）

        # 输出层：AI响应数据
        self.ai_response: Optional[str] = None  # 本次AI最终响应

    def to_dict(self) -> Dict[str, Any]:
        """轮次数据转字典，方便序列化（增加版本字段）"""
        return {
            "version": self.VERSION,
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "turn_create_time": self.turn_create_time.timestamp(),
            "user_query": self.user_query,
            "user_query_intent": self.user_query_intent,
            "user_query_intent_confidence": self.user_query_intent_confidence,
            "user_query_entities": self.user_query_entities.copy(),
            "plan_functions": self.plan_functions.copy(),
            "function_exec_results": self.function_exec_results.copy(),
            "ai_response": self.ai_response,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TurnData":
        """从字典恢复轮次数据（兼容版本，强化时间戳校验）"""
        # 版本兼容（示例：后续可扩展不同版本的解析逻辑）
        data_version = data.get("version", "1.0")
        if data_version != cls.VERSION:
            logger.warning(f"TurnData版本不匹配（当前：{cls.VERSION}，数据：{data_version}），尝试兼容解析")

        # 基础初始化
        turn = cls(
            turn_id=data["turn_id"],
            session_id=data["session_id"],
            user_query=data["user_query"]
        )

        # 强化时间戳转换：仅处理数字类型，否则用当前时间
        ts = data.get("turn_create_time")
        if isinstance(ts, (int, float)):
            try:
                turn.turn_create_time = datetime.fromtimestamp(ts)
            except ValueError:
                logger.warning(f"无效的轮次时间戳{ts}，使用当前时间")
                turn.turn_create_time = datetime.now()
        else:
            turn.turn_create_time = datetime.now()

        # 其他字段恢复（带默认值）
        turn.user_query_intent = data.get("user_query_intent")
        turn.user_query_intent_confidence = data.get("user_query_intent_confidence", 0.0)
        turn.user_query_entities = data.get("user_query_entities", {})
        turn.plan_functions = data.get("plan_functions", [])
        turn.function_exec_results = data.get("function_exec_results", {})
        turn.ai_response = data.get("ai_response")
        return turn

# ========== 会话特征状态标签枚举 ==========
class SessionFeatureStage:
    """
    会话特征状态标签
    
    用于标识当前会话的主要特征，帮助 Planner 更好地理解用户意图
    """
    COMPANIONSHIP_MODE = "COMPANIONSHIP_MODE"
    ADVICE_MODE = "ADVICE_MODE"
    CASUAL_CHAT_MODE = "CASUAL_CHAT_MODE"
    EMOTIONAL_SUPPORT_MODE = "EMOTIONAL_SUPPORT_MODE"
    LEARNING_MODE = "LEARNING_MODE"
    BEAUTY_CONSULTATION_MODE = "BEAUTY_CONSULTATION_MODE"
    PRODUCT_CONSULTATION_MODE = "PRODUCT_CONSULTATION_MODE"
    MEDICAL_CONSULTATION_MODE = "MEDICAL_CONSULTATION_MODE"
    SKINCARE_CONSULTATION_MODE = "SKINCARE_CONSULTATION_MODE"
    
    @classmethod
    def get_description(cls, stage: str) -> str:
        """获取状态标签的中文描述"""
        descriptions = {
            cls.COMPANIONSHIP_MODE: "陪伴倾听",
            cls.ADVICE_MODE: "提供建议",
            cls.CASUAL_CHAT_MODE: "闲聊",
            cls.EMOTIONAL_SUPPORT_MODE: "情感支持",
            cls.LEARNING_MODE: "知识学习",
            cls.BEAUTY_CONSULTATION_MODE: "美学咨询",
            cls.PRODUCT_CONSULTATION_MODE: "产品咨询",
            cls.MEDICAL_CONSULTATION_MODE: "医美咨询",
            cls.SKINCARE_CONSULTATION_MODE: "护肤咨询",
        }
        return descriptions.get(stage, "未知状态")
    
    @classmethod
    def determine_stage(cls, user_input: str, context: str = "") -> str:
        """
        根据用户输入和上下文判断会话状态
        
        Args:
            user_input: 用户输入
            context: 对话上下文
        
        Returns:
            会话状态标签
        """
        input_lower = user_input.lower()
        combined = f"{context} {user_input}".lower()
        
        skin_keywords = ["色斑", "雀斑", "晒斑", "黄褐斑", "痘痘", "痤疮", "皱纹", "细纹", 
                        "毛孔", "黑头", "敏感", "红血丝", "暗沉", "干燥", "出油", "黑眼圈"]
        medical_keywords = ["玻尿酸", "肉毒素", "水光针", "热玛吉", "超声刀", "激光", 
                           "光子嫩肤", "皮秒", "双眼皮", "隆鼻", "吸脂", "填充"]
        product_keywords = ["产品", "推荐", "哪个好", "怎么选", "多少钱", "价格", "品牌"]
        ingredient_keywords = ["烟酰胺", "维c", "视黄醇", "a醇", "水杨酸", "果酸", 
                              "神经酰胺", "胶原蛋白", "胜肽"]
        
        if any(kw in combined for kw in medical_keywords):
            return cls.MEDICAL_CONSULTATION_MODE
        
        if any(kw in combined for kw in skin_keywords):
            return cls.SKINCARE_CONSULTATION_MODE
        
        if any(kw in combined for kw in ingredient_keywords):
            return cls.LEARNING_MODE
        
        if any(kw in combined for kw in product_keywords):
            return cls.PRODUCT_CONSULTATION_MODE
        
        if any(kw in combined for kw in ["推荐", "建议", "怎么", "如何"]):
            return cls.ADVICE_MODE
        
        if any(kw in combined for kw in ["你好", "hi", "hello", "在吗", "谢谢"]):
            return cls.CASUAL_CHAT_MODE
        
        return cls.BEAUTY_CONSULTATION_MODE

# ========== 会话数据模型（简化后保留核心，优化性能） ==========
class SessionData:
    # 序列化版本（用于版本兼容）
    VERSION = "1.0"

    def __init__(self, session_id: str, user_id: Optional[str] = None):
        # -------------------------- 基础字段 --------------------------
        self.session_id = session_id  # 会话唯一ID
        self.user_id = user_id  # 用户ID
        self.create_time: datetime = datetime.now()  # 会话创建时间
        self.update_time: datetime = datetime.now()  # 会话更新时间
        self.language_settings: str = "zh_CN"  # 语言配置

        # -------------------------- 状态/记忆相关字段 --------------------------
        self.feature_stage: str = ""  # 会话特征状态标签
        self.context: str = ""  # 全局对话上下文
        self.dialog_summary: str = ""  # 生成的摘要内容
        self.archived_contexts: List[Dict[str, Any]] = []  # 归档的对话上下文（CONTEXT_COLLAPSE）

        # -------------------------- 临时数据存储 --------------------------
        self.session_data = None  # 由各Function按需写入数据
        # -------------------------- 函数执行中间结果存储 --------------------------
        self.intermediate_results: Dict[str, Any] = {}  # 存储函数执行的中间结果，供后续函数参考
        # -------------------------- 错误记录存储 --------------------------
        self.error_records: List[Dict[str, Any]] = []  # 存储用户纠正的信息，供后续对话参考
        # -------------------------- 用户画像存储 --------------------------
        self.user_profile: Dict[str, Any] = {}  # 存储用户画像信息
        # -------------------------- 知识更新存储 --------------------------
        self.knowledge_updates: List[Dict[str, Any]] = []  # 存储知识更新信息

        # -------------------------- 轮次列表（核心拓展，优化性能） --------------------------
        self.turns: List[TurnData] = []  # 全会话的轮次数据列表
        self.current_turn_id: Optional[str] = None  # 当前活跃轮次ID
        self.current_turn: Optional[TurnData] = None  # 缓存当前轮次，避免遍历

    # 快捷获取当前轮次数据（优化性能）
    def get_current_turn(self) -> Optional[TurnData]:
        """获取当前活跃轮次数据（缓存优化，避免遍历）"""
        # 缓存命中直接返回
        if self.current_turn and self.current_turn.turn_id == self.current_turn_id:
            return self.current_turn
        # 缓存未命中，遍历查找并更新缓存
        if not self.current_turn_id:
            return None
        for turn in self.turns:
            if turn.turn_id == self.current_turn_id:
                self.current_turn = turn
                return turn
        return None

    # 添加轮次数据（自动更新全局状态+缓存）
    def add_turn(self, turn: TurnData):
        """添加轮次数据，并自动更新会话更新时间+当前轮次缓存"""
        self.turns.append(turn)
        self.current_turn_id = turn.turn_id
        self.current_turn = turn  # 更新缓存
        self.update_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（包含所有字段+版本），方便序列化和数据库存储"""
        # 处理datetime：转换为时间戳（兼容JSON和数据库存储）
        def _datetime_to_ts(dt: datetime) -> float:
            return dt.timestamp() if dt else None

        return {
            "version": self.VERSION,
            # 基础字段
            "session_id": self.session_id,
            "user_id": self.user_id,
            "create_time": _datetime_to_ts(self.create_time),
            "update_time": _datetime_to_ts(self.update_time),
            "language_settings": self.language_settings,

            # 状态/记忆相关字段
            "feature_stage": self.feature_stage,
            "context": self.context,
            "dialog_summary": self.dialog_summary,
            "archived_contexts": self.archived_contexts,

            # 轮次数据
            "turns": [turn.to_dict() for turn in self.turns],
            "current_turn_id": self.current_turn_id,

            # 临时数据存储
            "session_data": self.session_data,
            # 函数执行中间结果存储
            "intermediate_results": self.intermediate_results,
            # 错误记录存储
            "error_records": self.error_records,
            # 用户画像存储
            "user_profile": self.user_profile,
            # 知识更新存储
            "knowledge_updates": self.knowledge_updates
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """从字典恢复对象（兼容版本，强化类型校验）"""
        # 版本兼容
        data_version = data.get("version", "1.0")
        if data_version != cls.VERSION:
            logger.warning(f"SessionData版本不匹配（当前：{cls.VERSION}，数据：{data_version}），尝试兼容解析")

        # 1. 初始化基础对象
        session = cls(session_id=data["session_id"], user_id=data.get("user_id"))

        # 2. 处理datetime：强化类型校验
        def _ts_to_datetime(ts: Any) -> datetime:
            """时间戳转datetime（仅处理数字类型，否则返回当前时间）"""
            if not isinstance(ts, (int, float)):
                logger.warning(f"无效的时间戳{ts}（非数字类型），使用当前时间")
                return datetime.now()
            try:
                return datetime.fromtimestamp(ts)
            except (TypeError, ValueError):
                logger.warning(f"时间戳{ts}转换失败，使用当前时间")
                return datetime.now()

        # 3. 恢复所有字段（按分类填充，带默认值保证健壮性）
        # 基础字段
        session.create_time = _ts_to_datetime(data.get("create_time"))
        session.update_time = _ts_to_datetime(data.get("update_time"))
        session.language_settings = data.get("language_settings", "zh_CN")

        # 状态/记忆相关字段
        session.feature_stage = data.get("feature_stage", "")
        session.context = data.get("context", "")
        session.dialog_summary = data.get("dialog_summary", "")

        # 轮次数据恢复
        turns_data = data.get("turns", [])
        session.turns = [TurnData.from_dict(turn_dict) for turn_dict in turns_data]
        session.current_turn_id = data.get("current_turn_id")

        # 恢复当前轮次缓存
        session._current_turn = session.get_current_turn()

        # 临时数据存储
        session.session_data = data.get("session_data")
        # 函数执行中间结果存储
        session.intermediate_results = data.get("intermediate_results", {})
        # 错误记录存储
        session.error_records = data.get("error_records", [])
        # 用户画像存储
        session.user_profile = data.get("user_profile", {})
        # 知识更新存储
        session.knowledge_updates = data.get("knowledge_updates", [])

        return session

# ========== 会话管理器（单例，修复Bug+优化日志） ==========
class SessionManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        """单例模式（线程安全简化版）"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.sessions: Dict[str, SessionData] = {}
        # 初始化存储目录（捕获权限异常）
        try:
            if not os.path.exists(SESSION_STORAGE_PATH):
                os.makedirs(SESSION_STORAGE_PATH, exist_ok=True)
                logger.info(f"会话存储目录初始化成功：{SESSION_STORAGE_PATH}")
        except PermissionError:
            logger.critical(f"创建会话存储目录{SESSION_STORAGE_PATH}权限不足，服务无法启动")
            raise
        except Exception as e:
            logger.critical(f"初始化会话存储目录失败：{str(e)}")
            raise
        # 预留数据库接口扩展入口
        self.use_database = False  # 默认为False，使用文件存储
        self.db_client = None  # 数据库客户端占位
        self._initialized = True

    # -------------------------- 数据库接口（黑盒） --------------------------
    async def _db_get_session(self, session_id: str) -> Optional[SessionData]:
        """调用后端数据库接口获取会话（黑盒）"""
        if not BACKEND_DB_API:
            logger.debug("BACKEND_DB_API未配置，跳过数据库查询")
            return None
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get(f"{BACKEND_DB_API}/{session_id}")
                if resp.status == 200:
                    tmp_data = await resp.json()
                    return SessionData.from_dict(tmp_data)
            logger.warning(f"数据库查询会话{session_id}返回非200状态")
            return None
        except Exception as e:
            logger.error(f"数据库接口查询会话{session_id}失败：{str(e)}", exc_info=True)
            return None

    async def _db_update_session(self, session: SessionData) -> bool:
        """调用后端数据库接口更新会话（黑盒，异步）"""
        if not BACKEND_DB_API:
            logger.debug("BACKEND_DB_API未配置，跳过数据库更新")
            return True
        try:
            # 后续替换为实际的POST/PUT请求
            logger.debug(f"调用数据库接口更新会话：{session.session_id}")
            return True
        except Exception as e:
            logger.error(f"数据库接口更新会话{session.session_id}失败：{str(e)}", exc_info=True)
            return False

    async def _db_clear_session(self, session_id: str) -> bool:
        """调用后端数据库接口删除会话（黑盒，异步）"""
        if not BACKEND_DB_API:
            logger.debug("BACKEND_DB_API未配置，跳过数据库删除")
            return True
        try:
            # 后续替换为实际的DELETE请求
            logger.debug(f"调用数据库接口删除会话：{session_id}")
            return True
        except Exception as e:
            logger.error(f"数据库接口删除会话{session_id}失败：{str(e)}", exc_info=True)
            return False

    # -------------------------- 文件存储相关方法 --------------------------
    def _get_session_file_path(self, session_id: str) -> str:
        """获取会话文件的存储路径"""
        return os.path.join(SESSION_STORAGE_PATH, f"session_{session_id}.pkl")

    def _load_session_from_file(self, session_id: str) -> Optional[SessionData]:
        """从文件加载会话（同步）"""
        try:
            file_path = self._get_session_file_path(session_id)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    logger.warning(f"会话文件为空，删除并返回None：{file_path}")
                    os.remove(file_path)
                    return None
                with open(file_path, "rb") as f:
                    session_data = pickle.load(f)
                logger.info(f"从文件加载会话成功：session_id={session_id}")
                return session_data
            logger.debug(f"会话文件不存在：{file_path}")
            return None
        except EOFError as e:
            logger.warning(f"会话文件不完整，删除并创建新会话：{session_id}, {e}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            return None
        except Exception as e:
            logger.error(f"加载会话{session_id}失败：{str(e)}", exc_info=True)
            return None

    def _save_session_to_file(self, session: SessionData) -> None:
        """保存会话到文件（同步）"""
        try:
            # 移除不可序列化的属性（如asyncio.Task）
            if hasattr(session, '_moderation_task'):
                delattr(session, '_moderation_task')
            if hasattr(session, '_moderation_done'):
                delattr(session, '_moderation_done')
            if hasattr(session, '_is_simple'):
                delattr(session, '_is_simple')
            
            file_path = self._get_session_file_path(session.session_id)
            with open(file_path, "wb") as f:
                pickle.dump(session, f)
            logger.debug(f"会话保存到文件成功：session_id={session.session_id}")
        except Exception as e:
            logger.error(f"保存会话{session.session_id}失败：{str(e)}", exc_info=True)

    async def _async_save_session_to_file(self, session: SessionData) -> None:
        """异步保存会话到文件"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(EXECUTOR, self._save_session_to_file, session)

    async def _async_delete_session_file(self, session_id: str):
        """异步删除会话文件"""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(EXECUTOR, self._delete_session_file, session_id)

    def _delete_session_file(self, session_id: str):
        """同步删除会话文件"""
        try:
            file_path = self._get_session_file_path(session_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"会话文件删除成功：session_id={session_id}")
            else:
                logger.debug(f"会话文件不存在，无需删除：session_id={session_id}")
        except Exception as e:
            logger.error(f"删除会话{session_id}文件失败：{str(e)}", exc_info=True)

    # -------------------------- 核心业务方法 --------------------------
    async def get_session(self, session_id: str, user_id: Optional[str] = None) -> SessionData:
        """
        获取/初始化会话（优先级：数据库接口 → 内存 → 文件 → 新建）
        """
        # 1. 优先从数据库接口获取 (暂时关闭，如需开启注释下方代码)
        # db_session = await self._db_get_session(session_id)
        # if db_session:
        #     self.sessions[session_id] = db_session
        #     logger.info(f"从数据库加载会话成功：session_id={session_id}")
        #     return db_session

        # 2. 数据库无则查内存
        if session_id in self.sessions:
            logger.debug(f"从内存加载会话：session_id={session_id}")
            return self.sessions[session_id]

        # 3. 内存无则查文件
        file_session = self._load_session_from_file(session_id)
        if file_session:
            self.sessions[session_id] = file_session
            return file_session

        # 4. 都没有则新建
        new_session = SessionData(session_id, user_id)
        self.sessions[session_id] = new_session
        logger.info(f"初始化新会话：session_id={session_id}, user_id={user_id}")

        # 新建会话立即异步保存到文件（保底）
        await self._async_save_session_to_file(new_session)
        return new_session

    async def update_session(self, session_id: str, **kwargs):
        """
        更新会话（优先级：异步调用数据库接口 → 更新内存 → 异步保存文件）
        限制仅能更新SessionData已定义的属性，避免动态添加无效属性
        """
        if session_id not in self.sessions:
            raise ValueError(f"会话{session_id}不存在，无法更新")

        # 1. 过滤仅更新已定义的属性
        session = self.sessions[session_id]
        valid_attrs = set(dir(session)) - set(dir(object))  # 获取SessionData自定义属性
        for k, v in kwargs.items():
            if k in valid_attrs:
                setattr(session, k, v)
                logger.debug(f"更新会话属性：session_id={session_id}, key={k}, value={v}")
            elif k == 'intermediate_results':
                # 特殊处理 intermediate_results 字段
                session.intermediate_results = v
                logger.debug(f"更新会话中间结果：session_id={session_id}, key={k}, value={v}")
            elif k == 'error_records':
                # 特殊处理 error_records 字段
                session.error_records = v
                logger.debug(f"更新会话错误记录：session_id={session_id}, key={k}, value={v}")
            elif k == 'user_profile':
                # 特殊处理 user_profile 字段
                session.user_profile = v
                logger.debug(f"更新会话用户画像：session_id={session_id}, key={k}, value={v}")
            elif k == 'knowledge_updates':
                # 特殊处理 knowledge_updates 字段
                session.knowledge_updates = v
                logger.debug(f"更新会话知识更新：session_id={session_id}, key={k}, value={v}")
            else:
                logger.warning(f"忽略无效的会话属性更新：session_id={session_id}, key={k}（属性不存在）")

        # 强制更新时间戳
        session.update_time = datetime.now()

        # 2. 异步调用数据库接口更新（不阻塞）
        asyncio.create_task(self._db_update_session(session))

        # 3. 异步保存到文件（保底）
        await self._async_save_session_to_file(session)

    async def clear_session(self, session_id: str):
        """
        清除会话（优先级：异步调用数据库接口 → 清除内存 → 异步删除文件）
        """
        # 1. 异步调用数据库接口删除（不阻塞）
        asyncio.create_task(self._db_clear_session(session_id))

        # 2. 清除内存中的会话
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"清除内存中会话成功：session_id={session_id}")

        # 3. 异步删除文件（保底）
        await self._async_delete_session_file(session_id)
        
    async def add_error_record(self, session_id: str, correction: str, original_info: str = None):
        """
        添加错误记录到会话
        :param session_id: 会话ID
        :param correction: 用户纠正的信息
        :param original_info: 原始信息（可选）
        """
        if session_id not in self.sessions:
            raise ValueError(f"会话{session_id}不存在，无法添加错误记录")
        
        session = self.sessions[session_id]
        error_record = {
            "timestamp": datetime.now().timestamp(),
            "correction": correction,
            "original_info": original_info
        }
        session.error_records.append(error_record)
        logger.debug(f"添加错误记录到会话：session_id={session_id}, correction={correction}")
        
        # 异步保存到文件
        await self._async_save_session_to_file(session)
        # 异步调用数据库接口更新
        asyncio.create_task(self._db_update_session(session))

# 单例实例
session_manager = SessionManager()