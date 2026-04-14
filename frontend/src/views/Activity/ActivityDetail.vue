<template>
  <div class="py-8">
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="h-12 w-12 animate-spin rounded-full border-b-2 border-primary"></div>
      <p class="mt-4 text-muted-foreground">加载中...</p>
    </div>

    <div v-else-if="error" class="py-20 text-center">
      <h2 class="text-2xl font-bold text-destructive">出错了</h2>
      <p class="mt-2 text-muted-foreground">{{ errorMessage }}</p>
      <Button class="mt-4" @click="router.back()">返回</Button>
    </div>

    <div v-else-if="activity" class="mx-auto max-w-6xl space-y-6">
      <div class="mb-2 flex items-center gap-3">
        <Button
          variant="outline"
          size="icon"
          @click="router.back()"
          class="rounded-full shadow-sm transition-all hover:bg-primary hover:text-white"
        >
          <ChevronLeft class="h-5 w-5" />
        </Button>
        <span class="text-sm font-medium text-muted-foreground">返回列表</span>
      </div>

      <Card class="border-slate-200/80 shadow-sm">
        <CardContent class="space-y-4 p-6">
          <div class="flex flex-wrap items-center gap-2">
            <Badge :variant="getBadgeVariant(activity.level)">
              {{ getLevelLabel(activity.level) }}
            </Badge>
            <Badge variant="outline">活动编号 #{{ activity.id }}</Badge>
            <Badge variant="outline">参与社团 {{ participantCount }}</Badge>
            <Badge variant="outline">审核通过 {{ approvedCount }}</Badge>
          </div>
          <div>
            <h1 class="mb-2 text-4xl font-bold tracking-tight text-balance">{{ activity.name }}</h1>
            <p class="text-sm text-muted-foreground">
              发布时间：{{ formatDate(activity.created_at) }}
            </p>
          </div>
        </CardContent>
      </Card>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <div class="space-y-6">
          <Card class="border-slate-200/80 shadow-sm">
            <CardHeader>
              <CardTitle class="text-lg">活动介绍</CardTitle>
            </CardHeader>
            <CardContent>
              <p class="whitespace-pre-wrap text-base leading-7 text-slate-700">
                {{ activity.description }}
              </p>
            </CardContent>
          </Card>

          <Card class="border-slate-200/80 shadow-sm">
            <CardHeader>
              <CardTitle class="text-lg">参与社团列表</CardTitle>
              <CardDescription> 点击条目可跳转到对应社团详情 </CardDescription>
            </CardHeader>
            <CardContent>
              <div v-if="activity.club_records?.length" class="space-y-3">
                <button
                  v-for="record in activity.club_records"
                  :key="record.id"
                  type="button"
                  class="flex w-full items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-3 text-left transition hover:bg-slate-100"
                  @click="goToClub(record.club_id)"
                >
                  <div
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 font-semibold text-primary"
                  >
                    {{ record.club_id }}
                  </div>
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-medium text-slate-800">
                      社团 ID: {{ record.club_id }}
                    </p>
                    <p class="text-xs text-muted-foreground">
                      {{ getParticipationTypeLabel(record.participation_type) }}
                    </p>
                  </div>
                  <Badge variant="outline" class="shrink-0 text-[10px]">
                    {{ getAuditLabel(record.audit_status) }}
                  </Badge>
                </button>
              </div>
              <div
                v-else
                class="rounded-lg border border-dashed border-slate-200 p-8 text-center text-sm text-muted-foreground"
              >
                暂无社团参与记录
              </div>
            </CardContent>
          </Card>
        </div>

        <div class="space-y-6 lg:sticky lg:top-6 lg:h-fit">
          <Card class="border-slate-200/80 shadow-sm">
            <CardHeader>
              <CardTitle class="text-lg">活动摘要</CardTitle>
            </CardHeader>
            <CardContent class="space-y-3 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">活动编号</span>
                <span class="font-mono text-slate-700">#{{ activity.id }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">活动级别</span>
                <span class="text-slate-700">{{ getLevelLabel(activity.level) }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">所属学期</span>
                <span class="text-slate-700">{{
                  activity.academic_term?.term_name || '未设置'
                }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground">发布时间</span>
                <span class="text-slate-700">{{ formatDate(activity.created_at) }}</span>
              </div>
            </CardContent>
          </Card>

          <Card class="border-primary/20 bg-primary/5 shadow-sm">
            <CardHeader>
              <CardTitle class="text-base">管理提示</CardTitle>
            </CardHeader>
            <CardContent class="text-sm text-muted-foreground">
              你可以在社团管理页面中对大型活动申请进行创建与更新。若记录状态非待审核，将无法继续编辑。
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
import {
  auditStatusLabels,
  generalActivityLevelLabels,
  getEnumLabel,
  getGeneralActivityBadgeVariant,
  participationTypeLabels,
} from '@/lib/i18n/enumLabels';
import { formatError } from '@/lib/utils';

const route = useRoute();
const router = useRouter();
const activityId = Number(route.params.id);

const activity = ref<GeneralActivityInfo | null>(null);
const loading = ref(true);
const error = ref(false);
const errorMessage = ref('');
const participantCount = ref(0);
const approvedCount = ref(0);

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
      errorMessage.value = formatError(apiError, '获取活动详情失败');
    } else if (data) {
      activity.value = data;
      participantCount.value = Array.isArray(data.club_records) ? data.club_records.length : 0;
      approvedCount.value = Array.isArray(data.club_records)
        ? data.club_records.filter((record) => record.audit_status === 'approved').length
        : 0;
    }
  } catch (_err) {
    error.value = true;
    errorMessage.value = '请求出错，请重试';
  } finally {
    loading.value = false;
  }
};

const getBadgeVariant = (level: string) => getGeneralActivityBadgeVariant(level);

const getLevelLabel = (level: string) => getEnumLabel(generalActivityLevelLabels, level);

const getParticipationTypeLabel = (type: string) => getEnumLabel(participationTypeLabels, type);

const getAuditLabel = (status: string) => getEnumLabel(auditStatusLabels, status);

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
