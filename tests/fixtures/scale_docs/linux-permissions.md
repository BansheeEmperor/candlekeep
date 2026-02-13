---
title: Linux File Permissions and Security
description: A comprehensive technical guide to managing file permissions, ownership, and advanced security features in Linux.
keywords: 
  - linux
  - file permissions
  - chmod
  - chown
  - acls
  - setuid
  - setgid
  - sticky bit
  - umask
  - capabilities
category: system administration
tags:
  - linux
  - security
  - file system
  - permissions
  - ownership
---

## Linux File Permissions

Linux files and directories have a set of permissions that control who can read, write, and execute the content. These permissions are stored as a series of 10 bits, with the first bit indicating the file type (`-` for regular file, `d` for directory, `l` for symlink, etc.), and the remaining 9 bits controlling the read, write, and execute permissions for the owner, group, and others.

The permissions are typically displayed in the format `rwxrwxrwx`, where `r` represents read, `w` represents write, and `x` represents execute. The first set of 3 bits is for the owner, the middle 3 bits are for the group, and the last 3 bits are for others.

For example, the permissions `-rw-r--r--` would mean:

- The first `-` indicates a regular file
- The owner has read and write permissions
- The group has read permissions
- Others have read permissions

You can view the permissions for a file or directory using the `ls -l` command:

```
$ ls -l
-rw-r--r-- 1 user group 1234 Apr 20 15:45 file.txt
drwxr-xr-x 2 user group 4096 Apr 19 10:23 directory/
```

## Changing File Permissions with `chmod`

The `chmod` (change mode) command is used to modify the permissions of a file or directory. You can specify the permissions using either symbolic notation or octal notation.

### Symbolic Notation

Symbolic notation uses the letters `u` (user/owner), `g` (group), `o` (others), and `a` (all) to represent the target, and the operators `+` (add), `-` (remove), and `=` (set) to specify the changes.

Examples:

- `chmod u+x file.txt`: Add execute permission for the owner
- `chmod go-w file.txt`: Remove write permission for group and others
- `chmod a=rx file.txt`: Set read and execute permissions for all

### Octal Notation

Octal notation uses a 3-digit number to represent the permissions, where each digit corresponds to the owner, group, and others, respectively. The digits range from 0 to 7, with each bit representing the read, write, and execute permissions.

- 4 = read (`r--`)
- 2 = write (`-w-`)
- 1 = execute (`--x`)

Examples:

- `chmod 755 file.txt`: Set permissions to `rwxr-xr-x`
- `chmod 644 file.txt`: Set permissions to `rw-r--r--`
- `chmod 700 directory/`: Set permissions to `rwx------`

## Changing File Ownership with `chown`

The `chown` (change owner) command is used to modify the owner and/or group of a file or directory.

Examples:

- `chown user:group file.txt`: Change the owner and group of the file
- `chown user file.txt`: Change the owner of the file, keeping the group the same
- `chown :group file.txt`: Change the group of the file, keeping the owner the same

## Access Control Lists (ACLs)

Access Control Lists (ACLs) provide a more granular way to control permissions on files and directories. ACLs allow you to set permissions for specific users or groups, beyond the basic owner, group, and others permissions.

To enable ACLs, you need to ensure the `acl` package is installed and that the file system supports ACLs (e.g., ext4, XFS).

### Setting ACLs with `setfacl`

The `setfacl` command is used to modify the ACL of a file or directory.

Examples:

- `setfacl -m u:user:rwx file.txt`: Add read, write, and execute permissions for the user
- `setfacl -m g:group:rx file.txt`: Add read and execute permissions for the group
- `setfacl -m d:u:user:rwx directory/`: Set default ACL for new files in the directory

### Viewing ACLs with `getfacl`

The `getfacl` command is used to view the ACL of a file or directory.

Example:
```
$ getfacl file.txt
# file: file.txt
# owner: user
# group: group
user::rw-
user:other_user:rwx
group::r--
mask::rwx
other::r--
```

## Setuid, Setgid, and Sticky Bit

The setuid, setgid, and sticky bits are special permission bits that can be set on files and directories to modify their behavior.

### Setuid Bit

The setuid bit, when set on an executable file, causes the process to run with the permissions of the file's owner, rather than the user who executed the file.

Example:
```
-rwsr-xr-x 1 root root 16K Apr 20 15:45 /usr/bin/passwd
```

The `s` in the permissions indicates the setuid bit is set.

### Setgid Bit

The setgid bit, when set on a directory, causes new files and subdirectories created within that directory to inherit the group ownership of the directory, rather than the user's primary group.

When set on an executable file, it behaves similarly to the setuid bit, but the process runs with the permissions of the file's group instead of the owner.

Example:
```
drwxrwsr-x 2 root developers 4096 Apr 19 10:23 project/
-rwxr-sr-x 1 root developers 16K Apr 20 15:45 program
```

The `s` in the group permissions indicates the setgid bit is set.

### Sticky Bit

The sticky bit, when set on a directory, prevents users from deleting or renaming files in that directory unless they are the owner of the file, the owner of the directory, or the superuser.

Example:
```
drwxrwxrwt 2 root root 4096 Apr 19 10:23 /tmp/
```

The `t` in the permissions indicates the sticky bit is set.

## The `umask` Command

The `umask` command sets the default permissions for newly created files and directories. It works by subtracting the specified permissions from the default permissions (usually `0666` for files and `0777` for directories).

Example:
```
$ umask
0022
$ touch file.txt
$ ls -l file.txt
-rw-r--r-- 1 user group 0 Apr 20 15:45 file.txt
```

In this example, the default permissions for a new file are `0644` (because the default is `0666` and the `umask` is `0022`).

## Linux Capabilities

Linux capabilities provide a finer-grained approach to managing superuser privileges. Instead of granting the entire set of superuser (root) privileges to a process, capabilities allow you to grant only the specific privileges that the process needs.

Some common capabilities include:

- `CAP_CHOWN`: Allows changing the owner of a file or directory
- `CAP_DAC_OVERRIDE`: Allows overriding directory permissions
- `CAP_FOWNER`: Allows performing operations on files/directories owned by a different user
- `CAP_KILL`: Allows sending signals to processes owned by a different user
- `CAP_NET_ADMIN`: Allows configuring network interfaces and firewall rules

You can view the capabilities of a process using the `getcap` command, and set capabilities using the `setcap` command.

Example:
```
$ getcap /usr/bin/ping
/usr/bin/ping = cap_net_raw+ep
$ setcap cap_net_raw+ep /usr/bin/ping
$ getcap /usr/bin/ping
/usr/bin/ping = cap_net_raw+ep
```

In this example, the `ping` command is granted the `CAP_NET_RAW` capability, allowing it to use raw sockets without requiring superuser privileges.