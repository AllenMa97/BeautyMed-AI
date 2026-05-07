# Developer: 马赫·马智勇
# Position: 大模型算法工程师
# Created: 2026-04-22
# Copyright (c) 2026. All rights reserved.

import os
from pathlib import Path

_env_loaded = False


def _load_env():
    global _env_loaded
    if _env_loaded:
        return
    env_file = Path(__file__).parent / "env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
    _env_loaded = True


_load_env()


def get_embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", "text-embedding-v3")


def get_embedding_dimension() -> int:
    return int(os.getenv("EMBEDDING_DIMENSION", "1024"))


def get_embedding_api_base() -> str:
    return os.getenv("EMBEDDING_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")


def get_embedding_batch_size() -> int:
    return int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))


def get_hnsw_m() -> int:
    return int(os.getenv("HNSW_M", "16"))


def get_hnsw_ef_construction() -> int:
    return int(os.getenv("HNSW_EF_CONSTRUCTION", "200"))


def get_hnsw_ef_search() -> int:
    return int(os.getenv("HNSW_EF_SEARCH", "50"))


def get_service_port() -> int:
    return int(os.getenv("SERVICE_PORT", "8002"))
