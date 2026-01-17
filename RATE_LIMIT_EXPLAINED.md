# 🎯 Rate Limit Explanation: Batch Size vs Max Concurrent

## Quick Answer

**Both affect rate limits, but in different ways:**

1. **Batch Size** → Affects **TPM (Tokens Per Minute)** limits
2. **Max Concurrent** → Affects **RPM (Requests Per Minute)** limits

**In your case: Batch size 50 is the PRIMARY problem**, but max concurrent 20 makes it worse.

---

## Detailed Explanation

### 1. Batch Size (Affects TPM - Tokens Per Minute)

**What it does:**
- Controls how many chunks are sent in ONE API call
- Larger batch = more tokens per call

**Rate Limit Impact:**
- **Batch size 10**: ~10,000-20,000 tokens per call
- **Batch size 50**: ~50,000-100,000 tokens per call
- **5x more tokens** = Higher TPM usage

**OpenAI Limits:**
- GPT-4o: ~1,000,000 tokens per minute (TPM)
- With batch size 50: You can only make ~10-20 calls per minute
- With batch size 10: You can make ~50-100 calls per minute

**Example:**
```
Batch size 50: 1 call = 50,000 tokens → Can make ~20 calls/min
Batch size 10: 1 call = 10,000 tokens → Can make ~100 calls/min
```

---

### 2. Max Concurrent (Affects RPM - Requests Per Minute)

**What it does:**
- Controls how many API calls happen SIMULTANEOUSLY
- Higher concurrent = more requests at once

**Rate Limit Impact:**
- **Max concurrent 5**: 5 requests at once
- **Max concurrent 20**: 20 requests at once
- **4x more requests** = Higher RPM usage

**OpenAI Limits:**
- GPT-4o: ~500 requests per minute (RPM)
- With max concurrent 20: You use 20 requests immediately
- With max concurrent 10: You use 10 requests at a time

**Example:**
```
Max concurrent 20: Fires 20 requests at once → Uses 20/500 RPM
Max concurrent 10: Fires 10 requests at once → Uses 10/500 RPM
```

---

## Combined Effect (Your Case)

### Your Settings: Batch 50 + Concurrent 20

**What happens:**
1. **20 requests fire at once** (max concurrent 20)
2. **Each request has 50 chunks** (batch size 50)
3. **Total**: 20 × 50 = **1000 chunks simultaneously**
4. **Token usage**: 20 × 50,000 = **~1,000,000 tokens at once**
5. **Result**: **IMMEDIATE rate limit hit** ❌

**Why it fails:**
- Hits TPM limit (1M tokens at once)
- Hits RPM limit (20 requests at once)
- Rate limiter can't prevent because all 20 fire simultaneously

---

## Which One Affects More?

### In Your Case: **Batch Size 50 is the PRIMARY problem**

**Reason:**
- Batch size 50 creates **huge token usage** (50k-100k per call)
- This hits **TPM limits** immediately
- Even with max concurrent 5, batch size 50 would still cause issues

**But:**
- Max concurrent 20 **makes it worse** by firing all at once
- If you had batch size 10 + max concurrent 20, it would work better
- But batch size 50 + max concurrent 5 would still be problematic

---

## Rate Limit Priority

### Priority 1: Batch Size (TPM Limits)
- **More critical** for avoiding rate limits
- Larger batches = higher token usage = TPM limit hits
- **Recommendation**: Keep batch size 10-12

### Priority 2: Max Concurrent (RPM Limits)
- **Secondary** but still important
- Higher concurrency = more simultaneous requests = RPM limit hits
- **Recommendation**: Keep max concurrent 10-15

---

## Ideal Balance

### The Sweet Spot:

```bash
--batch-size 10        # Keeps token usage low (TPM safe)
--max-concurrent 12    # Keeps request count manageable (RPM safe)
```

**Why this works:**
- **Token usage**: 12 × 10,000 = 120,000 tokens at once (safe)
- **Request count**: 12 requests at once (safe)
- **Combined**: Well within both TPM and RPM limits

---

## Comparison Table

| Batch Size | Max Concurrent | TPM Usage | RPM Usage | Status |
|-----------|----------------|-----------|-----------|--------|
| 10 | 12 | 120k tokens | 12 requests | ✅ Safe |
| 10 | 20 | 200k tokens | 20 requests | ⚠️ Risky |
| 50 | 12 | 600k tokens | 12 requests | ⚠️ Risky |
| 50 | 20 | 1M tokens | 20 requests | ❌ Fails |

---

## Recommendations

### For Your 10 Files:
```bash
--batch-size 10 --max-concurrent 12
```
- **Why**: Balanced TPM and RPM usage
- **Safe**: Well within limits

### For Full Run (141 files):
```bash
--batch-size 10 --max-concurrent 15
```
- **Why**: Slightly higher concurrency for speed
- **Still safe**: Within limits

### If You Want Maximum Speed:
```bash
--batch-size 12 --max-concurrent 15
```
- **Why**: Slightly larger batches, higher concurrency
- **Monitor**: Watch for rate limits

---

## Key Takeaways

1. **Batch size affects TPM** (tokens per minute) - PRIMARY factor
2. **Max concurrent affects RPM** (requests per minute) - SECONDARY factor
3. **Both matter**, but batch size is more critical
4. **Your problem**: Batch size 50 is too large (hits TPM limits)
5. **Solution**: Reduce batch size to 10, keep max concurrent at 12

---

## Answer to Your Question

**Which one affects rate limits more?**

**Batch size** affects rate limits MORE because:
- It directly controls token usage (TPM limits)
- Larger batches = immediate TPM limit hits
- Even with low concurrency, large batches cause problems

**But max concurrent** also matters because:
- It controls simultaneous requests (RPM limits)
- High concurrency + large batches = double problem
- But high concurrency with small batches is usually fine

**In your case:**
- **Batch size 50** = PRIMARY problem (hits TPM limits)
- **Max concurrent 20** = Makes it worse (fires all at once)
- **Solution**: Reduce BOTH, but batch size is more critical

