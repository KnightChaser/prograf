// server/index.js
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const path = require("path");

const { setupCleanup } = require("./src/cleanup");
const { createApiRouter } = require("./src/api-router");
const { createTcpServer } = require("./src/tcp-server");

// --- Core App Instances and State ---
const app = express();
const server = http.createServer(app);
const io = new Server(server);

const WEB_PORT = 3000;
const TCP_PORT = 9090;
const LOGS_DIR = path.join(__dirname, "logs");

let logFiles = []; // Shared in-memory state for log filenames

// Set up cleanup logic
setupCleanup(LOGS_DIR);
const apiRouter = createApiRouter(logFiles, LOGS_DIR);
const tcpServer = createTcpServer(io, logFiles, LOGS_DIR);

// --- Express Middleware and Routes ---
app.use(express.static(path.join(__dirname, "public"))); // When user accesses "/"
app.use("/api", apiRouter);

// --- Socket.IO Connection Handling ---
io.on("connection", (socket) => {
  console.log("A web client connected");
  // Immediately inform the new client about the current number of logs
  socket.emit("update_count", { total: logFiles.length });
  socket.on("disconnect", () => {
    console.log("Web client disconnected");
  });
});

// --- Start the Servers ---
server.listen(WEB_PORT, () => {
  console.log(`Web server listening on http://localhost:${WEB_PORT}`);
});

tcpServer.listen(TCP_PORT, "127.0.0.1", () => {
  console.log(`TCP server for tracer listening on localhost:${TCP_PORT}`);
});
