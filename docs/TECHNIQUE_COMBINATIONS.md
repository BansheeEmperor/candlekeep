# RAG Technique Combination Analysis

## Pipeline Stages

RAG techniques operate at different stages of the pipeline:

1. **Ingestion** (offline): Document → Chunks → Embeddings → Store
2. **Query Processing** (online): User query → Query transformation
3. **Retrieval** (online): Search vector DB → Get candidates
4. **Post-Processing** (online): Rerank/filter/expand results
5. **Return** (online): Send to LLM

---

## Technique Classification by Stage

### Stage 1: Ingestion (Mutually Exclusive)
- **Bardic Knowledge** (Contextual Embeddings) - Adds metadata context to chunks
- **Scrying Window** (Sentence Window) - Changes chunking strategy
- **Conflict:** Can't easily combine both without careful design

### Stage 2: Query Processing (Can Combine)
- **Mirror Image** (Multi-Query) - Generates query variations
- **Flurry of Blows** (Query Decomposition) - Breaks into sub-questions
- **Illusory Script** (HyDE) - Generates hypothetical answers
- **Synergy:** Can chain or parallel these transformations

### Stage 3: Retrieval (Mutually Exclusive)
- **Wild Magic Surge** (Hybrid Search) - Combines vector + BM25
- **Conflict:** Only one retrieval strategy at a time

### Stage 4: Post-Processing (Can Combine)
- **Divine Insight** (Reranking) - Reorders results by relevance
- **Arcane Recall** (Parent Document) - Expands to larger context
- **Synergy:** Can apply sequentially

---

## Synergistic Combinations

### Group 1: Query Expansion + Reranking ⭐⭐⭐
**Techniques:** Mirror Image + Divine Insight

**Why it works:**
- Mirror Image increases recall (finds more relevant docs)
- Divine Insight increases precision (ranks best docs first)
- Addresses complementary weaknesses

**Expected benefit:** +15-20% recall, +5% precision

**Research support:** "Query expansion broadens search terms... Re-ranking algorithms reorder initial search results... Together, these techniques create more robust retrieval systems." (markaicode.com)

**Implementation:**
```
1. Generate 3-5 query variations (Mirror Image)
2. Search with all variations → get 50 candidates
3. Merge and deduplicate results
4. Rerank with cross-encoder (Divine Insight)
5. Return top-5
```

---

### Group 2: Query Decomposition + Reranking ⭐⭐
**Techniques:** Flurry of Blows + Divine Insight

**Why it works:**
- Flurry of Blows handles complex multi-part questions
- Each sub-question retrieves focused results
- Divine Insight ranks across all sub-results

**Expected benefit:** +20% on complex queries

**Implementation:**
```
1. Decompose query into sub-questions (Flurry of Blows)
2. Search each sub-question → get candidates per sub-question
3. Merge all results
4. Rerank combined pool (Divine Insight)
5. Return top-5
```

---

### Group 3: Parent Document + Reranking ⭐⭐
**Techniques:** Arcane Recall + Divine Insight

**Why it works:**
- Divine Insight finds most relevant chunks
- Arcane Recall provides full context around those chunks
- Precision first, then context expansion

**Expected benefit:** +10% content match, maintains precision

**Implementation:**
```
1. Search and get candidates
2. Rerank to find best chunks (Divine Insight)
3. Expand top-5 chunks to parent documents (Arcane Recall)
4. Return expanded contexts
```

---

### Group 4: HyDE + Reranking ⭐
**Techniques:** Illusory Script + Divine Insight

**Why it works:**
- HyDE bridges vocabulary gap with hypothetical answer
- Divine Insight validates actual relevance
- Good for abstract/conceptual queries

**Expected benefit:** +10% on abstract queries

**Implementation:**
```
1. Generate hypothetical answer (Illusory Script)
2. Embed and search with hypothetical
3. Get candidates
4. Rerank with original query (Divine Insight)
5. Return top-5
```

---

### Group 5: Multi-Query + Parent Document ⭐
**Techniques:** Mirror Image + Arcane Recall

