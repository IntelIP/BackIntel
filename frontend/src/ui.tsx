import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Adapted from the verified IntelIPWebsite shadcn-compatible button primitive.
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50',
  { variants: { variant: {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
    outline: 'border border-border bg-surface hover:bg-muted',
    ghost: 'hover:bg-muted',
  } }, defaultVariants: { variant: 'ghost' } },
)

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>>(
  ({ className, variant, ...props }, ref) => <button ref={ref} className={twMerge(clsx(buttonVariants({ variant }), className))} {...props} />,
)
Button.displayName = 'Button'
