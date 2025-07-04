# proc_tracer/callbacks.py

import os
import ctypes as ct
from .events import ExecData, ForkData, ExitData

class ProcessNode:
    """
    Represents a single process in the process tree.
    """
    def __init__(self, pid, ppid, comm="<...>", is_initial=False):
        self.pid = pid
        self.ppid = ppid
        self.comm = comm

        # We use a dictionary for children for quick lookups and removal.
        # - Key: child_pid
        # - Value: ProcessNode instance (for the child process)
        self.children = {}

        # NOTE: Flag for processes existed beofre the tracer started
        self.is_initial = is_initial

class ProcessTreeTracker:
    """
    A stateful class to build and display a live process tree from eBPF events.
    """
    def __init__(self):
        # The core data structure
        # - Key: pid (int)
        # - Value: ProcessNode instance
        self.nodes = {}

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

    def print_tree(self):
        """
        Prints the entire process tree by finding roots and traversing.
        """
        self._rewrite_screen()
        print("=== Live Process Tree ===")

        # Find all root nodes (nodes whose parent is not in our tracked set)
        root_nodes = []
        for _, node in self.nodes.items():
            if node.ppid not in self.nodes:
                root_nodes.append(node)

        # Sort roots by PID and print the subtree for each
        for node in sorted(root_nodes, key=lambda x: x.pid):
            self._print_subtree(node, 0)

        print("\n" + "="*50)
        print(f"Tracking {len(self.nodes)} processes.\n")

    def _populate_initial_tree(self):
        """
        Scans the /proc filesystem to build an initial process tree.
        (To track processes that existed before the tracer started.)
        """
        # First pass: Create a ProcessNode for every existing process
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
                    is_initial=True
                )
                self.nodes[pid] = node

            except FileNotFoundError:
                # The process might have exited before we could read it
                continue
            except (ValueError, IndexError):
                # If we can't read the comm or ppid, skip this process
                continue

        # Second pass: Link children to their parents
        for node in self.nodes.values():
            if node.ppid in self.nodes:
                parent_node = self.nodes[node.ppid]
                parent_node.children[node.pid] = node

    def _print_subtree(self, node, indent_level):
        """
        Recursively prints a subtree starting from the given node.
        """
        indent = "  " * indent_level
        prefix = "|- " if indent_level > 0 else ""
        initial_marker = "*" if node.is_initial else ""
        
        print(f"{indent}{prefix}{node.pid:<6} {node.comm:<20} {initial_marker}")

        # Recursively call for children, sorted by PID
        for child_node in sorted(node.children.values(), key=lambda x: x.pid):
            self._print_subtree(child_node, indent_level + 1)

    def handle_fork(self, cpu, data, size):
        """
        Callback for fork(sched_process_fork) events.
        Adds a new process to the status.
        """
        _ = cpu
        _ = size
        event = ct.cast(data, ct.POINTER(ForkData)).contents

        # Ensure the parent node exists (it might be an un-traced, pre-existing process)
        if event.ppid not in self.nodes:
            # Create a placeholder for the parent
            parent_node = ProcessNode(event.ppid, 
                                      ppid="???", 
                                      comm=event.pcomm.decode('utf-8', 'replace'), 
                                      is_initial=True)
            self.nodes[event.ppid] = parent_node
        else:
            parent_node = self.nodes[event.ppid]

        # Create the new child node
        child_comm = event.comm.decode('utf-8', 'replace')
        child_node = ProcessNode(event.pid, event.ppid, child_comm)
        
        # Add to the main node dictionary and link to parent
        self.nodes[event.pid] = child_node
        parent_node.children[event.pid] = child_node

    def handle_exec(self, cpu, data, size):
        """
        Callback for exec(sched_process_exec) events.
        Updates the command of an existing process.
        """
        _ = cpu
        _ = size
        event = ct.cast(data, ct.POINTER(ExecData)).contents

        if event.pid in self.nodes:
            # Update the command for an existing trakced process
            self.nodes[event.pid].comm = event.comm.decode('utf-8', 'replace')
            self.nodes[event.pid].is_initial = False
        else:
            # This is an exec from a process that existed before we started tracing.
            # Add it as a new root node.
            node = ProcessNode(event.pid,
                               ppid="???",
                               comm=event.comm.decode('utf-8', 'replace'), 
                               is_initial=True)
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

        # Unlink from the parent
        parent_node = self.nodes.get(exiting_node.ppid)
        if parent_node:
            if event.pid in parent_node.children:
                del parent_node.children[event.pid]

        # NOTE: The children of the exiting node are now orphans (orphaned processes).
        # The rendering will be automatically updated to reflect this.

        # Finally, remove the exiting node from our main nodes dictionary
        del self.nodes[event.pid]
