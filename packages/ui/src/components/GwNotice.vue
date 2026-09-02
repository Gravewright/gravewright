<script setup lang="ts">
/** Maps a semantic notice tone to its visual and accessible presentation. */
defineProps<{ tone?: "info" | "danger" | "ok" | "warning" }>();
</script>

<template>
  <div
    class="gw-notice"
    :class="tone && tone !== 'info' ? `gw-notice--${tone}` : ''"
    :role="tone === 'danger' ? 'alert' : 'status'"
  >
    <slot />
  </div>
</template>
