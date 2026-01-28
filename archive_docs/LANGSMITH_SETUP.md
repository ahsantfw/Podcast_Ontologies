# 🔍 LangSmith Observability Setup Guide

LangSmith provides comprehensive observability for LLM applications, including automatic tracing, cost tracking, performance monitoring, and debugging tools.

## Why LangSmith?

### Advantages Over Custom Tracking

1. **Automatic Tracing**: No manual instrumentation needed for LangChain components
2. **Rich Dashboards**: Visual interface for exploring traces, costs, and performance
3. **Debugging Tools**: Step-through execution, prompt inspection, error analysis
4. **Evaluation Framework**: Built-in tools for testing and comparing model versions
5. **Production Ready**: Used by thousands of production LLM applications
6. **OpenTelemetry Support**: Can integrate with existing observability stacks

### What It Tracks

- ✅ **All LLM calls** (automatic for LangChain components)
- ✅ **Token usage** (input/output) with cost calculation
- ✅ **Latency** (per call, per chain, per operation)
- ✅ **Errors and retries**
- ✅ **Prompt versions** and A/B testing
- ✅ **Custom metadata** and tags
- ✅ **Feedback** and evaluation scores

## Setup

### 1. Install LangSmith

```bash
pip install langsmith
```

### 2. Get API Key

1. Sign up at https://smith.langchain.com
2. Go to Settings → API Keys
3. Create a new API key
4. Copy the key

### 3. Configure Environment

Add to your `.env` file:

```bash
# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-api-key-here
LANGCHAIN_PROJECT=ontology-ingestion
```

Or set in code:

```python
from core_engine.metrics.langsmith_integration import setup_langsmith

setup_langsmith(
    api_key="your-api-key",
    project="ontology-ingestion"
)
```

### 4. Verify Setup

```python
from core_engine.metrics.langsmith_integration import is_langsmith_enabled

if is_langsmith_enabled():
    print("✅ LangSmith is enabled!")
else:
    print("❌ LangSmith not configured")
```

## Usage

### Automatic Tracing (LangChain Components)

LangSmith automatically traces LangChain components. Just use them normally:

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# This is automatically traced!
llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_template("Extract concepts from: {text}")
chain = prompt | llm

result = chain.invoke({"text": "transcript text"})
# View trace at: https://smith.langchain.com
```

### Manual Tracing (Custom Code)

For non-LangChain code, use decorators or context managers:

```python
from core_engine.metrics.langsmith_integration import (
    trace_operation,
    langsmith_run
)

# Option 1: Decorator
@trace_operation(
    "extract_kg",
    metadata={"model": "gpt-4o", "workspace": "default"},
    tags=["kg-extraction"]
)
def extract_kg(chunks):
    # Your extraction code
    return results

# Option 2: Context Manager
with langsmith_run(
    "process_episode",
    inputs={"episode_id": "001"},
    metadata={"workspace": "default"},
    tags=["ingestion"]
):
    # Your processing code
    process_transcript(episode_id)
```

### Integration with Existing Code

#### KG Extraction

```python
from core_engine.kg.extractor import KGExtractor
from core_engine.metrics.langsmith_integration import trace_operation

@trace_operation("kg_extraction", tags=["kg", "ingestion"])
def extract_with_tracing(chunks, workspace_id="default"):
    extractor = KGExtractor(model="gpt-4o", workspace_id=workspace_id)
    return extractor.extract_from_chunks(chunks)
```

#### Embeddings

```python
from openai import OpenAI
from core_engine.metrics.langsmith_integration import trace_operation

@trace_operation("create_embeddings", tags=["embeddings", "ingestion"])
def embed_with_tracing(texts, model="text-embedding-3-large"):
    client = OpenAI()
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]
```

#### Full Ingestion Pipeline

```python
from core_engine.metrics.langsmith_integration import langsmith_run

def process_with_langsmith(transcripts_dir, workspace_id="default"):
    with langsmith_run(
        "full_ingestion",
        inputs={"workspace": workspace_id, "transcript_count": len(transcripts)},
        tags=["ingestion", "pipeline"]
    ):
        # Load transcripts
        docs = load_transcripts(transcripts_dir, workspace_id=workspace_id)
        
        # Chunk
        chunks = chunk_documents(docs)
        
        # Extract KG (automatically traced if using LangChain)
        kg_results = extract_kg_from_chunks(chunks, workspace_id=workspace_id)
        
        # Create embeddings (manually traced)
        embeddings = create_embeddings(chunks)
        
        return kg_results, embeddings
```

## Viewing Traces

### Web UI

1. Go to https://smith.langchain.com
2. Select your project
3. View traces in real-time or filter by:
   - Date range
   - Tags
   - Metadata
   - Errors

### Programmatic Access

```python
from core_engine.metrics.langsmith_integration import get_langsmith_client

client = get_langsmith_client()
if client:
    # List recent runs
    runs = client.list_runs(project_name="ontology-ingestion", limit=10)
    for run in runs:
        print(f"Run: {run.name}, Cost: ${run.total_cost}, Duration: {run.latency}s")
