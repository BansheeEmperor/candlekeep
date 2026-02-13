---
title: Linux Filesystem Hierarchy, File Systems, and Mount Configuration
description: A comprehensive technical guide to the Linux filesystem hierarchy, ext4, XFS, Btrfs, inodes, hard/soft links, mount options, and the fstab configuration file.
keywords: 
  - linux
  - filesystem
  - ext4
  - xfs
  - btrfs
  - inode
  - hard link
  - soft link
  - mount
  - fstab
category: Linux
tags:
  - linux
  - filesystem
  - ext4
  - xfs
  - btrfs
  - storage
  - configuration
---

## Linux Filesystem Hierarchy

The Linux filesystem hierarchy is a standard that defines the directory structure and folder naming conventions for the Linux operating system. This hierarchy organizes the filesystem into a tree-like structure with the root directory `/` at the top.

The main directories and their typical purposes are:

- `/bin`: Essential user binaries (e.g. `ls`, `cp`, `mv`)
- `/sbin`: Essential system binaries (e.g. `ifconfig`, `route`, `iptables`)
- `/etc`: System configuration files
- `/var`: Variable data files (e.g. logs, spool files, temp files)
- `/usr`: Secondary hierarchy for user-related binaries and files
- `/home`: User home directories
- `/root`: Home directory for the root (administrative) user
- `/dev`: Device files (e.g. `/dev/sda`, `/dev/tty1`, `/dev/null`)
- `/proc`: Virtual filesystem providing information about running processes
- `/sys`: Virtual filesystem providing information about the system
- `/lib`: Essential shared libraries and kernel modules
- `/opt`: Optional/third-party application files

The filesystem hierarchy is designed to provide a consistent and predictable organization, making it easier for users, scripts, and applications to find and access the files they need.

## Ext4 Filesystem

The ext4 (Fourth Extended Filesystem) is a widely-used journaling file system for Linux. It is the default file system for many modern Linux distributions. Some key features of ext4 include:

### Filesystem Structure
The ext4 filesystem is divided into the following main components:

- **Superblock**: Stores overall filesystem information (e.g. total block count, free block count, filesystem state).
- **Group Descriptors**: Describes the filesystem blocks and inodes in each block group.
- **Block Bitmap**: Tracks which blocks are in use.
- **Inode Bitmap**: Tracks which inodes are in use.
- **Inode Table**: Contains metadata about each file and directory in the filesystem.
- **Data Blocks**: Stores the actual file and directory data.

### Inodes
In ext4, each file and directory is represented by an inode, which contains the file's metadata:

```
$ ls -li
17451 -rw-r--r-- 1 user group 1234 Jan 1 12:00 example.txt
```

In this example, `17451` is the inode number. Inodes store attributes like:

- File type (regular file, directory, symlink, etc.)
- Owner and group
- Permissions
- Access/modification/change timestamps
- File size
- Block pointers to the file's data

The maximum number of inodes is set during filesystem creation and cannot be changed later.

### Extents
Ext4 uses an "extents" system to more efficiently manage file storage compared to previous ext filesystems. Instead of storing a list of all data blocks, extents store the starting block and length of contiguous runs of blocks, reducing metadata overhead.

### Delayed Allocation
Ext4 delays the allocation of filesystem blocks until data is actually written, allowing the filesystem to make more intelligent allocation decisions.

### Online Defragmentation
Ext4 supports online defragmentation, allowing files to be defragmented without unmounting the filesystem.

### Example Configuration
Here is an example `fstab` entry to mount an ext4 filesystem:

```
/dev/sda1 / ext4 defaults 0 1
```

This mounts the `/dev/sda1` partition as the root filesystem (`/`) using the ext4 file system type with the default mount options.

## XFS Filesystem

XFS is a high-performance journaling file system developed by Silicon Graphics. It has several advanced features compared to ext4:

### Metadata Logging
XFS uses a journaling system to log metadata changes, allowing for fast crash recovery.

### Extent-based Allocation
Similar to ext4's extents, XFS allocates file data in variable-sized extents to reduce metadata overhead.

### Online Filesystem Expansion
XFS filesystems can be expanded online without unmounting.

### Quota Management
XFS has built-in support for user and group quotas.

### Real-time Subvolumes
XFS can have real-time subvolumes for low-latency, high-throughput applications.

### Filesystem Snapshots
XFS supports creating read-only snapshots of the filesystem.

### Example Configuration
Here is an example `fstab` entry to mount an XFS filesystem:

```
/dev/sdb1 /data xfs defaults 0 0
```

This mounts the `/dev/sdb1` partition as the `/data` mount point using the XFS file system type with the default options.

## Btrfs Filesystem

Btrfs (B-tree File System) is a modern copy-on-write filesystem designed for fault tolerance, repair, and efficient management of large storage volumes. Some key Btrfs features include:

### Pooled Storage
Btrfs allows multiple storage devices to be combined into a single storage pool, which can then be divided into subvolumes.

### Copy-on-Write
Btrfs uses a copy-on-write (CoW) mechanism, where new data is written to unused blocks and metadata is updated to point to the new blocks.

### Snapshots
Btrfs supports creating read-write snapshots of subvolumes, which can be used for backup, cloning, and rollback.

### Checksumming
Btrfs checksums both data and metadata to detect and correct errors.

### Compression
Btrfs can transparently compress files using algorithms like zlib or lzo.

