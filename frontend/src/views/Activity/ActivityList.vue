<template>
  <div class="py-8">
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">活动列表</h1>
        <p class="text-muted-foreground mt-2">当前学期: {{ currentTermName || '加载中...' }}</p>
      </div>
      <div class="flex gap-4">
        <Dialog v-model:open="createDialogOpen">
          <DialogTrigger as-child>
            <Button>创建活动</Button>
          </DialogTrigger>
          <DialogContent class="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>创建新活动</DialogTitle>
              <DialogDescription> 创建一个通用的校园活动或社团联合活动。 </DialogDescription>
            </DialogHeader>
            <div class="grid gap-4 py-4">
              <div class="grid gap-2">
                <Label for="name">活动名称</Label>
                <Input id="name" v-model="form.name" placeholder="请输入活动名称" />
              </div>
              <div class="grid gap-2">
                <Label for="level">活动级别</Label>
                <Select v-model="form.level">
                  <SelectTrigger>
                    <SelectValue placeholder="选择活动级别" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="school">全校性活动 (School)</SelectItem>
                    <SelectItem value="large">大型活动 (Large)</SelectItem>
                    <SelectItem value="sua">社联活动 (SUA)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="grid gap-2">
                <Label for="description">活动描述</Label>
                <textarea
                  id="description"
                  v-model="form.description"
                  class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder="描述一下这个活动..."
                ></textarea>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" @click="createDialogOpen = false">取消</Button>
              <Button :disabled="submitting" @click="handleCreate">
                {{ submitting ? '提交中...' : '提交创建' }}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
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
          <p class="text-sm text-muted-foreground line-clamp-3 mb-4">
            {{ activity.description }}
          </p>
          <div v-if="activity.club_records.length > 0" class="mt-4">
            <p class="text-xs font-semibold text-muted-foreground mb-2">参与社团:</p>
            <div class="flex flex-wrap gap-2">
              <Badge
                v-for="record in activity.club_records"
                :key="record.id"
                variant="outline"
                class="text-[10px]"
              >
                {{ record.club_name }}
              </Badge>
            </div>
          </div>
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
import { ref, onMounted, computed, reactive } from 'vue';
import { useRouter } from 'vue-router';
import {
  listActivitiesApiV1GeneralActivitiesGet,
  createApiV1AdminGeneralActivitiesPost,
  type GeneralActivityInfo,
} from '@/client';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  generalActivityLevelLabels,
  getEnumLabel,
  getGeneralActivityBadgeVariant,
} from '@/lib/i18n/enumLabels';

const router = useRouter();
const activities = ref<GeneralActivityInfo[]>([]);
const loading = ref(true);
const createDialogOpen = ref(false);
const submitting = ref(false);

const handleCreate = async () => {
  if (!form.name || !form.description) {
    alert('请填写完整信息');
    return;
  }

  submitting.value = true;
  try {
    const { data, error } = await createApiV1AdminGeneralActivitiesPost({
      body: {
        name: form.name,
        description: form.description,
        level: form.level as any,
      },
    });

    if (error) {
      console.error('创建失败:', error);
      alert('创建失败: ' + JSON.stringify(error));
    } else {
      createDialogOpen.value = false;
      // 重置表单
      form.name = '';
      form.description = '';
      form.level = 'school';
      // 重新加载列表
      fetchActivities();
    }
  } catch (err) {
    console.error('创建出错:', err);
  } finally {
    submitting.value = false;
  }
};
const form = reactive({
  name: '',
  description: '',
  level: 'school' as 'school' | 'large' | 'sua',
});

const currentTermName = computed(() => {
  if (activities.value.length > 0) {
    return activities.value[0].academic_term.term_name;
  }
  return '';
});

const fetchActivities = async () => {
  loading.value = true;
  try {
    const { data, error } = await listActivitiesApiV1GeneralActivitiesGet();
    if (error) {
      console.error('获取活动列表失败:', error);
    } else if (data) {
      // 这里的 data 目前是 GeneralActivityInfo[]，但后端代码中显示是 Page[GeneralActivityInfo]
      // 实际上根据 openapi 生成的代码，如果后端返回值被识别为列表，data 就是数组
      activities.value = Array.isArray(data) ? data : (data as any).items || [];
    }
  } catch (err) {
    console.error('获取活动列表出错:', err);
  } finally {
    loading.value = false;
  }
};

const getBadgeVariant = (level: string) => getGeneralActivityBadgeVariant(level);

const getLevelLabel = (level: string) => getEnumLabel(generalActivityLevelLabels, level);

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
