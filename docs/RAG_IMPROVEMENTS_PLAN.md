# RAG Quality Improvement Techniques - Evaluation Plan

## Current State

**Implemented:**
- ✅ **Bardic Knowledge** - Contextual Chunk Embeddings (9739b1e) - 97.3% precision, 17ms
- ✅ **Divine Insight** - Cross-Encoder Reranking (b36b6c4) - 98.7% precision, 1500ms (optional)
- ❌ **Wild Magic Surge** - Hybrid Search (BM25) - Rejected, hurts quality
- ❌ **Scrying Window** - Sentence Window Retrieval - Rejected, precision collapse

**Current Recommendation:** Bardic Knowledge (default) + optional Divine Insight

---

## Proposed Techniques to Evaluate

### 1. Scrying Window: Sentence Window Retrieval ⭐ PRIORITY

> *"Wizards use scrying to see wider context around a focal point—small precise focus with expanded vision."*

**Concept:**
- Embed individual sentences for precise matching
- Store surrounding sentences (e.g., 2 before, 3 after) as metadata
- Return wider context to LLM instead of single sentence

**Problem it solves:**
- Information split across chunks
- Pronoun/reference resolution (e.g., "its population" → "Berlin's population")
- Semantic dilution from large chunks

**Expected Results:**
- Precision: +5-10%
- Content Match: +10-15%
- Latency: +2-5ms (minimal)

**Implementation:**
1. Modify chunking to split by sentences
2. Store surrounding sentences in chunk metadata
3. Update retrieval to return context instead of sentence
4. Benchmark vs Bardic Knowledge

**Complexity:** Medium
**Estimated Time:** 2-3 hours

**References:**
- https://glaforge.dev/posts/2025/02/25/advanced-rag-sentence-window-retrieval/
- https://michaeljohnpena.com/blog/2023-10-28-sentence-window-retrieval

---

### 2. Mirror Image: Multi-Query Retrieval (Query Expansion)

> *"Creates multiple versions of the same query—each mirror searches independently."*

**Concept:**
- LLM generates 3-5 variations of user query
- Run all queries in parallel
- Merge results using Reciprocal Rank Fusion (RRF)

**Problem it solves:**
- Ambiguous queries with multiple valid interpretations
- Different phrasings of same intent
- Vocabulary mismatch between query and documents

**Example:**
- Query: "How do I cache data?"
- Variations:
  - "What are caching strategies?"
  - "Best practices for data caching"
  - "Cache implementation patterns"
  - "How to implement caching layer"

**Expected Results:**
- Recall: +10-15%
- Precision: Neutral or slight decrease
- Latency: +50-100ms (LLM call + parallel searches)

**Implementation:**
1. Add query generation prompt
2. Run multiple searches in parallel
3. Implement RRF scoring to merge results
4. Benchmark vs baseline

**Complexity:** Low-Medium
**Estimated Time:** 1-2 hours

**References:**
- https://arxiv.org/html/2411.13154v1
- https://haystack.deepset.ai/blog/query-expansion

---

### 3. Flurry of Blows: Query Decomposition

> *"Monk's rapid strikes breaking down complex problems into precise attacks."*

**Concept:**
- LLM breaks complex query into sub-questions
- Retrieve for each sub-question separately
- Merge candidate pool and rerank

**Problem it solves:**
- Multi-hop reasoning questions
- Complex queries requiring multiple pieces of information
- "How do X and Y relate?" type questions

**Example:**
- Query: "How do microservices handle authentication and caching?"
- Sub-queries:
  - "How do microservices handle authentication?"
  - "How do microservices implement caching?"
  - "How do authentication and caching interact in microservices?"

**Expected Results:**
- Complex query accuracy: +15-20%
- Simple query accuracy: Neutral
- Latency: +100-200ms (LLM call + multiple retrievals)

**Implementation:**
1. Add decomposition prompt
2. Retrieve for each sub-question
3. Merge and deduplicate results
4. Optional: Rerank merged pool
5. Benchmark with complex queries

**Complexity:** Medium
**Estimated Time:** 2-3 hours

**References:**
- https://arxiv.org/html/2507.00355v1

---

### 4. Arcane Recall: Parent Document Retrieval

> *"Wizard recalls the full spell tome after finding a single fragment."*

**Concept:**
- Index small chunks for precise retrieval
- Store reference to parent document/section
- Return entire parent or larger section to LLM

**Problem it solves:**
- Context loss from chunking
- Information spread across multiple chunks
- Need for broader context after precise match

**Example:**
- Chunk: "JWT tokens should expire after 15 minutes"
- Parent: Entire "Authentication Security" section (500 tokens)
- Return: Full section with context about token refresh, storage, etc.

**Expected Results:**
- Content Match: +5-10%
- Precision: Neutral
- Latency: Minimal (just metadata lookup)

**Trade-off:** More tokens sent to LLM (cost increase)

**Implementation:**
1. Store parent document ID in chunk metadata
2. Add parent document lookup
3. Return parent instead of chunk
4. Benchmark vs baseline

