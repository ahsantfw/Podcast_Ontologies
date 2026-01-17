# 🧠 Knowledge Graph Extraction Plan

## Overview
Extract structured knowledge (concepts, relationships, quotes) from chunked transcripts and store in Neo4j with full provenance tracking.

---

## 📋 Requirements (from Project Plan)

### Required Concept Types
- **Concept** - Abstract ideas, theories, frameworks
- **Practice** - Actions, methods, techniques
- **CognitiveState/MindState** - Mental states, emotions, cognitive patterns
- **BehavioralPattern** - Recurring behaviors, habits
- **Principle/Framework** - Guiding principles, conceptual frameworks
- **Outcome/Effect** - Results, consequences, effects
- **Causality** - Cause-effect relationships (as concepts)
- **Person** - Named individuals
- **Place** - Locations, geographical entities
- **Organization** - Companies, institutions, groups
- **Event** - Specific occurrences, happenings

### Required Relationship Types
- **CAUSES** - Source causes target
- **INFLUENCES** - Source influences target
- **OPTIMIZES** - Source optimizes target
- **ENABLES** - Source enables target
- **REDUCES** - Source reduces target
- **LEADS_TO** - Source leads to target
- **REQUIRES** - Source requires target
- **RELATES_TO** - General relationship
- **IS_PART_OF** - Part-whole relationship

### Must Extract
1. **Key Concepts** - All concept types listed above
2. **Relationships** - Between concepts with types
3. **Important Quotes** - Key statements with exact text
4. **Speaker Context** - Who said what
5. **Cross-episode Links** - Connections across episodes

### Provenance Requirements
Every extracted entity must include:
- `source_path` - File path
- `episode_id` - Episode identifier
- `start_char` / `end_char` - Character offsets in source
- `speaker` - Who said it
- `timestamp` - When it was said (if available)
- `chunk_index` - Which chunk it came from

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│              KG Extraction Pipeline                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Chunk Reader                                        │
│     - Read chunks from Qdrant or chunk files            │
│     - Filter by workspace_id                            │
│                                                          │
│  2. LLM Extractor                                       │
│     - GPT-4o for structured extraction                  │
│     - JSON schema for deterministic output              │
│     - Batch processing for efficiency                   │
│                                                          │
│  3. Entity Normalizer                                   │
│     - Normalize concept names (lowercase, dedupe)       │
│     - Link to existing nodes                            │
│     - Handle aliases/synonyms                          │
│                                                          │
│  4. Neo4j Writer                                        │
│     - Create/update nodes                              │
│     - Create relationships                             │
│     - Attach provenance metadata                       │
│     - Handle duplicates                                │
│                                                          │
│  5. Quote Extractor                                     │
│     - Extract important quotes                         │
│     - Link quotes to concepts/speakers                 │
│     - Store with timestamps                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 Implementation Plan

### Phase 1: Neo4j Setup & Schema Design

**Files:**
- `core_engine/kg/neo4j_client.py` - Neo4j connection & utilities
- `core_engine/kg/schema.py` - Node/relationship schemas

**Tasks:**
1. ✅ Set up Neo4j connection (local or cloud)
2. ✅ Define node labels and properties
3. ✅ Define relationship types and properties
4. ✅ Create indexes for performance
5. ✅ Create constraints (unique node IDs)

**Neo4j Schema:**

```cypher
// Node Labels
(:Concept {id, name, type, description, ...})
(:Person {id, name, ...})
(:Place {id, name, ...})
(:Organization {id, name, ...})
(:Event {id, name, ...})
(:Quote {id, text, speaker, timestamp, ...})

// Relationships
(:Concept)-[:CAUSES {confidence, ...}]->(:Concept)
(:Concept)-[:INFLUENCES {confidence, ...}]->(:Concept)
(:Concept)-[:OPTIMIZES {confidence, ...}]->(:Concept)
(:Concept)-[:ENABLES {confidence, ...}]->(:Concept)
(:Concept)-[:REDUCES {confidence, ...}]->(:Concept)
(:Concept)-[:LEADS_TO {confidence, ...}]->(:Concept)
(:Concept)-[:REQUIRES {confidence, ...}]->(:Concept)
(:Concept)-[:RELATES_TO {confidence, ...}]->(:Concept)
(:Concept)-[:IS_PART_OF {confidence, ...}]->(:Concept)

(:Person)-[:SAID {timestamp, ...}]->(:Quote)
(:Quote)-[:ABOUT {confidence, ...}]->(:Concept)
(:Concept)-[:MENTIONED_IN {episode_id, ...}]->(:Episode)
```

