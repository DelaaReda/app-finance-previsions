import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import { cn } from '@/features/okc/utils';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'elevated' | 'outlined';
  padding?: 'sm' | 'md' | 'lg' | 'xl';
  hoverable?: boolean;
}

const paddingClasses = {
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
  xl: 'p-12',
};

const variantClasses = {
  default: 'bg-surface border border-border',
  glass: 'bg-glass border border-glass-border backdrop-blur-md',
  elevated: 'bg-surface-elevated border border-border shadow-lg',
  outlined: 'bg-transparent border-2 border-border',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, variant = 'default', padding = 'md', hoverable = true, children, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        'rounded-xl transition-all duration-300',
        variantClasses[variant],
        paddingClasses[padding],
        hoverable && 'hover:scale-[1.01] hover:shadow-xl',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
});

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardHeader(
  { className, children, ...props },
  ref,
) {
  return (
    <div ref={ref} className={cn('mb-4 flex items-center justify-between gap-3', className)} {...props}>
      {children}
    </div>
  );
});

export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(function CardTitle(
  { className, children, ...props },
  ref,
) {
  return (
    <h3 ref={ref} className={cn('text-lg font-semibold text-text', className)} {...props}>
      {children}
    </h3>
  );
});

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function CardContent(
  { className, children, ...props },
  ref,
) {
  return (
    <div ref={ref} className={cn('space-y-4', className)} {...props}>
      {children}
    </div>
  );
});
