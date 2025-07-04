// bpf/probes.c

#include <linux/sched.h>
#include <uapi/linux/ptrace.h>

// Data structures to send to user-space
struct exec_data {
  u32 pid;
  char comm[TASK_COMM_LEN];
  char fname[256];
};

struct fork_data {
  u64 ts;
  u32 ppid;
  u32 pid;
  char pcomm[TASK_COMM_LEN];
  char comm[TASK_COMM_LEN];
};

struct exit_data {
  u64 ts;
  u32 pid;
  char comm[TASK_COMM_LEN];
};

// Perf output buffers
BPF_PERF_OUTPUT(exec_events);
BPF_PERF_OUTPUT(fork_events);
BPF_PERF_OUTPUT(exit_events);

// HELPER FUNCTION for exec* syscalls
static inline int process_exec(void *ctx, const char __user *filename) {
  struct exec_data data = {};

  // Get PID and command
  data.pid = bpf_get_current_pid_tgid() >> 32;
  bpf_get_current_comm(&data.comm, sizeof(data.comm));
  bpf_probe_read_user_str(&data.fname, sizeof(data.fname), filename);

  return 0;
}

// 1a. execve syscall entry
TRACEPOINT_PROBE(syscalls, sys_enter_execve) {
  return process_exec(args, args->filename);
}

// 1b. execveat syscall entry
TRACEPOINT_PROBE(syscalls, sys_enter_execveat) {
  return process_exec(args, args->filename);
}

// 2. process fork
TRACEPOINT_PROBE(sched, sched_process_fork) {
  struct fork_data data = {};
  data.ts = bpf_ktime_get_ns();
  data.ppid = args->parent_pid;
  data.pid = args->child_pid;
  bpf_probe_read_kernel_str(&data.pcomm, sizeof(data.pcomm), args->parent_comm);
  bpf_probe_read_kernel_str(&data.comm, sizeof(data.comm), args->child_comm);

  fork_events.perf_submit(args, &data, sizeof(data));
  return 0;
}

// 3. process exit
TRACEPOINT_PROBE(sched, sched_process_exit) {
  struct exit_data data = {};
  data.ts = bpf_ktime_get_ns();
  data.pid = args->pid;
  bpf_probe_read_kernel_str(&data.comm, sizeof(data.comm), args->comm);

  exit_events.perf_submit(args, &data, sizeof(data));
  return 0;
}
