#include <linux/sched.h>
#include <uapi/linux/ptrace.h>

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
  bpf_probe_read_user_str(&data.fname, sizeof(data.fname),
                          (void *)args->filename);

  exec_events.perf_submit(args, &data, sizeof(data));
  return 0;
}

// 2. process fork
TRACEPOINT_PROBE(sched, sched_process_fork) {
  struct fork_data data = {};
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
  data.pid = args->pid;
  bpf_probe_read_kernel_str(&data.comm, sizeof(data.comm), args->comm);

  exit_events.perf_submit(args, &data, sizeof(data));
  return 0;
}
