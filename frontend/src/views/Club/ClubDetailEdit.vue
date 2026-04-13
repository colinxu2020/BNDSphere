<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  getClubInfoApiV1ClubsClubIdGet,
  updateClubInfoApiV1ClubsClubIdPatch,
  type ClubUpdate,
} from '../../client';
import { Button } from '../../components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { formatError } from '../../lib/utils';

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const saving = ref(false);
const error = ref('');
const success = ref('');
const clubName = ref('');

const clubId = computed(() => Number(route.params.id));

const form = reactive({
  summary: '',
  description: '',
  logo_uri: '',
});

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
      error.value = formatError(fetchError, '获取社团信息失败');
      return;
    }

    if (!data) {
      error.value = '获取社团详情为空';
      return;
    }

    clubName.value = data.name;
    form.summary = data.summary ?? '';
    form.description = data.description ?? '';
    form.logo_uri = data.logo_uri ?? '';
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : '获取社团信息失败';
    error.value = `请求异常: ${message}`;
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  void fetchClubDetail();
}

async function saveClubInfo() {
  success.value = '';
  error.value = '';

  if (!Number.isInteger(clubId.value) || clubId.value <= 0) {
    error.value = '社团 ID 非法';
    return;
  }

  if (!form.summary.trim()) {
    error.value = '社团简介不能为空';
    return;
  }

  if (!form.description.trim()) {
    error.value = '社团介绍不能为空';
    return;
  }

  saving.value = true;

  try {
    const payload: ClubUpdate = {
      summary: form.summary.trim(),
      description: form.description.trim(),
      logo_uri: form.logo_uri?.trim() ? form.logo_uri.trim() : null,
    };

    const { error: updateError } = await updateClubInfoApiV1ClubsClubIdPatch({
      path: { club_id: clubId.value },
      body: payload,
    });

    if (updateError) {
      error.value = formatError(updateError, '更新社团信息失败');
      return;
    }

    success.value = '社团信息已保存';
    void router.push({ name: 'ClubDetail', params: { id: clubId.value } });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : '更新社团信息失败';
    error.value = `请求异常: ${message}`;
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  void fetchClubDetail();
});
</script>

<template>
  <div class="space-y-6">
    <Card class="border-slate-200/80 shadow-lg">
      <CardHeader>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardDescription>Club ID: {{ route.params.id }}</CardDescription>
            <CardTitle class="mt-2 text-2xl">编辑社团信息</CardTitle>
            <p class="mt-1 text-sm text-slate-500">{{ clubName || '加载中...' }}</p>
          </div>
          <Button variant="outline" as-child>
            <router-link :to="`/club/${route.params.id}`">返回社团详情</router-link>
          </Button>
        </div>
      </CardHeader>

      <CardContent class="space-y-5">
        <div
          v-if="loading"
          class="rounded-2xl border border-dashed border-slate-200 p-6 text-slate-500"
        >
          正在加载社团信息...
        </div>

        <div
          v-else-if="error"
          class="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-600"
        >
          {{ error }}
        </div>

        <div v-else class="space-y-4">
          <div>
            <p class="mb-1 text-sm text-slate-600">社团简介</p>
            <Input v-model="form.summary" placeholder="一句话介绍社团" />
          </div>

          <div>
            <p class="mb-1 text-sm text-slate-600">Logo 链接</p>
            <Input v-model="form.logo_uri" placeholder="https://example.com/logo.png" />
          </div>

          <div>
            <p class="mb-1 text-sm text-slate-600">社团介绍</p>
            <textarea
              v-model="form.description"
              rows="8"
              class="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
              placeholder="请填写更详细的社团介绍"
            />
          </div>

          <div
            v-if="success"
            class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-700"
          >
            {{ success }}
          </div>

          <div class="flex items-center gap-3">
            <Button variant="outline" :disabled="saving" @click="resetForm">重置</Button>
            <Button :disabled="saving" @click="saveClubInfo">
              {{ saving ? '保存中...' : '保存修改' }}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
