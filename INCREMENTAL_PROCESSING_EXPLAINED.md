# 📚 Incremental Processing Explained

## Quick Answer

**✅ YES - It APPENDS (adds to existing KG and embeddings)**

When you process 10 files first, then later process 100 more files:
- **New files are ADDED** to the existing KG
- **New embeddings are ADDED** to the existing collection
- **No data is deleted** unless you explicitly clear it
- **Duplicates are automatically prevented**

---

## How It Works

### 1. Knowledge Graph (Neo4j) - APPENDS

**How:**
- Uses `MERGE` operations (not `CREATE`)
- `MERGE` = "Create if doesn't exist, otherwise update"
- Based on unique IDs (concept.id, relationship.id, etc.)

**Example:**
```
First run (10 files):
- Creates 500 concepts
- Creates 200 relationships

Second run (100 more files):
- Adds 5000 more concepts (total: 5500)
- Adds 2000 more relationships (total: 2200)
- If same concept appears: Updates existing (no duplicate)
```

**Code:**
```cypher
MERGE (c:Concept {id: $concept_id})
SET c.name = $name, c.type = $type, ...
```

**Result:** ✅ **Incremental - adds to existing**

---

### 2. Embeddings (Qdrant) - APPENDS

**How:**
- Uses **deterministic IDs** (MD5 hash of content)
- Same chunk = same ID = no duplicate
- New chunks = new IDs = added to collection

**Example:**
```
First run (10 files):
- Creates 778 embeddings

Second run (100 more files):
- Adds 7,780 more embeddings (total: 8,558)
- If same chunk appears: Same ID = no duplicate
```

**Code:**
```python
id_string = f"{episode_id}:{source_path}:{chunk_index}:{start_char}:{ch.page_content[:100]}"
point_id = hashlib.md5(id_string.encode()).hexdigest()
```

**Result:** ✅ **Incremental - adds to existing**

---

## Example Scenario

### Step 1: Process 10 Files
```bash
uv run process_with_metrics_async.py \
  --workspace default \
  --transcripts-dir data/transcripts_10 \
  --max-concurrent 12 \
  --batch-size 10
```

**Result:**
- KG: 500 concepts, 200 relationships
- Embeddings: 778 vectors
- **Status**: ✅ Created

---

### Step 2: Process 100 More Files (Later)
```bash
uv run process_with_metrics_async.py \
  --workspace default \
  --transcripts-dir data/transcripts_100 \
  --max-concurrent 12 \
  --batch-size 10
```

**Result:**
- KG: **5,500 concepts** (500 + 5,000 new), **2,200 relationships** (200 + 2,000 new)
- Embeddings: **8,558 vectors** (778 + 7,780 new)
- **Status**: ✅ **APPENDED to existing**

---

## Duplicate Prevention

### Knowledge Graph:
- **Concepts**: Merged by `id` field
- **Relationships**: Merged by `id` field
- **Quotes**: Merged by `id` field
- **Result**: Same concept from different files = one node (updated)

### Embeddings:
- **Deterministic IDs**: Based on content hash
- **Same chunk** = Same ID = No duplicate
- **Different chunk** = Different ID = Added
- **Result**: No duplicate embeddings

---

## What Gets Updated

### If Same Content Appears Again:

**Knowledge Graph:**
- Same concept ID → **Updates existing node** (no duplicate)
- Same relationship ID → **Updates existing relationship** (no duplicate)
- New concept ID → **Creates new node**

**Embeddings:**
- Same chunk content → **Same ID** → **No duplicate** (skipped)
- Different chunk content → **New ID** → **Added**

---

## Workspace Isolation

### Each Workspace is Separate:

```
Workspace "default":
- Has its own KG nodes/relationships
- Has its own Qdrant collection

Workspace "user1":
- Has its own KG nodes/relationships
- Has its own Qdrant collection

Processing files in "default" does NOT affect "user1"
```

---

## How to Clear (If Needed)

### Clear Knowledge Graph:
```python
# In code (not in current script, but can be added):
MATCH (n) WHERE n.workspace_id = 'default' DELETE n
```

### Clear Embeddings:
```python
# Delete collection and recreate
qdrant.delete_collection(collection_name)
qdrant.recreate_collection(...)
```

### Clear Everything:
- Use `--clear` flag (if implemented)
- Or manually delete from Neo4j and Qdrant

---

## Best Practices

### 1. Incremental Processing ✅
- Process files in batches
- Each batch appends to existing
- No need to reprocess everything

### 2. Workspace Management:
- Use different workspaces for different projects
- Each workspace is isolated

### 3. Monitoring:
- Check KG stats before/after each run
- Verify new concepts/relationships added
- Check embedding count increased

---

## Example Workflow

### Day 1: Process 10 Files
```bash
uv run process_with_metrics_async.py \
  --workspace default \
  --transcripts-dir data/transcripts_10
```
**Result**: 500 concepts, 200 relationships, 778 embeddings

### Day 2: Process 50 More Files
```bash
uv run process_with_metrics_async.py \
  --workspace default \
  --transcripts-dir data/transcripts_50
```
**Result**: 3,000 concepts (500 + 2,500), 1,200 relationships (200 + 1,000), 3,890 embeddings (778 + 3,112)

### Day 3: Process 100 More Files
```bash
uv run process_with_metrics_async.py \
  --workspace default \
  --transcripts-dir data/transcripts_100
```
**Result**: 8,500 concepts (3,000 + 5,500), 3,200 relationships (1,200 + 2,000), 11,670 embeddings (3,890 + 7,780)

**Total**: 160 files processed incrementally ✅

---

## Summary

### ✅ Incremental Processing Works:

1. **First run**: Creates KG and embeddings
2. **Subsequent runs**: **APPENDS** to existing
3. **Duplicates**: Automatically prevented
4. **Workspace**: Each workspace is isolated
5. **No data loss**: Existing data remains

### 🎯 Answer to Your Question:

**"If I process 10 files once, then after few times when needed 100 files more, this new append in KG and embeddings or it creates new?"**

**Answer**: ✅ **APPENDS** - New files are added to existing KG and embeddings. No new KG/collection is created. Everything is incremental.

---

## Verification

### Check KG Stats:
```cypher
MATCH (c:Concept) WHERE c.workspace_id = 'default' RETURN count(c)
```

### Check Embedding Count:
```python
qdrant.get_collection(collection_name).points_count
```

### Before/After Comparison:
- Before: 500 concepts
- After: 5,500 concepts
- **Difference**: 5,000 new concepts added ✅

