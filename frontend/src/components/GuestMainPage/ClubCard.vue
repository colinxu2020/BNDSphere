<script setup>
defineProps({
  name: String,
  tags: Array,
  descrption: String,
});
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
</script>

<template>
  <Card class="rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition">
    <CardHeader>
      <CardTitle class="text-xl text-slate-800">{{ name }}</CardTitle>
      <CardDescription class="text-slate-500">{{ tags.join(', ') }}</CardDescription>
    </CardHeader>
    <CardContent class="text-sm text-slate-700"> {{ descrption }} </CardContent>
  </Card>
</template>
