<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  createApiV1AdminGeneralActivitiesPost,
  createTermApiV1AdminAcademicTermsPost,
  deleteApiV1AdminGeneralActivitiesActivityIdDelete,
  deleteTermApiV1AdminAcademicTermsTermIdDelete,
  getUserProfileApiV1UsersUserIdGet,
  listActivitiesApiV1GeneralActivitiesGet,
  listClubsApiV1ClubsGet,
  listTermsApiV1AdminAcademicTermsGet,
  setCurrentTermApiV1AdminAcademicTermsTermIdSetCurrentPost,
  updateApiV1AdminGeneralActivitiesActivityIdPatch,
  updateTermApiV1AdminAcademicTermsTermIdPatch,
  type ClubInfo,
  type GeneralActivityInfo,
  type RoleEnum,
} from '../../client';
import { useUserStore } from '../../lib/auth/userStore';
import { API_BASE_URL } from '../../lib/api';
import { formatError } from '../../lib/utils';
import {
  adminRoleLabels,
  clubStarLabels,
  clubStatusLabels,
  generalActivityLevelLabels,
  getEnumLabel,
} from '../../lib/i18n/enumLabels';
import { Button } from '../../components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
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

const userStore = useUserStore();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const globalError = ref('');

const canAccessAdmin = computed(() => {
  const role = userStore.userInfo?.role;
  return role === 'admin' || role === 'dev';
});

const activeAdminSection = computed<AdminSectionId>(() => {
  const section = route.query.section;
  if (typeof section === 'string' && isAdminSectionId(section)) {
    return section;
  }
  return defaultAdminSection;
});

const roleOptions: RoleEnum[] = ['ban', 'user', 'union of associations', 'admin', 'dev'];
const clubStatusOptions = ['unreviewed', 'normal', 'archived'];
const clubStarOptions = [
  'none',
  'one_star',
  'two_star',
  'three_star',
  'four_star',
  'five_star',
  'honorary',
];
const generalActivityLevelOptions = ['school', 'large', 'sua'];
const generalActivityLevelFilterOptions = ['all', ...generalActivityLevelOptions];

const adminSections = [
  { id: 'admin-users', label: '用户管理' },
  { id: 'admin-clubs', label: '社团管理' },
  { id: 'admin-terms', label: '学期管理' },
  { id: 'admin-activities', label: '大型活动管理' },
] as const;

type AdminSectionId = (typeof adminSections)[number]['id'];
const defaultAdminSection: AdminSectionId = 'admin-users';

function isAdminSectionId(value: string): value is AdminSectionId {
  return adminSections.some((section) => section.id === value);
}

const tokenHeader = computed(() => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
});

