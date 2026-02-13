---
title: "Database Schema Design"
description: "Principles for designing relational database schemas"
keywords: ["database", "schema", "SQL", "normalization", "indexes"]
category: "design"
tags: ["database", "sql", "schema", "data-modeling"]
---

# Database Schema Design

## Normalization

### First Normal Form (1NF)
- Atomic values (no arrays or lists in columns)
- Each column has unique name
- Order doesn't matter

### Second Normal Form (2NF)
- Must be in 1NF
- No partial dependencies (all non-key columns depend on entire primary key)

### Third Normal Form (3NF)
- Must be in 2NF
- No transitive dependencies (non-key columns don't depend on other non-key columns)

## Primary Keys

Choose appropriate primary key strategy:
- **Natural keys**: Existing unique identifier (email, SSN)
- **Surrogate keys**: Auto-generated ID (UUID, auto-increment)
- **Composite keys**: Multiple columns form unique identifier

## Indexes

Create indexes for:
- Primary keys (automatic)
- Foreign keys
- Frequently queried columns
- Columns used in WHERE, JOIN, ORDER BY

Trade-offs:
- **Pros**: Faster reads
- **Cons**: Slower writes, more storage

## Relationships

### One-to-Many
```sql
CREATE TABLE users (
  id INT PRIMARY KEY,
  name VARCHAR(100)
);

CREATE TABLE orders (
  id INT PRIMARY KEY,
  user_id INT,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Many-to-Many
Use junction table:
```sql
CREATE TABLE students (id INT PRIMARY KEY, name VARCHAR(100));
CREATE TABLE courses (id INT PRIMARY KEY, name VARCHAR(100));

CREATE TABLE enrollments (
  student_id INT,
  course_id INT,
  PRIMARY KEY (student_id, course_id),
  FOREIGN KEY (student_id) REFERENCES students(id),
  FOREIGN KEY (course_id) REFERENCES courses(id)
);
```

## Denormalization

When to denormalize:
- Read-heavy workloads
- Complex joins are slow
- Acceptable data redundancy

Techniques:
- Materialized views
- Cached aggregates
- Duplicate frequently accessed data
