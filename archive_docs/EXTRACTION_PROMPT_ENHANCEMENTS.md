# Extraction Prompt Enhancements

## Summary

Enhanced extraction prompts to prioritize Practice → Outcome relationships and improve concept linking. **NOT PROCESSING YET** - awaiting your approval.

---

## Key Changes Made

### 1. Added CRITICAL Section for Practice → Outcome Relationships

**New Section**: Explicitly marks Practice → Outcome as HIGHEST PRIORITY

**Added Examples**:
- "Meditation improves clarity" → meditation (Practice) OPTIMIZES clarity (Outcome)
- "Reflection helps with decision-making" → reflection (Practice) ENABLES decision_making_quality (Outcome)
- "Exercise reduces anxiety" → exercise (Practice) REDUCES anxiety (Outcome)
- "Reading leads to better understanding" → reading (Practice) LEADS_TO understanding (Outcome)
- "Journaling enables self-awareness" → journaling (Practice) ENABLES self_awareness (Outcome)

**Pattern Recognition**:
- "X improves Y" → X (Practice) OPTIMIZES Y (Outcome)
- "X helps with Y" → X (Practice) ENABLES Y (Outcome)
- "X reduces Y" → X (Practice) REDUCES Y (Outcome)
- "X leads to Y" → X (Practice) LEADS_TO Y (Outcome)
- "X enables Y" → X (Practice) ENABLES Y (Outcome)

### 2. Enhanced Guidelines with Extraction Rules

**Added Critical Extraction Rules**:
1. **Practice → Outcome Relationships (HIGHEST PRIORITY)**
   - Explicit instructions to extract when ANY speaker mentions practice improving/enabling/reducing outcome
   - Lists common practices: meditation, reflection, reading, journaling, exercise, self-observation
   - Lists common outcomes: clarity, decision-making quality, understanding, focus, self-awareness, reduced anxiety

2. **Concept Linking**
   - Instructions to connect related concepts
   - Example: "Reflection helps with decision-making" → reflection INFLUENCES decision_making_quality
   - Emphasis: "Don't leave concepts isolated - connect related ones"

3. **Outcome Extraction Patterns**
   - "improving X" → Outcome: "X"
   - "better X" → Outcome: "X"
   - "reduced X" → Outcome: "reduced X"
   - "achieving X" → Outcome: "X"

4. **Practice Extraction Patterns**
   - Methods, techniques, approaches, habits, routines → Practice

5. **Speaker Context**
   - Instructions to include speaker information in relationships
   - Enables speaker-anchored queries

### 3. Added Step-by-Step Extraction Instructions

**New Section**: Step-by-step process for extraction

1. **STEP 1**: Extract all Concepts
2. **STEP 2**: Extract Practice → Outcome Relationships (MOST IMPORTANT)
3. **STEP 3**: Extract Concept → Concept Relationships
4. **STEP 4**: Extract Quotes

**Emphasis**: "The most valuable relationships are Practice → Outcome. Extract these FIRST and with HIGHEST PRIORITY."

---

## Expected Improvements

After re-processing with these enhanced prompts, we should see:

1. **More Practice → Outcome Relationships**
   - Practices linked to clarity, decision-making quality, anxiety, etc.
   - Examples: meditation → clarity, reflection → decision-making quality

2. **Better Concept Linking**
   - Related concepts connected (e.g., reflection ↔ decision-making)
   - Fewer isolated concepts

3. **Speaker-Anchored Relationships**
   - Relationships include speaker information
   - Enables "What did Phil Jackson emphasize?" queries

4. **Better Outcome Extraction**
   - Outcomes extracted when speakers mention "improving X", "better Y", etc.
   - Normalized IDs (e.g., "decision_making_quality" not "decision-making quality")

---

## Files Modified

- `core_engine/kg/prompts.py` - Enhanced extraction prompt

---

## Next Steps (After Your Approval)

1. Clean database (if needed)
2. Re-process transcripts with enhanced prompts
3. Verify Practice → Outcome relationships created
4. Re-test client questions
5. Target: 80% of questions should have KG results

---

## Review Checklist

Before processing, verify:
- [ ] Practice → Outcome examples are clear
- [ ] Extraction patterns match your expectations
- [ ] Step-by-step instructions make sense
- [ ] Common practices/outcomes lists are appropriate

**Ready for your review and approval!**

