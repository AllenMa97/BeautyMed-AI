# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

"""
直接构建ANN索引 - 基于新导入的数据
"""
import json
import os
import sys
import numpy as np
from pathlib import Path
from datetime import datetime
import dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

dotenv.load_dotenv(os.path.join(PROJECT_ROOT, "config", "LLM_API.env"))

class DirectIndexBuilder:
    def __init__(self):
        self.storage_dir = os.path.join(PROJECT_ROOT, "knowledge_storage")
        self.contents_dir = os.path.join(self.storage_dir, "contents")
        self.embeddings_dir = os.path.join(self.storage_dir, "embeddings")
        self.ann_dir = os.path.join(PROJECT_ROOT, "data", "ann_index")
        
        os.makedirs(self.ann_dir, exist_ok=True)
    
    def load_contents(self, prefix):
        contents = {}
        files = list(Path(self.contents_dir).glob(f"{prefix}*.json"))
        
        for f in files:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                contents[data["id"]] = data
        
        return contents
    
    def load_embeddings(self, prefix):
        embeddings = {}
        files = list(Path(self.embeddings_dir).glob(f"{prefix}*.json"))
        
        for f in files:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                embeddings[data["id"]] = np.array(data["embedding"], dtype=np.float32)
        
        return embeddings
    
    def build_hnsw_index(self, vectors, ids):
        print(f"  构建HNSW索引: {len(vectors)} 个向量")
        
        from core.vector_store.ann_index import HNSWIndex
        
        index = HNSWIndex()
        
        for id_, vec in zip(ids, vectors):
            index.add_vector(id_, vec)
        
        return index
    
    def build_all(self):
        print("="*50)
        print("直接构建ANN索引")
        print("="*50)
        
        # 产品
        print("\n处理产品...")
        product_contents = self.load_contents("product_")
        product_embeddings = self.load_embeddings("product_")
        print(f"  产品内容: {len(product_contents)}")
        print(f"  产品embedding: {len(product_embeddings)}")
        
        valid_product_ids = []
        valid_product_vectors = []
        for id_ in product_contents:
            if id_ in product_embeddings:
                valid_product_ids.append(id_)
                valid_product_vectors.append(product_embeddings[id_])
        
        print(f"  有效产品: {len(valid_product_ids)}")
        
        if valid_product_ids:
            product_index = self.build_hnsw_index(valid_product_vectors, valid_product_ids)
            # 使用项目自带的保存方法
            ann_file = os.path.join(self.ann_dir, "product_hnsw.json")
            product_index.save(ann_file)
            print(f"  已保存: {ann_file}")
        
        # 医美知识
        print("\n处理医美知识...")
        medical_contents = self.load_contents("medical_")
        medical_embeddings = self.load_embeddings("medical_")
        print(f"  医美内容: {len(medical_contents)}")
        print(f"  医美embedding: {len(medical_embeddings)}")
        
        valid_medical_ids = []
        valid_medical_vectors = []
        for id_ in medical_contents:
            if id_ in medical_embeddings:
                valid_medical_ids.append(id_)
                valid_medical_vectors.append(medical_embeddings[id_])
        
        print(f"  有效医美: {len(valid_medical_ids)}")
        
        if valid_medical_ids:
            medical_index = self.build_hnsw_index(valid_medical_vectors, valid_medical_ids)
            ann_file = os.path.join(self.ann_dir, "entry_hnsw.json")
            medical_index.save(ann_file)
            print(f"  已保存: {ann_file}")
        
        # 更新统计
        index_file = os.path.join(self.storage_dir, "knowledge_index.json")
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        index_data["statistics"]["total_products"] = len(valid_product_ids)
        index_data["statistics"]["total_entries"] = len(valid_medical_ids)
        index_data["last_updated"] = datetime.now().isoformat()
        
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*50)
        print(f"完成! 产品: {len(valid_product_ids)}, 医美: {len(valid_medical_ids)}")
        print("="*50)

if __name__ == "__main__":
    builder = DirectIndexBuilder()
    builder.build_all()
