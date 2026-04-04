<script setup>
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  avatarUrl: {
    type: String,
    default: '',
  },
  size: {
    type: String,
    default: 'md',
  },
});
</script>

<template>
  <Avatar :size="props.size">
    <AvatarImage :src="props.avatarUrl" :alt="props.name" />
    <AvatarFallback class="text-2xl">{{ props.name ? props.name[0] : '' }}</AvatarFallback>
  </Avatar>
</template>
