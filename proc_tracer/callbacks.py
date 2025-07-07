# proc_tracer/callbacks.py

import os
import time
import ctypes as ct
from .models import ProcessNode
from .events import ExecData, ForkData, ExitData


class ProcessTreeTracker:
    """
    A stateful class to build and display a live process tree from eBPF events.
    """

    def __init__(self, max_history=10):
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
                with open(f"/proc/{pid}/status", "r") as f:
                    lines = f.readlines()

                comm = lines[0].strip() if lines else "<unknown>"
                ppid = lines[6].strip() if len(lines) > 6 else "???"

                # Create the node and add it to the nodes dictioanry
                node = ProcessNode(
                    pid=pid,
                    ppid=ppid,
                    comm=comm,
                    is_initial=True,
                    creation_time=tracer_start_time,
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
                parent = self.nodes[node.ppid]
                parent.children[node.pid] = node
                parent.activave_children_count += 1

    def _find_root(self, node: ProcessNode):
        """
        (Helper method)
        Traverse up the tree to find the root of a given node.
        """
        current = node
        while current.ppid in self.nodes:
            parent = self.nodes.get(current.ppid)
            if not parent:
                break
            current = parent
        return current

    def _prune_tree(self, node: ProcessNode):
        """
        (Helper method)
        Recursively removes a node and all its children from self.nodes
        """
        for child in node.children.values():
            self._prune_tree(child)
        if node.pid in self.nodes:
            del self.nodes[node.pid]

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
            parent_node = ProcessNode(
                event.ppid,
                ppid="???",
                comm=event.pcomm.decode("utf-8", "replace"),
                is_initial=True,
                creation_time=event.ts,
            )
            self.nodes[event.ppid] = parent_node

        # Increment the parent's active children count
        parent_node.active_children_count += 1

        child_node = ProcessNode(
            event.pid,
            event.ppid,
            comm=event.comm.decode("utf-8", "replace"),
            creation_time=event.ts,
        )

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
            node.comm = event.comm.decode("utf-8", "replace")
            node.is_initial = False  # Mark as not initial anymore
        else:
            # Exec from a process we missed.
            node = ProcessNode(
                event.pid,
                ppid="???",
                comm=event.comm.decode("utf-8", "replace"),
                is_initial=False,
                creation_time=time.monotonic_ns(),
            )
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
        if not exiting_node or not exiting_node.is_active:
            # Do not track if the process is not in our tree
            return

        # Set the exit time and mark the node as inactive
        exiting_node.exit_time = event.ts
        exiting_node.is_active = False

        # Decrement the parent's active child count
        parent_node = self.nodes.get(exiting_node.ppid, None)
        if parent_node:
            parent_node.active_children_count -= 1

        # Check for a reapable tree.
        # We start checking from the parent of the exiting node and move upwards.
        node_to_check = exiting_node
        while node_to_check:
            is_absolute_root = (
                node_to_check.ppid not in self.nodes
            )  # Is this node a root?
            is_gnome_shell_exception = (
                node_to_check.comm == "gnome-shell"
            )  # Is this node's comm "gnome-shell"? (Speical rule)

            if (
                is_absolute_root or is_gnome_shell_exception
            ) and node_to_check.is_terminated_tree:
                # We find a reapable root (either real or a gnome-shell sub-root).
                # First, unlink it from its own parent to break the tree structure.
                reap_root_parent = self.nodes.get(node_to_check.ppid, None)
                if reap_root_parent and node_to_check.pid in reap_root_parent.children:
                    del reap_root_parent.children[node_to_check.pid]

                # Now prune the entire sub-tree from the live nodes
                self._prune_tree(node_to_check)

                # Then, move 'em to history
                self.history.insert(0, node_to_check)
                if len(self.history) > self.max_history:
                    self.history.pop()

                return

            # Move up the tree if we are not at the root
            node_to_check = self.nodes.get(node_to_check.ppid, None)
