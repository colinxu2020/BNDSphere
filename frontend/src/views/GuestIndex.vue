<script setup>
import { Button } from '@/components/ui/button';
import ClubCard from '@/components/GuestMainPage/ClubCard.vue';
import { listClubsApiV1ClubsGet } from '@/client';
import { ref, computed } from 'vue';
// const clubs = [
//   {
//     name: '信息技术协会',
//     tags: ['技术', '编程'],
//     descrption: '专注于信息技术与编程学习的社团',
//   },
//   {
//     name: '艺术社',
//     tags: ['艺术', '绘画'],
//     descrption: '热爱艺术与绘画的同学们的聚集地',
//   },
//   {
//     name: '文学社',
//     tags: ['文学', '写作'],
//     descrption: '喜欢文学创作与阅读的同学们',
//   },
// ];

var clubs = ref([]);
listClubsApiV1ClubsGet({
  query: {
    offset: 0,
    limit: 100,
  },
}).then(({ data, error }) => {
  if (error) {
    console.error('获取社团列表失败:', error);
  } else {
    console.log('社团列表:', data);
    clubs.value = data.items;
  }
});

// 社团分类映射与翻译
const CATEGORY_MAP = {
  sports: '体育',
  humanity: '人文',
  arts: '艺术',
  science: '科学',
  charity: '公益',
  business: '商业',
  campus: '校园',
  other: '其他',
};

const allCategories = Object.keys(CATEGORY_MAP);

const selectedCategory = ref('全部');

const filteredClubs = computed(() => {
  if (selectedCategory.value === '全部') return clubs.value;
  return clubs.value.filter((club) => club.category === selectedCategory.value);
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
  <div class="mt-16 px-48 flex flex-wrap gap-4">
    <Button
      variant="outline"
      :class="selectedCategory === '全部' ? 'bg-gray-200' : ''"
      @click="selectedCategory = '全部'"
    >
      全部
    </Button>
    <Button
      v-for="catKey in allCategories"
      :key="catKey"
      variant="outline"
      :class="selectedCategory === catKey ? 'bg-gray-200' : ''"
      @click="selectedCategory = catKey"
    >
      {{ CATEGORY_MAP[catKey] }}
    </Button>
  </div>
  <div class="mt-16 px-48 pb-24">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      <ClubCard
        v-for="(club, idx) in filteredClubs"
        :key="idx"
        :name="club.name"
        :category="CATEGORY_MAP[club.category] || club.category"
        :description="club.description"
        :logo_uri="club.logo_uri"
      />
    </div>
  </div>
</template>
