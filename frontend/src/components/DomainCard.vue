<template>
  <div class="domain-card">
    <div class="domain-title">
      <span style="font-weight: normal">Domain</span> {{ name.toUpperCase() }}
    </div>
    <div class="categories">
      <div class="category" title="Vision AI">
        <Property icon="fa-users" name="Population">
          <Value :value="status.population" :width="2" />
        </Property>
      </div>

      <div class="category" title="Sensor Reading">
        <Property icon="fa-thermometer-half" name="Temperature">
          <Value
            :value="status.temperature"
            unit="°C"
            :decimals="1"
            :width="5"
          />
        </Property>
        <Property icon="fa-droplet" name="Humidity">
          <Value :value="status.humidity" unit="%" :decimals="1" :width="5" />
        </Property>
      </div>

      <div class="category" title="AC Control">
        <Property icon="fa-bolt" name="Fan Power">
          <Value
            :value="status.fan_power"
            unit="%"
            :multiplier="100"
            :decimals="0"
            :width="4"
          />
        </Property>
        <Property icon="fa-fan" name="Fan RPM">
          <Value :value="status.fan_rpm" :decimals="0" :width="4" />
        </Property>
      </div>
    </div>
  </div>
</template>

<script setup>
import Property from "./Property.vue";
import Value from "./Value.vue";

defineProps({
  name: {
    type: String,
    required: true,
  },
  status: {
    type: Object,
    required: true,
  },
});
</script>

<style scoped>
.domain-card {
  --theme: #aaaaaa;
  background: #1a1a1a;
  outline: 1px solid var(--theme);
  border-radius: 12px;
}

.domain-card:hover,
.domain-card:focus-within,
.domain-card:active {
  --theme: #42b883;
}

.domain-title {
  padding: 1rem;
  font-size: 1.2rem;
  line-height: 1;
  color: var(--theme);
  text-align: left;
  border-bottom: 1px solid #333;
  font-weight: 700;
}

.categories {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  justify-content: center;
  padding: 1rem;
}

.category {
  position: relative;
  padding: 0 1rem;
  /* Reserved for title */
  padding-top: 2rem;
  display: flex;
  flex-direction: row;
  align-items: stretch;
  justify-content: center;
  gap: 1rem;
}

.category:not(:last-child) {
  border-right: 1px solid #333;
}

.category:last-child {
  margin-bottom: 0;
}

.category[title]:before {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  position: absolute;
  top: 0;
  left: 50%;
  width: max-content;
  transform: translateX(-50%);
  content: attr(title);
  white-space: nowrap;
}
</style>
