<script setup>
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
</script>
<template>
  <div class="ml-48 mt-16">
    <h1 class="text-5xl font-bold text-gray-800 tracking-wide mb-4">北京市十一学校社团共享平台</h1>
    <h2 class="text-3xl font-semibold text-gray-600 tracking-wide mb-4">
      Beijing National Day School
    </h2>
    <p class="text-gray-500">一站式社团共享与协作平台</p>
  </div>
  <div class="mt-16 px-48">
    <div class="grid grid-cols-3 gap-8">
      <Card class="rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition">
        <CardHeader>
          <CardTitle class="text-xl text-slate-800">标题1</CardTitle>
          <CardDescription class="text-slate-500">说明文字1</CardDescription>
        </CardHeader>
        <CardContent class="text-sm text-slate-700"> 内容区域1 </CardContent>
      </Card>
      <Card class="rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition">
        <CardHeader>
          <CardTitle class="text-xl text-slate-800">标题2</CardTitle>
          <CardDescription class="text-slate-500">说明文字2</CardDescription>
        </CardHeader>
        <CardContent class="text-sm text-slate-700"> 内容区域2 </CardContent>
      </Card>
      <Card class="rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition">
        <CardHeader>
          <CardTitle class="text-xl text-slate-800">标题3</CardTitle>
          <CardDescription class="text-slate-500">说明文字3</CardDescription>
        </CardHeader>
        <CardContent class="text-sm text-slate-700"> 内容区域3 </CardContent>
      </Card>
    </div>
  </div>
</template>
