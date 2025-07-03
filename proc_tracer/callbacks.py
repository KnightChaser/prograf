# proc_tracer/callbacks.py

import ctypes as ct
from .events import ExecData, ForkData, ExitData
def print_exec(cpu, data, size):
    """Callback for exec events."""
    e = ct.cast(data, ct.POINTER(ExecData)).contents
    print(f"EXEC  PID={e.pid:<6} COMM={e.comm.decode('utf-8', 'replace'):<16} FILE={e.fname.decode('utf-8', 'replace')}")

def print_fork(cpu, data, size):
    """Callback for fork events."""
    e = ct.cast(data, ct.POINTER(ForkData)).contents
    print(f"FORK  PPID={e.ppid:<6} P_COMM={e.pcomm.decode('utf-8', 'replace'):<16} -> PID={e.pid:<6} COMM={e.comm.decode('utf-8', 'replace')}")

def print_exit(cpu, data, size):
    """Callback for exit events."""
    e = ct.cast(data, ct.POINTER(ExitData)).contents
    print(f"EXIT  PID={e.pid:<6} COMM={e.comm.decode('utf-8', 'replace'):<16}")