**Why it works:**
- Mirror Image casts wide net with variations
- Arcane Recall provides full context for matches
- Good for exploratory queries

**Expected benefit:** +15% recall, +10% content match

**Implementation:**
```
1. Generate query variations (Mirror Image)
2. Search all variations
3. Merge and deduplicate
4. Expand to parent documents (Arcane Recall)
5. Return top-5 expanded contexts
```

---

## Three-Way Combinations

### Combo A: Query Expansion + Hybrid + Reranking ⭐⭐⭐
**Techniques:** Mirror Image + Wild Magic Surge + Divine Insight

**Why it works:**
- Mirror Image: Broad query coverage
- Wild Magic Surge: Combines semantic + keyword matching
- Divine Insight: Precise final ranking

**Expected benefit:** Best of all worlds - high recall + high precision

**Trade-off:** Higher latency (~1.5s)

---

### Combo B: Query Decomposition + Parent + Reranking ⭐⭐
**Techniques:** Flurry of Blows + Arcane Recall + Divine Insight

**Why it works:**
- Flurry of Blows: Handles complex questions
- Arcane Recall: Provides full context per sub-question
- Divine Insight: Ranks across all contexts

**Expected benefit:** Best for complex, multi-part questions

**Trade-off:** Higher latency (~200ms + reranking)

---

## Combinations to AVOID

### ❌ Bardic Knowledge + Scrying Window
**Why:** Both modify chunking strategy - conflict at ingestion stage

### ❌ Mirror Image + Flurry of Blows (without careful design)
**Why:** Explosion of queries (5 variations × 3 sub-questions = 15 searches)
**Could work:** If you decompose first, then expand only the main sub-questions

### ❌ HyDE + Mirror Image
**Why:** Redundant query expansion - both transform the query
**Could work:** Use HyDE for abstract queries, Mirror Image for concrete ones

---

## Recommended Testing Order

### Phase 1: Two-Way Combinations (High Priority)
1. **Mirror Image + Divine Insight** ⭐⭐⭐ (query expansion + reranking)
2. **Arcane Recall + Divine Insight** ⭐⭐ (parent doc + reranking)
3. **Flurry of Blows + Divine Insight** ⭐⭐ (decomposition + reranking)

### Phase 2: Alternative Two-Way
4. **Mirror Image + Arcane Recall** ⭐ (expansion + context)
5. **Illusory Script + Divine Insight** ⭐ (HyDE + reranking)

### Phase 3: Three-Way (If two-way shows promise)
6. **Mirror Image + Wild Magic Surge + Divine Insight** ⭐⭐⭐
7. **Flurry of Blows + Arcane Recall + Divine Insight** ⭐⭐

---

## Implementation Strategy

### Approach 1: Sequential Testing
- Test each two-way combination individually
- Compare against Bardic Knowledge baseline
- Pick best performer
- Test three-way with best two-way

### Approach 2: Parallel Testing (Recommended)
- Implement all Stage 2 techniques (Mirror Image, Flurry of Blows, Illusory Script)
- Implement all Stage 4 techniques (Arcane Recall)
- Test all combinations in matrix:
  ```
  Stage 2 × Stage 4 × Divine Insight
  = 3 × 2 × 2 = 12 combinations
  ```

### Approach 3: Use-Case Specific
- **Simple queries:** Bardic Knowledge + Divine Insight (current best)
- **Broad queries:** Mirror Image + Divine Insight
- **Complex queries:** Flurry of Blows + Divine Insight
- **Abstract queries:** Illusory Script + Divine Insight
- **Context-heavy:** Arcane Recall + Divine Insight

---

## Success Criteria

For a combination to be accepted:
1. **Must improve** at least one metric by ≥5% vs Bardic Knowledge
2. **Must not degrade** any metric by >5%
3. **Latency** must be acceptable for use case:
   - Real-time: <100ms
   - Interactive: <500ms
   - Batch: <2000ms

---

## Next Steps

