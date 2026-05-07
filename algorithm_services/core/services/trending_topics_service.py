# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

import os
import requests
from bs4 import BeautifulSoup
import re
import random
from typing import List, Dict, Optional
import logging
from datetime import datetime
import time
import threading
import json

logger = logging.getLogger(__name__)

TRENDING_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge")
TRENDING_CACHE_FILE = os.path.join(TRENDING_DATA_DIR, "trending.json")

# 导入浏览器服务 (核心依赖)
try:
    from .browser_trending_service import browser_trending_service, PLAYWRIGHT_AVAILABLE
except ImportError:
    try:
        from browser_trending_service import browser_trending_service, PLAYWRIGHT_AVAILABLE
    except ImportError:
        PLAYWRIGHT_AVAILABLE = False
        browser_trending_service = None
        logger.warning("浏览器自动化服务导入失败")

# 导入时尚门户服务 (可选)
try:
    from .fashion_portal_service import fashion_portal_service
except ImportError:
    try:
        from fashion_portal_service import fashion_portal_service
    except ImportError:
        fashion_portal_service = None
        logger.warning("时尚门户服务导入失败")

class TrendingTopicsService:
    """
    热搜话题服务
    用于获取微博、搜索引擎、小红书等平台的热搜信息
    """
    
    UAPIS_BASE_URL = "https://uapis.cn/api/v1/misc/hotboard"
    DABENSHI_BASE_URL = "https://dabenshi.cn/other/api/hot.php"
    
    UAPIS_PLATFORMS = {
        'zhihu_hot': 'zhihu',
        'baidu_hot': 'baidu',
        'douyin_hot': 'douyin',
        'bilibili': 'bilibili',
        'toutiao_hot': 'toutiao',
        'thepaper': 'thepaper',
        'hupu': 'hupu',
        'douban': 'douban-movie',
        'douban_group': 'douban-group',
        '36kr': '36kr',
        'sina': 'sina',
        'netease_news': 'netease-news',
        'tencent_news': 'qq-news',
        'tieba': 'tieba',
        'kuaishou': 'kuaishou',
        'huxiu': 'huxiu',
        'ifanr': 'ifanr',
        'sspai': 'sspai',
        'ithome': 'ithome',
        'juejin': 'juejin',
        'jianshu': 'jianshu',
        'guokr': 'guokr',
        'smzdm': 'smzdm',
        'coolapk': 'coolapk',
        'v2ex': 'v2ex',
    }
    
    FASHION_KEYWORDS = [
        '时尚', '穿搭', '美妆', '护肤', '化妆', '口红', '粉底', '面膜',
        '服装', '衣服', '裙子', '包包', '鞋子', '配饰', '珠宝', '首饰',
        '时装周', '品牌', '奢侈品', '大牌', '设计师', '模特', '街拍',
        '发型', '美甲', '香水', '防晒', '精华', '眼霜', '面霜',
        'vogue', 'elle', 'cosmo', 'bazaar', 'gq', 'fashion',
        '搭配', '风格', '潮流', '流行', '趋势',
        '明星同款', '网红', '博主', '种草', '拔草',
        '减肥', '瘦身', '健身', '瑜伽', '塑形',
        '婚礼', '婚纱', '新娘', '婚庆',
    ]
    
    BEAUTY_KEYWORDS = [
        '美业', '美容院', '美容师', '美发店', '美甲店', '美睫', '纹绣', '半永久',
        '护肤品牌', '护肤心得', '抗衰老', '祛斑', '祛痘印', '美白精华', '补水面膜',
        '医美项目', '整形手术', '微整形', '玻尿酸填充', '肉毒素', '热玛吉', '皮秒激光',
        '植发手术', '生发液', '脱发治疗', '染发剂', '烫发',
        'SPA会所', '精油按摩', '芳疗师', '身体护理',
        '丰胸产品', '瘦身产品', '减肥产品', '塑形衣', '体雕',
        '皮肤管理中心', '敏感肌护理', '油皮护肤', '干皮护肤',
        '整形医院', '皮肤科医生',
        '美业培训', '美业创业',
        '美容护肤', '美妆教程', '化妆技巧', '底妆', '眼妆', '唇妆',
        '粉底液', '遮瑕', '定妆', '修容', '高光', '腮红',
    ]
    
    CELEBRITY_KEYWORDS = [
        '明星', '艺人', '演员', '歌手', '偶像', '爱豆', 'idol',
        '八卦', '绯闻', '恋情曝光', '分手了', '结婚了', '离婚了', '出轨门',
        '恋情官宣', '恋情实锤', '官宣恋情',
        '红毯造型', '颁奖礼', '电影节红毯', '时装周', '品牌活动',
        '粉丝应援', '打榜', '控评', '反黑站',
        '磕cp', '嗑糖', '发糖', 'be了', 'he了',
        '塌房了', '翻车现场', '人设崩',
        '娱乐圈', '演艺圈', '影视圈', '音乐圈',
        '经纪人', '工作室', '解约', '合约纠纷',
        '名媛', '富二代', '豪门', '阔太', '贵妇',
        '网红', '博主', '主播', '达人', 'KOL',
        '恋情', '官宣', '结婚', '离婚',
    ]
    
    VARIETY_SHOW_KEYWORDS = [
        '综艺', '真人秀', '选秀', '比赛', '竞技',
        '奔跑吧', '极限挑战', '向往的生活', '快乐大本营', '天天向上',
        '王牌对王牌', '歌手', '中国好声音', '乘风破浪', '披荆斩棘',
        '密室大逃脱', '明星大侦探', '向往的生活', '爸爸去哪儿',
        '妻子的浪漫旅行', '幸福三重奏', '我家那闺女', '我家那小子',
        '吐槽大会', '脱口秀', '奇葩说', '辩论',
        '恋爱', '相亲', '约会', '心动', '告白',
        '综艺嘉宾', '常驻', '飞行嘉宾', 'mc', '主持人',
        '节目', '播出', '收官', '开播', '季终',
    ]
    
    MOVIE_KEYWORDS = [
        '电影', '影片', '大片', '票房', '上映', '首映',
        '导演', '编剧', '制片人', '演员', '主演', '配角',
        '剧情片', '喜剧片', '动作片', '科幻片', '恐怖片', '爱情片',
        '悬疑片', '犯罪片', '战争片', '历史片', '纪录片',
        '国产片', '进口片', '好莱坞', '华语片', '港片',
        '春节档', '暑期档', '国庆档', '贺岁档',
        '金像奖', '金马奖', '金鸡奖', '奥斯卡', '戛纳',
        '影评', '口碑', '豆瓣评分', '猫眼', '淘票票',
        '预告片', '海报', '剧照', '花絮', '幕后',
    ]
    
    DRAMA_KEYWORDS = [
        '电视剧', '剧集', '网剧', '热播剧', '追剧党',
        '韩剧推荐', '美剧推荐', '日剧推荐', '泰剧推荐', '英剧推荐',
        '古装剧', '现代剧', '都市剧', '偶像剧', '悬疑剧',
        '仙侠剧', '武侠剧', '历史剧', '年代剧', '家庭剧',
        '韩剧新剧', '韩剧更新', '欧巴', '欧尼', '韩流明星',
        '美剧新季', 'Netflix新剧', 'HBO新剧', 'Disney新剧',
        '日剧新番', '日本动漫', '动漫新番',
        '泰剧推荐', '腐剧', 'BL剧',
        '剧集更新', '大结局', '开播', '定档', '杀青',
        '收视率', '播放量', '剧集热度', '剧话题',
        '追剧', '剧荒', '好剧推荐', '必看剧',
    ]
    
    WESTERN_FASHION_KEYWORDS = [
        '欧美', '欧美风', '欧美穿搭', '欧美妆容',
        'streetwear', 'street style', 'high fashion',
        'london fashion', 'paris fashion', 'milan fashion', 'new york fashion',
        'runway', 'catwalk', 'lookbook', 'editorial',
        'celebrity style', 'red carpet', 'met gala', 'oscar',
        'chanel', 'dior', 'gucci', 'prada', 'lv', 'louis vuitton',
        'balenciaga', 'off-white', 'supreme', 'nike', 'adidas',
        'kardashian', 'jenner', 'hadid', 'bella', 'gigi',
        'influencer', 'fashion blogger', 'style icon',
        'vogue', 'harper', 'elle', 'cosmopolitan', 'instyle',
        '米兰时装周', '巴黎时装周', '伦敦时装周', '纽约时装周',
        '超模', '国际超模', '维密', 'victoria secret',
    ]

    REGENERATIVE_MEDICINE_KEYWORDS = [
        '再生医学', '细胞疗法', '干细胞治疗', '干细胞研究',
        '胚胎干细胞', '成体干细胞', '间充质干细胞', '造血干细胞',
        'IPS细胞', 'iPSC', '诱导多能干细胞', '细胞重编程',
        '基因编辑', 'CRISPR', '基因治疗', '基因疗法',
        'CAR-T', 'CAR-T细胞', '细胞免疫疗法', '免疫细胞治疗',
        '组织工程', '3D生物打印', '器官打印', '人工器官',
        '组织再生', '器官再生', '伤口愈合', '创伤修复',
        '皮肤再生', '软骨再生', '骨再生', '神经再生',
        '心肌修复', '心脏再生', '肝脏再生', '肾脏再生',
        '抗衰老', '延缓衰老', '衰老逆转', '端粒酶',
        '富血小板血浆', 'PRP疗法', '生长因子', '外泌体',
        '胎盘干细胞', '脐带血', '脐带干细胞', '羊膜干细胞',
        '骨髓移植', '造血干细胞移植', '干细胞移植',
        '生物工程', '生物支架', 'ECM', '细胞外基质',
        '转化医学', '精准医疗', '个性化治疗', '细胞银行',
        '临床试验', 'FDA批准', 'NMPA批准', '新药审批',
        '帕金森病', '阿尔茨海默', '糖尿病', '脊髓损伤',
        '退行性疾病', '自身免疫病', '癌症治疗', '肿瘤免疫',
    ]
    
    MUSIC_KEYWORDS = [
        '音乐', '歌曲', '专辑', '单曲', 'EP', 'MV', '音乐录影带',
        '演唱会', '音乐会', '音乐节', '巡演', 'live',
        '歌手', '唱作人', '音乐人', 'rapper', 'Rapper', '说唱',
        '乐队', '乐团', '组合', 'solo', 'solo歌手',
        '专辑发布', '新歌', '首发', '音源', '歌曲上线',
        '音乐榜单', '排行榜', 'Billboard', 'QQ音乐', '网易云音乐',
        '金曲奖', '格莱美', '奥斯卡提名', '音乐奖项',
        '热门歌曲', '神曲', '爆火', '刷屏', '热歌',
        '音乐综艺', '歌手', '中国好声音', '我是歌手', '歌手2024',
        '音乐节', '草莓音乐节', '迷笛', '拜拜音乐节',
        '流行音乐', '摇滚', '嘻哈', 'RAP', '民谣', '电子音乐', 'EDM',
        '作曲', '作词', '编曲', '制作人', '音乐制作',
        '音乐版权', '版权', '侵权', '抄袭',
    ]
    
    FOOD_KEYWORDS = [
        '美食', '餐厅', '食谱', '做菜', '烹饪', '厨艺',
        '网红餐厅', '必吃', '打卡', '探店', '美食推荐',
        '米其林', '黑珍珠', '餐厅评选', '美食榜单',
        '外卖', '团购', '美食优惠', '餐厅折扣',
        '家常菜', '私房菜', '特色菜', '招牌菜',
        '甜点', '蛋糕', '面包', '甜品', '奶茶', '咖啡',
        '小吃', '街头美食', '夜市', '美食街',
        '地方美食', '川菜', '粤菜', '湘菜', '鲁菜', '浙菜', '闽菜',
        '火锅', '烧烤', '自助餐', '日料', '韩餐', '西餐',
        '食材', '食材推荐', '食材购买', '生鲜', '有机食品',
        '健康饮食', '减脂餐', '轻食', '素食', '养生',
        '烘焙', '甜品制作', '奶茶配方', '咖啡拉花',
    ]
    
    TRAVEL_KEYWORDS = [
        '旅游', '旅行', '度假', '出游', '出行',
        '旅游景点', '景区', '景点', '打卡景点', '网红景点',
        '旅行攻略', '旅游指南', '自由行', '跟团游', '自驾游',
        '酒店', '民宿', '度假村', '住宿推荐', '酒店预订',
        '机票', '航班', '往返机票', '特价机票', '机票优惠',
        '签证', '护照', '入境', '出境', '免签', '落地签',
        '海岛', '海滩', '沙滩', '度假海岛', '岛屿',
        '雪山', '滑雪', '温泉', '泡汤', 'spa',
        '古镇', '古城', '小镇', '村落', '乡村旅游',
        '城市旅游', '都市游', '城市打卡', '地标',
        '出境游', '出国', '境外游', '海外旅游',
        '境内游', '国内游', '周边游', '短途游',
        '旅行装备', '行李', '背包', '旅行必备',
        '旅行博主', '旅游达人', '旅行Vlog', '旅行分享',
    ]
    
    ASTROLOGY_KEYWORDS = [
        '星座', '星象', '占星', '占卜', '运势',
        '十二星座', '白羊座', '金牛座', '双子座', '巨蟹座',
        '狮子座', '处女座', '天秤座', '天蝎座', '射手座', '摩羯座',
        '水瓶座', '双鱼座', '星座配对', '星座匹配',
        '星座运势', '今日运势', '本周运势', '月度运势', '年度运势',
        '水逆', '水星逆行', '行星逆行', '星座知识',
        '占星术', '星盘', '出生图', '行星位置',
        '太阳星座', '月亮星座', '上升星座', '星宿',
        '幸运色', '幸运数字', '幸运方位', '开运物品',
        '塔罗', '塔罗牌', ' Tarot', '占卜',
        '生肖', '属相', '属鼠', '属牛', '属虎', '属兔',
        '属龙', '属蛇', '属马', '属羊', '属猴', '属鸡', '属狗', '属猪',
        '血型', 'A型血', 'B型血', 'O型血', 'AB型血',
        '命理', '算命', '八字', '五行', '命理分析',
    ]

    CATEGORY_KEYWORDS = {
        'fashion': FASHION_KEYWORDS,
        'beauty': BEAUTY_KEYWORDS,
        'celebrity': CELEBRITY_KEYWORDS,
        'variety_show': VARIETY_SHOW_KEYWORDS,
        'movie': MOVIE_KEYWORDS,
        'drama': DRAMA_KEYWORDS,
        'western_fashion': WESTERN_FASHION_KEYWORDS,
        'regenerative_medicine': REGENERATIVE_MEDICINE_KEYWORDS,
        'music': MUSIC_KEYWORDS,
        'food': FOOD_KEYWORDS,
        'travel': TRAVEL_KEYWORDS,
        'astrology': ASTROLOGY_KEYWORDS,
    }
    
    def __init__(self):
        self.session = requests.Session()
        self._cache: Dict[str, any] = {}
        self._cache_lock = threading.Lock()
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh = threading.Event()
        self._cache_ttl = int(os.getenv("TRENDING_CACHE_TTL", 1800))
        self._initialized = False
        self._ensure_data_dir()
        self._load_persisted_cache()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.199 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.199 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.199 Safari/537.36 Edg/119.0.2151.97',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.160 Mobile Safari/537.36',
        ]
        
        self.accept_headers = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        ]
        
        self.accept_languages = [
            'zh-CN,zh;q=0.9,en;q=0.8',
            'zh-CN,zh;q=0.9',
            'zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4',
            'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        ]
        
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': random.choice(self.accept_headers),
            'Accept-Language': random.choice(self.accept_languages)
        })
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(TRENDING_DATA_DIR, exist_ok=True)
    
    def _load_persisted_cache(self):
        """从文件加载持久化的热搜缓存"""
        if os.path.exists(TRENDING_CACHE_FILE):
            try:
                with open(TRENDING_CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cached = data.get("trending_topics")
                    if cached:
                        self._cache['trending_topics'] = cached
                        logger.info(f"从持久化文件加载热搜缓存: fetch_time={cached.get('data', {}).get('fetch_time', 'unknown')}")
            except Exception as e:
                logger.warning(f"加载热搜持久化缓存失败: {e}")
    
    def _save_persisted_cache(self):
        """保存热搜缓存到文件"""
        try:
            cached = self._cache.get('trending_topics')
            if cached:
                data = {
                    "knowledge_type": "trending",
                    "updated_at": datetime.now().isoformat(),
                    "trending_topics": cached
                }
                with open(TRENDING_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.debug(f"热搜缓存已持久化: fetch_time={cached.get('data', {}).get('fetch_time', 'unknown')}")
        except Exception as e:
            logger.warning(f"保存热搜持久化缓存失败: {e}")
    
    def get_random_headers(self):
        """
        生成随机请求头，用于反爬虫
        """
        # 用户代理列表 - 更新为最新版本
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.109 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.109 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        ]
        
        # 随机选择一个用户代理
        user_agent = random.choice(user_agents)
        
        # 生成随机的Accept - 更新为更现代的格式
        accepts = [
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "application/json, text/plain, */*",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "application/xml,application/xhtml+xml,text/html;q=0.9, text/plain;q=0.8,image/png,image/webp,image/apng,*/*;q=0.5"
        ]
        accept = random.choice(accepts)
        
        # 生成随机的Accept-Language
        accept_languages = [
            "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "zh-CN,zh;q=0.9,en;q=0.8",
            "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
        ]
        accept_language = random.choice(accept_languages)
        
        # 生成随机的Accept-Encoding - 添加zstd等现代压缩算法
        accept_encodings = [
            "gzip, deflate, br, zstd",
            "gzip, deflate, br",
            "gzip, deflate",
            "deflate",
            "identity"
        ]
        accept_encoding = random.choice(accept_encodings)
        
        # 生成随机的Connection
        connections = [
            "keep-alive",
            "close"
        ]
        connection = random.choice(connections)
        
        # 生成随机的Cache-Control
        cache_controls = [
            "max-age=0",
            "no-cache",
            "no-store",
            "no-transform"  # 添加这个选项
        ]
        cache_control = random.choice(cache_controls)
        
        # 生成随机的DNT (Do Not Track)
        dnts = [
            "1",
            "0"
        ]
        dnt = random.choice(dnts)
        
        # 生成随机的Upgrade-Insecure-Requests
        upgrade_insecure_requests = random.choice(["1", "0"])
        
        # 生成随机的Sec-Fetch-Dest
        sec_fetch_dests = [
            "document",
            "empty",
            "frame",  # 添加frame选项
            "iframe"
        ]
        sec_fetch_dest = random.choice(sec_fetch_dests)
        
        # 生成随机的Sec-Fetch-Mode
        sec_fetch_modes = [
            "navigate",
            "cors",
            "no-cors",  # 添加no-cors选项
            "same-origin"
        ]
        sec_fetch_mode = random.choice(sec_fetch_modes)
        
        # 生成随机的Sec-Fetch-Site
        sec_fetch_sites = [
            "none",
            "same-site",
            "cross-site",
            "same-origin"
        ]
        sec_fetch_site = random.choice(sec_fetch_sites)
        
        # 生成随机的Sec-Fetch-User
        sec_fetch_users = [
            "?1",
            "?0"
        ]
        sec_fetch_user = random.choice(sec_fetch_users)
        
        # 生成随机的Sec-Ch-Ua - 更新为最新版本
        sec_ch_uas = [
            '"Google Chrome";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
            '"Not_A Brand";v="24", "Chromium";v="120", "Google Chrome";v="120"',
            '"Opera";v="106", "Chromium";v="120", "Not?A_Brand";v="24"'
        ]
        sec_ch_ua = random.choice(sec_ch_uas)
        
        # 生成随机的Sec-Ch-Ua-Mobile
        sec_ch_ua_mobiles = [
            "?0",
            "?1"
        ]
        sec_ch_ua_mobile = random.choice(sec_ch_ua_mobiles)
        
        # 生成随机的Sec-Ch-Ua-Platform
        sec_ch_ua_platforms = [
            '"Windows"',
            '"macOS"',
            '"Linux"',
            '"Android"',
            '"iOS"'
        ]
        sec_ch_ua_platform = random.choice(sec_ch_ua_platforms)
        
        # 生成随机的Priority
        priorities = [
            "u=0, i",
            "u=1, i",
            "u=2, i"
        ]
        priority = random.choice(priorities)
        
        # 构建请求头
        headers = {
            'User-Agent': user_agent,
            'Accept': accept,
            'Accept-Language': accept_language,
            'Accept-Encoding': accept_encoding,
            'Connection': connection,
            'Upgrade-Insecure-Requests': upgrade_insecure_requests,
            'Sec-Fetch-Dest': sec_fetch_dest,
            'Sec-Fetch-Mode': sec_fetch_mode,
            'Sec-Fetch-Site': sec_fetch_site,
            'Sec-Fetch-User': sec_fetch_user,
            'Cache-Control': cache_control,
            'DNT': dnt,
            'Sec-Ch-Ua': sec_ch_ua,
            'Sec-Ch-Ua-Mobile': sec_ch_ua_mobile,
            'Sec-Ch-Ua-Platform': sec_ch_ua_platform,
            'Priority': priority,  # 添加Priority头部
        }
        
        # 随机添加一些额外的头部
        if random.random() > 0.5:
            headers['Referer'] = random.choice([
                "https://www.google.com/",
                "https://www.baidu.com/",
                "https://www.bing.com/",
                "https://www.yahoo.com/",
                "https://www.sogou.com/",
                "https://www.duckduckgo.com/",  # 添加duckduckgo
                "https://www.ecosia.org/"       # 添加ecosia
            ])
        
        if random.random() > 0.7:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        
        if random.random() > 0.6:
            headers['X-Forwarded-For'] = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        if random.random() > 0.6:
            headers['X-Real-IP'] = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        # 随机添加TE头部
        if random.random() > 0.7:
            headers['TE'] = 'trailers'
        
        return headers
        
    def get_all_trending_topics(self, prefer_method: str = 'auto', include_fashion: bool = True) -> Dict[str, any]:
        """
        获取所有平台的热搜信息
        
        三级降级机制：
        1. 免费API - 最快最稳定
        2. 浏览器自动化 - 能处理动态加载页面
        3. requests - 降级方案
        
        Args:
            prefer_method: 首选方法
                'auto' - 自动选择（默认，优先免费API）
                'free_api' - 仅使用免费API
                'browser' - 仅使用浏览器自动化
                'requests' - 仅使用 requests
            include_fashion: 是否包含时尚门户数据（默认 True）
        """
        result = self._get_empty_result('fallback')
        
        if prefer_method == 'free_api':
            try:
                result = self._fetch_via_free_api()
            except Exception as e:
                logger.warning(f"免费API获取失败：{e}")
                result = self._get_empty_result('free_api')
        elif prefer_method == 'browser':
            try:
                result = self._fetch_via_browser()
            except Exception as e:
                logger.warning(f"浏览器自动化获取失败：{e}")
                result = self._fetch_via_requests()
        elif prefer_method == 'requests':
            try:
                result = self._fetch_via_requests()
            except Exception as e:
                logger.warning(f"requests 获取失败：{e}")
                result = self._get_empty_result('requests')
        else:
            success = False
            
            try:
                logger.info("使用免费API获取热搜...")
                result = self._fetch_via_free_api()
                total = sum(len(result.get(k, [])) for k in self.UAPIS_PLATFORMS.keys())
                if total > 50:
                    logger.info(f"免费API获取热搜成功，总计: {total} 条数据")
                    success = True
                else:
                    logger.warning(f"免费API获取数据不足: {total}条")
            except Exception as e:
                logger.warning(f"免费API获取失败：{e}")
            
            # 不再使用浏览器自动化（包含微博抓取，需要登录）
            # 不再使用requests备用方案（也包含微博）
            if not success:
                logger.warning("免费API获取失败，跳过微博等需要登录的热搜源")
                result = self._get_empty_result('api_failed')
        
        # 获取时尚数据
        if include_fashion and fashion_portal_service:
            try:
                logger.info("获取时尚门户数据...")
                fashion_result = None
                exception_occurred = None
                
                def fetch_fashion():
                    nonlocal fashion_result, exception_occurred
                    try:
                        fashion_result = fashion_portal_service.get_fashion_news()
                    except Exception as e:
                        exception_occurred = e
                
                thread = threading.Thread(target=fetch_fashion)
                thread.daemon = True
                thread.start()
                thread.join(timeout=35)
                
                if thread.is_alive():
                    logger.warning("时尚门户数据获取超时")
                    result['fashion_news'] = []
                elif exception_occurred:
                    logger.warning(f"获取时尚门户数据异常：{exception_occurred}")
                    result['fashion_news'] = []
                elif fashion_result and fashion_result.get('success'):
                    result['fashion_news'] = fashion_result.get('fashion_news', [])
                    logger.info(f"时尚门户数据获取成功：{len(result['fashion_news'])}条")
                else:
                    result['fashion_news'] = []
            except Exception as e:
                logger.warning(f"获取时尚门户数据失败：{e}")
                result['fashion_news'] = []
        else:
            result['fashion_news'] = []
        
        return result
    
    def _fetch_via_free_api(self) -> Dict[str, any]:
        """使用免费API获取热搜（主要方法）"""
        trending_data = {
            'baidu_hot': [],
            'zhihu_hot': [],
            'douyin_hot': [],
            'fashion_trends': [],
            'beauty_trends': [],
            'celebrity_trends': [],
            'variety_show_trends': [],
            'movie_trends': [],
            'drama_trends': [],
            'western_fashion_trends': [],
            'regenerative_medicine_trends': [],
            'music_trends': [],
            'food_trends': [],
            'travel_trends': [],
            'astrology_trends': [],
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
            'tieba': [],
            'kuaishou': [],
            'sina': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': True,
            'method': 'free_api'
        }
        
        for key, platform in self.UAPIS_PLATFORMS.items():
            try:
                resp = self.session.get(
                    f"{self.UAPIS_BASE_URL}?type={platform}",
                    timeout=10
                )
                data = resp.json()
                
                if 'list' in data and isinstance(data.get('list'), list):
                    items = []
                    for item in data['list'][:30]:
                        if isinstance(item, dict):
                            items.append({
                                'rank': len(items) + 1,
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'hot': item.get('hot', ''),
                                'platform': platform
                            })
                    trending_data[key] = items
                    logger.info(f"{platform} 获取成功: {len(items)}条")
            except Exception as e:
                logger.warning(f"获取 {platform} 失败: {e}")
        
        if sum(len(trending_data[k]) for k in self.UAPIS_PLATFORMS.keys()) == 0:
            logger.warning("uapis.cn 所有平台获取失败，尝试备用数据源...")
            self._fetch_fallback_sources(trending_data)
        
        source_keys = ['weibo_hot', 'zhihu_hot', 'douyin_hot', 'bilibili', 'douban', 'douban', 'toutiao_hot', 'sina']
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            category_items = []
            for key in source_keys:
                for item in trending_data.get(key, []):
                    title = item.get('title', '').lower()
                    if any(kw in title for kw in keywords):
                        category_items.append({
                            **item,
                            'category': category,
                            'source': key
                        })
            
            category_key = f'{category}_trends'
            trending_data[category_key] = category_items[:30]
            if category_items:
                logger.info(f"从热搜中筛选出 {len(category_items)} 条 {category} 相关话题")
        
        total = sum(len(trending_data[k]) for k in self.UAPIS_PLATFORMS.keys())
        trending_data['success'] = total > 0
        
        return trending_data
    
    def _fetch_via_browser(self) -> Dict[str, any]:
        """使用浏览器自动化获取热搜"""
        if PLAYWRIGHT_AVAILABLE and browser_trending_service:
            return browser_trending_service.get_all_trending_topics()
        return self._get_empty_result('browser')
    
    def _fetch_fallback_sources(self, trending_data: Dict[str, any]):
        """备用数据源 - 当主数据源失效时使用"""
        fallback_sources = [
            ('baidu_hot', 'https://top.baidu.com/board?tab=realtime'),
            ('weibo_hot', 'https://weibo.com/ajax/statuses/mymblog'),
        ]
        
        for key, url in fallback_sources:
            try:
                resp = self.session.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if 'list' in resp.json():
                    data = resp.json()['list']
                    items = []
                    for i, item in enumerate(data[:20], 1):
                        items.append({
                            'rank': i,
                            'title': item.get('word', item.get('title', '')),
                            'url': item.get('url', ''),
                            'hot': item.get('hotScore', ''),
                            'platform': key
                        })
                    trending_data[key] = items
                    logger.info(f"备用数据源 {key} 获取成功: {len(items)}条")
            except Exception as e:
                logger.warning(f"备用数据源 {key} 获取失败: {e}")
    
    def _fetch_via_requests(self) -> Dict[str, any]:
        """使用 requests 获取热搜（备用方案，优先使用API）"""
        trending_data = {
            'baidu_hot': [],
            'zhihu_hot': [],
            'douyin_hot': [],
            'fashion_trends': [],
            'beauty_trends': [],
            'celebrity_trends': [],
            'variety_show_trends': [],
            'movie_trends': [],
            'drama_trends': [],
            'western_fashion_trends': [],
            'regenerative_medicine_trends': [],
            'music_trends': [],
            'food_trends': [],
            'travel_trends': [],
            'astrology_trends': [],
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
            'method': 'requests'
        }

        try:
            # 优先尝试免费API（更稳定可靠）
            api_result = self._fetch_via_free_api()
            if api_result.get('success'):
                trending_data = api_result
                trending_data['method'] = 'free_api_fallback'
            else:
                # API也失败时才尝试网页抓取（但跳过微博）
                trending_data['baidu_hot'] = self._get_baidu_hot_search()
                trending_data['xiaohongshu_hot'] = self._get_xiaohongshu_hot_search()
                # 微博直接返回空，不尝试抓取（需要登录）
                trending_data['weibo_hot'] = []
                logger.info("微博热搜跳过（需要登录），仅获取百度和小红书")
        except Exception as e:
            logger.error(f"获取热搜信息失败: {e}")
            trending_data['success'] = False

        return trending_data
    
    def _get_empty_result(self, method: str) -> Dict[str, any]:
        """返回空结果"""
        return {
            'baidu_hot': [],
            'zhihu_hot': [],
            'douyin_hot': [],
            'fashion_trends': [],
            'beauty_trends': [],
            'celebrity_trends': [],
            'variety_show_trends': [],
            'movie_trends': [],
            'drama_trends': [],
            'western_fashion_trends': [],
            'regenerative_medicine_trends': [],
            'music_trends': [],
            'food_trends': [],
            'travel_trends': [],
            'astrology_trends': [],
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
            'douban_group': [],
            'huxiu': [],
            'ifanr': [],
            'sspai': [],
            'ithome': [],
            'juejin': [],
            'jianshu': [],
            'guokr': [],
            'smzdm': [],
            'coolapk': [],
            'v2ex': [],
            'tieba': [],
            'kuaishou': [],
            'sina': [],
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
            'method': method
        }
    
    def _get_weibo_hot_search(self) -> List[Dict[str, str]]:
        """
        获取微博热搜（通过网页抓取）
        注意：由于微博需要登录才能访问热搜，此功能已被禁用
        """
        logger.info("微博热搜获取功能已被禁用，返回空列表")
        return []
    
    def _get_mock_weibo_hot_search(self) -> List[Dict[str, str]]:
        """
        当获取微博热搜失败时，返回空列表（不返回假数据）
        """
        logger.info("微博热搜获取失败，返回空列表")
        return []
    
    def _get_mock_baidu_hot_search(self) -> List[Dict[str, str]]:
        """
        当获取百度热搜失败时，返回空列表（不返回假数据）
        """
        logger.info("百度热搜获取失败，返回空列表")
        return []
    
    def _get_baidu_hot_search(self) -> List[Dict[str, str]]:
        """
        获取百度热搜（通过网页抓取）
        """
        try:
            url = "http://top.baidu.com/buzz?b=1&fr=topindex"
            
            # 使用随机请求头
            headers = self.get_random_headers()

            # 添加会话级别的随机延迟，模拟人类行为
            time.sleep(random.uniform(2, 5))

            # 设置更长的超时时间
            response = self.session.get(url, headers=headers, timeout=15)
            response.encoding = 'gbk'  # 百度使用GBK编码
            
            # 检查响应状态
            if response.status_code != 200:
                logger.warning(f"获取百度热搜失败，状态码: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hot_list = []
            # 尝试多种选择器策略
            selectors = [
                # 百度热搜的主要选择器
                'a[list-title]',
                'a[class*="list-title"]',
                'a[href*="/detail"]',
                '[class*="keyword"] a',
                '[class*="link"] a',
                '[class*="title"] a',
                '.c-single-text',
                '.c-block-a',
                'a[target="_blank"]',
                'a'
            ]
            
            seen_titles = set()
            rank = 1
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    logger.debug(f"百度热搜使用选择器 '{selector}' 找到 {len(items)} 个元素")
                    
                    for link in items:
                        title = link.get_text().strip()
                        href = link.get('href', '')
                        
                        # 清理标题
                        title = re.sub(r'\s+', ' ', title).strip()
                        
                        if (title and len(title) > 2 and len(title) < 50 and 
                            not href.startswith('#') and 'javascript:' not in href and
                            title not in seen_titles):
                            
                            # 过滤无效标题
                            invalid_keywords = ['百度', '热搜', '榜单', '更多', '展开', '收起', '广告', '推广', '登录', '注册']
                            if any(keyword in title for keyword in invalid_keywords):
                                continue
                            
                            seen_titles.add(title)
                            
                            if rank <= 10:  # 只取前10个
                                hot_list.append({
                                    'rank': rank,
                                    'title': title,
                                    'url': href if href.startswith('http') else 'https://www.baidu.com' + href,
                                    'platform': 'baidu'
                                })
                                rank += 1
                            else:
                                break
                
                if len(hot_list) >= 5:  # 如果已经找到足够多的数据，就停止
                    break
            
            # 如果上面方法不行，尝试从script标签中提取数据
            if len(hot_list) < 3:
                hot_list = []
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        # 尝试从JS中提取热搜数据
                        # 这里可以添加更复杂的JS解析逻辑
                        pass
            
            return hot_list[:10]  # 只返回前10个
            
        except Exception as e:
            logger.warning(f"获取百度热搜失败: {e}")
            return []
    
    def _get_xiaohongshu_hot_search(self) -> List[Dict[str, str]]:
        """
        获取小红书热搜（通过网页抓取）
        """
        try:
            url = "https://www.xiaohongshu.com/explore"
            
            # 使用随机请求头
            headers = self.get_random_headers()
            
            # 添加会话级别的随机延迟，模拟人类行为
            time.sleep(random.uniform(2, 5))
            
            # 设置更长的超时时间
            response = self.session.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            # 检查响应状态
            if response.status_code != 200:
                logger.warning(f"获取小红书热搜失败，状态码: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            hot_list = []
            # 尝试多种选择器策略
            selectors = [
                '[data-component*="note"] a',
                '[class*="explore-item"] a',
                '[class*="note"] a',
                '[class*="tag"] a',
                '[class*="title"] a',
                'a[href*="/note/"]',
                'a[href*="/tag/"]',
                'a'
            ]
            
            seen_titles = set()
            rank = 1
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    logger.debug(f"小红书使用选择器 '{selector}' 找到 {len(items)} 个元素")
                    
                    for link in items:
                        title = link.get_text().strip()
                        href = link.get('href', '')
                        
                        # 清理标题
                        title = re.sub(r'\s+', ' ', title).strip()
                        
                        if (title and len(title) > 2 and len(title) < 50 and 
                            not href.startswith('#') and 'javascript:' not in href and
                            title not in seen_titles):
                            
                            # 过滤无效标题
                            invalid_keywords = ['小红书', '推荐', '热门', '更多', '展开', '收起', '广告', '推广', '登录', '注册']
                            if any(keyword in title for keyword in invalid_keywords):
                                continue
                            
                            seen_titles.add(title)
                            
                            if rank <= 10:  # 只取前10个
                                hot_list.append({
                                    'rank': rank,
                                    'title': title,
                                    'url': href if href.startswith('http') else 'https://www.xiaohongshu.com' + href,
                                    'platform': 'xiaohongshu'
                                })
                                rank += 1
                            else:
                                break
                
                if len(hot_list) >= 3:  # 如果已经找到足够多的数据，就停止
                    break
            
            return hot_list[:10]  # 只返回前10个
            
        except Exception as e:
            logger.warning(f"获取小红书热搜失败: {e}")
            return []
    
    def get_fashion_beauty_trends(self) -> List[Dict[str, str]]:
        """
        获取时尚美妆相关的热搜（过滤出与时尚、美妆、护肤相关的话题）
        """
        all_trends = self.get_all_trending_topics()
        
        fashion_beauty_keywords = [
            '美妆', '护肤', '口红', '面膜', '精华', '面霜', '防晒', '粉底',
            '眼影', '睫毛膏', '唇膏', '化妆', '卸妆', '洁面', '爽肤水',
            '乳液', '眼霜', '精华液', '面油', '护肤', '美容', '保养',
            '时尚', '穿搭', '发型', '造型', '潮流', '流行', '风格',
            '衣服', '服装', '鞋子', '包包', '首饰', '配饰', '美甲',
            '美发', '染发', '烫发', '护发', '洗发水', '护发素', '香水',
            'vogue', '时尚芭莎', 'elle', '世界时装之苑', '智族gq', 'gq'
        ]
        
        fashion_beauty_trends = []
        
        # 检查所有平台的热搜
        for platform, trends in [('baidu', all_trends['baidu_hot']), 
                                 ('xiaohongshu', all_trends['xiaohongshu_hot'])]:
            for trend in trends:
                title = trend.get('title', '').lower()
                # 检查是否包含时尚美妆关键词
                for keyword in fashion_beauty_keywords:
                    if keyword in title:
                        trend_copy = trend.copy()
                        trend_copy['related_to'] = 'fashion_beauty'
                        fashion_beauty_trends.append(trend_copy)
                        break  # 找到匹配的关键词后跳出内层循环
        
        return fashion_beauty_trends
    
    def warmup(self) -> bool:
        """
        预热服务，启动时立即获取热搜数据
        """
        if self._initialized:
            logger.info("热搜话题服务已预热，跳过")
            return True
        
        logger.info("正在预热热搜话题服务...")
        try:
            data = self.get_all_trending_topics()
            with self._cache_lock:
                self._cache['trending_topics'] = {
                    'data': data,
                    'timestamp': time.time()
                }
            self._save_persisted_cache()
            self._initialized = True
            logger.info(f"热搜话题服务预热完成: 微博{len(data['weibo_hot'])}条, 百度{len(data['baidu_hot'])}条")
            return True
        except Exception as e:
            logger.warning(f"热搜话题服务预热失败: {e}")
            return False
    
    def start_background_refresh(self):
        """
        启动后台定时刷新线程
        """
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.info("热搜后台刷新线程已在运行")
            return
        
        self._stop_refresh.clear()
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("热搜后台刷新线程已启动")
    
    def stop_background_refresh(self):
        """
        停止后台刷新线程
        """
        if self._refresh_thread:
            self._stop_refresh.set()
            self._refresh_thread.join(timeout=5)
            logger.info("热搜后台刷新线程已停止")
    
    def _refresh_loop(self):
        """
        后台刷新循环
        """
        while not self._stop_refresh.is_set():
            self._stop_refresh.wait(timeout=self._cache_ttl)
            if self._stop_refresh.is_set():
                break
            try:
                logger.debug("后台刷新热搜数据...")
                data = self.get_all_trending_topics()
                with self._cache_lock:
                    self._cache['trending_topics'] = {
                        'data': data,
                        'timestamp': time.time()
                    }
                self._save_persisted_cache()
                logger.debug("热搜数据后台刷新完成")
            except Exception as e:
                logger.warning(f"后台刷新热搜数据失败: {e}")
    
    def get_cached_trending_topics(self) -> Dict[str, any]:
        """
        获取缓存的热搜数据，只返回缓存，不实时刷新（无锁，极速返回）
        """
        cached = self._cache.get('trending_topics')
        if cached:
            # 检查缓存是否过期
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['data']
            else:
                # 缓存过期，返回空数据，但触发后台刷新
                logger.debug("热搜缓存已过期，返回空数据并触发后台刷新")
                # 在后台刷新数据，不阻塞当前请求
                threading.Thread(target=self._refresh_cache_async, daemon=True).start()
                return cached['data']  # 返回过期数据以避免阻塞，同时后台刷新
        
        # 没有缓存，返回空（不会重新爬取！）
        return {
            "baidu_hot": [],
            "xiaohongshu_hot": [],
            "combined_context": "暂无热搜信息",
            "success": False
        }
    
    def _refresh_cache_async(self):
        """
        异步刷新缓存，不阻塞主线程
        """
        try:
            logger.debug("开始异步刷新热搜缓存...")
            data = self.get_all_trending_topics()
            with self._cache_lock:
                self._cache['trending_topics'] = {
                    'data': data,
                    'timestamp': time.time()
                }
            self._save_persisted_cache()
            logger.debug("异步刷新热搜缓存完成")
        except Exception as e:
            logger.warning(f"异步刷新热搜缓存失败: {e}")


trending_topics_service = TrendingTopicsService()