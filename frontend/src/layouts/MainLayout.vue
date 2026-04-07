<script setup>
import NavItem from '@/components/TopBar/NavItem.vue';
import UserCard from '@/components/TopBar/UserCard.vue';
import { useUserStore } from '@/lib/auth/userStore';
import { onMounted } from 'vue';

const userStore = useUserStore();

onMounted(async () => {
  if (!userStore.userInfo) {
    try {
      await userStore.fetchUser();
    } catch (error) {
      console.error('MainLayout fetchUser failed:', error);
    }
  }
});
</script>

<template>
  <div class="h-full w-full">
    <header class="h-16 border-b border-gray-200 px-32">
      <div class="flex h-full items-center">
        <!-- 左侧 -->
        <div class="w-40 font-semibold text-gray-800">十一学校云平台</div>

        <!-- 中间 -->
        <nav class="flex flex-1 items-center justify-center gap-8">
          <NavItem text="首页" to="/" />
          <NavItem text="活动列表" to="/activities" />
          <NavItem text="发现社团" to="/pricing" />
        </nav>

        <!-- 右侧 -->
        <div class="w-40 flex justify-end gap-6">
          <UserCard
            v-if="userStore.userInfo"
            :avatar-url="userStore.userInfo.avatar_uri"
            :name="userStore.userInfo.username"
            :user-id="userStore.userInfo.id"
          />
        </div>
      </div>
    </header>

    <div id="MainCountainer" class="h-[calc(100vh-64px)] overflow-auto bg-b-gray-50">
      <slot />
    </div>
  </div>
</template>
