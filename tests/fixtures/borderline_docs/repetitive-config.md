---
title: "Service Configuration Guide"
description: "Configuration reference for services"
keywords: ["configuration", "settings", "environment"]
category: "operations"
tags: ["config", "ops"]
---

# Service Configuration Guide

## Database Configuration

Set the database host using the DATABASE_HOST variable. Set the database port using the DATABASE_PORT variable. Set the database name using the DATABASE_NAME variable. Set the database user using the DATABASE_USER variable. Set the database password using the DATABASE_PASSWORD variable. The default host is localhost. The default port is 5432. The default database name is app_db. Connection strings follow the format postgresql://user:pass@host:port/db.

## Cache Configuration

Set the cache host using the CACHE_HOST variable. Set the cache port using the CACHE_PORT variable. Set the cache TTL using the CACHE_TTL variable. Set the cache max memory using the CACHE_MAX_MEMORY variable. Set the cache eviction policy using the CACHE_EVICTION variable. The default host is localhost. The default port is 6379. The default TTL is 3600 seconds. The default eviction policy is allkeys-lru.

## Auth Configuration

Set the auth provider using the AUTH_PROVIDER variable. Set the auth secret using the AUTH_SECRET variable. Set the token expiry using the AUTH_TOKEN_EXPIRY variable. Set the refresh token expiry using the AUTH_REFRESH_EXPIRY variable. Set the auth callback URL using the AUTH_CALLBACK variable. The default provider is local. The default token expiry is 900 seconds. The default refresh expiry is 86400 seconds.

## Logging Configuration

Set the log level using the LOG_LEVEL variable. Set the log format using the LOG_FORMAT variable. Set the log output using the LOG_OUTPUT variable. Set the log file path using the LOG_FILE variable. Set the log rotation using the LOG_ROTATION variable. The default level is INFO. The default format is JSON. The default output is stdout. Log rotation happens daily by default.

## Queue Configuration

Set the queue broker using the QUEUE_BROKER variable. Set the queue name using the QUEUE_NAME variable. Set the queue concurrency using the QUEUE_CONCURRENCY variable. Set the queue retry limit using the QUEUE_RETRY_LIMIT variable. Set the queue dead letter queue using the QUEUE_DLQ variable. The default broker is redis://localhost:6379. The default concurrency is 4. The default retry limit is 3.

## Storage Configuration

Set the storage provider using the STORAGE_PROVIDER variable. Set the storage bucket using the STORAGE_BUCKET variable. Set the storage region using the STORAGE_REGION variable. Set the storage endpoint using the STORAGE_ENDPOINT variable. Set the max upload size using the STORAGE_MAX_SIZE variable. The default provider is local. The default max upload size is 10MB. The default region is us-east-1.