**Provenance Properties (on all nodes/relationships):**
- `source_path` - String
- `episode_id` - String
- `start_char` - Integer
- `end_char` - Integer
- `speaker` - String (nullable)
- `timestamp` - String (nullable)
- `chunk_index` - Integer
- `workspace_id` - String
- `extracted_at` - DateTime

---

### Phase 2: LLM Extraction Module

**Files:**
- `core_engine/kg/extractor.py` - Main extraction logic
- `core_engine/kg/prompts.py` - LLM prompts
- `core_engine/kg/schemas.py` - JSON schemas for extraction

**Tasks:**
1. ✅ Design extraction prompt with examples
2. ✅ Define JSON schema for structured output
3. ✅ Implement batch extraction (multiple chunks per call)
4. ✅ Handle extraction errors gracefully
5. ✅ Add retry logic for API failures

**Extraction Strategy:**
- Process chunks in batches (5-10 chunks per LLM call)
- Use structured output (JSON mode) for deterministic results
- Extract concepts, relationships, and quotes in one pass
- Include confidence scores for human review

**Prompt Structure:**
```
You are extracting structured knowledge from podcast transcripts.

Extract:
1. Concepts (with types: Concept, Practice, CognitiveState, etc.)
2. Relationships between concepts (CAUSES, INFLUENCES, etc.)
3. Important quotes (memorable statements)

For each entity, include:
- Exact text span from the transcript
- Speaker (if mentioned)
- Timestamp (if available)
- Confidence level

Output JSON matching this schema: {...}
```

---

### Phase 3: Entity Normalization

**Files:**
- `core_engine/kg/normalizer.py` - Normalization logic

**Tasks:**
1. ✅ Normalize concept names (lowercase, trim, dedupe)
2. ✅ Link to existing nodes in Neo4j
3. ✅ Handle aliases and synonyms
4. ✅ Merge duplicate concepts

**Normalization Rules:**
- Lowercase all concept names
- Remove extra whitespace
- Handle variations: "meditation" = "Meditation" = "MEDITATION"
- Link aliases: "RR" = "Rick Rubin" (if in context)

---

### Phase 4: Neo4j Writer

**Files:**
- `core_engine/kg/writer.py` - Neo4j write operations

**Tasks:**
1. ✅ Create/update nodes with MERGE
2. ✅ Create relationships with MERGE
3. ✅ Attach provenance metadata
4. ✅ Handle duplicates (update vs. create)
5. ✅ Batch writes for performance

**Write Strategy:**
- Use MERGE to avoid duplicates
- Update provenance arrays (multiple sources per concept)
- Use transactions for atomicity
- Batch writes (100-500 operations per transaction)

---

### Phase 5: Quote Extraction

**Files:**
- `core_engine/kg/quotes.py` - Quote extraction logic

**Tasks:**
1. ✅ Extract memorable/important quotes
2. ✅ Link quotes to concepts
3. ✅ Link quotes to speakers
4. ✅ Store timestamps
5. ✅ Store character offsets

**Quote Criteria:**
- Memorable statements
- Key insights
- Definitions
- Principles
- Important claims

---

### Phase 6: Cross-Episode Linking ✅ **COMPLETE**

**Files:**
- `core_engine/kg/cross_episode.py` - Cross-episode analysis
- `analyze_cross_episode.py` - Standalone analysis script

