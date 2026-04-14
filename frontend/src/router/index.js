import { createRouter, createWebHistory } from 'vue-router';
import { checkAuth } from '@/lib/auth/utils'; // 导入认证检查函数
const routes = [
  {
    path: '/user/:id',
    name: 'UserProfile',
    component: () => import('@/views/profile/Profile.vue'),
    meta: { layout: 'main', requiresAuth: true, title: '用户资料' },
    props: true,
  },
  {
    path: '/settings',
    meta: { layout: 'main', requiresAuth: true, title: '设置' },
    children: [
      {
        path: 'profile',
        name: 'ProfileSettings',
        component: () => import('@/views/profile/ProfileSettings.vue'),
        meta: { title: '个人设置' },
      },
    ],
  },
  {
    path: '/dev/test',
    name: 'DevTest',
    component: () => import('@/views/dev/Test.vue'),
    meta: { layout: 'main', requiresAuth: true, title: '开发测试' },
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/AdminDashboard.vue'),
    meta: { layout: 'main', requiresAuth: true, title: '后台管理' },
  },
  {
    path: '/activities',
    meta: { layout: 'main', requiresAuth: true, title: '活动列表' },
    children: [
      {
        path: '',
        name: 'ActivityList',
        component: () => import('@/views/Activity/ActivityList.vue'),
      },
      {
        path: '/activity/:id',
        name: 'ActivityDetail',
        component: () => import('@/views/Activity/ActivityDetail.vue'),
        meta: { title: '活动详情' },
      },
    ],
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
    meta: { layout: 'guest', title: '登录' }, // 使用空白布局
  },
  {
    path: '/register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { layout: 'guest', title: '注册' },
  },
  {
    path: '/',
    component: () => import('@/views/GuestIndex.vue'),
    meta: { layout: 'guest', title: '首页' }, // 使用访客布局
  },
  {
    path: '/clubs/discover',
    name: 'ClubDiscover',
    component: () => import('@/views/Club/ClubDiscover.vue'),
    meta: { layout: 'guest', title: '发现社团' },
  },
  {
    path: '/club/:id/manage',
    name: 'ClubManage',
    component: () => import('@/views/Club/ClubManage.vue'),
    meta: { layout: 'main', requiresAuth: true, title: '社团管理' },
    props: true,
  },
  {
    path: '/club/:id',
    name: 'ClubDetail',
    component: () => import('@/views/Club/ClubDetail.vue'),
    meta: { layout: 'main', requiresAuth: true, title: '社团详情' }, // 使用主布局
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
