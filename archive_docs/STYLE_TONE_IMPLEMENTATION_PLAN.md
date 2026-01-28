# Style & Tone Implementation Plan

## 1. Product Requirements Analysis

### Product Context
- **Product**: Podcast Intelligence Assistant
- **Domain**: Philosophy, Creativity, Coaching, Personal Development
- **Primary Use Cases**:
  - Research and exploration of podcast insights
  - Finding quotes and sources
  - Understanding relationships between concepts
  - Cross-episode pattern discovery
  - Content creation (scripts, articles)

### Target Users
1. **Researchers** - Need detailed, academic responses
2. **Content Creators** - Need engaging, creative responses
3. **Coaches/Therapists** - Need warm, supportive responses
4. **Students/Learners** - Need clear, educational responses
5. **General Users** - Need casual, friendly responses

---

## 2. Style & Tone Definitions

### STYLE Options (How information is presented)

#### 1. **Casual** (Default)
- **Definition**: Relaxed, conversational, everyday language
- **Use Case**: General exploration, friendly interactions
- **Characteristics**:
  - Uses contractions (don't, can't, it's)
  - Conversational tone
  - Simple, accessible language
  - Can use casual phrases
- **Example**: "So, creativity is basically about..."

#### 2. **Professional**
- **Definition**: Business-appropriate, structured, clear
- **Use Case**: Work-related research, presentations
- **Characteristics**:
  - Clear structure with headings/bullets
  - Formal language (avoid contractions)
  - Professional terminology
  - Action-oriented
- **Example**: "Creativity can be understood as..."

#### 3. **Academic**
- **Definition**: Scholarly, detailed, with citations
- **Use Case**: Research papers, deep analysis
- **Characteristics**:
  - Precise terminology
  - Detailed explanations
  - Multiple perspectives
  - Citation-heavy
- **Example**: "The concept of creativity, as explored in contemporary discourse..."

#### 4. **Concise**
- **Definition**: Brief, direct, to-the-point
- **Use Case**: Quick answers, summaries
- **Characteristics**:
  - Short sentences
  - No fluff
  - Bullet points preferred
  - Direct answers
- **Example**: "Creativity: innovative thinking + execution"

#### 5. **Detailed**
- **Definition**: Comprehensive, thorough, expansive
- **Use Case**: Deep dives, comprehensive understanding
- **Characteristics**:
  - Long-form explanations
  - Multiple examples
  - Context and background
  - Comprehensive coverage
- **Example**: "Creativity encompasses multiple dimensions..."

---

### TONE Options (Emotional/relational quality)

#### 1. **Warm** (Default)
- **Definition**: Friendly, approachable, genuinely interested
- **Use Case**: Personal development, coaching contexts
- **Characteristics**:
  - Empathetic language
  - Encouraging
  - Personal connection
  - Shows care
- **Example**: "That's a great question! Let me help you explore..."

#### 2. **Neutral**
- **Definition**: Balanced, objective, informative
- **Use Case**: Research, factual queries
- **Characteristics**:
  - Objective language
  - No emotional coloring
  - Fact-focused
  - Balanced perspective
- **Example**: "Creativity is defined as..."

#### 3. **Formal**
- **Definition**: Reserved, respectful, professional distance
- **Use Case**: Academic, business contexts
- **Characteristics**:
  - Formal address
  - Respectful distance
  - Professional boundaries
  - Structured communication
- **Example**: "I would be pleased to provide information regarding..."

#### 4. **Enthusiastic**
- **Definition**: Energetic, excited, passionate
- **Use Case**: Creative exploration, inspiring content
- **Characteristics**:
  - High energy
  - Passionate language
  - Excitement about topics
  - Inspiring tone
- **Example**: "Oh, this is fascinating! Creativity is such an amazing topic..."

---

## 3. UI/UX Design Plan

### Current Problem
- Both Style and Tone in one dropdown = confusing
- Users can't see both selections clearly
- Not intuitive which is which

### Proposed Solution

#### Option A: Two Separate Dropdowns (Recommended)
```
[Style: Casual ▼] [Tone: Warm ▼]
```
- **Pros**: Clear separation, easy to understand
- **Cons**: Takes more horizontal space

#### Option B: Two-Tab Modal
```
[Style & Tone] button → Opens modal with:
  Tab 1: Style (5 options)
  Tab 2: Tone (4 options)
```
- **Pros**: Clean UI, organized
- **Cons**: Requires click to change

#### Option C: Side-by-Side Selectors
```
┌─────────────────┬─────────────────┐
│ Style            │ Tone             │
│ ○ Casual         │ ○ Warm           │
│ ○ Professional   │ ○ Neutral        │
│ ○ Academic       │ ○ Formal         │
│ ○ Concise        │ ○ Enthusiastic   │
│ ○ Detailed       │                  │
└─────────────────┴─────────────────┘
```
- **Pros**: See all options, clear
- **Cons**: Takes vertical space

### Recommended: Option A (Two Separate Dropdowns)
- Most intuitive
- Quick to change
- Clear visual separation
- Mobile-friendly

---

## 4. Architecture Plan

### Frontend Changes

#### Component Structure
```
Chat.jsx
  └── Header
      ├── StyleSelector (dropdown)
      └── ToneSelector (dropdown)
```

#### State Management
- Store in `localStorage`: `chat_style`, `chat_tone`
- Send with each query to backend
- Persist across sessions

#### Files to Modify
1. `frontend/src/components/StyleSelector.jsx` (NEW - separate component)
2. `frontend/src/components/ToneSelector.jsx` (NEW - separate component)
3. `frontend/src/pages/Chat.jsx` (UPDATE - add both selectors)
4. `frontend/src/services/api.js` (UPDATE - send style/tone)

---

### Backend Changes

#### API Layer
- Accept `style` and `tone` in QueryRequest
- Pass to reasoner

#### Reasoner Layer
- Store in session metadata
- Pass to agent

#### Agent Layer
- Apply style/tone to ALL prompts:
  - Intent classification
  - Greeting responses
  - Conversational responses
  - Knowledge query synthesis
  - System info responses

#### Files to Modify
1. `backend/app/api/routes/query.py` (UPDATE - accept params)
2. `core_engine/reasoning/reasoning.py` (UPDATE - pass to agent)
3. `core_engine/reasoning/agent.py` (UPDATE - apply to prompts)

---

## 5. Implementation Details

### Where Style/Tone Instructions Are Applied

#### Location 1: `_get_style_tone_instructions()` method
**File**: `core_engine/reasoning/agent.py`
**Purpose**: Generate style/tone-specific instruction text
**Called from**: All prompt generation methods

#### Location 2: Intent-Specific Prompts
**Methods**:
- `_handle_with_llm()` - For greetings, conversational, system_info
- `_synthesize_answer()` - For knowledge queries
- `_handle_user_memory()` - For memory queries
- `_handle_out_of_scope_llm()` - For out-of-scope responses

**How**: Append style/tone instructions to system prompts

#### Location 3: System Prompt Base
**File**: `core_engine/reasoning/agent.py`
**Method**: `_synthesize_answer()`
**Location**: In the system_prompt string

---

## 6. Testing Plan

### Test Cases

#### Style Tests
1. **Casual**: "What is creativity?"
   - Should use contractions, casual language
   
2. **Professional**: "What is creativity?"
   - Should be structured, formal language
   
3. **Academic**: "What is creativity?"
   - Should be detailed, citation-heavy
   
4. **Concise**: "What is creativity?"
   - Should be brief, bullet points
   
5. **Detailed**: "What is creativity?"
   - Should be comprehensive, long-form

#### Tone Tests
1. **Warm**: "What is creativity?"
   - Should be friendly, encouraging
   
2. **Neutral**: "What is creativity?"
   - Should be objective, balanced
   
3. **Formal**: "What is creativity?"
   - Should be reserved, respectful
   
4. **Enthusiastic**: "What is creativity?"
   - Should be energetic, passionate

#### Combination Tests
- Casual + Warm
- Professional + Formal
- Academic + Neutral
- Concise + Enthusiastic
- Detailed + Warm

---

## 7. Code Structure

### Style/Tone Instruction Generator
```python
def _get_style_tone_instructions(self, session_metadata):
    style = session_metadata.get("style", "casual")
    tone = session_metadata.get("tone", "warm")
    
    # Return formatted instructions
    return f"""
RESPONSE STYLE: {style_instructions[style]}
RESPONSE TONE: {tone_instructions[tone]}
"""
```

### Prompt Integration Pattern
```python
system_prompt = f"""
{base_personality}
{style_tone_instructions}  # ← Added here
{domain_specific_rules}
"""
```

---

## 8. Next Steps

1. ✅ Create plan (THIS DOCUMENT)
2. ⏳ Redesign UI components (separate Style/Tone selectors)
3. ⏳ Define exact prompt instructions for each style/tone
4. ⏳ Implement backend changes
5. ⏳ Test each combination
6. ⏳ Refine based on testing

---

## 9. Questions to Answer Before Implementation

1. **Default Values**: Casual + Warm? (Yes, recommended)
2. **Persistence**: Per-session or global? (Global - localStorage)
3. **Visual Indicator**: Show current selection in UI? (Yes)
4. **Reset Option**: Allow reset to defaults? (Yes, good UX)
5. **Mobile**: How to display on small screens? (Stack vertically)

---

## 10. Success Criteria

- ✅ Users can easily change style and tone
- ✅ Changes apply immediately to next response
- ✅ Each style/tone produces distinctly different responses
- ✅ UI is intuitive and clear
- ✅ Settings persist across sessions
- ✅ Works on mobile devices
