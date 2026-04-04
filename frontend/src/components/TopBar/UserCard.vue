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
});

console.log('UserCard props:', props);
</script>

<template>
  <router-link to="/profile" class="block">
    <div class="flex flex-row gap-2 items-center align-middle cursor-pointer">
      <p>{{ props.name }}</p>
      <Avatar>
        <AvatarImage :src="props.avatarUrl" :alt="props.name" />
        <AvatarFallback>{{ props.name ? props.name[0] : '' }}</AvatarFallback>
      </Avatar>
    </div>
  </router-link>
</template>
