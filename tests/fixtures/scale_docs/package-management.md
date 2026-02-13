---
title: Package Management in Linux
description: A comprehensive guide to package management tools and concepts in Linux, including apt, yum, dnf, rpm, dpkg, repository configuration, and dependency resolution.
keywords: 
  - package management
  - apt
  - yum
  - dnf
  - rpm
  - dpkg
  - repository
  - dependency resolution
category: Linux
tags:
  - package management
  - apt
  - yum
  - dnf
  - rpm
  - dpkg
  - repository
  - dependency
---

## Package Management in Linux

Linux distributions use various package management tools and concepts to handle the installation, removal, and management of software packages. This guide covers the most popular package management systems, including `apt`, `yum`, `dnf`, `rpm`, and `dpkg`, as well as repository configuration and dependency resolution.

### apt (Advanced Package Tool)

`apt` is the package management tool used in Debian-based Linux distributions, such as Ubuntu and Mint.

#### Common `apt` Commands
- `apt update`: Update the package index
- `apt install <package>`: Install a package
- `apt remove <package>`: Remove a package
- `apt upgrade`: Upgrade all installed packages to the newest version
- `apt search <keyword>`: Search for a package
- `apt show <package>`: Display information about a package
- `apt list --installed`: List all installed packages

#### `apt` Configuration
The main configuration file for `apt` is `/etc/apt/sources.list`. This file specifies the repositories from which `apt` should download packages. Example entry:

```
deb http://archive.ubuntu.com/ubuntu focal main restricted universe multiverse
```

You can also add third-party repositories by creating a file in the `/etc/apt/sources.list.d/` directory, e.g., `/etc/apt/sources.list.d/nginx.list`:

```
deb http://nginx.org/packages/ubuntu/ focal nginx
```

### yum (Yellowdog Updater, Modified)

`yum` is the package management tool used in Red Hat-based Linux distributions, such as RHEL, CentOS, and Fedora.

#### Common `yum` Commands
- `yum update`: Update all installed packages
- `yum install <package>`: Install a package
- `yum remove <package>`: Remove a package
- `yum search <keyword>`: Search for a package
- `yum info <package>`: Display information about a package
- `yum list installed`: List all installed packages

#### `yum` Configuration
The main configuration file for `yum` is `/etc/yum.repos.d/`. This directory contains individual repository configuration files, such as `/etc/yum.repos.d/epel.repo`:

```
[epel]
name=Extra Packages for Enterprise Linux $releasever - $basearch
baseurl=http://download.fedoraproject.org/pub/epel/$releasever/$basearch
```

You can also enable or disable repositories by modifying the `enabled=` option in these files.

### dnf (Dandified YUM)

`dnf` is the next-generation package manager that replaced `yum` in Fedora and other recent Red Hat-based distributions.

#### Common `dnf` Commands
- `dnf update`: Update all installed packages
- `dnf install <package>`: Install a package
- `dnf remove <package>`: Remove a package
- `dnf search <keyword>`: Search for a package
- `dnf info <package>`: Display information about a package
- `dnf list installed`: List all installed packages

#### `dnf` Configuration
The `dnf` configuration is similar to `yum`, with the main configuration files located in `/etc/dnf/`.

### RPM (Red Hat Package Manager)

`rpm` is the underlying package management system used by `yum` and `dnf` in Red Hat-based distributions. It can also be used directly.

#### Common `rpm` Commands
- `rpm -i <package.rpm>`: Install a package
- `rpm -e <package>`: Remove a package
- `rpm -q <package>`: Query information about a package
- `rpm -ql <package>`: List all files installed by a package
- `rpm -Va`: Verify all installed packages

#### `rpm` Configuration
`rpm` does not have a central configuration file. However, you can customize its behavior by modifying the `/etc/rpm/` directory.

### dpkg (Debian Package Manager)

`dpkg` is the underlying package management system used by `apt` in Debian-based distributions.

#### Common `dpkg` Commands
- `dpkg -i <package.deb>`: Install a package
- `dpkg -r <package>`: Remove a package
- `dpkg -l`: List all installed packages
- `dpkg -L <package>`: List all files installed by a package
- `dpkg -S <file>`: Find the package that owns a specific file

#### `dpkg` Configuration
The main configuration file for `dpkg` is `/etc/dpkg/dpkg.cfg`. You can also create configuration files in the `/etc/dpkg/dpkg.cfg.d/` directory.

### Repository Configuration

Repositories are remote servers that host packages and their metadata. Package managers use these repositories to download and install software.

