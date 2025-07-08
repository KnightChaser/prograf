// server/public/js/app.js
const socket = io();

// UI Elements
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const logCounterEl = document.getElementById("log-counter");
const jsonOutputEl = document.getElementById("json-output");
const ganttChartSelector = "#gantt-chart";
const histogramSelector = "#histogram-chart";

// State
let currentIndex = -1;
let totalLogs = 0;

// --- Main Fetch Logic ---
async function fetchLog(index) {
  if (index < 0 || index >= totalLogs) return;
  try {
    const response = await fetch(`/api/log/${index}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const data = await response.json();

    // Update JSON viewer
    jsonOutputEl.textContent = JSON.stringify(data, null, 2);

    // Use the imported module to render the charts
    createGanttChart(data, ganttChartSelector);
    createHistogram(data, histogramSelector);

    currentIndex = index;
    updateUI();
  } catch (error) {
    console.error("Could not fetch log:", error);
    jsonOutputEl.textContent = `Error loading log ${index}.`;
    // Clear the chart on error by passing empty data
    createGanttChart({ children: [] }, chartSvgSelector);
  }
}

// --- UI State and Event Handlers (Unchanged) ---
function updateUI() {
  if (totalLogs === 0) {
    logCounterEl.textContent = "No logs yet";
  } else {
    logCounterEl.textContent = `${currentIndex + 1} / ${totalLogs}`;
  }
  prevBtn.disabled = currentIndex <= 0;
  nextBtn.disabled = currentIndex >= totalLogs - 1;
}

prevBtn.addEventListener("click", () => {
  if (currentIndex > 0) fetchLog(currentIndex - 1);
});

nextBtn.addEventListener("click", () => {
  if (currentIndex < totalLogs - 1) fetchLog(currentIndex + 1);
});

socket.on("update_count", (data) => {
  const shouldFetchLatest = totalLogs > 0 && currentIndex === totalLogs - 1;
  totalLogs = data.total;
  if (totalLogs > 0 && (currentIndex === -1 || shouldFetchLatest)) {
    fetchLog(totalLogs - 1);
  } else {
    updateUI();
  }
});

updateUI();
