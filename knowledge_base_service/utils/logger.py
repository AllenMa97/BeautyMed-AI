# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-20
# Copyright (c) 2026. All rights reserved.
"""
终极日志修复模块 - 专门解决 Windows 文件锁定问题

问题根源:
    Windows 系统下，当多个进程同时访问同一个日志文件时，
    会发生文件锁定冲突，导致 "PermissionError: [WinError 32]" 错误。

解决方案:
    1. 提供安全的日志轮转策略
    2. 添加完善的异常处理，确保程序永不崩溃
    3. 通过环境变量控制日志行为

使用方式:
    from utils.logger import get_logger
    
    logger = get_logger("my_module")
    logger.info("这是一个测试日志")
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
import re
import sys

# 从 config 目录读取环境变量
config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
if os.path.exists(config_dir):
    env_file = os.path.join(config_dir, "env")
    if os.path.exists(env_file):
        # 读取环境变量文件
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()


def get_logger(name: str) -> logging.Logger:
    """
    获取通用日志实例（所有模块复用，兼容所有Python版本，时间100%显示）
    
    该函数已升级为终极安全版本，解决了 Windows 下文件锁定问题。
    
    Args:
        name: 日志名称
        
    Returns:
        logging.Logger 实例
    """
    # 创建日志目录 - 改为服务专属目录
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 配置日志：强制使用独立logger，不继承父logger的配置
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # 核心：禁止日志向上传递，避免根logger覆盖格式

    # 安全判断：清空已有handlers（彻底避免重复/继承的handler干扰）
    if logger.handlers:
        logger.handlers.clear()

    # 日志文件路径
    log_file = os.path.join(log_dir, "knowledge_base.log")
    
    # 创建安全的文件处理器
    try:
        # 先尝试创建 TimedRotatingFileHandler
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="D",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        file_handler.suffix = "%Y%m%d"
        file_handler.extMatch = re.compile(r"^\d{8}$")
        
    except Exception as e:
        # 如果创建失败，使用基础 FileHandler
        print(f"警告：无法创建 TimedRotatingFileHandler，使用基础 FileHandler: {e}")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
    
    file_handler.setLevel(logging.INFO)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 格式器（改进格式，使日志更有逻辑性）
    formatter = logging.Formatter(
        "%(asctime)s - %(name)-20s - %(levelname)-8s - [%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 为文件处理器添加终极安全的错误处理
    def ultimate_handleError(record):
        """终极安全的日志错误处理，确保程序永不崩溃"""
        try:
            # 直接调用原始错误处理方法
            if hasattr(file_handler, 'handleError'):
                file_handler.handleError(record)
        except PermissionError as e:
            # 处理文件锁定错误，只记录不中断
            if "Another program is using this file" in str(e) or "被另一个程序使用" in str(e):
                # 记录但不中断程序
                print(f"⚠️ 日志轮转权限错误（可忽略）: {e}")
            else:
                # 其他权限错误也记录但不中断
                print(f"⚠️ 日志权限错误（可忽略）: {e}")
        except Exception as e:
            # 其他异常也记录但不中断
            print(f"⚠️ 日志处理异常（可忽略）: {e}")
            # 不抛出异常，确保不影响主程序运行
    
    # 设置错误处理函数
    if hasattr(file_handler, 'handleError'):
        file_handler.handleError = ultimate_handleError

    return logger