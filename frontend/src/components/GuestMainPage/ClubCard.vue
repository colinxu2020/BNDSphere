<script setup>
defineProps({
  name: String,
  category: String,
  description: String,
  logo_uri: String,
  id: String,
  memberCount: {
    type: Number,
    default: 0,
  },
  presidentName: {
    type: String,
    default: '未知',
  },
  isJoined: {
    type: Boolean,
    default: false,
  },
});
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
</script>

<template>
  <router-link :to="`/club/${id}`">
    <Card
      class="rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition cursor-pointer"
    >
      <CardHeader class="flex flex-row items-center gap-4">
        <img
          v-if="logo_uri"
          :src="logo_uri"
          class="w-12 h-12 rounded-lg object-cover border"
          alt="Logo"
        />
        <div class="flex-1">
          <CardTitle class="text-xl text-slate-800">{{ name }}</CardTitle>
          <div class="mt-1 flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{{ category }}</Badge>
            <Badge v-if="isJoined" variant="outline" class="border-emerald-200 text-emerald-700">
              已加入
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent class="space-y-2 text-sm text-slate-700">
        <p>{{ description }}</p>
        <div class="flex flex-wrap gap-3 text-xs text-slate-500">
          <span>成员人数: {{ memberCount }}</span>
          <span>社长: {{ presidentName }}</span>
        </div>
      </CardContent>
    </Card>
  </router-link>
</template>
