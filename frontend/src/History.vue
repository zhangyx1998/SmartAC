<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import Layout from "./components/Layout.vue";
import { Chart } from "vue-chartjs";
import { createToastInterface, POSITION } from "vue-toastification";
import "vue-toastification/dist/index.css";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  LineController,
  BarController,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  LineController,
  BarController,
  Title,
  Tooltip,
  Legend,
);

const toast = createToastInterface({
  position: POSITION.BOTTOM_RIGHT,
  timeout: 5000,
  closeOnClick: false,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: false,
  showCloseButtonOnHover: true,
  hideProgressBar: false,
  closeButton: "button",
  icon: true,
  rtl: false,
  transition: "Vue-Toastification__fade",
  maxToasts: 20,
  newestOnTop: true,
});

function formatDateTimeLocal(timestamp: string): string {
  const date = new Date(parseInt(timestamp));
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function getParam(key: string, parser: (val: string) => any): any {
  const params = new URLSearchParams(window.location.search);
  const value = params.get(key);
  return value ? parser(value) : undefined;
}

// Component state - initialize from URL parameters
const domain = ref<string>(getParam("domain", (v) => v) || "");
const startTime = ref<string>(getParam("start", formatDateTimeLocal));
const endTime = ref<string>(getParam("end", formatDateTimeLocal));
const step = ref<number | undefined>(getParam("step", (v) => parseInt(v)));
const loading = ref(false);
const environmentChartData = ref<any>(null);
const operationChartData = ref<any>(null);

// Auto-fetch if domain is present
onMounted(() => {
  if (domain.value) fetchHistory();
});

function updateUrlParams(): void {
  const params = new URLSearchParams();
  if (domain.value) params.append("domain", domain.value);
  if (startTime.value) {
    const timestamp = new Date(startTime.value).getTime() / 1000;
    params.append("start", timestamp.toString());
  }
  if (endTime.value) {
    const timestamp = new Date(endTime.value).getTime() / 1000;
    params.append("end", timestamp.toString());
  }
  if (step.value && step.value !== 60) {
    params.append("step", step.value.toString());
  }
  const queryString = params.toString();
  const newUrl = queryString ? `?${queryString}` : window.location.pathname;
  window.history.replaceState({}, "", newUrl);
}

function buildApiParams(): URLSearchParams {
  const params = new URLSearchParams();
  if (startTime.value) {
    const timestamp = new Date(startTime.value).getTime() / 1000;
    params.append("start", timestamp.toString());
  }
  if (endTime.value) {
    const timestamp = new Date(endTime.value).getTime() / 1000;
    params.append("end", timestamp.toString());
  }
  if (step.value) {
    params.append("step", step.value.toString());
  }
  return params;
}

async function fetchHistory(): Promise<void> {
  if (!domain.value.trim()) {
    toast.error("Domain is required");
    return;
  }
  updateUrlParams();
  toast.clear();
  loading.value = true;
  const loading_toast_id = toast.info("Loading...", { timeout: false, closeButton: false });
  try {
    const params = buildApiParams();
    const queryString = params.toString();
    const url = `/history/${encodeURIComponent(domain.value)}${queryString ? "?" + queryString : ""
      }`;
    const response = await fetch(url);
    toast.dismiss(loading_toast_id);
    if (!response.ok) {
      const errorText = await response.text();
      toast.error(`Error: ${errorText}`, { timeout: false });
      loading.value = false;
      return;
    }
    const data = await response.text();
    const lines = data
      .trim()
      .split("\n")
      .filter((line) => line);
    if (lines.length === 0) {
      toast.warning("No data available in selected time range", { timeout: false });
      loading.value = false;
      return;
    }
    // Parse data - format: timestamp, { key: value, ... }
    type DataPoint = { t: number; v: number };
    const dataMap = new Map<string, DataPoint[]>();
    for (const line of lines) {
      try {
        const [ts, records] = JSON.parse("[" + line + "]");
        if (typeof ts !== "number" || typeof records !== "object") {
          throw new Error("Invalid data format");
        }
        for (const [key, value] of Object.entries(records)) {
          if (!dataMap.has(key)) {
            dataMap.set(key, []);
          }
          dataMap.get(key)!.push({ t: ts, v: value as number });
        }
      } catch (e) {
        console.warn("Failed to parse line:", line);
      }
    }
    toast.success(`Loaded ${lines.length} data points`, { timeout: 2000 });
    // Prepare chart data
    prepareChartData(dataMap);
  } catch (error: any) {
    toast.error(`Error fetching data: ${error.message}`, { timeout: false });
  } finally {
    loading.value = false;
  }
}

function hexToRgba(hex: string, alpha: number = 0.1): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function prepareChartData(dataMap: Map<string, { t: number; v: number }[]>) {
  // Extract all unique timestamps and sort them
  const timestampSet = new Set<number>();
  for (const points of dataMap.values()) {
    points.forEach((p) => timestampSet.add(p.t));
  }
  const timestamps = Array.from(timestampSet).sort((a, b) => a - b);

  if (timestamps.length === 0) return;

  // Format labels for each data point
  const formattedLabels: (string | string[])[] = [];
  let lastDate = "";

  for (const ts of timestamps) {
    const date = new Date(ts);
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const month = date.toLocaleString("default", { month: "short" });
    const day = date.getDate();
    const currentDate = `${month} ${day}`;

    const timeStr = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    formattedLabels.push([timeStr, currentDate]);

    if (currentDate !== lastDate) {
      lastDate = currentDate;
    }
  }

  // Environment chart: temperature and humidity
  const environmentDatasets = [];
  const environmentConfig = [
    {
      key: "temperature",
      label: "Temperature (°C)",
      color: "#ffd93d",
      yAxisID: "y",
    },
    {
      key: "humidity",
      label: "Humidity (%)",
      color: "#4a9eff",
      yAxisID: "y1",
    },
  ];

  for (const config of environmentConfig) {
    const points = dataMap.get(config.key);
    if (!points || points.length === 0) continue;
    const valueMap = new Map(points.map((p) => [p.t, p.v]));
    const data = timestamps.map((ts) => valueMap.get(ts) ?? NaN);
    if (data.some((v) => !isNaN(v))) {
      environmentDatasets.push({
        type: "line",
        label: config.label,
        data,
        borderColor: config.color,
        backgroundColor: hexToRgba(config.color, 0.1),
        yAxisID: config.yAxisID,
        tension: 0.4,
        spanGaps: true,
      });
    }
  }

  environmentChartData.value = {
    labels: formattedLabels,
    datasets: environmentDatasets,
  };

  // Operation chart: population and fan RPM
  const operationDatasets = [];
  const operationConfig = [
    {
      key: "population",
      label: "Population",
      color: "#6bcf7f",
      yAxisID: "y",
    },
    {
      key: "fan_rpm",
      label: "Fan RPM",
      color: "#ff00ff",
      yAxisID: "y1",
    },
  ];

  for (const config of operationConfig) {
    const points = dataMap.get(config.key);
    if (!points || points.length === 0) continue;
    const valueMap = new Map(points.map((p) => [p.t, p.v]));
    const data = timestamps.map((ts) => valueMap.get(ts) ?? NaN);
    if (data.some((v) => !isNaN(v))) {
      operationDatasets.push({
        type: config.key === "population" ? "bar" : "line",
        label: config.label,
        data,
        borderColor: config.color,
        backgroundColor: hexToRgba(config.color, config.key === "population" ? 0.7 : 0.1),
        yAxisID: config.yAxisID,
        tension: 0.4,
        spanGaps: true,
      });
    }
  }

  operationChartData.value = {
    labels: formattedLabels,
    datasets: operationDatasets,
  };
}

const createChartOptions = (yAxisTitle: string, y1AxisTitle: string) => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: "index" as const,
    intersect: false,
  },
  plugins: {
    legend: {
      position: "top" as const,
      labels: {
        color: "#fff",
        usePointStyle: true,
        padding: 10,
      },
    },
    tooltip: {
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      titleColor: "#fff",
      bodyColor: "#fff",
      borderColor: "#333",
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      type: "category" as const,
      grid: {
        color: "#2a2a2a",
      },
      ticks: {
        color: "#aaa",
        maxRotation: 0,
        minRotation: 0,
        autoSkip: true,
        maxTicksLimit: 12,
        autoSkipPadding: 20,
      },
    },
    y: {
      type: "linear" as const,
      position: "left" as const,
      title: {
        display: true,
        text: yAxisTitle,
        color: yAxisTitle.includes("Temperature") ? "#ffd93d" : "#6bcf7f",
      },
      grid: {
        color: "#2a2a2a",
      },
      ticks: {
        color: yAxisTitle.includes("Temperature") ? "#ffd93d" : "#6bcf7f",
      },
    },
    y1: {
      type: "linear" as const,
      position: "right" as const,
      title: {
        display: true,
        text: y1AxisTitle,
        color: y1AxisTitle.includes("Humidity") ? "#4a9eff" : "#ff00ff",
      },
      grid: {
        drawOnChartArea: false,
      },
      ticks: {
        color: y1AxisTitle.includes("Humidity") ? "#4a9eff" : "#ff00ff",
      },
    },
  },
});

