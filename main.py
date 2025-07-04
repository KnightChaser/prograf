# main.py
import os
from proc_tracer.tracer import ProcTracer
from proc_tracer.callbacks import ProcessTreeTracker
from proc_tracer.renderer import ConsoleRenderer


def main():
    # Instantiate our tracer
    tracker = ProcessTreeTracker()
    renderer = ConsoleRenderer(tracker=tracker)
    tracer = ProcTracer(bpf_file_path="bpf/probes.c")

    # Attach the callbacks we want to use
    tracer.attach_callbacks(
        exec_cb=tracker.handle_exec,
        fork_cb=tracker.handle_fork,
        exit_cb=tracker.handle_exit,
    )

    # Run the tracer
    tracer.run(renderer=renderer, refresh_rate_hz=5)


if __name__ == "__main__":
    # This should be run with root privileges because
    # it needs to attach to kernel probes.
    if os.geteuid() != 0:
        print("This program must be run as root! >_<")
        exit(1)

    main()
