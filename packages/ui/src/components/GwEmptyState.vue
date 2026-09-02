<script setup lang="ts">
/** Marks an empty state as waiting for content when loading is active. */
defineProps<{ loading?: boolean }>();
</script>

<template>
  <div class="gw-empty" :class="{ 'gw-empty--loading': loading }">
    <span class="gw-mark gw-mark--lg gw-empty__marker" aria-hidden="true" />
    <p class="gw-empty__text"><slot /></p>
    <div v-if="$slots.actions" class="gw-empty__actions"><slot name="actions" /></div>
  </div>
</template>
