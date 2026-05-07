# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
知识库Embedding生成脚本
- 产品：用 品牌+产品名+tags 做embedding
- 医美知识：用 标题+核心关键词 做embedding
- 分批处理，持久化存储，支持断点续传
"""
import os
import json
import asyncio
import dotenv
from datetime import datetime

from config.settings import get_embedding_model, get_embedding_dimension

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv.load_dotenv(os.path.join(PROJECT_ROOT, "config", "LLM_API.env"))

API_KEY = "sk-614f2e32ce44483892c6fd2ce494d4ac"
os.environ["DASHSCOPE_API_KEY"] = API_KEY

from dashscope import TextEmbedding

BATCH_SIZE = 10
REQUEST_DELAY = 0.5

class EmbeddingGenerator:
    def __init__(self):
        self.products_file = os.path.join(PROJECT_ROOT, "import_data", "llm_products.json")
        self.medical_file = os.path.join(PROJECT_ROOT, "import_data", "llm_medical_knowledge.json")
        self.embeddings_dir = os.path.join(PROJECT_ROOT, "embeddings")
        
        os.makedirs(self.embeddings_dir, exist_ok=True)
    
    def prepare_product_text(self, product):
        parts = [
            product.get("brand", ""),
            product.get("name", ""),
        ]
        tags = product.get("tags", [])
        if tags:
            parts.append(" ".join(tags))
        return " ".join(parts)
    
    def prepare_medical_text(self, item):
        parts = [
            item.get("title", ""),
            item.get("category", ""),
        ]
        content = item.get("content", "")
        if content:
            parts.append(content[:200].replace("\n", " "))
        return " ".join(parts)
    
    def generate_embeddings_batch(self, texts, ids):
        resp = TextEmbedding.call(
            model=get_embedding_model(),
            input=texts,
            dimensions=get_embedding_dimension()
        )
        
        if resp.status_code != 200:
            raise Exception(f"API Error: {resp}")
        
        embeddings = resp.output["embeddings"]
        return [e["embedding"] for e in embeddings]
    
    def load_progress(self, prefix):
        progress_file = os.path.join(self.embeddings_dir, f"{prefix}_progress.json")
        embeddings_file = os.path.join(self.embeddings_dir, f"{prefix}_embeddings.json")
        
        processed_ids = set()
        all_embeddings = {}
        
        if os.path.exists(progress_file):
            with open(progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                processed_ids = set(data.get("processed_ids", []))
        
        if os.path.exists(embeddings_file):
            with open(embeddings_file, "r", encoding="utf-8") as f:
                all_embeddings = json.load(f)
        
        return processed_ids, all_embeddings, progress_file, embeddings_file
    
    def save_progress(self, processed_ids, all_embeddings, progress_file, embeddings_file):
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump({"processed_ids": list(processed_ids), "updated": datetime.now().isoformat()}, f)
        with open(embeddings_file, "w", encoding="utf-8") as f:
            json.dump(all_embeddings, f)
    
    def process_products(self):
        print("\n" + "="*50)
        print("处理产品embedding...")
        print("="*50)
        
        with open(self.products_file, "r", encoding="utf-8") as f:
            products = json.load(f)
        
        print(f"总产品数: {len(products)}")
        
        processed_ids, all_embeddings, progress_file, embeddings_file = self.load_progress("products")
        print(f"已处理: {len(processed_ids)}")
        
        to_process = [(i, p) for i, p in enumerate(products) if f"product_{i}" not in processed_ids]
        print(f"待处理: {len(to_process)}")
        
        if not to_process:
            print("全部完成!")
            return
        
        total_batches = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(to_process))
            batch = to_process[start:end]
            
            print(f"\n批次 {batch_idx + 1}/{total_batches} ({len(batch)} 个)")
            
            texts = []
            indices = []
            for idx, p in batch:
                texts.append(self.prepare_product_text(p))
                indices.append(idx)
            
            try:
                embeddings = self.generate_embeddings_batch(texts, indices)
                
                for idx, emb, p in zip(indices, embeddings, [p for _, p in batch]):
                    key = f"product_{idx}"
                    all_embeddings[key] = {
                        "embedding": emb,
                        "data": p,
                        "text": self.prepare_product_text(p)
                    }
                    processed_ids.add(key)
                
                self.save_progress(processed_ids, all_embeddings, progress_file, embeddings_file)
                print(f"  ✅ 累计 {len(processed_ids)}/{len(products)}")
                
                if batch_idx < total_batches - 1:
                    asyncio.sleep(REQUEST_DELAY)
                    
            except Exception as e:
                print(f"  ❌ 错误: {e}")
                continue
        
        print(f"\n✅ 产品处理完成: {len(processed_ids)}/{len(products)}")
    
    def process_medical(self):
        print("\n" + "="*50)
        print("处理医美知识embedding...")
        print("="*50)
        
        with open(self.medical_file, "r", encoding="utf-8") as f:
            medical = json.load(f)
        
        print(f"总知识数: {len(medical)}")
        
        processed_ids, all_embeddings, progress_file, embeddings_file = self.load_progress("medical")
        print(f"已处理: {len(processed_ids)}")
        
        to_process = [(i, item) for i, item in enumerate(medical) if f"medical_{i}" not in processed_ids]
        print(f"待处理: {len(to_process)}")
        
        if not to_process:
            print("全部完成!")
            return
        
        total_batches = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(to_process))
            batch = to_process[start:end]
            
            print(f"\n批次 {batch_idx + 1}/{total_batches} ({len(batch)} 个)")
            
            texts = []
            indices = []
            for idx, item in batch:
                texts.append(self.prepare_medical_text(item))
                indices.append(idx)
            
            try:
                embeddings = self.generate_embeddings_batch(texts, indices)
                
                for idx, emb, item in zip(indices, embeddings, [item for _, item in batch]):
                    key = f"medical_{idx}"
                    all_embeddings[key] = {
                        "embedding": emb,
                        "data": item,
                        "text": self.prepare_medical_text(item)
                    }
                    processed_ids.add(key)
                
                self.save_progress(processed_ids, all_embeddings, progress_file, embeddings_file)
                print(f"  ✅ 累计 {len(processed_ids)}/{len(medical)}")
                
                if batch_idx < total_batches - 1:
                    asyncio.sleep(REQUEST_DELAY)
                    
            except Exception as e:
                print(f"  ❌ 错误: {e}")
                continue
        
        print(f"\n✅ 医美知识处理完成: {len(processed_ids)}/{len(medical)}")
    
    def run(self):
        print("="*50)
        print("知识库Embedding生成")
        print("="*50)
        print(f"产品文件: {self.products_file}")
        print(f"医美文件: {self.medical_file}")
        print(f"输出目录: {self.embeddings_dir}")
        print(f"批次大小: {BATCH_SIZE}")
        
        self.process_products()
        self.process_medical()
        
        print("\n" + "="*50)
        print("全部完成!")
        print("="*50)

if __name__ == "__main__":
    generator = EmbeddingGenerator()
    generator.run()
