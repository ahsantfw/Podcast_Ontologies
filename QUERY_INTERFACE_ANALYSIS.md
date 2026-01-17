# Query Interface Analysis

## Client End File: `main.py`

### Query Interface Function: `query_interactive()`

**Location**: `ontology_production_v1/main.py` (lines ~100-190)

---

## How Questions Are Handled

### 1. **Question Input**
```python
question = input("💬 Question: ").strip()
```
- User types question in terminal
- Question is stripped of whitespace
- Stored in `question` variable

### 2. **Special Commands**

#### Exit Commands:
```python
if question.lower() in ["exit", "quit"]:
    print("\n👋 Goodbye!")
    break
```
- User can type `exit` or `quit` to end session

#### Stats Command:
```python
if question.lower() == "stats":
    # Shows graph statistics
    print(f"📊 Graph Statistics:")
    print(f"   Total nodes: {total}")
    print(f"   Total relationships: {rels}\n")
```
- User can type `stats` to see database statistics

### 3. **Question Processing Flow**

```python
# Step 1: User enters question
question = input("💬 Question: ").strip()

# Step 2: Query the reasoner
result = reasoner.query(question, session_id=session_id)

# Step 3: Update session ID (for memory)
session_id = result["session_id"]

# Step 4: Display answer
print(f"\n💡 Answer:")
print("-" * 60)
print(result["answer"])
print("-" * 60)
```

---

## What Happens When You Ask a Question

### Flow Diagram:

```
User Input
    ↓
[Question: "Who is Phil Jackson?"]
    ↓
reasoner.query(question, session_id)
    ↓
┌─────────────────────────────────────┐
│  KGReasoner.query()                 │
│  - Gets/creates session              │
│  - Adds user message to session      │
│  - Chooses query method:            │
│    • Hybrid RAG+KG (default)        │
│    • LLM-based                      │
│    • Pattern-based                  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Hybrid Retriever                   │
│  - Vector search (Qdrant)           │
│  - Graph search (Neo4j)             │
│  - Fuse results                     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Query Generator                    │
│  - Generate Cypher query            │
│  - Execute query                    │
│  - Return KG results                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  LLM Synthesis                      │
│  - Combine RAG + KG results         │
│  - Use conversation history          │
│  - Generate answer                  │
└─────────────────────────────────────┘
    ↓
[Answer returned to main.py]
    ↓
Display to user
```

---

## Question Types Supported

### 1. **Entity Questions**
- "Who is Phil Jackson?"
- "What is meditation?"
- "Tell me about mindfulness"

### 2. **Relationship Questions**
- "What practices does Phil Jackson recommend?"
- "What concepts are related to meditation?"
- "What practices optimize flow state?"

### 3. **Cross-Episode Questions**
- "What concepts appear in multiple episodes?"
- "What practices are mentioned across episodes?"

### 4. **Quote Questions**
- "What quotes about meditation?"
- "Show me quotes from Phil Jackson"

### 5. **List Questions**
- "List all practices"
- "What concepts are mentioned?"

### 6. **Follow-up Questions (Memory)**
- "What did he say about that?"
- "Tell me more about the first one"
- "What are the benefits?"

---

## Special Features

### 1. **Session Management**
```python
session_id = result["session_id"]
```
- Each query session has a unique ID
- Session maintains conversation history
- Memory persists within session

### 2. **Metadata Display**
```python
if result.get("metadata"):
    meta = result["metadata"]
    if meta.get("method"):
        print(f"📝 Method: {meta['method']}")
    if meta.get("rag_count"):
        print(f"📄 RAG results: {meta['rag_count']}")
    if meta.get("kg_count"):
        print(f"🕸️  KG results: {meta['kg_count']}")
```
- Shows which method was used (hybrid, llm, pattern)
- Shows how many RAG results found
- Shows how many KG results found

### 3. **Error Handling**
```python
except Exception as e:
    print(f"\n❌ Error: {e}\n")
```
- Catches and displays errors gracefully
- Continues to next question

---

## Example Interaction

```
💬 Question: Who is Phil Jackson?

🔍 Querying...

💡 Answer:
------------------------------------------------------------
Phil Jackson is a person known for his career in professional 
basketball. He is a former NBA player and coach...
------------------------------------------------------------

📝 Method: hybrid
🕸️  KG results: 5

💬 Question: What practices does he recommend?

🔍 Querying...

💡 Answer:
------------------------------------------------------------
Based on the conversation, Phil Jackson recommends practices 
such as meditation, mindfulness, and team cohesion...
------------------------------------------------------------

📝 Method: hybrid
📄 RAG results: 3
🕸️  KG results: 8
```

---

## Code Structure

### Main Components:

1. **`query_interactive(workspace_id, use_hybrid=True)`**
   - Main query loop
   - Handles user input
   - Displays results

2. **`reasoner.query(question, session_id)`**
   - Processes question
   - Returns answer + metadata

3. **Session Management**
   - Maintains conversation history
   - Tracks session ID

---

## Questions You Can Ask

Based on the code analysis, you can ask:

### ✅ **Basic Questions**
- "Who is [person]?"
- "What is [concept]?"
- "Tell me about [topic]"

### ✅ **Relationship Questions**
- "What practices does [person] recommend?"
- "What concepts are related to [concept]?"
- "What practices optimize [outcome]?"

### ✅ **List Questions**
- "List all practices"
- "What concepts are mentioned?"
- "What quotes about [topic]?"

### ✅ **Cross-Episode Questions**
- "What concepts appear in multiple episodes?"
- "What practices are mentioned across episodes?"

### ✅ **Follow-up Questions (Memory)**
- "What did he say about that?"
- "Tell me more about [previous topic]"
- "What are the benefits?"

### ✅ **Special Commands**
- `stats` - Show graph statistics
- `exit` or `quit` - End session

---

## Memory Integration

The query interface uses session management:

```python
result = reasoner.query(question, session_id=session_id)
session_id = result["session_id"]  # Maintains same session
```

This allows:
- ✅ Pronoun resolution ("he", "it", "that")
- ✅ Context awareness
- ✅ Conversation flow
- ✅ Follow-up questions

---

## Summary

**File**: `main.py`  
**Function**: `query_interactive()`  
**Purpose**: Interactive query interface for asking questions

**Key Features**:
- ✅ Simple input/output
- ✅ Session management
- ✅ Error handling
- ✅ Metadata display
- ✅ Special commands (stats, exit)
- ✅ Memory support

**Question Flow**:
1. User types question
2. System processes with hybrid RAG+KG
3. Answer displayed with metadata
4. Session maintained for follow-ups

