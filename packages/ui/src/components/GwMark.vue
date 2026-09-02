<script setup lang="ts">
/** Chooses the visual scale and purpose of the Gravewright mark. */
defineProps<{ variant?: "brand" | "lg" | "xl" | "bullet" }>();
</script>

<template>
  <span
    class="gw-mark"
    :class="variant && variant !== 'brand' ? `gw-mark--${variant}` : ''"
    aria-hidden="true"
  />
</template>
