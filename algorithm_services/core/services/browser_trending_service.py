# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import asyncio
import random
import logging
import threading
import json
import re
import os
import platform
import concurrent.futures

from typing import List, Dict, Optional, Any
from datetime import datetime
from playwright_stealth import Stealth
from playwright.async_api import async_playwright, Browser, Page, BrowserContext


logger = logging.getLogger(__name__)

try:
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright未安装，浏览器自动化功能不可用。请运行: pip install playwright && playwright install chromium")

try:
    STEALTH_AVAILABLE = True
    logger.info("playwright-stealth 已加载，将使用隐身模式绕过反爬虫检测")
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("playwright-stealth未安装，反爬虫能力受限。请运行: pip install playwright-stealth")

MAX_ITEMS_PER_PLATFORM = 20


class BrowserTrendingService:
    """
    基于浏览器自动化的热搜获取服务
    使用 Playwright 模拟真实浏览器行为，有效规避反爬虫检测

    数据源：
    - 微博热搜
    - 百度热搜
    - 知乎热榜
    - 抖音热点
    - 微博时尚话题
    """

    def __init__(self, headless: bool = True, timeout: int = 45000):
        self.headless = headless
        self.timeout = timeout
        self._lock = threading.Lock()

        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 1800

        self.min_scroll_delay = 0.3
        self.max_scroll_delay = 1.2
        self.min_page_wait = 2
        self.max_page_wait = 5
        self.scroll_iterations = 3

        self._init_enhanced_configs()

    def _init_enhanced_configs(self):
        """初始化增强的反检测配置"""
        system = platform.system()

        if system == "Windows":
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/126.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/125.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
            ]
            self.viewports = [
                {'width': 1920, 'height': 1080},
                {'width': 1536, 'height': 864},
                {'width': 1440, 'height': 900},
                {'width': 1366, 'height': 768},
                {'width': 1600, 'height': 900},
            ]
        elif system == "Darwin":
            self.user_agents = [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18 Safari/605.1.15',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0',
            ]
            self.viewports = [
                {'width': 1440, 'height': 900},
                {'width': 1280, 'height': 800},
                {'width': 1536, 'height': 864},
            ]
        else:
            self.user_agents = [
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0',
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            ]
            self.viewports = [
                {'width': 1920, 'height': 1080},
                {'width': 1366, 'height': 768},
            ]

        self.timezones = [
            'Asia/Shanghai',
            'Asia/Hong_Kong',
            'Asia/Tokyo',
            'Asia/Seoul',
            'America/New_York',
            'Europe/London',
            'America/Los_Angeles',
        ]

        self.locales = [
            'zh-CN,zh;q=0.9,en;q=0.8',
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'zh-TW,zh;q=0.9,en;q=0.8',
            'en-US,en;q=0.9,zh-CN;q=0.8',
            'en-GB,en;q=0.9',
        ]

        self.languages = [
            'zh-CN',
            'zh-TW',
            'en-US',
            'en-GB',
            'ja-JP',
            'ko-KR',
        ]

    @property
    def is_available(self) -> bool:
        return PLAYWRIGHT_AVAILABLE

    async def _random_delay(self, min_sec: float = 0.5, max_sec: float = 2.0):
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def _human_like_scroll(self, page: Page):
        """增强版人类滚动行为"""
        scroll_times = random.randint(3, 6)
        for i in range(scroll_times):
            scroll_distance = random.randint(200, 600)
            await page.evaluate(f'''
                window.scrollBy(0, {scroll_distance});
            ''')
            await asyncio.sleep(random.uniform(0.2, 0.7))

            if random.random() > 0.7 and i < scroll_times - 1:
                await page.evaluate('window.scrollBy(0, -50)')
                await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _human_like_mouse_move(self, page: Page):
        """增强版人类鼠标移动"""
        try:
            viewport = page.viewport_size or {'width': 1920, 'height': 1080}
            points = []
            num_moves = random.randint(5, 12)

            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            points.append((x, y))

            for _ in range(num_moves - 1):
                x = random.randint(50, viewport['width'] - 50)
                y = random.randint(50, viewport['height'] - 50)
                points.append((x, y))

            for i, (x, y) in enumerate(points):
                steps = random.randint(8, 20)
                await page.mouse.move(x, y, steps=steps)
                if i < len(points) - 1:
                    await asyncio.sleep(random.uniform(0.05, 0.15))
        except Exception as e:
            logger.debug(f"鼠标移动模拟失败: {e}")

    async def _human_like_interaction(self, page: Page):
        """增强版人类交互行为"""
        try:
            await self._human_like_mouse_move(page)
            await self._random_delay(0.3, 0.8)

            clickable_elements = await page.query_selector_all(
                'a, button, [role="button"], [tabindex]:not([tabindex="-1"]), input[type="text"], input[type="search"]'
            )
            if clickable_elements and len(clickable_elements) > 0:
                elements = random.sample(
                    clickable_elements[:min(15, len(clickable_elements))],
                    min(random.randint(1, 3), len(clickable_elements))
                )
                for element in elements:
                    try:
                        rect = await element.bounding_box()
                        if rect:
                            center_x = rect['x'] + rect['width'] / 2
                            center_y = rect['y'] + rect['height'] / 2

                            await page.mouse.move(
                                center_x + random.randint(-5, 5),
                                center_y + random.randint(-5, 5),
                                steps=random.randint(3, 8)
                            )
                            await self._random_delay(0.3, 0.8)

                            if random.random() > 0.6:
                                await page.mouse.down()
                                await asyncio.sleep(random.uniform(0.05, 0.1))
                                await page.mouse.up()
                                await self._random_delay(0.5, 1.2)
                    except:
                        pass
        except Exception as e:
            logger.debug(f"人类交互模拟失败: {e}")

    async def _random_keyboard_input(self, page: Page):
        """模拟随机键盘输入"""
        try:
            if random.random() > 0.5:
                await page.keyboard.press('End')
                await self._random_delay(0.5, 1.0)

            if random.random() > 0.7:
                await page.keyboard.press('Home')
                await self._random_delay(0.3, 0.6)

            if random.random() > 0.8:
                for _ in range(random.randint(2, 5)):
                    await page.keyboard.press('ArrowDown')
                    await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            logger.debug(f"键盘输入模拟失败: {e}")

    async def _detect_and_handle_blocking(self, page: Page) -> bool:
        """检测并处理反爬虫拦截"""
        try:
            content = await page.content()

            blocking_indicators = [
                '访问被拒绝', 'access denied', 'blocked', '您的访问已被拦截',
                'cloudflare', 'ray id', '请完成安全验证', '人机验证',
                '验证码', 'captcha', '请输入验证码', '安全验证',
                '检测到异常', '异常访问', 'too many requests',
                '请稍后', '访问频繁', '系统繁忙'
            ]

            is_blocked = any(indicator.lower() in content.lower() for indicator in blocking_indicators)

            if is_blocked:
                logger.warning("检测到反爬虫拦截，尝试绕过...")

                await self._random_delay(2, 4)

                await page.reload(wait_until='domcontentloaded', timeout=30000)
                await self._random_delay(2, 5)

                await self._human_like_interaction(page)
                await self._human_like_scroll(page)
                await self._random_keyboard_input(page)

                content = await page.content()
                is_still_blocked = any(
                    indicator.lower() in content.lower() for indicator in blocking_indicators
                )

                if is_still_blocked:
                    logger.warning("反爬虫拦截仍然存在")
                    return False

            return True

        except Exception as e:
            logger.debug(f"检测拦截失败: {e}")
            return True

    async def _enhanced_page_load(self, page: Page, url: str):
        """增强版页面加载"""
        strategies = [
            ('domcontentloaded', 20000),
            ('load', 30000),
            ('networkidle', 35000),
        ]

        success = False
        for wait_until, timeout in strategies:
            try:
                await page.goto(url, wait_until=wait_until, timeout=timeout)

                current_url = page.url
                if any(keyword in current_url.lower() for keyword in ['login', 'passport', 'verify', 'captcha', 'security', 'auth']):
                    if not any(safe in current_url for safe in ['weibo.com', 'zhihu.com', 'baidu.com', 'douyin.com']):
                        logger.warning(f"页面被重定向到验证页面: {current_url}")
                        try:
                            await page.keyboard.press('Escape')
                            await self._random_delay(1, 2)
                        except:
                            pass
                        continue

                await self._detect_and_handle_blocking(page)

                await self._random_delay(2, 4)
                await self._human_like_mouse_move(page)
                await self._human_like_interaction(page)
                await self._human_like_scroll(page)
                await self._random_delay(1, 2)

                success = True
                break
            except Exception as e:
                logger.debug(f"页面加载策略 {wait_until} 失败: {e}")
                continue

        if not success:
            raise Exception("所有页面加载策略都失败")

    def _get_browser_args(self) -> List[str]:
        """获取增强的浏览器启动参数 - 简化版，减少冲突"""
        args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-background-networking',
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas',
            '--disable-xss-auditor',
            '--disable-renderer-backgrounding',
            '--disable-background-timer-throttling',
            '--window-position=0,0',
            '--disable-popup-blocking',
            '--disable-sync',
            '--metrics-recording-only',
            '--password-store=basic',
            '--use-mock-keychain',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--disable-domain-reliability',
            '--disable-metrics',
            '--disable-metrics-reporting',
            '--disable-software-rasterizer',
            '--use-gl=swiftshader',
        ]

        return args

    def _get_context_options(self) -> Dict[str, Any]:
        """获取浏览器上下文选项"""
        user_agent = random.choice(self.user_agents)
        viewport = random.choice(self.viewports)
        timezone = random.choice(self.timezones)
        locale = random.choice(self.locales)
        language = random.choice(self.languages)

        return {
            'viewport': viewport,
            'user_agent': user_agent,
            'locale': locale,
            'timezone_id': timezone,
            'geolocation': {
                'latitude': random.choice([31.2304, 39.9042, 23.1291, 22.5431, 37.5665, 35.6762]),
                'longitude': random.choice([121.4737, 116.4074, 113.2644, 114.0579, 126.9780, 139.6917])
            },
            'permissions': ['geolocation'],
            'device_scale_factor': random.choice([1, 1.25, 1.5, 2]),
            'is_mobile': False,
            'has_touch': False,
            'extra_http_headers': {
                "Accept-Language": f"{language},{locale}",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": f'"Not-A.Brand";v="99", "Chromium";v="{random.randint(100, 130)}"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": random.choice(['"Windows"', '"macOS"', '"Linux"', '"Android"']),
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": random.choice(['none', 'same-site', 'cross-site']),
                "Sec-Fetch-User": "?1",
            },
            'bypass_csp': True,
        }

    async def _apply_stealth(self, context: BrowserContext):
        """应用隐身脚本"""
        if STEALTH_AVAILABLE:
            try:
                stealth = Stealth()
                for script in stealth.enabled_scripts:
                    await context.add_init_script(script)
                logger.info("已应用 playwright-stealth 隐身模式")
            except Exception as e:
                logger.warning(f"应用 stealth 脚本失败: {e}")

                await context.add_init_script('''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                ''')
                await context.add_init_script('''
                    window.navigator.chrome = {
                        runtime: {}
                    };
                ''')
                await context.add_init_script('''
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                ''')
                await context.add_init_script('''
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-CN', 'zh', 'en']
                    });
                ''')
        else:
            await context.add_init_script('''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            ''')
            await context.add_init_script('''
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            ''')
    
    async def _get_weibo_hot_search(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://s.weibo.com/top/summary"
            logger.info(f"正在访问微博热搜: {url}")
            
            # 使用增强的页面加载策略
            await self._enhanced_page_load(page, url)
            
            current_url = page.url
            if 'login' in current_url.lower() or 'passport' in current_url.lower():
                logger.warning("微博要求登录，尝试等待...")
                await self._random_delay(3, 5)
                if 'login' in page.url.lower():
                    logger.warning("微博强制要求登录，无法获取热搜")
                    return []
            
            hot_list = []
            # 尝试多种选择器策略，增加成功率
            selectors = [
                'td.td-02',  # 原始选择器
                '#pl_top_realtimehot table tbody tr',
                '.data table tbody tr',
                '[node-type="feed_list_item"]',  # 新浪微博可能的选择器
                '.list-item',  # 可能的列表项
                '.card-wrap',  # 卡片包装
                '.weibo-top-item',  # 微博顶部项目
                'tr',  # 通用表格行
            ]
            
            items = []
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items and len(items) > 1:  # 确保找到多个元素
                    logger.debug(f"微博使用选择器 '{selector}' 找到 {len(items)} 个元素")
                    break
            
            for i, item in enumerate(items[:30]):
                try:
                    # 尝试多种方式获取链接和标题
                    link = await item.query_selector('a')
                    if not link:
                        link = await item.query_selector('[href]')
                    
                    if link:
                        title = await link.inner_text()
                        if not title or len(title.strip()) == 0:
                            # 如果链接内没有文本，尝试其他方式
                            title_elem = await item.query_selector('.title, .info, [class*="text"]')
                            if title_elem:
                                title = await title_elem.inner_text()
                        
                        title = title.strip()
                        
                        if not title or title in ['热搜榜', '更多热搜', '实时', '热门', '上升']:
                            continue
                        
                        href = await link.get_attribute('href')
                        if href and not href.startswith('http'):
                            href = 'https://s.weibo.com' + href
                        
                        hot_list.append({
                            'rank': len(hot_list) + 1,
                            'title': title,
                            'url': href or '',
                            'platform': 'weibo'
                        })
                        
                        if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                            break
                            
                except Exception as e:
                    logger.debug(f"解析微博热搜第{i+1}条失败: {e}")
                    continue
            
            logger.info(f"微博热搜获取成功: {len(hot_list)}条")
            return hot_list
            
        except Exception as e:
            logger.warning(f"获取微博热搜失败: {e}")
            return []
    
    async def _get_baidu_hot_search(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://top.baidu.com/board?tab=realtime"
            logger.info(f"正在访问百度热搜: {url}")
            
            # 使用增强的页面加载策略
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            # 尝试多种选择器策略，增加成功率
            selectors = [
                '.category-wrap_iQLoo',  # 原始选择器
                '.content_1YWBm',
                '[class*="item"]',
                '[data-row]',  # 百度可能的数据行
                '.c-single-text',  # 百度单项文本
                '.list-group-item',  # 列表组项目
                '.hot-word',  # 热词
                '.item',  # 通用项目
                'li',  # 列表项
            ]
            
            items = []
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items and len(items) > 1:  # 确保找到多个元素
                    logger.debug(f"百度使用选择器 '{selector}' 找到 {len(items)} 个元素")
                    break
            
            for i, item in enumerate(items[:30]):
                try:
                    # 尝试多种方式获取标题和链接
                    title_elem = await item.query_selector('.title_dIF3B')
                    if not title_elem:
                        title_elem = await item.query_selector('a[title]')
                    if not title_elem:
                        title_elem = await item.query_selector('a')
                    if not title_elem:
                        title_elem = await item.query_selector('[class*="text"], [class*="title"], .keyword')
                    
                    if title_elem:
                        title = await title_elem.inner_text()
                        if not title or len(title.strip()) == 0:
                            title = await title_elem.get_attribute('title') or await title_elem.get_attribute('data-title') or ""
                        
                        title = title.strip()
                        
                        if not title:
                            # 尝试从父元素获取文本
                            parent_text = await item.inner_text()
                            if parent_text:
                                # 提取最相关的文本部分
                                import re
                                matches = re.findall(r'[\u4e00-\u9fa5\w\s]{2,20}', parent_text)
                                if matches:
                                    title = matches[0].strip()
                        
                        if not title or len(title) < 2 or len(title) > 50:
                            continue
                        
                        href = await title_elem.get_attribute('href')
                        if not href:
                            link_elem = await item.query_selector('a[href]')
                            if link_elem:
                                href = await link_elem.get_attribute('href')
                        
                        if href and not href.startswith('http'):
                            href = 'https://www.baidu.com' + href
                        
                        hot_list.append({
                            'rank': len(hot_list) + 1,
                            'title': title,
                            'url': href or '',
                            'platform': 'baidu'
                        })
                        
                        if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                            break
                            
                except Exception as e:
                    logger.debug(f"解析百度热搜第{i+1}条失败: {e}")
                    continue
            
            logger.info(f"百度热搜获取成功: {len(hot_list)}条")
            return hot_list
            
        except Exception as e:
            logger.warning(f"获取百度热搜失败: {e}")
            return []
    
    async def _get_zhihu_hot_search(self, page: Page) -> List[Dict[str, str]]:
        try:
            hot_list = []
            seen_titles = set()
            
            # 首先尝试API方式
            url = "https://www.zhihu.com/api/v4/search/top_search"
            logger.info(f"正在访问知乎热搜API: {url}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=min(self.timeout, 20000))
                content = await page.content()
                
                json_match = re.search(r'<pre[^>]*>(.*?)</pre>', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    data = json.loads(json_str)
                    
                    if 'top_search' in data:
                        top_search = data['top_search']
                        if 'words' in top_search:
                            for item in top_search['words'][:MAX_ITEMS_PER_PLATFORM]:
                                try:
                                    title = item.get('word', '')
                                    if not title:
                                        continue
                                    
                                    if title not in seen_titles:
                                        seen_titles.add(title)
                                        
                                        hot_list.append({
                                            'rank': len(hot_list) + 1,
                                            'title': title,
                                            'url': f'https://www.zhihu.com/search?type=content&q={title}',
                                            'platform': 'zhihu'
                                        })
                                except:
                                    continue
                            
                            if hot_list:
                                logger.info(f"知乎热搜API获取成功: {len(hot_list)}条")
                                return hot_list
            except Exception as e:
                logger.debug(f"知乎热搜API失败: {e}")
            
            # 如果API失败，尝试访问知乎热榜页面
            url = "https://www.zhihu.com/hot"
            logger.info(f"正在访问知乎热榜页面: {url}")
            
            # 使用增强的页面加载策略
            await self._enhanced_page_load(page, url)
            
            # 尝试多种选择器
            selectors = [
                'a[href*="/question/"]',
                '.HotItem a',
                '.HotItem-title a',
                '.List-item a',
                'a[target="_blank"]',
                '[data-zop-question]',  # 知乎可能的数据属性
                '.ContentItem-title a',
                '.RichContent-inner a',
                '.AnswerItem a',
                'article a',
            ]
            
            for selector in selectors:
                try:
                    items = await page.query_selector_all(selector)
                    if items:
                        logger.debug(f"知乎热榜 {selector}: 找到 {len(items)} 个元素")
                        
                        for item in items:
                            try:
                                text = await item.inner_text()
                                text = text.strip()
                                
                                if not text or len(text) < 5 or len(text) > 100:
                                    continue
                                
                                if text in seen_titles:
                                    continue
                                
                                if any(skip in text for skip in ['登录', '注册', '下载', '广告', 'App', '关注', '分享', '知乎', '用户', '话题']):
                                    continue
                                
                                href = await item.get_attribute('href')
                                if href:
                                    if href.startswith('//'):
                                        href = 'https:' + href
                                    elif not href.startswith('http'):
                                        href = 'https://www.zhihu.com' + href
                                
                                seen_titles.add(text)
                                hot_list.append({
                                    'rank': len(hot_list) + 1,
                                    'title': text,
                                    'url': href or '',
                                    'platform': 'zhihu'
                                })
                                
                                if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                    break
                            except:
                                continue
                        
                        if len(hot_list) >= 3:  # 达到最小数量要求就停止
                            break
                except:
                    continue
            
            # 如果热榜页面也失败，尝试首页
            if len(hot_list) < 3:
                url = "https://www.zhihu.com/"
                logger.info(f"正在访问知乎首页: {url}")
                
                # 使用增强的页面加载策略
                await self._enhanced_page_load(page, url)
                
                selectors = [
                    '.List-item a',
                    'a[href*="/question/"]',
                    '.ContentItem-title a',
                    'main a[href*="question"]',
                    '[data-zop-question]',
                    '.AnswerItem a',
                    '.RichContent-inner a',
                    'article a',
                ]
                
                for selector in selectors:
                    try:
                        items = await page.query_selector_all(selector)
                        if items:
                            logger.debug(f"知乎首页 {selector}: 找到 {len(items)} 个元素")
                            
                            for item in items:
                                try:
                                    text = await item.inner_text()
                                    text = text.strip()
                                    
                                    if not text or len(text) < 5 or len(text) > 100:
                                        continue
                                    
                                    if text in seen_titles:
                                        continue
                                    
                                    if any(skip in text for skip in ['登录', '注册', '下载', '广告', 'App', '关注', '分享', '知乎', '用户', '话题']):
                                        continue
                                    
                                    href = await item.get_attribute('href')
                                    if href:
                                        if href.startswith('//'):
                                            href = 'https:' + href
                                        elif not href.startswith('http'):
                                            href = 'https://www.zhihu.com' + href
                                    
                                    seen_titles.add(text)
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href or '',
                                        'platform': 'zhihu'
                                    })
                                    
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                                except:
                                    continue
                            
                            if len(hot_list) >= 3:
                                break
                    except:
                        continue
            
            logger.info(f"知乎热榜获取成功: {len(hot_list)}条")
            return hot_list
            
        except Exception as e:
            logger.warning(f"获取知乎热榜失败: {e}")
            return []
    
    async def _get_douyin_hot_search(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://www.douyin.com/hot"
            logger.info(f"正在访问抖音热点: {url}")
            
            # 使用增强的页面加载策略
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            
            # 尝试多种选择器策略，优先使用更通用的选择器
            strategies = [
                ('[data-e2e*="hot"]', 'data-e2e策略'),
                ('[class*="hot"]', 'hot类策略'),
                ('[class*="rank"]', 'rank类策略'),
                ('[class*="item"]', 'item类策略'),
                ('.hot-list-item', 'hot-list-item策略'),
                ('.hot-item', 'hot-item策略'),
                ('.rank-item', 'rank-item策略'),
                ('li', 'li标签策略'),
                ('div', 'div标签策略'),
                ('[data-elem]', '通用数据元素'),
                ('[data-index]', '索引数据元素'),
            ]
            
            for selector, name in strategies:
                try:
                    items = await page.query_selector_all(selector)
                    if items:
                        logger.debug(f"抖音 {name}: 找到 {len(items)} 个元素")
                        
                        for i, item in enumerate(items[:20]):  # 减少处理数量
                            try:
                                # 尝试多种方式获取文本
                                title = ''
                                
                                # 优先尝试获取链接内的文本
                                title_elem = await item.query_selector('a')
                                if title_elem:
                                    title = await title_elem.inner_text()
                                else:
                                    # 尝试获取标题类元素
                                    title_elem = await item.query_selector('[class*="title"], h1, h2, h3, h4, h5, h6')
                                    if title_elem:
                                        title = await title_elem.inner_text()
                                    else:
                                        # 尝试获取包含文本的元素
                                        text_elem = await item.query_selector('[class*="text"], [class*="content"], span, p')
                                        if text_elem:
                                            title = await text_elem.inner_text()
                                        else:
                                            # 直接获取元素文本
                                            title = await item.inner_text()
                                
                                title = title.strip()
                                
                                if not title or len(title) < 2 or len(title) > 100:
                                    continue
                                
                                # 过滤掉可能是UI元素的文本
                                skip_keywords = ['搜索', '榜单', '排行', '更多', '查看详情', '点击', '首页', '返回', '顶部', '底部', 
                                               '播放', '点赞', '评论', '分享', '喜欢', '关注', '取消', '设置', '退出']
                                if any(keyword in title for keyword in skip_keywords):
                                    continue
                                
                                # 检查是否是数字排名（过滤掉）
                                if re.match(r'^\d+$', title):
                                    continue
                                
                                # 检查是否包含特殊字符（可能是图标或装饰）
                                if re.search(r'[^\w\s\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff]', title) and len([c for c in title if ord(c) < 128]) > 3:
                                    continue
                                
                                hot_list.append({
                                    'rank': len(hot_list) + 1,
                                    'title': title,
                                    'url': '',
                                    'platform': 'douyin'
                                })
                                
                                if len(hot_list) >= MAX_ITEMS_PER_PLATFORM // 2:  # 进一步降低要求
                                    break
                                    
                            except Exception as e:
                                continue  # 继续处理下一个元素
                        
                        if len(hot_list) >= 1:  # 保持最低要求
                            break
                            
                except Exception as e:
                    logger.debug(f"抖音 {name} 策略失败: {e}")
                    continue
            
            logger.info(f"抖音热点获取成功: {len(hot_list)}条")
            return hot_list
            
        except Exception as e:
            logger.warning(f"获取抖音热点失败: {e}")
            return []
    
    async def _get_weibo_fashion_topics(self, page: Page) -> List[Dict[str, str]]:
        try:
            fashion_list = []
            seen_content = set()
            
            fashion_urls = [
                ("https://huati.weibo.com/", "微博话题榜"),
                ("https://s.weibo.com/top/summary", "微博热搜榜"),
            ]
            
            for url, source_name in fashion_urls:
                try:
                    logger.info(f"正在访问{source_name}: {url}")
                    
                    # 使用增强的页面加载策略
                    await self._enhanced_page_load(page, url)
                    
                    current_url = page.url
                    if 'login' in current_url.lower() or 'passport' in current_url.lower():
                        logger.warning(f"{source_name}需要登录，跳过")
                        continue
                    
                    # 模拟人类行为
                    await self._human_like_interaction(page)
                    
                    items = await page.query_selector_all('a[href*="weibo.com"]')
                    if not items:
                        items = await page.query_selector_all('a')
                    
                    fashion_keywords = ['时尚', '穿搭', '美妆', '护肤', '服装', '潮流', '品牌', '设计', 
                                       'fashion', 'style', 'beauty', 'makeup', 'outfit', 'look', 'vogue', 'gucci', 'chanel', 'lv', 'prada']
                    
                    for item in items[:100]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            
                            if not text or len(text) < 5 or len(text) > 100:
                                continue
                            
                            if text in seen_content:
                                continue
                            
                            if any(skip in text for skip in ['登录', '注册', '下载', '广告', '展开', '收起', '关注', '粉丝', '微博', '话题']):
                                continue
                            
                            is_fashion = any(kw in text.lower() for kw in fashion_keywords)
                            
                            if is_fashion or len(fashion_list) < 10:
                                seen_content.add(text)
                                
                                href = await item.get_attribute('href')
                                if href and not href.startswith('http'):
                                    href = 'https://s.weibo.com' + href
                                
                                fashion_list.append({
                                    'rank': len(fashion_list) + 1,
                                    'title': text[:60],
                                    'url': href or '',
                                    'platform': 'weibo_fashion'
                                })
                                
                                if len(fashion_list) >= MAX_ITEMS_PER_PLATFORM:
                                    break
                                    
                        except:
                            continue
                    
                    if len(fashion_list) >= MAX_ITEMS_PER_PLATFORM:
                        break
                        
                except Exception as e:
                    logger.debug(f"访问{source_name}失败: {e}")
                    continue
            
            if len(fashion_list) < 5:
                logger.info("尝试从微博热搜提取时尚相关内容...")
                
                url = "https://s.weibo.com/top/summary"
                # 使用增强的页面加载策略
                await self._enhanced_page_load(page, url)
                
                # 尝试多种选择器
                selectors = [
                    'td.td-02 a',
                    '.list-item a',
                    '[node-type="feed_list_item"] a',
                    '.weibo-item a',
                    'a[href*="/status/"]',
                    'a'
                ]
                
                items = []
                for selector in selectors:
                    items = await page.query_selector_all(selector)
                    if items and len(items) > 1:
                        logger.debug(f"微博时尚使用选择器 '{selector}' 找到 {len(items)} 个元素")
                        break
                
                for item in items[:50]:
                    try:
                        text = await item.inner_text()
                        text = text.strip()
                        
                        if not text or text in ['热搜榜', '更多热搜', '实时', '热门']:
                            continue
                        
                        if text not in seen_content:
                            seen_content.add(text)
                            
                            href = await item.get_attribute('href')
                            if href and not href.startswith('http'):
                                href = 'https://s.weibo.com' + href
                            
                            fashion_list.append({
                                'rank': len(fashion_list) + 1,
                                'title': text[:60],
                                'url': href or '',
                                'platform': 'weibo_fashion'
                            })
                            
                            if len(fashion_list) >= MAX_ITEMS_PER_PLATFORM:
                                break
                    except:
                        continue
            
            logger.info(f"微博时尚话题获取成功: {len(fashion_list)}条")
            return fashion_list
            
        except Exception as e:
            logger.warning(f"获取微博时尚话题失败: {e}")
            return []
    
    async def _get_toutiao_hot_search(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://www.toutiao.com/"
            logger.info(f"正在访问今日头条: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = [
                '.title', '[class*="title"]', 'a[href*="/article/"]', 
                '.main a', '.content a', 'h3', 'h4'
            ]
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告', '推荐']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href if href.startswith('http') else f'https://www.toutiao.com{href}',
                                        'platform': 'toutiao'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"今日头条热点获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取今日头条热点失败: {e}")
            return []
    
    async def _get_tencent_news_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://news.qq.com/"
            logger.info(f"正在访问腾讯新闻: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.title', '.content-title', 'h2', 'h3', 'a[href*="/rain/"]', '.list a']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href,
                                        'platform': 'tencent_news'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"腾讯新闻热点获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取腾讯新闻热点失败: {e}")
            return []
    
    async def _get_netease_news_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://news.163.com/"
            logger.info(f"正在访问网易新闻: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.title', 'h2', 'h3', 'a[href*="/article/"]', '.news a', '.item a']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href,
                                        'platform': 'netease_news'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"网易新闻热点获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取网易新闻热点失败: {e}")
            return []
    
    async def _get_sohu_news_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://news.sohu.com/"
            logger.info(f"正在访问搜狐新闻: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.title', 'h2', 'h3', 'a[href*="/n/"]', '.news a', '.list a']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href,
                                        'platform': 'sohu_news'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"搜狐新闻热点获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取搜狐新闻热点失败: {e}")
            return []
    
    async def _get_thepaper_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://www.thepaper.cn/"
            logger.info(f"正在访问澎湃新闻: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.news_title', 'h2', 'h3', 'a[href*="/newsDetail/"]', '.index_item a']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href,
                                        'platform': 'thepaper'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"澎湃新闻热点获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取澎湃新闻热点失败: {e}")
            return []
    
    async def _get_36kr_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://36kr.com/hot-list/catalog"
            logger.info(f"正在访问36氪热榜: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.hot-list-item', '.article-item', 'a[href*="/p/"]', '.title', 'h2', 'h3']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告', 'APP']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href if href.startswith('http') else f'https://36kr.com{href}',
                                        'platform': '36kr'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"36氪热榜获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取36氪热榜失败: {e}")
            return []
    
    async def _get_hupu_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://bbs.hupu.com/all-gambia"
            logger.info(f"正在访问虎扑热榜: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.post-title', '.title', 'a[href*="/"]', 'h3', 'h4']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href if href.startswith('http') else f'https://bbs.hupu.com{href}',
                                        'platform': 'hupu'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"虎扑热榜获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取虎扑热榜失败: {e}")
            return []
    
    async def _get_bilibili_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://www.bilibili.com/v/popular/rank/all"
            logger.info(f"正在访问B站热榜: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.title', '.info a', 'a[href*="/video/"]', 'h3', 'h4']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 2 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告', '播放', '弹幕']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href if href.startswith('http') else f'https://www.bilibili.com{href}',
                                        'platform': 'bilibili'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"B站热榜获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取B站热榜失败: {e}")
            return []
    
    async def _get_douban_hot(self, page: Page) -> List[Dict[str, str]]:
        try:
            url = "https://www.douban.com/group/explore"
            logger.info(f"正在访问豆瓣热榜: {url}")
            await self._enhanced_page_load(page, url)
            
            hot_list = []
            selectors = ['.title', 'a[href*="/topic/"]', 'h3', 'h4', '.channel-item a']
            
            seen_titles = set()
            for selector in selectors:
                items = await page.query_selector_all(selector)
                if items:
                    for item in items[:30]:
                        try:
                            text = await item.inner_text()
                            text = text.strip()
                            if text and len(text) > 5 and len(text) < 80 and text not in seen_titles:
                                if not any(skip in text for skip in ['登录', '注册', '下载', '广告', '豆瓣']):
                                    seen_titles.add(text)
                                    href = await item.get_attribute('href') or ''
                                    hot_list.append({
                                        'rank': len(hot_list) + 1,
                                        'title': text,
                                        'url': href,
                                        'platform': 'douban'
                                    })
                                    if len(hot_list) >= MAX_ITEMS_PER_PLATFORM:
                                        break
                        except:
                            continue
                if len(hot_list) >= 5:
                    break
            
            logger.info(f"豆瓣热榜获取成功: {len(hot_list)}条")
            return hot_list
        except Exception as e:
            logger.warning(f"获取豆瓣热榜失败: {e}")
            return []
    
    async def _fetch_with_browser(self) -> Dict[str, Any]:
        if not PLAYWRIGHT_AVAILABLE:
            return self._get_empty_result()
        
        trending_data = {
            'weibo_hot': [],
            'baidu_hot': [],
            'zhihu_hot': [],
            'douyin_hot': [],
            'fashion_trends': [],
            'xiaohongshu_hot': [],
            'toutiao_hot': [],
            'tencent_news': [],
            'netease_news': [],
            'sohu_news': [],
            'thepaper': [],
            '36kr': [],
            'hupu': [],
            'bilibili': [],
            'douban': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': True,
            'method': 'browser'
        }
        
        playwright = None
        browser = None
        context = None
        page = None
        
        try:
            playwright = await async_playwright().start()

            browser_args = self._get_browser_args()
            browser_args.append('--user-agent=' + random.choice(self.user_agents))

            browser = await playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )

            context_options = self._get_context_options()
            context = await browser.new_context(**context_options)

            await self._apply_stealth(context)
            
            page = await context.new_page()
            
            page.set_default_timeout(45000)
            
            # 对每个平台使用独立的重试机制
            max_retries = 3  # 增加重试次数
            platforms = [
                ('weibo_hot', self._get_weibo_hot_search),
                ('baidu_hot', self._get_baidu_hot_search),
                ('zhihu_hot', self._get_zhihu_hot_search),
                ('douyin_hot', self._get_douyin_hot_search),
                ('fashion_trends', self._get_weibo_fashion_topics),
                ('toutiao_hot', self._get_toutiao_hot_search),
                ('tencent_news', self._get_tencent_news_hot),
                ('netease_news', self._get_netease_news_hot),
                ('sohu_news', self._get_sohu_news_hot),
                ('thepaper', self._get_thepaper_hot),
                ('36kr', self._get_36kr_hot),
                ('hupu', self._get_hupu_hot),
                ('bilibili', self._get_bilibili_hot),
                ('douban', self._get_douban_hot),
            ]
            
            for platform_name, platform_func in platforms:
                for attempt in range(max_retries + 1):
                    try:
                        logger.info(f"正在获取 {platform_name} (尝试 {attempt + 1}/{max_retries + 1})")
                        result = await platform_func(page)
                        if result:
                            trending_data[platform_name] = result
                            logger.info(f"成功获取 {platform_name}: {len(result)} 条数据")
                            break
                        elif attempt < max_retries:
                            logger.info(f"{platform_name} 第 {attempt + 1} 次尝试未获取到数据，准备重试...")
                            # 增加重试间隔时间
                            await self._random_delay(5, 10)
                        else:
                            logger.warning(f"{platform_name} 经过 {max_retries + 1} 次尝试仍未获取到数据")
                    except Exception as e:
                        logger.warning(f"获取 {platform_name} 时发生错误 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        if attempt < max_retries:
                            # 增加重试间隔时间
                            await self._random_delay(5, 10)
                
                # 在每次请求之间添加延迟，避免过于频繁的请求
                await self._random_delay(3, 6)
            
            trending_data['xiaohongshu_hot'] = []
            
            # 检查是否获取到了任何数据
            all_platforms = ['weibo_hot', 'baidu_hot', 'zhihu_hot', 'douyin_hot', 'fashion_trends',
                           'toutiao_hot', 'tencent_news', 'netease_news', 'sohu_news', 'thepaper',
                           '36kr', 'hupu', 'bilibili', 'douban']
            total_items = sum(len(trending_data[platform]) for platform in all_platforms)
            if total_items == 0:
                trending_data['success'] = False
                logger.warning("浏览器自动化获取未获得任何数据")
            else:
                logger.info(f"浏览器自动化获取成功，总计: {total_items} 条数据")
                
        except Exception as e:
            logger.error(f"浏览器获取热搜失败: {e}")
            trending_data['success'] = False
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except:
                    pass
        
        return trending_data
    
    def _get_empty_result(self) -> Dict[str, Any]:
        return {
            'weibo_hot': [],
            'baidu_hot': [],
            'zhihu_hot': [],
            'douyin_hot': [],
            'fashion_trends': [],
            'xiaohongshu_hot': [],
            'toutiao_hot': [],
            'tencent_news': [],
            'netease_news': [],
            'sohu_news': [],
            'thepaper': [],
            '36kr': [],
            'hupu': [],
            'bilibili': [],
            'douban': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
            'method': 'browser'
        }
    
    def get_all_trending_topics(self) -> Dict[str, Any]:
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._fetch_with_browser())
                        return future.result(timeout=120)
                else:
                    return loop.run_until_complete(self._fetch_with_browser())
            except RuntimeError:
                return asyncio.run(self._fetch_with_browser())
        except Exception as e:
            logger.error(f"浏览器获取热搜失败: {e}")
            return self._get_empty_result()


browser_trending_service = BrowserTrendingService()
