<script setup lang="ts">
import { ref } from 'vue';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const username = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');

const handleRegister = () => {
  console.log('Register attempt:', {
    username: username.value,
    email: email.value,
    password: password.value,
    confirmPassword: confirmPassword.value,
  });
};
</script>

<template>
  <div class="h-full flex items-center justify-center bg-gray-50/50 px-4 py-12 sm:px-6 lg:px-8">
    <Card class="w-full max-w-md shadow-lg">
      <CardHeader class="space-y-1 text-center">
        <CardTitle class="text-2xl font-bold tracking-tight">创建新账号</CardTitle>
        <CardDescription>
          请填写以下信息以注册 BNDSphere
        </CardDescription>
      </CardHeader>
      
      <CardContent class="space-y-4">
        <div class="space-y-2">
          <label for="username" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            用户名
          </label>
          <input 
            id="username"
            v-model="username"
            type="text" 
            placeholder="johndoe"
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        <div class="space-y-2">
          <label for="email" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            电子邮箱
          </label>
          <input 
            id="email"
            v-model="email"
            type="email" 
            placeholder="name@example.com"
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
        
        <div class="space-y-2">
          <label for="password" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            设置密码
          </label>
          <input 
            id="password"
            v-model="password"
            type="password" 
            placeholder=""
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        <div class="space-y-2">
          <label for="confirmPassword" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            确认密码
          </label>
          <input 
            id="confirmPassword"
            v-model="confirmPassword"
            type="password" 
            placeholder=""
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
      </CardContent>

      <CardFooter class="flex flex-col gap-4">
        <Button class="w-full" size="lg" @click="handleRegister">
          注册账号
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