const environmentChartOptions = computed(() =>
  createChartOptions("Temperature (°C)", "Humidity (%)")
);

const operationChartOptions = computed(() =>
  createChartOptions("Population", "Fan RPM")
);

function backToDashboard(): void {
  window.location.href = "/";
}
</script>

<template>
  <Layout title="SmartAC History">
    <template #titlebar>
      <button class="dashboard-btn" @click="backToDashboard">Dashboard</button>
    </template>
    <div class="page-content">
      <div class="controls">
        <div class="control-group">
          <label for="domain">Domain *</label>
          <input id="domain" v-model="domain" type="text" placeholder="e.g., living-room" required
            @keypress.enter="fetchHistory" style="width: 8ch" />
        </div>
        <div class="control-group">
          <label for="start">Start Time</label>
          <input id="start" v-model="startTime" type="datetime-local" />
        </div>
        <div class="control-group">
          <label for="end">End Time</label>
          <input id="end" v-model="endTime" type="datetime-local" />
        </div>
        <div class="control-group">
          <label for="step">Time Step (s)</label>
          <input id="step" v-model.number="step" type="number" min="1" style="width: 8ch" />
        </div>
        <div class="control-group">
          <label>&nbsp;</label>
          <button :disabled="loading" @click="fetchHistory">Fetch Data</button>
        </div>
      </div>
      <div class="chart-container">
        <h2 class="chart-title">Environment Conditions</h2>
        <Chart v-if="environmentChartData" type="line" :data="environmentChartData"
          :options="environmentChartOptions" />
        <div v-else class="no-data">No data to display</div>
      </div>
      <div class="chart-container">
        <h2 class="chart-title">Operation Metrics</h2>
        <Chart v-if="operationChartData" type="line" :data="operationChartData" :options="operationChartOptions" />
        <div v-else class="no-data">No data to display</div>
      </div>
    </div>
  </Layout>
