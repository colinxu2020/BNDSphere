<!-- src/layouts/UserLayout.vue -->
<template>
  <div class="user-layout">
    <!-- 复用全局顶栏（实际项目中可以抽离成组件） -->
    <header class="navbar">
      <div class="logo">我的账户中心</div>
      <router-link to="/">返回首页</router-link>
    </header>

    <div class="user-content-wrapper">
      <div class="user-card">
        <!-- 内部侧边菜单 -->
        <aside class="user-menu">
          <router-link to="/user/profile">基本资料</router-link>
          <router-link to="/user/security">安全设置</router-link>
          <router-link to="/user/msg">我的消息</router-link>
        </aside>

        <!-- 内部页面内容 -->
        <section class="user-view">
          <router-view />
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-layout {
  min-height: 100vh;
  background: #f5f7f9;
}
.navbar {
  height: 60px;
  background: #fff;
  padding: 0 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.user-content-wrapper {
  max-width: 1200px;
  margin: 40px auto;
  padding: 0 20px;
}
.user-card {
  display: flex;
  background: #fff;
  border-radius: 8px;
  min-height: 500px;
  overflow: hidden;
}
.user-menu {
  width: 200px;
  border-right: 1px solid #eee;
  padding: 20px 0;
}
.user-menu a {
  display: block;
  padding: 15px 25px;
  color: #333;
  text-decoration: none;
}
.user-menu a.router-link-active {
  background: #e6f7ff;
  color: #1890ff;
  border-right: 3px solid #1890ff;
}
.user-view {
  flex: 1;
  padding: 30px;
}
</style>
