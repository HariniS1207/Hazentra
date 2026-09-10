const socket = io();
const statusEl = document.getElementById("connection-status");
const bannerEl = document.getElementById("alert-banner");
const alertLogEl = document.getElementById("alert-log");

const valEls = {
  accel: document.getElementById("val-accel"),
  temp: document.getElementById("val-temp"),
  dist: document.getElementById("val-dist"),
  gas: document.getElementById("val-gas"),
  soil: document.getElementById("val-soil"),
};
const cardEls = {
  accel: document.getElementById("card-accel"),
  temp: document.getElementById("card-temp"),
  dist: document.getElementById("card-dist"),
  gas: document.getElementById("card-gas"),
  soil: document.getElementById("card-soil"),
};

const MAX_POINTS = 60;
const trendCtx = document.getElementById("trendChart").getContext("2d");
const trendChart = new Chart(trendCtx, {
  type: "line",
  data: {
    labels: [],
    datasets: [
      { label: "Accel (m/s²)", data: [], borderColor: "#58a6ff", tension: 0.3, pointRadius: 0 },
      { label: "Temp (°C)", data: [], borderColor: "#f85149", tension: 0.3, pointRadius: 0 },
      { label: "Soil (%)", data: [], borderColor: "#3fb950", tension: 0.3, pointRadius: 0 },
    ],
  },
  options: {
    responsive: true,
    animation: false,
    scales: {
      x: { ticks: { color: "#8b949e" } },
      y: { ticks: { color: "#8b949e" } },
    },
    plugins: { legend: { labels: { color: "#e6edf3" } } },
  },
});

socket.on("connect", () => {
  statusEl.textContent = "Live";
  statusEl.className = "status online";
});

socket.on("disconnect", () => {
  statusEl.textContent = "Offline";
  statusEl.className = "status offline";
});

// Map disaster labels back to their sensor card for highlighting
const LABEL_TO_CARD = {
  "EARTHQUAKE": "accel",
  "FIRE DISASTER": "temp",
  "FLOOD ALERT": "dist",
  "AIR QUALITY ALERT": "gas",
  "LANDSLIDE RISK": "soil",
};

socket.on("telemetry", (payload) => {
  const { reading, status } = payload;

  valEls.accel.textContent = reading.accel.toFixed(1);
  valEls.temp.textContent = reading.temp.toFixed(1);
  valEls.dist.textContent = reading.dist.toFixed(1);
  valEls.gas.textContent = reading.gas;
  valEls.soil.textContent = reading.soil;

  Object.values(cardEls).forEach(c => c.classList.remove("triggered"));
  status.active.forEach(label => {
    const key = LABEL_TO_CARD[label];
    if (key) cardEls[key].classList.add("triggered");
  });

  if (status.active.length > 0) {
    bannerEl.textContent = "⚠ ACTIVE ALERT: " + status.active.join(" | ");
    bannerEl.classList.remove("hidden");
  } else {
    bannerEl.classList.add("hidden");
  }

  status.newly_triggered.forEach(label => addLogEntry(label, reading.timestamp));

  const t = new Date(reading.timestamp * 1000).toLocaleTimeString();
  trendChart.data.labels.push(t);
  trendChart.data.datasets[0].data.push(reading.accel);
  trendChart.data.datasets[1].data.push(reading.temp);
  trendChart.data.datasets[2].data.push(reading.soil);
  if (trendChart.data.labels.length > MAX_POINTS) {
    trendChart.data.labels.shift();
    trendChart.data.datasets.forEach(d => d.data.shift());
  }
  trendChart.update("none");
});

function addLogEntry(label, timestamp) {
  const li = document.createElement("li");
  const time = new Date(timestamp * 1000).toLocaleString();
  li.innerHTML = `<span class="badge">${label}</span><span>${time}</span>`;
  alertLogEl.prepend(li);
}

// Load persisted alert history on page load
fetch("/api/alerts")
  .then(r => r.json())
  .then(alerts => {
    alerts.forEach(a => addLogEntry(a.disaster_type, a.timestamp));
  });
