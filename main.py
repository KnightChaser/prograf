# main.py
from proc_tracer.tracer import ProcTracer
from proc_tracer.callbacks import ProcessTreeTracker

def main():
    # Instantiate our tracer
    tracker = ProcessTreeTracker()
    tracer = ProcTracer(bpf_file_path="bpf/probes.c")

    # Attach the callbacks we want to use
    tracer.attach_callbacks(
        exec_cb=tracker.handle_exec,
        fork_cb=tracker.handle_fork,
        exit_cb=tracker.handle_exit,
    )

    # Run the tracer
    tracer.run()

if __name__ == "__main__":
    main()
