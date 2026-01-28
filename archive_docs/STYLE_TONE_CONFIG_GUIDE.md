# Style & Tone Configuration Guide

## Overview

Style and Tone instructions are now stored in **separate config files** for easy editing by developers.

---

## Config Files Location

### Style Config
**File**: `core_engine/reasoning/style_config.py`

**Contains**:
- `STYLE_INSTRUCTIONS` - Prompt instructions for each style
- `DEFAULT_STYLE` - Default style value
- `STYLE_DESCRIPTIONS` - UI descriptions (for frontend reference)

### Tone Config
**File**: `core_engine/reasoning/tone_config.py`

**Contains**:
- `TONE_INSTRUCTIONS` - Prompt instructions for each tone
- `DEFAULT_TONE` - Default tone value
- `TONE_DESCRIPTIONS` - UI descriptions (for frontend reference)

---

## How to Modify Instructions

### Example: Changing "Casual" Style Instructions

1. Open `core_engine/reasoning/style_config.py`
2. Find `STYLE_INSTRUCTIONS["casual"]`
3. Modify the prompt text:

```python
STYLE_INSTRUCTIONS = {
    "casual": """
RESPONSE STYLE: Casual
- Use everyday, conversational language
- Use contractions naturally (don't, can't, it's, you're)
- Keep it relaxed and accessible
# ... modify these instructions ...
""",
    # ... other styles ...
}
```

4. Save the file
5. **No restart needed** - Changes apply to next query (if using reload)

### Example: Adding a New Style

1. Add to `STYLE_INSTRUCTIONS`:
```python
STYLE_INSTRUCTIONS = {
    # ... existing styles ...
    "storytelling": """
RESPONSE STYLE: Storytelling
- Use narrative flow and scene-setting
- Create engaging stories around concepts
- Use character-driven examples
# ... your instructions ...
""",
}
```

2. Add to `STYLE_DESCRIPTIONS`:
```python
STYLE_DESCRIPTIONS = {
    # ... existing descriptions ...
    "storytelling": {
        "label": "Storytelling",
        "description": "Narrative and engaging",
        "icon": "📖"
    },
}
```

3. Update frontend component to include new option

---

## How It Works

### Flow:
```
User selects Style/Tone
    ↓
Frontend sends to API
    ↓
Backend stores in session_metadata
    ↓
Agent calls _get_style_tone_instructions()
    ↓
Loads from style_config.py & tone_config.py
    ↓
Appends to system prompts
    ↓
LLM generates response with that style/tone
```

### Code Location:
- **Config Files**: `core_engine/reasoning/style_config.py` & `tone_config.py`
- **Usage**: `core_engine/reasoning/agent.py` → `_get_style_tone_instructions()`
- **Applied In**: All prompt generation methods:
  - `_handle_with_llm()` - Greetings, conversational, system_info
  - `_synthesize_answer()` - Knowledge queries
  - `_handle_user_memory()` - Memory queries
  - `_handle_out_of_scope_llm()` - Out-of-scope responses

---

## Current Styles & Tones

### Styles (5):
1. **Casual** - Relaxed, conversational
2. **Professional** - Business-appropriate
3. **Academic** - Scholarly, detailed
4. **Concise** - Brief, direct
5. **Detailed** - Comprehensive

### Tones (4):
1. **Warm** - Friendly, approachable
2. **Neutral** - Balanced, objective
3. **Formal** - Reserved, respectful
4. **Enthusiastic** - Energetic, excited

---

## Best Practices

### When Modifying Instructions:

1. **Be Specific**: Give clear, actionable guidance
2. **Use Examples**: Include example phrasing when helpful
3. **Test Changes**: Test each style/tone after modification
4. **Keep Consistent**: Maintain similar structure across styles/tones
5. **Document Changes**: Note why you changed something

### Prompt Writing Tips:

- **Start with clear directive**: "RESPONSE STYLE: ..."
- **Use bullet points**: Easier to read and follow
- **Be specific**: "Use contractions" vs "Be casual"
- **Include examples**: Show what you mean
- **Avoid contradictions**: Don't say "be brief" and "be detailed"

---

## Testing

After modifying config files:

1. **Test each style** with same question:
   - "What is creativity?"
   - Compare responses

2. **Test each tone** with same question:
   - "What is creativity?"
   - Compare emotional quality

3. **Test combinations**:
   - Casual + Warm
   - Academic + Formal
   - Concise + Enthusiastic

---

## Questions?

- **Where are instructions?** → `core_engine/reasoning/style_config.py` & `tone_config.py`
- **How to add new style?** → Add to `STYLE_INSTRUCTIONS` dict
- **How to change default?** → Modify `DEFAULT_STYLE` or `DEFAULT_TONE`
- **Do I need to restart?** → Yes, for Python changes (unless using reload)

---

## Next Steps

1. ✅ Config files created
2. ⏳ Review: Do we need "Storytelling" style or "Supportive" tone?
3. ⏳ Fix UI: Separate Style/Tone dropdowns
4. ⏳ Test all combinations
5. ⏳ Refine instructions based on testing
