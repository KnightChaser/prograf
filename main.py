# main.py
import os
import time
from proc_tracer.tracer import ProcTracer
from proc_tracer.callbacks import ProcessTreeTracker
from proc_tracer.ipc import TCPClient


def main():
    # Setup the IPC client
    ipc_client = TCPClient()
    if not ipc_client.connect():
        time.sleep(2)
        if not ipc_client.connect():
            # retry
            print("Failed to connect to the IPC server. Exiting.")

    # Instantiate our tracer
    tracker = ProcessTreeTracker(ipc_client=ipc_client)
    tracer = ProcTracer(bpf_file_path="bpf/probes.c")

    # Attach the callbacks we want to use
    tracer.attach_callbacks(
        exec_cb=tracker.handle_exec,
        fork_cb=tracker.handle_fork,
        exit_cb=tracker.handle_exit,
    )

    # Run the tracer
    tracer.run(refresh_rate_hz=5)


if __name__ == "__main__":
    # This should be run with root privileges because
    # it needs to attach to kernel probes.
    if os.geteuid() != 0:
        print("This program must be run as root! >_<")
        exit(1)

    main()
