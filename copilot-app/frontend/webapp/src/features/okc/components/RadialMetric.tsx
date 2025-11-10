import { RingProgress, Text, Group, Badge } from '@mantine/core';
import { cn } from '@/features/okc/utils';

interface RadialMetricProps {
  label: string;
  value: number | string;
  percent?: number; // 0..100, if omitted, renders as 100 with neutral color
  color?: string;
  size?: number;
  subtitle?: string;
  badge?: { label: string; color?: string };
  className?: string;
}

export function RadialMetric({
  label,
  value,
  percent,
  color = 'indigo',
  size = 70,
  subtitle,
  badge,
  className,
}: RadialMetricProps) {
  const p = Math.max(0, Math.min(100, percent ?? 100));
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <RingProgress
        size={size}
        thickness={8}
        sections={[{ value: p, color }]}
        label={
          <Text size="xs" fw={700} ta="center">
            {typeof value === 'number' ? value.toFixed(2) : value}
          </Text>
        }
      />
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Text size="sm" fw={600} className="truncate">
            {label}
          </Text>
          {badge && (
            <Badge size="xs" variant="light" color={badge.color ?? 'slate'}>
              {badge.label}
            </Badge>
          )}
        </div>
        {subtitle && (
          <Text size="xs" c="dimmed" className="truncate">
            {subtitle}
          </Text>
        )}
      </div>
    </div>
  );
}

