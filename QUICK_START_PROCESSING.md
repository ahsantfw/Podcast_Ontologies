# 🚀 Quick Start: Processing All Transcripts

## Answer: Yes, but you need to specify the correct directory!

The command `python process_with_metrics.py --workspace default` **will process ALL `.txt` files** it finds, but it looks in a specific location by default.

## Default Location

By default, the script looks for transcripts in:
```
data/workspaces/default/transcripts/*.txt
```

## Your Transcripts Location

Your transcripts are in:
```
data/transcripts/*.txt
```

## Solution: Use the `--transcripts-dir` Flag

To process all your transcripts from `data/transcripts/`:

```bash
python process_with_metrics.py --workspace default --transcripts-dir data/transcripts
```

This will:
- ✅ Find ALL `.txt` files in `data/transcripts/` (and subdirectories)
- ✅ Process all 150+ transcripts
- ✅ Create KG and embeddings for all of them
- ✅ Track costs and performance
- ✅ Generate detailed reports

## What Gets Processed?

The script uses `glob="**/*.txt"` which means:
- ✅ All `.txt` files in the directory
- ✅ All `.txt` files in subdirectories (recursive)
- ✅ Automatically finds all transcripts

## Verify Before Processing

Check how many transcripts will be processed:

```bash
# Count transcripts
find data/transcripts -name "*.txt" -type f | wc -l

# List first 10
find data/transcripts -name "*.txt" -type f | head -10
```

## Full Command with All Options

```bash
python process_with_metrics.py \
  --workspace default \
  --transcripts-dir data/transcripts \
  --output-dir metrics/default
```

## Alternative: Move Transcripts

If you prefer, you can move transcripts to the default location:

```bash
# Create directory
mkdir -p data/workspaces/default/transcripts

# Move transcripts
mv data/transcripts/*.txt data/workspaces/default/transcripts/

# Then run without --transcripts-dir
python process_with_metrics.py --workspace default
```

## What Happens During Processing

1. **Loads all transcripts** from the directory
2. **Chunks them** into smaller pieces (2000 chars each)
3. **Extracts KG** (concepts, relationships, quotes) - **This is where rate limits matter!**
4. **Creates embeddings** for vector search
5. **Stores everything** in Neo4j (KG) and Qdrant (embeddings)
6. **Tracks costs** and performance
7. **Generates reports**

## Expected Time & Cost

For 150 transcripts:
- **Time**: 60-90 minutes (with rate limiting)
- **Cost**: $10-30 (depending on transcript length)
- **Rate Limits**: Automatically handled with retries

## Progress Tracking

You'll see:
```
📁 Step 1: Loading transcripts...
✅ Loaded 150 transcript(s)

✂️  Step 2: Chunking documents...
✅ Created 3,000 chunks

🧠 Step 4: Extracting knowledge graph...
Processing batch 1/600... ✅ Success
Processing batch 2/600... ⚠️ Rate limit, retrying in 60s...
Processing batch 2/600... ✅ Success (retry 1)
...
```

## After Processing

Check results:
- **KG Stats**: Neo4j database (concepts, relationships)
- **Cost Report**: `metrics/default/cost_data.json`
- **Performance**: `metrics/default/performance_data.json`
- **LangSmith Traces**: https://smith.langchain.com

## Quick Reference

```bash
# Process all transcripts from data/transcripts/
python process_with_metrics.py --workspace default --transcripts-dir data/transcripts

# Process with custom output directory
python process_with_metrics.py --workspace default --transcripts-dir data/transcripts --output-dir my_metrics

# Clear existing data and reprocess
python process_with_metrics.py --workspace default --transcripts-dir data/transcripts --clear
```

---

**Ready?** Run: `python process_with_metrics.py --workspace default --transcripts-dir data/transcripts` 🚀

