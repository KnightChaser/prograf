// server/src/tcp-server.js

const net = require("net");
const fs = require("fs");
const path = require("path");

// createTcpServer handles incoming TCP connections from the Python tracer
function createTcpServer(io, logFiles, LOGS_DIR) {
  const tcpServer = net.createServer((socket) => {
    console.log("Python tracer connected.");

    let buffer = "";
    socket.on("data", (data) => {
      buffer += data.toString();
      let boundary = buffer.indexOf("\n");
      while (boundary !== -1) {
        const jsonLine = buffer.substring(0, boundary);
        buffer = buffer.substring(boundary + 1);

        try {
          const timestamp = Date.now();
          const fileName = `${timestamp}.json`;
          const filePath = path.join(LOGS_DIR, fileName);

          const processTree = JSON.parse(jsonLine);
          fs.writeFileSync(filePath, JSON.stringify(processTree, null, 2));

          logFiles.push(fileName);
          logFiles.sort(); // Sort log files by name(timestamp, chronological order)

          console.log(`Saved log: ${fileName}`);

          // Notify web clients of the new total count
          io.emit("update_count", {
            total: logFiles.length,
          });
        } catch (e) {
          console.error("Error processing data from tracer:", e);
        }
        boundary = buffer.indexOf("\n");
      }
    });

    socket.on("end", () => console.log("Python tracer disconnected."));
    socket.on("error", (err) =>
      console.error("TCP socket error:", err.message)
    );
  });

  return tcpServer;
}

module.exports = { createTcpServer };
