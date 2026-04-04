<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { ENDPOINTS } from '@/lib/api';
import { request } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const route = useRoute();
const loading = ref(true);
const error = ref('');
const club = ref(null);

const clubId = computed(() => Number(route.params.id));

const statusTextMap = {
  unreviewed: '未审核',
  approved: '已通过',
  rejected: '未通过',
};

const starTextMap = {
  none: '无评级',
  one: '1 星',
  two: '2 星',
  three: '3 星',
};

const statusText = computed(() => {
  if (!club.value) return '';
  return statusTextMap[club.value.status] || club.value.status;
});

const starText = computed(() => {
  if (!club.value) return '';
  return starTextMap[club.value.star_level] || club.value.star_level;
});

const createdAtText = computed(() => {
  if (!club.value) return '';
  return new Date(club.value.created_at).toLocaleString('zh-CN');
});

async function fetchClubDetail() {
  loading.value = true;
  error.value = '';

  if (!Number.isInteger(clubId.value) || clubId.value <= 0) {
    error.value = '社团 ID 非法';
    loading.value = false;
    return;
  }

  const token = localStorage.getItem('token');

  try {
    club.value = await request(`${ENDPOINTS.CLUBS.BASE}/${clubId.value}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
  } catch (err) {
    if (err instanceof Error) {
      error.value = err.message || '获取社团详情失败';
    } else {
      error.value = '获取社团详情失败';
    }
  } finally {
    loading.value = false;
  }
}

onMounted(fetchClubDetail);
</script>

<template>
  <div class="px-32 py-8">
    <Card>
      <CardHeader>
        <CardTitle class="text-2xl">社团详情</CardTitle>
        <CardDescription>Club ID: {{ route.params.id }}</CardDescription>
      </CardHeader>

      <CardContent>
        <div v-if="loading" class="text-slate-500">加载中...</div>

        <div v-else-if="error" class="text-red-500">
          {{ error }}
        </div>

        <div v-else-if="club" class="space-y-5">
          <div class="flex items-start gap-4">
            <img
              v-if="club.logo_uri"
              :src="club.logo_uri"
              :alt="club.name"
              class="h-20 w-20 rounded-lg border object-cover"
            />
            <div class="space-y-2">
              <h1 class="text-2xl font-bold text-slate-800">{{ club.name }}</h1>
              <p class="text-slate-600">{{ club.summary }}</p>
              <div class="flex gap-2">
                <Badge variant="outline">状态: {{ statusText }}</Badge>
                <Badge variant="outline">评级: {{ starText }}</Badge>
              </div>
            </div>
          </div>

          <div>
            <h2 class="mb-2 text-lg font-semibold">社团介绍</h2>
            <p class="whitespace-pre-line text-slate-700">{{ club.description }}</p>
          </div>

          <div class="text-sm text-slate-500">创建时间: {{ createdAtText }}</div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
