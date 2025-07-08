# prograf
![C](https://img.shields.io/badge/c-%2300599C.svg?style=for-the-badge&logo=c&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![NodeJS](https://img.shields.io/badge/node.js-6DA55F?style=for-the-badge&logo=node.js&logoColor=white)
![Express.js](https://img.shields.io/badge/express.js-%23404d59.svg?style=for-the-badge&logo=express&logoColor=%2361DAFB)
![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)
> Track and visualize Linux process lifecycle in real-time, powered by BCC/eBPF

This project provides a powerful, real-time visualization of process lifecycles on a Linux system.
It uses BPF (via BCC) to efficiently capture low-level kernel events (`fork`, `execve`, `exit`) and 
sends this data to a web-based user interface for interactive analysis.

![image](https://github.com/user-attachments/assets/fcfba793-e26c-4394-bb2d-582dbb79193c)

## Features

- **Real-Time Monitoring:** Captures process creation and termination events as they happen via BPF.
- **Hierarchical Gantt Chart Visualization:** Displays terminated process trees in a clear, nested Gantt chart using D3.js, making it easy to understand parent-child relationships and execution overlap.
- **Histogram Visualization**: Displays the execution times of terminated processes in a single chart, allowing for a glance at how long they were executed on the system.
- **Interactive UI:**
    - Hover over any process for a detailed tooltip with PID, PPID, command, and precise execution timing.
    - Navigate through the history of all captured termination trees. (Note: When you restart the web server, the history is reset.)
    - Automatically truncates and provides an "Expand" option for giant process trees to maintain UI performance.
- **Statistical Analysis:** Includes a histogram showing the distribution of process execution times for each captured tree.

The project is composed of two main components that run concurrently:

1.  **The Tracer (Python)**: `proc_tracer/`
    - Uses the **BPF Compiler Collection (BCC)** to attach eBPF programs to kernel tracepoints for `fork`, `execve`, `execveat`, and `sched_process_exit`.
    - The BPF programs collect process metadata (PID, PPID, command, timestamps) and send it to user-space via perf buffers.
    - A Python script (`callbacks.py`) maintains an in-memory state of the live process tree.
    - When a process tree fully terminates, the script serializes it to JSON and sends the result over a local TCP socket to the web server.

2.  **The Web Server (Node.js)**: `server/`
    - A Node.js server built with **express.js** and **socket.io**.
    - It listens for TCP connections from the Python tracer to receive terminated tree data.
    - Each received tree is saved as a temporary JSON file in the `server/logs/` directory. (As mentioned earlier, when the server restarts, the logs are purged.)
    - It serves as a static front end to the user.
    - When a new tree is received, it notifies all connected web clients via WebSocket.
    - The frontend fetches the log data via an API endpoint and uses **d3.js** to render the complex, interactive visualizations.
    - All temporary logs are automatically cleaned up when the server is shut down.
  
## Setup
If you run this project locally, you must successfully install [bcc](https://github.com/iovisor/bcc) on your computer. The tracer (Python sensor) will utilize that.
To facilitate the web server, install [Node.js](https://nodejs.org/en) and [npm](https://www.npmjs.com/). After that, hit `npm install` to install all the required Node.js dependencies.
If you installed all required packages, run the services concurrently:
1. At `/server`, run `npm run watch:css` (_Web service_)
2. At `/server`, run `npm start` (_Web service_)
3. At `/`, run `sudo python3 main.py` (_BPF tracer_ / Using BPF feature requires kernel access.)

## Project structure
```
.
├── bpf/                  # BPF C code for the kernel probes
│   └── probes.c
├── proc_tracer/          # Python application logic for the tracer
│   ├── callbacks.py      # Manages the live process tree state
│   ├── ipc.py            # Handles TCP communication to the Node.js server
│   └── ...
├── server/               # Node.js web server and frontend
│   ├── public/           # Static assets served to the browser (HTML, JS, CSS)
│   ├── src/              # Modularized Node.js backend logic
│   ├── styles/           # Source CSS for Tailwind
│   ├── index.js          # Main entry point for the Node.js server
│   └── package.json
└── main.py               # Main entry point to start the Python tracer
```
