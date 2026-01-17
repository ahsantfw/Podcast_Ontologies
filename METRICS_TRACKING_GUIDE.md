# 📊 Cost & Performance Tracking Guide

This guide explains how to use the comprehensive cost and performance tracking system for ingestion operations.

## Overview

The metrics tracking system automatically tracks:
- **Cost**: OpenAI API token usage and costs for all LLM calls
- **Performance**: Time taken for each operation (loading, chunking, KG extraction, embeddings)
- **Throughput**: Items processed per second
- **Breakdown**: Costs and times by model, operation type, etc.

## Quick Start

### 1. Process Transcripts with Metrics

```bash
# Process all transcripts in default workspace
python process_with_metrics.py

# Process with custom workspace
python process_with_metrics.py --workspace my_workspace

# Process with custom transcripts directory
python process_with_metrics.py --transcripts-dir /path/to/transcripts

# Save metrics to custom directory
python process_with_metrics.py --output-dir /path/to/metrics
```

### 2. View Reports

The script automatically:
1. Prints a comprehensive report to the console
2. Saves detailed JSON files with all metrics
3. Saves a combined text report

Reports are saved to: `metrics/{workspace_id}/`

## What Gets Tracked

### Cost Tracking

- **Chat Completions** (KG extraction):
  - Input tokens
  - Output tokens
  - Cost per call
  - Model used
  - Duration

- **Embeddings** (Vector DB):
  - Input tokens
  - Cost per call
  - Batch size
  - Model used
  - Duration

### Performance Tracking

- **Load Transcripts**: Time to load all transcript files
- **Chunk Documents**: Time to chunk documents into segments
- **Initialize Schema**: Time to set up Neo4j schema
- **Extract KG**: Time to extract knowledge graph (with chunk count)
- **Ingest Qdrant**: Time to create embeddings and store in Qdrant

## Report Format

### Cost Report

```
💰 COST REPORT
================================================================================

📈 OVERALL STATISTICS:
  Total API Calls:     150
  Total Input Tokens:  2.5M
  Total Output Tokens: 500K
  Total Cost:          $12.50
  Total Duration:      45.2m
  Calls per Second:    0.06

📊 BY MODEL:
  gpt-4o:
    Calls:      100
    Input:      2.0M
    Output:     400K
    Cost:       $10.00
    Duration:   30.5m

  text-embedding-3-large:
    Calls:      50
    Input:      500K
    Output:     0
    Cost:       $2.50
    Duration:   14.7m

📊 BY OPERATION:
  CHAT:
    Calls:      100
    Input:      2.0M
    Output:     400K
    Cost:       $10.00
    Duration:   30.5m

  EMBEDDING:
    Calls:      50
    Input:      500K
    Output:     0
    Cost:       $2.50
    Duration:   14.7m
```

### Performance Report

```
⚡ PERFORMANCE REPORT
================================================================================

📈 OVERALL STATISTICS:
  Total Operations:      5
  Total Duration:         45.2m
  Total Items Processed:  1,500
  Overall Throughput:     0.55 items/sec

📊 BY OPERATION:
  load_transcripts:
    Count:         1
    Total Time:    0.5m
    Items:         10
    Avg Duration:  0.5m
    Avg Throughput: 0.33 items/sec

  extract_kg:
    Count:         1
    Total Time:    30.5m
    Items:         1,000
    Avg Duration:  30.5m
    Avg Throughput: 0.55 items/sec
```

## Saved Files

After processing, the following files are saved:

1. **cost_data.json**: Complete cost tracking data
2. **performance_data.json**: Complete performance metrics
3. **combined_report_{timestamp}.txt**: Human-readable combined report
4. **cost_report_{timestamp}.json**: Detailed cost data with all API calls
5. **performance_report_{timestamp}.json**: Detailed performance data

## Programmatic Usage

### Track Costs Only

```python
from core_engine.metrics import get_cost_tracker, reset_cost_tracker
from core_engine.metrics.reporting import print_cost_report

# Reset for fresh tracking
reset_cost_tracker()

# Your code that makes OpenAI API calls...

# Get summary
summary = get_cost_tracker().get_summary()
print_cost_report(summary)
```

### Track Performance Only

```python
from core_engine.metrics import get_performance_tracker, reset_performance_tracker
from core_engine.metrics.reporting import print_performance_report

# Reset for fresh tracking
reset_performance_tracker()

tracker = get_performance_tracker()

# Track an operation
op_id = tracker.start_operation("my_operation")
# ... do work ...
tracker.finish_operation(op_id, items_processed=100)

# Get summary
summary = tracker.get_summary()
print_performance_report(summary)
```

### Track Both

```python
from core_engine.metrics import (
    get_cost_tracker,
    get_performance_tracker,
    reset_cost_tracker,
    reset_performance_tracker,
)
from core_engine.metrics.reporting import print_combined_report, save_reports

# Reset both
reset_cost_tracker()
reset_performance_tracker()

# Your processing code...

# Print and save reports
print_combined_report()
save_reports(Path("metrics/my_workspace"))
```

## Cost Estimation

Before processing, you can estimate costs:

### GPT-4o Pricing (as of 2024)
- Input: $2.50 per 1M tokens
- Output: $10.00 per 1M tokens

### Text Embedding 3 Large
- Input: $0.13 per 1M tokens

### Example Calculation

For 1,000 chunks:
- **KG Extraction**: ~2,000 tokens input per chunk = 2M tokens
  - Cost: 2M × $2.50 / 1M = **$5.00**
  - Output: ~400 tokens per chunk = 400K tokens
  - Cost: 400K × $10.00 / 1M = **$4.00**
  - **Total KG: $9.00**

- **Embeddings**: ~1,000 tokens per chunk = 1M tokens
  - Cost: 1M × $0.13 / 1M = **$0.13**

- **Total: ~$9.13 for 1,000 chunks**

## Tips

1. **Start Small**: Test with a few transcripts first to estimate costs
2. **Monitor Progress**: The script prints progress as it runs
3. **Save Reports**: Reports are automatically saved for later analysis
4. **Compare Runs**: Use different output directories to compare different processing runs
5. **Batch Size**: Adjust `batch_size` in KG extraction to balance cost vs. speed

## Troubleshooting

### No costs tracked

- Ensure OpenAI API calls are being made
- Check that the client is patched (should happen automatically)
- Verify `OPENAI_API_KEY` is set

### Performance metrics missing

- Ensure operations are started with `start_operation()`
- Operations must be finished with `finish_operation()`
- Check that the performance tracker is initialized

### Reports not saving

- Check that the output directory is writable
- Ensure the directory path is valid
- Check disk space

## Next Steps

After processing with metrics:

1. Review the cost report to understand API usage
2. Check performance bottlenecks
3. Optimize batch sizes based on throughput
4. Estimate costs for full corpus processing
5. Use insights to optimize the ingestion pipeline

