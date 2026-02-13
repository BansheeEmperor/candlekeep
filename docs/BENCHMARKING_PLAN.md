# RAG Technique Combination Benchmarking Plan

## Objective

Systematically benchmark all promising technique combinations in **isolation** (without Bardic Knowledge) to understand their true individual and combined effects.

---

## Critical Testing Principle: Isolation

**Problem with Previous Tests:**
- Wild Magic Surge tested WITH Bardic Knowledge active
- Scrying Window tested WITH Bardic Knowledge active
- Cannot determine if techniques help/hurt in isolation

**Solution:**
Test each combination against **pure baseline** (78a12e9) without any other techniques active.

---

## Baseline Configuration

**Pure Baseline (78a12e9):**
- Embedding: bge-small-en-v1.5
- Chunking: Fixed-size (512 chars, 50 overlap)
- No contextual embeddings
- No reranking
- No query processing
- Metrics: P=83.3%, R=354.2%, F1=134.9%, Content=80.5%, Latency=18.3ms

---

## Groups to Benchmark

### Group 1: Bardic Knowledge (Already Tested) ✅
**Techniques:** Contextual Chunk Embeddings only

**Configuration:**
- Prepend document title + description to chunks
- No other techniques

**Results (9739b1e):**
- Precision: 83.3% → 97.3% (+14.0%)
- Content: 80.5% → 71.7% (-8.8%)
- Latency: 18.3ms → 17.4ms (-0.9ms)

**Status:** ✅ Validated, currently active

---

### Group 2: Divine Insight (Already Tested) ✅
**Techniques:** Cross-Encoder Reranking only

**Configuration:**
- Model: cross-encoder/ms-marco-MiniLM-L-6-v2
- Fetch: 3x results (15 candidates for top-5)
- Rerank: Score all pairs, return top-k

**Results (b36b6c4 with Bardic Knowledge):**
- Precision: 97.3% → 98.7% (+1.4%)
- Content: 71.7% → 86.8% (+15.1%)
- Latency: 17.4ms → 1499.6ms (+1482ms)

**Status:** ✅ Validated, optional via config

**Note:** This was tested WITH Bardic Knowledge. Should retest in isolation.

---

### Group 3: Mirror Image (Multi-Query Retrieval) 🆕
**Techniques:** Query expansion via multiple query variations

**Configuration Parameters:**
```python
{
    "num_variations": 3,           # Number of query variations to generate
    "variation_method": "llm",     # llm | synonym | template
    "merge_strategy": "union",     # union | rrf (Reciprocal Rank Fusion)
    "fetch_per_query": 10,         # Candidates per variation
    "final_top_k": 5               # Final results to return
}
```

**Parameter Rationale:**

**num_variations = 3:**
- Research shows 3-5 variations optimal
- Too few: Limited coverage
- Too many: Noise and latency
- Start with 3, can test 5 if promising

**variation_method = "llm":**
- Most sophisticated, understands semantic intent
- Alternatives: synonym (simpler), template (rule-based)
- LLM likely best quality for technical docs

**merge_strategy = "union":**
- Simple: Combine all results, deduplicate
- Alternative: RRF (Reciprocal Rank Fusion) - weighted by rank
- Start with union, test RRF if needed

**fetch_per_query = 10:**
- 3 queries × 10 results = 30 candidates
- Provides diversity without overwhelming
- Can adjust based on results

**Expected Results:**
- Precision: Neutral or slight decrease (more candidates)
- Recall: +10-15% (broader coverage)
- Content: +5-10% (more diverse matches)
- Latency: +50-100ms (LLM call + 3 searches)

---

### Group 4: Flurry of Blows (Query Decomposition) 🆕
**Techniques:** Break complex queries into sub-questions

**Configuration Parameters:**
```python
{
    "decomposition_method": "llm",     # llm | rule-based
    "max_sub_questions": 3,            # Maximum sub-questions to generate
    "fetch_per_sub": 5,                # Results per sub-question
    "merge_strategy": "weighted",      # weighted | equal | rrf
    "sub_question_weight": [0.5, 0.3, 0.2],  # Weights for sub-questions
    "final_top_k": 5
}
```

