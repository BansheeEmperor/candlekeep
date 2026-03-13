---
title: "In-Memory Caching"
description: "In-memory cache patterns, eviction policies, and read-through strategies"
keywords: [in-memory, cache, lru, read-through, write-behind, eviction]
category: "performance"
tags: [caching, in-memory]
---

## In-Memory Cache Architecture

An in-memory cache stores frequently accessed data in RAM to reduce latency.
In-memory access is orders of magnitude faster than disk or network I/O.
The in-memory tier sits between the application and the backing store.

## Eviction Policies

When the in-memory cache reaches capacity, an eviction policy determines which
entries to remove. LRU evicts the least-recently-used entry. LFU evicts the
least-frequently-used. TTL-based eviction removes entries after a fixed duration
regardless of access pattern.

## Read-Through and Write-Behind

A read-through cache loads missing entries from the backing store automatically.
A write-behind cache buffers writes in-memory and flushes asynchronously,
improving write throughput at the cost of durability.

## Cache Stampede

Cache stampede occurs when many requests simultaneously miss the in-memory cache
for the same key. Probabilistic early expiration and request coalescing mitigate
stampede by preventing concurrent regeneration of the same cached value.
