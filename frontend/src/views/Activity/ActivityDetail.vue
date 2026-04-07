<template>
  <div class="py-8">
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      <p class="mt-4 text-muted-foreground">加载中...</p>
    </div>

    <div v-else-if="error" class="text-center py-20">
      <h2 class="text-2xl font-bold text-destructive">出错了</h2>
      <p class="mt-2 text-muted-foreground">{{ errorMessage }}</p>
      <Button class="mt-4" @click="router.back()">返回</Button>
    </div>

    <div v-else-if="activity" class="max-w-4xl">
      <div class="flex items-center gap-4 mb-6">
        <Button
          variant="outline"
          size="icon"
          @click="router.back()"
          class="rounded-full shadow-sm hover:bg-primary hover:text-white transition-all"
        >
          <ChevronLeft class="h-5 w-5" />
        </Button>
        <span class="text-sm font-medium text-muted-foreground">返回列表</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- 左侧详情 -->
        <div class="md:col-span-2 space-y-6">
          <div>
            <div class="flex items-center gap-3 mb-4">
              <Badge :variant="getBadgeVariant(activity.level)">
                {{ getLevelLabel(activity.level) }}
              </Badge>
              <span class="text-sm text-muted-foreground">
                发布于 {{ formatDate(activity.created_at) }}
              </span>
            </div>
            <h1 class="text-4xl font-bold tracking-tight mb-4 text-balance">
              {{ activity.name }}
            </h1>
          </div>

          <Card>
            <CardHeader>
              <CardTitle class="text-lg">活动介绍</CardTitle>
            </CardHeader>
            <CardContent class="prose prose-sm max-w-none dark:prose-invert">
              <p class="whitespace-pre-wrap leading-relaxed text-base">
                {{ activity.description }}
              </p>
            </CardContent>
          </Card>
        </div>

        <!-- 右侧侧边栏 (参与社团) -->
        <div class="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle class="text-lg"
                >参与社团 ({{ activity.club_records?.length || 0 }})</CardTitle
              >
            </CardHeader>
            <CardContent>
              <div v-if="activity.club_records?.length" class="space-y-4">
                <div
                  v-for="record in activity.club_records"
                  :key="record.id"
                  class="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
                  @click="goToClub(record.club_id)"
                >
                  <div
                    class="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center font-bold text-primary"
                  >
                    {{ record.club_id }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">社团 ID: {{ record.club_id }}</p>
                    <p class="text-xs text-muted-foreground">
                      {{ getParticipationTypeLabel(record.participation_type) }}
                    </p>
                  </div>
                  <Badge variant="outline" class="text-[10px] px-1.5 py-0">
                    {{ getAuditLabel(record.audit_status) }}
                  </Badge>
                </div>
              </div>
              <div v-else class="text-center py-6">
                <p class="text-sm text-muted-foreground">暂无社团参与记录</p>
              </div>
            </CardContent>
          </Card>

          <!-- 快速信息卡片 -->
          <Card class="bg-primary/5 border-primary/10">
            <CardContent class="pt-6 space-y-4 text-sm">
              <div class="flex justify-between">
                <span class="text-muted-foreground">活动编号</span>
                <span class="font-mono">{{ activity.id }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted-foreground">活动级别</span>
                <span>{{ getLevelLabel(activity.level) }}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getApiV1GeneralActivitiesActivityIdGet, type GeneralActivityInfo } from '@/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronLeft } from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const activityId = Number(route.params.id);

const activity = ref<GeneralActivityInfo | null>(null);
const loading = ref(true);
const error = ref(false);
const errorMessage = ref('');

const fetchActivityDetail = async () => {
  if (isNaN(activityId)) {
    error.value = true;
    errorMessage.value = '无效的活动 ID';
    loading.value = false;
    return;
  }

  loading.value = true;
  try {
    const { data, error: apiError } = await getApiV1GeneralActivitiesActivityIdGet({
      path: { activity_id: activityId },
    });

    if (apiError) {
      error.value = true;
      errorMessage.value =
        '获取活动详情失败: ' + (typeof apiError === 'object' ? JSON.stringify(apiError) : apiError);
    } else if (data) {
      activity.value = data;
    }
  } catch (_err) {
    error.value = true;
    errorMessage.value = '请求出错，请重试';
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
    case 'sua':
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
    case 'sua':
      return '学生会活动';
    default:
      return level;
  }
};

const getParticipationTypeLabel = (type: string) => {
  switch (type) {
    case 'participate_only':
      return '普通参与';
    case 'organize':
      return '承办/组织';
    default:
      return type;
  }
};

const getAuditLabel = (status: string) => {
  switch (status) {
    case 'pending':
      return '待审核';
    case 'approved':
      return '已通过';
    case 'rejected':
      return '已拒绝';
    default:
      return status;
  }
};

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const goToClub = (clubId: number) => {
  router.push(`/club/${clubId}`);
};

onMounted(() => {
  fetchActivityDetail();
});
</script>
