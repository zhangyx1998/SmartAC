<template>
  <div class="property">
    <div class="property-header">
      <i :class="['icon', 'fas', icon]"></i>
      <div class="property-details">
        <slot></slot>
      </div>
    </div>
    <div class="property-name">{{ name }}</div>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    required: true,
  },
  name: {
    type: String,
    required: true,
  },
});
</script>

<style scoped>
.property {
  background: #0f0f0f;
  border-radius: 8px;
  overflow: hidden;
  outline: 2px solid black;
}

.property-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
}

.icon {
  font-size: 1.6rem;
  width: 2ch;
  text-align: center;
  color: #42b883;
  flex-shrink: 0;
}

.property-name {
  width: 100%;
  text-align: center;
  font-size: 0.9rem;
  font-weight: 600;
  color: #fff8;
  background-color: #fff1;
  padding: 0.2rem 0;
}

.property-details {
  text-align: right;
}
</style>
