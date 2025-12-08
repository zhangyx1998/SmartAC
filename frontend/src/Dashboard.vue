<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import Layout from "./components/Layout.vue";
import DomainCard from "./components/DomainCard.vue";

const status = ref({});
let intervalId: NodeJS.Timeout | null = null;

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

<script lang="ts">
export function viewHistory(domain?: string) {
  const url = domain
    ? `/history.html?domain=${encodeURIComponent(domain)}`
    : "/history.html";
  window.location.href = url;
}
</script>

<template>
  <Layout title="SmartAC Dashboard">
    <template #titlebar>
      <button class="history-btn" @click="() => viewHistory()">
        View History
      </button>
    </template>

    <div class="domains">
      <DomainCard v-for="(domainStatus, name) in status" :key="name" :name="name" :status="domainStatus" />
      <div v-if="Object.keys(status).length === 0" class="no-data">
        No Data Available
      </div>
    </div>
  </Layout>
</template>

<style scoped>
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

.domains {
  display: flex;
  gap: 2rem;
  max-width: 900px;
  flex-direction: column;
  margin: 0 auto;
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