async function adminPatch<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const headers = new Headers({
    'Content-Type': 'application/json',
  });
  if (tokenHeader.value.Authorization) {
    headers.set('Authorization', tokenHeader.value.Authorization);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    let detail: string;
    try {
      const data = await response.json();
      detail = formatError(data, `请求失败 ${response.status}`);
    } catch {
      detail = `请求失败 ${response.status}`;
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

const userManage = reactive({
  userIdInput: '',
  loading: false,
  saving: false,
  message: '',
  messageIsError: false,
  role: 'user' as RoleEnum,
  email: '',
  avatar_uri: '',
  description: '',
});

async function loadUserForAdminUpdate() {
  userManage.loading = true;
  userManage.message = '';

  const userId = Number(userManage.userIdInput);
  if (!Number.isInteger(userId) || userId <= 0) {
    userManage.loading = false;
    userManage.message = '请输入合法用户 ID';
    userManage.messageIsError = true;
    return;
  }

  try {
    const { data, error } = await getUserProfileApiV1UsersUserIdGet({
      path: { user_id: userId },
    });
    if (error || !data) {
      userManage.message = formatError(error, '获取用户信息失败');
      userManage.messageIsError = true;
      return;
    }

    userManage.email = data.email || '';
    userManage.avatar_uri = data.avatar_uri || '';
    userManage.description = data.description || '';
    userManage.role = data.role;
    userManage.message = '用户信息已加载';
    userManage.messageIsError = false;
  } catch (err: any) {
    userManage.message = err?.message || '获取用户信息失败';
    userManage.messageIsError = true;
  } finally {
    userManage.loading = false;
  }
}

async function saveUserAdminUpdate() {
  userManage.saving = true;
  userManage.message = '';

  const userId = Number(userManage.userIdInput);
  if (!Number.isInteger(userId) || userId <= 0) {
    userManage.saving = false;
    userManage.message = '请输入合法用户 ID';
    userManage.messageIsError = true;
    return;
  }

  try {
    await adminPatch(`/api/v1/admin/users/${userId}`, {
      email: userManage.email || null,
      avatar_uri: userManage.avatar_uri || null,
      description: userManage.description || null,
      role: userManage.role || null,
    });
    userManage.message = '用户信息更新成功';
    userManage.messageIsError = false;
  } catch (err: any) {
    userManage.message = err?.message || '用户信息更新失败';
    userManage.messageIsError = true;
  } finally {
    userManage.saving = false;
  }
}

const clubManage = reactive({
  search: '',
  page: 1,
  size: 20,
  loading: false,
  clubs: [] as ClubInfo[],
  total: 0,
  pages: 1,
  selectedClubId: 0,
  saving: false,
  message: '',
  messageIsError: false,
  summary: '',
  description: '',
  logo_uri: '',
  status: 'normal',
  star_level: 'none',
});

async function fetchClubsForAdmin() {
  clubManage.loading = true;
  try {
    const { data, error } = await listClubsApiV1ClubsGet({
      query: {
        page: clubManage.page,
        size: clubManage.size,
        status: null,
        search: clubManage.search.trim() || null,
      },
    });

    if (error) {
      clubManage.message = formatError(error, '获取社团列表失败');
      clubManage.messageIsError = true;
      return;
    }

    clubManage.clubs = Array.isArray(data?.items) ? data.items : [];
    clubManage.total = Number(data?.total || 0);
    clubManage.pages = Math.max(1, Number(data?.pages || 1));
  } finally {
    clubManage.loading = false;
  }
}

function selectClubForAdmin(club: ClubInfo) {
  clubManage.selectedClubId = club.id;
  clubManage.summary = club.summary;
  clubManage.description = club.description;
  clubManage.logo_uri = club.logo_uri || '';
  clubManage.status = club.status;
  clubManage.star_level = club.star_level;
}

async function saveClubAdminUpdate() {
  if (!clubManage.selectedClubId) {
    clubManage.message = '请先选择社团';
    clubManage.messageIsError = true;
    return;
  }

  clubManage.saving = true;
  clubManage.message = '';

  try {
    await adminPatch(`/api/v1/admin/clubs/${clubManage.selectedClubId}`, {
      summary: clubManage.summary,
      description: clubManage.description,
      logo_uri: clubManage.logo_uri || null,
      status: clubManage.status,
      star_level: clubManage.star_level,
    });

    clubManage.message = '社团信息更新成功';
    clubManage.messageIsError = false;
    await fetchClubsForAdmin();
  } catch (err: any) {
    clubManage.message = err?.message || '社团信息更新失败';
    clubManage.messageIsError = true;
  } finally {
    clubManage.saving = false;
  }
}

const termManage = reactive({
  loading: false,
  items: [] as any[],
  message: '',
  messageIsError: false,
  creating: false,
  updating: false,
  deletingId: 0,
  createTermName: '',
  createStartDate: '',
  createEndDate: '',
  createIsCurrent: false,
  editTermId: 0,
  editTermName: '',
  editStartDate: '',
  editEndDate: '',
});

async function fetchTerms() {
  termManage.loading = true;
  try {
    const { data, error } = await listTermsApiV1AdminAcademicTermsGet({
      query: { page: 1, size: 100 },
    });

    if (error) {
      termManage.message = formatError(error, '获取学期列表失败');
      termManage.messageIsError = true;
      return;
    }

    termManage.items = Array.isArray(data?.items) ? data.items : [];
  } finally {
    termManage.loading = false;
  }
}

function startEditTerm(term: any) {
  if (termManage.editTermId === term.id) {
    termManage.editTermId = 0;
    return;
  }
  termManage.editTermId = term.id;
  termManage.editTermName = term.term_name || '';
  termManage.editStartDate = term.start_date || '';
  termManage.editEndDate = term.end_date || '';
}

async function createTerm() {
  termManage.creating = true;
  termManage.message = '';

  try {
    const { error } = await createTermApiV1AdminAcademicTermsPost({
      body: {
        term_name: termManage.createTermName || null,
        start_date: termManage.createStartDate,
        end_date: termManage.createEndDate,
        is_current: termManage.createIsCurrent,
      },
    });

    if (error) {
      termManage.message = formatError(error, '创建学期失败');
      termManage.messageIsError = true;
      return;
    }

    termManage.message = '学期创建成功';
    termManage.messageIsError = false;
    termManage.createTermName = '';
    termManage.createStartDate = '';
    termManage.createEndDate = '';
    termManage.createIsCurrent = false;
    await fetchTerms();
  } catch (err: any) {
    termManage.message = err?.message || '创建学期失败';
    termManage.messageIsError = true;
  } finally {
    termManage.creating = false;
  }
}

async function updateTerm() {
  if (!termManage.editTermId) return;

  termManage.updating = true;
  termManage.message = '';

  try {
    const { error } = await updateTermApiV1AdminAcademicTermsTermIdPatch({
      path: { term_id: termManage.editTermId },
      body: {
        term_name: termManage.editTermName || null,
        start_date: termManage.editStartDate || null,
        end_date: termManage.editEndDate || null,
      },
    });

    if (error) {
      termManage.message = formatError(error, '更新学期失败');
      termManage.messageIsError = true;
      return;
    }

    termManage.message = '学期更新成功';
    termManage.messageIsError = false;
    await fetchTerms();
  } catch (err: any) {
    termManage.message = err?.message || '更新学期失败';
    termManage.messageIsError = true;
  } finally {
    termManage.updating = false;
  }
}

async function deleteTerm(termId: number) {
  termManage.deletingId = termId;
  termManage.message = '';
  try {
    const { error } = await deleteTermApiV1AdminAcademicTermsTermIdDelete({
      path: { term_id: termId },
    });

    if (error) {
      termManage.message = formatError(error, '删除学期失败');
      termManage.messageIsError = true;
      return;
    }

    termManage.message = '学期删除成功';
    termManage.messageIsError = false;
    await fetchTerms();
  } catch (err: any) {
    termManage.message = err?.message || '删除学期失败';
    termManage.messageIsError = true;
  } finally {
    termManage.deletingId = 0;
  }
}

async function setCurrentTerm(termId: number) {
  termManage.message = '';
  try {
    const { error } = await setCurrentTermApiV1AdminAcademicTermsTermIdSetCurrentPost({
      path: { term_id: termId },
    });

    if (error) {
      termManage.message = formatError(error, '设置当前学期失败');
      termManage.messageIsError = true;
      return;
    }

    termManage.message = '已设置当前学期';
    termManage.messageIsError = false;
    await fetchTerms();
  } catch (err: any) {
    termManage.message = err?.message || '设置当前学期失败';
    termManage.messageIsError = true;
  }
}

const activityManage = reactive({
  loading: false,
  items: [] as GeneralActivityInfo[],
  search: '',
  level: 'all',
  message: '',
  messageIsError: false,
  creating: false,
  updating: false,
  deletingId: 0,
  createName: '',
  createDescription: '',
  createLevel: 'school',
  editId: 0,
  editName: '',
  editDescription: '',
  editLevel: 'school',
});

async function fetchGeneralActivities() {
  activityManage.loading = true;
  try {
    const { data, error } = await listActivitiesApiV1GeneralActivitiesGet({
      query: {
        search: activityManage.search.trim() || null,
        level: activityManage.level === 'all' ? null : (activityManage.level as any),
      },
    });

    if (error) {
      activityManage.message = formatError(error, '获取大型活动列表失败');
      activityManage.messageIsError = true;
      return;
    }

    activityManage.items = Array.isArray(data) ? data : [];
  } finally {
    activityManage.loading = false;
  }
}

async function createGeneralActivity() {
  activityManage.creating = true;
  activityManage.message = '';

  try {
    const { error } = await createApiV1AdminGeneralActivitiesPost({
      body: {
        name: activityManage.createName,
        description: activityManage.createDescription,
        level: activityManage.createLevel as any,
      },
    });

    if (error) {
      activityManage.message = formatError(error, '创建大型活动失败');
      activityManage.messageIsError = true;
      return;
    }

    activityManage.message = '大型活动创建成功';
    activityManage.messageIsError = false;
    activityManage.createName = '';
    activityManage.createDescription = '';
    activityManage.createLevel = 'school';
    await fetchGeneralActivities();
  } catch (err: any) {
    activityManage.message = err?.message || '创建大型活动失败';
    activityManage.messageIsError = true;
  } finally {
    activityManage.creating = false;
  }
}

function startEditGeneralActivity(activity: GeneralActivityInfo) {
  if (activityManage.editId === activity.id) {
    activityManage.editId = 0;
    return;
  }
  activityManage.editId = activity.id;
  activityManage.editName = activity.name;
  activityManage.editDescription = activity.description;
  activityManage.editLevel = activity.level;
}

async function updateGeneralActivity() {
  if (!activityManage.editId) return;

  activityManage.updating = true;
  activityManage.message = '';

  try {
    const { error } = await updateApiV1AdminGeneralActivitiesActivityIdPatch({
      path: { activity_id: activityManage.editId },
      body: {
        name: activityManage.editName,
        description: activityManage.editDescription,
        level: activityManage.editLevel as any,
      },
    });

    if (error) {
      activityManage.message = formatError(error, '更新大型活动失败');
      activityManage.messageIsError = true;
      return;
    }

    activityManage.message = '大型活动更新成功';
    activityManage.messageIsError = false;
    await fetchGeneralActivities();
  } catch (err: any) {
    activityManage.message = err?.message || '更新大型活动失败';
    activityManage.messageIsError = true;
  } finally {
    activityManage.updating = false;
  }
}

async function deleteGeneralActivity(activityId: number) {
  activityManage.deletingId = activityId;
  activityManage.message = '';

  try {
    const { error } = await deleteApiV1AdminGeneralActivitiesActivityIdDelete({
      path: { activity_id: activityId },
    });

    if (error) {
      activityManage.message = formatError(error, '删除大型活动失败');
      activityManage.messageIsError = true;
      return;
    }

    activityManage.message = '大型活动删除成功';
    activityManage.messageIsError = false;
    await fetchGeneralActivities();
  } catch (err: any) {
    activityManage.message = err?.message || '删除大型活动失败';
    activityManage.messageIsError = true;
  } finally {
    activityManage.deletingId = 0;
  }
}

function setAdminSection(sectionId: AdminSectionId) {
  void router.replace({
    query: {
      ...route.query,
      section: sectionId,
    },
  });
}

onMounted(async () => {
  loading.value = true;
  try {
    if (userStore.isLogin && !userStore.userInfo) {
      await userStore.fetchUser();
    }

    if (!canAccessAdmin.value) {
      globalError.value = '你没有后台管理权限（仅 admin/dev 可访问）';
      return;
    }

    if (!route.query.section || !isAdminSectionId(String(route.query.section))) {
      setAdminSection(defaultAdminSection);
    }

    await Promise.all([fetchClubsForAdmin(), fetchTerms(), fetchGeneralActivities()]);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="space-y-6">
    <Card class="border-slate-200/80 shadow-lg">
      <CardHeader>
        <CardTitle class="text-2xl">后台管理台</CardTitle>
        <CardDescription>
          覆盖用户、社团、学期和大型活动四类管理能力。仅 admin/dev 可使用。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="loading"
          class="rounded-xl border border-dashed border-slate-200 p-6 text-slate-500"
        >
          正在加载后台数据...
        </div>
        <div
          v-else-if="globalError"
          class="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-600"
        >
          {{ globalError }}
        </div>

        <div v-else class="w-full">
          <SidebarProvider
            class="w-full min-h-[calc(100vh-16rem)] items-stretch rounded-2xl border border-slate-200"
          >
            <Sidebar collapsible="none" class="h-full border-r border-slate-200 bg-white">
              <SidebarContent>
                <SidebarGroup>
                  <SidebarGroupLabel>后台导航</SidebarGroupLabel>
                  <SidebarGroupContent>
                    <SidebarMenu>
                      <SidebarMenuItem v-for="section in adminSections" :key="section.id">
                        <SidebarMenuButton
                          :is-active="activeAdminSection === section.id"
                          @click="setAdminSection(section.id)"
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
                <Card
                  v-if="activeAdminSection === 'admin-users'"
                  id="admin-users"
                  class="border-slate-200"
                >
                  <CardHeader>
                    <CardTitle>用户管理</CardTitle>
                    <CardDescription>按用户 ID 加载并更新用户信息与角色</CardDescription>
                  </CardHeader>
                  <CardContent class="space-y-3">
                    <div class="grid gap-3 md:grid-cols-4">
                      <input
                        v-model="userManage.userIdInput"
                        class="rounded-md border border-slate-200 px-3 py-2"
                        placeholder="用户 ID"
                      />
                      <Button
                        variant="outline"
                        :disabled="userManage.loading"
                        @click="loadUserForAdminUpdate"
                      >
                        {{ userManage.loading ? '加载中...' : '加载用户' }}
                      </Button>
                    </div>

                    <div class="grid gap-3 md:grid-cols-2">
                      <input
                        v-model="userManage.email"
                        class="rounded-md border border-slate-200 px-3 py-2"
                        placeholder="邮箱"
                      />
                      <Select v-model="userManage.role">
                        <SelectTrigger class="w-full">
                          <SelectValue placeholder="选择角色" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem v-for="role in roleOptions" :key="role" :value="role">
                              {{ getEnumLabel(adminRoleLabels, role) }}
                            </SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <input
                        v-model="userManage.avatar_uri"
                        class="rounded-md border border-slate-200 px-3 py-2 md:col-span-2"
                        placeholder="头像 URL"
                      />
                      <textarea
                        v-model="userManage.description"
                        class="min-h-24 rounded-md border border-slate-200 px-3 py-2 md:col-span-2"
                        placeholder="用户简介"
                      />
                    </div>

                    <div
                      v-if="userManage.message"
                      :class="[
                        'rounded-md border px-3 py-2 text-sm',
                        userManage.messageIsError
                          ? 'border-rose-200 bg-rose-50 text-rose-600'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                      ]"
                    >
                      {{ userManage.message }}
                    </div>

                    <Button :disabled="userManage.saving" @click="saveUserAdminUpdate">
                      {{ userManage.saving ? '保存中...' : '保存用户修改' }}
                    </Button>
                  </CardContent>
                </Card>

                <Card
                  v-if="activeAdminSection === 'admin-clubs'"
                  id="admin-clubs"
                  class="border-slate-200"
                >
                  <CardHeader>
                    <CardTitle>社团管理</CardTitle>
                    <CardDescription>搜索并选择社团后，更新状态、评级和基础信息</CardDescription>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div class="flex flex-wrap items-center gap-2">
                      <input
                        v-model="clubManage.search"
                        class="min-w-[260px] rounded-md border border-slate-200 px-3 py-2"
                        placeholder="搜索社团"
                        @keyup.enter="fetchClubsForAdmin"
                      />
                      <Button
                        variant="outline"
                        :disabled="clubManage.loading"
                        @click="fetchClubsForAdmin"
                        >查询社团</Button
                      >
                    </div>

                    <div class="rounded-lg border border-slate-200">
                      <div class="max-h-56 overflow-auto">
                        <button
                          v-for="club in clubManage.clubs"
                          :key="club.id"
                          type="button"
                          class="flex w-full items-center justify-between border-b border-slate-100 px-3 py-2 text-left hover:bg-slate-50"
                          @click="selectClubForAdmin(club)"
                        >
                          <span class="truncate">#{{ club.id }} {{ club.name }}</span>
                          <span class="text-xs text-slate-500">{{
                            getEnumLabel(clubStatusLabels, club.status)
                          }}</span>
                        </button>
                      </div>
                    </div>

                    <div class="grid gap-3 md:grid-cols-2">
                      <textarea
                        v-model="clubManage.summary"
                        class="min-h-20 rounded-md border border-slate-200 px-3 py-2"
                        placeholder="社团简介"
                      />
                      <textarea
                        v-model="clubManage.description"
                        class="min-h-20 rounded-md border border-slate-200 px-3 py-2"
                        placeholder="社团详情"
                      />
                      <input
                        v-model="clubManage.logo_uri"
                        class="rounded-md border border-slate-200 px-3 py-2 md:col-span-2"
                        placeholder="Logo URL"
                      />
                      <Select v-model="clubManage.status">
                        <SelectTrigger class="w-full">
                          <SelectValue placeholder="社团状态" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem
                              v-for="status in clubStatusOptions"
                              :key="status"
                              :value="status"
                            >
                              {{ getEnumLabel(clubStatusLabels, status) }}
                            </SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <Select v-model="clubManage.star_level">
                        <SelectTrigger class="w-full">
                          <SelectValue placeholder="社团评级" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem v-for="star in clubStarOptions" :key="star" :value="star">
                              {{ getEnumLabel(clubStarLabels, star) }}
                            </SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    </div>

                    <div
                      v-if="clubManage.message"
                      :class="[
                        'rounded-md border px-3 py-2 text-sm',
                        clubManage.messageIsError
                          ? 'border-rose-200 bg-rose-50 text-rose-600'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                      ]"
                    >
                      {{ clubManage.message }}
                    </div>

                    <Button
                      :disabled="clubManage.saving || !clubManage.selectedClubId"
                      @click="saveClubAdminUpdate"
                    >
                      {{ clubManage.saving ? '保存中...' : '保存社团修改' }}
                    </Button>
                  </CardContent>
                </Card>

                <Card
                  v-if="activeAdminSection === 'admin-terms'"
                  id="admin-terms"
                  class="border-slate-200"
                >
                  <CardHeader>
                    <CardTitle>学期管理</CardTitle>
                    <CardDescription>支持创建、更新、删除和设置当前学期</CardDescription>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div class="grid gap-3 md:grid-cols-4">
                      <input
                        v-model="termManage.createTermName"
                        class="rounded-md border border-slate-200 px-3 py-2"
                        placeholder="学期名称"
                      />
                      <input
                        v-model="termManage.createStartDate"
                        type="date"
                        class="rounded-md border border-slate-200 px-3 py-2"
                      />
                      <input
                        v-model="termManage.createEndDate"
                        type="date"
                        class="rounded-md border border-slate-200 px-3 py-2"
                      />
                      <label class="flex items-center gap-2 text-sm">
                        <input v-model="termManage.createIsCurrent" type="checkbox" />
                        设为当前学期
                      </label>
                    </div>
                    <Button :disabled="termManage.creating" @click="createTerm">{{
                      termManage.creating ? '创建中...' : '创建学期'
                    }}</Button>

                    <div class="rounded-lg border border-slate-200">
                      <div class="max-h-64 overflow-auto">
                        <div
                          v-for="term in termManage.items"
                          :key="term.id"
                          class="flex flex-wrap items-center gap-2 border-b border-slate-100 px-3 py-2"
                        >
                          <span class="font-medium">#{{ term.id }} {{ term.term_name }}</span>
                          <span class="text-xs text-slate-500"
                            >{{ term.start_date }} ~ {{ term.end_date }}</span
                          >
                          <span
                            v-if="term.is_current"
                            class="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700"
                            >当前</span
                          >
                          <div class="ml-auto flex items-center gap-2">
                            <Button variant="outline" @click="startEditTerm(term)">
                              {{ termManage.editTermId === term.id ? '收起' : '编辑' }}
                            </Button>
                            <Button variant="outline" @click="setCurrentTerm(term.id)"
                              >设为当前</Button
                            >
                            <Button
                              variant="destructive"
                              :disabled="termManage.deletingId === term.id"
                              @click="deleteTerm(term.id)"
                              >删除</Button
                            >
                          </div>
                        </div>
                      </div>
                    </div>

                    <div
                      v-if="termManage.editTermId"
                      class="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-3"
                    >
                      <input
                        v-model="termManage.editTermName"
                        class="rounded-md border border-slate-200 px-3 py-2"
                        placeholder="学期名称"
                      />
                      <input
                        v-model="termManage.editStartDate"
                        type="date"
                        class="rounded-md border border-slate-200 px-3 py-2"
                      />
                      <input
                        v-model="termManage.editEndDate"
                        type="date"
                        class="rounded-md border border-slate-200 px-3 py-2"
                      />
                      <Button :disabled="termManage.updating" @click="updateTerm">{{
                        termManage.updating ? '更新中...' : '保存学期修改'
                      }}</Button>
                      <!-- <Button variant="outline" :disabled="termManage.updating" @click="cancelEditTerm">取消编辑</Button> -->
                    </div>

                    <div
                      v-if="termManage.message"
                      :class="[
                        'rounded-md border px-3 py-2 text-sm',
                        termManage.messageIsError
                          ? 'border-rose-200 bg-rose-50 text-rose-600'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                      ]"
                    >
                      {{ termManage.message }}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  v-if="activeAdminSection === 'admin-activities'"
                  id="admin-activities"
                  class="border-slate-200"
                >
                  <CardHeader>
                    <CardTitle>大型活动管理</CardTitle>
                    <CardDescription>支持筛选、创建、编辑与删除大型活动</CardDescription>
                  </CardHeader>
                  <CardContent class="space-y-4">
                    <div class="flex flex-wrap items-center gap-2">
                      <input
                        v-model="activityManage.search"
                        class="min-w-[220px] rounded-md border border-slate-200 px-3 py-2"
                        placeholder="搜索活动"
                        @keyup.enter="fetchGeneralActivities"
                      />
                      <Select v-model="activityManage.level">
                        <SelectTrigger class="w-[180px]">
                          <SelectValue placeholder="全部级别" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem
                              v-for="level in generalActivityLevelFilterOptions"
                              :key="level"
                              :value="level"
                            >
                              {{ getEnumLabel(generalActivityLevelLabels, level) }}
                            </SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <Button
                        variant="outline"
                        :disabled="activityManage.loading"
                        @click="fetchGeneralActivities"
                        >查询</Button
                      >
                    </div>

                    <div
                      class="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-3"
                    >
                      <input
                        v-model="activityManage.createName"
                        class="rounded-md border border-slate-200 px-3 py-2"
                        placeholder="活动名称"
                      />
                      <Select v-model="activityManage.createLevel">
                        <SelectTrigger class="w-full">
                          <SelectValue placeholder="活动级别" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem
                              v-for="level in generalActivityLevelOptions"
                              :key="level"
                              :value="level"
                            >
                              {{ getEnumLabel(generalActivityLevelLabels, level) }}
                            </SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <Button :disabled="activityManage.creating" @click="createGeneralActivity">{{
                        activityManage.creating ? '创建中...' : '创建活动'
                      }}</Button>
                      <textarea
                        v-model="activityManage.createDescription"
                        class="min-h-20 rounded-md border border-slate-200 px-3 py-2 md:col-span-3"
                        placeholder="活动描述"
                      />
                    </div>

                    <div class="rounded-lg border border-slate-200">
                      <div class="max-h-72 overflow-auto">
                        <div
                          v-for="activity in activityManage.items"
                          :key="activity.id"
                          class="space-y-2 border-b border-slate-100 px-3 py-3"
                        >
                          <div class="flex items-center gap-2">
                            <span class="font-medium">#{{ activity.id }} {{ activity.name }}</span>
                            <span class="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{{
                              getEnumLabel(generalActivityLevelLabels, activity.level)
                            }}</span>
                            <div class="ml-auto flex gap-2">
                              <Button variant="outline" @click="startEditGeneralActivity(activity)">
                                {{ activityManage.editId === activity.id ? '收起' : '编辑' }}
                              </Button>
                              <Button
                                variant="destructive"
                                :disabled="activityManage.deletingId === activity.id"
                                @click="deleteGeneralActivity(activity.id)"
                                >删除</Button
                              >
                            </div>
                          </div>
                          <p class="text-sm text-slate-600">{{ activity.description }}</p>
                        </div>
                      </div>
                    </div>

                    <div
                      v-if="activityManage.editId"
                      class="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-3"
                    >
                      <input
                        v-model="activityManage.editName"
                        class="rounded-md border border-slate-200 px-3 py-2"
                        placeholder="活动名称"
                      />
                      <Select v-model="activityManage.editLevel">
                        <SelectTrigger class="w-full">
                          <SelectValue placeholder="活动级别" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem
                              v-for="level in generalActivityLevelOptions"
                              :key="level"
                              :value="level"
                            >
                              {{ getEnumLabel(generalActivityLevelLabels, level) }}
                            </SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                      <Button :disabled="activityManage.updating" @click="updateGeneralActivity">{{
                        activityManage.updating ? '保存中...' : '保存活动修改'
                      }}</Button>
                      <!-- <Button variant="outline" :disabled="activityManage.updating" @click="cancelEditGeneralActivity">取消编辑</Button> -->
                      <textarea
                        v-model="activityManage.editDescription"
                        class="min-h-20 rounded-md border border-slate-200 px-3 py-2 md:col-span-3"
                        placeholder="活动描述"
                      />
                    </div>

                    <div
                      v-if="activityManage.message"
                      :class="[
                        'rounded-md border px-3 py-2 text-sm',
                        activityManage.messageIsError
                          ? 'border-rose-200 bg-rose-50 text-rose-600'
                          : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                      ]"
                    >
                      {{ activityManage.message }}
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
