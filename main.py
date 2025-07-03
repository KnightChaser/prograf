from bcc import BPF
import ctypes as ct

# BPF program
bpf_text = r"""
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

// Data structures to send to user-space
struct exec_data {
    u32 pid;
    char comm[TASK_COMM_LEN];
    char fname[256];
};

struct fork_data {
    u32 ppid;
    u32 pid;
    char pcomm[TASK_COMM_LEN];
    char comm[TASK_COMM_LEN];
};

struct exit_data {
    u32 pid;
    char comm[TASK_COMM_LEN];
};

// Perf output buffers
BPF_PERF_OUTPUT(exec_events);
BPF_PERF_OUTPUT(fork_events);
BPF_PERF_OUTPUT(exit_events);

// 1. execve syscall entry
TRACEPOINT_PROBE(syscalls, sys_enter_execve) {
    struct exec_data data = {};
    data.pid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    bpf_probe_read_user_str(&data.fname, sizeof(data.fname), (void *)args->filename);

    exec_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

// 2. process fork
TRACEPOINT_PROBE(sched, sched_process_fork) {
    struct fork_data data = {};
    data.ppid = args->parent_pid;
    data.pid  = args->child_pid;
    bpf_probe_read_kernel_str(&data.pcomm, sizeof(data.pcomm), args->parent_comm);
    bpf_probe_read_kernel_str(&data.comm,  sizeof(data.comm),  args->child_comm);

    fork_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

// 3. process exit
TRACEPOINT_PROBE(sched, sched_process_exit) {
    struct exit_data data = {};
    data.pid = args->pid;
    bpf_probe_read_kernel_str(&data.comm, sizeof(data.comm), args->comm);

    exit_events.perf_submit(args, &data, sizeof(data));
    return 0;
}
"""

# Define Python data structures to match the C structs
class ExecData(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("comm", ct.c_char * 16), # TASK_COMM_LEN
        ("fname", ct.c_char * 256)
    ]

class ForkData(ct.Structure):
    _fields_ = [
        ("ppid", ct.c_uint),
        ("pid", ct.c_uint),
        ("pcomm", ct.c_char * 16),
        ("comm", ct.c_char * 16)
    ]

class ExitData(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("comm", ct.c_char * 16)
    ]


# load BPF program
# This will compile the C code and automatically attach the TRACEPOINT_PROBEs.
b = BPF(text=bpf_text)

# Event callback functions
def print_exec(cpu, data, size):
    # Use the ctypes structure to cast the raw data
    e = ct.cast(data, ct.POINTER(ExecData)).contents
    print(f"EXEC  PID={e.pid:<6} COMM={e.comm.decode('utf-8', 'replace'):<16} FILE={e.fname.decode('utf-8', 'replace')}")

def print_fork(cpu, data, size):
    e = ct.cast(data, ct.POINTER(ForkData)).contents
    print(f"FORK  PPID={e.ppid:<6} P_COMM={e.pcomm.decode('utf-8', 'replace'):<16} -> PID={e.pid:<6} COMM={e.comm.decode('utf-8', 'replace')}")

def print_exit(cpu, data, size):
    e = ct.cast(data, ct.POINTER(ExitData)).contents
    print(f"EXIT  PID={e.pid:<6} COMM={e.comm.decode('utf-8', 'replace'):<16}")

# Set up perf buffers and attach callbacks
b["exec_events"].open_perf_buffer(print_exec)
b["fork_events"].open_perf_buffer(print_fork)
b["exit_events"].open_perf_buffer(print_exit)

print("Tracing process events... Ctrl+C to quit.")

# Main loop
while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
