<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  createClubGeneralActivitiesApiV1ClubsClubIdGeneralActivitiesPost,
  getClubGeneralActivitiesApiV1ClubsClubIdGeneralActivitiesGet,
  getClubInfoApiV1ClubsClubIdGet,
  getUserProfileApiV1UsersUserIdGet,
  listActivitiesApiV1GeneralActivitiesGet,
  updateClubGeneralActivitiesApiV1ClubsClubIdGeneralActivitiesPatch,
  updateClubInfoApiV1ClubsClubIdPatch,
  type ClubGeneralActivityInfo,
  type ClubInfo,
  type ClubMemberInfo,
  type GeneralActivityInfo,
  type ParticipationTypeEnum,
  type UserInfo,
} from '../../client';
import { useUserStore } from '../../lib/auth/userStore';
import {
  clubCategoryLabels,
  clubStatusLabels,
  getEnumLabel,
  membershipLabels,
} from '../../lib/i18n/enumLabels';
import { formatError } from '../../lib/utils';
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
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from '../../components/ui/sidebar';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const clubId = computed(() => Number(route.params.id));

const loading = ref(true);
const error = ref('');
const club = ref<ClubInfo | null>(null);

const savingClubInfo = ref(false);
const clubMessage = ref('');
const clubMessageIsError = ref(false);
const clubForm = reactive({
  summary: '',
  description: '',
  logo_uri: '',
});

const membersProfileCache = ref<Record<number, UserInfo | null>>({});
const membersProfileLoading = ref(false);
const membersProfileError = ref('');
const memberFilter = ref<'all' | ClubMemberInfo['membership']>('all');
const memberKeyword = ref('');
const memberPage = ref(1);
const memberPageSize = 20;

const recordsLoading = ref(false);
const recordsError = ref('');
const records = ref<ClubGeneralActivityInfo[]>([]);

const recordDisplayStatus = ref<'all' | 'pending' | 'approved' | 'rejected'>('all');
const recordDisplayParticipation = ref<'all' | ParticipationTypeEnum>('all');

const activitiesLoading = ref(false);
const activitiesError = ref('');
const activities = ref<GeneralActivityInfo[]>([]);
const activitySearch = ref('');
const activityLevelFilter = ref<'all' | GeneralActivityInfo['level']>('all');

const clubManageSections = [
  { id: 'club-overview', label: '社团概览' },
  { id: 'club-info-edit', label: '信息编辑' },
  { id: 'club-members', label: '成员管理' },
  { id: 'club-records', label: '活动申请' },
] as const;

type ClubManageSectionId = (typeof clubManageSections)[number]['id'];
const defaultClubSection: ClubManageSectionId = 'club-overview';

function isClubSectionId(value: string): value is ClubManageSectionId {
  return clubManageSections.some((section) => section.id === value);
}

const activeClubSection = computed<ClubManageSectionId>(() => {
  const section = route.query.section;
  if (typeof section === 'string' && isClubSectionId(section)) {
    return section;
  }
  return defaultClubSection;
});

const createSubmitting = ref(false);
const createMessage = ref('');
const createMessageIsError = ref(false);
const createForm = reactive<{
  activity_id: number | null;
  participation_type: ParticipationTypeEnum;
  requested_score: number;
  proof_files_text: string;
}>({
  activity_id: null,
  participation_type: 'participate_only',
  requested_score: 0,
  proof_files_text: '',
});

const editingRecordId = ref<number | null>(null);
const updateSubmitting = ref(false);
const updateMessage = ref('');
const updateMessageIsError = ref(false);
const updateForm = reactive<{
  activity_id: number;
  participation_type: ParticipationTypeEnum;
  requested_score: number;
  proof_files_text: string;
}>({
  activity_id: 0,
  participation_type: 'participate_only',
  requested_score: 0,
  proof_files_text: '',
});

const auditTextMap = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝',
} as const;

const participationTextMap: Record<ParticipationTypeEnum, string> = {
  participate_only: '仅参与',
  organize: '组织者',
};

const myMembership = computed<ClubMemberInfo['membership'] | null>(() => {
  const myUserId = userStore.userInfo?.id;
  if (!myUserId || !club.value) return null;
  const member = club.value.members.find((m) => m.user_id === myUserId);
  return member?.membership ?? null;
});

