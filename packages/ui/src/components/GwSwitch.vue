<script setup lang="ts">
/** Supplies optional explanatory content for a boolean control. */
defineProps<{ title?: string; help?: string }>();
/** Exposes the switch value through Vue's default `v-model`. */
const model = defineModel<boolean>({ default: false });
</script>

<template>
  <label class="gw-switch">
    <input v-model="model" class="gw-switch__input" type="checkbox">
    <span class="gw-switch__control" aria-hidden="true" />
    <span class="gw-switch__text">
      <strong v-if="title" class="gw-switch__title">{{ title }}</strong>
      <small v-if="help" class="gw-switch__help">{{ help }}</small>
      <slot />
    </span>
  </label>
</template>
