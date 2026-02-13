---
title: Database Replication
description: Detailed technical documentation on database replication concepts, architectures, and implementation details.
keywords:
  - database
  - replication
  - primary-replica
  - multi-primary
  - synchronous
  - asynchronous
  - conflict resolution
  - failover
category: databases
tags:
  - replication
  - high availability
  - scalability
  - fault tolerance
---

## Database Replication

Database replication is the process of maintaining multiple copies of a database on different servers or nodes. This provides several key benefits:

- **High Availability**: If one database server fails, the application can seamlessly failover to another replica, minimizing downtime.
- **Scalability**: Read queries can be load-balanced across multiple replicas, improving overall throughput.
- **Disaster Recovery**: Replication allows you to maintain offsite backups of your data in case of a regional disaster.

There are several different replication architectures and approaches, each with their own tradeoffs. This document will cover the key concepts in detail.

## Primary-Replica Replication

The most common replication architecture is primary-replica, also known as master-slave replication. In this model, there is a single primary (or master) database that accepts all write queries. Changes are then asynchronously replicated to one or more read-only replica (or slave) databases.

### Architecture

The high-level architecture of a primary-replica replication system looks like this:

```
+-------------+    +--------------+
|   Primary   |    |   Replica 1  |
|   Database  |    |   Database   |
+-------------+    +--------------+
       |                   |
       |                   |
+-------------+    +--------------+
|   Replica 2  |    |   Replica 3  |
|   Database   |    |   Database   |
+-------------+    +--------------+
```

1. The application sends all write queries to the primary database.
2. The primary database applies the changes to its local data.
3. The primary database then asynchronously replicates the changes to each of the replica databases.
4. Clients can query any of the replica databases for read-only operations, distributing the load.

### Replication Process

The replication process typically works as follows:

1. **Change Capture**: The primary database tracks all changes to its data, usually by maintaining a transaction log or binary log.
2. **Change Transmission**: The changes are then sent from the primary to the replica databases, often via a push or pull mechanism.
3. **Change Application**: The replica databases apply the changes to their local data, keeping them in sync with the primary.

Here's a sample configuration for MySQL primary-replica replication:

```
# my.cnf (Primary)
server-id=1
log-bin=mysql-bin
binlog-format=row

# my.cnf (Replica)
server-id=2
relay-log=mysql-relay-bin
read-only=1
```

### Failover and Switchover

If the primary database fails, the replication system needs to perform a failover operation to promote one of the replicas to become the new primary. This is typically an automated process, but may require manual intervention in some cases.

Alternatively, you can perform a manual switchover, where you intentionally promote a replica to become the new primary. This is useful for maintenance operations or to rebalance your infrastructure.

### Limitations

The primary-replica model has some limitations:

- **Single Point of Failure**: The primary database is a single point of failure. If it goes down, the entire system is unavailable until failover completes.
- **Read-Write Split**: The application must be aware of the replication topology and split read and write queries accordingly.
- **Eventual Consistency**: Replicas may lag behind the primary, leading to temporary inconsistencies.

These limitations can be addressed by using more advanced replication architectures, as described in the next section.

## Multi-Primary Replication

In a multi-primary (or multi-master) replication architecture, there are multiple databases that can accept write queries. Changes are then replicated bidirectionally between all nodes.

### Architecture

The high-level architecture of a multi-primary replication system looks like this:

```
+-------------+    +--------------+
|   Primary 1 |    |   Primary 2  |
|   Database  |    |   Database   |
+-------------+    +--------------+
       |                   |
       |                   |
+-------------+    +--------------+
|   Primary 3  |    |   Primary 4  |
|   Database   |    |   Database   |
+-------------+    +--------------+
```

1. Any of the primary databases can accept write queries from the application.
2. Changes are then replicated in both directions to all other primary databases.
3. Clients can query any of the primary databases for both read and write operations.

### Replication Process

The replication process in a multi-primary system is more complex than primary-replica:

1. **Change Capture**: Each primary database tracks its own changes, usually via a transaction log or binary log.
2. **Change Transmission**: Changes are transmitted to all other primary databases, often using a push or pull mechanism.
3. **Conflict Resolution**: Since multiple primaries can make conflicting changes, a conflict resolution process is required to determine which changes take precedence.
4. **Change Application**: The changes are then applied to the local data on each primary.

Here's a sample configuration for Postgres multi-primary replication using Pglogical:

