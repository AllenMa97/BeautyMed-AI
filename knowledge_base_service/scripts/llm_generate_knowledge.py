# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
使用httpx直接调用DashScope API生成知识 - 简化版
分多批次，每次只生成少量内容
"""
import asyncio
import json
import os
import sys
import httpx
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import dotenv
dotenv.load_dotenv(os.path.join(project_root, "config", "LLM_API.env"))

API_KEY = os.getenv("ALIYUN_API_KEY", "sk-614f2e32ce44483892c6fd2ce494d4ac")
API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

MAX_TOKENS = 15000
MAX_RETRIES = 3

async def call_dashscope(prompt, system_prompt="", max_tokens=MAX_TOKENS):
    """调用DashScope API"""
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens
    }
    
    for retry in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    print(f"  错误 {response.status_code}: {response.text[:100]}")
                    if retry < MAX_RETRIES - 1:
                        await asyncio.sleep(2 * (retry + 1))
        except Exception as e:
            print(f"  异常: {e}")
            if retry < MAX_RETRIES - 1:
                await asyncio.sleep(2 * (retry + 1))
    
    return None

def parse_json_array(content):
    if not content:
        return None
    try:
        if '[' in content:
            start = content.find('[')
            json_str = content[start:]
            bracket_count = 0
            for i, c in enumerate(json_str):
                if c == '[':
                    bracket_count += 1
                elif c == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        json_str = json_str[:i+1]
                        break
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
    return None

async def generate_products_simple(groups):
    """简化版产品生成 - 每个集团只问一次，返回多个产品"""
    
    prompt = f"""
你是一个专业的美妆行业顾问。

请为以下集团生成产品信息：{', '.join(groups)}

要求：
- 每个集团3个品牌，每个品牌3个产品
- 总共约{len(groups) * 9}个产品
- 产品要真实、热门

JSON格式：
[{{"group":"集团名","brand":"品牌名","name":"产品名","price":整数,"category":"类别","efficacy":"功效","applicable_skin":"适用肤质","capacity":"规格","description":"描述","tags":["标签"]}}]

只输出JSON数组。
"""
    
    print(f"  生成 {len(groups)} 个集团的产品...")
    content = await call_dashscope(prompt, "你是美妆顾问", 15000)
    return parse_json_array(content)

async def generate_medical_simple(topic):
    """简化版医美知识生成"""
    
    prompt = f"""
你是一个资深的医疗美容医生。

请生成关于以下主题的专业医美知识：{topic}

要求：生成15条专业知识

JSON格式：
[{{"category":"分类","title":"标题","content":"详细内容（包含原因、诊断、治疗、护理等）","references":["参考1"],"tags":["标签"]}}]

内容要专业准确，治疗方法要详细。
只输出JSON数组。
"""
    
    print(f"  生成医美知识: {topic[:30]}...")
    content = await call_dashscope(prompt, "你是医疗美容专家", 15000)
    return parse_json_array(content)

async def main():
    print("="*60)
    print("开始生成知识库...")
    print("="*60)
    
    all_products = []
    
    # 产品 - 分3批
    product_batches = [
        ["欧莱雅集团", "雅诗兰黛集团", "资生堂集团", "LVMH集团"],
        ["爱茉莉太平洋集团", "LG生活健康集团", "宝洁集团", "联合利华集团"],
        ["华熙生物集团", "巨子生物集团", "敷尔佳集团", "远想集团"],
    ]
    
    for i, groups in enumerate(product_batches):
        print(f"\n📦 产品批次 {i+1}/{len(product_batches)}: {groups}")
        products = await generate_products_simple(groups)
        
        if products:
            all_products.extend(products)
            print(f"  ✅ 获得 {len(products)} 个产品")
        else:
            print(f"  ❌ 失败")
    
    # 保存产品
    if all_products:
        groups = set(p.get("group") for p in all_products if p.get("group"))
        brands = set(p.get("brand") for p in all_products if p.get("brand"))
        print(f"\n📊 产品统计: 总数={len(all_products)}, 集团={len(groups)}, 品牌={len(brands)}")
        
        output_file = os.path.join(project_root, "import_data", "llm_products.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        print(f"   已保存到: {output_file}")
    
    print("\n" + "="*60)
    
    all_medical = []
    
    # 医美 - 分4批
    medical_topics = [
        "色斑：黄褐斑、雀斑、老年斑、太田痣、咖啡斑",
        "色素沉着：炎症后色素沉着、激光后色素沉着",
        "痤疮：青春痘、成人痘、囊肿型痤疮",
        "激光治疗：调Q激光、皮秒激光、光子嫩肤、点阵激光"
    ]
    
    for i, topic in enumerate(medical_topics):
        print(f"\n🏥 医美批次 {i+1}/{len(medical_topics)}")
        knowledge = await generate_medical_simple(topic)
        
        if knowledge:
            all_medical.extend(knowledge)
            print(f"  ✅ 获得 {len(knowledge)} 条")
        else:
            print(f"  ❌ 失败")
    
    # 保存医美
    if all_medical:
        print(f"\n📊 医美统计: 总数={len(all_medical)}")
        
        output_file = os.path.join(project_root, "import_data", "llm_medical_knowledge.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_medical, f, ensure_ascii=False, indent=2)
        print(f"   已保存到: {output_file}")
    
    print("\n" + "="*60)
    print("✅ 完成!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
