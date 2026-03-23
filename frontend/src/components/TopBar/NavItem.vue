<template>
  <router-link :to="to" class="text-gray-600 hover:text-blue-600 transition">
    {{ text }}
  </router-link>
</template>

<script setup>
defineProps({
  text: String,
  to: [String, Object]
})
</script>