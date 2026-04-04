<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import type { AlertVariants } from '.';
import Alert from './Alert.vue';
import AlertDescription from './AlertDescription.vue';
import AlertTitle from './AlertTitle.vue';

type AlertColorPreset = 'default' | 'success' | 'error' | 'info' | 'warning';

const props = withDefaults(
  defineProps<{
    visible: boolean;
    title?: string;
    description?: string;
    variant?: AlertVariants['variant'];
    color?: AlertColorPreset;
    autoClose?: boolean;
    duration?: number;
  }>(),
  {
    title: '',
    description: '',
    variant: 'default',
    color: 'default',
    autoClose: true,
    duration: 5000,
  },
);

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
}>();

const innerVisible = ref(props.visible);
let timer: ReturnType<typeof setTimeout> | null = null;

const resolvedVariant = computed<AlertVariants['variant']>(() => {
  if (props.variant && props.variant !== 'default') {
    return props.variant;
  }

  if (props.color === 'error') {
    return 'error';
  }
  if (props.color === 'success') {
    return 'success';
  }
  if (props.color === 'info') {
    return 'info';
  }
  if (props.color === 'warning') {
    return 'warning';
  }
  return 'default';
});

function clearTimer() {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
}

function startAutoClose() {
  clearTimer();
  if (!props.autoClose || !innerVisible.value) {
    return;
  }
  timer = setTimeout(
    () => {
      innerVisible.value = false;
    },
    Math.max(0, props.duration),
  );
}

watch(
  () => props.visible,
  (value) => {
    innerVisible.value = value;
    startAutoClose();
  },
  { immediate: true },
);

watch(innerVisible, (value) => {
  emit('update:visible', value);
  if (!value) {
    clearTimer();
  }
});

watch(
  () => [props.autoClose, props.duration],
  () => {
    startAutoClose();
  },
);

onBeforeUnmount(() => {
  clearTimer();
});
</script>

<template>
  <Alert v-if="innerVisible" :variant="resolvedVariant">
    <slot name="icon" />
    <AlertTitle v-if="title">{{ title }}</AlertTitle>
    <AlertDescription v-if="description || $slots.default">
      <slot>{{ description }}</slot>
    </AlertDescription>
  </Alert>
</template>
