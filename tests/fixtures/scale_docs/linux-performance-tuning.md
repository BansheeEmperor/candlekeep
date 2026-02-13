---
title: Linux Performance Tuning
description: A comprehensive guide to optimizing Linux system performance using sysctl, ulimits, I/O schedulers, CPU governors, and kernel parameters.
keywords: 
  - linux
  - performance tuning
  - sysctl
  - ulimits
  - I/O schedulers
  - CPU governors
  - kernel parameters
category: linux
tags:
  - performance
  - tuning
  - optimization
  - sysctl
  - ulimits
  - I/O
  - CPU
  - kernel
---

## sysctl

`sysctl` is a Linux command-line tool used to view and modify kernel parameters at runtime. These parameters control various aspects of the Linux kernel's behavior, including memory management, network settings, and process scheduling.

### Viewing Current sysctl Values

To view the current values of all available `sysctl` parameters, use the following command:

```
sysctl -a
```

This will display a long list of parameters and their current values.

To view the value of a specific parameter, use the following syntax:

```
sysctl parameter_name
```

For example, to view the current value of the `vm.swappiness` parameter, which controls the kernel's tendency to use swap space, you would run:

```
sysctl vm.swappiness
```

### Modifying sysctl Values

To modify the value of a `sysctl` parameter, use the following syntax:

```
sysctl -w parameter_name=new_value
```

