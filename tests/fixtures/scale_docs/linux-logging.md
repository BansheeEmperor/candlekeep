---
title: Linux Logging Guide
description: A comprehensive guide to Linux logging with syslog, journald, rsyslog, log rotation, centralized logging, and structured logging.
keywords: 
  - linux
  - logging
  - syslog
  - journald
  - rsyslog
  - log rotation
  - centralized logging
  - structured logging
category: System Administration
tags:
  - linux
  - logging
  - syslog
  - journald
  - rsyslog
  - log rotation
  - centralized logging
  - structured logging
---

## Syslog

Syslog is the standard system logging protocol on Linux and other Unix-like operating systems. It provides a way for system processes and applications to send log messages to a central syslog daemon, which then handles the storage and processing of those logs.

### Syslog Configuration

The syslog daemon is typically configured through the `/etc/syslog.conf` file (or `/etc/rsyslog.conf` for the rsyslog implementation). This file defines the rules for how log messages are handled, including:

- Facility - The type of process or application that generated the message (e.g., kernel, system, application)
- Priority - The severity level of the message (e.g., debug, info, warning, error, critical)
- Action - Where the message should be logged (e.g., file, remote host, terminal)

Example syslog.conf configuration:

```
# Log all kernel messages to the console
kern.*                                                 /dev/console

# Log anything of level notice or higher to the main log file
*.notice;auth,authpriv,cron,daemon.none                 /var/log/messages

# Log cron activities
cron.*                                                 /var/log/cron

# Log authentication-related messages
auth,authpriv.*                                         /var/log/auth.log
```

### Syslog Commands

- `logger` - Command-line tool to send messages to the syslog daemon
- `tail -f /var/log/messages` - View the main system log in real-time
- `journalctl` - Command to view and query the systemd journal (replaces traditional syslog on some systems)

## Journald

Journald is the logging system used by systemd, the init system and service manager used by many modern Linux distributions. Journald provides a more structured and powerful logging system compared to traditional syslog.

### Journald Configuration

Journald is configured through the `/etc/systemd/journald.conf` file. Some common settings include:

- `Storage=` - Specifies where journal files are stored (e.g., `persistent`, `volatile`, `none`)
- `Compress=` - Enables or disables compression of journal files
- `MaxRetentionSec=` - Sets the maximum age of journal files before they are deleted
- `MaxFileSec=` - Sets the maximum lifetime of a single journal file

Example journald.conf configuration:

```
[Journal]
Storage=persistent
Compress=yes
MaxRetentionSec=1year
MaxFileSec=1month
```

### Journalctl Commands

- `journalctl` - View the systemd journal
- `journalctl -u myservice.service` - View logs for a specific systemd service
- `journalctl -b` - View logs since last boot
- `journalctl --since "2023-04-01" --until "2023-04-30"` - View logs for a specific date range
- `journalctl -p err` - View only error-level logs
- `journalctl --flush` - Flush journal buffers to disk

## Rsyslog

Rsyslog is a popular and powerful replacement for the standard syslog daemon. It provides additional features and configuration options beyond the basic syslog protocol.

### Rsyslog Configuration

Rsyslog is configured through the `/etc/rsyslog.conf` file. The configuration syntax is similar to traditional syslog, but with some additional directives and modules.

Example rsyslog.conf configuration:

```
# Log all kernel messages to the console
kern.*                                                 /dev/console

# Log anything of level notice or higher to the main log file
*.notice;auth,authpriv,cron,daemon.none                 /var/log/messages

# Log cron activities
cron.*                                                 /var/log/cron

# Log authentication-related messages
auth,authpriv.*                                         /var/log/auth.log

# Enable UDP reception
$ModLoad imudp
$UDPServerRun 514

# Enable TCP reception
$ModLoad imtcp
$InputTCPServerRun 514
```

### Rsyslog Commands

- `rsyslogd` - Start the rsyslog daemon
- `rsyslog -c6 -N1` - Check the configuration file for syntax errors
- `rsyslog -i /var/run/rsyslogd.pid` - Send a signal to the running rsyslog process

## Log Rotation

