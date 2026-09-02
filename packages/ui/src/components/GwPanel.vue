<script setup lang="ts">
/** Provides the heading content for a standard Gravewright panel. */
defineProps<{ title: string; description?: string }>();
</script>

<template>
  <article class="gw-panel">
    <div class="gw-panel__inner">
      <header class="gw-panel__head">
        <h1 class="gw-panel__title">{{ title }}</h1>
        <p v-if="description" class="gw-panel__description">{{ description }}</p>
        <slot name="head" />
      </header>

      <slot name="alerts" />

      <div v-if="$slots.actions" class="gw-panel__actions">
        <slot name="actions" />
      </div>

      <slot />
    </div>
  </article>
</template>
