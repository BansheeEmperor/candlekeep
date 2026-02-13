---
title: Data Warehouse Modeling and ETL Patterns
description: Detailed technical documentation on data warehouse modeling techniques, schema designs, and common ETL patterns.
keywords: 
  - data warehouse
  - data modeling
  - star schema
  - snowflake schema
  - slowly changing dimensions
  - fact tables
  - ETL
category: data engineering
tags:
  - data warehouse
  - data modeling
  - ETL
  - BI
---

## Data Warehouse Modeling

Data warehouse modeling refers to the process of designing the logical and physical data models for a data warehouse environment. This includes determining the appropriate schema structures, dimensions, facts, and relationships to effectively capture and analyze business data.

### Star Schema

The star schema is a widely used dimensional data model for data warehouses. It consists of a central fact table surrounded by lookup dimension tables. The fact table contains numeric measures or facts, while the dimension tables contain descriptive attributes.

The key characteristics of a star schema are:

- **Fact Table**: The central fact table contains the primary metrics or measures of interest, such as sales amounts, order quantities, etc. Fact tables are typically large, with millions or billions of rows.
- **Dimension Tables**: Lookup tables that contain attributes describing the facts, such as product information, customer details, time periods, etc. Dimension tables are typically smaller, with thousands or millions of rows.
- **Foreign Key Relationships**: The fact table contains foreign keys that link it to the relevant dimension tables. This allows data to be aggregated and analyzed along multiple dimensions.

Example star schema:

```
+---------------+    +--------------+    +--------------+
|   Fact Table  |    | Time Dim     |    | Product Dim  |
+---------------+    +--------------+    +--------------+
| order_id      |    | time_id      |    | product_id   |
| product_id    |    | date         |    | product_name |
| time_id       |    | month        |    | category     |
| order_qty     |    | year         |    | brand        |
| order_amount  |    +--------------+    +--------------+
+---------------+
```

The fact table contains foreign keys (`product_id`, `time_id`) that link it to the dimension tables, allowing analysis of sales by product, time period, etc.

### Snowflake Schema

The snowflake schema is a variation of the star schema, where the dimension tables are further normalized into multiple lookup tables. This results in a more complex schema structure that resembles a snowflake shape when visualized.

The key characteristics of a snowflake schema are:

- **Normalized Dimensions**: Dimension tables are broken down into multiple lookup tables, creating a hierarchical structure.
- **Increased Complexity**: The schema becomes more complex, with more tables and joins required to retrieve data.
- **Storage Efficiency**: The normalized structure can reduce data redundancy and storage requirements for dimension data.
- **Query Complexity**: Queries become more complex due to the increased number of tables and joins required.

Example snowflake schema:

```
+---------------+    +--------------+    +--------------+    +--------------+
|   Fact Table  |    | Time Dim     |    | Product Dim  |    | Category Dim |
+---------------+    +--------------+    +--------------+    +--------------+
| order_id      |    | time_id      |    | product_id   |    | category_id  |
| product_id    |    | date         |    | product_name |    | category_name|
| time_id       |    | month        |    | brand_id     |    +--------------+
| order_qty     |    | year         |    +--------------+
| order_amount  |    +--------------+    | Brand Dim    |
+---------------+                       +--------------+
                                        | brand_id     |
                                        | brand_name   |
                                        +--------------+
```

In this example, the Product dimension has been further normalized into a Brand dimension, creating a more complex, snowflake-shaped schema.

### Slowly Changing Dimensions (SCD)

Slowly Changing Dimensions (SCDs) are a technique used in data warehousing to handle changes to dimension data over time. There are several types of SCD approaches:

**SCD Type 1 (Overwrite)**: The existing dimension record is simply overwritten with the new values. This effectively erases the historical changes to the dimension.

**SCD Type 2 (History)**: A new row is inserted in the dimension table for each change, with effective dates to track the history of the dimension.

**SCD Type 3 (Current and Previous)**: The dimension table stores both the current and previous values for relevant attributes, allowing analysis of the changes.

**SCD Type 4 (History in Satellite)**: The current dimension data is stored in the main dimension table, while historical changes are stored in a separate "satellite" table.

Example SCD Type 2 implementation:

```
+---------------+    +--------------+
|   Fact Table  |    | Product Dim  |
+---------------+    +--------------+
| order_id      |    | product_id   |
| product_id    |    | product_name |
| time_id       |    | category     |
| order_qty     |    | brand        |
| order_amount  |    | start_date   |
+---------------+    | end_date     |
                     | current_flag |
                     +--------------+
```

