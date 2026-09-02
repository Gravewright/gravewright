<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

/** Configures modal content, dimensions, accessibility role, and busy state. */
const props = withDefaults(defineProps<{
  eyebrow?: string;
  title: string;
  width?: "narrow" | "default" | "wide";
  /** Blocks Escape and the backdrop while a request is in flight. */
  busy?: boolean;
  closeLabel?: string;
  role?: "dialog" | "alertdialog";
}>(), { width: "default", role: "dialog", closeLabel: "Fechar" });

const emit = defineEmits<{ close: [] }>();
const dialog = ref<HTMLElement | null>(null);

/** Closes an idle modal when the user presses Escape. */
function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && !props.busy) emit("close");
}

onMounted(() => {
  window.addEventListener("keydown", onKeydown);
  void nextTick(() => dialog.value?.querySelector<HTMLElement>("[data-autofocus]")?.focus());
});
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));
</script>

<template>
  <div class="gw-modal" @click.self="!busy && emit('close')">
    <section
      ref="dialog"
      class="gw-modal__dialog"
      :class="width !== 'default' ? `gw-modal__dialog--${width}` : ''"
      :role="role"
      aria-modal="true"
      :aria-label="title"
    >
      <header class="gw-modal__header">
        <div>
          <p v-if="eyebrow" class="gw-modal__eyebrow">{{ eyebrow }}</p>
          <h2 class="gw-modal__title">{{ title }}</h2>
        </div>
        <button class="gw-modal__close" type="button" :disabled="busy" :aria-label="closeLabel" @click="emit('close')">
          &times;
        </button>
      </header>
      <div class="gw-modal__body">
        <slot />
      </div>
      <footer v-if="$slots.actions" class="gw-modal__footer">
        <slot name="actions" />
      </footer>
    </section>
  </div>
</template>
