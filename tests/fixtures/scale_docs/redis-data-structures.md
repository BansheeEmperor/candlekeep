---
title: Redis Data Structures, Persistence, and Clustering
description: Detailed technical documentation on Redis data structures, persistence models, and clustering capabilities.
keywords: 
  - redis
  - data structures
  - strings
  - lists
  - sets
  - sorted sets
  - hashes
  - streams
  - persistence
  - rdb
  - aof
  - clustering
category: databases
tags:
  - redis
  - nosql
  - data structures
  - persistence
  - clustering
---

## Redis Data Structures

Redis supports several different data structures beyond the basic key-value store. These include:

### Strings

Strings are the most basic data type in Redis. A string value can be up to 512MB in size. Some common string operations include:

```
SET mykey "Hello"
GET mykey
APPEND mykey " World"
INCR counter
INCRBY counter 10
```

Strings can also be used to store binary data, like images or serialized objects.

### Lists

Redis lists are ordered collections of strings. They support operations to add, get, and remove elements from the beginning or end of the list.

```
LPUSH mylist "hello"
LPUSH mylist "world"
LRANGE mylist 0 -1 # Get all elements
RPOP mylist # Remove and return the last element
```

Lists can store up to 2^32 - 1 elements (over 4 billion).

### Sets

Redis sets are unordered collections of unique strings. Some common set operations include:

```
SADD myset "apple" 
SADD myset "banana"
SMEMBERS myset # Get all members
SINTER set1 set2 # Get the intersection
SUNION set1 set2 # Get the union
SREM myset "banana" # Remove an element
```

Sets can have up to 2^32 - 1 members.

### Sorted Sets

Sorted sets are similar to sets, but each member has an associated score that is used for sorting. This allows efficient retrieval of members in a given range.

```
ZADD ages 35 "Alice"
ZADD ages 28 "Bob"
ZRANGE ages 0 -1 # Get all members sorted by score
ZRANGEBYSCORE ages 18 30 # Get members with score 18-30
ZREM ages "Bob" # Remove a member
```

Sorted sets can have up to 2^32 - 1 members.

### Hashes

Redis hashes are maps of key-value pairs. This allows grouping related data together.

```
HSET user:1 name "Alice" email "alice@example.com"
HGET user:1 name
HMGET user:1 name email
HGETALL user:1
HDEL user:1 email
```

Hashes can store up to 2^32 - 1 field-value pairs.

### Streams

Streams are a Redis data type for storing time series data. They are append-only logs that support efficient range queries.

```
XADD mystream * sensor_id 123 temperature 18.2
XRANGE mystream - + # Get all stream entries
XREAD COUNT 2 STREAMS mystream 0-0 # Read 2 new entries
XDEL mystream 1526569495631-0 # Delete an entry
```

Streams can store up to 2^64 - 1 entries.

## Redis Persistence

Redis supports two main persistence models: RDB (Redis Database) and AOF (Append-Only File).

### RDB (Redis Database)

RDB persistence works by creating a point-in-time snapshot of the Redis data at a configurable interval. This is configured in the `redis.conf` file:

```
# save 900 1     # Save if at least 1 key changed in 900 sec
# save 300 10    # Save if at least 10 keys changed in 300 sec
# save 60 10000  # Save if at least 10000 keys changed in 60 sec
save 60 1000
```

The RDB file is a compact binary format that can be efficiently loaded on server startup. This makes RDB great for backups and replication, but it can lead to data loss if the save interval is not frequent enough.

### AOF (Append-Only File)

AOF persistence logs every write operation to an append-only log file. This provides better durability, as the data can be recovered from the log on startup.

The AOF file is configured in `redis.conf`:

```
appendonly yes
appendfilename "appendonly.aof"
# appendfsync always    # Sync after every write (slow but safe)
appendfsync everysec   # Sync every second (fast and usually safe)
# appendfsync no       # Rely on OS to flush, may lose some data
```

The tradeoff is that the AOF file can become quite large over time. Redis provides mechanisms to automatically rewrite and compact the AOF file.

### Persistence Comparisons

RDB is generally faster and produces smaller files, but can lead to data loss. AOF is slower but provides better durability. Many Redis deployments use both, with RDB for backups/replication and AOF for immediate persistence.

It's also possible to disable persistence entirely, treating Redis as an in-memory cache. In this case, data will be lost on server restart.

## Redis Clustering

Redis supports clustering to provide high availability and scalability. The Redis Cluster implementation uses a distributed hash table to shard data across multiple Redis nodes.

### Cluster Architecture

A Redis cluster consists of multiple Redis instances, each running as a separate server. These instances are organized into a set of master nodes and replica nodes.

- Master nodes store the actual data and handle read/write requests.
- Replica nodes are read-only copies of the data, used for load balancing and high availability.

The cluster uses a hash slot-based sharding scheme to distribute keys across the master nodes. There are 16384 hash slots that are assigned to the master nodes.

When a client wants to access a key, it first determines which hash slot the key belongs to, and then routes the request to the appropriate master node.

An example 3-node Redis cluster might look like this:

```
   Slot 0 - 5500   Slot 5501 - 11000   Slot 11001 - 16383
+-------------+ +-------------+ +-------------+
|   Master 1  | |   Master 2  | |   Master 3  |
+-------------+ +-------------+ +-------------+
|   Replica 2 | |   Replica 3 | |   Replica 1 |
+-------------+ +-------------+ +-------------+
```

### Cluster Setup

To set up a Redis cluster, you'll need to run multiple Redis instances and configure them to work together. This can be done manually or using a tool like `redis-cli` with the `cluster` subcommands.

Here's an example of creating a 3-node cluster using `redis-cli`:

```
# Start 3 Redis instances
redis-server --port 7000
redis-server --port 7001 
redis-server --port 7002

# Create the cluster
redis-cli --cluster create 127.0.0.1:7000 127.0..1:7001 127.0.0.1:7002 --cluster-replicas 1
```

This will create a 3-node cluster with 1 replica per master. The cluster configuration is stored in the `cluster.conf` file.

### High Availability

The Redis cluster provides high availability through automatic failover. If a master node fails, one of its replica nodes will be promoted to a master to replace it.

The cluster uses a consensus-based algorithm to detect failures and coordinate failovers. This ensures that the cluster can tolerate the failure of up to half the nodes and still maintain availability.

### Scaling

Redis clustering also allows you to scale your deployment by adding or removing nodes. When a new node is added, the cluster will automatically rebalance the hash slots to distribute the data evenly.

Scaling can be done online without interrupting client operations. However, you need to be careful when removing nodes, as this can lead to data loss if not done correctly.

### Limitations

While Redis clustering provides many benefits, there are some limitations to be aware of:

- Keys belonging to the same data structure (e.g. a Redis list) must be stored on the same node. This can complicate certain data modeling scenarios.
- Transactions and lua scripting are limited to single keys, as they cannot span multiple nodes.
- The cluster cannot tolerate the failure of more than half the nodes.

Overall, Redis clustering is a powerful feature that allows you to build highly available, scalable Redis deployments. However, it's important to understand the tradeoffs and design your application architecture accordingly.