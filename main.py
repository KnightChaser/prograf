from bcc import BPF
import ctypes as ct

# BPF program (open the text from bpf.c)
bpf_text = ""
with open("bpf.c", "r") as f:
    bpf_text = f.read()

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
