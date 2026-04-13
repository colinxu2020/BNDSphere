<script setup>
import NavItem from '@/components/TopBar/NavItem.vue';
import { useUserStore } from '../lib/auth/userStore';
import { computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import UserCard from '../components/TopBar/UserCard.vue';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';

const userStore = useUserStore();
const route = useRoute();
const isLogin = computed(() => userStore.isLogin);

const breadcrumbs = computed(() => {
  const matched = route.matched;
  // 如果是首页，不显示面包屑
  if (route.path === '/') return [];

  return matched
    .map((m) => {
      // 动态处理带有参数的路径，例如 /activity/1
      let path = m.path;
      if (m.path.includes(':')) {
        path = route.path; // 使用当前真实的完整路径
      }

      return {
        name: m.name || m.path.split('/').pop(),
        path: path,
        label: m.meta.title,
      };
    })
    .filter((b) => b.label);
});

onMounted(async () => {
  if (userStore.isLogin && !userStore.userInfo) {
    try {
      await userStore.fetchUser();
    } catch (error) {
      console.error('GuestLayout fetchUser failed:', error);
    }
  }
});

watch(isLogin, async (loggedIn) => {
  if (loggedIn && !userStore.userInfo && !userStore.loading) {
    try {
      await userStore.fetchUser();
    } catch (error) {
      console.error('GuestLayout watch fetchUser failed:', error);
    }
  }
});

// var isLogin = ref(false);
</script>

<template>
  <div class="h-full w-full">
    <header class="h-16 border-b border-gray-200">
      <div class="mx-auto max-w-7xl h-full px-6 lg:px-12 flex items-center">
        <!-- 左侧 -->
        <div class="w-40 font-semibold text-gray-800">十一学校云平台</div>

        <!-- 中间 -->
        <nav class="flex flex-1 items-center justify-center gap-8">
          <NavItem text="首页" to="/" />
          <NavItem text="活动列表" to="/activities" />
          <NavItem text="发现社团" to="/clubs/discover" />
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

    <div
      id="MainCountainer"
      class="h-[calc(100vh-64px)] overflow-auto bg-b-gray-50 flex flex-col items-center"
    >
      <!-- 统一的内容限制容器 -->
      <div class="w-full max-w-7xl px-6 lg:px-12 flex flex-col">
        <!-- 面包屑导航 - 与下方 Card 头部对齐 -->
        <div v-if="breadcrumbs.length > 0" class="py-4">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink as-child>
                  <router-link to="/" class="hover:text-primary transition-colors"
                    >首页</router-link
                  >
                </BreadcrumbLink>
              </BreadcrumbItem>
              <template v-for="(breadcrumb, index) in breadcrumbs" :key="breadcrumb.path">
                <template v-if="breadcrumb.path !== '/'">
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    <BreadcrumbLink v-if="index < breadcrumbs.length - 1" as-child>
                      <router-link
                        :to="breadcrumb.path"
                        class="hover:text-primary transition-colors"
                      >
                        {{ breadcrumb.label }}
                      </router-link>
                    </BreadcrumbLink>
                    <BreadcrumbPage v-else class="font-medium text-foreground">
                      {{ breadcrumb.label }}
                    </BreadcrumbPage>
                  </BreadcrumbItem>
                </template>
              </template>
            </BreadcrumbList>
          </Breadcrumb>
        </div>

        <main class="flex-grow pb-12">
          <slot />
        </main>
      </div>
    </div>
  </div>
</template>