In this example, the `Product Dim` table stores historical changes to product data, with the `start_date`, `end_date`, and `current_flag` columns tracking the effective dates and current status of each record.

### Fact Tables

Fact tables are the central tables in a data warehouse schema, containing the numeric measures or facts of interest. Key characteristics of fact tables include:

- **Large Size**: Fact tables are typically very large, containing millions or billions of rows.
- **Additive Measures**: The measures in fact tables are usually additive, meaning they can be summed up (e.g., sales amount, order quantity).
- **Foreign Key Relationships**: Fact tables contain foreign keys that link them to the relevant dimension tables.
- **Granular Data**: Fact tables store data at the most granular level, such as individual transactions or events.

Example fact table:

```
+---------------+
|   Fact Table  |
+---------------+
| order_id      |
| product_id    |
| time_id       |
| customer_id   |
| order_qty     |
| order_amount  |
| order_date    |
| ship_date     |
+---------------+
```

This fact table contains measures like `order_qty` and `order_amount`, as well as foreign keys to link it to the corresponding dimension tables (product, time, customer).

## ETL Patterns

Extract, Transform, and Load (ETL) is the process of extracting data from source systems, transforming it to fit the data warehouse schema, and loading it into the target data warehouse.

### Batch ETL

Batch ETL is the traditional approach where data is extracted, transformed, and loaded in batches, typically on a regular schedule (e.g., daily, weekly).

Key characteristics of batch ETL:

- **Periodic Execution**: Batch ETL jobs run on a fixed schedule, such as nightly or weekly.
- **Entire Dataset Processed**: All data is extracted, transformed, and loaded during each batch run.
- **Potential Latency**: There can be a lag between the time data is generated and when it is available in the data warehouse.

Example batch ETL workflow:

1. Extract data from source systems (e.g., databases, files, APIs) into a staging area.
2. Transform the data to fit the data warehouse schema (e.g., data type conversions, aggregations, joins).
3. Load the transformed data into the data warehouse tables.
4. Schedule the ETL job to run on a regular basis (e.g., nightly, weekly).

```
+---------------+    +---------------+    +---------------+
| Source System |    |   Staging     |    | Data Warehouse|
+---------------+    +---------------+    +---------------+
| Database      |    | Temp Tables  |    | Fact Tables   |
| Files         |    | Transformation|    | Dimension     |
| APIs          |    +---------------+    | Tables        |
+---------------+                        +---------------+
       |                                        |
       |--- Batch ETL Job (Scheduled) -----------|
```

### Incremental ETL

Incremental ETL is a variation of batch ETL where only the new or changed data is extracted, transformed, and loaded, rather than the entire dataset.

Key characteristics of incremental ETL:

- **Partial Dataset Processed**: Only the new or modified data is processed during each ETL run.
- **Reduced Processing Time**: Incremental ETL is generally faster than processing the full dataset.
- **Requires Tracking of Changes**: The ETL process needs to track which data has been updated or added since the last run.

Example incremental ETL workflow:

1. Identify the new or changed data in the source systems (e.g., using change data capture, timestamp columns, or database logs).
2. Extract only the new or modified data into the staging area.
3. Transform the incremental data to fit the data warehouse schema.
4. Load the transformed data into the appropriate data warehouse tables, often using an "upsert" or merge operation to update existing records and insert new ones.
5. Schedule the incremental ETL job to run on a regular basis (e.g., hourly, daily).

```
+---------------+    +---------------+    +---------------+
| Source System |    |   Staging     |    | Data Warehouse|
+---------------+    +---------------+    +---------------+
| Database      |    | Temp Tables  |    | Fact Tables   |
| Files         |    | Transformation|    | Dimension     |
| APIs          |    +---------------+    | Tables        |
+---------------+                        +---------------+
       |                                        |
       |--- Incremental ETL Job (Scheduled) ----|
```

### Change Data Capture (CDC)

Change Data Capture (CDC) is a technique used to identify and extract only the data that has been added or modified in the source systems, rather than processing the entire dataset.

Key characteristics of CDC:

- **Real-time or Near-real-time Processing**: CDC can enable near-real-time data updates in the data warehouse.
- **Reduced Processing Load**: By only extracting changed data, CDC can significantly reduce the processing load and improve ETL performance.
- **Requires Source System Support**: CDC typically requires the source systems to provide change tracking capabilities, such as database logs or event streams.

Example CDC-based ETL workflow:

