<script setup>
const props = defineProps({
  comment: String,
  userName: String,
})
</script>

<template>
  <div class="comment border border-gray-300 rounded p-4 mb-4">
    <p class="user-name font-semibold">{{ userName }}</p>
    <p class="comment-content">{{ comment }}</p>
  </div>
</template>