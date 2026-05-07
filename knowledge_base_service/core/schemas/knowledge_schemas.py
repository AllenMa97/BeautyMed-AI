# Developer: 椹但路椹櫤鍕?
# Position: 澶фā鍨嬬畻娉曞伐绋嬪笀
# Created: 2026-04-16
# Copyright (c) 2026. All rights reserved.

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class KnowledgeEntry(BaseModel):
    id: str
    title: str
    content: str
    source_url: Optional[str] = None
    topic: str
    tags: List[str] = []
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    embedding_vector: Optional[List[float]] = None  # For similarity search