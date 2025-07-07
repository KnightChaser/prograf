// server/src/tcp-server.js

const net = require("net");
const fs = require("fs");
const path = require("path");

/**
 * Helper function to recursively traverse a process tree object
 * and remove redundant fields.
 * @param {object} node - The process node object to clean.
 */
function cleanupTree(node) {
  if (!node) return;

  // Delete the redundant fields from the current node
  delete node.is_active;
  delete node.is_initial;
  delete node.active_children_count;

  // Recurse for all children
  if (node.children && Array.isArray(node.children)) {
    node.children.forEach((child) => cleanupTree(child));
  }
}

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

          let processTree = JSON.parse(jsonLine);
          cleanupTree(processTree); // prune unnecessary fields
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
