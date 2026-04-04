<!-- src/App.vue -->
<template>
  <router-view v-slot="{ Component, route }">
    <transition name="layout-fade" mode="out-in">
      <component :is="resolveLayout(route.meta.layout)">
        <component :is="Component" />
      </component>
    </transition>
  </router-view>
</template>

<script setup lang="ts">
import type { RouteMeta } from 'vue-router';
import GuestLayout from './layouts/GuestLayout.vue';
import MainLayout from './layouts/MainLayout.vue';

function resolveLayout(layout: RouteMeta['layout']) {
  if (layout === 'main') {
    return MainLayout;
  }
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
