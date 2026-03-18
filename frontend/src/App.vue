<script setup lang="ts">
// --- PrimeVue 组件 ---
import PButton from 'primevue/button'
import PCard from 'primevue/card'
import PBadge from 'primevue/badge'
import PAvatar from 'primevue/avatar'

// --- shadcn-vue 组件 (假设你已通过 CLI 安装) ---
import { 
  Card as SCard, 
  CardContent as SCardContent, 
  CardFooter as SCardFooter, 
  CardHeader as SCardHeader 
} from '@/components/ui/card'
import { Button as SButton } from '@/components/ui/button'
import { Badge as SBadge } from '@/components/ui/badge'
import { Avatar as SAvatar, AvatarImage as SAvatarImage, AvatarFallback as SAvatarFallback } from '@/components/ui/avatar'
</script>

<template>
  <div class="min-h-screen bg-zinc-50 p-6 md:p-12 space-y-12">
    
    <!-- 标题区 -->
    <header class="max-w-4xl mx-auto border-b border-zinc-200 pb-6">
      <h1 class="text-2xl font-bold tracking-tight text-zinc-900">UI 方案对比测试</h1>
      <p class="text-zinc-500 text-sm mt-1">对比“工业化封装”与“源码所有权”两种手感</p>
    </header>

    <main class="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12">
      
      <!-- 方案 A: PrimeVue (封装思维) -->
      <section class="space-y-4">
        <h2 class="text-sm font-semibold text-blue-600 uppercase tracking-widest">方案 A: PrimeVue</h2>
        
        <PCard class="!border-none !shadow-sm overflow-hidden">
          <template #header>
             <div class="h-32 bg-gradient-to-r from-blue-500 to-indigo-600"></div>
          </template>
          <template #title>
            <div class="flex items-center gap-3">
              <PAvatar image="https://github.com/primefaces.png" shape="circle" size="large" />
              <span>BNDS 机器人社</span>
            </div>
          </template>
          <template #content>
            <p class="text-zinc-600 text-sm leading-relaxed">
              这是 PrimeVue 的实现。所有的槽位（Slot）都是预定义的。
              如果你想改内部间距，通常需要通过 CSS 变量或深度选择器。
            </p>
            <div class="mt-4 flex gap-2">
              <PBadge value="科技" severity="info"></PBadge>
              <PBadge value="50人" severity="secondary"></PBadge>
            </div>
          </template>
          <template #footer>
            <div class="flex gap-2">
              <PButton label="了解详情" variant="text" class="flex-1" />
              <PButton label="立即加入" class="flex-1" />
            </div>
          </template>
        </PCard>
        <p class="text-xs text-zinc-400">特点：快、稳、API 驱动、样式修改稍显被动。</p>
      </section>


      <!-- 方案 B: shadcn-vue (源码思维) -->
      <section class="space-y-4">
        <h2 class="text-sm font-semibold text-emerald-600 uppercase tracking-widest">方案 B: shadcn-vue</h2>
        
        <SCard class="border-zinc-200 shadow-sm overflow-hidden group">
          <SCardHeader class="p-0">
             <div class="h-32 bg-zinc-900 group-hover:bg-emerald-600 transition-colors duration-500"></div>
          </SCardHeader>
          <SCardContent class="p-6">
            <div class="flex items-center gap-3 -mt-12 mb-4">
              <SAvatar class="w-16 h-16 border-4 border-white shadow-sm">
                <SAvatarImage src="https://github.com/shadcn.png" />
                <SAvatarFallback>AI</SAvatarFallback>
              </SAvatar>
              <div class="mt-6">
                 <h3 class="font-bold text-lg">BNDS 极客社</h3>
                 <p class="text-xs text-zinc-400">建立于 2024</p>
              </div>
            </div>
            <p class="text-zinc-600 text-sm leading-relaxed">
              这是 shadcn 的实现。你会发现你可以自由控制 Avatar 的位置。
              甚至可以实现“头像悬浮在背景图之上”这种精细布局。
            </p>
            <div class="mt-4 flex gap-2">
              <SBadge variant="outline" class="rounded-full">极客</SBadge>
              <SBadge variant="secondary" class="rounded-full">不限人数</SBadge>
            </div>
          </SCardContent>
          <SCardFooter class="p-6 pt-0 flex flex-col md:flex-row gap-2">
             <SButton variant="ghost" class="w-full md:w-auto">了解详情</SButton>
             <SButton class="w-full md:flex-1 bg-emerald-600 hover:bg-emerald-700">立即加入</SButton>
          </SCardFooter>
        </SCard>
        <p class="text-xs text-zinc-400">特点：灵活、透明、Tailwind 原生手感、组件布局随你捏。</p>
      </section>

    </main>
  </div>
</template>

<style scoped>
/* PrimeVue 的卡片内部通常有默认 padding，如果不爽，你需要手动覆盖 */
:deep(.p-card-body) {
  padding: 1.5rem;
}
</style>