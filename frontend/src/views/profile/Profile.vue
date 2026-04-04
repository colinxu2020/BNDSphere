<template>
  <div class="pt-8 px-32 flex flex-col gap-4">
    <AutoCloseAlert
      v-model:visible="showErrorAlert"
      color="error"
      title="操作失败"
      :description="errorMessage"
      :auto-close="alertAutoClose"
      :duration="alertDuration"
    >
      <template #icon>
        <AlertCircleIcon />
      </template>
    </AutoCloseAlert>

    <AutoCloseAlert
      v-model:visible="showSuccessAlert"
      color="success"
      title="操作成功"
      :description="successMessage"
      :auto-close="alertAutoClose"
      :duration="alertDuration"
    >
      <template #icon>
        <CheckCircle2Icon />
      </template>
    </AutoCloseAlert>

    <div class="min-h-[100px] p-6 relative bg-white rounded-sm shadow" v-if="profileUser">
      <div class="flex flex-row items-center gap-4 mb-4">
        <div class="flex flex-row items-center gap-4">
          <UserAvatar
            :avatar-url="profileUser.avatar_uri"
            :name="profileUser.username"
            size="lg"
            class="shadow"
          />
          <div class="flex flex-col gap-1">
            <p class="text-lg font-semibold">{{ profileUser.username }}</p>
            <p class="text-sm text-gray-500">用户 ID：{{ profileUser.id }}</p>
            <p class="text-sm text-gray-500">注册时间：{{ formatDate(profileUser.created_at) }}</p>
          </div>
        </div>
        <Button
          class="ml-auto"
          variant="outline"
          v-if="isSelfProfile"
          :to="`/user/${profileUser.id}/settings`"
        >
          <router-link
            v-if="isSelfProfile"
            :to="`/settings/profile`"
            class="text-sm text-primary hover:underline"
          >
            账号设置
          </router-link>
        </Button>
      </div>
    </div>

    <div v-if="loading" class="bg-white min-h-[120px] rounded-sm p-6 shadow">
      正在加载用户资料...
    </div>

    <template v-if="profileUser && !loading">
      <div class="bg-white min-h-[160px] rounded-sm p-6 mt-4 shadow mb-4">
        <div class="flex flex-row items-center gap-4 mb-4">
          <p class="text-lg font-semibold">个人简介</p>
          <Button
            v-if="isSelfProfile && !isEditing"
            variant="outline"
            class="ml-auto"
            @click="startEdit"
          >
            编辑
          </Button>
          <div v-if="isSelfProfile && isEditing" class="ml-auto flex gap-2">
            <Button variant="outline" @click="cancelEdit">取消</Button>
            <Button :disabled="saving" @click="saveProfile">{{
              saving ? '保存中...' : '保存'
            }}</Button>
          </div>
        </div>

        <div id="description" v-if="!isEditing">
          <p class="whitespace-pre-line">
            {{ profileUser.description || '这个用户还没有填写个人简介。' }}
          </p>
        </div>

        <div v-else class="flex flex-col gap-4 mb-4">
          <div>
            <p class="text-sm mb-1 text-gray-600">个人简介</p>
            <textarea
              v-model="form.description"
              class="w-full min-h-[120px] rounded-md border border-input bg-transparent px-3 py-2 text-sm"
              placeholder="介绍一下你自己"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { AlertCircleIcon, CheckCircle2Icon } from 'lucide-vue-next';
import UserAvatar from '@/components/Profile/UserAvatar.vue';
import { useUserStore } from '@/lib/auth/userStore';
import { AutoCloseAlert } from '@/components/ui/alert';
import Button from '@/components/ui/button/Button.vue';
import { getUserById, updateMyProfile } from '@/lib/auth/utils';

const userStore = useUserStore();
const route = useRoute();

const profileUser = ref(null);
const loading = ref(false);
const saving = ref(false);
const isEditing = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const showErrorAlert = ref(false);
const showSuccessAlert = ref(false);

// 调用方可覆盖：是否自动关闭与关闭时长（默认 5 秒）
const alertAutoClose = ref(true);
const alertDuration = ref(5000);

const form = reactive({
  description: '',
});

const isSelfProfile = computed(() => {
  const currentUserId = userStore.userInfo?.id;
  const routeUserId = Number(route.params.id);
  return !!currentUserId && Number.isFinite(routeUserId) && currentUserId === routeUserId;
});

function fillFormFromProfile() {
  form.description = profileUser.value?.description || '';
}

async function loadProfile() {
  loading.value = true;
  errorMessage.value = '';
  successMessage.value = '';
  isEditing.value = false;

  try {
    if (userStore.isLogin && !userStore.userInfo) {
      await userStore.fetchUser();
    }

    const routeUserId = Number(route.params.id);
    if (!Number.isInteger(routeUserId) || routeUserId <= 0) {
      throw new Error('用户 ID 无效');
    }

    if (userStore.userInfo?.id === routeUserId) {
      profileUser.value = userStore.userInfo;
    } else {
      profileUser.value = await getUserById(routeUserId);
    }

    fillFormFromProfile();
  } catch (error) {
    profileUser.value = null;
    errorMessage.value = error instanceof Error ? error.message : '加载用户资料失败';
    showErrorAlert.value = true;
  } finally {
    loading.value = false;
  }
}

function startEdit() {
  if (!isSelfProfile.value) {
    return;
  }
  fillFormFromProfile();
  isEditing.value = true;
}

function cancelEdit() {
  fillFormFromProfile();
  isEditing.value = false;
}

async function saveProfile() {
  if (!isSelfProfile.value) {
    return;
  }
  saving.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const updated = await updateMyProfile({
      description: form.description,
    });

    userStore.userInfo = updated;
    profileUser.value = updated;
    fillFormFromProfile();
    isEditing.value = false;
    successMessage.value = '个人资料已更新';
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '更新资料失败';
    showErrorAlert.value = true;
  } finally {
    saving.value = false;
  }
}

function formatDate(dateString) {
  if (!dateString) {
    return '-';
  }
  const d = new Date(dateString);
  if (Number.isNaN(d.getTime())) {
    return dateString;
  }
  return d.toLocaleString();
}

watch(() => route.params.id, loadProfile, { immediate: true });

watch(errorMessage, (value) => {
  showErrorAlert.value = !!value;
});

watch(successMessage, (value) => {
  showSuccessAlert.value = !!value;
});
</script>
