<script setup lang="ts">
/** Selects the card's elevation treatment. */
defineProps<{ raised?: boolean; flat?: boolean }>();
</script>

<template>
  <section class="gw-card" :class="{ 'gw-card--raised': raised, 'gw-card--flat': flat }">
    <header v-if="$slots.head" class="gw-card__head"><slot name="head" /></header>
    <div class="gw-card__body"><slot /></div>
    <footer v-if="$slots.actions" class="gw-card__actions gw-card__actions--spread"><slot name="actions" /></footer>
  </section>
</template>
