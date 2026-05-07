import random
import ssl
import aiohttp
from typing import Optional, Dict, List
from knowledge_base_service.utils.logger import get_logger

logger = get_logger(__name__)


class HTTPClient:
    """
    共用的 HTTP 客户端
    提供统一的请求头生成、SSL 配置等功能
    """
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/110.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/108.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/110.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/109.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/110.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    ]
    
    ACCEPT_LANGUAGES = [
        'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.5',
        'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
        'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
        'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    ]
    
    ACCEPT_HEADERS = [
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'application/json, text/plain, */*',
        '*/*',
    ]
    
    REFERERS = [
        'https://www.google.com/',
        'https://www.bing.com/',
        'https://www.baidu.com/',
        'https://www.yahoo.com/',
        'https://www.sogou.com/',
        'https://www.so.com/',
        'https://www.google.com/search?q=health+information',
        'https://www.bing.com/search?q=medical+knowledge',
        'https://www.baidu.com/s?wd=医疗知识',
        '',
    ]
    
    SEC_CH_UA = [
        '"Google Chrome";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
        '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        '"Mozilla Firefox";v="110", "Gecko";v="110", "Firefox";v="110"',
        '"Apple Safari";v="17", "WebKit";v="605", "KHTML, like Gecko";v="17"',
        '"Microsoft Edge";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
    ]
    
    SEC_CH_UA_PLATFORM = [
        '"Windows"',
        '"macOS"',
        '"Linux"',
        '"Android"',
        '"iOS"',
    ]
    
    SENSITIVE_SITES = [
        'who.int',
        'ncbi.nlm.nih.gov',
        'europepmc.org',
        'pubmed.ncbi.nlm.nih.gov',
    ]
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.ssl_context = self._create_ssl_context()
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """创建 SSL 上下文，禁用证书验证"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        except Exception as e:
            logger.warning(f"SSL 配置失败: {str(e)}")
            return ssl.create_default_context()
    
    def get_random_headers(self, simple: bool = False) -> Dict[str, str]:
        """
        生成随机请求头
        
        Args:
            simple: 是否生成极简请求头（用于对请求头长度敏感的网站）
        """
        if simple:
            return {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
        
        accept_encoding = random.choice(['gzip, deflate, br', 'gzip, deflate', 'deflate'])
        connection = random.choice(['keep-alive', 'close'])
        cache_control = random.choice(['max-age=0', 'no-cache', 'no-store'])
        dnt = random.choice(['0', '1'])
        referer = random.choice(self.REFERERS)
        sec_ch_ua = random.choice(self.SEC_CH_UA)
        sec_ch_ua_mobile = random.choice(['?0', '?1'])
        sec_ch_ua_platform = random.choice(self.SEC_CH_UA_PLATFORM)
        
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': random.choice(self.ACCEPT_HEADERS),
            'Accept-Language': random.choice(self.ACCEPT_LANGUAGES),
            'Accept-Encoding': accept_encoding,
            'Connection': connection,
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': random.choice(['document', 'empty']),
            'Sec-Fetch-Mode': random.choice(['navigate', 'cors']),
            'Sec-Fetch-Site': random.choice(['none', 'same-site', 'cross-site']),
            'Cache-Control': cache_control,
            'DNT': dnt,
            'Sec-Ch-Ua': sec_ch_ua,
            'Sec-Ch-Ua-Mobile': sec_ch_ua_mobile,
            'Sec-Ch-Ua-Platform': sec_ch_ua_platform,
            'Sec-Fetch-User': '?1',
        }
        
        if referer:
            headers['Referer'] = referer
        
        if random.random() > 0.5:
            headers['Pragma'] = 'no-cache'
        
        if random.random() > 0.3:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        
        if random.random() > 0.4:
            headers['X-Forwarded-For'] = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        if random.random() > 0.6:
            headers['X-Real-IP'] = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        return headers
    
    def should_use_simple_headers(self, url: str) -> bool:
        """判断是否应该使用极简请求头"""
        url_lower = url.lower()
        return any(site in url_lower for site in self.SENSITIVE_SITES)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()
    
    async def start(self):
        """启动 HTTP 会话"""
        if self.session is None:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.get_random_headers()
            )
    
    async def close(self):
        """关闭 HTTP 会话"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> aiohttp.ClientResponse:
        """发送 GET 请求"""
        if self.session is None:
            await self.start()
        
        if headers is None:
            headers = self.get_random_headers(simple=self.should_use_simple_headers(url))
        
        return await self.session.get(url, headers=headers, **kwargs)
    
    async def post(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> aiohttp.ClientResponse:
        """发送 POST 请求"""
        if self.session is None:
            await self.start()
        
        if headers is None:
            headers = self.get_random_headers(simple=self.should_use_simple_headers(url))
        
        return await self.session.post(url, headers=headers, **kwargs)
    
    async def fetch_text(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> str:
        """获取文本内容"""
        async with await self.get(url, headers=headers, **kwargs) as response:
            return await response.text()
    
    async def fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> dict:
        """获取 JSON 内容"""
        async with await self.get(url, headers=headers, **kwargs) as response:
            return await response.json()