**Tasks:**
1. ✅ Detect concepts mentioned in multiple episodes
2. ✅ Create cross-episode relationships
3. ✅ Identify recurring themes
4. ✅ Build episode-to-episode links
5. ✅ Find co-occurring concepts
6. ✅ Generate cross-episode statistics

**Strategy:**
- After all episodes processed, analyze for duplicates
- Create CROSS_EPISODE relationships between co-occurring concepts
- Aggregate provenance from multiple episodes
- Identify recurring themes and patterns

**Usage:**
```bash
# Run cross-episode analysis
python analyze_cross_episode.py

# Or use programmatically:
from core_engine.kg import CrossEpisodeLinker, get_neo4j_client

client = get_neo4j_client(workspace_id="production")
linker = CrossEpisodeLinker(client, workspace_id="production")

# Find concepts in multiple episodes
concepts = linker.find_cross_episode_concepts(min_episodes=2)

# Create CROSS_EPISODE links
result = linker.create_cross_episode_links(
    min_episodes=2,
    min_co_occurrences=2,
    min_confidence=0.5
)
```

---

## 🔄 Processing Pipeline

### Step-by-Step Flow

```
1. Load Chunks
   ↓
2. Batch Chunks (5-10 per batch)
   ↓
3. LLM Extraction (structured JSON)
   ↓
4. Normalize Entities
   ↓
5. Write to Neo4j (MERGE nodes/relationships)
   ↓
6. Extract Quotes
   ↓
7. Link Quotes to Concepts/Speakers
   ↓
8. Cross-Episode Analysis (after all episodes)
```

---

## 📊 Data Flow

```
Chunks (from Qdrant/chunking)
    ↓
LLM Extractor (GPT-4o)
    ↓
Structured JSON (concepts, relationships, quotes)
    ↓
Normalizer (dedupe, link)
    ↓
Neo4j Writer (MERGE operations)
    ↓
Knowledge Graph (with provenance)
```

---

## 🎯 Success Criteria

1. ✅ Extract all required concept types
2. ✅ Extract all required relationship types
3. ✅ Store full provenance (source, speaker, timestamp, offsets)
4. ✅ Handle duplicates correctly
5. ✅ Process 100+ episodes efficiently
6. ✅ Extract quotes with speaker context
7. ✅ Enable cross-episode queries

---

## 🚀 Next Steps

1. **Set up Neo4j** (local Docker or cloud)
2. **Implement schema** (nodes, relationships, indexes)
3. **Build extractor** (LLM + structured output)
4. **Test on single file** (verify extraction quality)
5. **Scale to all files** (batch processing)
6. **Add cross-episode linking** (post-processing)

---

## 📁 File Structure

```
core_engine/kg/
├── __init__.py
├── KG_EXTRACTION_PLAN.md (this file)
├── neo4j_client.py      # Neo4j connection
├── schema.py            # Schema definitions
├── extractor.py         # LLM extraction logic
├── prompts.py           # LLM prompts
├── schemas.py           # JSON schemas
├── normalizer.py        # Entity normalization
├── writer.py            # Neo4j write operations
├── quotes.py            # Quote extraction
└── cross_episode.py     # Cross-episode linking
```

---

## 🔧 Configuration

**Environment Variables:**
- `NEO4J_URI` - Neo4j connection URI
- `NEO4J_USER` - Username
- `NEO4J_PASSWORD` - Password
- `OPENAI_API_KEY` - For LLM extraction
- `KG_EXTRACTION_BATCH_SIZE` - Chunks per LLM call (default: 5)
- `KG_CONFIDENCE_THRESHOLD` - Min confidence for extraction (default: 0.7)

---

## 📝 Notes

- **Deterministic Output**: Use structured JSON output from LLM
- **Provenance First**: Every entity must have source tracking
- **Incremental Processing**: Support adding new episodes without reprocessing
- **Error Handling**: Gracefully handle LLM failures, retry logic
- **Performance**: Batch operations, use transactions efficiently

