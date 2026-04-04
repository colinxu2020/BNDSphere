<script setup>
import NavItem from '@/components/TopBar/NavItem.vue';
import { useUserStore } from '../lib/auth/userStore';
import { computed, onMounted, watch } from 'vue';
import UserCard from '../components/TopBar/UserCard.vue';

const userStore = useUserStore();
const isLogin = computed(() => userStore.isLogin);

onMounted(async () => {
  if (userStore.isLogin && !userStore.userInfo) {
    await userStore.fetchUser();
  }
});

watch(isLogin, async (loggedIn) => {
  if (loggedIn && !userStore.userInfo && !userStore.loading) {
    await userStore.fetchUser();
  }
});

// var isLogin = ref(false);
</script>

<template>
  <header class="h-16 border-b border-gray-200 px-32">
    <div class="flex h-full items-center">
      <!-- 左侧 -->
      <div class="w-40 font-semibold text-gray-800">十一学校云平台</div>

      <!-- 中间 -->
      <nav class="flex flex-1 items-center justify-center gap-8">
        <NavItem text="首页" to="/" />
        <NavItem text="管理社团" to="/admin" />
        <NavItem text="发现社团" to="/pricing" />
      </nav>

      <!-- 右侧 -->
      <div class="w-40 flex justify-end gap-6" v-if="!userStore.isLogin || !userStore.userInfo">
        <NavItem text="登录" to="/login" />
        <NavItem text="注册" to="/register" />
      </div>
      <div class="w-40 flex justify-end gap-6" v-else>
        <UserCard
          :avatar-url="userStore.userInfo.avatar_uri"
          :name="userStore.userInfo.username"
          :user-id="userStore.userInfo.id"
        />
      </div>
    </div>
  </header>

  <div id="MainCountainer" class="h-[calc(100vh-64px)] overflow-auto bg-b-gray-100">
    <slot />
  </div>
</template>
