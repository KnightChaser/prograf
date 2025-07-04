# proc_tracer/tracer.py

from bcc import BPF
import time

class ProcTracer:
    def __init__(self, bpf_file_path):
        """
        Initializes the tracer by compiling the BPF C code.
        """
        bpf_text = ""
        with open(bpf_file_path, "r") as f:
            bpf_text = f.read()

        # This will compile the C code and automatically attach the TRACEPOINT_PROBEs.
        self.bpf = BPF(text=bpf_text)

    def attach_callbacks(self, exec_cb, fork_cb, exit_cb):
        """
        Attaches user-space callbacks to the BPF perf buffers.
        """
        self.bpf["exec_events"].open_perf_buffer(exec_cb)
        self.bpf["fork_events"].open_perf_buffer(fork_cb)
        self.bpf["exit_events"].open_perf_buffer(exit_cb)

    def run(self, tracker, refresh_rate_hz=5):
        """
        Starts the tracer and polls for events indefinitely.
        """
        print("Tracing process events... Ctrl+C to quit.")
        last_refresh_time = 0
        refresh_interval_sec = 1.0 / refresh_rate_hz

        while True:
            try:
                self.bpf.perf_buffer_poll(timeout=200)

                # Check if it's time to refresh the screen
                now = time.time()
                if now - last_refresh_time > refresh_interval_sec:
                    tracker.print_tree()
                    last_refresh_time = now

            except KeyboardInterrupt:
                print("\nExiting...")
                tracker.print_tree()
                break
