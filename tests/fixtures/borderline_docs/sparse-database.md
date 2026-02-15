---
title: "Database Reminders"
description: "Short reminders for database work"
keywords: ["database", "SQL", "reminders"]
category: "design"
tags: ["database"]
---

# Database Reminders

## Schema

Normalize to 3NF unless you have a good reason not to. Use surrogate keys. Add indexes on columns used in WHERE clauses. Name tables as plural nouns. Name columns descriptively.

## Operations

Back up before migrations. Test migrations on staging first. Monitor slow queries using query logs and explain plans. Use connection pooling to reduce overhead. Set statement timeouts to prevent runaway queries from locking tables. Review index usage periodically and drop unused indexes. Partition large tables by date or category when row counts exceed millions. Use read replicas to offload reporting queries from the primary database.
