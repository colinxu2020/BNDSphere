<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import {
  getClubActivitiesApiV1ClubsClubIdActivitiesGet,
  getClubInfoApiV1ClubsClubIdGet,
  type ActivityInfo,
  type ClubInfo,
} from '../../client';
import { Badge } from '../../components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { ScrollArea } from '../../components/ui/scroll-area';
import { formatError } from '@/lib/utils';

const route = useRoute();
const loading = ref(true);
const activityLoading = ref(true);
const error = ref('');
const activityError = ref('');
const club = ref<ClubInfo | null>(null);
const activities = ref<ActivityInfo[]>([]);

const clubId = computed(() => Number(route.params.id));

const statusTextMap = {
  unreviewed: '未审核',
  approved: '已通过',
  rejected: '未通过',
} as const;

const starTextMap = {
  none: '无评级',
  one: '1 星',
  two: '2 星',
  three: '3 星',
} as const;

const activityStatusTextMap = {
  upcoming: '预告中',
  ongoing: '进行中',
  completed: '已结束',
  cancelled: '已取消',
} as const;

const activityStatusClassMap = {
  upcoming: 'border-sky-200 bg-sky-100 text-sky-700',
  ongoing: 'border-emerald-200 bg-emerald-100 text-emerald-700',
  completed: 'border-slate-200 bg-slate-100 text-slate-700',
  cancelled: 'border-rose-200 bg-rose-100 text-rose-700',
} as const;

const statusText = computed(() => {
  if (!club.value) return '';
  return getClubStatusText(club.value.status);
});

const starText = computed(() => {
  if (!club.value) return '';
  return getClubStarText(club.value.star_level);
});

const createdAtText = computed(() => {
  if (!club.value) return '';
  return new Date(club.value.created_at).toLocaleString('zh-CN');
});

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getClubStatusText(status: ClubInfo['status']) {
  return statusTextMap[status as keyof typeof statusTextMap] || status;
}

function getClubStarText(starLevel: ClubInfo['star_level']) {
  return starTextMap[starLevel as keyof typeof starTextMap] || starLevel;
}

function getActivityStatusText(status: ActivityInfo['status']) {
  return activityStatusTextMap[status as keyof typeof activityStatusTextMap] || status;
}

function getActivityStatusClass(status: ActivityInfo['status']) {
  return activityStatusClassMap[status as keyof typeof activityStatusClassMap] || '';
}

async function fetchClubDetail() {
  loading.value = true;
  error.value = '';

  if (!Number.isInteger(clubId.value) || clubId.value <= 0) {
    error.value = '社团 ID 非法';
    loading.value = false;
    return;
  }

  try {
    const { data, error: fetchError } = await getClubInfoApiV1ClubsClubIdGet({
      path: { club_id: clubId.value },
    });

    if (fetchError) {
      error.value = formatError(fetchError, '获取社团详情失败');
      return;
    }

    if (!data) {
      error.value = '获取社团详情为空';
      return;
    }

    club.value = data;
  } catch (err: any) {
    error.value = `请求异常: ${err.message || '获取社团详情失败'}`;
  } finally {
    loading.value = false;
  }
}

async function fetchClubActivities() {
  activityLoading.value = true;
  activityError.value = '';

  if (!Number.isInteger(clubId.value) || clubId.value <= 0) {
    activityError.value = '社团 ID 非法';
    activityLoading.value = false;
    return;
  }

  try {
    const { data, error: fetchError } = await getClubActivitiesApiV1ClubsClubIdActivitiesGet({
      path: { club_id: clubId.value },
      query: { offset: 0, limit: 20 },
    });

    if (fetchError) {
      activityError.value = formatError(fetchError, '获取社团活动失败');
      return;
    }

    activities.value = Array.isArray(data?.items) ? data.items : [];
  } catch (err: any) {
    activityError.value = `请求异常: ${err.message || '获取社团活动失败'}`;
  } finally {
    activityLoading.value = false;
  }
}

onMounted(() => {
  void Promise.all([fetchClubDetail(), fetchClubActivities()]);
});
</script>

