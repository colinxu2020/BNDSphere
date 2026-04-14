<script setup>
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/lib/auth/userStore';
import { Bell, Settings, LogOut, UserRound } from 'lucide-vue-next';

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  avatarUrl: {
    type: String,
    default: '',
  },
  userId: {
    type: [Number, String],
    required: true,
  },
});

const router = useRouter();
const userStore = useUserStore();

const profilePath = computed(() => `/user/${props.userId}`);
const settingsPath = computed(() => '/settings/profile');
const canAccessAdmin = computed(() => {
  const role = userStore.userInfo?.role;
  return role === 'admin' || role === 'dev';
});

async function goToInbox() {
  // Temporary inbox entry while message center page is not available.
  await router.push('/activities');
}

async function goToSettings() {
  await router.push(settingsPath.value);
}

async function handleLogout() {
  userStore.logout();
  await router.push('/login');
}
</script>

<template>
  <div class="relative select-none">
    <div class="flex flex-row items-center gap-1.5 py-1">
      <button
        type="button"
        class="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
        title="站内信"
        @click="goToInbox"
      >
        <Bell class="h-4 w-4" />
      </button>
      <button
        type="button"
        class="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
        title="设置"
        @click="goToSettings"
      >
        <Settings class="h-4 w-4" />
      </button>
      <div class="relative group/avatar">
        <Avatar class="cursor-pointer border border-slate-200">
          <AvatarImage :src="props.avatarUrl" :alt="props.name" />
          <AvatarFallback>{{ props.name ? props.name[0] : '' }}</AvatarFallback>
        </Avatar>

        <div
          class="absolute right-0 top-full z-50 hidden min-w-[200px] rounded-xl border border-slate-200 bg-white p-2 shadow-lg group-hover/avatar:block hover:block"
        >
          <router-link
            :to="profilePath"
            class="mb-1 flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100"
          >
            <UserRound class="h-4 w-4 text-slate-500" />
            <span class="truncate">{{ props.name }}</span>
          </router-link>

          <div class="h-px bg-slate-200 my-1"></div>

          <router-link
            :to="profilePath"
            class="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            主页
          </router-link>
          <router-link
            :to="settingsPath"
            class="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            设置
          </router-link>
          <router-link
            v-if="canAccessAdmin"
            to="/admin"
            class="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            后台管理
          </router-link>
          <button
            type="button"
            class="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
            @click="handleLogout"
          >
            <LogOut class="h-4 w-4" />
            <span>登出</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
