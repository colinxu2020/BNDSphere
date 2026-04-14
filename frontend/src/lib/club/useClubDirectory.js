import { computed, onMounted, ref, watch } from 'vue';
import { getUserProfileApiV1UsersUserIdGet, listClubsApiV1ClubsGet } from '../../client';

export const CATEGORY_MAP = {
  sports: '体育',
  humanity: '人文',
  arts: '艺术',
  science: '科学',
  charity: '公益',
  business: '商业',
  campus: '校园',
  other: '其他',
};

export const ALL_CATEGORY = '全部';

export function useClubDirectory(options) {
  const { userStore, modeRef } = options;

  const clubs = ref([]);
  const joinedClubs = ref([]);
  const selectedCategory = ref(ALL_CATEGORY);
  const searchKeyword = ref('');
  const currentPage = ref(1);
  const pageSize = 20;
  const totalPages = ref(1);
  const totalItems = ref(0);
  const loading = ref(false);
  const presidentNameCache = ref({});

  const allCategories = Object.keys(CATEGORY_MAP);

  const mode = computed(() => {
    if (typeof modeRef === 'function') {
      return modeRef();
    }
    if (typeof modeRef === 'object' && modeRef !== null && 'value' in modeRef) {
      return modeRef.value;
    }
    return modeRef;
  });

  const isJoinedMode = computed(() => mode.value === 'joined');

  function getPresidentUserId(club) {
    const president = (club.members || []).find((member) => member.membership === 'president');
    return president?.user_id || null;
  }

  function getIsJoined(club) {
    const currentUserId = userStore.userInfo?.id;
    if (!currentUserId) return false;
    return (club.members || []).some(
      (member) =>
        member.user_id === currentUserId &&
        (member.membership === 'member' ||
          member.membership === 'vice president' ||
          member.membership === 'president'),
    );
  }

  function getMemberCount(club) {
    return (club.members || []).filter((member) => member.membership !== 'left').length;
  }

  function getPresidentName(club) {
    const presidentId = getPresidentUserId(club);
    if (!presidentId) return '-';
    return presidentNameCache.value[presidentId] || `用户 #${presidentId}`;
  }

  function updateJoinedPageData() {
    totalItems.value = joinedClubs.value.length;
    totalPages.value = Math.max(1, Math.ceil(totalItems.value / pageSize));
    if (currentPage.value > totalPages.value) {
      currentPage.value = totalPages.value;
    }
    const start = (currentPage.value - 1) * pageSize;
    clubs.value = joinedClubs.value.slice(start, start + pageSize);
  }

  async function ensurePresidentNames(list) {
    const missing = Array.from(
      new Set(
        list
          .map((club) => getPresidentUserId(club))
          .filter((id) => !!id && !presidentNameCache.value[id]),
      ),
    );

    if (missing.length === 0) return;

    await Promise.all(
      missing.map(async (userId) => {
        const { data } = await getUserProfileApiV1UsersUserIdGet({
          path: { user_id: userId },
        });
        if (data?.username) {
          presidentNameCache.value[userId] = data.username;
        }
      }),
    );
  }

  async function fetchDiscoverClubs() {
    const { data, error } = await listClubsApiV1ClubsGet({
      query: {
        category: selectedCategory.value === ALL_CATEGORY ? null : selectedCategory.value,
        status: 'normal',
        search: searchKeyword.value.trim() || null,
        page: currentPage.value,
        size: pageSize,
      },
    });

    if (error) {
      console.error('获取社团列表失败:', error);
      clubs.value = [];
      totalPages.value = 1;
      totalItems.value = 0;
      return;
    }

    clubs.value = Array.isArray(data?.items) ? data.items : [];
    totalPages.value = Math.max(1, Number(data?.pages || 1));
    totalItems.value = Number(data?.total || 0);
    await ensurePresidentNames(clubs.value);
  }

  async function fetchJoinedClubs() {
    let page = 1;
    let pages = 1;
    const size = 100;
    const allItems = [];

    while (page <= pages) {
      const { data, error } = await listClubsApiV1ClubsGet({
        query: {
          category: selectedCategory.value === ALL_CATEGORY ? null : selectedCategory.value,
          status: 'normal',
          search: searchKeyword.value.trim() || null,
          page,
          size,
        },
      });

      if (error) {
        console.error('获取社团列表失败:', error);
        break;
      }

      allItems.push(...(Array.isArray(data?.items) ? data.items : []));
      pages = Number(data?.pages || 1);
      page += 1;
    }

    joinedClubs.value = allItems.filter((club) => getIsJoined(club));
    updateJoinedPageData();
    await ensurePresidentNames(clubs.value);
  }

  async function fetchClubs() {
    loading.value = true;
    try {
      if (userStore.isLogin && !userStore.userInfo) {
        await userStore.fetchUser();
      }

      if (isJoinedMode.value) {
        await fetchJoinedClubs();
      } else {
        await fetchDiscoverClubs();
      }
    } finally {
      loading.value = false;
    }
  }

  function handleSearch() {
    currentPage.value = 1;
    void fetchClubs();
  }

  watch(selectedCategory, () => {
    currentPage.value = 1;
    void fetchClubs();
  });

  watch(currentPage, () => {
    if (isJoinedMode.value) {
      updateJoinedPageData();
      void ensurePresidentNames(clubs.value);
      return;
    }
    void fetchClubs();
  });

  watch(mode, () => {
    currentPage.value = 1;
    void fetchClubs();
  });

  onMounted(() => {
    void fetchClubs();
  });

  return {
    clubs,
    selectedCategory,
    searchKeyword,
    currentPage,
    pageSize,
    totalPages,
    totalItems,
    loading,
    allCategories,
    isJoinedMode,
    handleSearch,
    fetchClubs,
    getIsJoined,
    getMemberCount,
    getPresidentName,
  };
}