<template>
  <div class="space-y-6">
    <Card class="overflow-hidden border-slate-200/80 shadow-lg">
      <div class="from-slate-900 via-slate-800 to-slate-700 px-6 py-6">
        <CardDescription class="text-gray-500">Club ID: {{ route.params.id }}</CardDescription>
        <CardTitle class="mt-2 text-3xl font-bold tracking-tight">社团详情</CardTitle>
      </div>

      <CardContent class="p-6">
        <div
          v-if="loading"
          class="rounded-2xl border border-dashed border-slate-200 p-8 text-slate-500"
        >
          正在加载社团信息...
        </div>

        <div
          v-else-if="error"
          class="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-600"
        >
          {{ error }}
        </div>

        <div v-else-if="club" class="grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
          <div class="space-y-6">
            <div
              class="flex items-start gap-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <img
                v-if="club.logo_uri"
                :src="club.logo_uri"
                :alt="club.name"
                class="h-24 w-24 rounded-2xl border object-cover"
              />
              <div class="min-w-0 flex-1 space-y-3">
                <div class="flex flex-wrap items-center gap-2">
                  <h1 class="text-2xl font-bold text-slate-900">{{ club.name }}</h1>
                  <Badge variant="secondary" class="capitalize">{{ club.category }}</Badge>
                </div>
                <p class="text-slate-600">{{ club.summary }}</p>
                <div class="flex flex-wrap gap-2">
                  <Badge variant="outline">状态: {{ statusText }}</Badge>
                  <Badge variant="outline">评级: {{ starText }}</Badge>
                  <Badge variant="outline">创建于 {{ createdAtText }}</Badge>
                </div>
              </div>
            </div>

            <div class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 class="mb-3 text-lg font-semibold text-slate-900">社团介绍</h2>
              <p class="whitespace-pre-line leading-7 text-slate-700">{{ club.description }}</p>
            </div>
          </div>

          <div class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div class="mb-4 flex items-center justify-between">
              <div>
                <h2 class="text-xl font-semibold text-slate-900">社团活动</h2>
                <p class="text-sm text-slate-500">查看近期活动安排、时间与状态</p>
              </div>
              <Badge variant="outline">{{ activities.length }} 项</Badge>
            </div>

            <div
              v-if="activityLoading"
              class="rounded-2xl border border-dashed border-slate-200 p-6 text-slate-500"
            >
              正在加载活动...
            </div>

            <div
              v-else-if="activityError"
              class="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-600"
            >
              {{ activityError }}
            </div>

            <div
              v-else-if="activities.length === 0"
              class="rounded-2xl border border-dashed border-slate-200 p-8 text-center text-slate-500"
            >
              暂无活动，社团可以先发布一个活动计划。
            </div>

            <ScrollArea v-else class="h-[540px] pr-4">
              <div class="space-y-4">
                <Card
                  v-for="activity in activities"
                  :key="activity.id"
                  class="border-slate-200 bg-slate-50/70 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                >
                  <CardHeader class="space-y-3 pb-3">
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0 space-y-1">
                        <CardTitle class="text-base text-slate-900">{{ activity.name }}</CardTitle>
                        <CardDescription class="text-slate-500">{{
                          activity.location
                        }}</CardDescription>
                      </div>
                      <Badge :class="['border', getActivityStatusClass(activity.status)]">
                        {{ getActivityStatusText(activity.status) }}
                      </Badge>
                    </div>
                    <div class="grid gap-2 text-sm text-slate-600">
                      <div>开始：{{ formatDateTime(activity.start_time) }}</div>
                      <div>结束：{{ formatDateTime(activity.end_time) }}</div>
                    </div>
                  </CardHeader>
                  <CardContent class="space-y-4 pt-0">
                    <p class="whitespace-pre-line text-sm leading-6 text-slate-700">
                      {{ activity.description }}
                    </p>
                    <div v-if="activity.picture_urls.length" class="space-y-3">
                      <div class="text-xs font-medium uppercase tracking-wide text-slate-500">
                        活动图片
                      </div>
                      <div class="flex gap-3 overflow-x-auto pb-1">
                        <img
                          v-for="(url, index) in activity.picture_urls"
                          :key="`${activity.id}-${index}`"
                          :src="url"
                          :alt="`${activity.name} 图片 ${index + 1}`"
                          class="h-20 w-28 shrink-0 rounded-xl border object-cover"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </ScrollArea>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
