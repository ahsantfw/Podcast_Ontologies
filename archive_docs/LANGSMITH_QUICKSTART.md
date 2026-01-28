# 🚀 LangSmith Quick Start Guide

You've added LangSmith configuration to your `.env` file. Follow these steps to start using it!

## Step 1: Verify Setup ✅

Test that LangSmith is properly configured:

```bash
python test_langsmith.py
```

**Expected Output:**
```
✅ LangSmith is ENABLED
✅ Connected! Found X project(s)
✅ SETUP COMPLETE - LangSmith is ready to use!
```

If you see errors, check:
- `LANGCHAIN_TRACING_V2=true` in `.env`
- `LANGCHAIN_API_KEY` is set correctly
- API key is valid (get from https://smith.langchain.com)

## Step 2: Test Tracing (Optional) 🧪

The test script will ask if you want to create test traces. This verifies traces are being sent:

```bash
python test_langsmith.py
# When prompted, type 'y' to run trace test
```

Then check https://smith.langchain.com to see the test traces appear!

## Step 3: Run Ingestion with LangSmith 📊

Now run your ingestion pipeline. LangSmith will automatically trace everything:

```bash
# Process all transcripts with full observability
python process_with_metrics.py --workspace default

# Or with custom workspace
python process_with_metrics.py --workspace my_workspace
```

**What Gets Traced:**
- ✅ All LLM calls (KG extraction, embeddings)
- ✅ Token usage and costs
- ✅ Latency per operation
- ✅ Full execution traces
- ✅ Errors and retries

**You'll See:**
```
✅ LangSmith: Enabled (view traces at https://smith.langchain.com)
```

## Step 4: View Traces in LangSmith Dashboard 🔍

1. **Go to LangSmith**: https://smith.langchain.com
2. **Select your project**: (from `LANGCHAIN_PROJECT` in `.env`)
3. **View traces**:
   - Real-time traces appear as your code runs
   - Filter by date, tags, metadata
   - Click any trace to see full details

### What You Can Do in the Dashboard:

- **View Cost Breakdown**: See costs per model, per operation
- **Analyze Performance**: Latency, throughput, bottlenecks
- **Debug Issues**: Step through execution, see prompts/responses
- **Compare Runs**: A/B test different configurations
- **Set Alerts**: Get notified of high costs or errors

## Step 5: Explore Features 🎯

### Filter Traces

In LangSmith UI, filter by:
- **Tags**: `ingestion`, `pipeline`, `kg-extraction`, `embeddings`
- **Metadata**: `workspace`, `model`, `batch_size`
- **Date Range**: Last hour, day, week
- **Status**: Success, error, in-progress

### View Cost Analytics

1. Go to **Analytics** tab
2. See:
   - Total cost per day/week/month
   - Cost per model (GPT-4o, embeddings)
   - Cost per operation type
   - Cost trends over time

### Debug a Specific Run

1. Find a trace in the list
2. Click to open
3. See:
   - Full execution tree
   - Inputs/outputs at each step
   - Token usage per call
   - Latency breakdown
   - Errors (if any)

## Troubleshooting 🔧

### Traces Not Appearing?

1. **Check environment variables**:
   ```bash
   echo $LANGCHAIN_TRACING_V2  # Should be "true"
   echo $LANGCHAIN_API_KEY     # Should have your key
   ```

2. **Verify API key**:
   - Go to https://smith.langchain.com
   - Settings → API Keys
   - Make sure key is active

3. **Check project name**:
   ```bash
   echo $LANGCHAIN_PROJECT  # Should match your project
   ```

### High Overhead?

- LangSmith has minimal overhead (~1-2ms per trace)
- For very high volume, consider sampling
- Traces are sent asynchronously (non-blocking)

### Free Tier Limits?

- Free tier: 1,000 traces/month
- Paid plans start at $39/month
- Self-hosted option available

## Next Steps 🎯

1. ✅ **Verify setup** - Run `python test_langsmith.py`
2. ✅ **Run ingestion** - Process your transcripts
3. ✅ **View traces** - Check LangSmith dashboard
4. ✅ **Analyze costs** - Review cost breakdowns
5. ✅ **Optimize** - Use insights to improve pipeline

## Example: What a Trace Looks Like

When you run ingestion, you'll see traces like:

```
full_ingestion (chain)
├── load_transcripts (tool)
├── chunk_documents (tool)
├── extract_kg (chain)
│   ├── extract_batch_1 (llm) - GPT-4o
│   │   ├── Input: 2,000 tokens
│   │   ├── Output: 400 tokens
│   │   └── Cost: $0.005
│   ├── extract_batch_2 (llm) - GPT-4o
│   └── ...
├── ingest_qdrant (chain)
│   ├── embed_batch_1 (llm) - text-embedding-3-large
│   │   ├── Input: 1,000 tokens
│   │   └── Cost: $0.00013
│   └── ...
└── Total Cost: $X.XX
```

## Tips 💡

1. **Tag Everything**: Use tags for easy filtering (`workspace`, `operation`, `model`)
2. **Add Metadata**: Include context (episode_id, batch_size, etc.)
3. **Regular Reviews**: Check traces weekly to find optimizations
4. **Set Alerts**: Configure alerts for high costs or errors
5. **Compare Versions**: Tag runs with model/prompt versions

## Resources 📚

- **LangSmith Docs**: https://docs.smith.langchain.com
- **Dashboard**: https://smith.langchain.com
- **Setup Guide**: See `LANGSMITH_SETUP.md` for detailed docs

---

**Ready to go?** Run `python test_langsmith.py` to verify everything works! 🚀