#### Configuring Repositories
- For `apt`: Edit `/etc/apt/sources.list` or add files in `/etc/apt/sources.list.d/`
- For `yum`/`dnf`: Edit individual repo files in `/etc/yum.repos.d/`
- For `rpm`: No central repository configuration, use `rpm --import` to add GPG keys

Example `apt` repository configuration:

```
deb http://archive.ubuntu.com/ubuntu focal main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu focal main restricted universe multiverse
```

Example `yum` repository configuration (`/etc/yum.repos.d/epel.repo`):

```
[epel]
name=Extra Packages for Enterprise Linux $releasever - $basearch
baseurl=http://download.fedoraproject.org/pub/epel/$releasever/$basearch
enabled=1
gpgcheck=1
gpgkey=https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-$releasever
```

### Dependency Resolution

Package managers are responsible for resolving dependencies between packages. When you install a package, the package manager will also install any required dependencies.

#### Dependency Resolution in Different Package Managers
- `apt`: Uses a dependency solver to automatically install required packages
- `yum`/`dnf`: Resolves dependencies based on package metadata and available repositories
- `rpm`: Dependency resolution is handled by the package manager frontend (e.g., `yum`, `dnf`)
- `dpkg`: Dependency resolution is handled by the package manager frontend (e.g., `apt`)

Example of dependency resolution with `apt`:

```
$ apt install firefox
Reading package lists... Done
Building dependency tree
Reading state information... Done
The following additional packages will be installed:
  firefox-geckodriver fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libavcodec58 libavformat58 libavutil56 libbrotli1 libcairo2 libcolord2 libcroco3 libdbus-1-3 libdbusmenu-gtk4 libdrm2 libepoxy0 libexpat1 libffi7 libfreetype6 libgdk-pixbuf2.0-0 libglib2.0-0 libgmp10 libgomp1 libgraphite2-3 libgsettings-qt1 libgssapi-krb5-2 libharfbuzz0b libhyphen0 libice6 libjpeg-turbo8 libjsoncpp24 libk5crypto3 libkeyutils1 libkrb5-3 libkrb5support0 liblcms2-2 libldap-2.4-2 libllvm11 libltdl7 liblz4-1 libmp3lame0 libncurses6 libnspr4 libnss3 libogg0 libopenjp2-7 libp11-kit0 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libpcre2-8-0 libpixman-1-0 libpng16-16 libproxy1v5 libpulse0 libqt5core5a libqt5dbus5 libqt5gui5 libqt5network5 libqt5widgets5 libsm6 libsndfile1 libsnmp30 libsoup2.4-1 libsqlite3-0 libssl1.1 libstb0 libstdc++6 libtheora0 libtiff5 libtinfo6 libudev1 libvorbis0a libvorbisenc2 libwayland-client0 libwayland-server0 libwebp6 libwoff1 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxinerama1 libxkbcommon0 libxml2 libxrandr2 libxrender1 libxshmfence1 libxt6 libxtst6 libxxf86vm1 lsb-release mesa-va-drivers mesa-vdpau-drivers mesa-vulkan-drivers ocl-icd-libopencl1 xdg-utils
The following NEW packages will be installed:
  firefox firefox-geckodriver fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libavcodec58 libavformat58 libavutil56 libbrotli1 libcairo2 libcolord2 libcroco3 libdbus-1-3 libdbusmenu-gtk4 libdrm2 libepoxy0 libexpat1 libffi7 libfreetype6 libgdk-pixbuf2.0-0 libglib2.0-0 libgmp10 libgomp1 libgraphite2-3 libgsettings-qt1 libgssapi-krb5-2 libharfbuzz0b libhyphen0 libice6 libjpeg-turbo8 libjsoncpp24 libk5crypto3 libkeyutils1 libkrb5-3 libkrb5support0 liblcms2-2 libldap-2.4-2 libllvm11 libltdl7 liblz4-1 libmp3lame0 libncurses6 libnspr4 libnss3 libogg0 libopenjp2-7 libp11-kit0 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 libpcre2-8-0 libpixman-1-0 libpng16-16 libproxy1v5 libpulse0 libqt5core5a libqt5dbus5 libqt5gui5 libqt5network5 libqt5widgets5 libsm6 libsndfile1 libsnmp30 libsoup2.4-1 libsqlite3-0 libssl1.1 libstb0 libstdc++6 libtheora0 libtiff5 libtinfo6 libudev1 libvorbis0a libvorbisenc2 libwayland-client0 libwayland-server0 libwebp6 libwoff1 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxinerama1 libxkbcommon0 libxml2 libxrandr2 libxrender