Log rotation is the process of automatically managing the growth of log files. This typically involves:

- Renaming or moving old log files to a different location
- Compressing old log files to save space
- Deleting old log files that exceed a specified age or size

### Logrotate Configuration

Log rotation is typically handled by the `logrotate` utility, which is configured through the `/etc/logrotate.conf` file and associated configuration files in the `/etc/logrotate.d/` directory.

Example logrotate configuration:

```
/var/log/messages {
    rotate 7
    daily
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}

/var/log/auth.log {
    rotate 7
    daily
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
```

### Logrotate Commands

- `logrotate /etc/logrotate.conf` - Manually run the log rotation process
- `logrotate -d /etc/logrotate.conf` - Perform a "dry run" of the log rotation process
- `logrotate -f /etc/logrotate.conf` - Force the log rotation process to run immediately

## Centralized Logging

Centralized logging, also known as log aggregation, is the process of collecting and storing log data from multiple hosts or applications in a central location. This provides several benefits:

- Improved log management and analysis
- Easier troubleshooting and root cause analysis
- Compliance and regulatory requirements
- Centralized security monitoring and threat detection

### Centralized Logging Solutions

Some popular centralized logging solutions for Linux include:

- **Elasticsearch/Logstash/Kibana (ELK Stack)** - A open-source stack for collecting, processing, and visualizing log data
- **Graylog** - An open-source log management platform with advanced features for data analysis and alerting
- **Splunk** - A commercial log management and analytics platform
- **Papertrail** - A cloud-based centralized logging service

### Configuring Centralized Logging

The process of configuring centralized logging typically involves the following steps:

1. Install and configure the centralized logging solution on a dedicated server or cloud service.
2. Configure the logging agents (e.g., Filebeat, Logstash Forwarder) on each client system to forward logs to the centralized server.
3. Define log parsing and indexing rules to structure the log data for efficient searching and analysis.
4. Set up user access controls, dashboards, and alerts to monitor and respond to log events.

Example Filebeat configuration for forwarding logs to Elasticsearch:

```yaml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/messages
      - /var/log/auth.log

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  username: "filebeat_internal"
  password: "changeme"
```

## Structured Logging

Structured logging is the practice of representing log messages in a machine-readable format, such as JSON or key-value pairs, instead of the traditional free-form text format. This provides several benefits:

- Easier parsing and processing of log data
- Better support for structured search and analysis
- Improved interoperability between different logging systems
- Enhanced support for log aggregation and centralized logging

### Structured Logging Approaches

There are several ways to implement structured logging in Linux applications:

1. **Using a Logging Library**: Many programming languages have logging libraries that support structured logging, such as `logrus` for Go, `log4j` for Java, and `logging` for Python.

Example using the `logrus` library in Go:

```go
import (
    log "github.com/sirupsen/logrus"
)

func main() {
    log.WithFields(log.Fields{
        "animal": "walrus",
        "size":   10,
    }).Info("A walrus appears")
}
```

2. **Formatting Logs Manually**: Developers can also format log messages manually using a structured format, such as JSON, and write them to a file or send them to a logging service.

Example of manually formatted JSON logs:

```json
{
    "timestamp": "2023-04-01T12:34:56Z",
    "level": "info",
    "message": "A walrus appears",
    "animal": "walrus",
    "size": 10
}
```

3. **Using a Logging Agent**: Logging agents like Filebeat or Logstash can be configured to parse and structure log data from various sources.

Example Filebeat configuration for structuring Apache access logs:

```yaml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/apache2/access.log
    fields_under_root: true
    fields:
      service: apache
    processors:
      - dissect:
          tokenizer: '%{client_ip} %{ident} %{auth} [%{timestamp}] "%{method} %{request} HTTP/%{http_version}" %{status_code} %{response_size}'
          field: 'message'
          target_fields:
            client_ip: client_ip
            ident: ident
            auth: auth
            timestamp: timestamp
            method: method
            request: request
            http_version: http_version
            status_code: status_code
            response_size: response_size
```

By adopting structured logging practices, you can improve the overall quality and usefulness of your log data, making it easier to analyze, troubleshoot, and meet regulatory requirements.