---
title: "PostgreSQL Internals"
description: "PostgreSQL storage engine, MVCC, and query planner internals"
keywords: [postgresql, mvcc, vacuum, wal, query-planner]
category: "database"
tags: [postgresql, storage]
---

## PostgreSQL Storage Engine

PostgreSQL uses a heap-based storage model. Each table is stored as a heap file
divided into 8KB pages. PostgreSQL's MVCC implementation keeps old row versions
in the heap rather than a separate undo log.

## MVCC and Vacuum

PostgreSQL's multi-version concurrency control creates new row versions on update
rather than modifying in place. Dead tuples accumulate until the vacuum process
reclaims space. Autovacuum runs automatically to prevent table bloat.

## Write-Ahead Log

PostgreSQL's WAL ensures durability. Every change is written to the WAL before
the data page is modified. On crash recovery, PostgreSQL replays WAL records to
restore consistency.

## Query Planner

The PostgreSQL query planner uses statistics collected by ANALYZE to estimate
row counts and choose join strategies. The planner considers sequential scans,
index scans, and bitmap index scans based on cost estimates.
