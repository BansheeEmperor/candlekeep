---
title: Linux Memory Management Deep Dive
description: A comprehensive technical guide to understanding Linux memory management, virtual memory, page tables, swap, OOM killer, huge pages, and NUMA.
keywords: 
  - Linux
  - memory management
  - virtual memory
  - page tables
  - swap
  - OOM killer
  - huge pages
  - NUMA
category: Linux
tags:
  - memory
  - virtual memory
  - kernel
  - performance
---

## Linux Memory Management

Linux memory management is a complex topic that involves several interrelated components working together to efficiently utilize the available system memory. This guide will provide a deep dive into the key concepts and mechanisms that make up Linux memory management.

### Virtual Memory

Linux, like most modern operating systems, uses a virtual memory system to manage memory. Virtual memory allows processes to access more memory than is physically available on the system by mapping virtual addresses to physical addresses.

The virtual memory system is implemented using page tables, which map virtual memory pages to physical memory frames. The processor's Memory Management Unit (MMU) uses these page tables to translate virtual addresses to physical addresses during memory accesses.

#### Page Tables

Page tables are data structures maintained by the kernel that map virtual memory pages to physical memory frames. They are a critical component of the virtual memory system, as they allow the processor to translate virtual addresses to physical addresses.

Page tables are organized in a multi-level hierarchy, with a top-level page directory and lower-level page tables. The specific structure of the page table hierarchy can vary between different CPU architectures, but the general concept is the same.

```c
// Example page table entry (x86-64)
typedef struct {
    unsigned long long val;
} pte_t;

// Bit fields in the page table entry
#define PTE_PRESENT   (1UL << 0)  // Page is present in memory
#define PTE_WRITE     (1UL << 1)  // Page is writable
#define PTE_USER      (1UL << 2)  // Page is accessible from user mode
#define PTE_ACCESSED  (1UL << 5)  // Page has been accessed
#define PTE_DIRTY     (1UL << 6)  // Page has been modified
#define PTE_PSE       (1UL << 7)  // Page is a 2MB "huge page"
#define PTE_PWAIT     (1UL << 9)  // Page is waiting to be mapped
```

When a process attempts to access a virtual address, the MMU uses the page tables to translate the virtual address to a physical address. If the page is not present in the page tables, the MMU generates a page fault, which is handled by the kernel.

#### Page Fault Handling

When a page fault occurs, the kernel must determine the cause of the fault and take appropriate action. There are several types of page faults:

- **Major page fault**: The page is not present in physical memory, and the kernel must load it from disk.
- **Minor page fault**: The page is present in memory, but the access type (read/write) is not allowed.
- **Protection fault**: The process is attempting to access a page it does not have permission to access.

The kernel's page fault handler must analyze the fault and decide how to handle it. For major page faults, the kernel must allocate a physical memory frame, load the page from disk, and update the page tables to map the virtual page to the physical frame.

```c
// Example page fault handler (simplified)
void do_page_fault(struct pt_regs *regs, unsigned long error_code) {
    unsigned long address = read_cr2(); // Get faulting address
    
    if (error_code & FAULT_FLAG_WRITE) {
        // Handle write fault
        handle_write_fault(address, regs);
    } else {
        // Handle read fault
        handle_read_fault(address, regs);
    }
}

void handle_read_fault(unsigned long address, struct pt_regs *regs) {
    // Allocate a physical page frame
    struct page *page = alloc_page();
    
    // Load the page from disk
    load_page_from_disk(address, page);
    
    // Map the virtual page to the physical frame
    map_page(address, page);
    
    // Resume the faulting instruction
    resume_from_fault(regs);
}
```

The page fault handler is a critical part of the kernel's memory management system, as it is responsible for ensuring that the necessary pages are present in memory when a process attempts to access them.

### Swap

Linux uses a swap space, typically a dedicated partition or file, to temporarily store pages that are not currently in use. When the system runs low on physical memory, the kernel can swap out less-used pages to the swap space to free up memory for more active pages.

The kernel's swap subsystem manages the swap space and handles the swapping of pages in and out of memory. When a page is swapped out, the kernel updates the page table entry to mark the page as not present in memory, and stores the location of the page in the swap space.

