// server/src/api-router.js
const express = require("express");
const path = require("path");

// createApiRouter handles the API routes for serving log files
function createApiRouter(logFiles, LOGS_DIR) {
  const router = express.Router();

  // Endpoint to get the total number of log files
  router.get("/log/:index", (req, res) => {
    const index = parseInt(req.params.index, 10);
    if (isNaN(index) || index < 0 || index >= logFiles.length) {
      return res.status(404).json({
        error: "Log not found",
      });
    }
    const filePath = path.join(LOGS_DIR, logFiles[index]);
    res.sendFile(filePath);
  });

  return router;
}

module.exports = { createApiRouter };
