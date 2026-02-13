---
title: Elasticsearch: Indexing, Mappings, Analyzers, Queries, Aggregations, Sharding
description: A comprehensive technical guide to Elasticsearch's core features and functionality, including indexing, mappings, analyzers, queries, aggregations, and sharding.
keywords: 
  - elasticsearch
  - indexing
  - mappings
  - analyzers
  - queries
  - aggregations
  - sharding
category: databases
tags:
  - elasticsearch
  - search
  - indexing
  - querying
  - data-processing
---

## Indexing in Elasticsearch

Indexing is the process of adding data to an Elasticsearch index. When you index a document, Elasticsearch analyzes the contents of the document, extracts various components (terms, numbers, dates, etc.), and stores them in a way that makes them quickly searchable.

### Indexing a Document

To index a document in Elasticsearch, you can use the `_index` API. Here's an example:

```json
PUT /my-index/_doc/1
{
  "title": "Elasticsearch Indexing",
  "content": "This document explains how to index data in Elasticsearch."
}
```

This will index a new document with an ID of `1` in the `my-index` index. The document contains two fields: `title` and `content`.

### Partial Updates

You can also update a portion of an existing document using the `_update` API:

```json
POST /my-index/_doc/1/_update
{
  "doc": {
    "content": "This document explains how to index and update data in Elasticsearch."
  }
}
```

This will update the `content` field of the document with ID `1` in the `my-index` index.

### Bulk Indexing

For more efficient indexing of multiple documents, you can use the Elasticsearch Bulk API:

```
POST /_bulk
{ "index" : { "_index" : "my-index", "_id" : "1" }}
{ "title" : "Elasticsearch Indexing", "content" : "This document explains how to index data in Elasticsearch." }
{ "index" : { "_index" : "my-index", "_id" : "2" }}
{ "title" : "Elasticsearch Updating", "content" : "This document explains how to update data in Elasticsearch." }
```

The Bulk API allows you to index, update, delete, or upsert multiple documents in a single request, improving performance.

## Mappings in Elasticsearch

Mappings define the structure of documents in an Elasticsearch index, including the fields, their data types, and various configuration options.

### Defining a Mapping

You can define a mapping for an index when you create it:

```json
PUT /my-index
{
  "mappings": {
    "properties": {
      "title": { "type": "text" },
      "content": { "type": "text" },
      "published_date": { "type": "date" },
      "author": {
        "properties": {
          "name": { "type": "text" },
          "email": { "type": "keyword" }
        }
      }
    }
  }
}
```

This mapping defines four top-level fields: `title`, `content`, `published_date`, and `author`. The `author` field is an object field that contains two sub-fields: `name` and `email`.

### Dynamic Mappings

Elasticsearch can also automatically create mappings for you when you index a document without an explicit mapping. This is called "dynamic mapping":

