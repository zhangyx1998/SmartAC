<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>

<template>
  <div class="app">
    <header class="titlebar">
      <h1>{{ title }}</h1>
      <slot name="titlebar"></slot>
    </header>
    <div class="content">
      <slot></slot>
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
  user-select: none;
}

.content {
  margin-top: 60px;
  width: 100%;
}
</style>
