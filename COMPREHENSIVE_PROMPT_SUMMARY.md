# Comprehensive Extraction Prompt - Summary

## Overview

Completely rewrote the extraction prompt to be **production-grade and domain-agnostic**, capable of handling 1000+ different types of transcripts across multiple domains.

---

## Key Improvements

### 1. Domain-Agnostic Design
- Works for: philosophy, spirituality, creativity, health, business, technology, and any other domain
- Not limited to specific concept lists
- Adapts to content type automatically

### 2. Explicit + Implicit Relationship Extraction
**Before**: Only explicit relationships ("meditation improves clarity")
**After**: Also extracts:
- Implicit: "When I meditate, I feel clearer" → meditation OPTIMIZES clarity
- Subconscious: Underlying patterns domain experts mention
- Inverse: "X is good for Y" → also "Y is achieved through X"

### 3. Cross-Domain Connection Extraction
**New**: Links ideas across different domains
- Philosophy ↔ Health
- Spirituality ↔ Creativity
- Business ↔ Philosophy
- "Connected in spirit of thought" relationships

### 4. Speaker-Anchored Relationships
**Enhanced**: Captures what specific individuals emphasize
- Enables: "What did Phil Jackson consistently emphasize about discipline?"
- Tracks speaker-specific perspectives and beliefs
- Notes how emphasis evolves over time

### 5. Recurring Themes & "Core Truths"
**New**: Identifies patterns that appear across multiple episodes
- Marks concepts/relationships that recur
- Identifies "core truths" or universal principles
- Enables cross-episode queries

### 6. Comprehensive Concept Types
**Expanded**: Covers all domains
- Philosophy: enlightenment, wisdom, truth, meaning
- Spirituality: spiritual health, meditation, prayer, devotion
- Creativity: creative process, artistic expression, innovation
- Health: physical/mental health, anxiety, clarity, focus
- Business: leadership, strategy, innovation, team building
- Technology: automation, AI, digital tools

### 7. Systematic Extraction Process
**8-Step Process**:
1. Extract all concepts (comprehensive)
2. Extract Practice → Outcome (HIGHEST PRIORITY)
3. Extract cross-domain connections
4. Extract concept → concept relationships
5. Extract speaker-anchored relationships
6. Extract implicit/subconscious knowledge
7. Extract quotes
8. Mark recurring patterns

---

## What This Enables

### Client Use Cases Now Supported

1. **"What practices are most associated with improving clarity?"**
   - Will find Practice → Outcome relationships across all domains
   - Links practices from philosophy, spirituality, health, etc.

2. **"How does reflection relate to decision-making quality?"**
   - Extracts both explicit and implicit relationships
   - Links concepts even if not directly stated

3. **"What are the core ideas that recur most frequently about creativity?"**
   - Identifies recurring themes
   - Marks "core truths" across episodes

4. **"What did Speaker A consistently emphasize about X?"**
   - Captures speaker-anchored relationships
   - Tracks speaker-specific perspectives

5. **"If someone wants to reduce anxiety, what concepts or practices..."**
   - Multi-hop reasoning: anxiety → factors → practices
   - Cross-domain connections (spirituality, health, philosophy)

6. **Script Generation**
   - Links themes and ideas across episodes
   - Finds "connected in spirit of thought" relationships
   - Enables tapestry-style documentary scripts

7. **Conversational Interaction**
   - Captures "soul" of the work
   - Extracts subconscious knowledge
   - Enables deep, meaningful conversations

---

## Comparison: Before vs After

### Before (Limited)
- Focused on simple Practice → Outcome
- Domain-specific examples
- Only explicit relationships
- Basic concept linking

### After (Comprehensive)
- Practice → Outcome + Cross-domain + Implicit + Subconscious
- Domain-agnostic (works for any content)
- Explicit + Implicit + Subconscious relationships
- Multi-layered concept linking
- Speaker-anchored patterns
- Recurring theme detection
- Designed for 1000+ transcript types

---

## Expected Results After Re-processing

1. **More Relationships**: Practice → Outcome + Cross-domain + Concept → Concept
2. **Better Linking**: Concepts connected across domains
3. **Speaker Context**: Relationships include speaker information
4. **Recurring Patterns**: "Core truths" identified across episodes
5. **Implicit Knowledge**: Subconscious patterns extracted
6. **Domain Coverage**: Works for philosophy, spirituality, creativity, health, business, technology

---

## Files Modified

- `core_engine/kg/prompts.py` - Complete rewrite for production-grade extraction

---

## Next Steps

1. **Review** the comprehensive prompt
2. **Approve** when ready
3. **Clean database** (if needed)
4. **Re-process** transcripts
5. **Re-test** client questions
6. **Target**: 80%+ of questions should have KG results

---

## Status

✅ **Comprehensive prompt ready for review**
⏸️ **Not processing yet - awaiting approval**