1. Monitor the source systems for changes using CDC mechanisms (e.g., database triggers, log-based change data capture).
2. Extract only the new or modified data from the source systems.
3. Transform the incremental data to fit the data warehouse schema.
4. Load the transformed data into the appropriate data warehouse tables, often using an "upsert" or merge operation.
5. Continuously monitor the source systems for changes and trigger the ETL process in real-time or near-real-time.

```
+---------------+    +---------------+    +---------------+
| Source System |    |   Staging     |    | Data Warehouse|
+---------------+    +---------------+    +---------------+
| Database      |    | Temp Tables  |    | Fact Tables   |
| Files         |    | Transformation|    | Dimension     |
| APIs          |    +---------------+    | Tables        |
+---------------+                        +---------------+
       |                                        |
       |--- CDC-based ETL (Real-time/Continuous) |
```

CDC-based ETL can provide significantly lower latency compared to batch or incremental ETL, as data is processed as soon as changes occur in the source systems.

### Event-Driven ETL

Event-driven ETL is an approach where the ETL process is triggered by specific events or changes in the source systems, rather than running on a fixed schedule.

Key characteristics of event-driven ETL:

- **Real-time or Near-real-time Processing**: Event-driven ETL can enable near-real-time data updates in the data warehouse.
- **Event-triggered Execution**: The ETL process is triggered by events or changes in the source systems, rather than running on a fixed schedule.
- **Requires Event Monitoring**: The ETL process needs to continuously monitor the source systems for relevant events or changes.

Example event-driven ETL workflow:

1. Monitor the source systems for relevant events or data changes (e.g., using message queues, webhooks, or event logs).
2. When a relevant event is detected, extract the necessary data from the source systems.
3. Transform the data to fit the data warehouse schema.
4. Load the transformed data into the appropriate data warehouse tables, often using an "upsert" or merge operation.
5. Continuously monitor the source systems for events and trigger the ETL process in real-time or near-real-time.

```
+---------------+    +---------------+    +---------------+
| Source System |    |   Staging     |    | Data Warehouse|
+---------------+    +---------------+    +---------------+
| Database      |    | Temp Tables  |    | Fact Tables   |
| Files         |    | Transformation|    | Dimension     |
| APIs          |    +---------------+    | Tables        |
+---------------+                        +---------------+
       |                                        |
       |--- Event-driven ETL (Real-time/Continuous) |
```

Event-driven ETL can provide the lowest latency among the ETL patterns, as data is processed as soon as relevant events or changes occur in the source systems.

### Microservices-based ETL

Microservices-based ETL is an architectural approach where the ETL process is broken down into smaller, independent services that can be scaled and deployed independently.

Key characteristics of microservices-based ETL:

- **Modular Design**: The ETL process is divided into smaller, focused microservices (e.g., extraction, transformation, loading).
- **Scalability and Flexibility**: Individual microservices can be scaled and deployed independently, allowing for better resource utilization and flexible scaling.
- **Fault Tolerance**: If one microservice fails, the rest of the ETL process can continue to function.
- **Increased Complexity**: The overall ETL system becomes more complex, with increased coordination and communication between microservices.

Example microservices-based ETL architecture:

```
+---------------+    +---------------+    +---------------+
| Source System |    |   Extraction  |    |  Staging      |
+---------------+    +---------------+    +---------------+
| Database      |    | Extractor 1   |    | Temp Tables  |
| Files         |    | Extractor 2   |    +---------------+
| APIs          |    +---------------+            |
+---------------+            |                    |
                             |                    |
                 +---------------+    +---------------+
                 |  Transformation|    |   Loading     |
                 +---------------+    +---------------+
                 | Transformer 1  |    |   Loader 1    |
                 | Transformer 2  |    |   Loader 2    |
                 +---------------+    +---------------+
                             |                    |
                             |                    |
                 +---------------+    +---------------+
                 |  Orchestrator  |    | Data Warehouse|
                 +---------------+    +---------------+
                                      | Fact Tables   |
                                      | Dimension     |
                                      | Tables        |
                                      +---------------+
```

In this example, the ETL process is divided into separate microservices for extraction, transformation, and loading. The orchestrator service coordinates the execution of the individual microservices, ensuring the overall ETL process is completed successfully.

## Conclusion

This document provides a comprehensive overview of data warehouse modeling techniques, including star schema, snowflake schema, and slowly changing dimensions, as well as common ETL patterns, such as batch, incremental, change data capture, event-driven, and microservices-based ETL. These concepts and patterns are essential for building robust and efficient data warehousing solutions that support business intelligence and analytics.