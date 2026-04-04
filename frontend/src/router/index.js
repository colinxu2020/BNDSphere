import { createRouter, createWebHistory } from 'vue-router';
import { checkAuth } from '@/lib/auth/utils'; // 导入认证检查函数
const routes = [
  {
    path: '/user/:id',
    name: 'UserProfile',
    component: () => import('@/views/profile/Profile.vue'),
    meta: { layout: 'main', requiresAuth: true },
    props: true,
  },
  {
    path: '/settings/profile',
    name: 'ProfileSettings',
    component: () => import('@/views/profile/ProfileSettings.vue'),
    meta: { layout: 'main', requiresAuth: true },
  },
  {
    path: '/profile',
    meta: { layout: 'main', requiresAuth: true },
    redirect: () => {
      const raw = localStorage.getItem('userInfo');
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          if (parsed?.id) {
            return `/user/${parsed.id}`;
          }
        } catch (_error) {
          console.warn('Failed to parse userInfo from localStorage:', _error);
          // ignore parse errors and use default fallback
        }
      }
      return '/';
    },
  },
  {
    path: '/login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { layout: 'guest' }, // 使用空白布局
  },
  {
    path: '/register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { layout: 'guest' },
  },
  {
    path: '/',
    component: () => import('@/views/GuestIndex.vue'),
    meta: { layout: 'guest' }, // 使用访客布局
  },
  {
    path: '/club/:id',
    name: 'ClubDetail',
    component: () => import('@/views/Club/ClubDetail.vue'),
    meta: { layout: 'main', requiresAuth: true }, // 使用主布局
    props: true,
  },
  // {
  //   path: '/',
  //   component: () => import('@/views/GuestIndex.vue'),
  //   meta: { layout: 'main', requiresAuth: true }, // 使用主布局
  // },
  // {
  //   path: '/user/:id',
  //   name: 'User',
  //   component: () => import('../views/User.vue'),
  //   meta: { layout: 'main' },
  //   props: true,
  // },
  //   {
  //     path: '/',
  //     redirect: '/dashboard',
  //     children: [
  //       {
  //         path: 'dashboard',
  //         name: 'Dashboard',
  //         component: () => import('@/views/dashboard/index.vue'),
  //         meta: { title: '控制台', icon: 'home', requiresAuth: true }
  //       },
  //       {
  //         path: 'users',
  //         name: 'UserList',
  //         component: () => import('@/views/system/Users.vue'),
  //         meta: { title: '用户管理', requiresAuth: true, role: 'admin' }
  //       }
  //     ]
  //   }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth) {
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
      return { path: '/login' };
    }
  }
  return true;
});

export default router;
