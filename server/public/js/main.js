// server/public/js/main.js
const socket = io();

// UI Elements
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const logCounterEl = document.getElementById("log-counter");
const jsonOutputEl = document.getElementById("json-output");

// State
let currentIndex = -1;
let totalLogs = 0;

// --- Functions ---
async function fetchLog(index) {
  if (index < 0 || index >= totalLogs) {
    return;
  }
  try {
    const response = await fetch(`/api/log/${index}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    jsonOutputEl.textContent = JSON.stringify(data, null, 2);
    currentIndex = index;
    updateUI();
  } catch (error) {
    console.error("Could not fetch log:", error);
    jsonOutputEl.textContent = `Error loading log ${index}.`;
  }
}

function updateUI() {
  if (totalLogs === 0) {
    logCounterEl.textContent = "No logs yet";
  } else {
    logCounterEl.textContent = `${currentIndex + 1} / ${totalLogs}`;
  }
  prevBtn.disabled = currentIndex <= 0;
  nextBtn.disabled = currentIndex >= totalLogs - 1;
}

// --- Event Listeners ---
prevBtn.addEventListener("click", () => {
  if (currentIndex > 0) {
    fetchLog(currentIndex - 1);
  }
});

nextBtn.addEventListener("click", () => {
  if (currentIndex < totalLogs - 1) {
    fetchLog(currentIndex + 1);
  }
});

// --- Socket.IO Handlers ---
socket.on("update_count", (data) => {
  const shouldFetchLatest = totalLogs > 0 && currentIndex === totalLogs - 1;

  totalLogs = data.total;

  if (totalLogs > 0 && (currentIndex === -1 || shouldFetchLatest)) {
    fetchLog(totalLogs - 1);
  } else {
    updateUI();
  }
});

// Initial state
updateUI();
