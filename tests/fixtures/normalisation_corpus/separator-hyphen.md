---
title: "Cross-Encoder Reranking"
description: "Using cross-encoder models for re-ranking search results"
keywords: [cross-encoder, re-ranking, ms-marco, fine-tuning]
category: "retrieval"
tags: [cross-encoder, re-ranking]
---

## Cross-Encoder Architecture

A cross-encoder processes query-document pairs jointly, unlike bi-encoders which
encode them independently. The cross-encoder attends to both inputs simultaneously,
producing a relevance score directly.

## Re-Ranking Pipeline

The re-ranking stage takes candidate documents from a first-stage retriever and
re-scores them using the cross-encoder. This two-stage approach balances latency
with precision: fast retrieval followed by expensive but accurate re-ranking.

## MS-MARCO Fine-Tuning

Cross-encoder models fine-tuned on ms-marco achieve strong performance on passage
retrieval tasks. The ms-marco dataset contains real user queries paired with
human-judged relevant passages.

## Trade-Offs

Cross-encoder re-ranking adds latency proportional to the number of candidates.
The trade-off between re-ranking depth and query latency must be tuned per use case.
