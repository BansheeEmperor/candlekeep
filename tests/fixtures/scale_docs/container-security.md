---
title: Container Security: Comprehensive Guide
description: Comprehensive technical documentation on container security, including image scanning, runtime protection, seccomp, AppArmor, rootless containers, and supply chain security.
keywords: 
  - container security
  - image scanning
  - runtime protection
  - seccomp
  - AppArmor
  - rootless containers
  - supply chain security
category: security
tags:
  - containers
  - docker
  - kubernetes
  - security
  - image scanning
  - runtime protection
  - seccomp
  - AppArmor
  - rootless
  - supply chain
---

## Container Security Overview

Container security is a critical aspect of modern application deployment, as containers are increasingly used to package and distribute applications. This document provides a comprehensive guide to various container security features and best practices, including image scanning, runtime protection, seccomp, AppArmor, rootless containers, and supply chain security.

## Image Scanning

Secure container images are the foundation of a robust container security strategy. Image scanning is the process of analyzing container images for known vulnerabilities, malware, and other security issues.

### Vulnerability Scanning

Vulnerability scanning tools, such as [Trivy](https://github.com/aquasecurity/trivy), [Clair](https://github.com/quay/clair), and [Anchore](https://github.com/anchore/anchore-engine), can be used to scan container images for known vulnerabilities. These tools analyze the various layers of the image and provide a detailed report of any identified issues.

Example Trivy scan:

```bash
trivy image nginx:latest
```

Output:
```
Vulnerabilities:
+------------------------+------------------+----------+-------------------+---------------+
| VULNERABILITY         | SEVERITY        | PACKAGE  | INSTALLED VERSION | FIXED VERSION |
+------------------------+------------------+----------+-------------------+---------------+
| CVE-2019-15846        | HIGH            | openssl  | 1.1.1c            | 1.1.1d        |
| CVE-2019-1547         | MEDIUM          | openssl  | 1.1.1c            | 1.1.1d        |
| CVE-2019-1559         | MEDIUM          | openssl  | 1.1.1c            | 1.1.1d        |
+------------------------+------------------+----------+-------------------+---------------+
```

### Malware Scanning

Tools like [Clamav](https://www.clamav.net/) can be used to scan container images for known malware signatures. This can help detect and prevent the distribution of malicious code through container images.

Example Clamav scan:

```bash
docker run -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp --rm arsenalrecon/clamav-docker scan nginx:latest
```

Output:
```
Scanning nginx:latest...
/tmp/scan/Dockerfile.txt: OK
/tmp/scan/etc/debian_version: OK
/tmp/scan/etc/hostname: OK
/tmp/scan/etc/nsswitch.conf: OK
/tmp/scan/etc/resolv.conf: OK
/tmp/scan/etc/ssl/certs/ca-certificates.crt: OK
/tmp/scan/etc/sysctl.conf: OK
/tmp/scan/etc/wget/wgetrc: OK
/tmp/scan/run/nginx.pid: OK
/tmp/scan/usr/local/bin/docker-entrypoint.sh: OK
/tmp/scan/usr/local/bin/nginx: OK
/tmp/scan/usr/local/lib/mod_http2.so: OK
/tmp/scan/usr/local/lib/mod_http2.so.1: OK
/tmp/scan/usr/local/lib/mod_http2.so.1.13.0: OK
/tmp/scan/usr/local/nginx/conf/fastcgi.conf: OK
/tmp/scan/usr/local/nginx/conf/fastcgi_params: OK
/tmp/scan/usr/local/nginx/conf/koi-utf: OK
/tmp/scan/usr/local/nginx/conf/koi-win: OK
/tmp/scan/usr/local/nginx/conf/mime.types: OK
/tmp/scan/usr/local/nginx/conf/nginx.conf: OK
/tmp/scan/usr/local/nginx/conf/scgi_params: OK
/tmp/scan/usr/local/nginx/conf/uwsgi_params: OK
/tmp/scan/usr/local/nginx/conf/win-utf: OK
/tmp/scan/usr/local/sbin/nginx: OK

Scan completed successfully. No threats found.
```

### Supply Chain Security

Supply chain security is the process of ensuring the integrity and security of the components that make up a container image, from the base operating system to the application code and dependencies.

Tools like [Codenotary](https://www.codenotary.com/) and [Sigstore](https://www.sigstore.dev/) can be used to cryptographically sign and verify the provenance of container images, ensuring that they come from a trusted source and have not been tampered with.

Example Codenotary CLI usage:

```bash
# Sign an image
codenotary importsign --image nginx:latest --key-id <key-id>

# Verify an image
codenotary verify --image nginx:latest
```

## Runtime Protection

Runtime protection is the set of security measures that are applied to a running container to prevent and detect malicious activity.

### Seccomp (Secure Computing Mode)

Seccomp is a Linux kernel feature that allows you to restrict the system calls that a process can make. This can be used to limit the attack surface of a container by restricting the system calls that the container can perform.

Example Seccomp profile:

```json
{
    "defaultAction": "SCMP_ACT_ERRNO",
    "syscalls": [
        {
            "names": [
                "accept",
                "accept4",
                "access",
                "alarm",
                "alarm",
                "bind",
                "brk",
                "capget",
                "capset",
                "chdir",
                "chmod",
                "chown",
                "chown32",
                "clock_getres",
                "clock_gettime",
                "clock_nanosleep",
                "close",
                "connect",
                "copy_file_range",
                "creat",
                "dup",
                "dup2",
                "dup3",
                "epoll_create",
                "epoll_create1",
                "epoll_ctl",
                "epoll_pwait",
                "epoll_wait",
                "eventfd",
                "eventfd2",
                "execve",
                "exit",
                "exit_group",
                "faccessat",
                "fadvise64",
                "fadvise64_64",
                "fallocate",
                "fanotify_init",
                "fanotify_mark",
                "fchdir",
                "fchmod",
                "fchmodat",
                "fchown",
                "fchown32",
                "fchownat",
                "fcntl",
                "fcntl64",
                "fdatasync",
                "fgetxattr",
                "flistxattr",
                "flock",
                "fork",
                "fremovexattr",
                "fsetxattr",
                "fstat",
                "fstat64",
                "fstatat64",
                "fstatfs",
                "fstatfs64",
                "fsync",
                "ftruncate",
                "ftruncate64",
                "futex",
                "get_robust_list",
                "get_thread_area",
                "getcpu",
                "getcwd",
                "getdents",
                "getdents64",
                "getegid",
                "getegid32",
                "geteuid",
                "geteuid32",
                "getgid",
                "getgid32",
                "getgroups",
                "getgroups32",
                "getitimer",
                "getpeername",
                "getpgid",
                "getpgrp",
                "getpid",
                "getppid",
                "getpriority",
                "getrandom",
                "getresgid",
                "getresgid32",
                "getresuid",
                "getresuid32",
                "getrlimit",
                "get_robust_list",
                "getrusage",
                "getsid",
                "getsockname",
                "getsockopt",
                "gettid",
                "gettimeofday",
                "getuid",
                "getuid32",
                "getxattr",
                "inotify_add_watch",
                "inotify_init",
                "inotify_init1",
                "inotify_rm_watch",
                "ioctl",
                "io_cancel",
                "io_destroy",
                "io_getevents",
                "ioprio_get",
                "ioprio_set",
                "io_setup",
                "io_submit",
                "kill",
                "lchown",
                "lchown32",
                "lgetxattr",
                "link",
                "linkat",
                "listen",
                "listxattr",
                "llistxattr",
                "lremovexattr",
                "lseek",
                "lsetxattr",
                "lstat",
                "lstat64",
                "madvise",
                "memfd_create",
                "mincore",
                "mkdir",
                "mkdirat",
                "mknod",
                "mknodat",
                "mmap",
                "mmap2",
                "mprotect",
                "mq_getattr",
                "mq_notify",
                "mq_open",
                "mq_timedreceive",
                "mq_timedsend",
                "mq_unlink",
                "mremap",
                "msgctl",
                "msgget",
                "msgrcv",
                "msgsnd",
                "msync",
                "munmap",
                "nanosleep",
                "newfstatat",
                "open",
                "openat",
                "pause",
                "pipe",
                "pipe2",
                "poll",
                "ppoll",
                "prctl",
                "pread64",
                "preadv",
                "prlimit64",
                "pselect6",
                "pwrite64",
                "pwritev",
                "read",
                "readahead",
                "readlink",
                "readlinkat",
                "readv",
                "recvfrom",
                "recvmmsg",
                "recvmsg",
                "remap_file_pages",
                "removexattr",
                "rename",
                "renameat",
                "renameat2",
                "restart_syscall",
                "rmdir",
                "rt_sigaction",
                "rt_sigpending",
                "rt_sigprocmask",
                "rt_sigqueueinfo",
                "rt_sigreturn",
                "rt_sigsuspend",
                "rt_sigtimedwait",
                "rt_tgsigqueueinfo",
                "sched_getaffinity",
                "sched_getattr",
                "sched_getparam",
                "sched_get_priority_max",
                "sched_get_priority_min",
                "sched_getscheduler",
                "sched_rr_get_interval",
                "sched_setaffinity",
                "sched_setattr",
                "sched_setparam",
                "sched_setscheduler",
                "sched_yield",
                "seccomp",
                "select",
                "semctl",
                "semget",
                "semop",
                "semtimedop",
                "send",
                "sendfile",
                "sendfile64",
                "sendmmsg",
                "sendmsg",
                "sendto",
                "setfsgid",
                "setfsgid32",
                "setfsuid",
                "setfsuid32",
                "setgid",
                "setgid32",
                "setgroups",
                "setgroups32",
                "setitimer",
                "setpgid",
                "setpriority",
                "setregid",
                "setregid32",
                "setresgid",
                "setresgid32",
                "setresuid",
                "setresuid32",
                "setreuid",
                "setreuid32",
                "setrlimit",
                "set_robust_list",
                "setsid",
                "setsockopt",
                "set_thread_area",
                "set_tid_address",
                "setuid",
                "setuid32",
                "setxattr",
                "shmat",
                "shmctl",
                "shmdt",
                "shmget",
                "shutdown",
                "sigaltstack",
                "signalfd",
                "signalfd4",
                "socket",
                "socketcall",
                "socketpair",
                "splice",
                "stat",
                "stat64",
                "statfs",
                "statfs64",
                "symlink",
                "symlinkat",
                "sync",
                "sync_file_range",
                "syncfs",
                "sysinfo",
                "syslog",
                "tee",
                "tgkill",
                "time",
                "timer_create",
                "timer_delete",
                "timerfd_create",
                "timerfd_gettime",
                "timerfd_settime",
                "timer_getoverrun",
                "timer_gettime",
                "timer_settime",
                "times",
                "tkill",
                "truncate",
                "truncate64",
                "ugetrlimit",
                "umask",
                "uname",
                "unlink",
                "unlinkat",
                "utime",
                "utimensat",
                "utimes",
                "vfork",
                "vmsplice",
                "wait4",
                "waitid",
                "waitpid",
                "write",
                "writev"
            ],
            "action": "SCMP_ACT_ALLOW"
        }
    ]
}
```

This Seccomp profile allows a limited set of system calls that are typically required by a containerized application, while blocking all other system calls.

### AppArmor

AppArmor is a Linux kernel security module that can be used to restrict the capabilities of a container. AppArmor profiles can be used to define a set of allowed and denied actions for a container, further reducing its attack surface.

Example AppArmor profile:

```
#include <tunables/global>

profile nginx-container flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  /usr/sbin/nginx               mr,
  /etc/nginx/                   r,
  /etc/nginx/*.conf             r,
  /var/log/nginx/              rw,
  /var/lib/nginx/              rw,
  /run/nginx.pid               rw,

  network inet stream,
  network inet6 stream,

  deny @{PROC}/* w,   # Deny write for all files directly in /proc (not in subdirs)
  deny @{PROC}/{asound,fs,irq,sys,tmp}/* w,  # Deny write for certain /proc subdirectories
  deny @{PROC}/sysrq-trigger rwklx,
  deny @{PROC}/latency_stats   rw,
  deny @{PROC}/timer_list      rw,
  deny @{PROC}/timer_stats     rw,
  deny @{PROC}/vm/stat         rw,

  deny mount,

  deny /sys/[^f]*/** wklx,
  deny /sys/f[^s]*/** wklx,
  deny /sys/fs/[^c]*/** wklx,
  deny /sys/fs/c[^g]*/** wklx,
  deny /sys/fs/cg[^r]*/** wklx,
  deny /sys/firmware/** rd,
  deny /sys/kernel/debug/** rwklx