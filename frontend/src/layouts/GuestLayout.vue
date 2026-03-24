<script setup>
import NavItem from '@/components/TopBar/NavItem.vue';
</script>

<template>
  <header class="h-16 border-b border-gray-200 px-32">
    <div class="flex h-full items-center">
      <!-- 左侧 -->
      <div class="w-40 font-semibold text-gray-800">一学校云平台</div>

      <!-- 中间 -->
      <nav class="flex flex-1 items-center justify-center gap-8">
        <NavItem text="首页" to="/" />
        <NavItem text="管理社团" to="/product" />
        <NavItem text="发现社团" to="/pricing" />
      </nav>

      <!-- 右侧 -->
      <div class="w-40 flex justify-end">
        <NavItem text="Login" to="/login" />
      </div>
    </div>
  </header>

  <div id="MainCountainer" class="h-[calc(100vh-64px)]">
    <router-view />
  </div>
</template>
