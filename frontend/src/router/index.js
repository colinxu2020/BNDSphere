import { createRouter, createWebHistory } from 'vue-router';

const routes = [
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

// 商业级权限守卫
// router.beforeEach((to, from, next) => {
//   const token = localStorage.getItem('token')
//   if (to.meta.requiresAuth && !token) {
//     next('/login')
//   } else {
//     // 设置页面标题
//     document.title = `${to.meta.title} - 某某商业系统`
//     next()
//   }
// })

export default router;
