// server/index.js
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const net = require("net");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

const WEB_PORT = 3000;
const TCP_PORT = 9090;

// Open websocket server for browsers
app.get("/", (req, res) => {
  res.sendFile(__dirname + "/index.html");
});

io.on("connection", (socket) => {
  console.log("A client connected");
  socket.on("disconnect", () => {
    console.log("A client disconnected");
  });
});

server.listen(WEB_PORT, () => {
  console.log(`WebSocket server is running on port ${WEB_PORT}`);
});

// TCP server for the Python tracer (Prograf)
const tcpServer = net.createServer((socket) => {
    console.log('Python tracer connected.');

    let buffer = '';
    socket.on('data', (data) => {
        buffer += data.toString();

        // Process data line by line (since TCP is a stream)
        let boundary = buffer.indexOf('\n');
        while (boundary !== -1) {
            const jsonLine = buffer.substring(0, boundary);
            buffer = buffer.substring(boundary + 1);

            try {
                const processTree = JSON.parse(jsonLine);
                console.log('Received process tree for PID:', processTree.pid);

                // Broadcast the received data to all connected web clients
                io.emit('new_tree', processTree);

            } catch (e) {
                console.error('Error parsing JSON from tracer:', e);
            }
            boundary = buffer.indexOf('\n');
        }
    });

    socket.on('end', () => {
        console.log('Python tracer disconnected.');
    });

    socket.on('error', (err) => {
        console.error('TCP socket error:', err.message);
    });
});

tcpServer.listen(TCP_PORT, '127.0.0.1', () => {
    console.log(`TCP server for tracer listening on localhost:${TCP_PORT}`);
});
