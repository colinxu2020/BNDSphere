<script setup>
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import ClubCard from '@/components/GuestMainPage/ClubCard.vue';

import { ref, computed } from 'vue';

const clubs = [
  {
    name: '信息技术协会',
    tags: ['技术', '编程'],
    descrption: '专注于信息技术与编程学习的社团',
  },
  {
    name: '艺术社',
    tags: ['艺术', '绘画'],
    descrption: '热爱艺术与绘画的同学们的聚集地',
  },
  {
    name: '文学社',
    tags: ['文学', '写作'],
    descrption: '喜欢文学创作与阅读的同学们',
  },
];

// 聚合所有标签并去重
const allTags = computed(() => {
  const tagSet = new Set();
  clubs.forEach(club => club.tags.forEach(tag => tagSet.add(tag)));
  return Array.from(tagSet);
});

const selectedTag = ref('全部');

const filteredClubs = computed(() => {
  if (selectedTag.value === '全部') return clubs;
  return clubs.filter(club => club.tags.includes(selectedTag.value));
});
</script>
<template>
  <div class="ml-48 mt-16">
    <h1 class="text-5xl font-bold text-gray-800 tracking-wide mb-4">北京市十一学校社团共享平台</h1>
    <h2 class="text-3xl font-semibold text-gray-600 tracking-wide mb-4">
      Beijing National Day School
    </h2>
    <p class="text-gray-500">一站式社团共享与协作平台</p>
  </div>
  <div class="mt-16 px-48 flex gap-4">
    <Button
      variant="outline"
      :class="selectedTag === '全部' ? 'bg-gray-200' : ''"
      @click="selectedTag = '全部'"
    >
      全部
    </Button>
    <Button
      v-for="tag in allTags"
      :key="tag"
      variant="outline"
      :class="selectedTag === tag ? 'bg-gray-200' : ''"
      @click="selectedTag = tag"
    >
      {{ tag }}
    </Button>
  </div>
  <div class="mt-16 px-48">
    <div class="grid grid-cols-3 gap-8">
      <ClubCard
        v-for="(club, idx) in filteredClubs"
        :key="idx"
        :name="club.name"
        :tags="club.tags"
        :descrption="club.descrption"
      />
    </div>
  </div>
</template>