```c
// Example swap subsystem operations
int add_to_swap(struct page *page) {
    // Allocate a swap slot
    swp_entry_t entry = get_swap_page();
    
    // Write the page contents to the swap slot
    write_swap_page(entry, page);
    
    // Update the page table entry
    set_pte_at(mm, address, pte, make_swap_pte(entry));
    
    return 0;
}

struct page *swap_in(swp_entry_t entry) {
    // Allocate a new page frame
    struct page *page = alloc_page();
    
    // Read the page contents from the swap slot
    read_swap_page(entry, page);
    
    // Update the page table entry
    set_pte_at(mm, address, pte, mk_pte(page, PAGE_KERNEL));
    
    return page;
}
```

The swap subsystem is a crucial component of the Linux memory management system, as it allows the kernel to efficiently use the available physical memory by swapping out less-active pages to the swap space.

### OOM Killer

The Out-of-Memory (OOM) killer is a mechanism in the Linux kernel that is responsible for terminating processes when the system is running low on memory. When the available memory falls below a critical threshold, the OOM killer will select a process to kill in order to free up memory and prevent the system from freezing or crashing.

The OOM killer uses a scoring system to determine which process to kill. It considers factors such as the process's memory usage, its importance to the system, and its "oominess" (how likely it is to cause the system to run out of memory). The process with the highest OOM score is the one that will be terminated.

```c
// Example OOM killer scoring function
long oom_badness(struct task_struct *task) {
    long points = 0;
    
    // Calculate points based on memory usage
    points += get_mm_rss(task->mm) / PAGE_SIZE;
    
    // Calculate points based on other factors
    if (is_system_critical_process(task))
        points -= 1000;
    if (is_interactive_process(task))
        points -= 100;
    
    return clamp(points, 0, 1000);
}
```

The OOM killer is an essential part of the Linux memory management system, as it ensures that the system can continue to function even when memory is scarce. However, it is important to configure the OOM killer carefully, as terminating the wrong process can have serious consequences for the system.

### Huge Pages

Linux supports the use of "huge pages", which are larger than the standard 4KB page size. Huge pages can provide performance benefits for certain workloads, as they can reduce the overhead of managing the page table hierarchy.

Huge pages are typically 2MB or 1GB in size, depending on the CPU architecture. To use huge pages, the kernel must be configured to support them, and the application must request the use of huge pages.

```c
// Example usage of huge pages
#include <sys/mman.h>

int main() {
    // Request a 2MB hugepage
    void *addr = mmap(NULL, 2 * 1024 * 1024, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS | MAP_HUGETLB, -1, 0);
    if (addr == MAP_FAILED) {
        perror("mmap");
        return 1;
    }
    
    // Use the huge page memory...
    
    // Free the huge page
    munmap(addr, 2 * 1024 * 1024);
    
    return 0;
}
```

Huge pages can provide significant performance benefits for certain workloads, such as databases and scientific computing applications. However, they also have some drawbacks, such as increased memory fragmentation and the need for specialized configuration.

### NUMA

Non-Uniform Memory Access (NUMA) is a computer memory design where the memory access time depends on the memory location relative to the processor. In a NUMA system, the memory is divided into multiple nodes, each with its own local memory and CPU.

When a process accesses memory, the kernel must ensure that the memory access is serviced by the local node's memory, if possible, to minimize access latency. The kernel's NUMA-aware memory management subsystem is responsible for managing memory allocations and page migrations in a NUMA system.

```c
// Example NUMA-aware memory allocation
#include <numaif.h>

int main() {
    // Allocate memory on a specific NUMA node
    void *addr = numa_alloc_onnode(4096, 0);
    if (addr == NULL) {
        perror("numa_alloc_onnode");
        return 1;
    }
    
    // Use the memory...
    
    // Free the memory
    numa_free(addr, 4096);
    
    return 0;
}
```

NUMA can have a significant impact on application performance, as memory access latency can vary greatly depending on the location of the memory relative to the CPU. Careful configuration and tuning of the NUMA subsystem is often required to achieve optimal performance on NUMA systems.

## Conclusion

Linux memory management is a complex and intricate system that involves many interrelated components. This guide has provided a deep dive into the key concepts and mechanisms that make up Linux memory management, including virtual memory, page tables, swap, the OOM killer, huge pages, and NUMA.

By understanding these technical details, system administrators and developers can optimize the performance and reliability of their Linux systems, ensuring that they are making the most efficient use of the available system memory.