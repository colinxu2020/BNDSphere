<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { createClubApiV1ClubsPost, type ClubCategoryEnum } from '../../client';
import { clubCategoryLabels, getEnumLabel } from '../../lib/i18n/enumLabels';
import { formatError } from '../../lib/utils';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';

const router = useRouter();

const submitting = ref(false);
const message = ref('');
const messageIsError = ref(false);

const form = reactive<{
  name: string;
  category: ClubCategoryEnum;
  summary: string;
  description: string;
  logo_uri: string;
}>({
  name: '',
  category: 'other',
  summary: '',
  description: '',
  logo_uri: '',
});

const categoryOptions: ClubCategoryEnum[] = [
  'sports',
  'humanity',
  'arts',
  'science',
  'charity',
  'business',
  'campus',
  'other',
];

async function handleCreateClub() {
  if (submitting.value) return;

  if (!form.name.trim() || !form.summary.trim() || !form.description.trim()) {
    message.value = '请填写完整信息（名称、简介、描述）';
    messageIsError.value = true;
    return;
  }

  submitting.value = true;
  message.value = '';

  try {
    const { data, error } = await createClubApiV1ClubsPost({
      body: {
        name: form.name.trim(),
        category: form.category,
        summary: form.summary.trim(),
        description: form.description.trim(),
        logo_uri: form.logo_uri.trim() || null,
      },
    });

    if (error) {
      message.value = formatError(error, '创建社团失败');
      messageIsError.value = true;
      return;
    }

    if (!data?.id) {
      message.value = '创建成功，但未返回社团 ID';
      messageIsError.value = true;
      return;
    }

    message.value = '社团创建成功，等待管理员审核';
    messageIsError.value = false;
    await router.push(`/club/${data.id}`);
  } catch (err: any) {
    message.value = err?.message || '创建社团失败';
    messageIsError.value = true;
  } finally {
    submitting.value = false;
  }
}

function goBack() {
  void router.push('/clubs/discover');
}
</script>

<template>
  <div class="mx-auto w-full max-w-3xl px-6 py-10">
    <Card class="border-slate-200 shadow-sm">
      <CardHeader>
        <CardTitle class="text-2xl">新建社团</CardTitle>
        <CardDescription>填写基础资料并提交创建申请，管理员审核后生效。</CardDescription>
      </CardHeader>

      <CardContent class="space-y-5">
        <div class="grid gap-2">
          <label class="text-sm font-medium text-slate-700">社团名称</label>
          <Input v-model="form.name" placeholder="例如：篮球社" />
        </div>

        <div class="grid gap-2">
          <label class="text-sm font-medium text-slate-700">社团分类</label>
          <select
            v-model="form.category"
            class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            <option v-for="item in categoryOptions" :key="item" :value="item">
              {{ getEnumLabel(clubCategoryLabels, item) }}
            </option>
          </select>
        </div>

        <div class="grid gap-2">
          <label class="text-sm font-medium text-slate-700">社团简介</label>
          <Input v-model="form.summary" placeholder="一句话简介" />
        </div>

        <div class="grid gap-2">
          <label class="text-sm font-medium text-slate-700">社团描述</label>
          <textarea
            v-model="form.description"
            class="min-h-[120px] w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
            placeholder="介绍社团定位、活动方向等"
          />
        </div>

        <div class="grid gap-2">
          <label class="text-sm font-medium text-slate-700">Logo 地址（可选）</label>
          <Input v-model="form.logo_uri" placeholder="https://..." />
        </div>

        <div
          v-if="message"
          :class="[
            'rounded-md border px-3 py-2 text-sm',
            messageIsError
              ? 'border-rose-200 bg-rose-50 text-rose-600'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700',
          ]"
        >
          {{ message }}
        </div>

        <div class="flex items-center gap-3">
          <Button variant="outline" @click="goBack">取消</Button>
          <Button :disabled="submitting" @click="handleCreateClub">
            {{ submitting ? '提交中...' : '提交创建' }}
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
