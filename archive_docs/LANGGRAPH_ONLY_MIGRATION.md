# LangGraph-Only Migration

## Summary

Removed the non-LangGraph path and made LangGraph the default and only path for query processing.

---

## Changes Made

### 1. **Removed Feature Flag** ✅
**File**: `core_engine/reasoning/reasoning.py`

**Before**:
```python
self.use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
if self.use_langgraph:
    # Initialize LangGraph
else:
    # Fallback to standard flow
```

**After**:
```python
# LangGraph is now the default and only path
self.langgraph_workflow = None

# Initialize LangGraph workflow (required)
try:
    from core_engine.reasoning.langgraph_workflow import create_retrieval_workflow
    self.langgraph_workflow = create_retrieval_workflow()
    if not self.langgraph_workflow:
        raise RuntimeError("LangGraph workflow creation failed")
except Exception as e:
    raise RuntimeError(f"Failed to initialize LangGraph workflow: {e}")
```

### 2. **Removed Conditional Routing** ✅
**File**: `core_engine/reasoning/reasoning.py` → `query()` method

**Before**:
```python
if self.use_langgraph and self.langgraph_workflow:
    agent_response = self._query_with_langgraph(...)
else:
    agent_response = self.agent.run(...)  # Standard flow
```

**After**:
```python
# Use LangGraph workflow (only path)
agent_response = self._query_with_langgraph(...)
```

### 3. **Removed Fallback in LangGraph Query** ✅
**File**: `core_engine/reasoning/reasoning.py` → `_query_with_langgraph()` method

**Before**:
```python
except Exception as e:
    # Fallback to standard agent flow
    return self.agent.run(...)
```

**After**:
```python
except Exception as e:
    # Re-raise exception - no fallback, LangGraph is required
    raise RuntimeError(f"LangGraph query failed: {e}") from e
```

---

## Impact

### ✅ **What Changed**
- LangGraph is now **required** (not optional)
- No more feature flag `USE_LANGGRAPH`
- No fallback to standard agent flow
- System will fail fast if LangGraph can't initialize

### ⚠️ **What Stayed the Same**
- `query_streaming()` method still uses its own implementation (doesn't use LangGraph yet)
- Test file `test_langgraph_before_after.py` still references `USE_LANGGRAPH` (can be updated separately)

---

## Benefits

1. **Simpler Code**: No conditional logic, single code path
2. **Clearer Intent**: LangGraph is the architecture going forward
3. **Better Error Handling**: Fail fast if LangGraph can't initialize
4. **Easier Maintenance**: One code path to maintain

---

## Migration Notes

### Environment Variables
- `USE_LANGGRAPH=true` in `.env` is now **ignored** (can be removed)
- LangGraph is always enabled

### Error Handling
- If LangGraph fails to initialize → **RuntimeError** (system won't start)
- If LangGraph query fails → **RuntimeError** (no fallback)

### Testing
- All queries now go through LangGraph workflow
- Test file `test_langgraph_before_after.py` may need updates if you want to test baseline vs LangGraph

---

## Files Modified

1. **`core_engine/reasoning/reasoning.py`**
   - Removed `use_langgraph` feature flag
   - Made LangGraph initialization mandatory
   - Removed conditional routing
   - Removed fallback to standard agent flow

---

## Status

✅ **Complete**: LangGraph is now the only path for query processing

**Next Steps** (Optional):
- Update `test_langgraph_before_after.py` if needed
- Consider migrating `query_streaming()` to use LangGraph (future work)
- Remove `USE_LANGGRAPH=true` from `.env` (optional, doesn't hurt to leave it)
