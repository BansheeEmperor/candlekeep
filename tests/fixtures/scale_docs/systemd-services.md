---
title: Systemd Service Management
description: A comprehensive guide to managing services, unit files, targets, timers, the journal, and socket activation with systemd on Linux.
keywords: 
  - systemd
  - service management
  - unit files
  - targets
  - timers
  - journal
  - socket activation
category: Linux
tags:
  - systemd
  - services
  - unit files
  - targets
  - timers
  - journal
  - socket activation
---

## Systemd Service Management

Systemd is the default init system and service manager on many modern Linux distributions, including Debian, Ubuntu, Fedora, and CentOS. It is responsible for initializing the system, managing services, and providing various other system management capabilities.

### Unit Files

Systemd uses "unit files" to manage services, sockets, mounts, devices, and other system resources. Unit files are configuration files that define how a particular service or resource should be managed.

Unit files are typically located in the `/etc/systemd/system/` directory, although some may also be found in `/usr/lib/systemd/system/`. Unit files have a `.service`, `.socket`, `.target`, `.timer`, or other extension depending on the type of unit.

Here's an example of a simple service unit file:

```
[Unit]
Description=My Service
After=network.target

[Service]
ExecStart=/path/to/my-service.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

This unit file defines a service called "My Service" that should be started after the network target has been reached. The `ExecStart` directive specifies the command to start the service, and the `Restart` directive tells systemd to automatically restart the service if it fails.

The `[Install]` section specifies that this service should be enabled to start at boot as part of the "multi-user" target.

#### Common Unit File Directives

- `[Unit]` section:
  - `Description`: A brief description of the unit.
  - `After`/`Before`: Specify the ordering of unit activation.
  - `Wants`/`Requires`: Declare dependencies on other units.
- `[Service]` section (for service units):
  - `ExecStart`/`ExecStop`: The command to start/stop the service.
  - `Restart`: Specifies when to automatically restart the service.
  - `User`/`Group`: The user and group to run the service as.
- `[Install]` section:
  - `WantedBy`/`RequiredBy`: Specify which target(s) the unit should be enabled for.

### Targets

Systemd uses "targets" to group related services and resources together. Targets are similar to the runlevels used in older init systems, but provide more flexibility and granularity.

Some common systemd targets include:

- `multi-user.target`: The default target for a fully-functional multi-user system.
- `graphical.target`: Includes the display manager and desktop environment.
- `emergency.target`: A rescue mode target for system recovery.
- `shutdown.target`: The target for shutting down the system.

You can list all available targets with the following command:

```
systemctl list-unit-files --type=target
```

To change the default target (the one that is booted into), use the `systemctl set-default` command:

```
sudo systemctl set-default graphical.target
```

### Timers

Systemd "timers" are unit files that schedule the execution of other units (usually services) at specific intervals. Timers can be used to replace traditional cron jobs.

Here's an example timer unit file:

```
[Unit]
Description=Run my-service.service daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

This timer unit file schedules the execution of the `my-service.service` unit every day. The `OnCalendar` directive specifies the schedule, and the `Persistent` directive ensures the service runs even if the system was powered off during the scheduled time.

To enable and start the timer:

```
sudo systemctl enable --now my-service.timer
```

Common timer directives include:

- `OnActiveSec`/`OnBootSec`/`OnStartupSec`: Delay the first execution.
- `OnUnitActiveSec`/`OnUnitInactiveSec`: Schedule based on previous service activation.
- `RandomizedDelaySec`: Add a random delay to the schedule.

### The Journal

Systemd's logging system is called the "journal", and it replaces traditional text-based log files like `/var/log/syslog`. The journal stores log entries in a binary format, providing more functionality and flexibility than traditional text-based logs.

You can view the journal using the `journalctl` command:

```
# View all log entries
journalctl

# View log entries for a specific service
journalctl -u my-service.service

# View log entries from the current boot
journalctl -b

# View log entries from a specific time range
journalctl --since "2023-04-01" --until "2023-04-30"
```

Some useful `journalctl` options include:

- `-f`: Follow the log in real-time (like `tail -f`).
- `-n`: Show the most recent N log entries.
- `-p`: Filter by priority level (e.g., `journalctl -p err` for errors).
- `--vacuum-time=`: Automatically delete logs older than the specified time.

