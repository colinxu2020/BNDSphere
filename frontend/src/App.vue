<!-- src/App.vue -->
<template>
  <!-- 动态绑定布局组件 -->
  <component :is="layout">
    <router-view />
  </component>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import DefaultLayout from './layouts/DefaultLayout.vue';
import BlankLayout from './layouts/BlankLayout.vue';
import GuestLayout from './layouts/GuestLayout.vue';

const route = useRoute();
// 根据路由 meta 里的 layout 字段判断，默认使用 DefaultLayout
const layout = computed(() => {
  if (route.meta.layout === 'blank') return BlankLayout;
  if (route.meta.layout === 'guest') return GuestLayout;
  return DefaultLayout;
});
</script>
