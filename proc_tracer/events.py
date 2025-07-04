# proc_tracer/events.py

import ctypes as ct

# Define constants to match kernel definitions (at bpf/probes.c)
TASK_COMM_LEN = 16
FILENAME_LEN = 256


class ExecData(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("comm", ct.c_char * TASK_COMM_LEN),
        ("fname", ct.c_char * FILENAME_LEN),
    ]


class ForkData(ct.Structure):
    _fields_ = [
        ("ts", ct.c_ulonglong),
        ("ppid", ct.c_uint),
        ("pid", ct.c_uint),
        ("pcomm", ct.c_char * TASK_COMM_LEN),
        ("comm", ct.c_char * TASK_COMM_LEN),
    ]


class ExitData(ct.Structure):
    _fields_ = [
        ("ts", ct.c_ulonglong),
        ("pid", ct.c_uint),
        ("comm", ct.c_char * TASK_COMM_LEN),
    ]
