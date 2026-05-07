"""
时间地理位置工具
获取时间和位置信息，用于增强的上下文感知能力
"""
# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import concurrent.futures
import datetime
import pytz
import requests
from typing import Optional, Dict, Any
import threading
import time as time_module

from algorithm_services.utils.logger import get_logger

logger = get_logger(__name__)


class TimeLocationUtil:
    """时间地理位置工具"""

    description = "获取当前时间和位置信息"

    def __init__(self):
        self.china_tz = pytz.timezone('Asia/Shanghai')
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._initialized = False

    def warmup(self) -> bool:
        """预热服务，启动时立即获取时间和位置信息（并行执行）"""
        if self._initialized:
            logger.info("时间地理位置工具已预热，跳过")
            return True

        logger.info("正在预热时间地理位置工具...")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                time_future = executor.submit(self.get_current_time_info)
                location_future = executor.submit(self.get_location_info)

                time_info = time_future.result()
                location_info = location_future.result()

            with self._cache_lock:
                self._cache['time_info'] = time_info
                self._cache['location_info'] = location_info
                self._cache['timestamp'] = time_module.time()
            self._initialized = True
            logger.info(f"时间地理位置工具预热完成: {time_info.get('formatted_time', 'N/A')}")
            return True
        except Exception as e:
            logger.warning(f"时间地理位置工具预热失败: {e}")
            return False

    def get_current_time_info(self) -> Dict[str, str]:
        """获取当前时间信息（使用中国官方时间源+datetime兜底）"""
        time_info = self._get_time_from_official_sources()
        if not time_info:
            time_info = self._get_time_from_local_datetime()
        return time_info

    def _get_time_from_official_sources(self) -> Optional[Dict[str, str]]:
        """尝试从多个中国官方时间源获取时间"""
        official_time_sources = [
            'https://www.ntsc.ac.cn',
            'https://www.beijing-time.org',
            'https://time.tianqi.com',
            'https://www.baidu.com',
            'https://www.taobao.com',
            'https://www.jd.com',
            'https://www.163.com',
            'https://www.sina.com.cn',
            'https://www.qq.com',
            'https://www.btime.com',
        ]

        for url in official_time_sources:
            try:
                response = requests.get(url, timeout=1)
                date_header = response.headers.get('Date')

                if date_header:
                    utc_time = datetime.datetime.strptime(date_header, '%a, %d %b %Y %H:%M:%S %Z')
                    china_time = utc_time.replace(tzinfo=pytz.utc).astimezone(self.china_tz)

                    return {
                        "current_time": china_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "formatted_time": china_time.strftime('%Y年%m月%d日 %H:%M:%S'),
                        "hour": str(china_time.hour),
                        "weekday": self._get_weekday_chinese(china_time.weekday()),
                        "timezone": "Asia/Shanghai",
                        "is_daytime": 6 <= china_time.hour < 18
                    }
            except Exception as e:
                logger.warning(f"从时间源 {url} 获取时间失败: {e}")
                continue

        return None

    def _get_time_from_local_datetime(self) -> Dict[str, str]:
        """使用本地datetime作为兜底方案"""
        china_time = datetime.datetime.now(self.china_tz)

        return {
            "current_time": china_time.strftime('%Y-%m-%d %H:%M:%S'),
            "formatted_time": china_time.strftime('%Y年%m月%d日 %H:%M:%S'),
            "hour": str(china_time.hour),
            "weekday": self._get_weekday_chinese(china_time.weekday()),
            "timezone": "Asia/Shanghai",
            "is_daytime": 6 <= china_time.hour < 18
        }

    def _get_weekday_chinese(self, weekday: int) -> str:
        """将星期几转换为中文"""
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return weekdays[weekday]

    def get_location_info(self, ip_address: Optional[str] = None) -> Dict[str, str]:
        """获取地理位置信息"""
        if not ip_address:
            return {
                "country": "中国",
                "province": "广东省",
                "city": "广州市",
                "location_desc": "中国华南地区",
                "ip_address": "local"
            }

        location_info = self._get_location_from_ip(ip_address)
        if location_info:
            return location_info
        else:
            return {
                "country": "中国",
                "province": "广东省",
                "city": "广州市",
                "location_desc": "中国华南地区",
                "ip_address": ip_address
            }

    def _get_location_from_ip(self, ip_address: str) -> Optional[Dict[str, str]]:
        """通过IP地址获取地理位置（使用免费服务）"""
        try:
            response = requests.get(f'http://ip-api.com/json/{ip_address}?lang=zh-CN', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        "country": data.get('country', '中国'),
                        "province": data.get('regionName', '未知省份'),
                        "city": data.get('city', '未知城市'),
                        "location_desc": f"{data.get('country', '中国')}{data.get('regionName', '')}{data.get('city', '')}",
                        "ip_address": ip_address
                    }
        except Exception as e:
            logger.warning(f"通过IP获取地理位置失败: {e}")

        return None

    def get_context_info(self, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """获取完整的时间和地理位置上下文信息"""
        try:
            time_info = self.get_current_time_info()
            location_info = self.get_location_info(ip_address)

            context_info = {
                "time_info": time_info,
                "location_info": location_info,
                "combined_context": f"current time:{time_info['current_time']}, location:{location_info['country']+location_info['province']+location_info['city']}"
            }

            return context_info
        except Exception as e:
            logger.error(f"获取时间地理位置上下文失败: {str(e)}")
            return {
                "time_info": {},
                "location_info": {},
                "combined_context": "无法获取当前时间和位置信息"
            }

    def get_time_location_info(self, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """获取时间地理位置信息（返回字典格式）"""
        try:
            context_info = self.get_context_info(ip_address)
            return {
                "time_info": context_info.get("time_info", {}),
                "location_info": context_info.get("location_info", {}),
                "combined_context": context_info.get("combined_context", "无法获取当前时间和位置信息"),
                "success": True
            }
        except Exception as e:
            logger.error(f"获取时间地理位置信息失败: {str(e)}")
            return {
                "time_info": {},
                "location_info": {},
                "combined_context": "无法获取当前时间和位置信息",
                "success": False
            }

    def get_for_context(self, ip_address: Optional[str] = None) -> str:
        """获取时间位置上下文（返回字符串格式，用于直接插入prompt）"""
        try:
            context_info = self.get_context_info(ip_address)
            return context_info.get("combined_context", "无法获取当前时间和位置信息")
        except Exception as e:
            logger.error(f"获取时间位置上下文失败: {str(e)}")
            return "无法获取当前时间和位置信息"


time_location_util = TimeLocationUtil()
