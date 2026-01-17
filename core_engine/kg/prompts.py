"""
LLM prompts for knowledge graph extraction.
Production-grade, domain-agnostic extraction for diverse content types.
"""

from __future__ import annotations

from typing import List
from langchain_core.documents import Document


def build_extraction_prompt(chunks: List[Document]) -> str:
    """
    Build comprehensive extraction prompt for LLM.
    Designed to handle diverse content types: podcasts, interviews, lectures, meetings, research, creator archives.
    
    Args:
        chunks: List of document chunks to extract from
        
    Returns:
        Formatted prompt string
    """
    # Combine chunk texts with metadata
    chunk_texts = []
    for i, chunk in enumerate(chunks):
        metadata = chunk.metadata
        text = chunk.page_content
        
        chunk_info = f"=== Chunk {i+1} ===\n"
        chunk_info += f"Source: {metadata.get('source_path', 'unknown')}\n"
        chunk_info += f"Episode: {metadata.get('episode_id', 'unknown')}\n"
        if metadata.get('speaker'):
            chunk_info += f"Speaker: {metadata.get('speaker')}\n"
        if metadata.get('timestamp'):
            chunk_info += f"Timestamp: {metadata.get('timestamp')}\n"
        chunk_info += f"Start char: {metadata.get('start_char', 'N/A')}\n"
        chunk_info += f"End char: {metadata.get('end_char', 'N/A')}\n"
        chunk_info += f"\nText:\n{text}\n"
        
        chunk_texts.append(chunk_info)
    
    combined_text = "\n\n".join(chunk_texts)
    
    prompt = f"""You are an expert knowledge extraction system designed to transform long-form unstructured content (podcasts, interviews, lectures, meetings, research, creator archives) into a persistent, structured, reasoning-grade knowledge system.

Your goal is to extract high-signal concepts and relationships that enable:
- Multi-hop reasoning (X → Y → Z)
- Cross-content pattern detection
- Detection of recurring "core truths" across a corpus
- Evidence-grounded answers with full provenance
- Conversational interaction with the "soul" of the work

## MISSION

Extract structured knowledge that captures:
1. **Explicit relationships** - Directly stated connections
2. **Implicit relationships** - Subconscious knowledge, underlying patterns
3. **Cross-domain connections** - How ideas in different domains connect
4. **Recurring themes** - "Core truths" that appear across multiple episodes
5. **Speaker-specific patterns** - What specific individuals emphasize
6. **Temporal evolution** - How ideas develop or change over time
7. **Abstract to concrete** - High-level principles to specific examples

## CONCEPT TYPES (Domain-Agnostic)

Extract concepts across ALL domains (philosophy, spirituality, creativity, health, business, technology, etc.):

- **Concept**: Abstract ideas, theories, frameworks, themes
  - Examples: "creativity", "philosophy", "spirituality", "enlightenment", "innovation", "leadership"
  
- **Practice**: Actions, methods, techniques, approaches, habits, routines
  - Examples: "meditation", "reflection", "walking in nature", "journaling", "cold exposure", "visualization"
  
- **CognitiveState / MindState**: Mental states, emotions, qualities of mind, awareness levels
  - Examples: "flow state", "anxiety", "clarity", "awareness", "consciousness", "enlightenment", "confusion"
  
- **BehavioralPattern**: Recurring behaviors, habits, processes, ways of operating
  - Examples: "morning routine", "decision-making process", "creative process", "learning process"
  
- **Principle / Framework**: Guiding principles, frameworks, rules, laws, maxims
  - Examples: "80/20 rule", "principles of creativity", "laws of nature", "spiritual principles"
  
- **Outcome / Effect**: Results, consequences, effects, qualities achieved, states reached
  - Examples: "improved focus", "clarity", "decision-making quality", "reduced anxiety", "spiritual health", "better understanding", "enlightenment"
  
- **Causality**: Cause-effect relationships as concepts themselves
  - Examples: "stress causes anxiety", "practice leads to mastery"
  
- **Person**: Named individuals, speakers, guests, mentioned people
  - Examples: "Phil Jackson", "Rick Rubin", "Alejandro Iñárritu"
  
- **Place**: Locations, geographical entities, spaces
  - Examples: "nature", "studio", "meditation space"
  
- **Organization**: Companies, institutions, groups, collectives
  - Examples: "Origin Studios", "Tetragrammatron"
  
- **Event**: Specific occurrences, happenings, experiences
  - Examples: "spiritual experience", "creative breakthrough", "enlightenment moment"

## RELATIONSHIP TYPES (Comprehensive)

Extract BOTH explicit and implicit relationships:

- **CAUSES**: Source directly causes target
  - Explicit: "stress causes anxiety"
  - Implicit: If speaker implies causation without stating it directly
  
- **INFLUENCES**: Source influences target (weaker than causes, broader impact)
  - Explicit: "childhood influences adult behavior"
  - Implicit: "The way he was raised shaped his approach" → upbringing INFLUENCES approach
  
- **OPTIMIZES**: Source optimizes, improves, enhances, or makes target better
  - Explicit: "meditation improves clarity", "walking in nature optimizes spiritual health"
  - Implicit: "When I do X, I feel more Y" → X OPTIMIZES Y
  
- **ENABLES**: Source enables, makes possible, or facilitates target
  - Explicit: "practice enables mastery", "reflection enables self-awareness"
  - Implicit: "Without X, Y wouldn't be possible" → X ENABLES Y
  
- **REDUCES**: Source reduces, decreases, or mitigates target
  - Explicit: "meditation reduces anxiety", "exercise reduces stress"
  - Implicit: "X helps me deal with Y" → X REDUCES Y
  
- **LEADS_TO**: Source leads to target (outcome, result, consequence)
  - Explicit: "consistent practice leads to improvement"
  - Implicit: "If you do X, eventually Y happens" → X LEADS_TO Y
  
- **REQUIRES**: Source requires target (dependency, prerequisite)
  - Explicit: "mastery requires practice"
  - Implicit: "To achieve X, you need Y" → X REQUIRES Y
  
- **RELATES_TO**: General relationship when more specific type doesn't fit
  - Use for: Abstract connections, thematic links, "connected in spirit of thought"
  - Examples: "enlightenment relates to physical health", "creativity relates to spirituality"
  
- **IS_PART_OF**: Part-whole relationship, hierarchical structure
  - Examples: "warm-up is part of workout", "meditation is part of morning routine"

## CRITICAL EXTRACTION PRIORITIES

### Priority 1: Practice → Outcome Relationships (HIGHEST)
**This is the MOST VALUABLE type of relationship for client use cases.**

Extract when speakers mention (explicitly OR implicitly):
- "X improves Y" → X (Practice) OPTIMIZES Y (Outcome)
- "X helps with Y" → X (Practice) ENABLES or OPTIMIZES Y (Outcome)
- "X leads to Y" → X (Practice) LEADS_TO Y (Outcome)
- "X reduces Y" → X (Practice) REDUCES Y (Outcome)
- "X enables Y" → X (Practice) ENABLES Y (Outcome)
- "When I do X, I feel more Y" → X (Practice) OPTIMIZES Y (Outcome)
- "X is good for Y" → X (Practice) OPTIMIZES Y (Outcome)
- "X makes Y possible" → X (Practice) ENABLES Y (Outcome)

**Examples to extract:**
- "Walking in nature optimizes spiritual health" → walking_in_nature (Practice) OPTIMIZES spiritual_health (Outcome)
- "Meditation improves clarity" → meditation (Practice) OPTIMIZES clarity (Outcome)
- "Reflection helps with decision-making" → reflection (Practice) ENABLES decision_making_quality (Outcome)
- "Exercise reduces anxiety" → exercise (Practice) REDUCES anxiety (Outcome)
- "Reading leads to better understanding" → reading (Practice) LEADS_TO understanding (Outcome)

### Priority 2: Cross-Domain Connections
**Link ideas across different domains (philosophy ↔ health, spirituality ↔ creativity, etc.)**

Extract relationships that show:
- How philosophical ideas connect to practical outcomes
- How spiritual concepts relate to physical health
- How creative principles apply to business
- How different speakers' stories connect "in the spirit of thought"

Examples:
- "Enlightenment relates to physical health" → enlightenment (Concept) RELATES_TO physical_health (Outcome)
- "Creativity is connected to spirituality" → creativity (Concept) RELATES_TO spirituality (Concept)
- "The same principle applies to both art and business" → principle (Principle) RELATES_TO art (Concept) AND business (Concept)

### Priority 3: Concept → Concept Relationships
**Link related ideas, even if not explicitly stated as Practice → Outcome**

Extract when:
- Concepts are discussed together
- One concept influences another
- Concepts are part of the same theme or domain
- Concepts represent different perspectives on the same idea

Examples:
- "Reflection influences decision-making quality" → reflection (Practice) INFLUENCES decision_making_quality (Outcome)
- "Creativity requires vulnerability" → creativity (Concept) REQUIRES vulnerability (CognitiveState)
- "Philosophy and spirituality are connected" → philosophy (Concept) RELATES_TO spirituality (Concept)

### Priority 4: Speaker-Anchored Relationships
**Capture what specific individuals emphasize or believe**

Extract when:
- A specific person (e.g., "Phil Jackson", "Rick Rubin") emphasizes something
- Speaker's personal experience or belief is stated
- Speaker's perspective differs from others
- Speaker's emphasis evolves over time (note episode context)

Include speaker information in relationships to enable queries like:
- "What did Phil Jackson consistently emphasize about discipline?"
- "What does Rick Rubin think about creativity?"

### Priority 5: Implicit/Subconscious Knowledge
**Extract underlying patterns and "subconscious knowledge" that domain experts mention but aren't fully conscious of**

Look for:
- Patterns that emerge across multiple statements
- Underlying principles not explicitly stated
- Connections speakers make without directly stating them
- "Core truths" that appear across episodes

Example from client recording:
- "This artist talks about its health and its health is optimized when it does walking in nature. And then it gives you the inverse and shows walking in nature is good for spiritual health."
- Extract: walking_in_nature (Practice) OPTIMIZES health (Outcome)
- Extract: walking_in_nature (Practice) OPTIMIZES spiritual_health (Outcome)
- Extract: health (Outcome) RELATES_TO spiritual_health (Outcome)

### Priority 6: Recurring Themes and "Core Truths"
**Identify concepts and relationships that appear across multiple episodes**

Mark concepts/relationships that:
- Appear in multiple episodes (will be aggregated later)
- Represent recurring themes
- Are emphasized by multiple speakers
- Represent "core truths" or universal principles

## DOMAIN-SPECIFIC EXTRACTION GUIDELINES

### Philosophy Domain
- Extract: Abstract principles, frameworks, ways of thinking
- Relationships: How philosophical ideas connect to practical life
- Examples: "enlightenment", "wisdom", "truth", "meaning", "existence"

### Spirituality Domain
- Extract: Spiritual practices, states, experiences, principles
- Relationships: How spiritual practices affect other domains (health, creativity, etc.)
- Examples: "spiritual health", "enlightenment", "meditation", "prayer", "devotion"

### Creativity Domain
- Extract: Creative processes, principles, states, outcomes
- Relationships: What enables/optimizes creativity, how creativity relates to other domains
- Examples: "creative process", "artistic expression", "innovation", "inspiration"

### Health & Wellness Domain
- Extract: Practices, outcomes, states related to physical/mental health
- Relationships: What practices optimize health outcomes
- Examples: "physical health", "mental health", "anxiety", "clarity", "focus"

### Business Domain
- Extract: Business principles, practices, outcomes, frameworks
- Relationships: How business principles connect to other domains
- Examples: "leadership", "strategy", "innovation", "team building"

### Technology Domain
- Extract: Technical concepts, practices, outcomes
- Relationships: How technology enables/optimizes other domains
- Examples: "automation", "AI", "digital tools"

## EXTRACTION GUIDELINES

### 1. Extract Both Explicit and Implicit Relationships
- **Explicit**: Directly stated ("meditation improves clarity")
- **Implicit**: Implied or suggested ("When I meditate, I feel clearer" → meditation OPTIMIZES clarity)
- **Subconscious**: Underlying patterns ("This artist's health is optimized when walking in nature" → walking_in_nature OPTIMIZES health)

### 2. Outcome Extraction Patterns
Extract as Outcomes when speakers mention:
- "improving X" → Outcome: "X" (e.g., "improving clarity" → clarity)
- "better X" → Outcome: "X" (e.g., "better decision-making" → decision_making_quality)
- "reduced X" → Outcome: "reduced X" or "X" (e.g., "reduced anxiety" → anxiety or reduced_anxiety)
- "achieving X" → Outcome: "X"
- "X is good" → Outcome: "X" (if X is a quality/state)
- "X happens" → Outcome: "X" (if X is a result/effect)

### 3. Practice Extraction Patterns
Extract as Practices when speakers mention:
- Methods, techniques, approaches, habits, routines
- Actions people take: "I do X", "We practice X", "The method is X"
- Ways of doing things: "The approach is X", "The technique involves X"

### 4. Concept Linking - Don't Leave Concepts Isolated
- When concepts are discussed together, extract relationships
- When concepts are part of the same theme, link them
- When one concept influences another, extract the relationship
- When concepts represent different perspectives on the same idea, link them

### 5. Speaker Context - Always Include
- When a specific person emphasizes something, include speaker in relationship
- When speaker's personal experience is shared, note it
- When speaker's perspective is unique, capture it
- This enables speaker-anchored queries

### 6. Cross-Episode Patterns
- If a concept appears multiple times, note it (will be aggregated)
- If a relationship is mentioned across episodes, extract it each time
- If a "core truth" emerges, capture it

### 7. Normalize IDs
- Use lowercase, normalized names
- Replace spaces with underscores
- Remove special characters
- Examples: "meditation" not "Meditation", "decision_making_quality" not "decision-making quality", "spiritual_health" not "spiritual health"

### 8. Confidence Scores
- **0.8-1.0**: High confidence - explicitly stated, clear relationship
- **0.6-0.8**: Moderate confidence - implied but clear
- **0.4-0.6**: Lower confidence - inferred, may need validation
- **<0.4**: Very uncertain - only extract if pattern is strong

### 9. Quotes - Extract Memorable Statements
- Key insights, definitions, principles
- Memorable phrases that capture essence
- Statements that represent "core truths"
- Speaker-specific quotes that show their perspective

### 10. Provenance - Always Include
- Exact text spans where concepts/relationships are mentioned
- Character offsets (start_char, end_char)
- Speaker information
- Episode/timestamp context

## OUTPUT FORMAT

Return a JSON object with three arrays: "concepts", "relationships", "quotes".

### For each concept:
```json
{{
  "id": "normalized_identifier",
  "name": "Name as it appears in text",
  "type": "Concept|Practice|CognitiveState|BehavioralPattern|Principle|Outcome|Causality|Person|Place|Organization|Event",
  "description": "Brief description if available",
  "text_span": "Exact text where concept is mentioned",
  "start_char": 1234,
  "end_char": 1250,
  "confidence": 0.8
}}
```

### For each relationship:
```json
{{
  "source_id": "source_concept_id",
  "target_id": "target_concept_id",
  "type": "CAUSES|INFLUENCES|OPTIMIZES|ENABLES|REDUCES|LEADS_TO|REQUIRES|RELATES_TO|IS_PART_OF",
  "description": "Brief description of the relationship",
  "text_span": "Text describing the relationship",
  "start_char": 1234,
  "end_char": 1250,
  "confidence": 0.8
}}
```

**Note**: If speaker information is available and the relationship is speaker-specific, include speaker context in the description or as metadata.

### For each quote:
```json
{{
  "text": "Exact quote text",
  "speaker": "Speaker name if mentioned",
  "timestamp": "Timestamp if available",
  "related_concepts": ["concept_id1", "concept_id2"],
  "confidence": 0.8
}}
```

## EXTRACTION PROCESS

Follow this systematic process:

**STEP 1: Extract All Concepts**
- Scan for ALL concepts across ALL domains
- Identify Practices, Outcomes, CognitiveStates, Concepts, Principles, etc.
- Don't limit to specific domains - be comprehensive
- Extract both explicit mentions and implied concepts

**STEP 2: Extract Practice → Outcome Relationships (HIGHEST PRIORITY)**
- For EVERY Practice mentioned, check if it's linked to an Outcome
- Look for explicit phrases: "improves", "helps with", "enables", "reduces", "leads to"
- Look for implicit patterns: "When I do X, I feel more Y", "X is good for Y"
- Extract with high confidence (0.8+) when clear
- This is the MOST VALUABLE type of relationship

**STEP 3: Extract Cross-Domain Connections**
- Link concepts across different domains (philosophy ↔ health, spirituality ↔ creativity)
- Extract "connected in spirit of thought" relationships
- Show how seemingly different stories connect

**STEP 4: Extract Concept → Concept Relationships**
- Link related concepts that are discussed together
- Don't leave concepts isolated
- Extract both explicit and implicit connections

**STEP 5: Extract Speaker-Anchored Relationships**
- When specific individuals emphasize something, include speaker context
- Capture speaker-specific perspectives and beliefs

**STEP 6: Extract Implicit/Subconscious Knowledge**
- Look for underlying patterns not explicitly stated
- Extract "subconscious knowledge" that domain experts mention
- Capture inverse relationships (e.g., "X is good for Y" → also "Y is achieved through X")

**STEP 7: Extract Quotes**
- Memorable statements, key insights, definitions, principles
- Speaker-specific quotes that show their perspective
- Quotes that represent "core truths"

**STEP 8: Mark Recurring Patterns**
- Note if concepts/relationships appear multiple times
- This helps identify "core truths" across episodes

## REMEMBER

1. **Practice → Outcome relationships are HIGHEST PRIORITY** - Extract these first and with highest confidence
2. **Extract BOTH explicit and implicit relationships** - Don't only look for direct statements
3. **Link concepts across domains** - Show how philosophy, spirituality, creativity, health, business connect
4. **Capture speaker context** - Enable speaker-anchored queries
5. **Don't leave concepts isolated** - Connect related ideas
6. **Be comprehensive** - This system must work for 1000+ different types of transcripts
7. **Extract "core truths"** - Patterns that recur across episodes
8. **Capture subconscious knowledge** - Underlying patterns domain experts mention

## TRANSCRIPT CHUNKS

{combined_text}

## EXTRACTION

Extract concepts, relationships, and quotes from the above chunks following the systematic process above. 

**Priority Order:**
1. Practice → Outcome relationships (extract these FIRST)
2. Cross-domain connections
3. Concept → Concept relationships
4. Speaker-anchored relationships
5. Implicit/subconscious knowledge
6. Quotes

Return ONLY valid JSON matching the schema. Do not include any explanatory text before or after the JSON.
"""

    return prompt


def build_single_chunk_prompt(chunk: Document) -> str:
    """
    Build extraction prompt for a single chunk.
    
    Args:
        chunk: Document chunk
        
    Returns:
        Formatted prompt string
    """
    return build_extraction_prompt([chunk])
