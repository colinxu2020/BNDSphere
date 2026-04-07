<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { registerApiV1AuthRegisterPost } from '@/client';
import { formatError } from '@/lib/utils';

const router = useRouter();
const username = ref('');
const password = ref('');
const confirmPassword = ref('');
const agreeToTerms = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');
const validationErrors = ref({
  password: '',
  confirm: '',
});

// 校验规则：长度 > 6，且包含英文和数字
const validatePassword = (val: string) => {
  if (!val) return '';
  if (val.length <= 6) return '密码必须大于 6 位';
  const hasEnglish = /[a-zA-Z]/.test(val);
  const hasNumber = /[0-9]/.test(val);
  if (!hasEnglish || !hasNumber) return '密码必须同时包含英文和数字';
  return '';
};

// 监听密码变化，实时校验
watch(password, (newVal) => {
  validationErrors.value.password = validatePassword(newVal);
  // 如果确认密码已经填了，也要触发一致性校验
  if (confirmPassword.value) {
    validationErrors.value.confirm = newVal !== confirmPassword.value ? '两次输入的密码不一致' : '';
  }
});

// 监听确认密码变化，实时校验一致性
watch(confirmPassword, (newVal) => {
  validationErrors.value.confirm = newVal !== password.value ? '两次输入的密码不一致' : '';
});

const isFormValid = computed(() => {
  return (
    username.value &&
    password.value &&
    confirmPassword.value &&
    agreeToTerms.value &&
    !validationErrors.value.password &&
    !validationErrors.value.confirm &&
    !isLoading.value
  );
});

const handleRegister = async () => {
  if (!isFormValid.value) return;

  isLoading.value = true;
  errorMessage.value = '';

  try {
    const { error } = await registerApiV1AuthRegisterPost({
      body: {
        username: username.value,
        password: password.value,
      },
    });

    if (error) {
      errorMessage.value = formatError(error, '注册失败');
      return;
    }

    // 注册成功，跳转到登录页
    void router.push('/login');
  } catch (err: any) {
    // 处理由请求过程抛出的意外错误
    errorMessage.value = `请求异常: ${err.message || '请检查网络连接'}`;
    console.error('Register unexpected error:', err);
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="h-full flex items-center justify-center bg-gray-50/50 px-4 py-12 sm:px-6 lg:px-8">
    <Card class="w-full max-w-md shadow-lg">
      <CardHeader class="space-y-1 text-center">
        <CardTitle class="text-2xl font-bold tracking-tight">创建新账号</CardTitle>
        <CardDescription> 注册以加入 BNDSphere </CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">
        <!-- 错误提示 -->
        <div
          v-if="errorMessage"
          class="bg-destructive/10 text-destructive text-sm p-3 rounded-md text-center"
        >
          {{ errorMessage }}
        </div>

        <div class="space-y-2">
          <label for="username" class="text-sm font-medium leading-none"> 用户名 </label>
          <input
            id="username"
            v-model="username"
            type="text"
            placeholder="账号名称"
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            @keyup.enter="handleRegister"
          />
        </div>

        <div class="space-y-2">
          <label for="password" class="text-sm font-medium leading-none"> 密码 </label>
          <input
            id="password"
            v-model="password"
            type="password"
            placeholder="必须包含英文和数字，且大于 6 位"
            :class="[
              'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
              validationErrors.password
                ? 'border-destructive ring-destructive/20 focus-visible:ring-destructive'
                : '',
            ]"
            @keyup.enter="handleRegister"
          />
          <p v-if="validationErrors.password" class="text-[12px] font-medium text-destructive">
            {{ validationErrors.password }}
          </p>
        </div>

        <div class="space-y-2">
          <label for="confirmPassword" class="text-sm font-medium leading-none"> 确认密码 </label>
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            type="password"
            placeholder=""
            :class="[
              'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
              validationErrors.confirm
                ? 'border-destructive ring-destructive/20 focus-visible:ring-destructive'
                : '',
            ]"
            @keyup.enter="handleRegister"
          />
          <p v-if="validationErrors.confirm" class="text-[12px] font-medium text-destructive">
            {{ validationErrors.confirm }}
          </p>
        </div>

        <!-- 隐私协议 -->
        <div class="flex items-center space-x-2 pt-2 group">
          <Checkbox
            id="terms"
            v-model="agreeToTerms"
            class="cursor-pointer transition-all hover:ring-2 hover:ring-primary/40 hover:border-primary"
          />
          <label
            for="terms"
            class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
          >
            我已阅读并同意
            <a href="#" class="text-primary hover:underline" @click.stop>《用户隐私协议》</a>
          </label>
        </div>
      </CardContent>

      <CardFooter class="flex flex-col gap-4">
        <Button class="w-full" size="lg" :disabled="!isFormValid" @click="handleRegister">
          {{ isLoading ? '提交中...' : '立即注册' }}
        </Button>
        <div class="text-center text-sm text-muted-foreground">
          已有账号？
          <router-link to="/login" class="text-primary hover:underline font-medium">
            立即登录
          </router-link>
        </div>
      </CardFooter>
    </Card>
  </div>
</template>
