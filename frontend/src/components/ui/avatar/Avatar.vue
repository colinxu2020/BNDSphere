<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { AvatarRoot } from 'reka-ui';
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

const avatarVariants = cva('relative flex shrink-0 overflow-hidden rounded-full', {
  variants: {
    size: {
      sm: 'size-8',
      md: 'size-10',
      lg: 'size-16',
      xl: 'size-24',
    },
  },
  defaultVariants: {
    size: 'sm',
  },
});

type AvatarVariants = VariantProps<typeof avatarVariants>;

const props = defineProps<{
  class?: HTMLAttributes['class'];
  size?: AvatarVariants['size'];
}>();
</script>

<template>
  <AvatarRoot data-slot="avatar" :class="cn(avatarVariants({ size }), props.class)">
    <slot />
  </AvatarRoot>
</template>
