<template>
  <div class="pt-8 px-32 flex flex-col gap-4">
    <div class="min-h-[100px]p-6 relative">
      <div class="flex flex-row items-center gap-4">
        <UserAvatar
          :avatar-url="userInfo?.avatar_uri"
          :name="userInfo?.username"
          size="lg"
          class="shadow"
        />
        <div class="flex flex-col">
          <p class="text-lg font-semibold">{{ userInfo?.username }}</p>
          <div class="">
            <p>Hi</p>
          </div>
        </div>
      </div>
    </div>

    <div class="bg-white min-h-[200px] rounded-sm p-6 mt-4 shadow">
      <div class="flex flex-row items-center gap-4 mb-4">
        <p class="text-lg font-semibold">个人简介</p>
        <Button variant="outline" class="ml-auto" @click="editDescription">编辑</Button>
      </div>
      <div id="description" class="">
        <p>{{ userInfo?.description }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import UserAvatar from '@/components/Profile/UserAvatar.vue';
import { useUserStore } from '@/lib/auth/userStore';
import Button from '@/components/ui/button/Button.vue';
// import Input from '../../components/ui/input/Input.vue';
const userStore = useUserStore();

// 使用 computed 保持响应式链接
const userInfo = computed(() => userStore.userInfo);

onMounted(async () => {
  // 如果页面刷新或者直接进入，store 里可能还没数据，需要获取一下
  if (!userStore.userInfo) {
    await userStore.fetchUser();
  }
  console.log('Profile userInfo:', userStore.userInfo);
});

function editDescription() {}
</script>
