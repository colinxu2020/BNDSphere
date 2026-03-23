<script setup>
import { ref } from 'vue' // 1. 引入响应式工具
import Comment from './components/Comment.vue'
// 定义一个“响应式”变量
const clubName = ref('BNDS 编程社') 
const memberCount = ref(15)
const comments = ref([
  { userName: 'Alice', comment: '这是一个很棒的社团！' },
  { userName: 'Bob', comment: '我喜欢这里的活动！' },
])
// 定义一个函数来改数据
const addMember = () => {
  memberCount.value++ // 注意：在 JS 里改 ref 必须加 .value
}
</script>

<template>
  <div class="p-10">
    <h1 class="text-2xl font-bold">{{ clubName }}</h1>
    <p class="mt-4">当前人数：{{ memberCount }}</p>
    
    <!-- 点击按钮，触发函数 -->
    <button 
      @click="addMember"
      class="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
    >
      增加一人
    </button>
    <br>
    <input v-model="clubName" class="border border-gray-300 rounded px-4 py-2" />
    <p class="mt-4">俱乐部名称：{{ clubName }}</p>
    <br>
    <h2 class="text-xl font-semibold">评论区</h2>
    <Comment 
      v-for="(item, index) in comments"
      :key="index"
      :userName="item.userName"
      :comment="item.comment"
    />
  </div>
</template>