const canManageClub = computed(() => {
  const role = userStore.userInfo?.role;
  if (role === 'dev' || role === 'admin') return true;
  return myMembership.value === 'president';
});

const filteredMembers = computed(() => {
  if (!club.value) return [];

  let items = club.value.members;
  if (memberFilter.value !== 'all') {
    items = items.filter((member) => member.membership === memberFilter.value);
  }

  const keyword = memberKeyword.value.trim().toLowerCase();
  if (!keyword) return items;

  return items.filter((member) => {
    const profile = membersProfileCache.value[member.user_id];
    const username = profile?.username?.toLowerCase() || '';
    return String(member.user_id).includes(keyword) || username.includes(keyword);
  });
});

const totalMemberPages = computed(() => {
  const total = Math.ceil(filteredMembers.value.length / memberPageSize);
  return Math.max(1, total);
});

const pagedMembers = computed(() => {
  const start = (memberPage.value - 1) * memberPageSize;
  return filteredMembers.value.slice(start, start + memberPageSize);
});

const filteredRecords = computed(() => {
  let items = records.value;
  if (recordDisplayStatus.value !== 'all') {
    items = items.filter((record) => record.audit_status === recordDisplayStatus.value);
  }
  if (recordDisplayParticipation.value !== 'all') {
    items = items.filter(
      (record) => record.participation_type === recordDisplayParticipation.value,
    );
  }
  return items;
});

function getMembershipText(membership: ClubMemberInfo['membership']) {
  return getEnumLabel(membershipLabels, membership);
}

function getAuditText(status: ClubGeneralActivityInfo['audit_status']) {
  return auditTextMap[status as keyof typeof auditTextMap] || status;
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getMemberName(userId: number) {
  return membersProfileCache.value[userId]?.username || `用户 #${userId}`;
}

function getActivityNameById(activityId: number) {
  return (
    activities.value.find((activity) => activity.id === activityId)?.name || `活动 #${activityId}`
  );
}

function parseProofFiles(input: string) {
  const files = input
    .split(/\r?\n|,|;/)
    .map((item) => item.trim())
    .filter(Boolean);
  return files.length > 0 ? files : null;
}

async function fetchClubInfo() {
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
      error.value = formatError(fetchError, '获取社团信息失败');
      return;
    }

    if (!data) {
      error.value = '社团信息为空';
      return;
    }

    club.value = data;
    clubForm.summary = data.summary;
    clubForm.description = data.description;
    clubForm.logo_uri = data.logo_uri || '';
  } catch (err: any) {
    error.value = err?.message || '获取社团信息失败';
  } finally {
    loading.value = false;
  }
}

async function fetchClubRecords() {
  recordsLoading.value = true;
  recordsError.value = '';
  try {
    const { data, error: fetchError } =
      await getClubGeneralActivitiesApiV1ClubsClubIdGeneralActivitiesGet({
        path: { club_id: clubId.value },
      });
    if (fetchError) {
      recordsError.value = formatError(fetchError, '获取大型活动申请记录失败');
      return;
    }
    records.value = Array.isArray(data) ? data : [];
  } catch (err: any) {
    recordsError.value = err?.message || '获取大型活动申请记录失败';
  } finally {
    recordsLoading.value = false;
  }
}

async function fetchActivities() {
  activitiesLoading.value = true;
  activitiesError.value = '';

  try {
    const { data, error: fetchError } = await listActivitiesApiV1GeneralActivitiesGet({
      query: {
        search: activitySearch.value.trim() || null,
        level: activityLevelFilter.value === 'all' ? null : activityLevelFilter.value,
      },
    });

    if (fetchError) {
      activitiesError.value = formatError(fetchError, '获取大型活动列表失败');
      return;
    }

    activities.value = Array.isArray(data) ? data : [];
  } catch (err: any) {
    activitiesError.value = err?.message || '获取大型活动列表失败';
  } finally {
    activitiesLoading.value = false;
  }
}

