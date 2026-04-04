<script setup>
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/lib/auth/userStore';

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

async function handleLogout() {
  userStore.logout();
  await router.push('/login');
}
</script>

<template>
  <div class="relative group">
    <div class="flex flex-row gap-2 items-center align-middle cursor-pointer py-1">
      <p>{{ props.name }}</p>
      <Avatar>
        <AvatarImage :src="props.avatarUrl" :alt="props.name" />
        <AvatarFallback>{{ props.name ? props.name[0] : '' }}</AvatarFallback>
      </Avatar>
    </div>

    <div
      class="absolute right-0 top-full z-50 hidden min-w-[140px] rounded-md border bg-white p-1 shadow-md group-hover:block"
    >
      <router-link
        :to="profilePath"
        class="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
      >
        主页
      </router-link>
      <router-link
        :to="settingsPath"
        class="block rounded px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
      >
        设置
      </router-link>
      <button
        type="button"
        class="block w-full cursor-pointer rounded px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
        @click="handleLogout"
      >
        登出
      </button>
    </div>
  </div>
</template>
