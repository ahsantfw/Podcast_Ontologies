# Logging & Observability Plan (Pre-Implementation)

Purpose: Define how we will log before coding begins. No code here.

## Goals
- Structured, machine-parseable logs for all services.
- Correlate requests, jobs, and graph/vector operations with run IDs and workspace IDs.
- Minimal overhead; plain file/console (no Docker/K8s assumed).

## What to log
- **Request/Job metadata**: request_id/run_id, workspace_id, user/context, command.
- **Processing stages**: ingest, chunk, embed, extract, build_graph, index_vectors, hybrid_query, export.
- **Performance**: latency per stage, counts (nodes/edges/evidence), vector hits, cache hits.
- **Quality**: confidence summaries, low-confidence counts, review-queue size.
- **Errors**: full stack traces, payload summaries (never secrets).

## Where to log
- Console + rotating file logs per service/module (backend, core_engine CLI).
- Separate files per run for batch jobs (ingest/extract/build).

## Format
- JSON lines: timestamp, level, logger, message, context dict.
- Levels: DEBUG (dev), INFO (runtime), WARN, ERROR.

## Correlation & IDs
- request_id/run_id generated at entrypoints (CLI, API).
- propagate workspace_id, episode_id, job_id through calls.

## Redaction
- Never log credentials, API keys, raw embeddings; truncate long texts and store hashes.

## Files (to be implemented later)
- `configs/logging.yaml`: shared logging config (console + rotating files).
- `core_engine/logging.py`: helper to init structured logger with request_id/run_id/workspace_id; progress logging helper.
- `backend/config/logging.py`: FastAPI logging setup, middleware to inject IDs.
- `scripts/logging_demo.md`: quick examples for devs (optional).

## Metrics (later)
- Counters/latency via simple stdout/CSV until a metrics sink is chosen; add dashboard definitions when sink is decided.

