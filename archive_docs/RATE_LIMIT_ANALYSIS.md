# 🚨 Rate Limit Analysis & Ideal Settings

## Your Current Run Analysis

### Configuration Used:
```bash
--max-concurrent 20
--batch-size 50
```

### Results:
- **Files**: 10 transcripts
- **Chunks**: 778 total
- **Batches**: 16 (778 ÷ 50)
- **Status**: ❌ **STUCK - Massive rate limit errors**

### Problems Identified:

1. **Batch Size Too Large (50)**:
   - Each API call processes 50 chunks = **HUGE prompts**
   - Very high token usage per call
   - Longer processing time per call
   - Higher rate limit risk

2. **Concurrency Too High (20)**:
   - 20 concurrent calls × 50 chunks = **1000 chunks simultaneously**
   - Immediate rate limit hits
   - All 20 requests fire at once before rate limiter can prevent

3. **Rate Limit Errors**:
   - Almost every API call gets 429 error
   - Retries with 50+ second delays
   - Only 3/16 batches completed after 3+ minutes
   - Processing essentially stuck

---

## Ideal Settings

### Recommended Configuration:

```bash
uv run process_with_metrics_async.py \
  --workspace default \
  --transcripts-dir data/transcripts_10 \
  --max-concurrent 12 \
  --batch-size 10
```

### Why These Settings:

#### Batch Size: 10 ✅
- **Smaller prompts**: Faster API responses
- **Lower token usage**: Reduces rate limit risk
- **Better error handling**: If one batch fails, less work lost
- **Optimal balance**: Not too small (too many calls) or too large (rate limits)

#### Max Concurrent: 12 ✅
- **Balanced speed**: Good parallelization without overwhelming API
- **Rate limit safe**: Allows rate limiter to work effectively
- **12 × 10 = 120 chunks simultaneously**: Manageable load

---

## Settings Comparison

| Setting | Batch Size | Max Concurrent | Status | Time (10 files) |
|---------|-----------|----------------|--------|-----------------|
| **Your Current** | 50 | 20 | ❌ Stuck | N/A (rate limited) |
| **Recommended** | 10 | 12 | ✅ Good | 5-10 min |
| **Conservative** | 10 | 8 | ✅ Very Safe | 8-12 min |
| **Aggressive** | 12 | 15 | ⚠️ Risky | 4-8 min |

---

## Why Batch Size 50 Failed

### Token Usage:
- **Batch size 50**: ~50,000-100,000 tokens per call
- **Batch size 10**: ~10,000-20,000 tokens per call
- **5x difference**: Much higher rate limit risk

### Concurrent Load:
- **20 × 50 = 1000 chunks**: Massive simultaneous load
- **12 × 10 = 120 chunks**: Manageable load
- **8x difference**: Much safer

### API Response Time:
- **Batch size 50**: 30-60 seconds per call
- **Batch size 10**: 5-15 seconds per call
- **4x faster**: Better throughput despite more calls

---

## Recommended Settings by Scale

### Small (10-50 files):
```bash
--max-concurrent 12 --batch-size 10
```
- **Time**: 5-15 minutes
- **Rate limit risk**: Low

### Medium (50-150 files):
```bash
--max-concurrent 15 --batch-size 10
```
- **Time**: 15-45 minutes
- **Rate limit risk**: Medium

### Large (150+ files):
```bash
--max-concurrent 15 --batch-size 12
```
- **Time**: 1-3 hours
- **Rate limit risk**: Medium-High (monitor closely)

---

## How to Fix Current Run

### Option 1: Stop and Restart (Recommended)
```bash
# Press Ctrl+C to stop current run
# Then restart with correct settings:
uv run process_with_metrics_async.py \
  --workspace default \
  --transcripts-dir data/transcripts_10 \
  --max-concurrent 12 \
  --batch-size 10
```

### Option 2: Wait It Out
- Current run will eventually complete
- But will take 30-60+ minutes due to rate limit delays
- Not recommended

---

## Expected Performance with Ideal Settings

### For 10 Files (778 chunks):
- **Batches**: 78 (778 ÷ 10)
- **Concurrent**: 12
- **Time per batch**: ~5-10 seconds
- **Total time**: **5-10 minutes** ✅

### For 141 Files (~8,834 chunks):
- **Batches**: ~884 (8,834 ÷ 10)
- **Concurrent**: 12-15
- **Time per batch**: ~5-10 seconds
- **Total time**: **1-2 hours** ✅

---

## Key Takeaways

1. **Batch size 50 is TOO LARGE** ❌
   - Causes massive rate limit issues
   - Use 10-12 instead

2. **Max concurrent 20 is TOO HIGH** ❌
   - Fires too many requests at once
   - Use 10-15 instead

3. **Ideal Settings**: `--max-concurrent 12 --batch-size 10` ✅
   - Balanced speed and safety
   - Minimal rate limit issues
   - Best overall performance

4. **Monitor Rate Limits**:
   - If you see many 429 errors: Reduce concurrency
   - If processing is slow: Increase batch size slightly (12-15)

---

## Next Steps

1. **Stop current run** (Ctrl+C)
2. **Restart with recommended settings**:
   ```bash
   uv run process_with_metrics_async.py \
     --workspace default \
     --transcripts-dir data/transcripts_10 \
     --max-concurrent 12 \
     --batch-size 10
   ```
3. **Monitor progress**: Should see steady progress without rate limits
4. **For full run (141 files)**: Use same settings, expect 1-2 hours

