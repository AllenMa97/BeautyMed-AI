# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import logging
import os
import sys
import re
import threading
from logging.handlers import RotatingFileHandler,TimedRotatingFileHandler
from contextvars import ContextVar
from typing import Optional

# -------------------------- 上下文变量（用于日志关联）--------------------------
_log_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
_log_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

# -------------------------- 内部私有配置（无需外部感知）--------------------------
# 全局锁：保证多线程下初始化安全
_LOCK = threading.Lock()
# 标记是否已初始化，避免重复添加Handler
_INITIALIZED = False
# 默认日志配置
_DEFAULT_LOG_CONFIG = {
    "name": "YISIA",
    "log_dir": os.path.join(os.path.dirname(os.path.abspath(__file__)), "../logs"),  # 统一日志目录
    "level": logging.INFO,
    "max_bytes": 10 * 1024 * 1024,  # 10MB（按大小切分用）
    "backup_count": 7,  # 备份文件数
    "encoding": "utf-8",
    "when": "midnight",  # 每天午夜切分
    "interval": 1,
    "keep_days": 7  # 保留7天日志
}

# 全局logger实例
logger = logging.getLogger(_DEFAULT_LOG_CONFIG["name"])

# -------------------------- 内部工具函数 --------------------------
def _get_abs_log_dir():
    """获取绝对日志目录，确保目录存在"""
    log_dir = os.path.abspath(_DEFAULT_LOG_CONFIG["log_dir"])
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return log_dir


class SessionUserFilter(logging.Filter):
    """日志过滤器，自动添加 session_id 和 user_id 到日志记录"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        session_id = _log_session_id.get()
        user_id = _log_user_id.get()
        
        if session_id or user_id:
            extra_info = []
            if session_id:
                extra_info.append(f"[session:{session_id}]")
            if user_id:
                extra_info.append(f"[user:{user_id}]")
            record.session_user = " ".join(extra_info)
        else:
            record.session_user = ""
        
        return True


class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """安全的定时日志文件处理器，处理Windows文件占用问题"""
    
    def doRollover(self):
        try:
            super().doRollover()
        except (PermissionError, OSError) as e:
            print(f"日志文件轮转失败: {e}，继续使用当前日志文件")
            pass


def set_log_context(session_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    设置日志上下文关联
    在处理请求时调用，自动将 session_id 和 user_id 关联到日志输出
    """
    if session_id:
        _log_session_id.set(session_id)
    if user_id:
        _log_user_id.set(user_id)


def clear_log_context():
    """清除日志上下文"""
    _log_session_id.set(None)
    _log_user_id.set(None)


# -------------------------- 内部初始化逻辑（自动执行，外部无感知）--------------------------
def _init_logger():
    """内部初始化日志器，仅执行一次"""
    global _INITIALIZED
    with _LOCK:
        if _INITIALIZED:
            return

        # 1. 清空原有 Handler（防止重复添加导致文件占用）
        logger.handlers.clear()
        
        # 2. 基础配置 - 设置全局日志级别
        logger.setLevel(_DEFAULT_LOG_CONFIG["level"])
        logger.propagate = True  # 启用传播，让子 logger 也能输出

        # 添加 session/user 过滤器
        session_user_filter = SessionUserFilter()
        logger.addFilter(session_user_filter)

        # 3. 控制台 Handler（美化格式，添加 session/user 信息）
        console_fmt = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(session_user)s%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # 控制台只输出 INFO 及以上
        console_handler.setFormatter(console_fmt)
        console_handler.addFilter(session_user_filter)
        logger.addHandler(console_handler)

        # 4. 文件 Handler（按天切分 + 延迟打开文件释放句柄）
        log_file = os.path.join(_get_abs_log_dir(), _DEFAULT_LOG_CONFIG["name"]+".log")
        
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 关键：使用SafeTimedRotatingFileHandler实现按天切分，处理Windows文件占用问题
        file_handler = SafeTimedRotatingFileHandler(
            filename=log_file,
            when=_DEFAULT_LOG_CONFIG["when"],
            interval=_DEFAULT_LOG_CONFIG["interval"],
            backupCount=_DEFAULT_LOG_CONFIG["keep_days"],
            encoding=_DEFAULT_LOG_CONFIG["encoding"],
            delay=True,  # 延迟打开文件，避免Windows文件占用问题
            utc=False,  # 使用本地时间
            atTime=None  # 使用默认时间（午夜）
        )
        # 按天切分的文件名后缀：_DEFAULT_LOG_CONFIG["name"].log.2024-06-01
        file_handler.suffix = "%Y-%m-%d"
        file_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_handler.setFormatter(console_fmt)
        file_handler.addFilter(session_user_filter)
        logger.addHandler(file_handler)

        _INITIALIZED = True
        logger.info("日志系统初始化完成")
        #
        # if log_file:
        #     # 确保日志目录存在
        #     log_dir = os.path.dirname(log_file)
        #     if log_dir and not os.path.exists(log_dir):
        #         os.makedirs(log_dir, exist_ok=True)
        #
        #     # 关键：delay=True 延迟打开文件，写入后释放句柄；RotatingFileHandler避免文件过大
        #     file_handler = RotatingFileHandler(
        #         log_file,
        #         mode="a",
        #         maxBytes=_DEFAULT_LOG_CONFIG["max_bytes"],
        #         backupCount=_DEFAULT_LOG_CONFIG["backup_count"],
        #         encoding=_DEFAULT_LOG_CONFIG["encoding"],
        #         delay=True  # 核心！解决文件占用的关键参数
        #     )
        #     file_handler.setFormatter(console_fmt)  # 复用格式
        #     logger.addHandler(file_handler)
        #
        # # 标记初始化完成
        # _INITIALIZED = True

# -------------------------- 自动执行初始化（外部无需调用）--------------------------
# 模块加载时自动初始化，外部import logger时已完成配置
_init_logger()


def get_logger(name: str) -> logging.Logger:
    """
    获取一个标准、独立、且自动绑定控制台与文件 Handler 的 Logger 对象。
    支持传入任意 name（比如 __name__），每个模块可以有自己的 logger 名称，
    并且所有 logger 都会输出到控制台 + 按天切分的日志文件。
    """
    # 直接返回全局 logger 实例，避免多 logger 配置冲突
    # 所有模块共用同一个 logger 实例，统一管理
    return logger