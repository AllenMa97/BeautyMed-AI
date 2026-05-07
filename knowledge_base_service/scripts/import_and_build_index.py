# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
将新生成的知识导入存储并构建ANN索引
"""
import asyncio
import json
import os
import sys
import dotenv
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

dotenv.load_dotenv(os.path.join(PROJECT_ROOT, "config", "LLM_API.env"))

class DataImporter:
    def __init__(self):
        self.storage_dir = os.path.join(PROJECT_ROOT, "knowledge_storage")
        self.contents_dir = os.path.join(self.storage_dir, "contents")
        self.embeddings_dir = os.path.join(self.storage_dir, "embeddings")
        
        os.makedirs(self.contents_dir, exist_ok=True)
        os.makedirs(self.embeddings_dir, exist_ok=True)
    
    def load_products(self):
        with open(os.path.join(PROJECT_ROOT, "import_data", "llm_products.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_medical(self):
        with open(os.path.join(PROJECT_ROOT, "import_data", "llm_medical_knowledge.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_product_embeddings(self):
        with open(os.path.join(PROJECT_ROOT, "embeddings", "products_embeddings.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_medical_embeddings(self):
        with open(os.path.join(PROJECT_ROOT, "embeddings", "medical_embeddings.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    
    def import_products(self, products, embeddings):
        """导入产品数据"""
        print("\n导入产品数据...")
        
        # 加载现有索引（V2格式）
        index_file = os.path.join(self.storage_dir, "knowledge_index.json")
        if os.path.exists(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        else:
            index_data = {"version": "2.0", "statistics": {}, "last_updated": None}
        
        imported = 0
        skipped = 0
        
        for i, product in enumerate(products):
            key = f"product_{i}"
            if key not in embeddings:
                skipped += 1
                continue
            
            content = {
                "id": key,
                "type": "product",
                "group": product.get("group", ""),
                "brand": product.get("brand", ""),
                "name": product.get("name", ""),
                "category": product.get("category", ""),
                "efficacy": product.get("efficacy", ""),
                "applicable_skin": product.get("applicable_skin", ""),
                "capacity": product.get("capacity", ""),
                "reference_price": product.get("reference_price", 0),
                "description": product.get("description", ""),
                "tags": product.get("tags", []),
                "text": embeddings[key]["text"]
            }
            
            # 保存内容
            content_file = os.path.join(self.contents_dir, f"{key}.json")
            with open(content_file, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False)
            
            # 保存embedding
            emb_file = os.path.join(self.embeddings_dir, f"{key}.json")
            with open(emb_file, "w", encoding="utf-8") as f:
                json.dump({"id": key, "embedding": embeddings[key]["embedding"]}, f)
            
            imported += 1
        
        # 更新统计
        if "statistics" not in index_data:
            index_data["statistics"] = {}
        
        old_count = index_data["statistics"].get("total_products", 0)
        index_data["statistics"]["total_products"] = old_count + imported
        index_data["last_updated"] = datetime.now().isoformat()
        
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"  导入: {imported}, 跳过: {skipped}")
        return imported
    
    def import_medical(self, medical_data, embeddings):
        """导入医美知识"""
        print("\n导入医美知识...")
        
        # 加载现有索引
        index_file = os.path.join(self.storage_dir, "knowledge_index.json")
        if os.path.exists(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        else:
            index_data = {"version": "2.0", "statistics": {}, "last_updated": None}
        
        imported = 0
        skipped = 0
        
        for i, item in enumerate(medical_data):
            key = f"medical_{i}"
            if key not in embeddings:
                skipped += 1
                continue
            
            content = {
                "id": key,
                "type": "entry",
                "category": item.get("category", ""),
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "references": item.get("references", []),
                "tags": item.get("tags", []),
                "text": embeddings[key]["text"]
            }
            
            # 保存内容
            content_file = os.path.join(self.contents_dir, f"{key}.json")
            with open(content_file, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False)
            
            # 保存embedding
            emb_file = os.path.join(self.embeddings_dir, f"{key}.json")
            with open(emb_file, "w", encoding="utf-8") as f:
                json.dump({"id": key, "embedding": embeddings[key]["embedding"]}, f)
            
            imported += 1
        
        # 更新统计
        if "statistics" not in index_data:
            index_data["statistics"] = {}
        
        old_count = index_data["statistics"].get("total_entries", 0)
        index_data["statistics"]["total_entries"] = old_count + imported
        index_data["last_updated"] = datetime.now().isoformat()
        
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"  导入: {imported}, 跳过: {skipped}")
        return imported

async def build_ann_index():
    """构建ANN索引"""
    print("\n" + "="*50)
    print("构建ANN索引...")
    print("="*50)
    
    from knowledge_base_service.core.index.index_builder import get_index_builder
    
    index_builder = get_index_builder()
    result = await index_builder.build_index(force=True)
    
    print(f"\n索引构建结果: {result}")
    return result

async def main():
    print("="*50)
    print("数据导入和ANN索引构建")
    print("="*50)
    
    importer = DataImporter()
    
    # 1. 导入产品
    products = importer.load_products()
    product_embeddings = importer.load_product_embeddings()
    print(f"产品: {len(products)}, Embeddings: {len(product_embeddings)}")
    importer.import_products(products, product_embeddings)
    
    # 2. 导入医美知识
    medical = importer.load_medical()
    medical_embeddings = importer.load_medical_embeddings()
    print(f"医美: {len(medical)}, Embeddings: {len(medical_embeddings)}")
    importer.import_medical(medical, medical_embeddings)
    
    # 3. 构建ANN索引
    await build_ann_index()
    
    print("\n" + "="*50)
    print("完成!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
