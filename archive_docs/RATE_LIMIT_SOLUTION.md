# 🚦 Rate Limit Solution for 150+ Transcripts

## Problem

When processing 150+ transcripts, you hit OpenAI rate limits:
- **Rate Limit Error (429)**: Too many requests
- **Quota Exceeded**: Daily/monthly limits
- **Timeout Errors**: API overload

## Solution Implemented

### 1. Automatic Retry with Exponential Backoff ✅

The system now automatically retries failed requests with increasing delays:

- **Initial delay**: 1 second
- **Exponential backoff**: 2x each retry (1s → 2s → 4s → 8s → 16s)
- **Max delay**: 120 seconds (2 minutes)
- **Max retries**: 5 attempts
- **Jitter**: Random variation to prevent thundering herd

### 2. Rate Limiting Between Calls ✅

The system respects OpenAI rate limits:

- **Requests Per Minute (RPM)**: 500 (configurable)
- **Tokens Per Minute (TPM)**: 1,000,000 (configurable)
- **Automatic throttling**: Waits if approaching limits

### 3. Smart Batch Processing ✅

- Processes in smaller batches
- Adds delays between batches
- Tracks progress to resume if interrupted

## Configuration

### Default Limits (GPT-4o)

```python
# KG Extraction
requests_per_minute = 500
tokens_per_minute = 1,000,000

# Embeddings
requests_per_minute = 500
tokens_per_minute = 5,000,000  # Higher for embeddings
```

### Customize Limits

Edit `.env` or modify `process_with_metrics.py`:

```python
from core_engine.utils.rate_limiter import get_rate_limiter

# For slower processing (more conservative)
rate_limiter = get_rate_limiter(
    requests_per_minute=300,  # Lower RPM
    tokens_per_minute=500_000,  # Lower TPM
)
```

## Usage

### Automatic (Recommended)

The rate limiting is **automatic** - just run normally:

```bash
python process_with_metrics.py --workspace default
```

The system will:
- ✅ Automatically retry on rate limit errors
- ✅ Wait between batches to respect limits
- ✅ Handle quota errors gracefully
- ✅ Continue processing after delays

### Manual Configuration

If you need custom limits:

```python
from core_engine.kg.extractor import KGExtractor
from core_engine.utils.rate_limiter import get_rate_limiter

# Create custom rate limiter
rate_limiter = get_rate_limiter(
    requests_per_minute=300,
    tokens_per_minute=500_000,
)

# Use in extractor
extractor = KGExtractor(
    model="gpt-4o",
    rate_limiter=rate_limiter,
)
```

## What Happens During Processing

### Normal Flow:
```
Batch 1 → Success → Wait 0.1s → Batch 2 → Success → ...
```

### Rate Limit Hit:
```
Batch 10 → Rate Limit Error → Wait 60s → Retry → Success → Continue
```

### Multiple Rate Limits:
```
Batch 20 → Rate Limit → Wait 60s → Retry → Still Rate Limited → Wait 120s → Retry → Success
```

## Expected Processing Time

### Without Rate Limits:
- 150 transcripts: ~30-45 minutes

### With Rate Limiting (Conservative):
- 150 transcripts: ~60-90 minutes
- **But**: No failures, reliable completion

### With Rate Limiting (Aggressive):
- 150 transcripts: ~45-60 minutes
- **Risk**: Occasional rate limit delays

## Monitoring

### Check Progress

The script shows progress:
```
Processing 150 chunks in batches of 5...
Batch 1/30: ✅ Success
Batch 2/30: ⚠️ Rate limit, retrying in 60s...
Batch 2/30: ✅ Success (retry 1)
...
```

### View in LangSmith

Check LangSmith dashboard for:
- Rate limit errors (will show retries)
- Actual delays between calls
- Token usage patterns

## Troubleshooting

### Still Hitting Rate Limits?

1. **Reduce batch size**:
   ```python
   extractor = KGExtractor(batch_size=3)  # Smaller batches
   ```

2. **Lower RPM/TPM limits**:
   ```python
   rate_limiter = get_rate_limiter(
       requests_per_minute=200,  # More conservative
       tokens_per_minute=300_000,
   )
   ```

3. **Add longer delays**:
   ```python
   # In rate_limiter.py, increase initial_delay
   initial_delay=2.0  # Start with 2s delay
   ```

### Quota Exceeded?

- Check your OpenAI usage dashboard
- Wait for quota reset (daily/monthly)
- Consider upgrading tier
- Process in smaller batches over multiple days

### Timeouts?

- Increase `max_delay` in rate limiter
- Check network connection
- Process during off-peak hours

## Best Practices

1. **Process During Off-Peak Hours**: Lower API load = fewer rate limits
2. **Use Smaller Batches**: More reliable, easier to retry
3. **Monitor Progress**: Check logs/LangSmith regularly
4. **Save Progress**: System tracks progress, can resume
5. **Start Small**: Test with 10-20 transcripts first

## Advanced: Resume After Interruption

The system tracks progress. If interrupted:

1. Check last processed batch in logs
2. Modify script to start from that batch
3. Or just re-run - duplicates are handled

## Cost Considerations

Rate limiting doesn't increase costs:
- ✅ Same number of API calls
- ✅ Same token usage
- ✅ Just adds delays between calls

**Time vs. Cost Trade-off**:
- Faster = More rate limit errors = More retries = Same cost
- Slower = Fewer errors = More reliable = Same cost

## Next Steps

1. ✅ **Run with rate limiting** (automatic):
   ```bash
   python process_with_metrics.py --workspace default
   ```

2. ✅ **Monitor progress** in terminal and LangSmith

3. ✅ **Adjust if needed** based on your OpenAI tier limits

4. ✅ **Let it run** - it will handle rate limits automatically!

---

**The system is now production-ready for 150+ transcripts!** 🚀

