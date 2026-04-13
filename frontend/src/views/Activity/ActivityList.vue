<template>
  <div class="py-8">
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">活动列表</h1>
        <p class="text-muted-foreground mt-2">查看校内各类通用活动。</p>
      </div>
      <div class="flex gap-4">
        <!-- 可以在这里添加搜索或筛选 -->
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>

    <div v-else-if="activities.length === 0" class="text-center py-12 bg-muted/30 rounded-lg">
      <p class="text-muted-foreground">暂无活动。</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card v-for="activity in activities" :key="activity.id" class="flex flex-col h-full">
        <CardHeader>
          <div class="flex justify-between items-start">
            <Badge :variant="getBadgeVariant(activity.level)">
              {{ getLevelLabel(activity.level) }}
            </Badge>
          </div>
          <CardTitle class="mt-4 break-words line-clamp-2">{{ activity.name }}</CardTitle>
        </CardHeader>
        <CardContent class="flex-grow">
          <p class="text-sm text-muted-foreground line-clamp-3">
            {{ activity.description }}
          </p>
        </CardContent>
        <CardFooter class="border-t pt-4">
          <div class="flex justify-between w-full items-center text-xs text-muted-foreground">
            <span>发布于 {{ formatDate(activity.created_at) }}</span>
            <Button variant="ghost" size="sm" @click="viewDetail(activity.id)"> 查看详情 </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { listActivitiesApiV1GeneralActivitiesGet, type GeneralActivityInfo } from '@/client';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const router = useRouter();
const activities = ref<GeneralActivityInfo[]>([]);
const loading = ref(true);

const fetchActivities = async () => {
  loading.value = true;
  try {
    const { data, error } = await listActivitiesApiV1GeneralActivitiesGet();
    if (error) {
      console.error('获取活动列表失败:', error);
    } else if (data) {
      activities.value = data;
    }
  } catch (err) {
    console.error('获取活动列表出错:', err);
  } finally {
    loading.value = false;
  }
};

const getBadgeVariant = (level: string) => {
  switch (level) {
    case 'school':
      return 'default';
    case 'large':
      return 'secondary';
    case 'club_federation':
      return 'outline';
    default:
      return 'default';
  }
};

const getLevelLabel = (level: string) => {
  switch (level) {
    case 'school':
      return '全校活动';
    case 'large':
      return '大型活动';
    case 'club_federation':
      return '学生会活动';
    default:
      return level;
  }
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

const viewDetail = (id: number) => {
  router.push(`/activity/${id}`);
};

onMounted(() => {
  fetchActivities();
});
</script>
