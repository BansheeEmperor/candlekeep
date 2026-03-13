---
title: "BGE-Small-EN-v1.5 Embedding Model"
description: "BAAI bge-small-en-v1.5 embedding model characteristics and usage"
keywords: [bge-small-en-v1.5, baai, embedding, sentence-transformer, retrieval]
category: "ml"
tags: [embeddings, bge-small-en-v1.5]
---

## BGE-Small-EN-v1.5 Overview

The bge-small-en-v1.5 model from BAAI produces 384-dimensional dense embeddings.
It is optimised for English retrieval tasks and balances quality with inference
speed. The bge-small-en-v1.5 checkpoint is available via the sentence-transformers
library.

## Retrieval Performance

On MTEB benchmarks, bge-small-en-v1.5 achieves competitive retrieval scores
relative to its parameter count. The model uses a CLS token pooling strategy
and is fine-tuned with contrastive learning on large-scale retrieval datasets.

## Inference Characteristics

The bge-small-en-v1.5 model encodes a batch of 32 passages in approximately
12ms on CPU. Memory footprint is around 130MB. These characteristics make
bge-small-en-v1.5 suitable for latency-sensitive retrieval pipelines.

## Normalisation

Embeddings from bge-small-en-v1.5 should be L2-normalised before computing
cosine similarity. The model card recommends adding a query instruction prefix
for retrieval tasks: "Represent this sentence for searching relevant passages".
