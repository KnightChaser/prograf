// server/src/cleanup.js

const fs = require("fs");
const path = require("path");

// setupCleanup handles the cleanup of log files and sets up a signal handler for graceful shutdown
function setupCleanup(LOGS_DIR) {
  if (!fs.existsSync(LOGS_DIR)) {
    fs.mkdirSync(LOGS_DIR);
  } else {
    fs.readdirSync(LOGS_DIR).forEach((file) =>
      fs.unlinkSync(path.join(LOGS_DIR, file))
    );
  }

  // Handle Ctrl+C (SIGINT)
  process.on("SIGINT", () => {
    console.log("\nCaught interrupt signal. Deleting logs...");
    if (fs.existsSync(LOGS_DIR)) {
      fs.rmSync(LOGS_DIR, { recursive: true, force: true });
      console.log("Logs directory deleted.");
    }
    process.exit();
  });
}

module.exports = { setupCleanup };
