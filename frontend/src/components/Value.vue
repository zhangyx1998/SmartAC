<template>
  <div
    class="value"
    :class="{ unavailable: !isValid(value) }"
    :style="{ minWidth: width + 'ch' }"
  >
    {{ displayValue }}
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  value: {
    type: Number,
    required: true,
  },
  unit: {
    type: String,
    default: "",
  },
  decimals: {
    type: Number,
    default: undefined,
  },
  multiplier: {
    type: Number,
    default: 1,
  },
  width: {
    type: Number,
    default: 4,
  },
});

const displayValue = computed(() => {
  if (!isValid(props.value)) {
    return "---";
  }
  let formattedValue = props.value * props.multiplier;
  if (props.decimals !== undefined) {
    formattedValue = parseFloat(formattedValue.toFixed(props.decimals));
  }
  return `${formattedValue}${props.unit}`;
});
</script>

<script>
export function isValid(value) {
  return typeof value === "number" && !isNaN(value);
}
</script>

<style scoped>
.value {
  font-size: 1.6rem;
  font-weight: 700;
  color: #42b883;
  text-align: right;
}

.value.unavailable {
  color: #666;
}
</style>
