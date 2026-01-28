# Script Generation Module - Explained

## What Is Script Generation?

Based on the client requirements, the **Script Generation Module** is a feature that:

**Takes**: A theme or topic (e.g., "creativity", "overcoming obstacles", "what makes good art")

**Produces**: A complete script for a podcast/documentary that:
- Interweaves stories and ideas from multiple episodes
- Links themes together in a larger picture
- Includes exact quotes with timecodes
- Follows a tapestry-style format (like "The Midnight Miracle")
- Runs 40-60 minutes
- Has music cues and transitions

---

## Example Use Case

### User Request:
> "I want to create a 45-minute episode about 'creativity' using only the Rick Rubin podcast transcripts. The show should interweave different guests' perspectives, link themes together, and include music cues."

### Script Generation Output:
```
SCRIPT: "The Nature of Creativity"
Runtime: 45 minutes
Theme: Creativity

[00:00 - 00:30] INTRO
Music: Ambient intro
Narrator: "What is creativity? Across 150 episodes, we've explored..."

[00:30 - 05:00] SEGMENT 1: Defining Creativity
Quote from Episode 12 (Phil Jackson) [12:34]:
  "Creativity is not about making something new. It's about seeing 
   connections that others don't see."

Quote from Episode 45 (Jerrod Carmichael) [08:12]:
  "The creative act is an act of courage. You're putting something 
   into the world that didn't exist before."

[05:00 - 12:00] SEGMENT 2: The Creative Process
Quote from Episode 12 (Phil Jackson) [25:18]:
  "Meditation opens the space for creativity. When your mind is quiet, 
   ideas can emerge."

[Transition music: 30 seconds]

Quote from Episode 78 (Alejandro Inarritu) [15:42]:
  "I don't create. I discover. The story already exists. I just find it."

[12:00 - 20:00] SEGMENT 3: Obstacles to Creativity
...
```

---

## What It Should Do

### 1. **Theme Extraction**
- Identify all concepts/quotes related to a theme
- Find cross-episode patterns
- Group by sub-themes

### 2. **Quote Compilation**
- Extract relevant quotes with timecodes
- Organize by speaker and episode
- Filter by relevance/quality

### 3. **Narrative Structure**
- Create logical flow (intro → development → conclusion)
- Link ideas together
- Build narrative arc

### 4. **Formatting**
- Add timecodes
- Include speaker names
- Add music cues
- Format for production

### 5. **Output**
- Script file (Markdown/PDF)
- Timeline with segments
- Source citations

---

## How It Would Work

### Input:
```python
generate_script(
    theme="creativity",
    episodes=["001 PHIL JACKSON", "002 JERROD CARMICHAEL", "003 ALEJANDRO INARRITU"],
    runtime_minutes=45,
    style="tapestry",  # Interweaving style
    include_music_cues=True
)
```

### Process:
1. **Query Knowledge Graph**: Find all concepts/quotes about "creativity"
2. **Cross-Episode Analysis**: Find recurring themes across episodes
3. **Quote Selection**: Pick best quotes with timecodes
4. **Structure Building**: Organize into segments
5. **Narrative Flow**: Create logical progression
6. **Formatting**: Generate script document

### Output:
- Script file with segments, quotes, timecodes
- Timeline breakdown
- Source citations

---

## Current Status

❌ **NOT IMPLEMENTED**

The system can:
- ✅ Find quotes about a theme
- ✅ Find cross-episode concepts
- ✅ Query relationships

But cannot:
- ❌ Compile into script format
- ❌ Structure narrative flow
- ❌ Add timecodes automatically
- ❌ Format for production

---

## Implementation Plan

### Module Structure:
```
core_engine/
  script_generation/
    __init__.py
    theme_extractor.py      # Extract themes from KG
    quote_compiler.py        # Compile quotes with timecodes
    narrative_builder.py     # Build story structure
    formatter.py             # Format script output
    script_generator.py      # Main orchestrator
```

### Key Functions:

#### 1. Theme Extractor
```python
def extract_theme_concepts(theme: str, workspace_id: str) -> Dict:
    """
    Find all concepts, quotes, and relationships related to theme.
    Returns: {
        "concepts": [...],
        "quotes": [...],
        "relationships": [...],
        "cross_episode_patterns": [...]
    }
    """
```

#### 2. Quote Compiler
```python
def compile_quotes(
    theme: str,
    episodes: List[str],
    max_quotes: int = 20
) -> List[Quote]:
    """
    Compile relevant quotes with timecodes.
    Returns: List of quotes sorted by relevance/quality
    """
```

#### 3. Narrative Builder
```python
def build_narrative(
    quotes: List[Quote],
    concepts: List[Concept],
    runtime_minutes: int = 45
) -> Script:
    """
    Build narrative structure:
    - Intro segment
    - Development segments (3-5)
    - Conclusion segment
    - Transitions
    """
```