**Parameter Rationale:**

**max_sub_questions = 3:**
- Most complex queries have 2-3 distinct parts
- More than 3 suggests query too broad
- Prevents explosion of sub-queries

**decomposition_method = "llm":**
- Understands semantic relationships
- Can identify implicit sub-questions
- Better than rule-based splitting

**fetch_per_sub = 5:**
- 3 sub-questions × 5 results = 15 candidates
- Focused retrieval per sub-question
- Manageable result set

**merge_strategy = "weighted":**
- First sub-question most important (main intent)
- Later sub-questions provide context
- Weights: [0.5, 0.3, 0.2] for 3 sub-questions

**Expected Results:**
- Precision: +5-10% on complex queries
- Recall: +10-15% (comprehensive coverage)
- Content: +10-15% (addresses all parts)
- Latency: +100-200ms (LLM + multiple searches)

**Note:** Only beneficial for complex queries. Simple queries may degrade.

---

### Group 5: Illusory Script (HyDE) 🆕
**Techniques:** Hypothetical Document Embeddings

**Configuration Parameters:**
```python
{
    "generation_method": "llm",        # llm only
    "answer_length": "medium",         # short | medium | long
    "temperature": 0.7,                # LLM temperature for generation
    "fallback_to_query": True,         # Use original query if generation fails
    "final_top_k": 5
}
```

**Parameter Rationale:**

**answer_length = "medium":**
- Short (50-100 words): May lack detail
- Medium (100-200 words): Good balance
- Long (200+ words): May dilute embedding
- Start with medium (150 words)

**temperature = 0.7:**
- Not too deterministic (0.0): Want some creativity
- Not too random (1.0): Need coherent answer
- 0.7 balances creativity and coherence

**fallback_to_query = True:**
- If LLM fails or times out, use original query
- Ensures system doesn't break
- Graceful degradation

**Expected Results:**
- Precision: +5-10% on abstract queries
- Recall: Neutral (same search space)
- Content: +5-10% (better vocabulary match)
- Latency: +50-100ms (LLM generation)

**Note:** Most beneficial for abstract/conceptual queries. May hurt concrete queries.

---

### Group 6: Arcane Recall (Parent Document Retrieval) 🆕
**Techniques:** Return larger context around matched chunks

**Configuration Parameters:**
```python
{
    "expansion_strategy": "parent_section",  # parent_section | full_document | sliding_window
    "max_expansion_size": 2000,              # Max characters to return
    "include_chunk": True,                   # Include original chunk in result
    "final_top_k": 5
}
```

**Parameter Rationale:**

