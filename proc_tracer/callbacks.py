# proc_tracer/callbacks.py

import os
import time
import ctypes as ct
from .events import ExecData, ForkData, ExitData

class ProcessNode:
    """
    Represents a single process in the process tree.
    """
    def __init__(self, pid, ppid, comm="<...>", is_initial=False, creation_time=0):
        self.pid = pid
        self.ppid = ppid
        self.comm = comm

        # Timing metadata to track process life cycle
        self.creation_time = creation_time
        self.exit_time = 0

        # We use a dictionary for children for quick lookups and removal.
        # - Key: child_pid
        # - Value: ProcessNode instance (for the child process)
        self.children = {}

        # NOTE: Flag for processes existed beofre the tracer started
        self.is_initial = is_initial

    @property
    def execution_time_s(self):
        """
        Calculates execution time in seconds(s).
        Returns execution duration for exited processes or uptime for running processes.
        """
        if not self.creation_time:
            return None

        # Use exit time if it exits, otherwise use current time
        # NOTE: Use time.monotonic_ns() for live processes to match the kernel's eBPF clock(from boot).
        end_time_ns = self.exit_time or time.monotonic_ns()

        if end_time_ns < self.creation_time:
            return 0.0

        duration_ns = end_time_ns - self.creation_time
        return duration_ns / 1_000_000_000.0  # Convert nanoseconds to seconds

class ProcessTreeTracker:
    """
    A stateful class to build and display a live process tree from eBPF events.
    """
    def __init__(self, max_history=20):
        # The core data structure
        # - Key: pid (int)
        # - Value: ProcessNode instance
        self.nodes = {}

        # Store a list of recently exited processes to display their final stats
        self.history = []
        self.max_history = max_history

        print("ProcessTreeTracker initialized. Populating initial state from /proc...")
        self._populate_initial_tree()
        print(f"Initial process tree populated with {len(self.nodes)} processes.")


    def _rewrite_screen(self):
        """
        Rewrites the screen without forking a new process.
        - \033[H - Move cursor to the top-left corner of the terminal.
        - \033[J - Clear the screen from the cursor to the end of the screen.
        """
        print("\033[H\033[J", end='')

    def _populate_initial_tree(self):
        """
        Scans the /proc filesystem to build an initial process tree.
        (To track processes that existed before the tracer started.)
        """
        # First pass: Create a ProcessNode for every existing process
        tracer_start_time = time.monotonic_ns()
        for pid_str in os.listdir("/proc"):
            if not pid_str.isdigit():
                continue

            pid = int(pid_str)

            try:
                with open(f"/proc/{pid}/comm", "r") as f:
                    lines = f.readlines()

                comm = lines[0].strip() if lines else "<unknown>"
                ppid = lines[6].strip() if len(lines) > 6 else "???"

                # Create the node and add it to the nodes dictioanry
                node = ProcessNode(
                    pid=pid,
                    ppid=ppid,
                    comm=comm,
                    is_initial=True,
                    creation_time=tracer_start_time
                )
                self.nodes[pid] = node

            except FileNotFoundError:
                # The process might have exited before we could read it
                continue
            except (ValueError, IndexError):
                # If we can't read the comm or ppid, skip this process
                continue

        # Second pass: Link children to parents, which was missing.
        for node in self.nodes.values():
            if node.ppid in self.nodes:
                self.nodes[node.ppid].children[node.pid] = node

    def print_tree(self):
        """
        Prints the entire process tree by finding roots and traversing.
        """
        self._rewrite_screen()
        print("=== Live Process Tree ===")

        # Find all root nodes (nodes whose parent is not in our tracked set)
        # Then, Sort roots by PID and print the subtree for each
        root_nodes = sorted(
            [node for node in self.nodes.values() if node.ppid not in self.nodes],
            key=lambda x: x.pid
        )
        for node in root_nodes:
            self._print_subtree(node, 0)

        # Print recently exited nodes
        print("\n=== Recently Exited Processes ===")
        for node in self.history:
            exec_time = node.execution_time_s
            time_str = f"ran for {exec_time:.3f}s" if exec_time is not None else ""
            print(f"- {node.pid:<6} {node.comm:<20} {time_str}")

        print("\n" + "="*50)
        print(f"Tracking {len(self.nodes)} processes.\n")
        
    def _print_subtree(self, node, indent_level):
        """
        Recursively prints a subtree starting from the given node.
        """
        indent = "  " * indent_level
        prefix = "|- " if indent_level > 0 else ""
        initial_marker = "*" if node.is_initial else ""

        exec_time = node.execution_time_s
        time_str = f"(Running for {exec_time:.3f}s)" if exec_time is not None else ""

        print(f"{indent}{prefix}{node.pid:<6} {node.comm:<20} {time_str} {initial_marker}")

        for child_node in sorted(
            node.children.values(), 
            key=lambda x: x.pid):
            self._print_subtree(child_node, indent_level + 1)

    def handle_fork(self, cpu, data, size):
        """
        Callback for fork(sched_process_fork) events.
        Adds a new process to the status.
        """
        _ = cpu
        _ = size
        event = ct.cast(data, ct.POINTER(ForkData)).contents

        parent_node = self.nodes.get(event.ppid, None)
        if not parent_node:
            # Create a new root node if the parent is not tracked
            parent_node = ProcessNode(event.ppid, ppid="???",
                                      comm=event.pcomm.decode('utf-8', 'replace'),
                                      is_initial=True,
                                      creation_time=event.ts)
            self.nodes[event.ppid] = parent_node

        child_node = ProcessNode(event.pid, event.ppid,
                                 comm=event.comm.decode('utf-8', 'replace'),
                                 creation_time=event.ts)

        # Add the child node to our main nodes dictionary
        self.nodes[event.pid] = child_node

        # Link the child to the parent
        parent_node.children[event.pid] = child_node

    def handle_exec(self, cpu, data, size):
        """
        Callback for exec(sched_process_exec) events.
        Updates the command of an existing process.
        """
        _ = cpu
        _ = size
        event = ct.cast(data, ct.POINTER(ExecData)).contents

        node = self.nodes.get(event.pid)
        if node:
            node.comm = event.comm.decode('utf-8', 'replace')
            node.is_initial = False  # Mark as not initial anymore
        else:
            # Exec from a process we missed.
            node = ProcessNode(event.pid, ppid="???",
                               comm=event.comm.decode('utf-8', 'replace'),
                               is_initial=False,
                               creation_time=time.monotonic_ns())
            self.nodes[event.pid] = node

    def handle_exit(self, cpu, data, size):
        """
        Callback for exit(sched_process_exit) events.
        Removes a process from the status.
        """
        _ = cpu
        _ = size
        event = ct.cast(data, ct.POINTER(ExitData)).contents

        # Find the node that is exiting now
        exiting_node = self.nodes.get(event.pid, None)
        if not exiting_node:
            # Do not track if the process is not in our tree
            return

        # Set the exit time
        exiting_node.exit_time = event.ts

        # Unlink from the parent
        parent_node = self.nodes.get(exiting_node.ppid)
        if parent_node and event.pid in parent_node.children:
            del parent_node.children[event.pid]

        # NOTE: The children of the exiting node are now orphans (orphaned processes).
        # The rendering will be automatically updated to reflect this.
        
        # Move from live nodes to history
        del self.nodes[event.pid]

        # Add to history and keep history list at a fixed size at most `max_history`
        self.history.insert(0, exiting_node)
        if len(self.history) > self.max_history:
            self.history.pop()
