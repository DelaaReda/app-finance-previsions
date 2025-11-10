import type { PropsWithChildren, ReactNode } from 'react';
import { cn } from '@/features/okc/utils';

interface DashboardGridProps {
  left: ReactNode;
  right: ReactNode;
  className?: string;
}

// Desktop-focused two-column grid: 2fr / 1fr on xl+, stacks on smaller screens
export function DashboardGrid({ left, right, className }: PropsWithChildren<DashboardGridProps>) {
  return (
    <div className={cn('grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-6', className)}>
      <div className="space-y-6">{left}</div>
      <aside className="space-y-4">{right}</aside>
    </div>
  );
}

