<script setup>
import { Button } from '@/components/ui/button';
import ClubCard from '@/components/GuestMainPage/ClubCard.vue';

const props = defineProps({
  clubs: {
    type: Array,
    default: () => [],
  },
  selectedCategory: {
    type: String,
    default: '全部',
  },
  searchKeyword: {
    type: String,
    default: '',
  },
  currentPage: {
    type: Number,
    default: 1,
  },
  totalPages: {
    type: Number,
    default: 1,
  },
  totalItems: {
    type: Number,
    default: 0,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  allCategories: {
    type: Array,
    default: () => [],
  },
  categoryMap: {
    type: Object,
    default: () => ({}),
  },
  emptyText: {
    type: String,
    default: '没有找到符合条件的社团。',
  },
  getIsJoined: {
    type: Function,
    default: () => false,
  },
  getMemberCount: {
    type: Function,
    default: () => 0,
  },
  getPresidentName: {
    type: Function,
    default: () => '-',
  },
});

const emit = defineEmits([
  'update:selectedCategory',
  'update:searchKeyword',
  'update:currentPage',
  'search',
]);

function updateSearchKeyword(event) {
  emit('update:searchKeyword', event.target.value);
}

function selectCategory(category) {
  emit('update:selectedCategory', category);
}

function goPrevPage() {
  if (props.currentPage <= 1) return;
  emit('update:currentPage', props.currentPage - 1);
}

function goNextPage() {
  if (props.currentPage >= props.totalPages) return;
  emit('update:currentPage', props.currentPage + 1);
}
</script>

<template>
  <div class="space-y-8 pb-24">
    <div class="mt-8 flex flex-col gap-3 md:flex-row md:items-end">
      <label class="block md:w-[420px]">
        <span class="mb-1 block text-sm text-slate-600">搜索社团</span>
        <input
          :value="searchKeyword"
          type="text"
          class="w-full rounded-md border border-slate-200 px-3 py-2"
          placeholder="输入社团名称或关键词"
          @input="updateSearchKeyword"
          @keyup.enter="emit('search')"
        />
      </label>
      <Button variant="outline" class="md:h-10" @click="emit('search')">搜索</Button>
    </div>

    <div class="flex flex-wrap gap-3">
      <Button
        variant="outline"
        :class="selectedCategory === '全部' ? 'bg-gray-200' : ''"
        @click="selectCategory('全部')"
      >
        全部
      </Button>
      <Button
        v-for="catKey in allCategories"
        :key="catKey"
        variant="outline"
        :class="selectedCategory === catKey ? 'bg-gray-200' : ''"
        @click="selectCategory(catKey)"
      >
        {{ categoryMap[catKey] || catKey }}
      </Button>
    </div>

    <div>
      <div v-if="loading" class="mb-6 text-sm text-slate-500">正在加载社团列表...</div>
      <div
        v-else-if="clubs.length === 0"
        class="mb-6 rounded-lg border border-dashed border-slate-200 p-8 text-center text-slate-500"
      >
        {{ emptyText }}
      </div>

      <div class="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
        <ClubCard
          v-for="(club, idx) in clubs"
          :key="idx"
          :name="club.name"
          :category="categoryMap[club.category] || club.category"
          :description="club.description"
          :logo_uri="club.logo_uri"
          :id="`${club.id}`"
          :member-count="getMemberCount(club)"
          :president-name="getPresidentName(club)"
          :is-joined="getIsJoined(club)"
        />
      </div>

      <div class="mt-8 flex items-center justify-between">
        <p class="text-sm text-slate-500">
          共 {{ totalItems }} 个社团，当前第 {{ currentPage }} / {{ totalPages }} 页
        </p>
        <div class="flex items-center gap-2">
          <Button variant="outline" :disabled="currentPage <= 1 || loading" @click="goPrevPage">
            上一页
          </Button>
          <Button
            variant="outline"
            :disabled="currentPage >= totalPages || loading"
            @click="goNextPage"
          >
            下一页
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
