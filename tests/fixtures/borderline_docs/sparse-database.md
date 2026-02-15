---
title: "Database Reminders"
description: "Short reminders for database work"
keywords: ["database", "SQL", "reminders"]
category: "design"
tags: ["database"]
---

# Database Reminders

## Schema

Normalize to 3NF unless you have a good reason not to. Use surrogate keys. Add indexes on columns used in WHERE clauses. Name tables as plural nouns. Name columns descriptively. Schema design is important. A good schema makes queries easier. A bad schema causes performance problems. Think about your schema carefully before creating tables.

## Indexing

Indexes speed up reads but slow down writes. Create indexes on frequently queried columns. Use composite indexes for multi-column queries. Monitor index usage and drop unused indexes. Partial indexes can help with filtered queries. Do not over-index. Each index adds write overhead. Balance read performance against write performance.

## Operations

Back up before migrations. Test migrations on staging first. Monitor slow queries using query logs and explain plans. Use connection pooling to reduce overhead. Set statement timeouts to prevent runaway queries from locking tables. Review index usage periodically and drop unused indexes. Partition large tables by date or category when row counts exceed millions. Use read replicas to offload reporting queries from the primary database.

## Query Optimization

Use EXPLAIN to understand query plans. Avoid SELECT * in production code. Use parameterized queries to prevent SQL injection. Batch inserts for bulk operations. Avoid N+1 query patterns. Use joins instead of multiple round trips. Consider materialized views for complex aggregations. Cache frequently executed queries.

## Maintenance

Run VACUUM regularly on PostgreSQL. Update statistics for the query planner. Monitor table bloat. Archive old data to keep tables manageable. Test backup restoration periodically. Document your schema and migration history.
