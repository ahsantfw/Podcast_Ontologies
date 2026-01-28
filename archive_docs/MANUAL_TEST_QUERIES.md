# Manual Test Queries - No Results Rejection

## Test Instructions

1. **Start Backend**: `cd backend && uv run uvicorn app.main:app --reload`
2. **Start Frontend**: `cd frontend && npm run dev`
3. **Test Each Query**: Copy/paste each query into the chat
4. **Expected Result**: Should see "I couldn't find information about that..." when RAG=0, KG=0

---

## Test Queries (Should be REJECTED when RAG=0, KG=0)

### Category 1: General Knowledge Questions (15 queries)

1. What is RAG?
2. What is Retrieval Augmented Generation?
3. Do you know Urdu?
4. Can you translate Me acha hu into English?
5. What are the issues of society?
6. What are the main problems in society?
7. What are solutions to social problems?
8. What is the meaning of life?
9. What is philosophy?
10. What is creativity?
11. What is meditation?
12. What is mindfulness?
13. What is coaching?
14. What is personal development?
15. What is the meaning of all is well?

### Category 2: Technical/Programming Questions (5 queries)

16. How do I write a Python function?
17. What is machine learning?
18. What is artificial intelligence?
19. How does a neural network work?
20. What is the difference between Python and JavaScript?

### Category 3: Math Questions (4 queries)

21. What is 2+2?
22. Solve for x: 3x + 7 = 25
23. What is the square root of 16?
24. Calculate the area of a circle with radius 5

### Category 4: Current Events/News (4 queries)

25. What happened today?
26. What is the latest news?
27. What is happening in the world?
28. What are current events?

### Category 5: Weather/Geography (4 queries)

29. What is the weather today?
30. What is the capital of France?
31. Where is Mount Everest?
32. What is the population of India?

### Category 6: General Definitions (5 queries)

33. What does success mean?
34. What is happiness?
35. What is love?
36. What is failure?
37. What is leadership?

### Category 7: Language/Translation (3 queries)

38. Translate hello to Spanish
39. What does bonjour mean?
40. How do you say thank you in French?

### Category 8: General "How to" Questions (4 queries)

41. How do I become successful?
42. How do I improve my life?
43. How do I find my purpose?
44. How do I be happy?

### Category 9: Meta Questions About System (4 queries)

45. What can you do?
46. How do you work?
47. What is your purpose?
48. Who created you?

### Category 10: Week/Topic References (3 queries)

49. Week 1: Query Expansion
50. What is Week 1 about?
51. Tell me about Phase 2
52. What is the next step?

---

## Valid Queries (Should be ALLOWED)

### Greetings (Don't need results)
- Hi
- Hello
- Hey
- Thanks
- Thank you
- Bye

### Podcast-Specific (Should work if RAG/KG has results)
- Who is Phil Jackson?
- What did Phil Jackson say about meditation?
- What concepts are in the podcasts?
- What practices lead to better decision-making?
- What did speakers say about creativity?

---

## Expected Results

### For Test Queries (1-52):
- **RAG Count**: Should be 0
- **KG Count**: Should be 0
- **Answer**: Should contain "I couldn't find information about that in the podcast knowledge base..."
- **Status**: ✅ **REJECTED**

### For Valid Queries:
- **Greetings**: Should work (don't need results)
- **Podcast Queries**: Should work if RAG/KG has results (e.g., "Who is Phil Jackson?" should return RAG: 10, KG: 10)

---

## Test Checklist

- [ ] Test all 52 queries
- [ ] Verify RAG=0, KG=0 for each
- [ ] Verify rejection message appears
- [ ] Test valid queries work correctly
- [ ] Check logs for any errors

---

## Notes

- Some queries might return RAG/KG results if they happen to match podcast content (e.g., "What is meditation?" might find results if meditation is discussed in podcasts)
- The key is: **If RAG=0 AND KG=0, the query should be REJECTED**
- If RAG>0 OR KG>0, the query should proceed normally
