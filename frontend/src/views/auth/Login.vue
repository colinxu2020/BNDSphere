<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { loginApiV1AuthLoginPost } from '@/client';
import { useUserStore } from '@/lib/auth/userStore';
import { formatError } from '@/lib/utils';

const router = useRouter();
const userStore = useUserStore();
const username = ref('');
const password = ref('');
const isLoading = ref(false);
const errorMessage = ref('');

const handleLogin = async () => {
  if (!username.value || !password.value || isLoading.value) return;

  isLoading.value = true;
  errorMessage.value = '';

  try {
    const { data, error } = await loginApiV1AuthLoginPost({
      body: {
        username: username.value,
        password: password.value,
      },
    });

    if (error) {
      errorMessage.value = formatError(error, '登录失败');
      return;
    }

    if (data && data.access_token) {
      localStorage.setItem('token', data.access_token);
      await userStore.fetchUser();
      void router.push('/');
    }
  } catch (err: any) {
    errorMessage.value = `请求异常: ${err.message || '请检查网络连接'}`;
    console.error('Login unexpected error:', err);
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="h-full flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
    <Card class="w-full max-w-md shadow-lg">
      <CardHeader class="space-y-1 text-center">
        <CardTitle class="text-2xl font-bold tracking-tight">登入 BNDSphere</CardTitle>
        <CardDescription> 请输入您的账号和密码 </CardDescription>
      </CardHeader>

      <CardContent class="space-y-4">
        <div class="space-y-2">
          <label
            for="email"
            class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            邮箱 / 用户名
          </label>
          <input
            id="email"
            v-model="username"
            type="text"
            placeholder="name@example.com"
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            @keyup.enter="handleLogin"
          />
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <label
              for="password"
              class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              密码
            </label>
            <a href="#" class="text-xs text-primary hover:underline">忘记密码？</a>
          </div>
          <input
            id="password"
            v-model="password"
            type="password"
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            @keyup.enter="handleLogin"
          />
        </div>

        <div
          v-if="errorMessage"
          class="rounded-md bg-destructive/10 p-3 text-center text-sm text-destructive"
        >
          {{ errorMessage }}
        </div>
      </CardContent>

      <CardFooter class="flex flex-col gap-4">
        <Button class="w-full" size="lg" :disabled="isLoading" @click="handleLogin">
          {{ isLoading ? '登录中...' : '登录' }}
        </Button>
        <div class="text-center text-sm text-muted-foreground">
          还没有账号？
          <router-link to="/register" class="text-primary hover:underline font-medium">
            立即注册
          </router-link>
        </div>
      </CardFooter>
    </Card>
  </div>
</template>
