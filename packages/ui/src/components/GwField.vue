<script setup lang="ts">
/** Supplies optional label and supporting text around a form control slot. */
defineProps<{ label?: string; help?: string }>();
</script>

<template>
  <label class="gw-field">
    <span v-if="label" class="gw-field__label">{{ label }}</span>
    <slot />
    <small v-if="help" class="gw-field__help">{{ help }}</small>
  </label>
</template>
