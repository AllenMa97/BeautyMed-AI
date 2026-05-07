"""
定时任务管理器
负责定时触发各种更新任务
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import threading
import time
import random
import asyncio
from datetime import datetime
from algorithm_services.utils.logger import get_logger
from algorithm_services.core.services.scheduled_update_service import scheduled_update_service

logger = get_logger(__name__)


class ScheduledUpdateManager:
    """
    定时更新管理器
    负责启动和管理定时更新任务
    """

    def __init__(self):
        self.update_interval = int(os.getenv("CONTENT_UPDATE_INTERVAL", 14400))  # 内容更新间隔，默认4小时
        self.key_check_interval = int(os.getenv("API_KEY_CHECK_INTERVAL", 14400))  # API Key检测间隔，默认4小时
        self.simulation_check_interval = int(os.getenv("SIMULATION_CHECK_INTERVAL", 1800))  # 模拟用户检查间隔，默认30分钟
        self.memory_mining_interval = int(os.getenv("MEMORY_MINING_INTERVAL", 7200))  # 用户记忆挖掘间隔，默认2小时
        self.running = False
        self.thread = None
        self.simulation_thread = None
        self.key_check_thread = None
        self.memory_mining_thread = None
        self._request_count = 0
        self._last_reset_hour = None

    def start(self):
        """启动定时更新管理器"""
        if self.running:
            logger.warning("定时更新管理器已在运行中")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        self.simulation_thread = threading.Thread(target=self._run_simulation_loop, daemon=True)
        self.simulation_thread.start()
        
        self.key_check_thread = threading.Thread(target=self._run_key_check_loop, daemon=True)
        self.key_check_thread.start()

        self.memory_mining_thread = threading.Thread(target=self._run_memory_mining_loop, daemon=True)
        self.memory_mining_thread.start()
        
        logger.info(f"定时更新管理器已启动，内容更新间隔：{self.update_interval}s，记忆挖掘间隔：{self.memory_mining_interval}s")

    def stop(self):
        """停止定时更新管理器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.simulation_thread:
            self.simulation_thread.join(timeout=5)
        if self.key_check_thread:
            self.key_check_thread.join(timeout=5)
        if self.memory_mining_thread:
            self.memory_mining_thread.join(timeout=5)
        logger.info("定时更新管理器已停止")

    def record_request(self):
        """记录请求，用于判断系统负载"""
        current_hour = datetime.now().hour
        if self._last_reset_hour != current_hour:
            self._request_count = 0
            self._last_reset_hour = current_hour
        self._request_count += 1

    def get_request_count(self):
        """获取当前小时请求数"""
        return self._request_count

    def is_low_load(self, threshold: int = 50) -> bool:
        """判断是否低负载（当前小时请求数少于阈值）"""
        return self._request_count < threshold

    def _run_loop(self):
        """定时循环 - 热点/时尚/外部知识更新"""
        logger.info("内容更新循环开始")

        scheduled_update_service.update_all()

        while self.running:
            try:
                for _ in range(self.update_interval):
                    if not self.running:
                        break
                    time.sleep(1)

                if self.running:
                    scheduled_update_service.update_all()

            except Exception as e:
                logger.error(f"内容更新循环出错：{e}")
                time.sleep(60)

    def _run_simulation_loop(self):
        """模拟用户生成循环 - 仅在凌晨0-4点且低负载时运行"""
        logger.info("模拟用户生成循环开始")
        
        time.sleep(60)
        
        while self.running:
            try:
                now = datetime.now()
                current_hour = now.hour
                
                if 0 <= current_hour < 4:
                    if self.is_low_load(threshold=30):
                        logger.info(f"[模拟用户] 进入执行窗口(0-4点)，当前负载{self._request_count}，开始生成")
                        scheduled_update_service.update_simulated_users()
                    else:
                        logger.info(f"[模拟用户] 当前负载较高({self._request_count}请求)，跳过执行")
                else:
                    logger.debug(f"[模拟用户] 非执行时段({current_hour}点)，跳过")
                
                time.sleep(self.simulation_check_interval)
                
            except Exception as e:
                logger.error(f"模拟用户生成循环出错：{e}")
                time.sleep(300)

    def _run_key_check_loop(self):
        """定期检测API Key有效性"""
        logger.info("API Key定期检测循环开始")
        
        time.sleep(60)
        
        while self.running:
            try:
                self._check_api_keys()
                time.sleep(self.key_check_interval)
                
            except Exception as e:
                logger.error(f"API Key检测循环出错：{e}")
                time.sleep(300)

    def _check_api_keys(self):
        """检测所有API Key的有效性"""
        try:
            from algorithm_services.large_model.llm_factory import _check_api_key_health, llm_client_factory
            import asyncio
            
            logger.info("[Key定期检测] 开始检测...")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for provider in ["aliyun", "glm", "lansee"]:
                    client = llm_client_factory._client_map.get(provider)
                    if not client:
                        continue
                    
                    config = client.config
                    valid_keys = []
                    
                    for idx, key in enumerate(config.get("api_keys", [])):
                        is_valid = loop.run_until_complete(
                            _check_api_key_health(config["api_base"], key, config.get("model", "qwen-plus"))
                        )
                        if is_valid:
                            valid_keys.append(key)
                            logger.info(f"[Key定期检测] {provider} Key {idx+1} ✅ 可用")
                        else:
                            logger.warning(f"[Key定期检测] {provider} Key {idx+1} ❌ 无效")
                    
                    if valid_keys:
                        config["api_keys"] = valid_keys
                        config["current_key_index"] = 0
                        logger.info(f"[Key定期检测] {provider} 有效Key: {len(valid_keys)}")
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"[Key定期检测] 检测失败: {e}")

    def _run_memory_mining_loop(self):
        """用户记忆挖掘循环 - 仅在凌晨1-5点且低负载时运行"""
        logger.info("用户记忆挖掘循环开始")

        time.sleep(60)

        while self.running:
            try:
                now = datetime.now()
                current_hour = now.hour

                if 1 <= current_hour < 5:
                    if self.is_low_load(threshold=30):
                        logger.info(f"[记忆挖掘] 进入执行窗口(1-5点)，当前负载{self._request_count}，开始挖掘")
                        scheduled_update_service.update_user_memory_mining()
                    else:
                        logger.info(f"[记忆挖掘] 当前负载较高({self._request_count}请求)，跳过执行")
                else:
                    logger.debug(f"[记忆挖掘] 非执行时段({current_hour}点)，跳过")

                time.sleep(self.memory_mining_interval)

            except Exception as e:
                logger.error(f"用户记忆挖掘循环出错：{e}")
                time.sleep(300)


scheduled_update_manager = ScheduledUpdateManager()