```json
PUT /my-index/_doc/1
{
  "title": "Elasticsearch Mappings",
  "content": "This document explains how to work with mappings in Elasticsearch.",
  "published_date": "2023-04-01",
  "author": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

In this case, Elasticsearch will automatically create the mapping based on the data in the indexed document.

## Analyzers in Elasticsearch

Analyzers are responsible for processing text data during indexing and querying. They break down the text into individual terms, normalize them, and optionally apply additional transformations.

### Built-in Analyzers

Elasticsearch comes with several built-in analyzers that you can use:

- `standard`: Breaks text on word boundaries, as defined by the Unicode Text Segmentation algorithm, and converts terms to lowercase.
- `simple`: Splits text on any non-alphabetic character and lowercases the terms.
- `whitespace`: Splits text on whitespace.
- `keyword`: Treats the entire text as a single term.

You can configure these analyzers or create your own custom analyzers as needed.

### Custom Analyzers

Here's an example of a custom analyzer that uses the `standard` tokenizer and the `lowercase` and `stop` filters:

```json
PUT /my-index
{
  "settings": {
    "analysis": {
      "analyzer": {
        "my_custom_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "stop"
          ]
        }
      }
    }
  }
}
```

You can then use this custom analyzer when indexing or querying documents in the `my-index` index.

## Queries in Elasticsearch

Elasticsearch provides a rich set of query types that you can use to search your data.

### Match Query

The `match` query is one of the most commonly used queries. It performs a full-text search on the specified field:

```json
GET /my-index/_search
{
  "query": {
    "match": {
      "content": "elasticsearch indexing"
    }
  }
}
```

This query will return all documents where the `content` field matches the phrase "elasticsearch indexing".

### Term Query

The `term` query is used for exact matches on a field:

```json
GET /my-index/_search
{
  "query": {
    "term": {
      "author.name": "John Doe"
    }
  }
}
```

This query will return all documents where the `author.name` field is exactly "John Doe".

### Bool Query

The `bool` query allows you to combine multiple query clauses using boolean logic (must, must_not, should):

```json
GET /my-index/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "title": "elasticsearch" } },
        { "match": { "content": "indexing" } }
      ],
      "must_not": [
        { "term": { "author.name": "Jane Doe" } }
      ],
      "should": [
        { "range": { "published_date": { "gte": "2023-01-01", "lte": "2023-12-31" } } }
      ]
    }
  }
}
```

This query will return documents that match both the "elasticsearch" term in the title and the "indexing" term in the content, but exclude documents where the author's name is "Jane Doe", and include documents where the published date is within the specified range.

### Range Query

The `range` query allows you to filter documents by a range of values:

```json
GET /my-index/_search
{
  "query": {
    "range": {
      "published_date": {
        "gte": "2023-01-01",
        "lte": "2023-12-31"
      }
    }
  }
}
```

This query will return all documents where the `published_date` field is between January 1, 2023, and December 31, 2023.

## Aggregations in Elasticsearch

Aggregations in Elasticsearch allow you to generate statistics and perform data analysis on your search results.

### Histogram Aggregation

The `histogram` aggregation can be used to group data into fixed-size buckets:

```json
GET /my-index/_search
{
  "size": 0,
  "aggs": {
    "published_date_histogram": {
      "histogram": {
        "field": "published_date",
        "interval": 86400000 # 1 day in milliseconds
      }
    }
  }
}
```

This query will group the documents by the `published_date` field, creating one bucket for each day. The response will include the number of documents in each bucket.

### Terms Aggregation

The `terms` aggregation can be used to find the most common values in a field:

```json
GET /my-index/_search
{
  "size": 0,
  "aggs": {
    "top_authors": {
      "terms": {
        "field": "author.name",
        "size": 5
      }
    }
  }
}
```

This query will return the top 5 most common values in the `author.name` field.

### Nested Aggregation

Nested aggregations can be used to perform aggregations on nested objects:

```json
GET /my-index/_search
{
  "size": 0,
  "aggs": {
    "authors": {
      "nested": {
        "path": "author"
      },
      "aggs": {
        "top_emails": {
          "terms": {
            "field": "author.email",
            "size": 5
          }
        }
      }
    }
  }
}
```

This query will perform a `terms` aggregation on the `author.email` field, but only for the nested `author` objects.

## Sharding in Elasticsearch

Sharding is a fundamental concept in Elasticsearch that allows you to scale your data and query processing across multiple nodes.

### Primary and Replica Shards

When you create an index in Elasticsearch, it is divided into multiple shards. Each shard is an instance of a Lucene index, and Elasticsearch automatically manages the sharding process.

You can also configure replica shards, which are copies of the primary shards. Replica shards provide redundancy and improve query performance.

### Shard Allocation

Elasticsearch automatically allocates shards to nodes in your cluster based on the available resources and the configuration of your cluster. You can influence the shard allocation process using various settings, such as:

- `index.number_of_shards`: The number of primary shards for the index.
- `index.number_of_replicas`: The number of replica shards for each primary shard.
- `cluster.routing.allocation.awareness.attributes`: Assign shards to nodes based on specific attributes (e.g., rack, availability zone).

### Shard Rebalancing

Elasticsearch continuously monitors the cluster state and will automatically rebalance shards if necessary, for example, when a new node is added or a node fails.

You can also manually trigger a rebalance using the `_cluster/reroute` API:

```
POST /_cluster/reroute
{
  "commands": [
    {
      "move": {
        "index": "my-index",
        "shard": 0,
        "from_node": "node1",
        "to_node": "node2"
      }
    }
  ]
}
```

This command will move the shard 0 of the `my-index` index from `node1` to `node2`.

Proper shard management is crucial for ensuring the scalability and performance of your Elasticsearch cluster.