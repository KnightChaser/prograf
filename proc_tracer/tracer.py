# proc_tracer/tracer.py

from bcc import BPF

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

    def run(self):
        """
        Starts the tracer and polls for events indefinitely.
        """
        print("Tracing process events... Ctrl+C to quit.")
        while True:
            try:
                self.bpf.perf_buffer_poll()
            except KeyboardInterrupt:
                print("\nDetaching...")
                exit()