</template>

<style scoped>
.dashboard-btn {
  background: #42b883;
  color: #0a0a0a;
  border: none;
  padding: 0.5rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.dashboard-btn:hover {
  background: #35966d;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 20px;
  max-width: 1400px;
  width: 100%;
  margin-left: auto;
  margin-right: auto;
}

.controls {
  background: #1a1a1a;
  padding: 20px;
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  align-items: end;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

label {
  font-size: 0.9em;
  color: #aaa;
}

input,
select {
  padding: 8px 12px;
  border: 1px solid #333;
  border-radius: 4px;
  background: #0f0f0f;
  color: #fff;
  font-size: 1em;
}

input:focus,
select:focus {
  outline: none;
  border-color: #4a9eff;
}

button {
  padding: 8px 20px;
  background: #4a9eff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  transition: background 0.2s;
}

button:hover {
  background: #3a8eef;
}

button:disabled {
  background: #555;
  cursor: not-allowed;
}

.chart-container {
  background: #1a1a1a;
  padding: 20px;
  border-radius: 8px;
  position: relative;
  height: 400px;
  padding-bottom: 60px;
}

.chart-title {
  margin: 0 0 15px 0;
  font-size: 1.2em;
  color: #d3d3d3;
  font-weight: 600;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  font-size: 1.6em;
  font-weight: 600;
  user-select: none;
}
</style>