```
# postgresql.conf (Primary 1)
wal_level = logical
logical_decoding_work_mem = 64MB
max_replication_slots = 10
max_wal_senders = 10

# pglogical.conf (Primary 1)
create node local_node type 'origin' dsn 'dbname=mydb';
create sync set mysync add relation myschema.mytable;
create subscription sub1 sync set mysync target node 'remote_node';
```

### Conflict Resolution

Conflict resolution is a critical component of multi-primary replication. There are several common strategies:

- **Last Write Wins**: The most recent change takes precedence, regardless of the origin.
- **Merge**: Conflicting changes are automatically merged based on predefined rules.
- **Manual Intervention**: Conflicts are detected and surfaced to a human operator for manual resolution.

The appropriate conflict resolution strategy depends on the specific application and data requirements.

### Advantages and Disadvantages

The key advantages of multi-primary replication are:

- **High Availability**: There is no single point of failure, as any primary can accept writes.
- **Scalability**: Reads and writes can be distributed across all primaries.
- **Reduced Replication Lag**: Changes are propagated bidirectionally, reducing the potential for staleness.

However, multi-primary replication also has some downsides:

- **Complexity**: The replication process and conflict resolution are more complex.
- **Data Integrity**: Unresolved conflicts can lead to data inconsistencies across primaries.
- **Performance**: The bidirectional replication and conflict resolution process can impact overall performance.

Multi-primary replication is best suited for applications that require high availability and can tolerate occasional data inconsistencies.

## Synchronous vs. Asynchronous Replication

Replication can be implemented in either a synchronous or asynchronous manner, each with its own tradeoffs.

### Synchronous Replication

In synchronous replication, the primary database waits for the replica to acknowledge that it has received and applied the changes before confirming the write to the client. This ensures that the replica is always fully up-to-date with the primary.

```
+-------------+    +--------------+
|   Primary   |    |   Replica 1  |
|   Database  |    |   Database   |
+-------------+    +--------------+
       |                   |
       |                   |
       |                   |
       |                   |
       v                   v
+-------------+    +--------------+
|   Client    |    |   Client    |
+-------------+    +--------------+
```

The key benefits of synchronous replication are:

- **Data Consistency**: Replicas are always in sync with the primary, ensuring data consistency.
- **Failover Reliability**: If the primary fails, the replica can immediately take over with no data loss.

However, synchronous replication also has some drawbacks:

- **Performance Impact**: Waiting for the replica to acknowledge each write can significantly slow down the primary database.
- **Availability Tradeoff**: If the replica is unavailable, the primary will be unable to accept writes, reducing overall availability.

Synchronous replication is typically used in scenarios where data consistency and reliability are critical, such as financial applications or healthcare systems.

### Asynchronous Replication

In asynchronous replication, the primary database applies changes to its local data and then immediately confirms the write to the client, without waiting for the replica to acknowledge the change.

```
+-------------+    +--------------+
|   Primary   |    |   Replica 1  |
|   Database  |    |   Database   |
+-------------+    +--------------+
       |                   |
       |                   |
       v                   |
+-------------+    +--------------+
|   Client    |    |   Client    |
+-------------+    +--------------+
```

The key benefits of asynchronous replication are:

- **High Performance**: The primary database can confirm writes to the client immediately, without waiting for replication.
- **High Availability**: If a replica is unavailable, the primary can still accept writes, maintaining overall system availability.

However, asynchronous replication also has some drawbacks:

- **Data Inconsistency**: Replicas may lag behind the primary, leading to temporary data inconsistencies.
- **Failover Complexity**: If the primary fails, the replica may not have received all the latest changes, requiring more complex failover procedures.

Asynchronous replication is typically used in scenarios where performance and availability are more important than absolute data consistency, such as content delivery networks or analytical databases.

### Choosing between Synchronous and Asynchronous

The choice between synchronous and asynchronous replication depends on the specific requirements of your application:

- If data consistency and reliability are critical, use synchronous replication.
- If performance and availability are more important, use asynchronous replication.
- For a balance between the two, you can use a combination of synchronous and asynchronous replication, with the primary replicating synchronously to a nearby replica and asynchronously to more distant replicas.

## Conflict Resolution Strategies

In a multi-primary replication system, where multiple databases can accept writes, conflicts can arise when the same data is modified on different primaries. Resolving these conflicts is a critical aspect of maintaining data integrity.

