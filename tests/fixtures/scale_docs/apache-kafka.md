---
title: Apache Kafka Architecture and Components
description: Detailed technical documentation on the architecture, components, and concepts of Apache Kafka including topics, partitions, consumer groups, exactly-once semantics, Kafka Streams, and Kafka Connect.
keywords: 
  - Apache Kafka
  - Kafka architecture
  - Kafka topics
  - Kafka partitions
  - Kafka consumer groups
  - Exactly-once semantics
  - Kafka Streams
  - Kafka Connect
category: Big Data
tags:
  - Apache Kafka
  - Distributed Systems
  - Event Streaming
  - Data Pipelines
---

## Apache Kafka Architecture

Apache Kafka is a distributed, partitioned, replicated commit log service. It functions as a real-time data pipeline and message broker. 

The core elements of the Kafka architecture are:

- **Brokers**: Kafka servers that store and manage the data.
- **Topics**: The categories or feeds to which records are published.
- **Partitions**: Ordered, immutable sequences of records within a topic, where each record is assigned a sequential id number called the offset.
- **Producers**: Applications that publish (write) records to Kafka topics.
- **Consumers**: Applications that subscribe to (read) records from Kafka topics.
- **Consumer Groups**: A group of consumer instances that consume from the same topic.

![Apache Kafka Architecture Diagram](https://example.com/kafka-architecture.png)

### Brokers

Kafka brokers are the servers that store and manage the data. A Kafka cluster is composed of one or more brokers. Each broker is identified by a unique integer ID. 

The key responsibilities of Kafka brokers include:

- Receiving and storing records published by producers
- Replicating and managing the partitions
- Handling consumer requests to read records

Brokers can be added or removed from a Kafka cluster dynamically. When a new broker is added, it will automatically start receiving new data. When a broker fails, the partitions on that broker will be reassigned to other brokers.

Brokers are configured through a set of configuration parameters. Some key broker configs include:

```
# Broker ID
broker.id=0

# Port to listen on for client connections
port=9092 

# Directory where the log data is stored
log.dirs=/tmp/kafka-logs

# Minimum number of in-sync replicas required to commit a transaction
min.insync.replicas=2
```

### Topics and Partitions

**Topics** are the categories or feeds to which records are published in Kafka. Every record published to Kafka belongs to a particular topic.

Topics are divided into **partitions**, which are ordered, immutable sequences of records. Each record in a partition is assigned a sequential id number called the **offset** that uniquely identifies each record within the partition.

Partitions serve several purposes:

- **Scalability**: Partitions allow the workload to be distributed across multiple brokers.
- **Parallelism**: Consumers can read from multiple partitions in parallel to scale out consumption.
- **Ordering**: Records within a single partition are guaranteed to be stored and consumed in the order they were produced.

The number of partitions per topic is a important configuration parameter. It's recommended to have at least as many partitions as you have consumer instances in a consumer group. The partition count can be increased over time, but cannot be decreased.

Example topic and partition configuration:

```
# Create a new topic named "my-topic" with 3 partitions
bin/kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 3 --topic my-topic

# Describe the topic to see the partition information
bin/kafka-topics.sh --describe --bootstrap-server localhost:9092 --topic my-topic
Topic:my-topic	PartitionCount:3	ReplicationFactor:1	Configs:
	Topic: my-topic	Partition: 0	Leader: 0	Replicas: 0	Isr: 0
	Topic: my-topic	Partition: 1	Leader: 0	Replicas: 0	Isr: 0 
	Topic: my-topic	Partition: 2	Leader: 0	Replicas: 0	Isr: 0
```

### Producers

Producers are applications that publish (write) records to Kafka topics. When a producer wants to send a record to Kafka, it must specify the topic the record should be published to.

Producers can choose to use **key-based partitioning**, where records with the same key are guaranteed to be written to the same partition. This allows for ordered processing of related messages.

Producers can also choose to use **round-robin partitioning**, which distributes records evenly across partitions.

Example producer code in Java:

```java
Properties props = new Properties();
props.put("bootstrap.servers", "kafka-broker1:9092,kafka-broker2:9092");
props.put("acks", "all");
props.put("retries", 0);
props.put("batch.size", 16384);
props.put("linger.ms", 1);
props.put("buffer.memory", 33554432);
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");

Producer<String, String> producer = new KafkaProducer<>(props);

ProducerRecord<String, String> record = new ProducerRecord<>("my-topic", "key", "value");
producer.send(record);

producer.close();
```

### Consumers

Consumers are applications that subscribe to (read) records from Kafka topics. Consumers specify which topic(s) they want to consume from, and Kafka will deliver all of the records published to that topic to the consumer application.

Consumers are part of a **consumer group**. Each record published to a topic is delivered to one consumer instance within each subscribing consumer group. 

Consumer groups provide two main benefits:

1. **Load Balancing**: When multiple consumer instances belong to the same group, Kafka will automatically balance the partitions among the consumers.
2. **Failover**: If a consumer instance dies, the partitions assigned to it will be reassigned to other instances in the same group, ensuring continuous consumption.

Consumers use **offsets** to keep track of their position within a partition. Offsets are committed regularly so that if a consumer fails, it can resume consumption from the last committed offset.

Example consumer code in Java:

```java
Properties props = new Properties();
props.put("bootstrap.servers", "kafka-broker1:9092,kafka-broker2:9092");
props.put("group.id", "my-group");
props.put("enable.auto.commit", "true");
props.put("auto.commit.interval.ms", "1000");
props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
props.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
consumer.subscribe(Arrays.asList("my-topic"));

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(100);
    for (ConsumerRecord<String, String> record : records) {
        System.out.printf("topic = %s, partition = %d, offset = %d, key = %s, value = %s%n",
                record.topic(), record.partition(), record.offset(), record.key(), record.value());
    }
}
```

## Exactly-Once Semantics

Kafka provides various delivery semantics for handling message delivery guarantees:

- **At-Most-Once**: Records may be lost but are never redelivered.
- **At-Least-Once**: Records are guaranteed to be delivered at least once, but may be redelivered.
- **Exactly-Once**: Records are delivered exactly once and never redelivered.

Achieving **exactly-once semantics** in Kafka is especially important for use cases where duplicates cannot be tolerated, such as financial transactions or critical business data.

Kafka implements exactly-once semantics through the use of:

1. **Idempotent Producers**: Kafka producers are configured to be idempotent, ensuring that duplicate sends of the same message do not result in duplicate records in the log.
2. **Transactional API**: Kafka provides a transactional API that allows producers to atomically write a set of messages to different partitions and consumer offsets.

To configure exactly-once semantics:

1. Enable idempotence on the producer:
```
# Producer configuration
producer.enable.idempotence = true
```

2. Use the transactional API:
```java
// Create a transactional producer
Producer<String, String> producer = new KafkaProducer<>(producerConfig);
producer.initTransactions();

try {
    // Start the transaction
    producer.beginTransaction();
    
    // Send multiple records within the transaction
    producer.send(record1);
    producer.send(record2);
    
    // Commit the transaction
    producer.commitTransaction();
} catch (ProducerFencedException | RetriableException e) {
    // Abort the transaction on any exceptions
    producer.abortTransaction();
}
```

Enabling exactly-once semantics provides strong delivery guarantees, but it does come with some performance overhead. It's important to carefully consider your requirements and tradeoffs when choosing the appropriate delivery semantics for your application.

## Kafka Streams

Kafka Streams is a client library for building robust, scalable, and fault-tolerant stream processing applications. It allows you to perform complex processing on data stored in Kafka topics.

The key components of Kafka Streams are:

1. **KStream**: Represents a record stream, where each record is an independent event.
2. **KTable**: Represents a changelog stream, where each record represents an update to a particular key.
3. **GlobalKTable**: Represents a replicated in-memory table shared across all stream task instances.
4. **Processor Topology**: A graph of stream processors that process the input data.

Here's an example Kafka Streams application in Java that counts the number of words in messages:

```java
Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "wordcount-application");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "kafka-broker1:9092,kafka-broker2:9092");
props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass());

StreamsBuilder builder = new StreamsBuilder();
KStream<String, String> textLines = builder.stream("input-topic");

KTable<String, Long> wordCounts = textLines
    .flatMapValues(line -> Arrays.asList(line.toLowerCase().split("\\W+")))
    .groupBy((key, word) -> word)
    .count();

wordCounts.toStream().to("output-topic");

KafkaStreams streams = new KafkaStreams(builder.build(), props);
streams.start();
```

This application reads messages from the "input-topic", tokenizes the text into individual words, counts the occurrences of each word, and writes the word counts to the "output-topic".

Kafka Streams provides several powerful features:

- **Exactly-Once Processing**: Uses Kafka's transactional capabilities to provide exactly-once semantics.
- **Fault Tolerance**: Automatically handles broker failures and partition rebalancing.
- **Scalability**: Can scale processing capacity by adding more instances of the application.
- **Integration with Kafka**: Allows seamless integration with Kafka topics for input and output.
- **DSL and Processor API**: Provides a high-level DSL and a lower-level Processor API for building stream processing applications.

## Kafka Connect

Kafka Connect is a framework for building real-time data pipelines between Kafka and other data systems. It provides a set of plug-ins called **connectors** that simplify the process of moving data in and out of Kafka.

There are two types of Kafka Connect connectors:

1. **Source Connectors**: Read data from an external system and write it to Kafka topics.
2. **Sink Connectors**: Read data from Kafka topics and write it to an external system.

Kafka Connect can be run in two modes:

1. **Standalone mode**: A single worker process that runs connectors.
2. **Distributed mode**: Multiple worker processes that can scale out and provide fault tolerance.

Here's an example of configuring a Kafka Connect source connector to read data from a MySQL database and write it to a Kafka topic:

```
# Example Kafka Connect source connector configuration
name=mysql-source
connector.class=io.confluent.connect.jdbc.JdbcSourceConnector
tasks.max=1
connection.url=jdbc:mysql://mysql-host:3306/my_database
connection.user=my_user
connection.password=my_password
table.whitelist=users,products
mode=incrementing
incrementing.column.name=id
timestamp.column.name=modified_ts
topic.prefix=mysql-
```

The key features of Kafka Connect include:

- **Scalability**: Can scale out by adding more Connect worker instances.
- **Fault Tolerance**: Automatically handles worker failures and task rebalancing.
- **Reliable Delivery**: Ensures at-least-once delivery of records from source to Kafka.
- **Extensibility**: Supports a wide range of connectors through a plugin architecture.
- **Managed Offsets**: Manages offsets for source connectors to ensure no data loss on failures.
- **Transformations**: Allows applying transformations to records before writing to Kafka.

Kafka Connect simplifies the process of integrating Kafka with other data systems, making it easier to build robust, scalable, and fault-tolerant data pipelines.