<script setup>
import ClubDirectoryPanel from '@/components/GuestMainPage/ClubDirectoryPanel.vue';
import { useUserStore } from '@/lib/auth/userStore';
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { CATEGORY_MAP, useClubDirectory } from '@/lib/club/useClubDirectory.js';

const userStore = useUserStore();
const isLogin = computed(() => userStore.isLogin);
const router = useRouter();

function goToCreateClub() {
  void router.push('/clubs/create');
}

const {
  clubs,
  selectedCategory,
  searchKeyword,
  currentPage,
  totalPages,
  totalItems,
  loading,
  allCategories,
  handleSearch,
  getIsJoined,
  getMemberCount,
  getPresidentName,
} = useClubDirectory({
  userStore,
  modeRef: computed(() => 'discover'),
});
</script>

<template>
  <div class="h-full w-full max-w-7xl mx-auto px-6 lg:px-12">
    <div class="mt-12">
      <h1 class="text-4xl font-bold text-gray-800 tracking-wide mb-3">发现社团</h1>
      <p class="text-gray-500">浏览并搜索感兴趣的社团，选择你想加入的组织。</p>
      <div v-if="isLogin" class="mt-4">
        <button
          class="rounded-md bg-slate-900 px-4 py-2 text-sm text-white transition hover:bg-slate-700"
          @click="goToCreateClub"
        >
          新建社团
        </button>
      </div>
    </div>

    <div class="mt-8">
      <ClubDirectoryPanel
        v-model:selectedCategory="selectedCategory"
        v-model:searchKeyword="searchKeyword"
        v-model:currentPage="currentPage"
        :clubs="clubs"
        :loading="loading"
        :all-categories="allCategories"
        :category-map="CATEGORY_MAP"
        :total-pages="totalPages"
        :total-items="totalItems"
        empty-text="没有找到符合条件的社团。"
        :get-is-joined="getIsJoined"
        :get-member-count="getMemberCount"
        :get-president-name="getPresidentName"
        @search="handleSearch"
      />
    </div>
  </div>
</template>
