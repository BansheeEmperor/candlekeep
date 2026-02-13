---
title: "Caching Strategies"
description: "Patterns and best practices for application caching"
keywords: ["cache", "performance", "redis", "memcached", "CDN"]
category: "performance"
tags: ["caching", "performance", "optimization"]
---

# Caching Strategies

## Cache Patterns

### Cache-Aside (Lazy Loading)
Application checks cache first, loads from DB on miss:
```
1. Check cache
2. If miss: Load from DB, write to cache
3. Return data
```
**Pros**: Only cache what's needed  
**Cons**: Cache miss penalty, stale data possible

### Write-Through
Write to cache and DB simultaneously:
```
1. Write to cache
2. Write to DB
3. Return success
```
**Pros**: Cache always fresh  
**Cons**: Write latency, unnecessary caching

### Write-Behind (Write-Back)
Write to cache immediately, DB asynchronously:
```
1. Write to cache
2. Queue DB write
3. Return success immediately
```
**Pros**: Fast writes  
**Cons**: Data loss risk, complexity

### Read-Through
Cache handles DB loading:
```
1. Request from cache
2. Cache loads from DB if needed
3. Return data
```
**Pros**: Simplified application code  
**Cons**: Cache library dependency

## Cache Invalidation

### Time-To-Live (TTL)
Expire entries after fixed duration:
```
SET key value EX 3600  # 1 hour TTL
```

### Event-Based
Invalidate on data changes:
```
UPDATE users SET name='John' WHERE id=123;
DELETE cache:user:123;
```

### Cache Stampede Prevention
Use locks to prevent multiple DB queries on miss:
```
1. Check cache
2. If miss: Acquire lock
3. Check cache again (double-check)
4. Load from DB
5. Write to cache
6. Release lock
```

## Cache Layers

### L1: Application Memory
In-process cache (fastest, limited size).

### L2: Distributed Cache
Redis, Memcached (shared across instances).

### L3: CDN
Edge caching for static assets (global distribution).

## Cache Key Design

Use hierarchical keys:
```
user:123:profile
user:123:orders
product:456:details
```

Include version for schema changes:
```
user:v2:123:profile
```

## Eviction Policies

- **LRU** (Least Recently Used): Remove oldest accessed
- **LFU** (Least Frequently Used): Remove least accessed
- **FIFO** (First In First Out): Remove oldest added
- **Random**: Remove random entry

## Monitoring

Track metrics:
- Hit rate (cache hits / total requests)
- Miss rate
- Eviction rate
- Memory usage
- Latency (cache vs DB)

Target: 80%+ hit rate for effective caching.
