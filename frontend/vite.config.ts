import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path' // 引入 path 模块

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss()
  ],
  resolve: {
    alias: {
      // 设置 @ 指向 src 目录
      '@': path.resolve(__dirname, './src'),
    },
  },
})