1. Implement **Mirror Image** (Multi-Query Retrieval) first
2. Test **Mirror Image + Divine Insight** combination
3. If successful (≥5% improvement), continue with other Stage 2 techniques
4. If unsuccessful, try **Arcane Recall** (simpler, lower risk)
5. Build combination matrix once individual techniques validated


---

## Adaptive RAG: Query-Specific Routing

### Concept
Different query types benefit from different technique combinations. Instead of one-size-fits-all, route queries to optimal technique stacks based on characteristics.

### Query Classification

#### 1. Simple/Direct Queries
**Characteristics:**
- Single concept
- Clear intent
- Factual lookup
- Examples: "What is caching?", "JWT token expiration"

**Optimal Stack:** Bardic Knowledge only
- Precision: 97.3%
- Latency: 17ms
- Why: Already excellent, no need for complexity

---

#### 2. Broad/Exploratory Queries
**Characteristics:**
- Multiple related concepts
- Open-ended
- "How to" questions
- Examples: "How to implement authentication?", "Best practices for API design"

**Optimal Stack:** Mirror Image + Divine Insight
- Expected: +15% recall, +5% precision
- Latency: ~100ms
- Why: Query expansion finds diverse relevant docs, reranking picks best

---

#### 3. Complex/Multi-Part Queries
**Characteristics:**
- Multiple distinct questions
- Requires synthesis
- "X and Y" patterns
- Examples: "How do microservices handle authentication and caching?", "Compare REST vs GraphQL"

**Optimal Stack:** Flurry of Blows + Divine Insight
- Expected: +20% on complex queries
- Latency: ~200ms
- Why: Decomposition handles each part, reranking synthesizes

---

#### 4. Abstract/Conceptual Queries
**Characteristics:**
- High-level concepts
- Vocabulary mismatch likely
- Theoretical questions
- Examples: "Design patterns for scalability", "Principles of distributed systems"

**Optimal Stack:** Illusory Script + Divine Insight
- Expected: +10% on abstract queries
- Latency: ~150ms
- Why: HyDE bridges vocabulary gap, reranking validates

---

#### 5. Context-Heavy Queries
**Characteristics:**
- Needs surrounding information
- "Why" questions
- Requires full explanation
- Examples: "Why use OAuth over JWT?", "Explain database normalization"

**Optimal Stack:** Arcane Recall + Divine Insight
- Expected: +10% content match
- Latency: ~50ms
- Why: Parent document provides full context

---

#### 6. Keyword-Specific Queries
**Characteristics:**
- Exact terms matter
- Technical jargon
- Acronyms
- Examples: "BM25 algorithm", "HNSW index"

**Optimal Stack:** Wild Magic Surge + Divine Insight
- Expected: Better keyword matching
- Latency: ~50ms
- Why: BM25 excels at exact term matching

---

## Implementation: Query Router

### Option 1: Agent-Driven (Explicit Tags)
Agent analyzes query and passes tag to MCP tool:

```python
# MCP tool signature
def search(
    query: str, 
    n_results: int = 5,
    category: str | None = None,
    query_type: str = "simple"  # NEW PARAMETER
) -> str:
    """
    Search with adaptive technique selection.
    
    Args:
        query_type: One of:
            - "simple": Direct factual queries (default)
            - "broad": Exploratory queries
            - "complex": Multi-part questions
            - "abstract": Conceptual queries
            - "context": Needs full explanation
            - "keyword": Exact term matching
    """
    # Route to appropriate technique stack
    if query_type == "simple":
        return search_simple(query, n_results, category)
    elif query_type == "broad":
        return search_broad(query, n_results, category)
    elif query_type == "complex":
        return search_complex(query, n_results, category)
    # ... etc
```

**Agent prompt addition:**
```
Before searching, classify the query:
- simple: Single concept, factual lookup
- broad: Multiple concepts, exploratory
- complex: Multiple distinct questions
- abstract: High-level, conceptual
- context: Needs full explanation
- keyword: Exact terms/acronyms important

Pass classification as query_type parameter.
```

---

### Option 2: Automatic Classification (No Agent Input)
System automatically detects query type:

