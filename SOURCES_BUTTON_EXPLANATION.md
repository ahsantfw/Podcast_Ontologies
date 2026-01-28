# Sources Button - How It Works

## Overview
The "Sources" button appears next to the "Copy" button when AI provides a response. It shows where the information came from (transcripts and knowledge graph).

## Data Flow

### 1. Backend: Source Extraction (`agent.py`)

**Location**: `core_engine/reasoning/agent.py` - `_extract_sources()` method (line 1833)

**Process**:
1. **RAG Sources** (Transcript Sources):
   - Extracted from `rag_results` (vector search results from Qdrant)
   - Each RAG result contains:
     - `text`: The actual quote/text chunk
     - `metadata`: Contains episode info, speaker, timestamp, etc.
   
2. **KG Sources** (Knowledge Graph Sources):
   - Extracted from `kg_results` (Neo4j query results)
   - Each KG result contains:
     - `concept`: Concept name
     - `type`: Node type (Person, Concept, etc.)
     - `description`: Concept description

**Source Data Structure**:
```python
# RAG Source (Transcript)
{
    "type": "transcript",
    "episode_id": "002_JERROD_CARMICHAEL",  # From metadata
    "speaker": "Jerrod Carmichael",          # From metadata
    "timestamp": "00:15:30",                 # From metadata
    "text": "Creativity is about...",        # First 200 chars
    "source_path": "/path/to/transcript.txt"
}

# KG Source (Knowledge Graph)
{
    "type": "knowledge_graph",
    "concept": "Creativity",
    "node_type": "Concept",
    "description": "The ability to create..."
}
```

**Key Metadata Fields Extracted**:
- `episode_id`: From `metadata.episode_id`, `metadata.episode`, or filename
- `speaker`: From `metadata.speaker`, `metadata.speaker_name`, or `metadata.author`
- `timestamp`: From `metadata.timestamp`, `metadata.start_time`, or `metadata.time`
- `text`: First 200 characters of the retrieved text chunk

### 2. Backend: API Response (`reasoning.py`)

**Location**: `core_engine/reasoning/reasoning.py` - `query_streaming()` method (line 464-479)

**Process**:
1. After RAG + KG searches complete, sources are extracted:
   ```python
   sources = self.agent._extract_sources(rag_results[:5], kg_results[:10])
   ```

2. Sources are included in the final response:
   ```python
   yield {
       "chunk": "",
       "done": True,
       "session_id": session.session_id,
       "sources": sources,  # <-- Sources sent here
       "metadata": {
           "method": "agent_streaming",
           "rag_count": len(rag_results),
           "kg_count": len(kg_results),
       }
   }
   ```

### 3. Frontend: Receiving Sources (`Chat.jsx`)

**Location**: `frontend/src/pages/Chat.jsx` - `handleSend()` function (line 341, 357, 394)

**Process**:
1. Sources are extracted from streaming response:
   ```javascript
   finalSources = chunk.sources || []
   ```

2. Sources are stored in the message object:
   ```javascript
   updated[msgIndex] = {
       ...updated[msgIndex],
       content: cleanAnswer,
       sources: finalSources,  // <-- Sources stored here
       metadata: normalizedMetadata,
   }
   ```

### 4. Frontend: Displaying Sources (`ChatMessage.jsx`)

**Location**: `frontend/src/components/ChatMessage.jsx` (line 230-279)

**Process**:

1. **Sources Button** (line 230-248):
   - Only shows if `message.sources && message.sources.length > 0`
   - Displays count: `Sources (3)`
   - Toggles visibility when clicked

2. **Sources Display** (line 253-279):
   - Shows up to 5 sources (`message.sources.slice(0, 5)`)
   - For each source, displays:
     - **Episode ID**: `source.episode_id || 'Unknown Episode'`
     - **Timestamp**: `source.timestamp` (if available)
     - **Speaker**: `source.speaker` (if available)
     - **Text**: First 250 characters of `source.text` (if available)

**Source Display Format**:
```
┌─────────────────────────────────────┐
│ 002 JERROD CARMICHAEL (00:15:30)    │
│ Speaker: Jerrod Carmichael          │
│ "Creativity is about breaking..."   │
└─────────────────────────────────────┘
```

## Where Data Comes From

### RAG Sources (Transcripts)
1. **Vector Search** → Qdrant database
   - Searches embeddings for relevant text chunks
   - Returns chunks with metadata

2. **Metadata Fields**:
   - Stored when transcripts are processed/ingested
   - Includes: episode_id, speaker, timestamp, source_path

3. **Extraction**:
   - `_extract_sources()` reads metadata from RAG results
   - Handles multiple possible field names (episode_id, episode, file_name, etc.)
   - Deduplicates by `episode_id:speaker:timestamp`

### KG Sources (Knowledge Graph)
1. **Graph Search** → Neo4j database
   - Searches for concepts matching query terms
   - Returns concept nodes with relationships

2. **Data Structure**:
   - Concept name, type, description
   - Relationships to other concepts

3. **Extraction**:
   - `_extract_sources()` reads concept data from KG results
   - Formats as knowledge graph source type

## Example Flow

1. **User asks**: "What is creativity?"

2. **Backend searches**:
   - RAG: Finds 10 transcript chunks about creativity
   - KG: Finds 3 concepts related to creativity

3. **Backend extracts sources**:
   ```python
   sources = [
       {
           "type": "transcript",
           "episode_id": "002_JERROD_CARMICHAEL",
           "speaker": "Jerrod Carmichael",
           "timestamp": "00:15:30",
           "text": "Creativity is about breaking free from..."
       },
       {
           "type": "knowledge_graph",
           "concept": "Creativity",
           "node_type": "Concept",
           "description": "The ability to create novel ideas..."
       }
   ]
   ```

4. **Frontend receives**:
   - Sources array in response
   - Stores in message object

5. **UI displays**:
   - "Sources (2)" button appears
   - Clicking shows the 2 sources with full details

## Key Files

- **Backend Source Extraction**: `core_engine/reasoning/agent.py:1833` (`_extract_sources()`)
- **Backend API Response**: `core_engine/reasoning/reasoning.py:464` (`query_streaming()`)
- **Frontend Source Handling**: `frontend/src/pages/Chat.jsx:341, 357, 394`
- **Frontend Source Display**: `frontend/src/components/ChatMessage.jsx:230-279`

## Notes

- Sources are limited to **top 5 RAG results** and **top 10 KG results**
- Only **first 5 sources** are displayed in UI (even if more exist)
- Sources are **deduplicated** by episode_id:speaker:timestamp
- If no sources exist, the Sources button **doesn't appear**
- Sources text is truncated to **200 chars** in backend, **250 chars** in frontend display
