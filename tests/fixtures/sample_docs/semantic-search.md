---
title: "Semantic Search Techniques"
description: "Methods for improving semantic search accuracy"
keywords: ["semantic search", "query preprocessing", "ranking", "relevance"]
category: "search"
tags: ["search", "ranking", "preprocessing"]
---

# Semantic Search Techniques

Semantic search goes beyond keyword matching to understand the meaning and intent behind queries.

## Query Preprocessing

### Negation Handling
Queries with negation ("without", "not", "except") can confuse embedding models. Preprocess by:
- Removing negation clauses
- Reformulating to focus on positive concepts
- Using LLM to understand intent

### Query Expansion
Expand queries with synonyms and related terms to improve recall.

## Ranking and Reranking

### Initial Retrieval
Use vector similarity to get candidate documents.

### Metadata Boosting
Boost scores based on metadata matches:
- Title matching (strong signal)
- Keyword matching
- Category relevance

### Reranking
Apply additional ranking signals:
- Recency
- Popularity
- User preferences

## Evaluation Metrics

- Precision@K: Accuracy of top K results
- Recall@K: Coverage of relevant documents in top K
- MRR: Mean Reciprocal Rank
- NDCG: Normalized Discounted Cumulative Gain
