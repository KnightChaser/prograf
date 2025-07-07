// server/index.js
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const net = require("net");
const fs = require("fs");
const path = require("path");

const app = express();
const server = http.createServer(app);
const io = new Server(server);

const WEB_PORT = 3000;
const TCP_PORT = 9090;
const LOGS_DIR = path.join(__dirname, "logs");

// In-memory state
let logFiles = [];

// Create logs directory if it doesn't exist
if (!fs.existsSync(LOGS_DIR)) {
  fs.mkdirSync(LOGS_DIR);
} else {
  // Clean up old logs on start
  fs.readdirSync(LOGS_DIR).forEach((file) => {
    fs.unlinkSync(path.join(LOGS_DIR, file));
  })
}

// Cleanup on exit
process.on("SIGINT", () => {
  console.log("\nCaught interrupt signal. Deleting logs...");
  if (fs.existsSync(LOGS_DIR)) {
    fs.readdirSync(LOGS_DIR).forEach((file) => {
      fs.unlinkSync(path.join(LOGS_DIR, file));
    });
  }
  process.exit();
})

// Open websocket server for browsers
app.get("/", (req, res) => {
  res.sendFile(__dirname + "/index.html");
});

// API endpoint to get a specific log by index
app.get("/log/:index", (req, res) => {
  const index = parseInt(req.params.index, 10);
  if (isNaN(index) || index < 0 || index >= logFiles.length) {
    return res.status(404).json({
      error: "Log not found"
    })
  }
  const filePath = path.join(LOGS_DIR, logFiles[index]);
  res.sendFile(filePath, (err) => {
    if (err) {
      console.error("Error sending file:", err);
      res.status(500).json({ error: "Failed to send log file" });
    }
  });
});

io.on("connection", (socket) => {
  console.log("A client connected");
  socket.emit("update_count", {
    count: logFiles.length
  });
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
        let boundary = buffer.indexOf('\n');
        while (boundary !== -1) {
            const jsonLine = buffer.substring(0, boundary);
            buffer = buffer.substring(boundary + 1);

            try {
                // Save the file instead of just logging
                const timestamp = Date.now();
                const fileName = `${timestamp}.json`;
                const filePath = path.join(LOGS_DIR, fileName);

                // We can parse it to make sure it's valid JSON before saving
                const processTree = JSON.parse(jsonLine);
                fs.writeFileSync(filePath, JSON.stringify(processTree, null, 2));

                // Update our in-memory state
                logFiles.push(fileName);
                logFiles.sort(); // Keep it sorted by time

                console.log(`Saved log: ${fileName}`);

                // Notify all web clients that a new log has arrived
                io.emit('update_count', { 
                  total: logFiles.length 
                });

            } catch (e) {
                console.error('Error processing data from tracer:', e);
            }
            boundary = buffer.indexOf('\n');
        }
    });

    socket.on('end', () => console.log('Python tracer disconnected.'));
    socket.on('error', (err) => console.error('TCP socket error:', err.message));
});

tcpServer.listen(TCP_PORT, '127.0.0.1', () => {
    console.log(`TCP server for tracer listening on localhost:${TCP_PORT}`);
});
