<!-- src/App.vue -->
<template>
  <router-view v-slot="{ Component, route }">
    <component :is="resolveLayout(route.meta.layout)">
      <transition name="layout-fade" mode="out-in">
        <component :is="Component" :key="route.fullPath" />
      </transition>
    </component>
  </router-view>
</template>

<script setup lang="ts">
import { nextTick, watch } from 'vue';
import type { RouteMeta } from 'vue-router';
import { useRoute } from 'vue-router';
import GuestLayout from './layouts/GuestLayout.vue';
// import MainLayout from './layouts/MainLayout.vue';

const route = useRoute();

watch(
  () => route.fullPath,
  async () => {
    await nextTick();

    const mainContainer = document.getElementById('MainCountainer');
    if (mainContainer) {
      mainContainer.scrollTop = 0;
    }
  },
  { immediate: true },
);

function resolveLayout(_layout: RouteMeta['layout']) {
  return GuestLayout;
}
</script>

<style scoped>
.layout-fade-enter-active,
.layout-fade-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.layout-fade-enter-from,
.layout-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}
</style>
