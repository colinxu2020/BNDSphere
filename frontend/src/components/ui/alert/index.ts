import type { VariantProps } from 'class-variance-authority';
import { cva } from 'class-variance-authority';

export { default as Alert } from './Alert.vue';
export { default as AutoCloseAlert } from './AutoCloseAlert.vue';
export { default as AlertDescription } from './AlertDescription.vue';
export { default as AlertTitle } from './AlertTitle.vue';

export const alertVariants = cva(
  'relative w-full rounded-lg border px-4 py-3 text-sm grid has-[>svg]:grid-cols-[calc(var(--spacing)*4)_1fr] grid-cols-[0_1fr] has-[>svg]:gap-x-3 gap-y-0.5 items-start [&>svg]:size-4 [&>svg]:translate-y-0.5 [&>svg]:text-current',
  {
    variants: {
      variant: {
        default: 'bg-card text-card-foreground',
        success:
          'border-green-200 bg-green-50 text-green-800 [&>svg]:text-green-700 *:data-[slot=alert-description]:text-green-700',
        info: 'border-blue-200 bg-blue-50 text-blue-800 [&>svg]:text-blue-700 *:data-[slot=alert-description]:text-blue-700',
        warning:
          'border-yellow-300 bg-yellow-50 text-yellow-900 [&>svg]:text-yellow-700 *:data-[slot=alert-description]:text-yellow-800',
        error:
          'border-red-200 bg-red-50 text-red-800 [&>svg]:text-red-700 *:data-[slot=alert-description]:text-red-700',
        destructive:
          'border-red-200 bg-red-50 text-red-800 [&>svg]:text-red-700 *:data-[slot=alert-description]:text-red-700',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export type AlertVariants = VariantProps<typeof alertVariants>;