```python
def classify_query(query: str) -> str:
    """Automatically classify query type."""
    query_lower = query.lower()
    
    # Complex: Multiple questions or "and" patterns
    if " and " in query_lower or "?" in query[:-1]:
        return "complex"
    
    # Abstract: Contains conceptual keywords
    abstract_keywords = ["principle", "pattern", "design", "architecture", 
                         "philosophy", "approach", "strategy"]
    if any(kw in query_lower for kw in abstract_keywords):
        return "abstract"
    
    # Context: "Why" or "explain" questions
    if query_lower.startswith(("why", "explain", "how does")):
        return "context"
    
    # Keyword: Contains acronyms or technical terms
    if re.search(r'\b[A-Z]{2,}\b', query):  # Acronyms
        return "keyword"
    
    # Broad: "How to" or "best practices"
    if "how to" in query_lower or "best practice" in query_lower:
        return "broad"
    
    # Default: Simple
    return "simple"

def search(query: str, n_results: int = 5, category: str | None = None) -> str:
    """Search with automatic adaptive routing."""
    query_type = classify_query(query)
    # Route based on classification...
```

---

### Option 3: Hybrid (Agent Override)
Automatic classification with optional agent override:

```python
def search(
    query: str,
    n_results: int = 5,
    category: str | None = None,
    query_type: str | None = None  # Optional override
) -> str:
    """
    Search with adaptive routing.
    
    If query_type not provided, automatically classifies.
    Agent can override with explicit query_type.
    """
    if query_type is None:
        query_type = classify_query(query)
    
    # Route based on classification...
```

---

## Configuration Matrix

| Query Type | Techniques | Latency | When to Use |
|------------|-----------|---------|-------------|
| **simple** | Bardic Knowledge | 17ms | Default, factual lookups |
| **broad** | Mirror Image + Divine Insight | ~100ms | Exploratory, "how to" |
| **complex** | Flurry of Blows + Divine Insight | ~200ms | Multi-part questions |
| **abstract** | Illusory Script + Divine Insight | ~150ms | Conceptual, high-level |
| **context** | Arcane Recall + Divine Insight | ~50ms | "Why", explanations |
| **keyword** | Wild Magic Surge + Divine Insight | ~50ms | Acronyms, exact terms |

---

## Benefits of Adaptive Routing

1. **Optimal Performance:** Each query gets best-suited technique
2. **Latency Control:** Simple queries stay fast (17ms)
3. **Quality Gains:** Complex queries get specialized handling
4. **Resource Efficiency:** Don't waste compute on simple queries
5. **Measurable:** Can track performance per query type

---

## Testing Strategy

### Phase 1: Implement Routing
1. Add `query_type` parameter to search function
2. Implement classification logic (automatic or agent-driven)
3. Create separate search functions per type

### Phase 2: Benchmark Per Type
1. Classify existing 15 test queries
2. Run each with its optimal stack
3. Compare vs one-size-fits-all approach

### Phase 3: Validate Classification
1. Test automatic classification accuracy
2. Compare agent-driven vs automatic
3. Measure latency vs quality trade-offs

---

## Example Query Routing

```python
# Test queries classified:
queries = {
    "What is semantic search?": "simple",
    "How to implement caching?": "broad", 
    "How do microservices handle authentication and caching?": "complex",
    "Design patterns for scalability": "abstract",
    "Why use OAuth over JWT?": "context",
    "BM25 algorithm": "keyword"
}

# Expected improvements:
# - simple: No change (already optimal)
# - broad: +15% recall
# - complex: +20% accuracy
# - abstract: +10% precision
# - context: +10% content match
# - keyword: +5% precision
```

---

## Recommendation

**Start with Option 1 (Agent-Driven)** because:
1. More accurate classification (LLM understands intent)
2. Easier to debug (explicit tags)
3. Can gather data for training automatic classifier later
4. Agent already has context about user's needs

**Future:** Migrate to Option 3 (Hybrid) once we have:
- Enough data to train automatic classifier
- Validated classification accuracy
- Proven technique combinations per type
