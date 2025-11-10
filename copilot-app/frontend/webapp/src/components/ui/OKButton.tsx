/**
 * OKButton Component - From OKComputer Design
 * Modern button component with variants and loading states
 */
import React from 'react';
import { cn } from '@/lib/utils';

export interface OKButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
  xl: 'px-8 py-4 text-lg',
};

const variantClasses = {
  primary: 'bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/25',
  secondary: 'bg-surface text-text border border-border hover:bg-surface-elevated',
  ghost: 'bg-transparent text-text hover:bg-surface',
  danger: 'bg-danger text-white hover:bg-danger/90 shadow-lg shadow-danger/25',
  success: 'bg-success text-white hover:bg-success/90 shadow-lg shadow-success/25',
};

export const OKButton = React.forwardRef<HTMLButtonElement, OKButtonProps>(
  ({ 
    className, 
    variant = 'primary', 
    size = 'md', 
    loading = false, 
    leftIcon, 
    rightIcon, 
    children, 
    disabled,
    ...props 
  }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'hover:scale-105 active:scale-95',
          sizeClasses[size],
          variantClasses[variant],
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        {!loading && leftIcon}
        {children}
        {!loading && rightIcon}
      </button>
    );
  }
);

OKButton.displayName = 'OKButton';

export const OKIconButton = React.forwardRef<HTMLButtonElement, Omit<OKButtonProps, 'size'>>((props, ref) => {
  return (
    <OKButton
      ref={ref}
      size="md"
      className={cn('p-2', props.className)}
      {...props}
    />
  );
});

OKIconButton.displayName = 'OKIconButton';

