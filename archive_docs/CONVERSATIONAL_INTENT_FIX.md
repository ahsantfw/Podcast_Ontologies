# Fix: Conversational Intent Bypassing Retrieval

## Problem Identified

**Issue**: When asking "What are the issues of society?" in a NEW session:
- ❌ **RAG: 0, KG: 0** (no retrieval!)
- ❌ **Answer**: Generated from general knowledge
- ❌ **Root Cause**: Query was misclassified as "conversational" instead of "knowledge_query"

**Why This Happened**:
1. Intent classifier (`_classify_intent_llm`) classified the query as "conversational"
2. "Conversational" intent routes to `_handle_with_llm()` which bypasses retrieval entirely
3. `_handle_with_llm()` generates answers from LLM general knowledge without any retrieval

---

## Root Cause Analysis

### Intent Classification Issue

The query "What are the issues of society?" was being classified as:
- ❌ **"conversational"** (WRONG - bypasses retrieval)
- ✅ **Should be**: "knowledge_query" (requires retrieval)

### Code Path Problem

```
Query → _classify_intent_llm() → "conversational"
  ↓
_handle_with_llm() → Generates answer WITHOUT retrieval
  ↓
RAG=0, KG=0, but still answers from general knowledge ❌
```

**Correct Path Should Be**:
```
Query → _classify_intent_llm() → "knowledge_query"
  ↓
_handle_knowledge_query() → Retrieves RAG + KG
  ↓
_synthesize_answer() → Answers from corpus ✅
```

---

## Solutions Implemented

### 1. **Stricter Intent Classification** ✅
**File**: `core_engine/reasoning/agent.py` → `_classify_intent_llm()`

**Change**: Added explicit rule that questions are almost always `knowledge_query`:
```python
CRITICAL RULE: If a query is a QUESTION (starts with "what", "who", "how", etc.), 
it is ALMOST ALWAYS knowledge_query, NOT conversational, UNLESS it's clearly asking 
about the user's personal info or system capabilities.
```

### 2. **Safety Check Before Routing to Conversational** ✅
**File**: `core_engine/reasoning/agent.py` → `run()` method

**Change**: Added check before routing to `_handle_with_llm()`:
```python
if intent == "conversational":
    # SAFETY CHECK: If query looks like a knowledge question, route to retrieval instead
    question_patterns = [
        r"^(what|who|how|why|when|where|are|is|can|do|does|did|will|would|should|tell me|explain|describe|list|show|give|find|search)",
        r"\?$",  # Ends with question mark
    ]
    if is_question:
        # Route to retrieval instead
        return self._handle_knowledge_query(...)
```

### 3. **Double Safety Check in _handle_with_llm** ✅
**File**: `core_engine/reasoning/agent.py` → `_handle_with_llm()`

**Change**: Added check at the start of the method:
```python
# SAFETY CHECK: If this looks like a knowledge question, route to retrieval instead
if intent_type == "conversational":
    question_patterns = [...]
    knowledge_phrases = ["issues", "problems", "solutions", "concepts", ...]
    
    if is_question or has_knowledge_phrase:
        # Route to retrieval instead
        return self._handle_knowledge_query(...)
```

### 4. **Updated Conversational Prompt** ✅
**File**: `core_engine/reasoning/agent.py` → `_handle_with_llm()`

**Change**: Added warning in conversational prompt:
```python
CRITICAL: This intent is ONLY for casual statements, reactions, or personal sharing.
If the user asks a QUESTION about podcast content, concepts, or knowledge, you MUST NOT answer it here.
```

---

## Expected Behavior After Fix

### Query: "What are the issues of society?" (New Session)

**Before**:
- ❌ Intent: "conversational"
- ❌ Route: `_handle_with_llm()` (bypasses retrieval)
- ❌ RAG: 0, KG: 0
- ❌ Answer: From general knowledge

**After**:
- ✅ Intent: "knowledge_query" (or caught by safety check)
- ✅ Route: `_handle_knowledge_query()` (requires retrieval)
- ✅ RAG: 10, KG: 10
- ✅ Answer: From podcast corpus with citations

---

## Testing

### Test Cases

1. **"What are the issues of society?"** (New Session)
   - ✅ Should route to retrieval
   - ✅ Should get RAG > 0, KG > 0
   - ✅ Should cite podcast sources

2. **"Thanks!"** (Conversational)
   - ✅ Should route to `_handle_with_llm()`
   - ✅ Should respond conversationally
   - ✅ No retrieval needed

3. **"What did Phil Jackson say about meditation?"** (Knowledge Query)
   - ✅ Should route to retrieval
   - ✅ Should get RAG > 0, KG > 0
   - ✅ Should cite sources

---

## Files Modified

1. **`core_engine/reasoning/agent.py`**
   - `_classify_intent_llm()`: Stricter rules for question classification
   - `run()`: Safety check before routing to conversational
   - `_handle_with_llm()`: Double safety check + updated prompt

---

## Status

✅ **Fixed**: Multiple safety checks prevent knowledge questions from bypassing retrieval
✅ **Fixed**: Intent classifier is stricter about question classification
✅ **Fixed**: Conversational prompt warns against answering knowledge questions

**Ready for testing!**

---

## Key Insight

**The Problem**: Intent classification is imperfect - LLMs can misclassify queries.

**The Solution**: Multiple layers of safety checks:
1. **Prevention**: Stricter classification rules
2. **Detection**: Pattern matching for questions
3. **Correction**: Automatic re-routing to retrieval

This ensures that even if classification fails, retrieval is still enforced.