**expansion_strategy = "parent_section":**
- parent_section: Expand to markdown section (## header)
- full_document: Return entire document (may be too large)
- sliding_window: Fixed window around chunk
- Start with parent_section (semantic boundary)

**max_expansion_size = 2000:**
- Prevents returning entire large documents
- ~500 tokens (reasonable LLM context)
- Balances context vs token cost

**include_chunk = True:**
- Ensures matched content is present
- Provides context around match
- Helps LLM understand relevance

**Expected Results:**
- Precision: Neutral (same retrieval)
- Recall: Neutral (same retrieval)
- Content: +10-15% (more complete information)
- Latency: +5-10ms (metadata lookup + text expansion)

**Note:** Increases token usage to LLM. Trade-off: quality vs cost.

---

### Group 7: Wild Magic Surge (Hybrid Search) 🆕
**Techniques:** Combine vector similarity + BM25 keyword matching

**Configuration Parameters:**
```python
{
    "alpha": 0.8,                    # Weight for vector scores (1-alpha for BM25)
    "bm25_k1": 1.5,                  # BM25 term frequency saturation
    "bm25_b": 0.75,                  # BM25 length normalization
    "fusion_method": "weighted_sum", # weighted_sum | rrf | max
    "final_top_k": 5
}
```

**Parameter Rationale:**

**alpha = 0.8:**
- Previous test: 0.8 performed better than 0.5
- 80% vector, 20% BM25
- Vector embeddings primary, BM25 supplementary
- Can test: 0.7, 0.9 if needed

**bm25_k1 = 1.5:**
- Standard BM25 parameter
- Controls term frequency saturation
- 1.2-2.0 typical range, 1.5 is default

**bm25_b = 0.75:**
- Standard BM25 parameter
- Controls document length normalization
- 0.75 is default, works well for most corpora

**fusion_method = "weighted_sum":**
- Simple: alpha * vector + (1-alpha) * BM25
- Alternative: RRF (rank-based fusion)
- Start with weighted_sum (easier to interpret)

**Expected Results:**
- Precision: -2.6% (previous test with Bardic Knowledge)
- Recall: +5-10% (keyword matching helps)
- Content: -1.9% (previous test)
- Latency: +5-10ms (BM25 computation)

**Note:** Previous test showed degradation WITH Bardic Knowledge. Test in isolation.

---

## Two-Way Combinations

### Combo 1: Mirror Image + Divine Insight ⭐⭐⭐
**Techniques:** Query expansion + Reranking

**Configuration:**
```python
{
    # Mirror Image
    "num_variations": 3,
    "fetch_per_query": 10,
    
    # Divine Insight
    "rerank_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_top_k": 5
}
```

**Why This Combination:**
- Mirror Image: Increases recall (finds more relevant docs)
- Divine Insight: Increases precision (ranks best docs first)
- Complementary: Addresses different weaknesses
- Research-backed: Proven synergistic pattern

**Expected Results:**
- Precision: +5-10% (reranking effect)
- Recall: +15-20% (expansion effect)
- Content: +10-15% (best of both)
- Latency: ~1600ms (expansion + reranking)

---

### Combo 2: Flurry of Blows + Divine Insight ⭐⭐
**Techniques:** Query decomposition + Reranking

**Configuration:**
```python
{
    # Flurry of Blows
    "max_sub_questions": 3,
    "fetch_per_sub": 5,
    
    # Divine Insight
    "rerank_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_top_k": 5
}
```

**Why This Combination:**
- Flurry of Blows: Handles complex multi-part questions
- Divine Insight: Ranks across all sub-results
- Synergy: Comprehensive coverage + precise ranking

**Expected Results:**
- Precision: +10-15% on complex queries
- Recall: +15-20% (comprehensive)
- Content: +15-20% (addresses all parts)
- Latency: ~1700ms (decomposition + reranking)

**Note:** Test on complex queries specifically.

---

### Combo 3: Arcane Recall + Divine Insight ⭐⭐
**Techniques:** Parent document + Reranking

**Configuration:**
```python
{
    # Divine Insight (first)
    "rerank_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_top_k": 5,
    
    # Arcane Recall (second)
    "expansion_strategy": "parent_section",
    "max_expansion_size": 2000
}
```

**Why This Combination:**
- Divine Insight: Finds most relevant chunks (precision)
- Arcane Recall: Expands to full context (completeness)
- Order matters: Precision first, then expansion

**Expected Results:**
- Precision: +5-10% (reranking effect)
- Recall: Neutral (same retrieval)
- Content: +15-20% (full context)
- Latency: ~1510ms (reranking + expansion)

---

### Combo 4: Illusory Script + Divine Insight ⭐
**Techniques:** HyDE + Reranking

**Configuration:**
```python
{
    # Illusory Script
    "answer_length": "medium",
    "temperature": 0.7,
    
    # Divine Insight
    "rerank_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_top_k": 5
}
```

**Why This Combination:**
- Illusory Script: Bridges vocabulary gap
- Divine Insight: Validates actual relevance
- Synergy: Hypothetical retrieval + real validation

**Expected Results:**
- Precision: +5-10% on abstract queries
- Recall: +5-10% (better vocabulary match)
- Content: +10-15%
- Latency: ~1650ms (generation + reranking)

**Note:** Test on abstract/conceptual queries specifically.

---

### Combo 5: Wild Magic Surge + Divine Insight ⭐
**Techniques:** Hybrid search + Reranking

**Configuration:**
```python
{
    # Wild Magic Surge
    "alpha": 0.8,
    "fusion_method": "weighted_sum",
    
    # Divine Insight
    "rerank_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "rerank_top_k": 5
}
```

**Why This Combination:**
- Wild Magic Surge: Combines semantic + keyword
- Divine Insight: Precise final ranking
- Synergy: Broad retrieval + precise ranking

**Expected Results:**
- Precision: +5-10% (reranking effect)
- Recall: +10-15% (hybrid retrieval)
- Content: +5-10%
- Latency: ~1510ms (hybrid + reranking)

---

## Benchmarking Methodology

### Test Environment
- **Baseline:** Pure baseline (78a12e9) - NO Bardic Knowledge
- **Test Queries:** Same 15 queries (5 easy, 7 medium, 3 hard)
- **Test Documents:** Same 9 documents
- **Metrics:** Precision, Recall, F1, Content Match, Latency, Success Rate

### Isolation Strategy

**Critical:** Each test must start from pure baseline.

```bash
# 1. Checkout baseline commit
git checkout 78a12e9

# 2. Implement ONLY the technique being tested
# (create feature branch)

# 3. Run benchmark
CANDLEKEEP_RERANK=false pytest tests/test_benchmark.py -v -s

# 4. Record results

# 5. Revert to baseline for next test
git checkout 78a12e9
```

### Test Order

**Phase 1: Individual Techniques (Isolation)**
1. Mirror Image only
2. Flurry of Blows only
3. Illusory Script only
4. Arcane Recall only
5. Wild Magic Surge only
6. Divine Insight only (retest in isolation)

**Phase 2: Two-Way Combinations**
7. Mirror Image + Divine Insight
8. Flurry of Blows + Divine Insight
9. Arcane Recall + Divine Insight
10. Illusory Script + Divine Insight
11. Wild Magic Surge + Divine Insight

**Phase 3: Comparison**
12. Bardic Knowledge (current best)
13. Best two-way combo vs Bardic Knowledge
14. Bardic Knowledge + Best two-way combo (if promising)

---

## Phase 4: Parameter Variations

Test promising techniques with different parameters:

### Wild Magic Surge - Alpha Variations
```python
# Test different vector/BM25 weights
alpha_values = [0.7, 0.8, 0.9]
# Expected: Higher alpha (more vector weight) performs better
```

### Mirror Image - Variation Count
```python
# Test different numbers of query variations
num_variations = [3, 5]
# Expected: 5 may improve recall but increase latency
```

### Flurry of Blows - Sub-Question Count
```python
# Test different decomposition depths
max_sub_questions = [2, 3]
# Expected: 2 faster, 3 more comprehensive
```

---

## Phase 5: Three-Way Combinations

**Only test if two-way shows ≥10% improvement**

### Combo A: Mirror Image + Wild Magic Surge + Divine Insight
**Techniques:** Query expansion + Hybrid search + Reranking

**Configuration:**
```python
{
    "num_variations": 3,
    "alpha": 0.8,
    "rerank_top_k": 5
}
```

**Rationale:**
- Mirror Image: Broad query coverage
- Wild Magic Surge: Semantic + keyword matching
- Divine Insight: Precise final ranking
- Full pipeline: Expansion → Hybrid retrieval → Reranking

**Expected:**
- Precision: +10-15%
- Recall: +20-25%
- Latency: ~1600ms (acceptable if quality gain ≥15%)

---

### Combo B: Flurry of Blows + Arcane Recall + Divine Insight
**Techniques:** Decomposition + Parent doc + Reranking

**Configuration:**
```python
{
    "max_sub_questions": 3,
    "expansion_strategy": "parent_section",
    "rerank_top_k": 5
}
```

**Rationale:**
- Flurry of Blows: Handle complex questions
- Arcane Recall: Full context per sub-question
- Divine Insight: Rank across all contexts
- Full pipeline: Decompose → Retrieve → Expand → Rerank

**Expected:**
- Precision: +15-20% on complex queries
- Content: +20-25%
- Latency: ~1800ms (acceptable for complex query type)

---

### Combo C: Mirror Image + Arcane Recall + Divine Insight
**Techniques:** Query expansion + Parent doc + Reranking

**Configuration:**
```python
{
    "num_variations": 3,
    "expansion_strategy": "parent_section",
    "rerank_top_k": 5
}
```

**Rationale:**
- Mirror Image: Broad coverage
- Arcane Recall: Full context
- Divine Insight: Precise ranking
- Full pipeline: Expand → Retrieve → Expand context → Rerank

**Expected:**
- Precision: +10-15%
- Content: +20-25%
- Latency: ~1600ms

---

### Combo D: Illusory Script + Arcane Recall + Divine Insight
**Techniques:** HyDE + Parent doc + Reranking

**Configuration:**
```python
{
    "answer_length": "medium",
    "expansion_strategy": "parent_section",
    "rerank_top_k": 5
}
```

**Rationale:**
- Illusory Script: Bridge vocabulary gap
- Arcane Recall: Full context
- Divine Insight: Validate relevance
- Full pipeline: Generate hypothesis → Retrieve → Expand → Rerank

**Expected:**
- Precision: +10-15% on abstract queries
- Content: +20-25%
- Latency: ~1700ms (acceptable for abstract query type)

---

## Phase 6: Query-Type-Specific Testing

### Classify Existing Test Queries

**Simple (Direct factual):**
1. "What is semantic search?"
2. "vector database"
3. "database normalization"

**Broad (Exploratory):**
4. "REST API design"
5. "How should I implement caching?"
6. "cache eviction policies"

**Complex (Multi-part):**
7. "How do I handle negation in search queries?"
8. "What are microservices communication patterns?"
9. "How do microservices handle data consistency?"
10. "How do I design a scalable API with proper caching?"

**Context (Explanatory):**
11. "What's the difference between authentication and authorization?"
12. "When should I denormalize a database?"

**Abstract (Conceptual):**
13. "OAuth 2.0 flows"

**Keyword (Technical terms):**
14. "JWT tokens" (in "What are the security considerations for JWT tokens?")

### Create Additional Test Queries

**Need more:**
- Abstract queries (only 1 currently)
- Keyword queries (only 1 currently)

**Proposed additions:**

**Abstract:**
- "Design patterns for distributed systems"
- "Principles of API versioning"
- "Microservices architecture trade-offs"

**Keyword:**
- "HNSW index performance"
- "BM25 ranking algorithm"
- "CORS preflight requests"

**Total:** 15 existing + 6 new = 21 queries

---

## Latency Tiers

### Tier 1: Fast (<100ms)
- **Use case:** All queries, real-time
- **Techniques:** Bardic Knowledge, Arcane Recall
- **Status:** Production-ready

### Tier 2: Interactive (100-500ms)
- **Use case:** Most queries, acceptable delay
- **Techniques:** Mirror Image, Illusory Script, Wild Magic Surge
- **Status:** Production-ready with user feedback

### Tier 3: Standard (500-1000ms)
- **Use case:** Complex queries, batch processing
- **Techniques:** Flurry of Blows, two-way combos without reranking
- **Status:** Acceptable for specific query types

### Tier 4: Extended (1000-2000ms)
- **Use case:** High-value queries, fallback scenarios
- **Techniques:** Divine Insight, three-way combos
- **Conditions:**
  - Quality gain ≥15%
  - Specific query types only
  - Fallback when other methods fail
- **Status:** Acceptable with routing logic

### Tier 5: Batch Only (>2000ms)
- **Use case:** Offline processing only
- **Status:** Not acceptable for interactive use

---

## Success Criteria

### Individual Techniques
**Accept if:**
- Improves at least one metric by ≥5% vs baseline
- Does not degrade any metric by >10%
- Latency acceptable for use case (<2000ms)

### Two-Way Combinations
**Accept if:**
- Improves at least one metric by ≥10% vs baseline
- Does not degrade any metric by >10%
- Outperforms both individual techniques
- Latency acceptable (<2000ms)

### Comparison to Bardic Knowledge
**Accept if:**
- Matches or exceeds Bardic Knowledge quality
- OR provides complementary benefits (e.g., better recall)
- OR works better for specific query types

---

## Expected Timeline

**Phase 1 (Individual):** 6 techniques × 2 hours = 12 hours
- Implementation: 1 hour per technique
- Benchmarking: 30 min per technique
- Analysis: 30 min per technique

**Phase 2 (Combinations):** 5 combinations × 1.5 hours = 7.5 hours
- Implementation: 30 min per combo (reuse components)
- Benchmarking: 30 min per combo
- Analysis: 30 min per combo

**Phase 3 (Comparison):** 3 hours
- Comparative analysis
- Documentation
- Recommendations

**Phase 4 (Parameter Variations):** 3 techniques × 1 hour = 3 hours
- Test alpha variations for Wild Magic Surge
- Test variation counts for Mirror Image
- Test sub-question counts for Flurry of Blows

**Phase 5 (Three-Way Combos):** 4 combinations × 2 hours = 8 hours
- Only if two-way shows ≥10% improvement
- Implementation: 1 hour per combo
- Benchmarking: 30 min per combo
- Analysis: 30 min per combo

**Phase 6 (Query-Type Testing):** 4 hours
- Create 6 additional test queries
- Classify all 21 queries
- Benchmark per query type
- Identify specialized techniques

**Phase 7 (Automatic Classification):** 3 hours
- Implement rule-based classifier
- Test classification accuracy
- Integrate with search function

**Total:** ~40.5 hours (~5 days)
- **Minimum (Phases 1-3):** 22.5 hours (~3 days)
- **Full (All phases):** 40.5 hours (~5 days)

---

## Automatic Query Classification

### Implementation

```python
def classify_query_type(query: str) -> str:
    """
    Automatically classify query type using rule-based heuristics.
    
    Returns: simple | broad | complex | abstract | context | keyword
    """
    query_lower = query.lower()
    words = query_lower.split()
    
    # Keyword: Contains acronyms or technical terms (2+ uppercase letters)
    if re.search(r'\b[A-Z]{2,}\b', query):
        return "keyword"
    
    # Complex: Multiple questions or "and" connecting distinct concepts
    if " and " in query_lower and len(words) > 8:
        # Check if "and" connects distinct concepts (not just adjectives)
        and_index = words.index("and")
        if and_index > 2 and and_index < len(words) - 2:
            return "complex"
    
    # Complex: Multiple question marks
    if query.count("?") > 1:
        return "complex"
    
    # Context: "Why" or "explain" or "difference" questions
    context_starters = ["why", "explain", "what's the difference", 
                       "what is the difference", "compare"]
    if any(query_lower.startswith(starter) for starter in context_starters):
        return "context"
    
    # Abstract: Contains conceptual keywords
    abstract_keywords = ["principle", "pattern", "design", "architecture",
                        "philosophy", "approach", "strategy", "concept",
                        "paradigm", "methodology", "framework"]
    if any(kw in query_lower for kw in abstract_keywords):
        return "abstract"
    
    # Broad: "How to" or "best practices" or "implement"
    broad_indicators = ["how to", "how do i", "how should i", 
                       "best practice", "implement", "guide"]
    if any(indicator in query_lower for indicator in broad_indicators):
        return "broad"
    
    # Simple: Short queries (≤5 words) or "what is" questions
    if len(words) <= 5 or query_lower.startswith("what is"):
        return "simple"
    
    # Default: Simple
    return "simple"
```

### Classification Accuracy Testing

Test on existing 15 queries:
```python
test_cases = [
    ("What is semantic search?", "simple"),
    ("vector database", "simple"),
    ("REST API design", "broad"),
    ("database normalization", "simple"),
    ("How do I handle negation in search queries?", "broad"),
    ("What are microservices communication patterns?", "broad"),
    ("How should I implement caching?", "broad"),
    ("What's the difference between authentication and authorization?", "context"),
    ("When should I denormalize a database?", "context"),
    ("How do I design a scalable API with proper caching?", "complex"),
    ("What are the security considerations for JWT tokens?", "keyword"),
    ("How do microservices handle data consistency?", "broad"),
    ("OAuth 2.0 flows", "keyword"),
    ("cache eviction policies", "simple"),
]

# Expected accuracy: >80%
```

### Fallback Logic

```python
def search_with_routing(
    query: str,
    n_results: int = 5,
    category: str | None = None,
    query_type: str | None = None  # Optional override
) -> str:
    """
    Search with automatic query-type routing.
    
    Fallback chain:
    1. Try optimal technique for query type
    2. If fails or 0 results, try Bardic Knowledge (fast fallback)
    3. If still fails, try Divine Insight (quality fallback)
    """
    # Classify if not provided
    if query_type is None:
        query_type = classify_query_type(query)
    
    # Route to optimal technique
    try:
        results = route_by_query_type(query, n_results, category, query_type)
        
        if results and len(results) > 0:
            return results
    except Exception as e:
        log_error(f"Primary technique failed: {e}")
    
    # Fallback 1: Bardic Knowledge (fast, reliable)
    try:
        results = search_simple(query, n_results, category)
        if results and len(results) > 0:
            return results
    except Exception as e:
        log_error(f"Fallback 1 failed: {e}")
    
    # Fallback 2: Divine Insight (slow but high quality)
    try:
        results = search_with_reranking(query, n_results, category)
        return results
    except Exception as e:
        log_error(f"Fallback 2 failed: {e}")
        return "No results found."
```

---

## Documentation Requirements

For each test, record:
1. **Configuration:** All parameters used
2. **Results:** All metrics vs baseline
3. **Analysis:** What worked, what didn't, why
4. **Commit Hash:** For reproducibility
5. **Observations:** Any unexpected behavior

---

## Risk Mitigation

**Risk:** Tests take too long
**Mitigation:** Prioritize high-value combinations (Mirror Image + Divine Insight first)

**Risk:** Implementation bugs affect results
**Mitigation:** Unit test each technique before benchmarking

**Risk:** Results inconsistent
**Mitigation:** Run each benchmark 3 times, average results

**Risk:** Baseline drift
**Mitigation:** Always start from same commit (78a12e9)

---

## Next Steps

1. **Review this plan** - Validate approach and parameters
2. **Implement Mirror Image** - Start with highest-priority technique
3. **Benchmark in isolation** - Test against pure baseline
4. **Document results** - Record all metrics and observations
5. **Iterate** - Continue with remaining techniques

---

## Questions for Consideration

1. ✅ **Should we test with different parameter values?**
   - YES - Test alpha=[0.7, 0.8, 0.9] for Wild Magic Surge
   - Test num_variations=[3, 5] for Mirror Image
   - Test max_sub_questions=[2, 3] for Flurry of Blows
   - Document all parameter variations tested

2. ✅ **Should we create query-type-specific test sets?**
   - YES - Classify existing 15 queries by type
   - Create additional test queries for underrepresented types
   - Benchmark per query type to identify specialized techniques

3. ✅ **Should we test three-way combinations?**
   - YES - If two-way shows promise (≥10% improvement)
   - Document all new groups (≥2 techniques)
   - Focus on synergistic combinations

4. ✅ **Classification method?**
   - AUTOMATIC - Implement rule-based classifier
   - No agent input required
   - Can be overridden if needed

5. ✅ **Latency threshold?**
   - **Standard: 1000ms (1 second)** - For general use
   - **Extended: >1000ms allowed IF:**
     - Technique shows exceptional quality gains (≥15%)
     - Specific to certain query types (agent can route)
     - Fallback when other methods fail/return 0 results
   - Document latency tier for each technique
