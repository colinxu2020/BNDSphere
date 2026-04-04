<template>
  <div class="pt-8 px-32 flex flex-col gap-4">
    <div class="bg-white rounded-sm shadow p-6">
      <div class="flex items-center justify-between">
        <p class="text-lg font-semibold">账号设置</p>
        <Button variant="outline">
          <router-link
            v-if="userStore.userInfo?.id"
            :to="`/user/${userStore.userInfo.id}`"
            class="text-sm text-primary hover:underline"
          >
            返回个人主页
          </router-link>
        </Button>
      </div>
      <p class="text-sm text-gray-500 mt-1">在这里修改邮箱和头像链接，简介请在个人主页编辑。</p>
    </div>

    <AutoCloseAlert
      v-model:visible="showErrorAlert"
      color="error"
      title="保存失败"
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
      title="保存成功"
      :description="successMessage"
      :auto-close="alertAutoClose"
      :duration="alertDuration"
    >
      <template #icon>
        <CheckCircle2Icon />
      </template>
    </AutoCloseAlert>

    <div v-if="loading" class="bg-white rounded-sm shadow p-6">正在加载账号信息...</div>

    <template v-if="profileUser && !loading">
      <div class="bg-white rounded-sm shadow p-6">
        <p class="text-lg font-semibold mb-4">编辑资料</p>
        <div class="flex flex-col gap-4">
          <div>
            <p class="text-sm mb-1 text-gray-600">邮箱</p>
            <Input v-model="form.email" type="email" placeholder="请输入邮箱" />
          </div>
          <div>
            <p class="text-sm mb-1 text-gray-600">头像链接</p>
            <Input
              v-model="form.avatar_uri"
              type="url"
              placeholder="https://example.com/avatar.png"
            />
            <p class="mt-1 text-xs text-gray-500">头像链接必须是合法 URL；留空将清空头像。</p>
          </div>
          <div class="flex gap-2">
            <Button variant="outline" @click="resetForm">重置</Button>
            <Button :disabled="saving" @click="saveSettings">{{
              saving ? '保存中...' : '保存设置'
            }}</Button>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-sm shadow p-6 mb-8">
        <p class="text-lg font-semibold mb-4">账号信息</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-gray-500">用户名</p>
            <p>{{ profileUser.username }}</p>
          </div>
          <div>
            <p class="text-gray-500">用户 ID</p>
            <p>{{ profileUser.id }}</p>
          </div>
          <div>
            <p class="text-gray-500">角色</p>
            <p>{{ profileUser.role }}</p>
          </div>
          <div>
            <p class="text-gray-500">注册时间</p>
            <p>{{ formatDate(profileUser.created_at) }}</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { AlertCircleIcon, CheckCircle2Icon } from 'lucide-vue-next';
import { AutoCloseAlert } from '@/components/ui/alert';
import Button from '@/components/ui/button/Button.vue';
import Input from '@/components/ui/input/Input.vue';
import { updateMyProfile } from '@/lib/auth/utils';
import { useUserStore } from '@/lib/auth/userStore';

const userStore = useUserStore();
const router = useRouter();

const profileUser = ref(null);
const loading = ref(false);
const saving = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const showErrorAlert = ref(false);
const showSuccessAlert = ref(false);

// 调用方可覆盖：是否自动关闭与关闭时长（默认 5 秒）
const alertAutoClose = ref(true);
const alertDuration = ref(5000);

const form = reactive({
  email: '',
  avatar_uri: '',
});

function hydrateFromStore() {
  profileUser.value = userStore.userInfo;
  form.email = userStore.userInfo?.email || '';
  form.avatar_uri = userStore.userInfo?.avatar_uri || '';
}

async function loadSelfProfile() {
  loading.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    if (!userStore.userInfo) {
      await userStore.fetchUser();
    }
    if (!userStore.userInfo?.id) {
      throw new Error('请先登录');
    }
    hydrateFromStore();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载账号信息失败';
    showErrorAlert.value = true;
    if (!userStore.isLogin) {
      void router.push('/login');
    }
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  form.email = profileUser.value?.email || '';
  form.avatar_uri = profileUser.value?.avatar_uri || '';
}

async function saveSettings() {
  saving.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const payload = {
      email: form.email || null,
      avatar_uri: form.avatar_uri || null,
    };

    const updated = await updateMyProfile(payload);
    userStore.userInfo = updated;
    hydrateFromStore();
    successMessage.value = '账号设置已更新';
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '保存失败';
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

void loadSelfProfile();

watch(errorMessage, (value) => {
  showErrorAlert.value = !!value;
});

watch(successMessage, (value) => {
  showSuccessAlert.value = !!value;
});
</script>
