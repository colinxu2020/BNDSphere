<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  getClubActivitiesApiV1ClubsClubIdActivitiesGet,
  getClubInfoApiV1ClubsClubIdGet,
  getUserProfileApiV1UsersUserIdGet,
  joinClubApiV1ClubsClubIdMembersPost,
  leaveClubApiV1ClubsClubIdMembersMeDelete,
  type ActivityInfo,
  type ClubInfo,
  type ClubMemberInfo,
  type UserInfo,
} from '../../client';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { ScrollArea } from '../../components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import { formatError } from '../../lib/utils';
import { useUserStore } from '../../lib/auth/userStore';

const route = useRoute();
const router = useRouter();
const loading = ref(true);
const activityLoading = ref(true);
const error = ref('');
const activityError = ref('');
const club = ref<ClubInfo | null>(null);
const activities = ref<ActivityInfo[]>([]);
const actionLoading = ref<'join' | 'leave' | ''>('');
const actionMessage = ref('');
const actionMessageIsError = ref(false);
const membersDialogOpen = ref(false);
const membersLoading = ref(false);
const membersError = ref('');
const memberProfiles = ref<Record<number, UserInfo | null>>({});
const userStore = useUserStore();
const havePermissionToEdit = computed(() => {
  const role = userStore.userInfo?.role;
  if (role === 'admin' || role === 'dev') {
    return true;
  }

  const currentUserId = userStore.userInfo?.id;
  let havePermission = false;
  for (const member of club.value?.members || []) {
    if (member.user_id === currentUserId && member.membership === 'president') {
      havePermission = true;
    }
  }
  return havePermission;
});
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

const membershipTextMap = {
  pending: '待审核',
  member: '成员',
  president: '社长',
  'vice president': '副社长',
  left: '已退出',
} as const;