### Online Filesystem Expansion/Shrinking
Btrfs volumes can be expanded or shrunk online without downtime.

### Example Configuration
Here is an example `fstab` entry to mount a Btrfs filesystem:

```
/dev/sdc1 /backup btrfs defaults,subvol=@backup 0 0
```

This mounts the `/dev/sdc1` partition as the `/backup` mount point, using the Btrfs file system type and mounting the `@backup` subvolume.

## Inodes

An inode (index node) is a data structure in a Unix-like file system that stores all the information about a file except its name and the actual data contents. Some key facts about inodes:

- Each file and directory is represented by a unique inode.
- Inodes store metadata like file type, permissions, ownership, timestamps, and block pointers.
- The maximum number of inodes is set during filesystem creation and cannot be changed later.
- The `ls -l` command shows the inode number for each file.
- The `stat` command can be used to view detailed inode information.

Example `stat` output:

```
$ stat example.txt
  File: 'example.txt'
  Size: 1234        Blocks: 8          IO Block: 4096   regular file
Device: 801h/2049d  Inode: 17451       Links: 1
Access: (0644/-rw-r--r--)  Uid: (1000/user)   Gid: (1000/group)
Access: 2023-01-01 12:00:00.000000000 +0000
Modify: 2023-01-01 12:00:00.000000000 +0000
Change: 2023-01-01 12:00:00.000000000 +0000
 Birth: -
```

## Hard Links and Soft Links

In Linux, there are two types of links: hard links and soft (symbolic) links.

### Hard Links
- A hard link is a directory entry that points directly to the inode of a file.
- Hard links share the same inode, so they refer to the same file data.
- Changes to one hard link affect all other hard links to the same file.
- Hard links cannot span across different filesystems.
- The `ln` command is used to create hard links.

Example:

```
$ ln example.txt hard_link.txt
$ ls -li
17451 -rw-r--r-- 2 user group 1234 Jan 1 12:00 example.txt
17451 -rw-r--r-- 2 user group 1234 Jan 1 12:00 hard_link.txt
```

### Soft (Symbolic) Links
- A soft link (or symlink) is a special type of file that points to another file or directory.
- Soft links store the path to the target, not the inode.
- Changes to the target affect the symlink, but changes to the symlink do not affect the target.
- Soft links can span across different filesystems.
- The `ln -s` command is used to create soft links.

Example:

```
$ ln -s example.txt soft_link.txt
$ ls -li
17451 -rw-r--r-- 2 user group 1234 Jan 1 12:00 example.txt
17452 lrwxrwxrwx 1 user group       11 Jan 1 12:00 soft_link.txt -> example.txt
```

## Mount Options

Mount options are used to customize the behavior of a filesystem when it is mounted. Some common mount options include:

- `defaults`: Use the default options for the filesystem type.
- `rw`/`ro`: Mount the filesystem as read-write or read-only.
- `noatime`: Do not update the access time attribute on files.
- `nodiratime`: Do not update the access time on directories.
- `relatime`: Only update the access time if the previous access time is older than the modification time.
- `auto`/`noauto`: Mount or do not mount the filesystem at boot.
- `user`/`nouser`: Allow or disallow regular users to mount the filesystem.
- `exec`/`noexec`: Allow or disallow the execution of binaries on the filesystem.
- `sync`/`async`: Use synchronous or asynchronous I/O.
- `dirsync`: Force synchronous updates of directory metadata.
- `suid`/`nosuid`: Allow or disallow set-user-identifier or set-group-identifier bits to take effect.
- `dev`/`nodev`: Interpret or ignore character or block special devices on the filesystem.
- `_netdev`: The filesystem resides on a network device.

Example fstab entry with mount options:

```
/dev/sdb1 /data ext4 defaults,noatime,nodiratime 0 0
```

## /etc/fstab

The `/etc/fstab` (filesystem table) file is a system configuration file that describes how different filesystems should be mounted into the overall file hierarchy. Each line in the fstab file has six fields:

1. **Device**: The block device file, UUID, or label that represents the filesystem.
2. **Mount point**: The directory where the filesystem should be mounted.
3. **Filesystem type**: The type of filesystem (e.g. ext4, xfs, btrfs).
4. **Mount options**: Comma-separated list of options to use when mounting the filesystem.
5. **Dump**: Used by the `dump` backup tool to determine which filesystems need to be backed up. 0 means don't dump.
6. **Pass**: Used by the `fsck` tool to determine the order in which filesystems should be checked. 0 means don't check.

Example `/etc/fstab` file:

```
# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier (UUID)
# of a device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
UUID=14ae8a92-****-****-****-************ /                 ext4    defaults,noatime  0       1
UUID=3b6c43e2-****-****-****-************ /home             ext4    defaults          0       2
UUID=f3c46a0d-****-****-****-************ /var              ext4    defaults          0       2
/dev/sdb1                                /data              xfs     defaults          0       0
/dev/sdc1                                /backup           btrfs   defaults,subvol=@backup 0   0
tmpfs                                   /tmp               tmpfs   defaults,noatime,mode=1777 0 0
```

This example mounts the root filesystem (`/`), home directory (`/home`), and `/var` directory using the ext4 filesystem. It also mounts a XFS filesystem at `/data`, a Btrfs filesystem at `/backup`, and a tmpfs (in-memory) filesystem at `/tmp`.