#### 4. Formatter
```python
def format_script(
    script: Script,
    format: str = "markdown"  # or "pdf", "json"
) -> str:
    """
    Format script with:
    - Timecodes
    - Speaker names
    - Music cues
    - Source citations
    """
```

---

## Example Implementation

### Basic Flow:
```python
from core_engine.script_generation import ScriptGenerator

generator = ScriptGenerator(workspace_id="default")

script = generator.generate(
    theme="creativity",
    episodes=["001 PHIL JACKSON", "002 JERROD CARMICHAEL"],
    runtime_minutes=45,
    style="tapestry"
)

# Output
print(script.to_markdown())
# or
script.save("creativity_script.md")
```

### What It Would Generate:
```markdown
# Script: "The Nature of Creativity"
**Runtime**: 45 minutes
**Theme**: Creativity
**Source Episodes**: 001, 002, 003

---

## [00:00 - 00:30] INTRO
*[Music: Ambient intro, fade in]*

Narrator: "What is creativity? Across these conversations, we've explored 
the many facets of the creative process. Today, we weave together insights 
from different voices, all connected by a shared understanding of what it 
means to create."

---

## [00:30 - 08:00] SEGMENT 1: Defining Creativity

### Quote 1
**Speaker**: Phil Jackson  
**Episode**: 001 PHIL JACKSON  
**Timecode**: [12:34 - 12:48]  
**Quote**: 
> "Creativity is not about making something new. It's about seeing 
> connections that others don't see. When you can see those connections, 
> you're creating something that didn't exist before."

### Quote 2
**Speaker**: Jerrod Carmichael  
**Episode**: 002 JERROD CARMICHAEL  
**Timecode**: [08:12 - 08:28]  
**Quote**:
> "The creative act is an act of courage. You're putting something into 
> the world that didn't exist before. And that's terrifying, but also 
> necessary."

*[Music transition: 15 seconds]*

---

## [08:00 - 18:00] SEGMENT 2: The Creative Process

### Quote 3
**Speaker**: Phil Jackson  
**Episode**: 001 PHIL JACKSON  
**Timecode**: [25:18 - 25:42]  
**Quote**:
> "Meditation opens the space for creativity. When your mind is quiet, 
> ideas can emerge. You're not forcing them. You're allowing them."

[Connection to next quote]
This idea of creating space connects to...

### Quote 4
**Speaker**: Alejandro Inarritu  
**Episode**: 003 ALEJANDRO INARRITU  
**Timecode**: [15:42 - 16:05]  
**Quote**:
> "I don't create. I discover. The story already exists. I just find it. 
> The creative process is about removing what's not the story."

*[Music bridge: 20 seconds]*

---

## [18:00 - 35:00] SEGMENT 3: Obstacles to Creativity

[... more segments ...]

---

## [35:00 - 45:00] CONCLUSION

Narrator: "As we've seen, creativity takes many forms. But at its core, 
it's about connection, courage, and discovery. These voices, though 
different, all point to the same truth: creativity is not a gift, it's 
a practice."

*[Music: Outro, fade out]*

---

## Sources
- Episode 001: PHIL JACKSON
- Episode 002: JERROD CARMICHAEL  
- Episode 003: ALEJANDRO INARRITU
```

---

## Technical Requirements

### Data Needed:
1. **Quotes** with timecodes (✅ Have)
2. **Concepts** related to theme (✅ Have)
3. **Relationships** between ideas (✅ Have)
4. **Cross-episode patterns** (✅ Have)
5. **Speaker information** (✅ Have)

### Processing Needed:
1. **Theme matching** - Find relevant content
2. **Quote ranking** - Quality/relevance scoring
3. **Narrative structure** - Logical flow
4. **Time allocation** - Distribute across runtime
5. **Formatting** - Script output

---

## Why It's Important

From the requirements:
> "Can it thoughtfully compile an accurate script for a tapestry style 
> documentary, pulling from multiple episodes and themes and tying the 
> final result into a magic bow?"

This is a **core use case** - not just querying, but **creating new content** from the knowledge base.

---

## Implementation Priority

**High Priority** - This is a key differentiator and core feature mentioned in requirements.

**Estimated Effort**: 1-2 weeks
- Theme extraction: 2-3 days
- Quote compilation: 2-3 days
- Narrative building: 3-4 days
- Formatting: 1-2 days
- Testing: 2-3 days

---

## Summary

**Script Generation Module** = A tool that:
- Takes a theme/topic
- Queries the knowledge graph
- Compiles relevant quotes with timecodes
- Structures them into a narrative
- Formats as a production-ready script
- Outputs 40-60 minute tapestry-style episodes

**Status**: ❌ Not implemented yet  
**Priority**: 🔴 High (core feature)  
**Complexity**: Medium (requires narrative logic)