async function ensureMemberProfiles(members: ClubMemberInfo[]) {
  const missingIds = members
    .map((member) => member.user_id)
    .filter((id) => !(id in membersProfileCache.value));

  if (missingIds.length === 0) return;

  membersProfileLoading.value = true;
  membersProfileError.value = '';

  try {
    const results = await Promise.all(
      missingIds.map(async (userId) => {
        const { data, error: fetchError } = await getUserProfileApiV1UsersUserIdGet({
          path: { user_id: userId },
        });
        if (fetchError) {
          throw new Error(formatError(fetchError, `获取用户 ${userId} 信息失败`));
        }
        return { userId, data: data ?? null };
      }),
    );

    for (const item of results) {
      membersProfileCache.value[item.userId] = item.data;
    }
  } catch (err: any) {
    membersProfileError.value = err?.message || '加载成员资料失败';
  } finally {
    membersProfileLoading.value = false;
  }
}

async function saveClubInfo() {
  if (!club.value || !canManageClub.value || savingClubInfo.value) return;

  savingClubInfo.value = true;
  clubMessage.value = '';

  try {
    const { data, error: saveError } = await updateClubInfoApiV1ClubsClubIdPatch({
      path: { club_id: club.value.id },
      body: {
        summary: clubForm.summary,
        description: clubForm.description,
        logo_uri: clubForm.logo_uri.trim() || null,
      },
    });

    if (saveError) {
      clubMessage.value = formatError(saveError, '更新社团信息失败');
      clubMessageIsError.value = true;
      return;
    }

    if (data) {
      club.value = data;
    }
    clubMessage.value = '社团信息已更新';
    clubMessageIsError.value = false;
  } catch (err: any) {
    clubMessage.value = err?.message || '更新社团信息失败';
    clubMessageIsError.value = true;
  } finally {
    savingClubInfo.value = false;
  }
}

async function createRecord() {
  if (!club.value || !canManageClub.value || createSubmitting.value || !createForm.activity_id) {
    return;
  }

  createSubmitting.value = true;
  createMessage.value = '';

  try {
    const { error: createError } =
      await createClubGeneralActivitiesApiV1ClubsClubIdGeneralActivitiesPost({
        path: { club_id: club.value.id },
        body: {
          activity_id: createForm.activity_id,
          participation_type: createForm.participation_type,
          requested_score: createForm.requested_score,
          proof_files: parseProofFiles(createForm.proof_files_text),
        },
      });

    if (createError) {
      createMessage.value = formatError(createError, '创建大型活动申请失败');
      createMessageIsError.value = true;
      return;
    }

    createMessage.value = '已创建大型活动申请';
    createMessageIsError.value = false;
    createForm.activity_id = null;
    createForm.requested_score = 0;
    createForm.participation_type = 'participate_only';
    createForm.proof_files_text = '';
    await fetchClubRecords();
  } catch (err: any) {
    createMessage.value = err?.message || '创建大型活动申请失败';
    createMessageIsError.value = true;
  } finally {
    createSubmitting.value = false;
  }
}

function beginEditRecord(record: ClubGeneralActivityInfo) {
  editingRecordId.value = record.id;
  updateMessage.value = '';
  updateForm.activity_id = record.activity_id;
  updateForm.participation_type = record.participation_type;
  updateForm.requested_score = record.requested_score;
  updateForm.proof_files_text = record.proof_files.join('\n');
}

function cancelEditRecord() {
  editingRecordId.value = null;
}

async function updateRecord() {
  if (
    !club.value ||
    !canManageClub.value ||
    updateSubmitting.value ||
    editingRecordId.value === null
  ) {
    return;
  }

  updateSubmitting.value = true;
  updateMessage.value = '';

  try {
    const { error: updateError } =
      await updateClubGeneralActivitiesApiV1ClubsClubIdGeneralActivitiesPatch({
        path: { club_id: club.value.id },
        body: {
          activity_id: updateForm.activity_id,
          participation_type: updateForm.participation_type,
          requested_score: updateForm.requested_score,
          proof_files: parseProofFiles(updateForm.proof_files_text),
        },
      });

    if (updateError) {
      updateMessage.value = formatError(updateError, '更新大型活动申请失败');
      updateMessageIsError.value = true;
      return;
    }

    updateMessage.value = '大型活动申请已更新';
    updateMessageIsError.value = false;
    editingRecordId.value = null;
    await fetchClubRecords();
  } catch (err: any) {
    updateMessage.value = err?.message || '更新大型活动申请失败';
    updateMessageIsError.value = true;
  } finally {
    updateSubmitting.value = false;
  }
}

