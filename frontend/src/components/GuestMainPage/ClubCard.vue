<script setup>
defineProps({
  name: String,
  category: String,
  description: String,
  logo_uri: String,
  id: String,
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
          <div class="mt-1">
            <Badge variant="secondary">{{ category }}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent class="text-sm text-slate-700">
        {{ description }}
      </CardContent>
    </Card>
  </router-link>
</template>
