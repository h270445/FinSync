import { cn } from '@/lib/utils'

/** A styled native <select>: accessible and phone-friendly for simple filters. */
export function NativeSelect({ className, ...props }: React.ComponentProps<'select'>) {
  return (
    <select
      className={cn(
        'h-9 rounded-md border border-input bg-card px-2 text-sm',
        'focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
        className,
      )}
      {...props}
    />
  )
}