function goBackToClub() {
  if (!Number.isInteger(clubId.value) || clubId.value <= 0) {
    void router.push('/');
    return;
  }
  void router.push({ name: 'ClubDetail', params: { id: clubId.value } });
}

function setClubSection(sectionId: ClubManageSectionId) {
  void router.replace({
    query: {
      ...route.query,
      section: sectionId,
    },
  });
}

watch([memberFilter, memberKeyword], () => {
  memberPage.value = 1;
});

watch(
  pagedMembers,
  (members) => {
    if (members.length > 0) {
      void ensureMemberProfiles(members);
    }
  },
  { immediate: false },
);

onMounted(async () => {
  if (userStore.isLogin && !userStore.userInfo) {
    await userStore.fetchUser();
  }

  await Promise.all([fetchClubInfo(), fetchClubRecords(), fetchActivities()]);
  if (pagedMembers.value.length > 0) {
    await ensureMemberProfiles(pagedMembers.value);
  }

  if (!route.query.section || !isClubSectionId(String(route.query.section))) {
    setClubSection(defaultClubSection);
  }
});
</script>

<template>
  <div class="space-y-6">
    <Card class="border-slate-200/80 shadow-lg">
      <CardHeader class="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle class="text-2xl">社团管理</CardTitle>
          <CardDescription>管理社团信息、成员列表与大型活动申请记录</CardDescription>
        </div>
        <Button variant="outline" @click="goBackToClub">返回社团详情</Button>
      </CardHeader>

      <CardContent>
        <div
          v-if="loading"
          class="rounded-2xl border border-dashed border-slate-200 p-6 text-slate-500"
        >
          正在加载社团信息...
        </div>

        <div
          v-else-if="error"
          class="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-600"
        >
          {{ error }}
        </div>

        <div v-else-if="club" class="w-full">
          <SidebarProvider
            class="w-full min-h-[calc(100vh-16rem)] items-stretch rounded-2xl border border-slate-200"
          >
            <Sidebar collapsible="none" class="h-full border-r border-slate-200 bg-white">
              <SidebarContent>
                <SidebarGroup>
                  <SidebarGroupLabel>社团管理导航</SidebarGroupLabel>
                  <SidebarGroupContent>
                    <SidebarMenu>
                      <SidebarMenuItem v-for="section in clubManageSections" :key="section.id">
                        <SidebarMenuButton
                          :is-active="activeClubSection === section.id"
                          @click="setClubSection(section.id)"
                        >
                          <span>{{ section.label }}</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    </SidebarMenu>
                  </SidebarGroupContent>
                </SidebarGroup>
              </SidebarContent>
            </Sidebar>

            <SidebarInset
              class="h-full bg-transparent p-5 md:peer-data-[variant=inset]:m-0 md:peer-data-[variant=inset]:ml-0 md:peer-data-[variant=inset]:rounded-none md:peer-data-[variant=inset]:shadow-none"
            >
              <div class="space-y-6">
                <div
                  v-if="activeClubSection === 'club-overview'"
                  id="club-overview"
                  class="rounded-2xl border border-slate-200 bg-slate-50/60 p-5"
                >
                  <div class="flex flex-wrap items-center gap-2">
                    <h2 class="text-xl font-semibold text-slate-900">{{ club.name }}</h2>
                    <Badge variant="outline"
                      >分类: {{ getEnumLabel(clubCategoryLabels, club.category) }}</Badge
                    >
                    <Badge variant="outline"
                      >状态: {{ getEnumLabel(clubStatusLabels, club.status) }}</Badge
                    >
                    <Badge variant="outline"
                      >我的身份:
                      {{
                        myMembership ? getEnumLabel(membershipLabels, myMembership) : '非成员'
                      }}</Badge
                    >
                  </div>
                </div>

                <Card
                  v-if="activeClubSection === 'club-info-edit'"
                  id="club-info-edit"
                  class="border-slate-200"
                >
                  <CardHeader>
                    <CardTitle>社团信息编辑</CardTitle>
                    <CardDescription>可编辑简介、详情与社团 Logo 链接</CardDescription>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div class="grid gap-4 md:grid-cols-2">
                      <label class="space-y-1 text-sm text-slate-700">
                        <span>社团简介</span>
                        <input
                          v-model="clubForm.summary"
                          :disabled="!canManageClub || savingClubInfo"
                          class="w-full rounded-md border border-slate-200 px-3 py-2"
                          placeholder="请输入社团简介"
                        />
                      </label>
                      <label class="space-y-1 text-sm text-slate-700">
                        <span>Logo 链接</span>
                        <input
                          v-model="clubForm.logo_uri"
                          :disabled="!canManageClub || savingClubInfo"
                          class="w-full rounded-md border border-slate-200 px-3 py-2"
                          placeholder="https://..."
                        />
                      </label>
                    </div>

                    <label class="space-y-1 text-sm text-slate-700 block">
                      <span>社团详情</span>
                      <textarea
                        v-model="clubForm.description"
                        :disabled="!canManageClub || savingClubInfo"
                        class="min-h-28 w-full rounded-md border border-slate-200 px-3 py-2"
                        placeholder="请输入社团详情"
                      />
                    </label>

                    <div
                      v-if="clubMessage"
                      :class="[
                        'rounded-md border px-3 py-2 text-sm',
                        clubMessageIsError
                          ? 'border-rose-200 bg-rose-50 text-rose-600'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                      ]"
                    >
                      {{ clubMessage }}
                    </div>

                    <Button :disabled="!canManageClub || savingClubInfo" @click="saveClubInfo">
                      {{ savingClubInfo ? '保存中...' : '保存社团信息' }}
                    </Button>
                  </CardContent>
                </Card>

                <Card
                  v-if="activeClubSection === 'club-members'"
                  id="club-members"
                  class="border-slate-200"
                >
                  <CardHeader>
                    <CardTitle>社团成员</CardTitle>
                    <CardDescription>20 人/页，支持按身份与关键词筛选</CardDescription>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div class="grid gap-3 md:grid-cols-3">
                      <label class="space-y-1 text-sm">
                        <span>身份筛选</span>
                        <select
                          v-model="memberFilter"
                          class="w-full rounded-md border border-slate-200 px-3 py-2"
                        >
                          <option value="all">全部</option>
                          <option value="president">社长</option>
                          <option value="vice president">副社长</option>
                          <option value="member">成员</option>
                          <option value="pending">待审核</option>
                          <option value="left">已退出</option>
                        </select>
                      </label>

                      <label class="space-y-1 text-sm md:col-span-2">
                        <span>关键词（用户名 / 用户 ID）</span>
                        <input
                          v-model="memberKeyword"
                          class="w-full rounded-md border border-slate-200 px-3 py-2"
                          placeholder="输入关键词"
                        />
                      </label>
                    </div>

                    <div
                      v-if="membersProfileError"
                      class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700"
                    >
                      {{ membersProfileError }}
                    </div>

                    <ScrollArea class="max-h-[380px] pr-3">
                      <div class="space-y-2">
                        <div
                          v-for="member in pagedMembers"
                          :key="member.id"
                          class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2"
                        >
                          <div class="min-w-0">
                            <div class="truncate font-medium text-slate-900">
                              {{ getMemberName(member.user_id) }}
                            </div>
                            <div class="text-xs text-slate-500">
                              用户ID: {{ member.user_id }} · 更新时间:
                              {{ formatDateTime(member.updated_at) }}
                            </div>
                          </div>
                          <Badge variant="outline">{{
                            getMembershipText(member.membership)
                          }}</Badge>
                        </div>

                        <div
                          v-if="pagedMembers.length === 0"
                          class="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500"
                        >
                          无成员数据
                        </div>
                      </div>
                    </ScrollArea>

                    <div class="flex items-center justify-between text-sm">
                      <span class="text-slate-500"
                        >第 {{ memberPage }} / {{ totalMemberPages }} 页</span
                      >
                      <div class="flex items-center gap-2">
                        <Button
                          variant="outline"
                          :disabled="memberPage <= 1"
                          @click="memberPage -= 1"
                          >上一页</Button
                        >
                        <Button
                          variant="outline"
                          :disabled="memberPage >= totalMemberPages"
                          @click="memberPage += 1"
                          >下一页</Button
                        >
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card
                  v-if="activeClubSection === 'club-records'"
                  id="club-records"
                  class="border-slate-200"
                >
                  <CardHeader>
                    <CardTitle>大型活动申请管理</CardTitle>
                  </CardHeader>
                  <CardContent class="space-y-5">
                    <div class="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-4">
                      <div class="grid gap-3 md:grid-cols-3">
                        <label class="space-y-1 text-sm">
                          <span>活动搜索</span>
                          <input
                            v-model="activitySearch"
                            class="w-full rounded-md border border-slate-200 px-3 py-2"
                            placeholder="输入活动关键词"
                          />
                        </label>
                        <label class="space-y-1 text-sm">
                          <span>活动级别</span>
                          <select
                            v-model="activityLevelFilter"
                            class="w-full rounded-md border border-slate-200 px-3 py-2"
                          >
                            <option value="all">全部</option>
                            <option value="sua">社联活动</option>
                            <option value="school">校级活动</option>
                            <option value="large">大型活动</option>
                          </select>
                        </label>
                        <div class="flex items-end">
                          <Button
                            variant="outline"
                            :disabled="activitiesLoading"
                            @click="fetchActivities"
                          >
                            {{ activitiesLoading ? '加载中...' : '刷新活动列表' }}
                          </Button>
                        </div>
                      </div>

                      <div
                        v-if="activitiesError"
                        class="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-600"
                      >
                        {{ activitiesError }}
                      </div>

                      <div class="grid gap-3 md:grid-cols-2">
                        <label class="space-y-1 text-sm">
                          <span>选择大型活动</span>
                          <select
                            v-model="createForm.activity_id"
                            :disabled="!canManageClub || createSubmitting"
                            class="w-full rounded-md border border-slate-200 px-3 py-2"
                          >
                            <option :value="null">请选择活动</option>
                            <option
                              v-for="activity in activities"
                              :key="activity.id"
                              :value="activity.id"
                            >
                              {{ activity.name }}
                            </option>
                          </select>
                        </label>

                        <label class="space-y-1 text-sm">
                          <span>参与方式</span>
                          <select
                            v-model="createForm.participation_type"
                            :disabled="!canManageClub || createSubmitting"
                            class="w-full rounded-md border border-slate-200 px-3 py-2"
                          >
                            <option value="participate_only">仅参与</option>
                            <option value="organize">组织者</option>
                          </select>
                        </label>

                        <label class="space-y-1 text-sm">
                          <span>申请分值</span>
                          <input
                            v-model.number="createForm.requested_score"
                            type="number"
                            min="0"
                            step="0.5"
                            :disabled="!canManageClub || createSubmitting"
                            class="w-full rounded-md border border-slate-200 px-3 py-2"
                          />
                        </label>

                        <label class="space-y-1 text-sm md:col-span-2">
                          <span>证明材料（每行一个 URL）</span>
                          <textarea
                            v-model="createForm.proof_files_text"
                            :disabled="!canManageClub || createSubmitting"
                            class="min-h-20 w-full rounded-md border border-slate-200 px-3 py-2"
                            placeholder="https://..."
                          />
                        </label>
                      </div>

                      <div
                        v-if="createMessage"
                        :class="[
                          'rounded-md border px-3 py-2 text-sm',
                          createMessageIsError
                            ? 'border-rose-200 bg-rose-50 text-rose-600'
                            : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                        ]"
                      >
                        {{ createMessage }}
                      </div>

                      <Button
                        :disabled="!canManageClub || createSubmitting || !createForm.activity_id"
                        @click="createRecord"
                      >
                        {{ createSubmitting ? '创建中...' : '创建申请' }}
                      </Button>
                    </div>

                    <div class="grid gap-3 md:grid-cols-2">
                      <label class="space-y-1 text-sm">
                        <span>展示状态</span>
                        <select
                          v-model="recordDisplayStatus"
                          class="w-full rounded-md border border-slate-200 px-3 py-2"
                        >
                          <option value="all">全部</option>
                          <option value="pending">待审核</option>
                          <option value="approved">已通过</option>
                          <option value="rejected">已拒绝</option>
                        </select>
                      </label>

                      <label class="space-y-1 text-sm">
                        <span>展示参与方式</span>
                        <select
                          v-model="recordDisplayParticipation"
                          class="w-full rounded-md border border-slate-200 px-3 py-2"
                        >
                          <option value="all">全部</option>
                          <option value="participate_only">仅参与</option>
                          <option value="organize">组织者</option>
                        </select>
                      </label>
                    </div>

                    <div
                      v-if="recordsError"
                      class="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-600"
                    >
                      {{ recordsError }}
                    </div>
                    <div
                      v-if="updateMessage"
                      :class="[
                        'rounded-md border px-3 py-2 text-sm',
                        updateMessageIsError
                          ? 'border-rose-200 bg-rose-50 text-rose-600'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                      ]"
                    >
                      {{ updateMessage }}
                    </div>

                    <div
                      v-if="recordsLoading"
                      class="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500"
                    >
                      正在加载申请记录...
                    </div>

                    <div v-else class="space-y-3">
                      <div
                        v-for="record in filteredRecords"
                        :key="record.id"
                        class="rounded-xl border border-slate-200 bg-white p-4"
                      >
                        <div class="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <div class="font-medium text-slate-900">
                              {{ getActivityNameById(record.activity_id) }}
                            </div>
                            <div class="text-xs text-slate-500">
                              申请时间: {{ formatDateTime(record.created_at) }}
                            </div>
                          </div>
                          <div class="flex items-center gap-2">
                            <Badge variant="outline">{{ getAuditText(record.audit_status) }}</Badge>
                            <Badge variant="outline">{{
                              participationTextMap[record.participation_type]
                            }}</Badge>
                            <Badge variant="outline">申请分: {{ record.requested_score }}</Badge>
                          </div>
                        </div>

                        <div class="mt-3 text-sm text-slate-700">
                          <div>
                            证明材料：{{
                              record.proof_files.length ? `${record.proof_files.length} 项` : '无'
                            }}
                          </div>
                        </div>

                        <div
                          v-if="canManageClub && record.audit_status === 'pending'"
                          class="mt-3 flex items-center gap-2"
                        >
                          <Button variant="outline" @click="beginEditRecord(record)"
                            >编辑待审核记录</Button
                          >
                        </div>

                        <div
                          v-if="editingRecordId === record.id"
                          class="mt-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3 space-y-3"
                        >
                          <label class="space-y-1 text-sm block">
                            <span>参与方式</span>
                            <select
                              v-model="updateForm.participation_type"
                              class="w-full rounded-md border border-slate-200 px-3 py-2"
                            >
                              <option value="participate_only">仅参与</option>
                              <option value="organize">组织者</option>
                            </select>
                          </label>

                          <label class="space-y-1 text-sm block">
                            <span>申请分值</span>
                            <input
                              v-model.number="updateForm.requested_score"
                              type="number"
                              min="0"
                              step="0.5"
                              class="w-full rounded-md border border-slate-200 px-3 py-2"
                            />
                          </label>

                          <label class="space-y-1 text-sm block">
                            <span>证明材料（每行一个 URL）</span>
                            <textarea
                              v-model="updateForm.proof_files_text"
                              class="min-h-20 w-full rounded-md border border-slate-200 px-3 py-2"
                            />
                          </label>

                          <div class="flex items-center gap-2">
                            <Button :disabled="updateSubmitting" @click="updateRecord">
                              {{ updateSubmitting ? '保存中...' : '保存修改' }}
                            </Button>
                            <Button
                              variant="outline"
                              :disabled="updateSubmitting"
                              @click="cancelEditRecord"
                            >
                              取消
                            </Button>
                          </div>
                        </div>
                      </div>

                      <div
                        v-if="filteredRecords.length === 0"
                        class="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-500"
                      >
                        当前筛选下无申请记录
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </SidebarInset>
          </SidebarProvider>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
