# main.py
from proc_tracer.tracer import ProcTracer
from proc_tracer.callbacks import print_exec, print_fork, print_exit

def main():
    # Instantiate our tracer
    tracer = ProcTracer(bpf_file_path="bpf/probes.c")

    # Attach the callbacks we want to use
    tracer.attach_callbacks(
        exec_cb=print_exec,
        fork_cb=print_fork,
        exit_cb=print_exit
    )

    # Run the tracer
    tracer.run()

if __name__ == "__main__":
    main()
