import random
import asyncio
import aiohttp
from typing import Optional, Dict, List
from dataclasses import dataclass
import time

@dataclass
class ProxyConfig:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    
    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

class ProxyPool:
    """
    代理IP池管理器
    """
    
    def __init__(self, proxies: List[ProxyConfig]):
        self.proxies = proxies
        self.active_proxies = proxies.copy()
        self.failed_proxies = []
        self.proxy_stats = {}  # 记录每个代理的成功/失败次数
        self.check_urls = [
            "http://httpbin.org/ip",  # 测试IP
            "https://httpbin.org/ip",  # 测试HTTPS
            "http://www.baidu.com",    # 测试常用网站
        ]
        
        # 初始化统计信息
        for proxy in self.proxies:
            self.proxy_stats[proxy.url] = {"success": 0, "failure": 0}
    
    async def get_random_proxy(self) -> Optional[ProxyConfig]:
        """
        获取一个随机的有效代理
        """
        if not self.active_proxies:
            # 如果没有活跃代理，尝试恢复失败的代理
            self.active_proxies = self.failed_proxies.copy()
            self.failed_proxies = []
            
            if not self.active_proxies:
                return None
        
        return random.choice(self.active_proxies)
    
    async def test_proxy(self, proxy: ProxyConfig, timeout: int = 10) -> bool:
        """
        测试代理是否有效
        """
        try:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout_config = aiohttp.ClientTimeout(total=timeout)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout_config) as session:
                # 尝试访问测试URL
                for test_url in self.check_urls:
                    try:
                        async with session.get(test_url, proxy=proxy.url, proxy_auth=None) as response:
                            if response.status == 200:
                                # 成功访问，更新统计信息
                                self.proxy_stats[proxy.url]["success"] += 1
                                return True
                    except:
                        # 继续尝试下一个URL
                        continue
                
                # 所有URL都无法访问
                self.proxy_stats[proxy.url]["failure"] += 1
                return False
        except:
            self.proxy_stats[proxy.url]["failure"] += 1
            return False
    
    async def remove_failed_proxy(self, proxy: ProxyConfig):
        """
        将失效的代理移至失败列表
        """
        if proxy in self.active_proxies:
            self.active_proxies.remove(proxy)
            self.failed_proxies.append(proxy)
    
    async def get_working_proxy(self, max_retries: int = 3) -> Optional[ProxyConfig]:
        """
        获取一个可用的代理，最多尝试max_retries次
        """
        for _ in range(max_retries):
            proxy = await self.get_random_proxy()
            if proxy and await self.test_proxy(proxy):
                return proxy
            elif proxy:
                await self.remove_failed_proxy(proxy)
        
        return None
    
    def get_best_proxy(self) -> Optional[ProxyConfig]:
        """
        获取成功率最高的代理
        """
        if not self.active_proxies:
            return None
        
        best_proxy = None
        best_success_rate = -1
        
        for proxy in self.active_proxies:
            stats = self.proxy_stats.get(proxy.url, {"success": 0, "failure": 0})
            total_requests = stats["success"] + stats["failure"]
            
            if total_requests > 0:
                success_rate = stats["success"] / total_requests
                if success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_proxy = proxy
            elif best_proxy is None:
                best_proxy = proxy  # 如果都没有统计数据，选择第一个
        
        return best_proxy

# 示例代理池（实际使用时应替换为真实的代理IP）
# SAMPLE_PROXY_POOL = [
#     # 注意：以下仅为示例格式，实际使用时需要替换为真实可用的代理
#     # ProxyConfig(host="proxy1.example.com", port=8080),
#     # ProxyConfig(host="proxy2.example.com", port=8080, username="user", password="pass"),
#     # ProxyConfig(host="proxy3.example.com", port=3128),
# ]

# 创建空代理池，用户可以根据需要添加真实代理
SAMPLE_PROXY_POOL = []

# 创建全局代理池实例
proxy_pool = ProxyPool(SAMPLE_PROXY_POOL)

async def get_random_working_proxy(max_retries: int = 3) -> Optional[str]:
    """
    获取一个可用的代理URL
    """
    # 尝试获取最佳代理（基于成功率）
    best_proxy = proxy_pool.get_best_proxy()
    if best_proxy:
        # 测试最佳代理是否仍然可用
        if await proxy_pool.test_proxy(best_proxy):
            return best_proxy.url
    
    # 如果最佳代理不可用，尝试获取随机代理
    proxy = await proxy_pool.get_working_proxy(max_retries)
    return proxy.url if proxy else None

def add_proxy_to_pool(host: str, port: int, username: Optional[str] = None, 
                     password: Optional[str] = None, protocol: str = "http"):
    """
    向代理池添加新的代理
    """
    new_proxy = ProxyConfig(host=host, port=port, username=username, 
                           password=password, protocol=protocol)
    proxy_pool.proxies.append(new_proxy)
    proxy_pool.active_proxies.append(new_proxy)
    proxy_pool.proxy_stats[new_proxy.url] = {"success": 0, "failure": 0}

def get_proxy_stats():
    """
    获取代理池统计信息
    """
    return proxy_pool.proxy_stats