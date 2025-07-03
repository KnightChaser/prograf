# proc_tracer/callbacks.py

import ctypes as ct
import os
import collections
from .events import ExecData, ForkData, ExitData

class StatusTracker:
    """
    A stateful class to track the live processes based on eBPF events.
    """
    def __init__(self):
        # The core data structure
        # - Key: pid (int)
        # - Value: dictionary {"ppid": int, "comm": str}
        self.status = collections.OrderedDict()

        print("StatusTracker initialized.")

    def _rewrite_screen(self):
        """
        Rewrites the screen without forking a new process.
        - \033[H - Move cursor to the top-left corner of the terminal.
        - \033[J - Clear the screen from the cursor to the end of the screen.
        """
        print("\033[H\033[J", end='')

    def _print_status(self):
        """
        Internal method to print the current state of all tracked progress.
        This method is called after every event to update the display.
        """
        self._rewrite_screen()
        print("=== Live Process Status ===")
        print(f"Tracking {len(self.status)} processes.\n")
        print(f"{'PID':<8} {'PPID':<8} {'COMMAND'}")
        print(f"{'='*8} {'='*8} {'='*20}")

        # Print processes sorted by PID for consistency
        for pid in sorted(self.status.keys()):
            proc = self.status[pid]
            print(f"{pid:<8} {proc.get('ppid', 'N/A'):<8} {proc.get('comm', 'N/A')}")
        
        print("\n" + "="*40)


    def handle_fork(self, cpu, data, size):
        """
        Callback for fork(sched_process_fork) events.
        Adds a new process to the status.
        """
        event = ct.cast(data, ct.POINTER(ForkData)).contents

        # Add the new child process to the status dictionary
        self.status[event.pid] = {
            "ppid": event.ppid,
            "comm": event.comm.decode('utf-8', 'replace')
        }

        # In a fork, if there is no parent process,
        # It might be a process before the tracer started.
        # We just add it without PPID information.
        if event.ppid not in self.status:
            self.status[event.ppid] = {
                "ppid": "N/A",
                "comm": event.comm.decode('utf-8', 'replace')
            }

        self._print_status()

    def handle_exec(self, cpu, data, size):
        """
        Callback for exec(sched_process_exec) events.
        Updates the command of an existing process.
        """
        event = ct.cast(data, ct.POINTER(ExecData)).contents

        if event.pid in self.status:
            self.status[event.pid]["comm"] = event.comm.decode('utf-8', 'replace')
        else:
            # If the process is not tracked, we can add it
            self.status[event.pid] = {
                "ppid": "N/A",
                "comm": event.comm.decode('utf-8', 'replace')
            }

        self._print_status()

    def handle_exit(self, cpu, data, size):
        """
        Callback for exit(sched_process_exit) events.
        Removes a process from the status.
        """
        event = ct.cast(data, ct.POINTER(ExitData)).contents

        if event.pid in self.status:
            del self.status[event.pid]
            self._print_status()
        # If not, we don't do anything.
