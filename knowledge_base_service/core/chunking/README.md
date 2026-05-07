# Chunking 分块系统架构文档

> **版本**: v2.0  
> **更新时间**: 2026-04-20  
> **作者**: 马赫·马智勇

---

## 📚 目录

- [为什么需要分块](#为什么需要分块)
- [分块策略演进](#分块策略演进)
- [系统架构](#系统架构)
- [核心组件详解](#核心组件详解)
- [使用指南](#使用指南)
- [性能优化](#性能优化)
- [增量更新](#增量更新)
- [常见问题](#常见问题)

---

## 🎯 为什么需要分块？

### 问题背景

1. **LLM 输入长度限制**
   - 大多数 LLM 有 4K/8K/32K tokens 的输入限制
   - 不能一次性处理整篇文档（特别是长文档）

2. **检索精度需求**
   - 用户查询通常很具体（如"玻尿酸注射后有哪些副作用？"）
   - 需要找到文档中的**具体段落**，而不是整篇文档
   - 分块质量直接影响检索精度

3. **上下文相关性**
   - RAG 系统需要为 LLM 提供**最相关**的上下文
   - 粗粒度的文档级检索会包含大量无关信息
   - 细粒度的 chunk 级检索能精准定位相关段落

### 分块的目标

```
文档 → 分块 → 检索 → 找到最相关的 chunk → 提供给 LLM
```

**好的分块应该**:
- ✅ 保持语义完整性（一个 chunk 内主题统一）
- ✅ 粒度适中（不太长也不太短）
- ✅ 支持高效检索（有合适的索引结构）

---

## 📈 分块策略演进

### 1. 固定长度分块 ❌

```python
# 简单按字符数切分
chunks = [text[i:i+500] for i in range(0, len(text), 500)]
```

**问题**:
- ❌ 会从句子中间切断
- ❌ 不考虑语义边界
- ❌ 一个 chunk 可能包含多个不相关的话题

**示例**:
```
"玻尿酸是一种天然多糖。它具有强保水能力，广泛用于医美填充。
兰蔻小黑瓶售价 1200 元。使用方法：每日早晚各一次。"

固定长度分块可能在"填充。"和"兰蔻"之间切断，
导致前一个 chunk 包含"玻尿酸定义 + 兰蔻价格"两个不相关内容。
```

---

### 2. 句子边界分块 ✅

```python
# 在句号、感叹号、问号、换行符处切断
sentences = re.split(r"(?<=[。！？.!?])\s*|(?<=[\n])", text)
```

**优点**:
- ✅ 保持句子完整性
- ✅ 每个 chunk 内的内容语义相对连贯
- ✅ 实现简单，速度快

**问题**:
- ⚠️ 无法识别话题转换点
- ⚠️ 可能把两个不相关但都短的句子强行合并

**示例**:
```
句子 1: "玻尿酸是一种天然多糖。"  ─┐
句子 2: "它具有强保水能力。"      ├─→ 合并（合理）
句子 3: "兰蔻小黑瓶售价 1200 元。" ─┘
                                      ↓
句子 4: "使用方法：每日早晚各一次。"  ─┐
句子 5: "敏感肌建议先做皮试。"      ├─→ 合并（合理）
句子 6: "产品成分表如下：..."        ─┘
```

---

### 3. 语义相似度分块 ✅✅

```python
# 计算相邻句子的 Embedding 相似度
similarity = cosine_similarity(embedding(sentence_i), embedding(sentence_i+1))

# 在相似度低的地方切断（如 < 0.6）
if similarity < 0.6:
    # 语义转换，切断
    split_here()
```

**优点**:
- ✅ 自动识别话题转换点
- ✅ 确保每个 chunk 内主题统一
- ✅ 检索精度提升 20-30%

**示例**:
```
句子 1: "玻尿酸是一种天然多糖。"  ─┐
句子 2: "它具有强保水能力。"      ├─→ 相似度 0.85 → 合并
句子 3: "广泛用于医美填充。"      ─┘
                                      ↓
句子 4: "兰蔻小黑瓶售价 1200 元。"  ─┐
                                      ├─→ 相似度 0.45 → 切断！
句子 5: "使用方法：每日早晚各一次。"  ─┘
```

**性能**:
- 构建时：需要为每个句子调用 Embedding API
- 540 个文档 × 平均 20 句/文档 = 10800 次调用
- 约 30 分钟（可并行加速）

---

### 4. 父子分块 ✅✅✅（最佳实践）

```
文档 → 语义相似度分块 → 父 chunk (512 tokens)
                          │
                          ├─→ 子 chunk_1 (128 tokens)
                          ├─→ 子 chunk_2 (128 tokens)
                          └─→ 子 chunk_3 (128 tokens)
```

**核心思想**:
- **父 chunk**: 语义完整的段落（~512 tokens），提供上下文
- **子 chunk**: 细粒度的片段（~128 tokens），用于检索

**检索策略**:
1. 用**子 chunk**检索（粒度细，语义聚焦，精度高）
2. 找到子 chunk 后，通过 `parent_id` 找到**父 chunk**
3. 返回父 chunk 作为上下文（信息完整）

**示例**:
```
父 chunk_1 (512 tokens): 
  "兰蔻小黑瓶精华液，含二裂酵母发酵产物溶胞物，能够促进肌肤修复，
   增强屏障功能。适用肤质：所有肤质，特别推荐轻熟肌和初老肌使用。
   使用方法：每日早晚各一次，洁面后取适量涂抹于面部。"

  ├── 子 chunk_1a (128 tokens): 
  │     "兰蔻小黑瓶精华液，核心成分为二裂酵母发酵产物溶胞物..."
  │
  ├── 子 chunk_1b (128 tokens): 
  │     "二裂酵母发酵产物溶胞物，能够促进肌肤修复，增强屏障功能..."
  │
  └── 子 chunk_1c (128 tokens): 
        "适用肤质：所有肤质，特别推荐轻熟肌和初老肌使用..."

用户查询："兰蔻小黑瓶适合什么肤质？"
→ 检索到：子 chunk_1c（最匹配）
→ 返回：父 chunk_1（完整信息，包含成分、功效、适用肤质、使用方法等）
```

**优势**:
- ✅ 检索精度高（子 chunk 语义聚焦）
- ✅ 上下文完整（父 chunk 信息全面）
- ✅ 避免断章取义

---

## 🏗️ 系统架构

### 类图

```
BaseChunker (抽象基类)
    ↑
    │
HybridChunker (唯一推荐使用的分块器)
    │
    ├─ 用语义相似度识别话题转换点（内部实现）
    │   └─ 计算相邻句子的 Embedding 相似度，在相似度低处切断
    │
    └─ ParentChildChunker (父子分块，内部使用)
        └─ 将父 chunk 拆分为子 chunk，建立父子关系
```

### 重要说明

**只使用 `HybridChunker`！**

其他类（`BaseChunker`、`ParentChildChunker`）都是内部实现细节，不直接使用。

### 数据结构

#### Document（文档）

```python
@dataclass
class Document:
    id: str              # UUID
    content: str         # 完整文本
    title: str           # 标题
    source: str          # 来源（如"产品手册"）
    source_type: str     # 类型（如"product"）
    metadata: dict       # 额外元数据
    created_at: str      # 创建时间
```

#### Chunk（分块）

```python
@dataclass
class Chunk:
    id: str              # UUID
    content: str         # chunk 文本
    parent_id: str       # 父 chunk ID（如果是子 chunk）
    children_ids: list   # 子 chunk ID 列表（如果是父 chunk）
    metadata: dict       # 元数据
    embedding: list      # 向量（1024 维）
    token_count: int     # token 数
    created_at: str      # 创建时间
```

### 父子关系示例

```python
# 父 chunk
parent = Chunk(
    id="parent_123",
    content="兰蔻小黑瓶精华液，含二裂酵母...",
    children_ids=["child_456", "child_789", "child_012"],
)

# 子 chunk
child1 = Chunk(
    id="child_456",
    content="兰蔻小黑瓶精华液，核心成分为...",
    parent_id="parent_123",
)

child2 = Chunk(
    id="child_789",
    content="二裂酵母发酵产物溶胞物，能够促进...",
    parent_id="parent_123",
)
```

---

## 🔧 核心组件详解

### HybridChunker（唯一推荐使用的分块器）

**文件**: `core/chunking/hybrid_chunker.py`

**核心设计**:
- 用语义相似度识别话题转换点（内部实现）
- 生成父子 chunk 结构（细粒度检索 + 完整上下文）
- 自动推断元数据（权威等级、类别）

**参数**:
- `parent_max_tokens`: 父 chunk 最大 token 数（默认 512）
- `child_max_tokens`: 子 chunk 最大 token 数（默认 128）
- `similarity_threshold`: 语义相似度阈值（默认 0.6）
  - 调低（如 0.5）→ chunk 更大，可能包含多个子话题
  - 调高（如 0.7）→ chunk 更小，语义更聚焦
- `min_tokens`: 最小 token 数（默认 50）
- `enable_parent_child`: 是否启用父子分块（默认 True）

**使用示例**:
```python
from core.chunking import HybridChunker, Document

# 默认配置（推荐）
chunker = HybridChunker()

# 调整参数
chunker = HybridChunker(
    parent_max_tokens=512,      # 父 chunk 最大 512 tokens
    child_max_tokens=128,       # 子 chunk 最大 128 tokens
    similarity_threshold=0.6,   # 语义相似度阈值 0.6
    min_tokens=50,              # 最小 50 tokens
)

doc = Document(
    content="玻尿酸是一种天然多糖，具有强保水能力...",
    title="玻尿酸产品介绍",
    source="产品手册",
    source_type="product",
)

chunks = chunker.chunk(doc)
```

**内部实现细节**:

`HybridChunker` 内部使用了语义相似度识别和父子分块策略：

1. **语义相似度识别**：计算相邻句子的 Embedding 相似度，在相似度低处切断
2. **父子分块**：将父 chunk 拆分为子 chunk，建立父子关系
3. **元数据增强**：自动推断权威等级和类别

这些实现细节都被封装在内部，用户只需要使用 `HybridChunker` 即可。

---

## 📖 使用指南

### 1. 配置环境变量

**第一步**：复制 `.env.example` 到 `.env`

```bash
cp .env.example .env
```

**第二步**：编辑 `.env` 文件，配置 chunking 参数

```bash
# 语义相似度阈值（0-1 之间）
# 推荐值：0.6（适用于大多数医美文档）
CHUNK_SIMILARITY_THRESHOLD=0.6

# 父 chunk 最大 token 数
CHUNK_PARENT_MAX_TOKENS=512

# 子 chunk 最大 token 数
CHUNK_CHILD_MAX_TOKENS=128

# 最小 token 数
CHUNK_MIN_TOKENS=50

# 是否启用父子分块（True/False）
CHUNK_ENABLE_PARENT_CHILD=True
```

**详细说明**请查看 `.env.example` 文件中的注释，包含：
- 每个参数的作用
- 调整建议
- 实际示例

### 2. 基础用法

```python
from core.chunking import HybridChunker, Document

# 1. 创建文档
doc = Document(
    content="玻尿酸是一种天然多糖，具有强保水能力。"
            "广泛用于医美填充，如兰蔻小黑瓶、欧莱雅复颜系列...",
    title="玻尿酸产品介绍",
    source="产品手册",
    source_type="product",
)

# 2. 创建分块器（会自动从环境变量读取配置）
chunker = HybridChunker()

# 3. 分块
chunks = chunker.chunk(doc)

# 4. 查看结果
print(f"共生成 {len(chunks)} 个 chunk")

for chunk in chunks:
    chunk_type = chunk.metadata.get("chunk_type", "unknown")
    print(f"\n{chunk_type.upper()}: {chunk.content[:50]}...")
    print(f"  Token 数：{chunk.token_count}")
    print(f"  父子关系：parent_id={chunk.parent_id}, children_ids={chunk.children_ids}")
```

### 3. 覆盖环境变量（可选）

如果需要在代码中临时覆盖环境变量：

```python
# 临时调整语义相似度阈值
chunker = HybridChunker(
    similarity_threshold=0.7,  # 覆盖环境变量中的 0.6
    parent_max_tokens=600,     # 覆盖环境变量中的 512
)

# 这个 chunker 会使用传入的参数，而不是环境变量
chunks = chunker.chunk(doc)
```

**参数优先级**：
1. 代码中传入的参数（最高优先级）
2. 环境变量中的配置
3. 默认值（最低优先级）

### 高级用法

#### 1. 调整语义相似度阈值

```python
# 更严格（chunk 更小，语义更聚焦）
chunker = HybridChunker(similarity_threshold=0.7)

# 更宽松（chunk 更大，包含更多内容）
chunker = HybridChunker(similarity_threshold=0.5)
```

#### 2. 调整 chunk 大小

```python
# 父 chunk 更大（1024 tokens），子 chunk 更大（256 tokens）
chunker = HybridChunker(
    parent_max_tokens=1024,
    child_max_tokens=256,
)
```

#### 3. 只用语义相似度分块（不要父子分块）

```python
chunker = HybridChunker(enable_parent_child=False)
chunks = chunker.chunk(doc)
```

#### 4. 批量处理文档

```python
from core.chunking import HybridChunker, Document

chunker = HybridChunker()

documents = [
    Document(content="...", title="文档 1"),
    Document(content="...", title="文档 2"),
    # ...
]

all_chunks = []
for doc in documents:
    chunks = chunker.chunk(doc)
    all_chunks.extend(chunks)

print(f"共生成 {len(all_chunks)} 个 chunk")
```

---

## ⚡ 性能优化

### 构建时优化

#### 1. 批量调用 Embedding API

```python
# ❌ 慢：单个调用
embeddings = []
for sentence in sentences:
    emb = embedding_client.get_embedding(sentence)
    embeddings.append(emb)

# ✅ 快：批量调用（快 10 倍）
embeddings = embedding_client.get_embeddings(sentences)
```

#### 2. 并行处理文档

```python
from concurrent.futures import ProcessPoolExecutor

def process_document(doc):
    chunker = HybridChunker()
    return chunker.chunk(doc)

with ProcessPoolExecutor(max_workers=10) as executor:
    all_chunks = list(executor.map(process_document, documents))
```

**预估时间**:
- 540 个文档 × 平均 20 句/文档 = 10800 次 Embedding 调用
- 串行：约 30 分钟
- 并行（10 进程）：约 3 分钟

### 检索时优化

#### 1. 用子 chunk 检索，返回父 chunk

```python
# 检索
results = vector_store.search(query, top_k=10)

# 找到子 chunk 的父 chunk
parent_chunks = []
for result in results:
    if result.metadata.get("chunk_type") == "child":
        parent = get_parent_by_id(result.parent_id)
        parent_chunks.append(parent)

# 返回父 chunk 作为上下文
context = "\n\n".join([p.content for p in parent_chunks])
```

#### 2. 去重

```python
# 多个子 chunk 可能属于同一个父 chunk
# 需要去重
unique_parents = {}
for chunk in results:
    parent_id = chunk.parent_id or chunk.id
    if parent_id not in unique_parents:
        unique_parents[parent_id] = chunk

context = "\n\n".join([c.content for c in unique_parents.values()])
```

---

## 🔄 增量更新

### 问题

当文档更新时，如何高效更新 chunk 和向量索引？

### 解决方案

#### 1. Chunk 级别的版本管理

```python
# 每个文档的元数据
document_metadata = {
    "document_id": "doc_123",
    "version": "v1.2",
    "updated_at": "2026-04-20 14:30:00",
    "chunks": [
        {
            "chunk_id": "chunk_456",
            "chunk_hash": "md5(内容)",  # 用于检测内容变化
            "embedding_version": "v3.1",
            "created_at": "2026-04-15 10:00:00",
            "updated_at": "2026-04-20 14:30:00",
        },
        # ...
    ]
}
```

#### 2. 增量更新流程

```python
def update_document(document_id, new_content):
    # 1. 计算新内容的 MD5
    new_hash = md5(new_content)
    
    # 2. 检查是否已存在
    old_metadata = metadata_store.get(document_id)
    
    if not old_metadata:
        # 新文档：完整处理
        chunks = chunker.chunk(Document(content=new_content))
        embeddings = generate_embeddings(chunks)
        save_to_vector_store(chunks, embeddings)
        metadata_store.add(document_id, chunks, new_hash)
    else:
        # 已存在：对比 MD5
        old_hash = old_metadata.get("document_hash")
        
        if new_hash == old_hash:
            # 内容未变：跳过
            print("内容未变，跳过")
            return
        
        # 内容已变：重新 chunking
        chunks = chunker.chunk(Document(content=new_content))
        
        # 对比 chunk_hash，只更新变化的 chunk
        for chunk in chunks:
            chunk_hash = md5(chunk.content)
            old_chunk = find_chunk_by_hash(old_metadata["chunks"], chunk_hash)
            
            if not old_chunk:
                # 新 chunk：生成 embedding 并插入
                emb = generate_embedding(chunk)
                vector_store.add_vector(chunk.id, emb)
        
        # 更新元数据
        metadata_store.update(document_id, chunks, new_hash)
```

---

## ❓ 常见问题

### Q1: 为什么用语义相似度而不是纯按长度分块？

**A**: 语义相似度能识别话题转换点，确保每个 chunk 内主题统一。

**示例**:
```
"玻尿酸是一种天然多糖。它具有强保水能力。"  (相似度 0.85 → 合并)
"兰蔻小黑瓶售价 1200 元。"  (与前一句相似度 0.45 → 切断)
```

纯按长度分块可能在句子中间切断，或者把不相关的句子强行合并。

---

### Q2: 父子分块有什么好处？

**A**: 支持"细粒度检索 + 完整上下文"。

- **检索时**: 用子 chunk（128 tokens），粒度细，语义聚焦，能找到更精确的匹配
- **返回时**: 带父 chunk（512 tokens），信息完整，避免断章取义

**示例**:
```
用户查询："兰蔻小黑瓶适合什么肤质？"
→ 检索到：子 chunk_1c（"适用肤质：所有肤质，特别推荐轻熟肌和初老肌使用..."）
→ 返回：父 chunk_1（完整信息，包含成分、功效、适用肤质、使用方法等）
```

---

### Q3: 语义相似度阈值应该设多少？

**A**: 默认 0.6 是经验值，适用于大多数场景。

- **调低（如 0.5）**: chunk 更大，包含更多内容，但可能混入不相关信息
- **调高（如 0.7）**: chunk 更小，语义更聚焦，但可能切断相关上下文

**建议**: 先用默认值 0.6，然后根据实际效果调整。

---

### Q4: 构建 chunk 需要多长时间？

**A**: 取决于文档数量和 Embedding API 速度。

**估算**:
- 540 个文档 × 平均 20 句/文档 = 10800 次 Embedding 调用
- 阿里云 DashScope API: 约 10 次/秒
- 串行：约 18 分钟
- 并行（10 进程）：约 2 分钟

**建议**: 首次构建时用并行，增量更新时单个文档只需几秒。

---

### Q5: 如何处理文档更新？

**A**: 使用增量更新策略。

1. 计算文档内容的 MD5
2. 如果 MD5 未变，跳过
3. 如果 MD5 变了，重新 chunking
4. 对比 chunk_hash，只更新变化的 chunk
5. 增量更新向量索引和知识图谱

详见 [增量更新](#增量更新) 章节。

---

## 📝 总结

### 推荐配置

```python
chunker = HybridChunker(
    parent_max_tokens=512,      # 父 chunk 最大 512 tokens
    child_max_tokens=128,       # 子 chunk 最大 128 tokens
    similarity_threshold=0.6,   # 语义相似度阈值 0.6（推荐）
    min_tokens=50,              # 最小 50 tokens
    enable_parent_child=True,   # 启用父子分块
)
```

### 核心优势

1. ✅ **语义完整性**: 用语义相似度识别话题转换点
2. ✅ **细粒度检索**: 用子 chunk 检索，精度高
3. ✅ **完整上下文**: 返回父 chunk，信息全面
4. ✅ **增量更新**: 支持文档级别的版本管理
5. ✅ **详细注释**: 代码即文档，无需额外询问

### 下一步

1. 运行数据流水线脚本：
   ```bash
   python chunk_documents.py
   python generate_embeddings.py
   python build_knowledge_graph.py
   ```

2. 测试检索效果：
   ```python
   from core.services.rag_service import RAGService
   
   service = RAGService()
   result = await service.query("玻尿酸注射后有哪些副作用？")
   print(result.context)
   ```

---

**文档结束**
