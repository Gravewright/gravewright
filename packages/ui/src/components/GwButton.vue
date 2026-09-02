<script setup lang="ts">
import { computed } from "vue";

/** Configures a button or link with consistent visual and accessibility states. */
const props = withDefaults(defineProps<{
  /** The voice of the control. Only one `primary` per view. */
  variant?: "quiet" | "primary" | "danger" | "ghost" | "tool";
  size?: "sm" | "md" | "lg";
  block?: boolean;
  /** Renders an <a> instead of a <button> when set. */
  href?: string;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  pressed?: boolean;
}>(), { variant: "quiet", size: "md", type: "button" });

/** Selects native link semantics only when a destination is present. */
const tag = computed(() => (props.href ? "a" : "button"));
const classes = computed(() => [
  "gw-button",
  props.variant !== "quiet" ? `gw-button--${props.variant}` : "",
  props.size !== "md" ? `gw-button--${props.size}` : "",
  props.block ? "gw-button--block" : "",
]);
</script>

<template>
  <component
    :is="tag"
    :class="classes"
    :href="href"
    :type="href ? undefined : type"
    :disabled="href ? undefined : disabled"
    :aria-disabled="href && disabled ? 'true' : undefined"
    :aria-pressed="pressed === undefined ? undefined : String(pressed)"
  >
    <span v-if="$slots.icon" class="gw-button__icon"><slot name="icon" /></span>
    <slot />
    <span v-if="$slots.count" class="gw-button__count"><slot name="count" /></span>
  </component>
</template>