```

## Cost Tracking

LangSmith automatically tracks costs for:
- OpenAI API calls
- Token usage (input/output)
- Model-specific pricing

View costs in:
- **Dashboard**: Total cost per project, per day, per model
- **Traces**: Cost per individual run
- **Analytics**: Cost trends, cost per operation type

## Performance Monitoring

Track:
- **Latency**: Per operation, per model, per workspace
- **Throughput**: Operations per second
- **Error Rates**: Failed calls, retries
- **Token Usage**: Input/output tokens, trends

## Comparison: LangSmith vs Custom Tracker

| Feature | LangSmith | Custom Tracker |
|---------|-----------|----------------|
| **Automatic Tracing** | ✅ Yes (LangChain) | ❌ Manual |
| **Dashboards** | ✅ Rich web UI | ❌ JSON files |
| **Cost Tracking** | ✅ Automatic | ✅ Manual |
| **Debugging** | ✅ Step-through | ❌ Logs only |
| **Evaluation** | ✅ Built-in | ❌ Manual |
| **Self-Hosting** | ✅ Available | ✅ Always |
| **Custom Metrics** | ⚠️ Limited | ✅ Full control |
| **Offline** | ❌ Requires API | ✅ Works offline |

## Recommended Approach: Use Both!

### LangSmith for:
- **Development**: Debugging, prompt iteration, testing
- **Production Monitoring**: Real-time dashboards, alerts
- **Evaluation**: A/B testing, quality metrics
- **Automatic Tracing**: LangChain components

### Custom Tracker for:
- **Detailed Cost Analysis**: Per-chunk, per-episode breakdowns
- **Offline Processing**: When API access is limited
- **Custom Metrics**: Workspace-specific, ingestion-specific
- **Detailed Reports**: JSON exports for analysis

## Example: Combined Usage

```python
from core_engine.metrics import (
    get_cost_tracker,
    get_performance_tracker,
    reset_cost_tracker,
    reset_performance_tracker,
)
from core_engine.metrics.langsmith_integration import langsmith_run
from core_engine.metrics.reporting import print_combined_report

def process_with_full_observability(transcripts_dir, workspace_id):
    # Reset custom trackers
    reset_cost_tracker()
    reset_performance_tracker()
    
    # LangSmith automatically traces (if enabled)
    with langsmith_run(
        "full_ingestion",
        inputs={"workspace": workspace_id},
        tags=["ingestion"]
    ):
        # Custom trackers for detailed metrics
        perf_tracker = get_performance_tracker()
        
        op_id = perf_tracker.start_operation("extract_kg")
        kg_results = extract_kg_from_chunks(chunks, workspace_id=workspace_id)
        perf_tracker.finish_operation(op_id, items_processed=len(chunks))
        
        # ... rest of processing
    
    # Print custom reports
    print_combined_report()
    
    # LangSmith traces available in web UI
    print("View traces at: https://smith.langchain.com")
```

## Best Practices

1. **Tag Everything**: Use tags for filtering (workspace, operation type, model version)
2. **Add Metadata**: Include relevant context (episode_id, batch_size, etc.)
3. **Set Up Alerts**: Configure alerts for high costs or errors
4. **Regular Reviews**: Review traces weekly to identify optimization opportunities
5. **Version Control**: Tag runs with model/prompt versions for comparison
6. **Feedback Loop**: Log feedback on run quality for continuous improvement

## Troubleshooting

### Traces Not Appearing

1. Check environment variables are set:
   ```bash
   echo $LANGCHAIN_TRACING_V2  # Should be "true"
   echo $LANGCHAIN_API_KEY     # Should have your key
   ```

2. Verify API key is valid:
   ```python
   from langsmith import Client
   client = Client()
   print(client.list_projects())  # Should list your projects
   ```

3. Check project name matches:
   ```bash
   echo $LANGCHAIN_PROJECT  # Should match your project name
   ```

### High Overhead

- LangSmith has minimal overhead (~1-2ms per trace)
- For high-volume, consider sampling (trace 10% of runs)
- Use async tracing for non-blocking operations

### Cost Concerns

- LangSmith free tier: 1,000 traces/month
- Paid plans start at $39/month
- Self-hosted option available for unlimited traces

## Next Steps

1. **Set up LangSmith** (5 minutes)
2. **Add tracing to ingestion pipeline** (15 minutes)
3. **View first traces** in web UI
4. **Set up dashboards** for monitoring
5. **Configure alerts** for cost/errors
6. **Integrate with custom tracker** for detailed analysis

## Resources

- **LangSmith Docs**: https://docs.smith.langchain.com
- **LangSmith Pricing**: https://www.langchain.com/langsmith/pricing
- **OpenTelemetry Integration**: https://blog.langchain.com/end-to-end-opentelemetry-langsmith
- **Self-Hosting Guide**: https://docs.langchain.com/langsmith/observability-stack

