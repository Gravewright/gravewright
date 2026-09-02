<script setup lang="ts">
/** Configures the badge's semantic tone and optional compact pill shape. */
defineProps<{ tone?: "neutral" | "accent" | "ok" | "warning" | "danger" | "quiet"; pill?: boolean }>();
</script>

<template>
  <span class="gw-badge" :class="[tone && tone !== 'neutral' ? `gw-badge--${tone}` : '', { 'gw-badge--pill': pill }]">
    <slot />
  </span>
</template>