The journal can also be configured to persist logs across reboots and to limit the amount of disk space used. This is done by editing the `/etc/systemd/journald.conf` file.

### Socket Activation

Systemd supports "socket activation", which allows services to be started on-demand when a connection is made to a specific socket. This can be useful for improving performance and reducing resource usage for services that don't need to be running all the time.

Here's an example socket unit file:

```
[Unit]
Description=My Service Socket

[Socket]
ListenStream=/run/my-service.sock
Accept=true

[Install]
WantedBy=sockets.target
```

This socket unit file defines a local Unix domain socket at `/run/my-service.sock`. When a connection is made to this socket, systemd will automatically start the corresponding service unit (in this case, `my-service.service`).

To enable and start the socket:

```
sudo systemctl enable --now my-service.socket
```

Common socket directives include:

- `ListenStream`/`ListenDatagram`/`ListenSequentialPacket`: Specify the socket type and address.
- `Accept`: Whether to accept incoming connections or just notify the service.
- `SocketUser`/`SocketGroup`: The user and group for the socket file.

Socket activation can be combined with other systemd features, such as timers, to create powerful and flexible service management solutions.

## Advanced Systemd Concepts

### Unit File Dependencies

Systemd unit files can declare dependencies on other units using the `Wants`, `Requires`, `After`, and `Before` directives in the `[Unit]` section. This allows systemd to manage the ordering and relationships between different system components.

For example, to ensure that the `my-service.service` unit is started after the `network.target` unit has been reached:

```
[Unit]
Description=My Service
After=network.target
```

The `Wants` and `Requires` directives specify "soft" and "hard" dependencies, respectively. A "soft" dependency means the dependent unit will be started if possible, but the current unit can still start if the dependent unit fails. A "hard" dependency means the current unit cannot start unless the dependent unit is also available.

### Override Files

Systemd allows you to override the settings in a unit file by creating an "override" file. This is useful when you need to modify the behavior of a system-provided unit file without editing the original file directly.

To create an override file, use the `systemctl edit` command:

```
sudo systemctl edit my-service.service
```

This will open a text editor and allow you to add or modify directives in the `[Service]`, `[Unit]`, or other sections of the unit file. The changes will be saved in a separate override file, typically located at `/etc/systemd/system/my-service.service.d/override.conf`.

### Sandboxing and Security

Systemd provides several security features to sandbox and isolate services, including:

- `PrivateTmp`: Use a private `/tmp` directory for the service.
- `ProtectSystem`/`ProtectHome`: Restrict access to system files and the user's home directory.
- `CapabilityBoundingSet`: Limit the Linux capabilities available to the service.
- `NoNewPrivileges`: Prevent the service from gaining new privileges.

These options can be configured in the `[Service]` section of the unit file. For example:

```
[Service]
PrivateTmp=true
ProtectSystem=full
CapabilityBoundingSet=CAP_CHOWN CAP_DAC_OVERRIDE CAP_FOWNER
NoNewPrivileges=true
```

### Resource Limits

Systemd can also be used to set resource limits for services, such as CPU, memory, and file descriptor usage. This can help prevent a service from consuming too many system resources and impacting other processes.

Resource limits are configured in the `[Service]` section of the unit file:

```
[Service]
CPUShares=512
MemoryLimit=1G
LimitNOFILE=4096
```

These settings will limit the service to using 512 CPU shares, 1 GB of memory, and a maximum of 4,096 open file descriptors.

### Debugging and Troubleshooting

When things go wrong, systemd provides several tools for debugging and troubleshooting issues:

- `systemctl status <unit>`: Check the status and recent log entries for a specific unit.
- `journalctl -u <unit>`: View the journal logs for a specific unit.
- `systemd-analyze`: Analyze the boot process and identify slow-starting units.
- `systemd-run`: Temporarily run a command or script as a systemd unit.

Additionally, you can enable debug logging for systemd by editing the `/etc/systemd/system.conf` file and setting the `LogLevel` directive to `debug`.

## Conclusion

Systemd is a powerful and flexible system management tool that provides robust service management, logging, and other advanced features. By understanding unit files, targets, timers, the journal, and socket activation, you can effectively manage and maintain your Linux systems. The examples and technical details provided in this guide should serve as a valuable reference for system administrators and developers working with systemd.