const membershipClassMap = {
  pending: 'border-amber-200 bg-amber-50 text-amber-700',
  member: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  president: 'border-indigo-200 bg-indigo-50 text-indigo-700',
  'vice president': 'border-cyan-200 bg-cyan-50 text-cyan-700',
  left: 'border-slate-200 bg-slate-50 text-slate-600',
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

const myMembership = computed<ClubMemberInfo['membership'] | null>(() => {
  const currentUserId = userStore.userInfo?.id;
  if (!currentUserId || !club.value) return null;
  const mine = club.value.members.find((member) => member.user_id === currentUserId);
  return mine?.membership ?? null;
});

const canJoinClub = computed(() => {
  if (!myMembership.value) return true;
  return myMembership.value === 'left';
});

const canLeaveClub = computed(() => {
  return myMembership.value === 'member' || myMembership.value === 'vice president';
});

const sortedMembers = computed(() => {
  if (!club.value) return [];

  const priority: Record<ClubMemberInfo['membership'], number> = {
    president: 0,
    'vice president': 1,
    member: 2,
    pending: 3,
    left: 4,
  };

  return [...club.value.members].sort((a, b) => {
    const byRole = priority[a.membership] - priority[b.membership];
    if (byRole !== 0) return byRole;
    return b.updated_at.localeCompare(a.updated_at);
  });
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

function resolveActivityStatus(activity: ActivityInfo) {
  const status = (activity as ActivityInfo & { status?: string }).status;
  if (!status) return 'upcoming';
  return status;
}

function getActivityStatusText(status: string) {
  return activityStatusTextMap[status as keyof typeof activityStatusTextMap] || status;
}

function getActivityStatusClass(status: string) {
  return activityStatusClassMap[status as keyof typeof activityStatusClassMap] || '';
}

function getMembershipText(membership: ClubMemberInfo['membership']) {
  return membershipTextMap[membership as keyof typeof membershipTextMap] || membership;
}

function getMembershipClass(membership: ClubMemberInfo['membership']) {
  return membershipClassMap[membership as keyof typeof membershipClassMap] || 'border-slate-200';
}

function getMemberDisplayName(userId: number) {
  const profile = memberProfiles.value[userId];
  if (profile?.username) return profile.username;
  return `用户 #${userId}`;
}

function getMemberAvatar(userId: number) {
  const profile = memberProfiles.value[userId];
  return profile?.avatar_uri || '';
}

async function fetchMemberProfilesForDialog() {
  if (!club.value || club.value.members.length === 0) {
    membersError.value = '';
    return;
  }

  const userIds = Array.from(new Set(club.value.members.map((member) => member.user_id)));
  const missingIds = userIds.filter((id) => !(id in memberProfiles.value));

  if (missingIds.length === 0) {
    return;
  }

  membersLoading.value = true;
  membersError.value = '';

  try {
    const results = await Promise.all(
      missingIds.map(async (userId) => {
        const { data, error: fetchError } = await getUserProfileApiV1UsersUserIdGet({
          path: { user_id: userId },
        });
        if (fetchError) {
          throw new Error(formatError(fetchError, `获取用户 ${userId} 资料失败`));
        }
        return { userId, profile: data ?? null };
      }),
    );

    for (const item of results) {
      memberProfiles.value[item.userId] = item.profile;
    }
  } catch (err: any) {
    membersError.value = err?.message || '加载成员资料失败';
  } finally {
    membersLoading.value = false;
  }
}

async function handleJoinClub() {
  if (!Number.isInteger(clubId.value) || clubId.value <= 0 || actionLoading.value) {
    return;
  }

  actionLoading.value = 'join';
  actionMessage.value = '';

  try {
    const { error: joinError } = await joinClubApiV1ClubsClubIdMembersPost({
      path: { club_id: clubId.value },
    });

    if (joinError) {
      actionMessage.value = formatError(joinError, '加入社团失败');
      actionMessageIsError.value = true;
      return;
    }

    actionMessage.value = '已提交加入社团请求';
    actionMessageIsError.value = false;
    await fetchClubDetail();
  } catch (err: any) {
    actionMessage.value = err?.message || '加入社团失败';
    actionMessageIsError.value = true;
  } finally {
    actionLoading.value = '';
  }
}

async function handleLeaveClub() {
  if (!Number.isInteger(clubId.value) || clubId.value <= 0 || actionLoading.value) {
    return;
  }

  actionLoading.value = 'leave';
  actionMessage.value = '';

  try {
    const { error: leaveError } = await leaveClubApiV1ClubsClubIdMembersMeDelete({
      path: { club_id: clubId.value },
    });

    if (leaveError) {
      actionMessage.value = formatError(leaveError, '离开社团失败');
      actionMessageIsError.value = true;
      return;
    }

    actionMessage.value = '你已离开该社团';
    actionMessageIsError.value = false;
    await fetchClubDetail();
  } catch (err: any) {
    actionMessage.value = err?.message || '离开社团失败';
    actionMessageIsError.value = true;
  } finally {
    actionLoading.value = '';
  }
}

function goToManagePage() {
  if (!Number.isInteger(clubId.value) || clubId.value <= 0) {
    return;
  }
  void router.push({ name: 'ClubManage', params: { id: clubId.value } });
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

watch(
  membersDialogOpen,
  (open) => {
    if (open) {
      void fetchMemberProfilesForDialog();
    }
  },
  { immediate: false },
);
</script>

<template>
  <div class="space-y-6">
    <Card class="overflow-hidden border-slate-200/80 shadow-lg">
      <div class="px-6 py-6 flex flex-row">
        <div class="from-slate-900 via-slate-800 to-slate-700">
          <CardDescription class="text-gray-500">Club ID: {{ route.params.id }}</CardDescription>
          <CardTitle class="mt-2 text-3xl font-bold tracking-tight">社团详情</CardTitle>
        </div>
        <div class="ml-auto flex items-center gap-4">
          <Button variant="outline" @click="membersDialogOpen = true">查看成员</Button>
          <Button v-if="canJoinClub" :disabled="actionLoading === 'join'" @click="handleJoinClub">
            {{ actionLoading === 'join' ? '加入中...' : '加入社团' }}
          </Button>
          <Button
            v-else-if="canLeaveClub"
            variant="destructive"
            :disabled="actionLoading === 'leave'"
            @click="handleLeaveClub"
          >
            {{ actionLoading === 'leave' ? '提交中...' : '离开社团' }}
          </Button>
          <Button v-else-if="myMembership === 'pending'" disabled>审核中</Button>
          <Button v-else-if="myMembership === 'president'" disabled>社长不可离开</Button>
          <Badge v-else-if="myMembership === 'left'" variant="outline">已退出社团</Badge>
          <Button variant="outline" @click="goToManagePage" v-if="havePermissionToEdit">
            管理
          </Button>
        </div>
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

        <div
          v-if="actionMessage"
          :class="[
            'mb-4 rounded-2xl border p-4 text-sm',
            actionMessageIsError
              ? 'border-rose-200 bg-rose-50 text-rose-600'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700',
          ]"
        >
          {{ actionMessage }}
        </div>

        <div v-if="!loading && !error && club" class="grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
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
                      <Badge
                        :class="['border', getActivityStatusClass(resolveActivityStatus(activity))]"
                      >
                        {{ getActivityStatusText(resolveActivityStatus(activity)) }}
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

    <Dialog v-model:open="membersDialogOpen">
      <DialogContent class="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>社团成员</DialogTitle>
          <DialogDescription>
            共 {{ club?.members.length ?? 0 }} 人，按角色优先级展示。
          </DialogDescription>
        </DialogHeader>

        <div
          v-if="membersLoading"
          class="rounded-2xl border border-dashed border-slate-200 p-6 text-slate-500"
        >
          正在加载成员信息...
        </div>

        <div
          v-else-if="membersError"
          class="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-600"
        >
          {{ membersError }}
        </div>

        <div
          v-else-if="!club || club.members.length === 0"
          class="rounded-2xl border border-dashed border-slate-200 p-8 text-center text-slate-500"
        >
          当前社团暂无成员。
        </div>

        <ScrollArea v-else class="max-h-[60vh] pr-4">
          <div class="space-y-3">
            <div
              v-for="member in sortedMembers"
              :key="member.id"
              class="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50/70 p-4"
            >
              <div class="flex min-w-0 items-center gap-3">
                <Avatar class="h-10 w-10">
                  <AvatarImage
                    :src="getMemberAvatar(member.user_id)"
                    :alt="getMemberDisplayName(member.user_id)"
                  />
                  <AvatarFallback>
                    {{ getMemberDisplayName(member.user_id).slice(0, 1) }}
                  </AvatarFallback>
                </Avatar>
                <div class="min-w-0">
                  <div class="truncate text-sm font-semibold text-slate-900">
                    {{ getMemberDisplayName(member.user_id) }}
                  </div>
                  <div class="text-xs text-slate-500">用户 ID: {{ member.user_id }}</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <Badge :class="['border', getMembershipClass(member.membership)]">
                  {{ getMembershipText(member.membership) }}
                </Badge>
                <span class="text-xs text-slate-500">{{ formatDateTime(member.updated_at) }}</span>
              </div>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  </div>
</template>