For example, to set the `vm.swappiness` parameter to a value of 10 (which reduces the kernel's use of swap space), you would run:

```
sysctl -w vm.swappiness=10
```

Note that changes made using `sysctl -w` are temporary and will not persist across system reboots. To make changes persistent, you need to modify the appropriate configuration file, usually `/etc/sysctl.conf`.

### Persistent sysctl Configuration

To make `sysctl` changes persistent across system reboots, you need to edit the `/etc/sysctl.conf` file. This file contains a list of `sysctl` parameters and their desired values.

Here's an example of how to add a persistent configuration for the `vm.swappiness` parameter:

```
# /etc/sysctl.conf
vm.swappiness=10
```

After making changes to the `/etc/sysctl.conf` file, you need to run the following command to apply the changes:

```
sudo sysctl -p
```

This will load the new `sysctl` values from the `/etc/sysctl.conf` file.

### Common sysctl Parameters

Here are some common `sysctl` parameters that you may want to tune for performance:

- `vm.swappiness`: Controls the kernel's tendency to use swap space. Lower values (e.g., 10) reduce swapping, while higher values (e.g., 60) increase it.
- `net.core.somaxconn`: Specifies the maximum number of queued connection requests on the server socket. Increasing this value can improve performance for high-concurrency applications.
- `fs.file-max`: Specifies the maximum number of open files for the entire system. Increasing this value can prevent "Too many open files" errors.
- `kernel.pid_max`: Specifies the maximum PID value. Increasing this value can be necessary for systems with a large number of processes.
- `kernel.threads-max`: Specifies the maximum number of threads that can be created on the system. Increasing this value can be necessary for highly-threaded applications.

Remember to test changes carefully and monitor the impact on your system's performance.

## ulimits

`ulimit` is a Linux command-line tool used to set and view resource limits for user processes. These limits control the maximum amount of system resources (such as memory, CPU, and file descriptors) that a process can consume.

### Viewing Current ulimit Values

To view the current `ulimit` values for the current user, use the following command:

```
ulimit -a
```

This will display a list of all available resource limits and their current values.

To view the value of a specific resource limit, use the following syntax:

```
ulimit -n
```

This will display the current limit for the maximum number of open file descriptors.

### Modifying ulimit Values

To modify the value of a `ulimit` resource, use the following syntax:

```
ulimit -n 4096
```

This will set the maximum number of open file descriptors to 4096.

Note that changes made using `ulimit` are temporary and will not persist across system reboots. To make changes persistent, you need to modify the appropriate configuration file, usually `/etc/security/limits.conf`.

### Persistent ulimit Configuration

To make `ulimit` changes persistent across system reboots, you need to edit the `/etc/security/limits.conf` file. This file contains a list of resource limits and their desired values.

Here's an example of how to add a persistent configuration for the maximum number of open file descriptors:

```
# /etc/security/limits.conf
*    soft    nofile    4096
*    hard    nofile    8192
```

In this example, the `soft` limit for the maximum number of open file descriptors is set to 4096, and the `hard` limit is set to 8192. The `*` character represents all users.

After making changes to the `/etc/security/limits.conf` file, the new `ulimit` values will take effect the next time the user logs in.

### Common ulimit Parameters

Here are some common `ulimit` parameters that you may want to tune for performance:

- `nofile`: Specifies the maximum number of open file descriptors.
- `nproc`: Specifies the maximum number of processes/threads.
- `memlock`: Specifies the maximum amount of locked-in-memory address space.
- `core`: Specifies the maximum size of core files.
- `stack`: Specifies the maximum stack size.

Remember to test changes carefully and monitor the impact on your system's performance.

## I/O Schedulers

The I/O scheduler is a component of the Linux kernel that manages the order in which I/O requests are handled by the storage device. Different I/O schedulers are designed to optimize I/O performance for different workloads.

### Viewing the Current I/O Scheduler

To view the current I/O scheduler being used by a specific block device, you can use the following command:

```
cat /sys/block/device_name/queue/scheduler
```

Replace `device_name` with the name of the block device you want to check, such as `sda` or `nvme0n1`.

This will display the currently active I/O scheduler enclosed in square brackets, like this:

```
[mq-deadline] kyber bfq none
```

### Changing the I/O Scheduler

To change the I/O scheduler for a specific block device, you can use the following command:

```
echo scheduler_name > /sys/block/device_name/queue/scheduler
```

Replace `scheduler_name` with the name of the I/O scheduler you want to use, such as `mq-deadline`, `kyber`, or `bfq`. Replace `device_name` with the name of the block device.

For example, to set the I/O scheduler for the `sda` device to `mq-deadline`, you would run:

```
echo mq-deadline > /sys/block/sda/queue/scheduler
```

Note that changes made using this method are temporary and will not persist across system reboots. To make changes persistent, you need to modify the appropriate boot configuration file, such as `/etc/default/grub`.

### Persistent I/O Scheduler Configuration

To make I/O scheduler changes persistent across system reboots, you need to modify the `/etc/default/grub` file and add the `elevator=` kernel parameter with the desired I/O scheduler.

Here's an example of how to set the default I/O scheduler to `mq-deadline` for all block devices:

```
# /etc/default/grub
GRUB_CMDLINE_LINUX="elevator=mq-deadline"
```

After making changes to the `/etc/default/grub` file, you need to run the following command to update the GRUB configuration and apply the changes:

```
sudo update-grub
```

This will update the GRUB configuration and set the default I/O scheduler to `mq-deadline` for all block devices.

### Common I/O Schedulers

Here are some common I/O schedulers available in Linux:

- `mq-deadline`: A deadline-based I/O scheduler that aims to provide low latency and good throughput for a wide range of workloads.
- `kyber`: A newer I/O scheduler that uses a control theory-based approach to manage I/O requests and provide low latency.
- `bfq`: (Budget Fair Queueing) A proportional-share I/O scheduler that aims to provide low latency and fairness for interactive and real-time applications.
- `none`: Disables the I/O scheduler and uses a simple FIFO (First-In, First-Out) queue.

The choice of the best I/O scheduler depends on your specific workload and storage configuration. It's generally recommended to test different schedulers and monitor their impact on your system's performance.

## CPU Governors

The CPU governor is a Linux kernel component that manages the CPU's operating frequency and power consumption based on the current workload. Different CPU governors are designed to optimize for different performance and power-saving requirements.

### Viewing the Current CPU Governor

To view the current CPU governor being used by your system, you can use the following command:

```
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

This will display the currently active CPU governor, such as `performance`, `powersave`, `ondemand`, or `conservative`.

### Changing the CPU Governor

To change the CPU governor, you can use the following command:

```
echo governor_name > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

Replace `governor_name` with the name of the CPU governor you want to use, such as `performance`, `powersave`, `ondemand`, or `conservative`.

For example, to set the CPU governor to `performance` mode, you would run:

```
echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

Note that changes made using this method are temporary and will not persist across system reboots. To make changes persistent, you need to modify the appropriate boot configuration file, such as `/etc/default/grub`.

### Persistent CPU Governor Configuration

To make CPU governor changes persistent across system reboots, you need to modify the `/etc/default/grub` file and add the `cpufreq-governor=` kernel parameter with the desired CPU governor.

Here's an example of how to set the default CPU governor to `performance` mode:

```
# /etc/default/grub
GRUB_CMDLINE_LINUX="cpufreq-governor=performance"
```

After making changes to the `/etc/default/grub` file, you need to run the following command to update the GRUB configuration and apply the changes:

```
sudo update-grub
```

This will update the GRUB configuration and set the default CPU governor to `performance` mode.

### Common CPU Governors

Here are some common CPU governors available in Linux:

- `performance`: Selects the highest available CPU frequency to maximize performance, regardless of power consumption.
- `powersave`: Selects the lowest available CPU frequency to minimize power consumption, regardless of performance.
- `ondemand`: Dynamically adjusts the CPU frequency based on the current workload, aiming to balance performance and power consumption.
- `conservative`: Similar to `ondemand`, but more conservative in its frequency scaling, resulting in less frequent changes.

The choice of the best CPU governor depends on your specific workload and power-saving requirements. It's generally recommended to test different governors and monitor their impact on your system's performance and power consumption.

## Kernel Parameters

The Linux kernel provides a wide range of parameters that can be tuned to optimize system performance. These parameters control various aspects of the kernel's behavior, including memory management, process scheduling, and network settings.

### Viewing Current Kernel Parameters

To view the current values of all available kernel parameters, you can use the following command:

```
sysctl -a
```

This will display a long list of parameters and their current values.

To view the value of a specific kernel parameter, you can use the following syntax:

```
sysctl parameter_name
```

For example, to view the current value of the `kernel.pid_max` parameter, which controls the maximum number of processes that can be created on the system, you would run:

```
sysctl kernel.pid_max
```

### Modifying Kernel Parameters

To modify the value of a kernel parameter, you can use the following syntax:

```
sysctl -w parameter_name=new_value
```

For example, to set the `kernel.pid_max` parameter to a value of 4194304, you would run:

```
sysctl -w kernel.pid_max=4194304
```

Note that changes made using `sysctl -w` are temporary and will not persist across system reboots. To make changes persistent, you need to modify the appropriate configuration file, usually `/etc/sysctl.conf`.

### Persistent Kernel Parameter Configuration

To make kernel parameter changes persistent across system reboots, you need to edit the `/etc/sysctl.conf` file. This file contains a list of kernel parameters and their desired values.

Here's an example of how to add a persistent configuration for the `kernel.pid_max` parameter:

```
# /etc/sysctl.conf
kernel.pid_max=4194304
```

After making changes to the `/etc/sysctl.conf` file, you need to run the following command to apply the changes:

```
sudo sysctl -p
```

This will load the new kernel parameter values from the `/etc/sysctl.conf` file.

### Common Kernel Parameters

Here are some common kernel parameters that you may want to tune for performance:

- `kernel.pid_max`: Specifies the maximum number of processes that can be created on the system.
- `vm.swappiness`: Controls the kernel's tendency to use swap space.
- `net.core.somaxconn`: Specifies the maximum number of queued connection requests on the server socket.
- `fs.file-max`: Specifies the maximum number of open files for the entire system.
- `kernel.threads-max`: Specifies the maximum number of threads that can be created on the system.
- `kernel.sched_min_granularity_ns`: Specifies the minimum scheduling granularity in nanoseconds.
- `kernel.sched_latency_ns`: Specifies the target latency for scheduling in nanoseconds.

Remember to test changes carefully and monitor the impact on your system's performance.