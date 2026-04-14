<template>
  <div class="space-y-4 p-6">
    <div class="flex flex-wrap gap-3">
      <Button @click="createClub">createClub</Button>
      <Button variant="outline" @click="listClubs">ListClub</Button>
      <Button variant="secondary" @click="openActivityDialog">新建社团活动</Button>
      <Button variant="outline" @click="openGeneralActivityDialog">新建通用活动</Button>
    </div>

    <Dialog v-model:open="activityDialogOpen">
      <DialogContent class="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>新建社团活动</DialogTitle>
          <DialogDescription>填写活动信息后，提交到指定社团。</DialogDescription>
        </DialogHeader>

        <form class="grid gap-4 py-2" @submit.prevent="submitActivity">
          <div class="grid gap-2">
            <Label for="club-id">社团 ID</Label>
            <Input
              id="club-id"
              v-model="activityForm.clubId"
              type="number"
              min="1"
              placeholder="例如 1"
            />
          </div>

          <div class="grid gap-2">
            <Label for="activity-name">活动名称</Label>
            <Input id="activity-name" v-model="activityForm.name" placeholder="例如：第一次例会" />
          </div>

          <div class="grid gap-2 md:grid-cols-2 md:gap-4">
            <div class="grid gap-2">
              <Label for="activity-location">活动地点</Label>
              <Input
                id="activity-location"
                v-model="activityForm.location"
                placeholder="例如：教学楼 A301"
              />
            </div>
            <div class="grid gap-2">
              <Label for="activity-start">开始时间</Label>
              <Input id="activity-start" v-model="activityForm.startTime" type="datetime-local" />
            </div>
          </div>

          <div class="grid gap-2">
            <Label for="activity-end">结束时间</Label>
            <Input id="activity-end" v-model="activityForm.endTime" type="datetime-local" />
          </div>

          <div class="grid gap-2">
            <Label for="activity-description">活动描述</Label>
            <textarea
              id="activity-description"
              v-model="activityForm.description"
              class="min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs outline-none transition focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50"
              placeholder="写下活动简介、流程或报名要求"
            />
          </div>

          <div
            v-if="activityMessage"
            class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600"
          >
            {{ activityMessage }}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" @click="activityDialogOpen = false"
              >取消</Button
            >
            <Button type="submit" :disabled="activitySubmitting">
              {{ activitySubmitting ? '提交中...' : '创建活动' }}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <!-- 通用活动对话框 -->
    <Dialog v-model:open="generalActivityDialogOpen">
      <DialogContent class="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>新建通用活动</DialogTitle>
          <DialogDescription>创建全校范围或其他类型的通用活动。</DialogDescription>
        </DialogHeader>

        <form class="grid gap-4 py-2" @submit.prevent="submitGeneralActivity">
          <div class="grid gap-2">
            <Label for="ga-name">活动名称</Label>
            <Input id="ga-name" v-model="generalActivityForm.name" placeholder="例如：全校讲座" />
          </div>

          <div class="grid gap-2">
            <Label for="ga-level">级别</Label>
            <select
              id="ga-level"
              v-model="generalActivityForm.level"
              class="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            >
              <option value="school">全校性活动</option>
              <option value="large">大型活动</option>
              <option value="sua">学生会活动</option>
            </select>
          </div>

          <div class="grid gap-2">
            <Label for="ga-description">活动描述</Label>
            <textarea
              id="ga-description"
              v-model="generalActivityForm.description"
              class="min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-xs outline-none transition focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50"
              placeholder="写下活动简介、流程或要求"
            />
          </div>

          <div
            v-if="generalActivityMessage"
            class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600"
          >
            {{ generalActivityMessage }}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" @click="generalActivityDialogOpen = false"
              >取消</Button
            >
            <Button type="submit" :disabled="generalActivitySubmitting">
              {{ generalActivitySubmitting ? '提交中...' : '创建通用活动' }}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import {
  createApiV1AdminGeneralActivitiesPost,
  createClubActivityApiV1ClubsClubIdActivitiesPost,
  createClubApiV1ClubsPost,
  listClubsApiV1ClubsGet,
  type ActivityCreate,
  type ClubCategoryEnum,
} from '@/client';
import { Button } from '../../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const Categories: Record<string, ClubCategoryEnum> = {
  SPORTS: 'sports',
  HUMANITY: 'humanity',
  ARTS: 'arts',
  SCIENCE: 'science',
  CHARITY: 'charity',
  BUSINESS: 'business',
  CAMPUS: 'campus',
  OTHER: 'other',
};

