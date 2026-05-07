# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
产品知识库去重和补充脚本
"""
import asyncio
import httpx
import json
import os
import dotenv

dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "LLM_API.env"))

API_KEY = os.getenv("ALIYUN_API_KEY")
API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

async def call_llm(prompt, max_tokens=8000):
    """调用LLM"""
    url = f"{API_BASE}/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url, json=data, headers=headers)
        result = resp.json()
        return result["choices"][0]["message"]["content"]

def parse_json(content):
    try:
        start = content.find("[")
        return json.loads(content[start:])
    except:
        return None

def deduplicate_products(products):
    """去重产品"""
    seen = set()
    unique = []
    
    for p in products:
        # 用品牌+名称作为唯一键
        key = (p.get("brand", ""), p.get("name", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    
    return unique

def normalize_brand_groups(products):
    """标准化集团名称"""
    group_mapping = {
        "LVMH": "LVMH集团",
        "LVMH集团": "LVMH集团",
        "Estée Lauder Companies": "雅诗兰黛集团",
        "雅诗兰黛集团": "雅诗兰黛集团",
        "欧莱雅集团": "欧莱雅集团",
        "花王集团": "花王集团",
        "联合利华集团": "联合利华集团",
        "FanCL集团": "FANCL集团",
        "Fancl集团": "FANCL集团",
        "高丝集团": "高丝集团",
        "佳丽宝集团": "佳丽宝集团",
    }
    
    brand_canonical = {
        "芭比波朗彩妆": "芭比波朗",  # 统一品牌名
        "芭比布朗": "芭比波朗",
    }
    
    for p in products:
        # 标准化集团
        old_group = p.get("group", "")
        p["group"] = group_mapping.get(old_group, old_group)
        
        # 标准化品牌
        old_brand = p.get("brand", "")
        p["brand"] = brand_canonical.get(old_brand, old_brand)
    
    return products

async def add_yuanxin_products(products):
    """补充远想集团产品"""
    prompt = """
你是美妆顾问。请为远想集团（远信集团）生成产品：
品牌：丽芙莎、伊肤泉、OMICY、瑞恩诗

每个品牌4个热门产品，共16个左右。

JSON：[{"group":"远想集团","brand":"品牌名","name":"产品名","price":整数,"category":"类别","efficacy":"功效","applicable_skin":"肤质","capacity":"规格","description":"描述","tags":["标签"]}]
只输出JSON数组。
"""
    
    print("生成远想集团产品...")
    content = await call_llm(prompt)
    new_products = parse_json(content)
    
    if new_products:
        products.extend(new_products)
        print(f"  添加了 {len(new_products)} 个远想产品")
    else:
        print("  生成失败")
    
    return products

async def main():
    print("="*50)
    print("产品知识库处理...")
    print("="*50)
    
    # 读取现有产品
    filepath = os.path.join(PROJECT_ROOT, "import_data", "llm_products.json")
    with open(filepath, "r", encoding="utf-8") as f:
        products = json.load(f)
    print(f"原始产品数: {len(products)}")
    
    # 1. 标准化
    products = normalize_brand_groups(products)
    print("已标准化集团和品牌名")
    
    # 2. 去重
    before = len(products)
    products = deduplicate_products(products)
    after = len(products)
    print(f"去重: {before} -> {after} (删除了 {before-after} 个)")
    
    # 3. 补充远想集团产品
    products = await add_yuanxin_products(products)
    
    # 统计
    groups = set(p.get("group", "") for p in products)
    brands = set(p.get("brand", "") for p in products)
    print(f"\n最终统计:")
    print(f"  产品数: {len(products)}")
    print(f"  集团数: {len(groups)}")
    print(f"  品牌数: {len(brands)}")
    
    # 保存
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到: {filepath}")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