**Complexity:** Low
**Estimated Time:** 1 hour

**References:**
- https://medium.com/data-science/langchains-parent-document-retriever-revisited-1fca8791f5a0

---

### 5. Illusory Script: Hypothetical Document Embeddings (HyDE)

> *"Creates an illusion of the answer to find the real one—hypothetical document as magical illusion."*

**Concept:**
- LLM generates hypothetical answer to query
- Embed the hypothetical answer (not the query)
- Search for documents similar to hypothetical answer

**Problem it solves:**
- Query-document vocabulary mismatch
- Short queries that don't embed well
- Abstract questions

**Example:**
- Query: "What is caching?"
- HyDE: "Caching is a technique to store frequently accessed data in memory for faster retrieval. Common strategies include LRU, LFU, and TTL-based eviction..."
- Search: Find docs similar to this hypothetical answer

**Expected Results:**
- Precision: +5-10% on abstract queries
- Latency: +50-100ms (LLM call)

**Implementation:**
1. Add HyDE generation prompt
2. Embed hypothetical answer
3. Search with hypothetical embedding
4. Benchmark vs baseline

**Complexity:** Low
**Estimated Time:** 1 hour

**References:**
- https://arxiv.org/abs/2212.10496

---

## Evaluation Plan

### Phase 1: Quick Wins (Low Complexity)
1. **Arcane Recall** - Parent Document Retrieval (1 hour)
   - Easy to implement
   - Minimal risk
   - Benchmark immediately

2. **Mirror Image** - Multi-Query Retrieval (1-2 hours)
   - Low complexity
   - Good recall improvement expected
   - Benchmark

### Phase 2: High-Value Techniques (Medium Complexity)
3. **Scrying Window** - Sentence Window Retrieval (2-3 hours) ⭐
   - Highest expected quality gain
   - Minimal latency impact
   - Benchmark

4. **Flurry of Blows** - Query Decomposition (2-3 hours)
   - Good for complex queries
   - May need new test queries
   - Benchmark

### Phase 3: Experimental (Optional)
5. **Illusory Script** - HyDE (1 hour)
   - Interesting approach
   - May not help with current queries
   - Benchmark if time permits

---

## Success Criteria

For each technique, we'll measure:
- **Precision**: % retrieved docs that are relevant
- **Recall**: % relevant docs that are retrieved
- **F1 Score**: Harmonic mean
- **Content Match**: % expected phrases found
- **Latency**: Average query time
- **Success Rate**: % queries passing thresholds

**Acceptance Threshold:**
- Must improve at least one metric by ≥5%
- Must not degrade any metric by >5%
- Latency increase must be <100ms (unless optional like Divine Insight)

---

## Implementation Order

**Recommended sequence:**
1. **Arcane Recall** - Parent Document Retrieval (easiest, low risk)
2. **Scrying Window** - Sentence Window Retrieval (highest expected value)
3. **Mirror Image** - Multi-Query Retrieval (good recall boost)
4. **Flurry of Blows** - Query Decomposition (for complex queries)
5. **Illusory Script** - HyDE (experimental)

**Alternative sequence (by expected impact):**
1. **Scrying Window** - Sentence Window Retrieval ⭐
2. **Mirror Image** - Multi-Query Retrieval
3. **Flurry of Blows** - Query Decomposition
4. Parent Document Retrieval
5. HyDE

---

## Notes

- All techniques are **independent** and can be combined
- Some combinations may be synergistic:
  - **Scrying Window** + **Divine Insight**
  - **Mirror Image** + **Arcane Recall**
  - **Flurry of Blows** + **Divine Insight**
- Each technique will be benchmarked individually first
- Best combinations can be tested after individual evaluation
- All changes will be committed with benchmark results

---

## Questions to Consider

1. Should we test techniques individually or in combinations?
2. Do we need new test queries for complex scenarios (Flurry of Blows)?
3. What's the acceptable latency increase for quality gains?
4. Should we make all improvements optional via config flags?
5. Do we want to test on real Candlekeep data or keep using test fixtures?


---

## Rejected Techniques

### Scrying Window: Sentence Window Retrieval ❌

**Tested:** February 10, 2026

**Results vs Bardic Knowledge (9739b1e):**
- Precision: 97.3% → 50.7% (-46.6%) ⚠️⚠️
- Content Match: 71.7% → 90.6% (+18.9%) ✓
- Latency: 17.4ms → 1849ms (106x slower) ⚠️⚠️
- Success Rate: 100% → 33.3% (-66.7%)

**Issues:**
1. Sentence-based splitting creates too many small chunks
2. Dilutes semantic meaning in embeddings
3. Massive latency increase from chunk proliferation
4. Precision collapse makes it unusable

**Conclusion:**
Sentence window retrieval doesn't work well with our document structure and chunking strategy. The technique may work better with:
- Different document types (e.g., narrative text vs technical docs)
- Larger base chunk sizes
- Different embedding models optimized for shorter text

For our use case (technical documentation with markdown structure), the precision loss is unacceptable. **Not recommended.**
