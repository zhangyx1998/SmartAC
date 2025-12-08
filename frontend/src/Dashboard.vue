<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import DomainCard from "./components/DomainCard.vue";

const status = ref({});
let intervalId = null;

const fetchStatus = async () => {
  try {
    const response = await fetch("/status");
    if (response.ok) {
      status.value = await response.json();
    }
  } catch (error) {
    console.error("Failed to fetch status:", error);
  }
};

onMounted(() => {
  fetchStatus();
  intervalId = setInterval(fetchStatus, 1000);
});

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId);
  }
});
</script>

<template>
  <div class="app">
    <header class="titlebar">
      <h1>SmartAC Dashboard</h1>
      <button class="history-btn">View History</button>
    </header>
    <div class="content">
      <div class="domains">
        <DomainCard
          v-for="(domainStatus, name) in status"
          :key="name"
          :name="name"
          :status="domainStatus"
        />
        <div v-if="Object.keys(status).length === 0" class="no-data">
          No Data Available
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  background: #0a0a0a;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
}

.titlebar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: #1a1a1a;
  border-bottom: 2px solid #42b883;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.titlebar h1 {
  margin: 0;
  font-size: 1.5rem;
  color: #d3d3d3;
}

.history-btn {
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

.history-btn:hover {
  background: #35966d;
}

.history-btn:active {
}

.content {
  margin-top: 60px;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.domains {
  display: flex;
  gap: 2rem;
  max-width: 900px;
  flex-direction: column;
}

.no-data {
  text-align: center;
  margin-top: calc(50vh - 6rem);
  padding: 0;
  font-size: 3rem;
  color: #444;
  user-select: none;
  font-weight: 600;
}
</style>