const activityDialogOpen = ref(false);
const activitySubmitting = ref(false);
const activityMessage = ref('');

const activityForm = reactive({
  clubId: '1',
  name: '',
  location: '',
  startTime: toDatetimeLocal(new Date(Date.now() + 60 * 60 * 1000)),
  endTime: toDatetimeLocal(new Date(Date.now() + 2 * 60 * 60 * 1000)),
  description: '',
});

const generalActivityDialogOpen = ref(false);
const generalActivitySubmitting = ref(false);
const generalActivityMessage = ref('');

const generalActivityForm = reactive({
  name: '',
  description: '',
  level: 'school' as 'school' | 'large' | 'club_federation',
});

function toDatetimeLocal(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function resetActivityForm() {
  activityForm.clubId = '1';
  activityForm.name = '';
  activityForm.location = '';
  activityForm.startTime = toDatetimeLocal(new Date(Date.now() + 60 * 60 * 1000));
  activityForm.endTime = toDatetimeLocal(new Date(Date.now() + 2 * 60 * 60 * 1000));
  activityForm.description = '';
}

function openActivityDialog() {
  activityMessage.value = '';
  activityDialogOpen.value = true;
}

function openGeneralActivityDialog() {
  generalActivityMessage.value = '';
  generalActivityDialogOpen.value = true;
}

function resetGeneralActivityForm() {
  generalActivityForm.name = '';
  generalActivityForm.description = '';
  generalActivityForm.level = 'school';
}

async function submitGeneralActivity() {
  generalActivitySubmitting.value = true;
  generalActivityMessage.value = '';

  try {
    const { data, error } = await createApiV1AdminGeneralActivitiesPost({
      body: {
        name: generalActivityForm.name,
        description: generalActivityForm.description,
        level: generalActivityForm.level as any,
      },
    });

    if (error) {
      generalActivityMessage.value = `创建失败: ${JSON.stringify(error)}`;
    } else {
      generalActivityMessage.value = `创建成功: ID ${data.id}`;
      setTimeout(() => {
        generalActivityDialogOpen.value = false;
        resetGeneralActivityForm();
      }, 1500);
    }
  } catch (err: any) {
    generalActivityMessage.value = `发生错误: ${err.message}`;
  } finally {
    generalActivitySubmitting.value = false;
  }
}

function createClub() {
  createClubApiV1ClubsPost({
    body: {
      name: '测试社团3',
      description: '这是一个测试社团3',
      category: Categories.OTHER,
      summary: '测试社团简介3',
      logo_uri: 'https://example.com/logo.png',
    },
  }).then(({ data, error }) => {
    if (error) {
      console.error('创建社团失败:', error);
    } else {
      console.log('创建社团成功:', data);
    }
  });
}

function listClubs() {
  listClubsApiV1ClubsGet({
    query: {
      offset: 0,
      limit: 10,
    },
  }).then(({ data, error }) => {
    if (error) {
      console.error('获取社团列表失败:', error);
    } else {
      console.log('社团列表:', data);
    }
  });
}

async function submitActivity() {
  activitySubmitting.value = true;
  activityMessage.value = '';

  try {
    const clubId = Number(activityForm.clubId);
    if (!Number.isInteger(clubId) || clubId <= 0) {
      throw new Error('请输入正确的社团 ID');
    }

    const startTime = new Date(activityForm.startTime);
    const endTime = new Date(activityForm.endTime);

    if (Number.isNaN(startTime.getTime()) || Number.isNaN(endTime.getTime())) {
      throw new Error('请输入正确的开始/结束时间');
    }

    if (endTime <= startTime) {
      throw new Error('结束时间必须晚于开始时间');
    }

    const payload: ActivityCreate = {
      name: activityForm.name,
      description: activityForm.description,
      location: activityForm.location,
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
    };

    const { data, error } = await createClubActivityApiV1ClubsClubIdActivitiesPost({
      path: { club_id: clubId },
      body: payload,
    });

    if (error) {
      throw new Error(typeof error === 'string' ? error : '创建活动失败');
    }

    console.log('创建活动成功:', data);
    activityMessage.value = '创建成功';
    activityDialogOpen.value = false;
    resetActivityForm();
  } catch (error) {
    activityMessage.value = error instanceof Error ? error.message : '创建活动失败';
  } finally {
    activitySubmitting.value = false;
  }
}
</script>
