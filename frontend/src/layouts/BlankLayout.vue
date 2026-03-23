<!-- src/layouts/BlankLayout.vue -->
<template>
  <div class="blank-layout">
    <!-- 直接渲染子页面内容 -->
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style scoped>
.blank-layout {
  min-height: 100vh;
  background-color: #f5f7f9;
}

/* 简单的淡入淡出动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>