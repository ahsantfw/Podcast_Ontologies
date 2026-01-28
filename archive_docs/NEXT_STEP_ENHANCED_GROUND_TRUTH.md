# Next Step: Enhanced Ground Truth

## ✅ Completed So Far

1. ✅ **Intelligent Query Planner** - Context analysis, domain relevance, query decomposition
2. ✅ **Reranking (RRF, MMR, Hybrid)** - Configurable reranking strategies
3. ✅ **KG Query Optimizer** - Entity linking, multi-hop queries, cross-episode queries
4. ✅ **Query Expansion** - Intelligent query variation generation

---

## 🎯 Next Step: Enhanced Ground Truth

**Priority**: 🟡 **MEDIUM** (Improves UX)

**Goal**: Better source extraction, timestamps, speaker resolution, and source confidence scores

**Why**: Users want to see exactly where information came from (episode, timestamp, speaker) so they can verify and navigate to specific content.

---

## Current Issues

### 1. Episode Name Formatting ⚠️
**Current**: Episode IDs like `"143_TYLER_COWEN_PART_1"` displayed as-is
**Problem**: Not user-friendly, hard to read
**Solution**: Format as `"Tyler Cowen (Episode 143)"` or `"Tyler Cowen - Part 1"`

### 2. Timestamp Extraction ⚠️
**Current**: Timestamps may be missing or not formatted
**Problem**: Users can't navigate to specific moments
**Solution**: Extract timestamps from metadata, format as `"15:30"` or `"00:15:30"`

### 3. Speaker Resolution ⚠️
**Current**: Speaker names may be generic (`"Speaker 1"`, `"Unknown"`)
**Problem**: Users don't know who said what
**Solution**: Resolve speaker names from episode metadata or KG relationships

### 4. Source Confidence Scores ⚠️
**Current**: No confidence scores
**Problem**: Users don't know how reliable sources are
**Solution**: Calculate confidence based on relevance score, number of sources, KG relationship strength

---

## Implementation Plan

### Step 1: Enhanced Source Extraction
**File**: `core_engine/reasoning/agent.py` → `_extract_sources()`

**Improvements**:
1. **Episode Name Formatting**
   - Parse episode_id: `"143_TYLER_COWEN_PART_1"` → `"Tyler Cowen (Episode 143)"`
   - Handle edge cases (no number, no name, etc.)
   - Extract episode title if available in metadata

2. **Timestamp Extraction**
   - Extract from `metadata.timestamp`
   - Format: `"00:15:30"` → `"15:30"` (if < 1 hour)
   - Handle missing timestamps gracefully

3. **Speaker Resolution**
   - Use `metadata.speaker` if available
   - Fallback to episode name if speaker is generic
   - Query KG for speaker relationships if needed

4. **Source Confidence Scores**
   - Calculate based on:
     - Relevance score (from RAG/KG)
     - Number of sources mentioning it
     - KG relationship strength
   - Display in UI (optional)

---

### Step 2: Source Formatting
**Improvements**:
- Consistent format: `"Speaker Name (Episode: Episode Name) at 15:30"`
- Link timestamps (if UI supports it)
- Group sources by episode
- Sort by relevance/confidence

---

### Step 3: Integration
**Files to Modify**:
- `core_engine/reasoning/agent.py` - `_extract_sources()`
- `core_engine/reasoning/langgraph_nodes.py` - Pass source metadata
- Frontend (if needed) - Display formatted sources

---

## Expected Improvements

### Before:
- Episode: `"143_TYLER_COWEN_PART_1"`
- Speaker: `"Unknown"`
- Timestamp: Missing
- Confidence: N/A

### After:
- Episode: `"Tyler Cowen (Episode 143)"`
- Speaker: `"Tyler Cowen"`
- Timestamp: `"15:30"`
- Confidence: `0.85` (high)

---

## Benefits

1. **Better UX**: Users can easily identify sources
2. **Trust**: Users can verify information
3. **Navigation**: Users can jump to specific timestamps
4. **Transparency**: Clear source attribution

---

## Implementation Details

### Episode Name Formatting
```python
def format_episode_name(episode_id: str) -> str:
    """Format episode ID to readable name."""
    # "143_TYLER_COWEN_PART_1" → "Tyler Cowen (Episode 143)"
    parts = episode_id.split("_")
    if len(parts) >= 2:
        number = parts[0]
        name_parts = [p for p in parts[1:] if p.upper() not in ["PART", "1", "2", "3"]]
        name = " ".join(name_parts).title()
        return f"{name} (Episode {number})"
    return episode_id.replace("_", " ")
```

### Timestamp Formatting
```python
def format_timestamp(timestamp: str) -> str:
    """Format timestamp to readable format."""
    # "00:15:30" → "15:30"
    # "01:30:45" → "1:30:45"
    if not timestamp:
        return ""
    
    parts = timestamp.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        if int(hours) == 0:
            return f"{minutes}:{seconds}"
        return f"{int(hours)}:{minutes}:{seconds}"
    return timestamp
```

### Speaker Resolution
```python
def resolve_speaker(metadata: Dict[str, Any], episode_id: str) -> str:
    """Resolve speaker name from metadata or episode."""
    speaker = metadata.get("speaker", "")
    
    # Use metadata speaker if available and not generic
    if speaker and speaker not in ["Unknown", "Speaker 1", "Speaker 2"]:
        return speaker
    
    # Fallback to episode name
    episode_name = format_episode_name(episode_id)
    return episode_name.split(" (")[0]  # Extract name part
```

### Confidence Score Calculation
```python
def calculate_confidence(result: Dict[str, Any], all_results: List[Dict[str, Any]]) -> float:
    """Calculate source confidence score."""
    score = result.get("score", 0.5)
    
    # Boost if mentioned in multiple sources
    text = result.get("text", "")
    mentions = sum(1 for r in all_results if text[:50] in r.get("text", ""))
    if mentions > 1:
        score += 0.1
    
    # Boost if from KG (structured knowledge)
    if result.get("source_type") == "kg":
        score += 0.1
    
    return min(score, 1.0)
```

---

## Files to Modify

1. **`core_engine/reasoning/agent.py`**
   - Update `_extract_sources()` method
   - Add helper functions for formatting
   - Add confidence calculation

2. **`core_engine/reasoning/langgraph_nodes.py`** (if needed)
   - Pass source metadata through workflow

---

## Testing

### Test Cases:
1. Episode name formatting: `"143_TYLER_COWEN_PART_1"` → `"Tyler Cowen (Episode 143)"`
2. Timestamp formatting: `"00:15:30"` → `"15:30"`
3. Speaker resolution: `"Unknown"` → `"Tyler Cowen"`
4. Confidence scores: Calculate and display

---

## Status

🔄 **Next Step**: Enhanced Ground Truth Implementation

**Ready to start**: Enhanced source extraction improvements

---

## Timeline

**Estimated**: 2-3 days
- Day 1: Implement formatting functions
- Day 2: Update `_extract_sources()`
- Day 3: Testing and refinement

---

## Success Criteria

✅ **After Implementation**:
- Episode names formatted consistently
- Timestamps extracted and formatted
- Speaker names resolved correctly
- Confidence scores calculated (optional)
- Sources displayed clearly in UI
