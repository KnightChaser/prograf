# proc_tracer/renderer.py


class ConsoleRenderer:
    """
    Handles all rendering of the process tree to the console.
    """

    def __init__(self, tracker):
        self.tracker = tracker

    def _rewrite_screen(self):
        """
        Clears the console screen without using any external libraries or
        fork processes. (e.g., "clear" command in Linux)
        """
        print("\033[H\033[J", end="")

    def _print_subtree(self, node, indent_level):
        """Recursively prints a subtree starting from the given node."""
        indent = "  " * indent_level
        prefix = "|- " if indent_level > 0 else ""
        initial_marker = "*" if node.is_initial else ""

        exec_time = node.execution_time_s
        time_str = f"{exec_time:.3f}" if exec_time is not None else "N/A"

        print(
            f"{indent}{prefix}{node.pid:<6} {node.comm:<20} {time_str:<25} {initial_marker}"
        )

        # Recursively print children, sorted by PID
        for child_node in sorted(node.children.values(), key=lambda x: x.pid):
            self._print_subtree(child_node, indent_level + 1)

    def render(self):
        """
        Renders the entire output, including the live tree and recent history.
        """
        self._rewrite_screen()
        print(f"{'PID':<6} {'COMMAND':<20} {'LIFETIME (s)':<25} {'NOTES'}")
        print("-" * 70)

        # Find and sort root nodes from the tracker's state
        root_nodes = sorted(
            [
                node
                for node in self.tracker.nodes.values()
                if node.ppid not in self.tracker.nodes
            ],
            key=lambda x: x.pid,
        )
        for node in root_nodes:
            self._print_subtree(node, 0)

        # Print recently exited nodes from the tracker's history
        print("\n--- Recently Exited (last 20) ---")
        for node in self.tracker.history:
            exec_time = node.execution_time_s
            time_str = f"ran for {exec_time:.3f}s" if exec_time is not None else ""
            print(f"- {node.pid:<6} {node.comm:<20} {time_str}")

        print("\n" + "=" * 70)
        print(f"Tracking {len(self.tracker.nodes)} live processes.\n")
