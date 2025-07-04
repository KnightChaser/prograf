# proc_tracer/models.py

import time


class ProcessNode:
    """
    Represents a single process in the process tree. This is a data model.
    """

    def __init__(self, pid, ppid, comm="<...>", is_initial=False, creation_time=0):
        self.pid = pid
        self.ppid = ppid
        self.comm = comm

        # Timing metadata (in nanoseconds, from monotonic clock)
        self.creation_time = creation_time
        self.exit_time = 0

        # State attributes
        self.is_active = True
        self.is_initial = is_initial

        # Children are stored as a dictionary for efficient lookup
        self.children = {}

    @property
    def execution_time_s(self):
        """
        Calculates execution time in seconds.
        Returns duration for exited processes or uptime for running ones.
        """
        if not self.creation_time:
            return None

        # Use monotonic_ns for live processes to match the kernel's clock source
        end_time_ns = self.exit_time or time.monotonic_ns()

        if end_time_ns < self.creation_time:
            return 0.0

        duration_ns = end_time_ns - self.creation_time
        return duration_ns / 1_000_000_000.0