Here are some common conflict resolution strategies:

### Last Write Wins

The last write wins (LWW) strategy simply accepts the most recent change, regardless of the origin. This is the simplest approach, but it can lead to data loss if the "last" write was not intended to be the authoritative version.

```
+-------------+    +--------------+
|   Primary 1 |    |   Primary 2  |
|   Database  |    |   Database   |
+-------------+    +--------------+
       |                   |
       |                   |
       v                   v
+-------------+    +--------------+
|   Conflict  |    |   Conflict  |
|   Resolution|    |   Resolution|
+-------------+    +--------------+
       |                   |
       |                   |
       v                   v
+-------------+    +--------------+
|   Merged    |    |   Merged    |
|   Database  |    |   Database  |
+-------------+    +--------------+
```

### Merge-Based Resolution

In a merge-based approach, conflicting changes are automatically merged based on predefined rules. This allows preserving the intent of both changes, rather than simply discarding one.

For example, in a user profile system, if the first primary updated the user's email address and the second primary updated the user's phone number, a merge-based resolution would retain both the updated email and phone number.

The specific merge rules depend on the data model and application requirements.

### Manual Intervention

For some applications, automatically resolving conflicts may not be feasible or desirable. In these cases, conflicts can be detected and surfaced to a human operator for manual resolution.

This approach provides the most control, but also requires more administrative overhead and can introduce delays in applying changes.

### Choosing a Conflict Resolution Strategy

The appropriate conflict resolution strategy depends on the specific requirements of your application:

- **Last Write Wins**: Simple to implement, but can lead to data loss. Suitable for less critical data.
- **Merge-Based**: Preserves the intent of all changes, but requires more complex logic. Suitable for structured data with well-defined merge rules.
- **Manual Intervention**: Provides the most control, but introduces administrative overhead. Suitable for critical data where automated resolution is not feasible.

In some cases, you may use a combination of these strategies, with automatic resolution for most conflicts and manual intervention for more complex or critical cases.

## Failover and Disaster Recovery

Replication plays a crucial role in providing high availability and disaster recovery capabilities for your database infrastructure.

### Failover

If the primary database fails, the replication system needs to perform a failover operation to promote one of the replicas to become the new primary. This process typically involves the following steps:

1. **Detect Failure**: The replication monitoring system detects that the primary database is no longer available.
2. **Elect New Primary**: The system automatically promotes one of the healthy replicas to become the new primary.
3. **Redirect Traffic**: Client connections are automatically or manually redirected to the new primary database.
4. **Resync Remaining Replicas**: Any remaining replicas that were not promoted are resynchronized with the new primary.

Here's an example of a failover process using Patroni, a high-availability framework for Postgres:

```
$ patronctl switchover --master-host my-primary --new-primary my-replica
Waiting for leader to change...
Leader changed, new leader is my-replica
```

### Disaster Recovery

In addition to failover within a single data center, replication can also be used to provide disaster recovery capabilities across multiple geographical locations.

This typically involves setting up a secondary site with its own set of replicas, which can take over if the primary site becomes unavailable due to a regional disaster.

```
+-------------+    +--------------+
|   Primary   |    |   Replica 1  |
|   Database  |    |   Database   |
+-------------+    +--------------+
       |                   |
       |                   |
+-------------+    +--------------+
|   Replica 2  |    |   Replica 3  |
|   Database   |    |   Database   |
+-------------+    +--------------+
       |                   |
       |                   |
+-------------+    +--------------+
|   Disaster   |    |   Recovery  |
|    Site      |    |    Site     |
+-------------+    +--------------+
```

The disaster recovery site can be kept in sync with the primary site using asynchronous replication, ensuring that it has the latest data available in case of a failover.

### Considerations for Failover and Disaster Recovery

When designing a failover and disaster recovery strategy, consider the following:

- **Automation**: Automate the failover process as much as possible to minimize downtime and human error.
- **Monitoring**: Implement robust monitoring to quickly detect and respond to primary database failures.
- **Testing**: Regularly test your failover and disaster recovery procedures to ensure they work as expected.
- **Geographical Separation**: For disaster recovery, ensure that the secondary site is located in a different geographical region to protect against regional outages.
- **Network Latency**: High network latency between primary and secondary sites can impact replication performance and consistency.

By carefully planning and implementing your failover and disaster recovery strategies, you can ensure that your database infrastructure remains highly available and resilient to both local and regional failures.