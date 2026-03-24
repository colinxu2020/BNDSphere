<!-- src/layouts/DefaultLayout.vue -->
<template>
  <div class="default-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">LOGO</div>
      <nav>
        <router-link to="/dashboard">仪表盘</router-link>
        <router-link to="/users">用户管理</router-link>
        <router-link to="/settings">系统设置</router-link>
      </nav>
    </aside>

    <div class="main-container">
      <!-- 顶栏 -->
      <header class="navbar">
        <div class="breadcrumb">首页 / 当前页面</div>
        <div class="user-info">
          <span>管理员 Admin</span>
          <button @click="handleLogout">退出</button>
        </div>
      </header>

      <!-- 主体内容区 -->
      <main class="content">
        <router-view v-slot="{ Component }">
          <!-- 商业级项目通常会加一个过场动画 -->
          <transition name="slide-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
const handleLogout = () => {
  console.log('执行退出逻辑');
};
</script>

<style scoped>
.default-layout {
  display: flex;
  height: 100vh;
}
.sidebar {
  width: 240px;
  background: #001529;
  color: white;
  display: flex;
  flex-direction: column;
}
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.navbar {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #ddd;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f0f2f5;
}

/* 商业级平滑切页动画 */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
